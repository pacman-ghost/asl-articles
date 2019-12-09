""" Test publisher operations. """

from asl_articles.tests.utils import init_tests, init_db, do_search, get_result_names, \
    wait_for, wait_for_elem, find_child, find_children, set_elem_text, \
    set_toast_marker, check_toast, check_ask_dialog, check_error_msg

# ---------------------------------------------------------------------

def test_edit_publisher( webdriver, flask_app, dbconn ):
    """Test editing publishers."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, "basic.json" )

    # edit "Avalon Hill"
    results = do_search( "" )
    result = results[0]
    assert find_child( ".name", result ).text == "Avalon Hill"
    _edit_publisher( result, {
        "name": "  Avalon Hill (updated)  ",
        "description": "  Updated AH description.  ",
        "url": "  http://ah-updated.com  "
    } )

    # check that the search result was updated in the UI
    results = find_children( "#search-results .search-result" )
    result = results[0]
    _check_result( result, [ "Avalon Hill (updated)", "Updated AH description.", "http://ah-updated.com/" ] )

    # try to remove all fields from "Avalon Hill" (should fail)
    _edit_publisher( result,
        { "name": "", "description": "", "url": "" },
        expected_error = "Please specify the publisher's name."
    )

    # enter something for the name
    dlg = find_child( "#modal-form" )
    set_elem_text( find_child( ".name input", dlg ), "Updated Avalon Hill" )
    find_child( "button.ok", dlg ).click()

    # check that the search result was updated in the UI
    results = find_children( "#search-results .search-result" )
    result = results[0]
    assert find_child( ".name a", result ) is None
    assert find_child( ".name", result ).text == "Updated Avalon Hill"
    assert find_child( ".description", result ).text == ""

    # check that the search result was updated in the database
    results = do_search( "" )
    assert get_result_names( results ) == [ "Le Franc Tireur", "Multiman Publishing", "Updated Avalon Hill" ]

# ---------------------------------------------------------------------

def test_create_publisher( webdriver, flask_app, dbconn ):
    """Test creating new publishers."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # try creating a publisher with no name (should fail)
    _create_publisher( {}, toast_type=None )
    check_error_msg( "Please specify the publisher's name." )

    # enter a name and other details
    dlg = find_child( "#modal-form" ) # nb: the form is still on-screen
    set_elem_text( find_child( ".name input", dlg ), "New publisher" )
    set_elem_text( find_child( ".url input", dlg ), "http://new-publisher.com" )
    set_elem_text( find_child( ".description textarea", dlg ), "New publisher description." )
    set_toast_marker( "info" )
    find_child( "button.ok", dlg ).click()
    wait_for( 2,
        lambda: check_toast( "info", "created OK", contains=True )
    )

    # check that the new publisher appears in the UI
    def check_new_publisher( result ):
        _check_result( result, [ "New publisher", "New publisher description.", "http://new-publisher.com/" ] )
    results = find_children( "#search-results .search-result" )
    check_new_publisher( results[0] )

    # check that the new publisher has been saved in the database
    results = do_search( "new" )
    assert len( results ) == 1
    check_new_publisher( results[0] )

# ---------------------------------------------------------------------

def test_delete_publisher( webdriver, flask_app, dbconn ):
    """Test deleting publishers."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, "basic.json" )

    # start to delete publisher "Le Franc Tireur", but cancel the operation
    results = do_search( "" )
    result = results[1]
    assert find_child( ".name", result ).text == "Le Franc Tireur"
    find_child( ".delete", result ).click()
    check_ask_dialog( ( "Delete this publisher?", "Le Franc Tireur" ), "cancel" )

    # check that search results are unchanged on-screen
    results2 = find_children( "#search-results .search-result" )
    assert results2 == results

    # check that the search results are unchanged in the database
    results3 = do_search( "" )
    assert results3 == results

    # delete the publisher "Le Franc Tireur"
    result = results3[1]
    assert find_child( ".name", result ).text == "Le Franc Tireur"
    find_child( ".delete", result ).click()
    set_toast_marker( "info" )
    check_ask_dialog( ( "Delete this publisher?", "Le Franc Tireur" ), "ok" )
    wait_for( 2,
        lambda: check_toast( "info", "The publisher was deleted." )
    )

    # check that search result was removed on-screen
    results = find_children( "#search-results .search-result" )
    assert get_result_names( results ) == [ "Avalon Hill", "Multiman Publishing" ]

    # check that the search result was deleted from the database
    results = do_search( "" )
    assert get_result_names( results ) == [ "Avalon Hill", "Multiman Publishing" ]

# ---------------------------------------------------------------------

def test_cascading_deletes( webdriver, flask_app, dbconn ):
    """Test cascading deletes."""

    # initialize
    init_tests( webdriver, flask_app, None )

    def check_results( results, sr_type, expected, expected_deletions ):
        expected = [ "{} {}".format( sr_type, p ) for p in expected ]
        expected = [ e for e in expected if e not in expected_deletions ]
        results = [ find_child( ".name span", r ).text for r in results ]
        results = [ r for r in results if r.startswith( sr_type ) ]
        assert results == expected

    def do_test( publ_name, expected_warning, expected_deletions ):

        # initialize
        init_db( dbconn, "cascading-deletes-1.json" )
        results = do_search( "" )

        # delete the specified publisher
        results = [ r for r in results if find_child( ".name", r ).text == publ_name ]
        assert len( results ) == 1
        find_child( ".delete", results[0] ).click()
        check_ask_dialog( ( "Delete this publisher?", publ_name, expected_warning ), "ok" )

        # check that deleted associated publications/articles were removed from the UI
        results = find_children( "#search-results .search-result" )
        def check_publications():
            check_results( results,
                "publication", [ "2", "3", "4", "5a", "5b", "6a", "6b", "7a", "7b", "8a", "8b" ],
                expected_deletions
            )
        def check_articles():
            check_results( results,
                "article", [ "3", "4a", "4b", "6a", "7a", "7b", "8a.1", "8a.2", "8b.1", "8b.2" ],
                expected_deletions
            )
        check_publications()
        check_articles()

        # check that associated publications/articles were removed from the database
        results = do_search( "" )
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
    _create_publisher( {
        "name": "japan = \u65e5\u672c",
        "url": "http://\ud55c\uad6d.com",
        "description": "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1"
    } )

    # check that the new publisher is showing the Unicode content correctly
    results = do_search( "japan" )
    assert len( results ) == 1
    _check_result( results[0], [
        "japan = \u65e5\u672c",
        "greece = \u0395\u03bb\u03bb\u03ac\u03b4\u03b1",
        "http://xn--3e0b707e.com/"
    ] )

# ---------------------------------------------------------------------

def test_clean_html( webdriver, flask_app, dbconn ):
    """Test cleaning HTML content."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create a publisher with HTML content
    _create_publisher( {
        "name": "name: <span style='boo!'> <b>bold</b> <xxx>xxx</xxx> <i>italic</i>",
        "description": "bad stuff here: <script>HCF</script>"
    }, toast_type="warning" )

    # check that the HTML was cleaned
    results = wait_for( 2,
        lambda: find_children( "#search-results .search-result" )
    )
    assert len( results ) == 1
    result = results[0]
    _check_result( result, [ "name: bold xxx italic", "bad stuff here:", None ] )
    assert find_child( ".name span" ).get_attribute( "innerHTML" ) \
        == "name: <span> <b>bold</b> xxx <i>italic</i></span>"
    assert check_toast( "warning", "Some values had HTML removed.", contains=True )

    # update the publisher with new HTML content
    _edit_publisher( result, {
        "name": "<div style='...'>updated</div>"
    }, toast_type="warning" )
    def check_result():
        results = find_children( "#search-results .search-result" )
        assert len( results ) == 1
        result = results[0]
        return find_child( ".name", result ).text == "updated"
    wait_for( 2, check_result )
    assert check_toast( "warning", "Some values had HTML removed.", contains=True )

# ---------------------------------------------------------------------

def _create_publisher( vals, toast_type="info" ):
    """Create a new publisher."""
    # initialize
    if toast_type:
        set_toast_marker( toast_type )
    # create the new publisher
    find_child( "#menu .new-publisher" ).click()
    dlg = wait_for_elem( 2, "#modal-form" )
    for k,v in vals.items():
        sel = ".{} {}".format( k , "textarea" if k == "description" else "input" )
        set_elem_text( find_child( sel, dlg ), v )
    find_child( "button.ok", dlg ).click()
    if toast_type:
        # check that the new publisher was created successfully
        wait_for( 2,
            lambda: check_toast( toast_type, "created OK", contains=True )
        )

def _edit_publisher( result, vals, toast_type="info", expected_error=None ):
    """Edit a publisher's details."""
    # update the specified publisher's details
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
    assert find_child( ".name", result ).text == expected[0]
    assert find_child( ".description", result ).text == expected[1]
    elem = find_child( ".name a", result )
    if elem:
        assert elem.get_attribute( "href" ) == expected[2]
    else:
        assert expected[2] is None
