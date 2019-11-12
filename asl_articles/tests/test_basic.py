""" Basic tests. """

import json

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
        results = [ json.loads(r.text) for r in results ]
        assert set( r["publ_name"] for r in results ) == set( expected )
    do_test( "publish", ["Multiman Publishing"] )
    do_test( "foo", [] )
    do_test( "   ", [ "Avalon Hill", "Multiman Publishing", "Le Franc Tireur" ] )
    do_test( " H ", [ "Avalon Hill", "Multiman Publishing" ] )
