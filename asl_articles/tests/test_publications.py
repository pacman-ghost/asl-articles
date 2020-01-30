""" Test publication operations. """

import os
import urllib.request
import urllib.error
import json
import base64
from collections import defaultdict

from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException

from asl_articles.search import SEARCH_ALL, SEARCH_ALL_PUBLICATIONS, SEARCH_ALL_ARTICLES
from asl_articles.tests.test_articles import create_article, edit_article
from asl_articles.tests.utils import init_tests, load_fixtures, select_main_menu_option, select_sr_menu_option, \
    do_search, get_search_results, get_search_result_names, check_search_result, \
    wait_for, wait_for_elem, wait_for_not_elem, find_child, find_children, find_search_result, set_elem_text, \
    set_toast_marker, check_toast, send_upload_data, check_ask_dialog, check_error_msg, \
    change_image, get_publication_row
from asl_articles.tests.react_select import ReactSelect

# ---------------------------------------------------------------------

def test_edit_publication( webdriver, flask_app, dbconn ):
    """Test editing publications."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="publications.json" )

    # edit "ASL Journal #2"
    results = do_search( SEARCH_ALL_PUBLICATIONS )
    sr = find_search_result( "ASL Journal (2)", results )
    edit_publication( sr, {
        "name": "  ASL Journal (updated)  ",
        "edition": "  2a  ",
        "description": "  Updated ASLJ description.  ",
        "tags": [ "+abc", "+xyz" ],
        "url": "  http://aslj-updated.com  ",
    } )

    # check that the search result was updated in the UI
    expected = [ "ASL Journal (updated)", "2a", "Updated ASLJ description.", ["abc","xyz"], "http://aslj-updated.com/" ]
    sr = find_search_result( "ASL Journal (updated) (2a)" )
    check_search_result( sr, _check_sr, expected )

    # NOTE: We used to try to remove all fields from "ASL Journal #2" (which should fail, since we can't
    # have an empty name), but we can no longer remove an existing publication name (which is OK, since we
    # don't want to allow that, only change it).

    # check that the publication was updated in the database
    results = do_search( SEARCH_ALL_PUBLICATIONS )
    sr = find_search_result( "ASL Journal (updated) (2a)", results )
    check_search_result( sr, _check_sr, expected )

# ---------------------------------------------------------------------

def test_create_publication( webdriver, flask_app, dbconn ):
    """Test creating new publications."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="publications.json" )
    do_search( SEARCH_ALL_PUBLICATIONS )

    # try creating a publication with no name (should fail)
    create_publication( {}, toast_type=None )
    check_error_msg( "Please specify the publication's name." )

    # enter a name and other details
    edit_publication( None, { # nb: the form is still on-screen
        "name": "New publication",
        "edition": "#1",
        "description": "New publication description.",
        "tags": [ "+111", "+222", "+333" ],
        "url": "http://new-publication.com"
    } )

    # check that the new publication appears in the UI
    expected = [ "New publication", "#1", "New publication description.",
        ["111","222","333"], "http://new-publication.com/"
    ]
    check_search_result( "New publication (#1)", _check_sr, expected )

    # check that the new publication has been saved in the database
    results = do_search( SEARCH_ALL_PUBLICATIONS )
    sr = find_search_result( "New publication (#1)", results )
    check_search_result( sr, _check_sr, expected )

# ---------------------------------------------------------------------

def test_delete_publication( webdriver, flask_app, dbconn ):
    """Test deleting publications."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="publications.json" )

    # start to delete a publication, but cancel the operation
    article_name = "ASL Journal (2)"
    results = do_search( SEARCH_ALL_PUBLICATIONS )
    sr = find_search_result( article_name, results )
    select_sr_menu_option( sr, "delete" )
    check_ask_dialog( ( "Delete this publication?", article_name ), "cancel" )

    # check that search results are unchanged on-screen
    results2 = get_search_results()
    assert results2 == results

    # check that the search results are unchanged in the database
    results3 = do_search( SEARCH_ALL_PUBLICATIONS )
    assert results3 == results

    # delete the publication
    sr = find_search_result( article_name, results3 )
    select_sr_menu_option( sr, "delete" )
    set_toast_marker( "info" )
    check_ask_dialog( ( "Delete this publication?", article_name ), "ok" )
    wait_for( 2, lambda: check_toast( "info", "The publication was deleted." ) )

    # check that search result was removed on-screen
    wait_for( 2, lambda: article_name not in get_search_result_names() )

    # check that the search result was deleted from the database
    results = do_search( SEARCH_ALL_PUBLICATIONS )
    assert article_name not in get_search_result_names( results )

# ---------------------------------------------------------------------

def test_images( webdriver, flask_app, dbconn ): #pylint: disable=too-many-statements
    """Test publication images."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, max_image_upload_size=2*1024 )

    def check_image( expected ):

        # check the image in the publication's search result
        def check_sr_image( expected ):
            img = find_child( "img.image", pub_sr )
            if expected:
                expected_url = flask_app.url_for( "get_image", image_type="publication", image_id=pub_id )
                image_url = img.get_attribute( "src" ).split( "?" )[0]
                return image_url == expected_url
            else:
                return not img
        wait_for( 2, lambda: check_sr_image( expected ) )

        # check the image in the publisher's config
        select_sr_menu_option( pub_sr, "edit" )
        dlg = wait_for_elem( 2, "#publication-form" )
        if expected:
            # make sure there is an image
            img = find_child( ".row.image img.image", dlg )
            image_url = img.get_attribute( "src" )
            assert "/images/publication/{}".format( pub_id ) in image_url
            # make sure the "remove image" icon is visible
            btn = find_child( ".row.image .remove-image", dlg )
            assert btn.is_displayed()
            # make sure the publication's image is correct
            resp = urllib.request.urlopen( image_url ).read()
            assert resp == open( expected, "rb" ).read()
        else:
            # make sure there is no image
            img = find_child( ".row.image img.image", dlg )
            assert img.get_attribute( "src" ).endswith( "/images/placeholder.png" )
            # make sure the "remove image" icon is hidden
            btn = find_child( ".row.image .remove-image", dlg )
            assert not btn.is_displayed()
            # make sure the publication's image is not available
            url = flask_app.url_for( "get_image", image_type="publication", image_id=pub_id )
            try:
                resp = urllib.request.urlopen( url )
                assert False, "Should never get here!"
            except urllib.error.HTTPError as ex:
                assert ex.code == 404
        find_child( ".cancel", dlg ).click()

    # create an publication with no image
    create_publication( {"name": "Test Publication" } )
    results = get_search_results()
    assert len(results) == 1
    pub_sr = results[0]
    pub_id = pub_sr.get_attribute( "testing--pub_id" )
    check_image( None )

    # add an image to the publication
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/1.gif" )
    edit_publication( pub_sr, { "image": fname } )
    check_image( fname )

    # change the publication's image
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/2.gif" )
    edit_publication( pub_sr, { "image": fname } )
    check_image( fname )

    # remove the publication's image
    edit_publication( pub_sr, { "image": None } )
    check_image( None )

    # try to upload an image that's too large
    select_sr_menu_option( pub_sr, "edit" )
    dlg = wait_for_elem( 2, "#publication-form" )
    data = base64.b64encode( 5000 * b" " )
    data = "{}|{}".format( "too-big.png", data.decode("ascii") )
    send_upload_data( data,
        lambda: find_child( ".row.image img.image", dlg ).click()
    )
    check_error_msg( "The file must be no more than 2 KB in size." )

# ---------------------------------------------------------------------

def test_parent_publisher( webdriver, flask_app, dbconn ):
    """Test setting a publication's parent publisher."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="parents.json" )

    def check_result( sr, expected_parent ): #pylint: disable=too-many-return-statements

        # check that the parent publisher was updated in the UI
        elem = find_child( ".header .publisher", sr )
        if expected_parent:
            if elem.text != "{}".format( expected_parent[1] ):
                return None
        else:
            if elem is not None:
                return None

        # check that the parent publisher was updated in the database
        pub_id = sr.get_attribute( "testing--pub_id" )
        url = flask_app.url_for( "get_publication", pub_id=pub_id )
        pub = json.load( urllib.request.urlopen( url ) )
        if expected_parent:
            if pub["publ_id"] != expected_parent[0]:
                return None
        else:
            if pub["publ_id"] is not None:
                return None

        # check that the parent publisher was updated in the UI
        results = do_search( '"MMP News"' )
        assert len(results) == 1
        sr = results[0]
        elem = find_child( ".header .publisher", sr )
        if expected_parent:
            if elem.text != "{}".format( expected_parent[1] ):
                return None
        else:
            if elem is not None:
                return None

        return sr

    # create a publication with no parent publisher
    create_publication( { "name": "MMP News" } )
    results = get_search_results()
    assert len(results) == 1
    sr = wait_for( 2, lambda: check_result( results[0], None ) )

    # change the publication to have a publisher
    edit_publication( sr, { "publisher": "Multiman Publishing" } )
    sr = wait_for( 2, lambda: check_result( sr, (1, "Multiman Publishing") ) )

    # change the publication back to having no publisher
    edit_publication( sr, { "publisher": "(none)" } )
    sr = wait_for( 2, lambda: check_result( results[0], None ) )

# ---------------------------------------------------------------------

def test_cascading_deletes( webdriver, flask_app, dbconn ):
    """Test cascading deletes."""

    # initialize
    session = init_tests( webdriver, flask_app, dbconn )

    def do_test( pub_name, expected_warning, expected_articles ):

        # initialize
        load_fixtures( session, "cascading-deletes-2.json" )
        results = do_search( SEARCH_ALL )

        # delete the specified publication
        sr = find_search_result( pub_name, results )
        select_sr_menu_option( sr, "delete" )
        check_ask_dialog( ( "Delete this publication?", pub_name, expected_warning ), "ok" )

        def check_results():
            results = wait_for( 2, lambda: get_results( len(expected_articles) ) )
            assert set( results ) == set( expected_articles )
        def get_results( expected_len ):
            # NOTE: The UI will remove anything that has been deleted, so we need to
            # give it a bit of time to finish doing this.
            try:
                results = get_search_result_names()
            except StaleElementReferenceException:
                return None
            results = [ r for r in results if r.startswith( "article" ) ]
            if len(results) == expected_len:
                return results
            return None

        # check that deleted associated articles were removed from the UI
        check_results()

        # check that associated articles were removed from the database
        results = do_search( SEARCH_ALL_ARTICLES )
        check_results()

    # do the tests
    do_test( "Cascading Deletes 1",
        "No articles will be deleted", ["article 2","article 3a","article 3b"]
    )
    do_test( "Cascading Deletes 2",
        "1 associated article will also be deleted", ["article 3a","article 3b"]
    )
    do_test( "Cascading Deletes 3",
        "2 associated articles will also be deleted", ["article 2"]
    )

# ---------------------------------------------------------------------

def test_unicode( webdriver, flask_app, dbconn ):
    """Test Unicode content."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create a publication with Unicode content
    create_publication( {
        "name": "japan = \u65e5\u672c",
        "edition": "\u263a",
        "tags": [ "+\u0e51", "+\u0e52", "+\u0e53" ],
        "url": "http://\ud55c\uad6d.com",
        "description": "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1"
    } )

    # check that the new publication is showing the Unicode content correctly
    results = do_search( SEARCH_ALL_PUBLICATIONS )
    assert len( results ) == 1
    check_search_result( results[0], _check_sr, [
        "japan = \u65e5\u672c",  "\u263a",
        "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1",
        [ "\u0e51", "\u0e52", "\u0e53" ],
        "http://xn--3e0b707e.com/"
    ] )

# ---------------------------------------------------------------------

def test_clean_html( webdriver, flask_app, dbconn ):
    """Test cleaning HTML content."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )
    replace = [
        "[\u00ab\u00bb\u201c\u201d\u201e\u201f foo\u2014bar \u2018\u2019\u201a\u201b\u2039\u203a]",
        "[\"\"\"\"\"\" foo - bar '''''']"
    ]

    # create a publication with HTML content
    create_publication( {
        "name": "name: <span style='boo!'> <b>bold</b> <xxx>xxx</xxx> <i>italic</i> {}".format( replace[0] ),
        "edition": "<i>2</i>",
        "description": "bad stuff here: <script>HCF</script> {}".format( replace[0] )
    }, toast_type="warning" )

    # check that the HTML was cleaned
    sr = check_search_result( None, _check_sr, [
        "name: bold xxx italic {}".format( replace[1] ),
        "2",
        "bad stuff here: {}".format( replace[1] ),
        [], None
    ] )
    assert find_child( ".name", sr ).get_attribute( "innerHTML" ) \
        == "name: <span> <b>bold</b> xxx <i>italic</i> {}</span> (<i>2</i>)".format( replace[1] )
    assert check_toast( "warning", "Some values had HTML cleaned up.", contains=True )

    # update the publication with new HTML content
    edit_publication( sr, {
        "name": "<div style='...'>updated</div>"
    }, toast_type="warning" )
    results = get_search_results()
    assert len(results) == 1
    wait_for( 2, lambda: find_child( ".name", results[0] ).text == "updated (2)" )
    assert check_toast( "warning", "Some values had HTML cleaned up.", contains=True )

# ---------------------------------------------------------------------

def test_timestamps( webdriver, flask_app, dbconn ):
    """Test setting of timestamps."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create a publication
    create_publication( { "name": "My Publication" } )
    results = get_search_results()
    assert len(results) == 1
    pub_sr = results[0]
    pub_id = pub_sr.get_attribute( "testing--pub_id" )

    # check its timestamps
    row = get_publication_row( dbconn, pub_id, ["time_created","time_updated"] )
    assert row[0]
    assert row[1] is None

    # update the publication
    edit_publication( pub_sr, { "name": "My Publication (updated)" } )

    # check its timestamps
    row2 = get_publication_row( dbconn, pub_id, ["time_created","time_updated"] )
    assert row2[0] == row[0]
    assert row2[1] > row2[0]

# ---------------------------------------------------------------------

def test_article_order( webdriver, flask_app, dbconn ):
    """Test ordering of articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="article-order.json" )

    def check_article_order( expected ):

        # check the article order in the database
        articles = defaultdict( list )
        query = dbconn.execute(
            "SELECT pub_name, article_title, article_seqno"
            " FROM article LEFT JOIN publication"
            " ON article.pub_id = publication.pub_id"
            " ORDER BY article.pub_id, article_seqno"
        )
        for row in query:
            articles[ row[0] ].append( ( row[1], row[2] ) )
        assert articles == expected

        # check the article order in the UI
        results = do_search( SEARCH_ALL )
        for pub_name in expected:
            if not pub_name:
                continue
            sr = find_search_result( pub_name, results )
            select_sr_menu_option( sr, "edit" )
            dlg = wait_for_elem( 2, "#publication-form" )
            articles = [ a.text for a in find_children( ".articles li.draggable", dlg ) ]
            find_child( ".cancel", dlg ).click()
            assert articles == [ a[0] for a in expected[pub_name] ]

    # create some articles (to check the seq# is being assigned correctly)
    create_article( { "title": "Article 1", "publication": "Publication A" } )
    check_article_order( {
        "Publication A": [ ("Article 1",1) ]
    } )
    create_article( { "title": "Article 2", "publication": "Publication A" } )
    check_article_order( {
        "Publication A": [ ("Article 1",1), ("Article 2",2) ]
    } )
    create_article( { "title": "Article 3", "publication": "Publication A" } )
    check_article_order( {
        "Publication A": [ ("Article 1",1), ("Article 2",2), ("Article 3",3) ]
    } )

    # create some articles (to check the seq# is being assigned correctly)
    create_article( { "title": "Article 5", "publication": "Publication B" } )
    check_article_order( {
        "Publication A": [ ("Article 1",1), ("Article 2",2), ("Article 3",3) ],
        "Publication B": [ ("Article 5",1) ]
    } )
    create_article( { "title": "Article 6", "publication": "Publication B" } )
    check_article_order( {
        "Publication A": [ ("Article 1",1), ("Article 2",2), ("Article 3",3) ],
        "Publication B": [ ("Article 5",1), ("Article 6",2) ]
    } )

    # NOTE: It would be nice to test re-ordering articles via drag-and-drop,
    # but Selenium just ain't co-operating... :-/

    # move an article to another publication
    sr = find_search_result( "Article 1" )
    edit_article( sr, { "publication": "Publication B" } )
    check_article_order( {
        "Publication A": [ ("Article 2",2), ("Article 3",3) ],
        "Publication B": [ ("Article 5",1), ("Article 6",2), ("Article 1",3) ]
    } )

    # remove the article from the publication
    sr = find_search_result( "Article 1" )
    edit_article( sr, { "publication": "(none)" } )
    check_article_order( {
        "Publication A": [ ("Article 2",2), ("Article 3",3) ],
        "Publication B": [ ("Article 5",1), ("Article 6",2) ],
        None: [ ("Article 1", None) ]
    } )

    # add the article to another publication
    sr = find_search_result( "Article 1" )
    edit_article( sr, { "publication": "Publication A" } )
    check_article_order( {
        "Publication A": [ ("Article 2",2), ("Article 3",3), ("Article 1",4) ],
        "Publication B": [ ("Article 5",1), ("Article 6",2) ],
    } )

# ---------------------------------------------------------------------

def create_publication( vals, toast_type="info" ):
    """Create a new publication."""

    # initialize
    if toast_type:
        set_toast_marker( toast_type )

    # create the new publication
    select_main_menu_option( "new-publication" )
    dlg = wait_for_elem( 2, "#publication-form" )
    for key,val in vals.items():
        if key == "name":
            elem = find_child( ".row.name .react-select input", dlg )
            set_elem_text( elem, val )
            elem.send_keys( Keys.RETURN )
        elif key == "tags":
            select = ReactSelect( find_child( ".row.tags .react-select", dlg ) )
            select.update_multiselect_values( *val )
        else:
            sel = ".row.{} {}".format( key , "textarea" if key == "description" else "input" )
            set_elem_text( find_child( sel, dlg ), val )
    find_child( "button.ok", dlg ).click()

    if toast_type:
        # check that the new publication was created successfully
        wait_for( 2,
            lambda: check_toast( toast_type, "created OK", contains=True )
        )
        wait_for_not_elem( 2, "#publication-form" )

def edit_publication( sr, vals, toast_type="info", expected_error=None ):
    """Edit a publication's details."""

    # initialize
    if sr:
        select_sr_menu_option( sr, "edit" )
    else:
        pass # nb: we assume that the dialog is already on-screen
    dlg = wait_for_elem( 2, "#publication-form" )

    # update the specified publication's details
    for key,val in vals.items():
        if key == "image":
            if val:
                data = base64.b64encode( open( val, "rb" ).read() )
                data = "{}|{}".format( os.path.split(val)[1], data.decode("ascii") )
                change_image( find_child( ".row.image img.image", dlg ), data )
            else:
                find_child( ".row.image .remove-image", dlg ).click()
        elif key == "name":
            elem = find_child( ".row.name .react-select input", dlg )
            set_elem_text( elem, val )
            elem.send_keys( Keys.RETURN )
        elif key == "publisher":
            select = ReactSelect( find_child( ".row.publisher .react-select", dlg ) )
            select.select_by_name( val )
        elif key == "tags":
            select = ReactSelect( find_child( ".row.tags .react-select", dlg ) )
            select.update_multiselect_values( *val )
        else:
            sel = ".row.{} {}".format( key , "textarea" if key == "description" else "input" )
            set_elem_text( find_child( sel, dlg ), val )
    set_toast_marker( toast_type )
    find_child( "button.ok", dlg ).click()

    # check what happened
    if expected_error:
        # we were expecting an error, confirm the error message
        check_error_msg( expected_error )
    else:
        # we were expecting the update to work, confirm this
        expected = "updated OK" if sr else "created OK"
        wait_for( 2,
            lambda: check_toast( toast_type, expected, contains=True )
        )
        wait_for_not_elem( 2, "#publication-form" )

# ---------------------------------------------------------------------

def _check_sr( sr, expected ):
    """Check a search result."""

    # check the name and edition
    expected_name = expected[0]
    if expected[1]:
        expected_name += " ({})".format( expected[1] )
    if find_child( ".name", sr ).text != expected_name:
        return False

    # check the description
    if find_child( ".description", sr ).text != expected[2]:
        return False

    # check the tags
    tags = [ t.text for t in find_children( ".tag", sr ) ]
    if tags != expected[3]:
        return False

    # check the publication's link
    elem = find_child( "a.open-link", sr )
    if expected[4]:
        assert elem
        if elem.get_attribute( "href" ) != expected[4]:
            return False
    else:
        assert elem is None

    return True
