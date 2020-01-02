""" Test article operations. """

import os
import urllib.request
import urllib.error
import json
import base64

from asl_articles.tests.utils import init_tests, do_search, get_result_names, \
    wait_for, wait_for_elem, find_child, find_children, set_elem_text, \
    set_toast_marker, check_toast, send_upload_data, check_ask_dialog, check_error_msg
from asl_articles.tests.react_select import ReactSelect

# ---------------------------------------------------------------------

def test_edit_article( webdriver, flask_app, dbconn ):
    """Test editing articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="articles.json" )

    # edit "What To Do If You Have A Tin Can"
    results = do_search( '"tin can"' )
    assert len(results) == 1
    result = results[0]
    edit_article( result, {
        "title": "  Updated title  ",
        "subtitle": "  Updated subtitle  ",
        "snippet": "  Updated snippet.  ",
        "tags": [ "+abc", "+xyz" ],
        "url": "  http://updated-article.com  ",
    } )

    # check that the search result was updated in the UI
    results = find_children( "#search-results .search-result" )
    result = results[0]
    _check_result( result,
        [ "Updated title", "Updated subtitle", "Updated snippet.", ["abc","xyz"], "http://updated-article.com/" ]
    )

    # try to remove all fields from the article (should fail)
    edit_article( result,
        { "title": "", "subtitle": "", "snippet": "", "tags": ["-abc","-xyz"], "url": "" },
        expected_error = "Please specify the article's title."
    )

    # enter something for the name
    dlg = find_child( "#modal-form" )
    set_elem_text( find_child( ".title input", dlg ), "Tin Cans Rock!" )
    find_child( "button.ok", dlg ).click()

    # check that the search result was updated in the UI
    results = find_children( "#search-results .search-result" )
    result = results[0]
    assert find_child( ".title a", result ) is None
    assert find_child( ".title", result ).text == "Tin Cans Rock!"
    assert find_child( ".snippet", result ).text == ""
    assert find_children( ".tag", result ) == []

    # check that the search result was updated in the database
    results = do_search( '"tin can"' )
    _check_result( results[0], [ "Tin Cans Rock!", None, "", [], None ] )

# ---------------------------------------------------------------------

def test_create_article( webdriver, flask_app, dbconn ):
    """Test creating new articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # try creating a article with no name (should fail)
    create_article( {}, toast_type=None )
    check_error_msg( "Please specify the article's title." )

    # enter a name and other details
    dlg = find_child( "#modal-form" ) # nb: the form is still on-screen
    set_elem_text( find_child( ".title input", dlg ), "New article" )
    set_elem_text( find_child( ".subtitle input", dlg ), "New subtitle" )
    set_elem_text( find_child( ".snippet textarea", dlg ), "New snippet." )
    select = ReactSelect( find_child( ".tags .react-select", dlg ) )
    select.update_multiselect_values( "+111", "+222", "+333" )
    set_elem_text( find_child( ".url input", dlg ), "http://new-snippet.com" )
    set_toast_marker( "info" )
    find_child( "button.ok", dlg ).click()
    wait_for( 2,
        lambda: check_toast( "info", "created OK", contains=True )
    )

    # check that the new article appears in the UI
    def check_new_article( result ):
        _check_result( result, [
            "New article", "New subtitle", "New snippet.", ["111","222","333"], "http://new-snippet.com/"
        ] )
    results = find_children( "#search-results .search-result" )
    check_new_article( results[0] )

    # check that the new article has been saved in the database
    results = do_search( "new" )
    assert len( results ) == 1
    check_new_article( results[0] )

# ---------------------------------------------------------------------

def test_delete_article( webdriver, flask_app, dbconn ):
    """Test deleting articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="articles.json" )

    # start to delete article "Smoke Gets In Your Eyes", but cancel the operation
    results = do_search( "smoke" )
    assert len(results) == 1
    result = results[0]
    find_child( ".delete", result ).click()
    check_ask_dialog( ( "Delete this article?", "Smoke Gets In Your Eyes" ), "cancel" )

    # check that search results are unchanged on-screen
    results2 = find_children( "#search-results .search-result" )
    assert results2 == results

    # check that the search results are unchanged in the database
    results3 = do_search( "smoke" )
    assert results3 == results

    # delete the article "Smoke Gets In Your Eyes"
    result = results3[0]
    find_child( ".delete", result ).click()
    set_toast_marker( "info" )
    check_ask_dialog( ( "Delete this article?", "Smoke Gets In Your Eyes" ), "ok" )
    wait_for( 2,
        lambda: check_toast( "info", "The article was deleted." )
    )

    # check that search result was removed on-screen
    results = find_children( "#search-results .search-result" )
    assert get_result_names( results ) == []

    # check that the search result was deleted from the database
    results = do_search( "smoke" )
    assert get_result_names( results ) == []

# ---------------------------------------------------------------------

def test_images( webdriver, flask_app, dbconn ): #pylint: disable=too-many-statements
    """Test article images."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, max_image_upload_size=2*1024 )

    def check_image( expected ):

        # check the image in the article's search result
        img = find_child( "img.image", article_sr )
        if expected:
            expected_url = flask_app.url_for( "get_image", image_type="article", image_id=article_id )
            image_url = img.get_attribute( "src" ).split( "?" )[0]
            assert image_url == expected_url
        else:
            assert not img

        # check the image in the article's config
        find_child( ".edit", article_sr ).click()
        dlg = wait_for_elem( 2, "#modal-form" )
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
            assert resp == open(expected,"rb").read()
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
    results = find_children( "#search-results .search-result" )
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
    find_child( ".edit", article_sr ).click()
    dlg = wait_for_elem( 2, "#modal-form" )
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
    article_sr = None

    def check_results( expected_parent ):

        # check that the parent publication was updated in the UI
        nonlocal article_sr
        elem = find_child( ".title .publication", article_sr )
        if expected_parent:
            assert elem.text == "({})".format( expected_parent[1] )
        else:
            assert elem is None

        # check that the parent publication was updated in the database
        article_id = article_sr.get_attribute( "testing--article_id" )
        url = flask_app.url_for( "get_article", article_id=article_id )
        article = json.load( urllib.request.urlopen( url ) )
        if expected_parent:
            assert article["pub_id"] == expected_parent[0]
        else:
            assert article["pub_id"] is None

        # check that the parent publication was updated in the UI
        results = do_search( '"My Article"' )
        assert len(results) == 1
        article_sr = results[0]
        elem = find_child( ".title .publication", article_sr )
        if expected_parent:
            assert elem.text == "({})".format( expected_parent[1] )
        else:
            assert elem is None

    # create an article with no parent publication
    create_article( { "title": "My Article" } )
    results = find_children( "#search-results .search-result" )
    assert len(results) == 1
    article_sr = results[0]
    check_results( None )

    # change the article to have a publication
    edit_article( article_sr, { "publication": "ASL Journal" } )
    check_results( (1, "ASL Journal") )

    # change the article back to having no publication
    edit_article( article_sr, { "publication": "(none)" } )
    check_results( None )

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
    results = do_search( "japan" )
    assert len( results ) == 1
    _check_result( results[0], [
        "japan = \u65e5\u672c",
        "s.korea = \ud55c\uad6d",
        "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1",
        [ "\u0e51", "\u0e52", "\u0e53" ],
        "http://xn--3e0b707e.com/"
    ] )

# ---------------------------------------------------------------------

def test_clean_html( webdriver, flask_app, dbconn ):
    """Test cleaning HTML content."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create a article with HTML content
    create_article( {
        "title": "title: <span style='boo!'> <b>bold</b> <xxx>xxx</xxx> <i>italic</i>",
        "subtitle": "<i>italicized subtitle</i>",
        "snippet": "bad stuff here: <script>HCF</script>"
    }, toast_type="warning" )

    # check that the HTML was cleaned
    results = wait_for( 2,
        lambda: find_children( "#search-results .search-result" )
    )
    assert len( results ) == 1
    result = results[0]
    _check_result( result, [ "title: bold xxx italic", "italicized subtitle", "bad stuff here:", [], None ] )
    assert find_child( ".title span" ).get_attribute( "innerHTML" ) \
        == "title: <span> <b>bold</b> xxx <i>italic</i></span>"
    assert find_child( ".subtitle" ).get_attribute( "innerHTML" ) \
        == "<i>italicized subtitle</i>"
    assert check_toast( "warning", "Some values had HTML removed.", contains=True )

    # update the article with new HTML content
    edit_article( result, {
        "title": "<div style='...'>updated</div>"
    }, toast_type="warning" )
    def check_result():
        results = find_children( "#search-results .search-result" )
        assert len( results ) == 1
        result = results[0]
        return find_child( ".title span", result ).text == "updated"
    wait_for( 2, check_result )
    assert check_toast( "warning", "Some values had HTML removed.", contains=True )

# ---------------------------------------------------------------------

def create_article( vals, toast_type="info" ):
    """Create a new article."""
    # initialize
    if toast_type:
        set_toast_marker( toast_type )
    # create the new article
    find_child( "#menu .new-article" ).click()
    dlg = wait_for_elem( 2, "#modal-form" )
    for key,val in vals.items():
        if key in ["authors","scenarios","tags"]:
            select = ReactSelect( find_child( ".{} .react-select".format(key), dlg ) )
            select.update_multiselect_values( *val )
        else:
            sel = ".{} {}".format( key , "textarea" if key == "snippet" else "input" )
            set_elem_text( find_child( sel, dlg ), val )
    find_child( "button.ok", dlg ).click()
    if toast_type:
        # check that the new article was created successfully
        wait_for( 2,
            lambda: check_toast( toast_type, "created OK", contains=True )
        )

def edit_article( result, vals, toast_type="info", expected_error=None ):
    """Edit a article's details."""
    # update the specified article's details
    find_child( ".edit", result ).click()
    dlg = wait_for_elem( 2, "#modal-form" )
    for key,val in vals.items():
        if key == "image":
            if val:
                data = base64.b64encode( open( val, "rb" ).read() )
                data = "{}|{}".format( os.path.split(val)[1], data.decode("ascii") )
                send_upload_data( data,
                    lambda: find_child( ".image img", dlg ).click()
                )
            else:
                find_child( ".remove-image", dlg ).click()
        elif key == "publication":
            select = ReactSelect( find_child( ".publication .react-select", dlg ) )
            select.select_by_name( val )
        elif key in ["authors","scenarios","tags"]:
            select = ReactSelect( find_child( ".{} .react-select".format(key), dlg ) )
            select.update_multiselect_values( *val )
        else:
            sel = ".{} {}".format( key , "textarea" if key == "snippet" else "input" )
            set_elem_text( find_child( sel, dlg ), val )
    set_toast_marker( toast_type )
    find_child( "button.ok", dlg ).click()
    if expected_error:
        # we were expecting an error, confirm the error message
        check_error_msg( expected_error )
    else:
        # we were expecting the update to work, confirm this
        wait_for( 2,
            lambda: check_toast( toast_type, "updated OK", contains=True )
        )

# ---------------------------------------------------------------------

def _check_result( result, expected ):
    """Check a result."""
    # check the title and subtitle
    assert find_child( ".title span", result ).text == expected[0]
    elem = find_child( ".subtitle", result )
    if elem:
        assert elem.text == expected[1]
    else:
        assert expected[1] is None
    # check the snippet
    assert find_child( ".snippet", result ).text == expected[2]
    # check the tags
    tags = [ t.text for t in find_children( ".tag", result ) ]
    assert tags == expected[3]
    # check the article's link
    elem = find_child( ".title a", result )
    if elem:
        assert elem.get_attribute( "href" ) == expected[4]
    else:
        assert expected[4] is None
