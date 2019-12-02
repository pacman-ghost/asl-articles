""" Basic tests. """

from asl_articles.tests.utils import init_tests, init_db, do_search, find_child

# ---------------------------------------------------------------------

def test_basic( webdriver, flask_app, dbconn ):
    """Basic tests."""

    # initialize
    init_tests( webdriver, flask_app )
    init_db( dbconn, "basic.json" )

    # make sure the home page loaded correctly
    elem = find_child( "#search-form .caption" )
    assert elem.text == "Search for:"

    # run some test searches
    def do_test( query, expected ):
        results = do_search( query )
        def get_href( r ):
            elem = find_child( ".name a", r )
            return elem.get_attribute( "href" ) if elem else ""
        results = [ (
            find_child( ".name", r ).text,
            find_child( ".description", r ).text,
            get_href( r )
        ) for r in results ]
        assert results == expected
    do_test( "publish", [ ("Multiman Publishing","","http://mmp.com/") ] )
    do_test( "foo", [] )
    do_test( "   ", [
        ( "Avalon Hill", "AH description" , "http://ah.com/" ),
        ( "Le Franc Tireur", "The French guys.", "" ),
        ( "Multiman Publishing", "", "http://mmp.com/" )
    ] )
    do_test( " H ", [
        ( "Avalon Hill", "AH description" , "http://ah.com/" ),
        ( "Multiman Publishing", "", "http://mmp.com/" )
    ] )
