""" Test publisher operations. """

import os
import urllib.request
import urllib.error
import base64

from selenium.common.exceptions import StaleElementReferenceException

from asl_articles.search import SEARCH_ALL, SEARCH_ALL_PUBLISHERS
from asl_articles.tests.test_publications import create_publication, edit_publication
from asl_articles.tests.utils import init_tests, load_fixtures, select_main_menu_option, select_sr_menu_option, \
    do_search, get_search_results, get_search_result_names, check_search_result, \
    do_test_confirm_discard_changes, \
    wait_for, wait_for_elem, wait_for_not_elem, find_child, find_children, find_search_result, set_elem_text, \
    set_toast_marker, check_toast, send_upload_data, change_image, remove_image, get_publisher_row, \
    check_ask_dialog, check_error_msg

# ---------------------------------------------------------------------

def test_edit_publisher( webdriver, flask_app, dbconn ):
    """Test editing publishers."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="publishers.json" )

    # edit "Avalon Hill"
    results = do_search( SEARCH_ALL_PUBLISHERS )
    sr = find_search_result( "Avalon Hill", results )
    edit_publisher( sr, {
        "name": "  Avalon Hill (updated)  ",
        "description": "  Updated AH description.  ",
        "url": "  http://ah-updated.com  "
    } )

    # check that the search result was updated in the UI
    sr = check_search_result( "Avalon Hill (updated)", _check_sr, [
        "Avalon Hill (updated)", "Updated AH description.", "http://ah-updated.com/"
    ] )

    # remove all fields from the publisher
    edit_publisher( sr, {
        "name": "AH",
        "description": "",
        "url": ""
    } )

    # check that the search result was updated in the UI
    expected = [ "AH", "", None ]
    check_search_result( expected[0], _check_sr, expected )

    # check that the publisher was updated in the database
    results = do_search( SEARCH_ALL_PUBLISHERS )
    check_search_result( expected[0], _check_sr, expected )

# ---------------------------------------------------------------------

def test_create_publisher( webdriver, flask_app, dbconn ):
    """Test creating new publishers."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="publishers.json" )
    do_search( SEARCH_ALL_PUBLISHERS )

    # create a new publisher
    create_publisher( {
        "name": "New publisher",
        "url": "http://new-publisher.com",
        "description": "New publisher description."
    } )

    # check that the new publisher appears in the UI
    expected = [ "New publisher", "New publisher description.", "http://new-publisher.com/" ]
    check_search_result( expected[0], _check_sr, expected )

    # check that the new publisher has been saved in the database
    do_search( SEARCH_ALL_PUBLISHERS )
    check_search_result( expected[0], _check_sr, expected )

# ---------------------------------------------------------------------

def test_constraints( webdriver, flask_app, dbconn ):
    """Test constraint validation."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, disable_constraints=False, fixtures="publishers.json" )

    # try to create a publisher with no title
    dlg = create_publisher( {}, expected_error="Please give them a name." )

    # try to create a duplicate publisher
    create_publisher( { "name": "Avalon Hill" }, dlg=dlg,
        expected_error = "There is already a publisher with this name."
    )

    # set the publisher's name
    create_publisher( { "name": "Joe Publisher" }, dlg=dlg )

    # check that the search result was updated in the UI
    expected = [ "Joe Publisher", "", "" ]
    sr = check_search_result( expected[0], _check_sr, expected )

    # try to remove the publisher's name
    edit_publisher( sr, { "name": "   " }, expected_error="Please give them a name." )

# ---------------------------------------------------------------------

def test_delete_publisher( webdriver, flask_app, dbconn ):
    """Test deleting publishers."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="publishers.json" )

    # start to delete a publisher, but cancel the operation
    article_name = "Le Franc Tireur"
    results = do_search( SEARCH_ALL_PUBLISHERS )
    result_names = get_search_result_names( results )
    sr = find_search_result( article_name, results )
    select_sr_menu_option( sr, "delete" )
    check_ask_dialog( ( "Delete this publisher?", article_name ), "cancel" )

    # check that search results are unchanged on-screen
    results2 = get_search_results()
    assert results2 == results

    # check that the search results are unchanged in the database
    results3 = do_search( SEARCH_ALL_PUBLISHERS )
    assert get_search_result_names( results3 ) == result_names

    # delete the publisher
    sr = find_search_result( article_name, results3 )
    select_sr_menu_option( sr, "delete" )
    set_toast_marker( "info" )
    check_ask_dialog( ( "Delete this publisher?", article_name ), "ok" )
    wait_for( 2,
        lambda: check_toast( "info", "The publisher was deleted." )
    )

    # check that search result was removed on-screen
    wait_for( 2, lambda: article_name not in get_search_result_names() )

    # check that the search result was deleted from the database
    results = do_search( SEARCH_ALL_PUBLISHERS )
    assert article_name not in get_search_result_names( results )

# ---------------------------------------------------------------------

def test_images( webdriver, flask_app, dbconn ): #pylint: disable=too-many-statements
    """Test publisher images."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, max_image_upload_size=2*1024 )

    def check_image( expected ):

        # check the image in the publisher's search result
        def check_sr_image():
            img = find_child( "img.image", publ_sr )
            if expected:
                expected_image_url = flask_app.url_for( "get_image", image_type="publisher", image_id=publ_id )
                image_url = img.get_attribute( "src" ).split( "?" )[0]
                return image_url == expected_image_url
            else:
                return not img
        wait_for( 2, check_sr_image )

        # check the image in the publisher's config
        select_sr_menu_option( publ_sr, "edit" )
        dlg = wait_for_elem( 2, "#publisher-form" )
        if expected:
            # make sure there is an image
            img = find_child( ".row.image img.image", dlg )
            image_url = img.get_attribute( "src" )
            assert "/images/publisher/{}".format( publ_id ) in image_url
            # make sure the "remove image" icon is visible
            btn = find_child( ".row.image .remove-image", dlg )
            assert btn.is_displayed()
            # make sure the publisher's image is correct
            resp = urllib.request.urlopen( image_url ).read()
            assert resp == open(expected,"rb").read()
        else:
            # make sure there is no image
            img = find_child( ".row.image img.image", dlg )
            assert img.get_attribute( "src" ).endswith( "/images/placeholder.png" )
            # make sure the "remove image" icon is hidden
            btn = find_child( ".row.image .remove-image", dlg )
            assert not btn.is_displayed()
            # make sure the publisher's image is not available
            url = flask_app.url_for( "get_image", image_type="publisher", image_id=publ_id )
            try:
                resp = urllib.request.urlopen( url )
                assert False, "Should never get here!"
            except urllib.error.HTTPError as ex:
                assert ex.code == 404
        find_child( ".cancel", dlg ).click()

    # create an publisher with no image
    create_publisher( { "name": "Test Publisher" } )
    results = get_search_results()
    assert len(results) == 1
    publ_sr = results[0]
    publ_id = publ_sr.get_attribute( "testing--publ_id" )
    check_image( None )

    # add an image to the publisher
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/1.gif" )
    edit_publisher( publ_sr, { "image": fname } )
    check_image( fname )

    # change the publisher's image
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/2.gif" )
    edit_publisher( publ_sr, { "image": fname } )
    check_image( fname )

    # remove the publisher's image
    edit_publisher( publ_sr, { "image": None } )
    check_image( None )

    # try to upload an image that's too large
    select_sr_menu_option( publ_sr, "edit" )
    dlg = wait_for_elem( 2, "#publisher-form" )
    data = base64.b64encode( 5000 * b" " )
    data = "{}|{}".format( "too-big.png", data.decode("ascii") )
    send_upload_data( data,
        lambda: find_child( ".row.image img.image", dlg ).click()
    )
    check_error_msg( "The file must be no more than 2 KB in size." )

# ---------------------------------------------------------------------

def test_cascading_deletes( webdriver, flask_app, dbconn ):
    """Test cascading deletes."""

    # initialize
    session = init_tests( webdriver, flask_app, dbconn )

    def check_results( sr_type, expected, expected_deletions ):
        expected = [ "{} {}".format( sr_type, p ) for p in expected ]
        expected = [ e for e in expected if e not in expected_deletions ]
        results = wait_for( 2, lambda: get_results( sr_type, len(expected) ) )
        assert set( results ) == set( expected )
    def get_results( sr_type, expected_len ):
        # NOTE: The UI will remove anything that has been deleted, so we need to
        # give it a bit of time to finish doing this.
        try:
            results = get_search_result_names()
        except StaleElementReferenceException:
            return None
        results = [ r for r in results if r.startswith( sr_type ) ]
        if len(results) == expected_len:
            return results
        return None

    def do_test( publ_name, expected_warning, expected_deletions ):

        # initialize
        load_fixtures( session, "cascading-deletes-1.json" )
        results = do_search( SEARCH_ALL )

        # delete the specified publisher
        sr = find_search_result( publ_name, results )
        select_sr_menu_option( sr, "delete" )
        check_ask_dialog( ( "Delete this publisher?", publ_name, expected_warning ), "ok" )

        # check that deleted associated publications/articles were removed from the UI
        def check_publications():
            check_results(
                "publication", [ "2", "3", "4", "5a", "5b", "6a", "6b", "7a", "7b", "8a", "8b" ],
                expected_deletions
            )
        def check_articles():
            check_results(
                "article", [ "3", "4a", "4b", "6a", "7a", "7b", "8a.1", "8a.2", "8b.1", "8b.2" ],
                expected_deletions
            )
        check_publications()
        check_articles()

        # check that associated publications/articles were removed from the database
        results = do_search( SEARCH_ALL )
        check_publications()
        check_articles()

    # do the tests
    do_test( "#pubs=0, #articles=0",
        "No publications nor articles will be deleted", []
    )
    do_test( "#pubs=1, #articles=0",
        "1 publication will also be deleted",
        [ "publication 2" ]
    )
    do_test( "#pubs=1, #articles=1",
        "1 publication and 1 article will also be deleted",
        [ "publication 3", "article 3" ]
    )
    do_test( "#pubs=1, #articles=2",
        "1 publication and 2 articles will also be deleted",
        [ "publication 4", "article 4a", "article 4b" ]
    )
    do_test( "#pubs=2, #articles=0",
        "2 publications will also be deleted",
        [ "publication 5a", "publication 5b" ]
    )
    do_test( "#pubs=2, #articles=1",
        "2 publications and 1 article will also be deleted",
        [ "publication 6a", "publication 6b", "article 6a" ]
    )
    do_test( "#pubs=2, #articles=2",
        "2 publications and 2 articles will also be deleted",
        [ "publication 7a", "publication 7b", "article 7a", "article 7b" ]
    )
    do_test( "#pubs=2, #articles=4",
        "2 publications and 4 articles will also be deleted",
        [ "publication 8a", "publication 8b", "article 8a.1", "article 8a.2", "article 8b.1", "article 8b.2" ]
    )

# ---------------------------------------------------------------------

def test_unicode( webdriver, flask_app, dbconn ):
    """Test Unicode content."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create a publisher with Unicode content
    create_publisher( {
        "name": "japan = \u65e5\u672c",
        "url": "http://\ud55c\uad6d.com",
        "description": "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1"
    } )

    # check that the new publisher is showing the Unicode content correctly
    results = do_search( SEARCH_ALL_PUBLISHERS )
    assert len(results) == 1
    check_search_result( results[0], _check_sr, [
        "japan = \u65e5\u672c",
        "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1",
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

    # create a publisher with HTML content
    create_publisher( {
        "name": "name: <span onclick='boo!'> <b>bold</b> <xxx>xxx</xxx> <i>italic</i> {}".format( replace[0] ),
        "description": "bad stuff here: <script>HCF</script> {}".format( replace[0] )
    }, toast_type="warning" )

    # check that the HTML was cleaned
    sr = check_search_result( None, _check_sr, [
        "name: bold xxx italic {}".format( replace[1] ),
        "bad stuff here: {}".format( replace[1] ),
        None
    ] )
    assert find_child( ".name", sr ).get_attribute( "innerHTML" ) \
        == "name: <span> <b>bold</b> xxx <i>italic</i> {}</span>".format( replace[1] )
    assert check_toast( "warning", "Some values had HTML cleaned up.", contains=True )

    # update the publisher with new HTML content
    edit_publisher( sr, {
        "name": "<div onclick='...'>updated</div>"
    }, toast_type="warning" )
    results = get_search_results()
    assert len(results) == 1
    wait_for( 2, lambda: find_child( ".name", sr ).text == "updated" )
    assert check_toast( "warning", "Some values had HTML cleaned up.", contains=True )

# ---------------------------------------------------------------------

def test_confirm_discard_changes( webdriver, flask_app, dbconn ):
    """Test confirmation of discarding changes made to a dialog."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, disable_confirm_discard_changes=False )

    # do the test
    do_test_confirm_discard_changes( "new-publisher" )

# ---------------------------------------------------------------------

def test_publication_lists( webdriver, flask_app, dbconn ):
    """Test showing publications that belong a publisher."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="publishers.json" )

    def check_publications( results, expected ):
        for publ_name,pub_name in expected.items():
            publ_sr = find_search_result( publ_name, results )
            pubs = find_child( ".collapsible", publ_sr )
            if pub_name:
                # check that the publisher appears in the publisher's search result
                assert find_child( ".caption", pubs ).text == "Publications:"
                pubs = find_children( "li", pubs )
                assert len(pubs) == 1
                assert pubs[0].text == pub_name
            else:
                # check that the publisher has no associated publications
                assert pubs is None

    # check that the publishers have no publications associated with them
    results = do_search( SEARCH_ALL_PUBLISHERS )
    publ_name1, publ_name2 = "Avalon Hill", "Multiman Publishing"
    check_publications( results, { publ_name1: None, publ_name2: None } )

    # create a publication that has no parent publisher
    create_publication( { "name": "no parent" } )
    check_publications( results, { publ_name1: None, publ_name2: None } )

    # create a publication that has a parent publisher
    pub_name = "test publication"
    create_publication( { "name": pub_name, "publisher": publ_name1 } )
    check_publications( results, { publ_name1: pub_name, publ_name2: None } )

    # move the publication to another publisher
    pub_sr = find_search_result( pub_name )
    edit_publication( pub_sr, { "publisher": publ_name2 } )
    check_publications( results, { publ_name1: None, publ_name2: pub_name } )

    # change the publication to have no parent publisher
    edit_publication( pub_sr, { "publisher": "(none)" } )
    check_publications( results, { publ_name1: None, publ_name2: None } )

    # move the publication back to a publisher
    edit_publication( pub_sr, { "publisher": publ_name1 } )
    check_publications( results, { publ_name1: pub_name, publ_name2: None } )

    # delete the publication
    select_sr_menu_option( pub_sr, "delete" )
    check_ask_dialog( ( "Delete this publication?", pub_name ), "ok" )
    check_publications( results, { publ_name1: None, publ_name2: None } )

# ---------------------------------------------------------------------

def test_timestamps( webdriver, flask_app, dbconn ):
    """Test setting of timestamps."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create a publisher
    create_publisher( { "name": "Joe Publisher" } )
    results = get_search_results()
    assert len(results) == 1
    publ_sr = results[0]
    publ_id = publ_sr.get_attribute( "testing--publ_id" )

    # check its timestamps
    row = get_publisher_row( dbconn, publ_id, ["time_created","time_updated"] )
    assert row[0]
    assert row[1] is None

    # update the publisher
    edit_publisher( publ_sr, { "name": "Joe Publisher (updated)" } )

    # check its timestamps
    row2 = get_publisher_row( dbconn, publ_id, ["time_created","time_updated"] )
    assert row2[0] == row[0]
    assert row2[1] > row2[0]

# ---------------------------------------------------------------------

def create_publisher( vals, toast_type="info", expected_error=None, dlg=None ):
    """Create a new publisher."""

    # initialize
    set_toast_marker( toast_type )

    # create the new publisher
    if not dlg:
        select_main_menu_option( "new-publisher" )
        dlg = wait_for_elem( 2, "#publisher-form" )
    _update_values( dlg, vals )
    find_child( "button.ok", dlg ).click()

    # check what happened
    if expected_error:
        # we were expecting an error, confirm the error message
        check_error_msg( expected_error )
        return dlg # nb: the dialog is left on-screen
    else:
        # we were expecting the create to work, confirm this
        wait_for( 2,
            lambda: check_toast( toast_type, "created OK", contains=True )
        )
        wait_for_not_elem( 2, "#publisher-form" )
        return None

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def edit_publisher( sr, vals, toast_type="info", expected_error=None ):
    """Edit a publisher's details."""

    # initialize
    if sr:
        select_sr_menu_option( sr, "edit" )
    else:
        pass # nb: we assume that the dialog is already on-screen
    dlg = wait_for_elem( 2, "#publisher-form" )

    # update the specified publisher's details
    _update_values( dlg, vals )
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
        wait_for_not_elem( 2, "#publisher-form" )

def _update_values( dlg, vals ):
    """Update a publishers's values in the form."""
    for key,val in vals.items():
        if key == "image":
            if val:
                change_image( dlg, val )
            else:
                remove_image( dlg )
        else:
            sel = ".row.{} {}".format( key , "textarea" if key == "description" else "input" )
            set_elem_text( find_child( sel, dlg ), val )

# ---------------------------------------------------------------------

def _check_sr( sr, expected ):
    """Check a search result."""

    # check the name and description
    if find_child( ".name", sr ).text != expected[0]:
        return False
    if find_child( ".description", sr ).text != expected[1]:
        return False

    # check the publisher's link
    elem = find_child( "a.open-link", sr )
    if expected[2]:
        assert elem
        if elem.get_attribute( "href" ) != expected[2]:
            return False
    else:
        assert elem is None

    return True
