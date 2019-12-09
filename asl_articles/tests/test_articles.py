""" Test article operations. """

import urllib.request
import json

from asl_articles.tests.utils import init_tests, do_search, get_result_names, \
    wait_for, wait_for_elem, find_child, find_children, set_elem_text, \
    set_toast_marker, check_toast, check_ask_dialog, check_error_msg
from asl_articles.tests.utils import ReactSelect

# ---------------------------------------------------------------------

def test_edit_article( webdriver, flask_app, dbconn ):
    """Test editing articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, "articles.json" )

    # edit "What To Do If You Have A Tin Can"
    results = do_search( "tin can" )
    assert len(results) == 1
    result = results[0]
    _edit_article( result, {
        "title": "  Updated title  ",
        "subtitle": "  Updated subtitle  ",
        "snippet": "  Updated snippet.  ",
        "url": "  http://updated-article.com  ",
    } )

    # check that the search result was updated in the UI
    results = find_children( "#search-results .search-result" )
    result = results[0]
    _check_result( result, [ "Updated title", "Updated subtitle", "Updated snippet.", "http://updated-article.com/" ] )

    # try to remove all fields from the article (should fail)
    _edit_article( result,
        { "title": "", "subtitle": "", "snippet": "", "url": "" },
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

    # check that the search result was updated in the database
    results = do_search( "tin can" )
    _check_result( results[0], [ "Tin Cans Rock!", None, "", None ] )

# ---------------------------------------------------------------------

def test_create_article( webdriver, flask_app, dbconn ):
    """Test creating new articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # try creating a article with no name (should fail)
    _create_article( {}, toast_type=None )
    check_error_msg( "Please specify the article's title." )

    # enter a name and other details
    dlg = find_child( "#modal-form" ) # nb: the form is still on-screen
    set_elem_text( find_child( ".title input", dlg ), "New article" )
    set_elem_text( find_child( ".subtitle input", dlg ), "New subtitle" )
    set_elem_text( find_child( ".snippet textarea", dlg ), "New snippet." )
    set_elem_text( find_child( ".url input", dlg ), "http://new-snippet.com" )
    set_toast_marker( "info" )
    find_child( "button.ok", dlg ).click()
    wait_for( 2,
        lambda: check_toast( "info", "created OK", contains=True )
    )

    # check that the new article appears in the UI
    def check_new_article( result ):
        _check_result( result, [
            "New article", "New subtitle", "New snippet.", "http://new-snippet.com/"
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
    init_tests( webdriver, flask_app, dbconn, "articles.json" )

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

def test_parent_publisher( webdriver, flask_app, dbconn ):
    """Test setting an article's parent publication."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, "parents.json" )
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
        results = do_search( "My Article" )
        assert len(results) == 1
        article_sr = results[0]
        elem = find_child( ".title .publication", article_sr )
        if expected_parent:
            assert elem.text == "({})".format( expected_parent[1] )
        else:
            assert elem is None

    # create an article with no parent publication
    _create_article( { "title": "My Article" } )
    results = find_children( "#search-results .search-result" )
    assert len(results) == 1
    article_sr = results[0]
    check_results( None )

    # change the article to have a publication
    _edit_article( article_sr, { "publication": "ASL Journal" } )
    check_results( (1, "ASL Journal") )

    # change the article back to having no publication
    _edit_article( article_sr, { "publication": "(none)" } )
    check_results( None )

# ---------------------------------------------------------------------

def test_unicode( webdriver, flask_app, dbconn ):
    """Test Unicode content."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create a article with Unicode content
    _create_article( {
        "title": "japan = \u65e5\u672c",
        "subtitle": "s.korea = \ud55c\uad6d",
        "snippet": "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1",
        "url": "http://\ud55c\uad6d.com"
    } )

    # check that the new article is showing the Unicode content correctly
    results = do_search( "japan" )
    assert len( results ) == 1
    _check_result( results[0], [
        "japan = \u65e5\u672c",
        "s.korea = \ud55c\uad6d",
        "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1",
        "http://xn--3e0b707e.com/"
    ] )

# ---------------------------------------------------------------------

def test_clean_html( webdriver, flask_app, dbconn ):
    """Test cleaning HTML content."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create a article with HTML content
    _create_article( {
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
    _check_result( result, [ "title: bold xxx italic", "italicized subtitle", "bad stuff here:", None ] )
    assert find_child( ".title span" ).get_attribute( "innerHTML" ) \
        == "title: <span> <b>bold</b> xxx <i>italic</i></span>"
    assert find_child( ".subtitle" ).get_attribute( "innerHTML" ) \
        == "<i>italicized subtitle</i>"
    assert check_toast( "warning", "Some values had HTML removed.", contains=True )

    # update the article with new HTML content
    _edit_article( result, {
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

def _create_article( vals, toast_type="info" ):
    """Create a new article."""
    # initialize
    if toast_type:
        set_toast_marker( toast_type )
    # create the new article
    find_child( "#menu .new-article" ).click()
    dlg = wait_for_elem( 2, "#modal-form" )
    for k,v in vals.items():
        sel = ".{} {}".format( k , "textarea" if k == "snippet" else "input" )
        set_elem_text( find_child( sel, dlg ), v )
    find_child( "button.ok", dlg ).click()
    if toast_type:
        # check that the new article was created successfully
        wait_for( 2,
            lambda: check_toast( toast_type, "created OK", contains=True )
        )

def _edit_article( result, vals, toast_type="info", expected_error=None ):
    """Edit a article's details."""
    # update the specified article's details
    find_child( ".edit", result ).click()
    dlg = wait_for_elem( 2, "#modal-form" )
    for k,v in vals.items():
        if k == "publication":
            select = ReactSelect( find_child( ".publication .react-select", dlg ) )
            select.select_by_name( v )
        else:
            sel = ".{} {}".format( k , "textarea" if k == "snippet" else "input" )
            set_elem_text( find_child( sel, dlg ), v )
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
    assert find_child( ".title span", result ).text == expected[0]
    elem = find_child( ".subtitle", result )
    if elem:
        assert elem.text == expected[1]
    else:
        assert expected[1] is None
    assert find_child( ".snippet", result ).text == expected[2]
    elem = find_child( ".title a", result )
    if elem:
        assert elem.get_attribute( "href" ) == expected[3]
    else:
        assert expected[3] is None
