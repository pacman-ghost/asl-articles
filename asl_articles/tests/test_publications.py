""" Test publication operations. """

from asl_articles.tests.utils import init_tests, init_db, do_search, get_result_names, \
    wait_for, wait_for_elem, find_child, find_children, set_elem_text, \
    set_toast_marker, check_toast, check_ask_dialog, check_error_msg

# ---------------------------------------------------------------------

def test_edit_publication( webdriver, flask_app, dbconn ):
    """Test editing publications."""

    # initialize
    init_tests( webdriver, flask_app )
    init_db( dbconn, "publications.json" )

    # edit "ASL Journal #2"
    results = do_search( "asl journal" )
    assert len(results) == 2
    result = results[1]
    _edit_publication( result, {
        "name": "  ASL Journal (updated)  ",
        "edition": "  2a  ",
        "description": "  Updated ASLJ description.  ",
        "url": "  http://aslj-updated.com  ",
    } )

    # check that the search result was updated in the UI
    results = find_children( "#search-results .search-result" )
    result = results[1]
    _check_result( result, [ "ASL Journal (updated)", "2a", "Updated ASLJ description.", "http://aslj-updated.com/" ] )

    # try to remove all fields from "ASL Journal #2" (should fail)
    _edit_publication( result,
        { "name": "", "edition": "", "description": "", "url": "" },
        expected_error = "Please specify the publication's name."
    )

    # enter something for the name
    dlg = find_child( "#modal-form" )
    set_elem_text( find_child( ".name input", dlg ), "Updated ASL Journal" )
    find_child( "button.ok", dlg ).click()

    # check that the search result was updated in the UI
    results = find_children( "#search-results .search-result" )
    result = results[1]
    assert find_child( ".name a", result ) is None
    assert find_child( ".name", result ).text == "Updated ASL Journal"
    assert find_child( ".description", result ).text == ""

    # check that the search result was updated in the database
    results = do_search( "ASL Journal" )
    assert get_result_names( results ) == [ "ASL Journal (1)", "Updated ASL Journal" ]

# ---------------------------------------------------------------------

def test_create_publication( webdriver, flask_app, dbconn ):
    """Test creating new publications."""

    # initialize
    init_tests( webdriver, flask_app )
    init_db( dbconn, "basic.json" )

    # try creating a publication with no name (should fail)
    _create_publication( {}, toast_type=None )
    check_error_msg( "Please specify the publication's name." )

    # enter a name and other details
    dlg = find_child( "#modal-form" ) # nb: the form is still on-screen
    set_elem_text( find_child( ".name input", dlg ), "New publication" )
    set_elem_text( find_child( ".edition input", dlg ), "#1" )
    set_elem_text( find_child( ".description textarea", dlg ), "New publication description." )
    set_elem_text( find_child( ".url input", dlg ), "http://new-publication.com" )
    set_toast_marker( "info" )
    find_child( "button.ok", dlg ).click()
    wait_for( 2,
        lambda: check_toast( "info", "created OK", contains=True )
    )

    # check that the new publication appears in the UI
    def check_new_publication( result ):
        _check_result( result, [
            "New publication", "#1", "New publication description.", "http://new-publication.com/"
        ] )
    results = find_children( "#search-results .search-result" )
    check_new_publication( results[0] )

    # check that the new publication has been saved in the database
    results = do_search( "new" )
    assert len( results ) == 1
    check_new_publication( results[0] )

# ---------------------------------------------------------------------

def test_delete_publication( webdriver, flask_app, dbconn ):
    """Test deleting publications."""

    # initialize
    init_tests( webdriver, flask_app )
    init_db( dbconn, "publications.json" )

    # start to delete publication "ASL Journal #1", but cancel the operation
    results = do_search( "ASL Journal" )
    assert len(results) == 2
    result = results[1]
    assert find_child( ".name", result ).text == "ASL Journal (2)"
    find_child( ".delete", result ).click()
    check_ask_dialog( ( "Do you want to delete", "ASL Journal (2)" ), "cancel" )

    # check that search results are unchanged on-screen
    results2 = find_children( "#search-results .search-result" )
    assert results2 == results

    # check that the search results are unchanged in the database
    results3 = do_search( "ASL Journal" )
    assert results3 == results

    # delete the publication "ASL Journal 2"
    result = results3[1]
    assert find_child( ".name", result ).text == "ASL Journal (2)"
    find_child( ".delete", result ).click()
    set_toast_marker( "info" )
    check_ask_dialog( ( "Do you want to delete", "ASL Journal (2)" ), "ok" )
    wait_for( 2,
        lambda: check_toast( "info", "The publication was deleted." )
    )

    # check that search result was removed on-screen
    results = find_children( "#search-results .search-result" )
    assert get_result_names( results ) == [ "ASL Journal (1)" ]

    # check that the search result was deleted from the database
    results = do_search( "ASL Journal" )
    assert get_result_names( results ) == [ "ASL Journal (1)" ]

# ---------------------------------------------------------------------

def test_unicode( webdriver, flask_app, dbconn ):
    """Test Unicode content."""

    # initialize
    init_tests( webdriver, flask_app )
    init_db( dbconn, "publications.json" )

    # create a publication with Unicode content
    _create_publication( {
        "name": "japan = \u65e5\u672c",
        "edition": "\u263a",
        "url": "http://\ud55c\uad6d.com",
        "description": "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1"
    } )

    # check that the new publication is showing the Unicode content correctly
    results = do_search( "japan" )
    assert len( results ) == 1
    _check_result( results[0], [
        "japan = \u65e5\u672c",  "\u263a",
        "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1",
        "http://xn--3e0b707e.com/"
    ] )

# ---------------------------------------------------------------------

def test_clean_html( webdriver, flask_app, dbconn ):
    """Test cleaning HTML content."""

    # initialize
    init_tests( webdriver, flask_app )
    init_db( dbconn, "publications.json" )

    # create a publication with HTML content
    _create_publication( {
        "name": "name: <span style='boo!'> <b>bold</b> <xxx>xxx</xxx> <i>italic</i>",
        "edition": "<i>2</i>",
        "description": "bad stuff here: <script>HCF</script>"
    }, toast_type="warning" )

    # check that the HTML was cleaned
    results = wait_for( 2,
        lambda: find_children( "#search-results .search-result" )
    )
    assert len( results ) == 1
    result = results[0]
    _check_result( result, [ "name: bold xxx italic", "2", "bad stuff here:", None ] )
    assert find_child( ".name span" ).get_attribute( "innerHTML" ) \
        == "name: <span> <b>bold</b> xxx <i>italic</i></span> (<i>2</i>)"
    assert check_toast( "warning", "Some values had HTML removed.", contains=True )

    # update the publication with new HTML content
    _edit_publication( result, {
        "name": "<div style='...'>updated</div>"
    }, toast_type="warning" )
    def check_result():
        results = find_children( "#search-results .search-result" )
        assert len( results ) == 1
        result = results[0]
        return find_child( ".name", result ).text == "updated (2)"
    wait_for( 2, check_result )
    assert check_toast( "warning", "Some values had HTML removed.", contains=True )

# ---------------------------------------------------------------------

def _create_publication( vals, toast_type="info" ):
    """Create a new publication."""
    # initialize
    if toast_type:
        set_toast_marker( toast_type )
    # create the new publication
    find_child( "#menu .new-publication" ).click()
    dlg = wait_for_elem( 2, "#modal-form" )
    for k,v in vals.items():
        sel = ".{} {}".format( k , "textarea" if k == "description" else "input" )
        set_elem_text( find_child( sel, dlg ), v )
    find_child( "button.ok", dlg ).click()
    if toast_type:
        # check that the new publication was created successfully
        wait_for( 2,
            lambda: check_toast( toast_type, "created OK", contains=True )
        )

def _edit_publication( result, vals, toast_type="info", expected_error=None ):
    """Edit a publication's details."""
    # update the specified publication's details
    find_child( ".edit", result ).click()
    dlg = wait_for_elem( 2, "#modal-form" )
    for k,v in vals.items():
        sel = ".{} {}".format( k , "textarea" if k == "description" else "input" )
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
    expected_name = expected[0]
    if expected[1]:
        expected_name += " ({})".format( expected[1] )
    assert find_child( ".name", result ).text == expected_name
    assert find_child( ".description", result ).text == expected[2]
    elem = find_child( ".name a", result )
    if elem:
        assert elem.get_attribute( "href" ) == expected[3]
    else:
        assert expected[3] is None
