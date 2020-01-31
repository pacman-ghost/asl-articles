""" Test article operations. """

import os
import urllib.request
import urllib.error
import json
import base64

from asl_articles.search import SEARCH_ALL_ARTICLES
from asl_articles.tests.utils import init_tests, select_main_menu_option, select_sr_menu_option, \
    do_search, get_search_results, find_search_result, get_search_result_names, check_search_result, \
    wait_for, wait_for_elem, wait_for_not_elem, find_child, find_children, \
    set_elem_text, set_toast_marker, check_toast, send_upload_data, check_ask_dialog, check_error_msg, \
    change_image, get_article_row
from asl_articles.tests.react_select import ReactSelect

# ---------------------------------------------------------------------

def test_edit_article( webdriver, flask_app, dbconn ):
    """Test editing articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="articles.json" )

    # edit an article
    results = do_search( SEARCH_ALL_ARTICLES )
    sr = find_search_result( "What To Do If You Have A Tin Can", results )
    edit_article( sr, {
        "title": "  Updated title  ",
        "subtitle": "  Updated subtitle  ",
        "snippet": "  Updated snippet.  ",
        "pageno": "  p123  ",
        "tags": [ "+abc", "+xyz" ],
        "url": "  http://updated-article.com  ",
    } )

    # check that the search result was updated in the UI
    sr = check_search_result( "Updated title", _check_sr, [
        "Updated title", "Updated subtitle", "Updated snippet.", "p123", ["abc","xyz"], "http://updated-article.com/"
    ] )

    # try to remove all fields from the article (should fail)
    edit_article( sr,
        { "title": "", "subtitle": "", "snippet": "", "tags": ["-abc","-xyz"], "url": "" },
        expected_error = "Please specify the article's title."
    )

    # enter something for the name
    dlg = find_child( "#article-form" ) # nb: the form is still on-screen
    set_elem_text( find_child( ".row.title input", dlg ), "Tin Cans Rock!" )
    find_child( "button.ok", dlg ).click()

    # check that the search result was updated in the UI
    expected = [ "Tin Cans Rock!", None, "", "", [], None ]
    check_search_result( expected[0], _check_sr, expected )

    # check that the article was updated in the database
    do_search( SEARCH_ALL_ARTICLES )
    check_search_result( expected[0], _check_sr, expected )

# ---------------------------------------------------------------------

def test_create_article( webdriver, flask_app, dbconn ):
    """Test creating new articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="articles.json" )
    do_search( SEARCH_ALL_ARTICLES )

    # try creating a article with no name (should fail)
    create_article( {}, toast_type=None )
    check_error_msg( "Please specify the article's title." )

    # enter a name and other details
    edit_article( None, { # nb: the form is still on-screen
        "title": "New article",
        "subtitle": "New subtitle",
        "snippet": "New snippet.",
        "pageno": "99",
        "tags": [ "+111", "+222", "+333" ],
        "url": "http://new-snippet.com"
    } )

    # check that the new article appears in the UI
    expected = [ "New article", "New subtitle", "New snippet.", "99", ["111","222","333"], "http://new-snippet.com/" ]
    check_search_result( expected[0], _check_sr, expected )

    # check that the new article has been saved in the database
    do_search( SEARCH_ALL_ARTICLES )
    check_search_result( expected[0], _check_sr, expected )

# ---------------------------------------------------------------------

def test_delete_article( webdriver, flask_app, dbconn ):
    """Test deleting articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="articles.json" )

    # start to delete an article, but cancel the operation
    article_name = "Smoke Gets In Your Eyes"
    results = do_search( SEARCH_ALL_ARTICLES )
    sr = find_search_result( article_name, results )
    select_sr_menu_option( sr, "delete" )
    check_ask_dialog( ( "Delete this article?", article_name ), "cancel" )

    # check that search results are unchanged on-screen
    results2 = get_search_results()
    assert results2 == results

    # check that the search results are unchanged in the database
    results3 = do_search( SEARCH_ALL_ARTICLES )
    assert results3 == results

    # delete the article
    sr = find_search_result( article_name, results3 )
    select_sr_menu_option( sr, "delete" )
    set_toast_marker( "info" )
    check_ask_dialog( ( "Delete this article?", article_name ), "ok" )
    wait_for( 2, lambda: check_toast( "info", "The article was deleted." ) )

    # check that search result was removed on-screen
    wait_for( 2, lambda: article_name not in get_search_result_names() )

    # check that the search result was deleted from the database
    results = do_search( SEARCH_ALL_ARTICLES )
    assert article_name not in get_search_result_names( results )

# ---------------------------------------------------------------------

def test_images( webdriver, flask_app, dbconn ): #pylint: disable=too-many-statements
    """Test article images."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, max_image_upload_size=2*1024 )
    article_sr = article_id = None

    def check_image( expected ):

        # check the image in the article's search result
        def check_sr_image():
            img = find_child( "img.image", article_sr )
            if expected:
                expected_url = flask_app.url_for( "get_image", image_type="article", image_id=article_id )
                image_url = img.get_attribute( "src" ).split( "?" )[0]
                return image_url == expected_url
            else:
                return not img
        wait_for( 2, check_sr_image )

        # check the image in the article's config
        select_sr_menu_option( article_sr, "edit" )
        dlg = wait_for_elem( 2, "#article-form" )
        if expected:
            # make sure there is an image
            img = find_child( ".row.image img.image", dlg )
            image_url = img.get_attribute( "src" )
            assert "/images/article/{}".format( article_id ) in image_url
            # make sure the "remove image" icon is visible
            btn = find_child( ".row.image .remove-image", dlg )
            assert btn.is_displayed()
            # make sure the article's image is correct
            resp = urllib.request.urlopen( image_url ).read()
            assert resp == open( expected, "rb" ).read()
        else:
            # make sure there is no image
            img = find_child( ".row.image img.image", dlg )
            assert img.get_attribute( "src" ).endswith( "/images/placeholder.png" )
            # make sure the "remove image" icon is hidden
            btn = find_child( ".row.image .remove-image", dlg )
            assert not btn.is_displayed()
            # make sure the article's image is not available
            url = flask_app.url_for( "get_image", image_type="article", image_id=article_id )
            try:
                resp = urllib.request.urlopen( url )
                assert False, "Should never get here!"
            except urllib.error.HTTPError as ex:
                assert ex.code == 404
        find_child( ".cancel", dlg ).click()

    # create an article with no image
    create_article( { "title": "Test Article" } )
    results = get_search_results()
    assert len(results) == 1
    article_sr = results[0]
    article_id = article_sr.get_attribute( "testing--article_id" )
    check_image( None )

    # add an image to the article
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/1.gif" )
    edit_article( article_sr, { "image": fname } )
    check_image( fname )

    # change the article's image
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/2.gif" )
    edit_article( article_sr, { "image": fname } )
    check_image( fname )

    # remove the article's image
    edit_article( article_sr, { "image": None } )
    check_image( None )

    # try to upload an image that's too large
    select_sr_menu_option( article_sr, "edit" )
    dlg = wait_for_elem( 2, "#article-form" )
    data = base64.b64encode( 5000 * b" " )
    data = "{}|{}".format( "too-big.png", data.decode("ascii") )
    send_upload_data( data,
        lambda: find_child( ".row.image img.image", dlg ).click()
    )
    check_error_msg( "The file must be no more than 2 KB in size." )

# ---------------------------------------------------------------------

def test_parent_publisher( webdriver, flask_app, dbconn ):
    """Test setting an article's parent publication."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="parents.json" )

    def check_result( sr, expected_parent ): #pylint: disable=too-many-return-statements

        # check that the parent publication was updated in the UI
        elem = find_child( ".header .publication", sr )
        if expected_parent:
            if elem.text != "{}".format( expected_parent[1] ):
                return None
        else:
            if elem is not None:
                return None

        # check that the parent publication was updated in the database
        article_id = sr.get_attribute( "testing--article_id" )
        url = flask_app.url_for( "get_article", article_id=article_id )
        article = json.load( urllib.request.urlopen( url ) )
        if expected_parent:
            if article["pub_id"] != expected_parent[0]:
                return None
        else:
            if article["pub_id"] is not None:
                return None

        # check that the parent publication was updated in the UI
        results = do_search( '"My Article"' )
        assert len(results) == 1
        sr = results[0]
        elem = find_child( ".header .publication", sr )
        if expected_parent:
            if elem.text != "{}".format( expected_parent[1] ):
                return None
        else:
            if elem is not None:
                return None

        return sr

    # create an article with no parent publication
    create_article( { "title": "My Article" } )
    results = get_search_results()
    assert len(results) == 1
    sr = wait_for( 2, lambda: check_result( results[0], None ) )

    # change the article to have a publication
    edit_article( sr, { "publication": "ASL Journal" } )
    sr = wait_for( 2, lambda: check_result( sr, (1, "ASL Journal") ) )

    # change the article back to having no publication
    edit_article( sr, { "publication": "(none)" } )
    sr = wait_for( 2, lambda: check_result( sr, None ) )

# ---------------------------------------------------------------------

def test_unicode( webdriver, flask_app, dbconn ):
    """Test Unicode content."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create a article with Unicode content
    create_article( {
        "title": "japan = \u65e5\u672c",
        "subtitle": "s.korea = \ud55c\uad6d",
        "snippet": "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1",
        "tags": [ "+\u0e51", "+\u0e52", "+\u0e53" ],
        "url": "http://\ud55c\uad6d.com"
    } )

    # check that the new article is showing the Unicode content correctly
    results = do_search( SEARCH_ALL_ARTICLES )
    assert len(results) == 1
    check_search_result( results[0], _check_sr, [
        "japan = \u65e5\u672c",
        "s.korea = \ud55c\uad6d",
        "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1",
        "",
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

    # create a article with HTML content
    create_article( {
        "title": "title: <span style='boo!'> <b>bold</b> <xxx>xxx</xxx> <i>italic</i> {}".format( replace[0] ),
        "subtitle": "<i>italicized subtitle</i> {}".format( replace[0] ),
        "snippet": "bad stuff here: <script>HCF</script> {}".format( replace[0] )
    }, toast_type="warning" )

    # check that the HTML was cleaned
    sr = check_search_result( None, _check_sr, [
        "title: bold xxx italic {}".format( replace[1] ),
        "italicized subtitle {}".format( replace[1] ),
        "bad stuff here: {}".format( replace[1] ),
        "", [], None
    ] )
    assert find_child( ".title", sr ).get_attribute( "innerHTML" ) \
        == "title: <span> <b>bold</b> xxx <i>italic</i> {}</span>".format( replace[1] )
    assert find_child( ".subtitle", sr ).get_attribute( "innerHTML" ) \
        == "<i>italicized subtitle</i> {}".format( replace[1] )
    assert check_toast( "warning", "Some values had HTML cleaned up.", contains=True )

    # update the article with new HTML content
    edit_article( sr, {
        "title": "<div style='...'>updated</div>"
    }, toast_type="warning" )
    wait_for( 2, lambda: get_search_result_names() == ["updated"] )
    assert check_toast( "warning", "Some values had HTML cleaned up.", contains=True )

# ---------------------------------------------------------------------

def test_timestamps( webdriver, flask_app, dbconn ):
    """Test setting of timestamps."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create an article
    create_article( { "title": "My Article" } )
    results = get_search_results()
    assert len(results) == 1
    article_sr = results[0]
    article_id = article_sr.get_attribute( "testing--article_id" )

    # check its timestamps
    row = get_article_row( dbconn, article_id, ["time_created","time_updated"] )
    assert row[0]
    assert row[1] is None

    # update the article
    edit_article( article_sr, { "title": "My Article (updated)" } )

    # check its timestamps
    row2 = get_article_row( dbconn, article_id, ["time_created","time_updated"] )
    assert row2[0] == row[0]
    assert row2[1] > row2[0]

# ---------------------------------------------------------------------

def create_article( vals, toast_type="info" ):
    """Create a new article."""

    # initialize
    if toast_type:
        set_toast_marker( toast_type )

    # create the new article
    select_main_menu_option( "new-article" )
    dlg = wait_for_elem( 2, "#article-form" )
    _update_values( dlg, vals )
    find_child( "button.ok", dlg ).click()

    if toast_type:
        # check that the new article was created successfully
        wait_for( 2,
            lambda: check_toast( toast_type, "created OK", contains=True )
        )
        wait_for_not_elem( 2, "#article-form" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def edit_article( sr, vals, toast_type="info", expected_error=None ): #pylint: disable=too-many-branches
    """Edit a article's details."""

    # initialize
    if sr:
        select_sr_menu_option( sr, "edit" )
    else:
        pass # nb: we assume that the dialog is already on-screen
    dlg = wait_for_elem( 2, "#article-form" )

    # update the specified article's details
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
        wait_for_not_elem( 2, "#article-form" )

def _update_values( dlg, vals ):
    """Update an article's values in the form."""
    for key,val in vals.items():
        if key == "image":
            if val:
                data = base64.b64encode( open( val, "rb" ).read() )
                data = "{}|{}".format( os.path.split(val)[1], data.decode("ascii") )
                change_image( find_child( ".row.image img.image", dlg ), data )
            else:
                find_child( ".row.image .remove-image", dlg ).click()
        elif key == "publication":
            select = ReactSelect( find_child( ".row.publication .react-select", dlg ) )
            select.select_by_name( val )
        elif key in ["authors","scenarios","tags"]:
            select = ReactSelect( find_child( ".row.{} .react-select".format(key), dlg ) )
            select.update_multiselect_values( *val )
        else:
            if key == "snippet":
                sel = ".row.snippet textarea"
            elif key == "pageno":
                sel = "input.pageno"
            else:
                sel = ".row.{} input".format( key )
            set_elem_text( find_child( sel, dlg ), val )

# ---------------------------------------------------------------------

def _check_sr( sr, expected ): #pylint: disable=too-many-return-statements
    """Check a search result."""

    # check the title and subtitle
    names = get_search_result_names( [sr] )
    if names[0] != expected[0]:
        return False
    elem = find_child( ".subtitle", sr )
    if expected[1]:
        if not elem or elem.text != expected[1]:
            return False
    else:
        if elem is not None:
            return False

    # check the snippet
    if find_child( ".snippet", sr ).text != expected[2]:
        return False

    # check the tags
    tags = [ t.text for t in find_children( ".tag", sr ) ]
    if tags != expected[4]:
        return False

    # check the article's link
    elem = find_child( "a.open-link", sr )
    if expected[5]:
        assert elem
        if elem.get_attribute( "href" ) != expected[5]:
            return False
    else:
        assert elem is None

    return True
