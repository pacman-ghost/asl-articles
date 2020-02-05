""" Test search operations. """

from asl_articles.search import _load_search_aliases, _make_fts_query_string

from asl_articles.tests.test_publishers import create_publisher, edit_publisher
from asl_articles.tests.test_publications import create_publication, edit_publication
from asl_articles.tests.test_articles import create_article, edit_article
from asl_articles.tests.utils import init_tests, select_sr_menu_option, \
    wait_for_elem, find_child, find_children, check_ask_dialog, \
    do_search, get_search_result_names, find_search_result

# ---------------------------------------------------------------------

def test_search_publishers( webdriver, flask_app, dbconn ):
    """Test searching publishers."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # test searching publisher names/descriptions
    _do_test_searches( ["hill","original"], [] )
    create_publisher( {
        "name": "Avalon Hill", "description": "The original ASL vendor."
    } )
    _do_test_searches( ["hill","original"], ["Avalon Hill"] )

    # edit the publisher
    sr = find_search_result( "Avalon Hill" )
    edit_publisher( sr, {
        "name": "Avalon Mountain", "description": "The first ASL vendor."
    } )
    _do_test_searches( ["hill","original"], [] )
    _do_test_searches( ["mountain","first"], ["Avalon Mountain"] )

    # delete the publisher
    sr = find_search_result( "Avalon Mountain" )
    select_sr_menu_option( sr, "delete" )
    check_ask_dialog( "Delete this publisher?", "ok" )
    _do_test_searches( ["hill","original","mountain","first"], [] )

# ---------------------------------------------------------------------

def test_search_publications( webdriver, flask_app, dbconn ):
    """Test searching publications."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # test searching publication names/descriptions
    _do_test_searches( ["journal","good"], [] )
    create_publication( {
        "name": "ASL Journal", "description": "A pretty good magazine."
    } )
    _do_test_searches( ["journal","good"], ["ASL Journal"] )

    # edit the publication
    sr = find_search_result( "ASL Journal" )
    edit_publication( sr, {
        "name": "ASL Magazine", "description": "Not a bad magazine."
    } )
    _do_test_searches( ["journal","good"], [] )
    _do_test_searches( ["magazine","bad"], ["ASL Magazine"] )

    # delete the publication
    sr = find_search_result( "ASL Magazine" )
    select_sr_menu_option( sr, "delete" )
    check_ask_dialog( "Delete this publication?", "ok" )
    _do_test_searches( ["journal","good","magazine","bad"], [] )

# ---------------------------------------------------------------------

def test_search_articles( webdriver, flask_app, dbconn ):
    """Test searching articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # test searching article titles/subtitles/snippets
    _do_test_searches( ["low","some","game"], [] )
    create_article( {
         "title": "Hit 'Em High, Or Hit 'Em Low",
         "subtitle": "Some things about light mortars you might like to know",
         "snippet": "Light mortars in ASL can be game winners."
    } )
    _do_test_searches( ["low","some","game"], ["Hit 'Em High, Or Hit 'Em Low"] )

    # edit the article
    sr = find_search_result( "Hit 'Em High, Or Hit 'Em Low" )
    edit_article( sr, {
        "title": "Hit 'Em Hard",
        "subtitle": "Where it hurts!",
        "snippet": "Always the best way to do things."
    } )
    _do_test_searches( ["low","some","game"], [] )
    _do_test_searches( ["hard","hurt","best"], ["Hit 'Em Hard"] )

    # delete the article
    sr = find_search_result( "Hit 'Em Hard" )
    select_sr_menu_option( sr, "delete" )
    check_ask_dialog( "Delete this article?", "ok" )
    _do_test_searches( ["hard","hurt","best"], [] )

# ---------------------------------------------------------------------

def test_search_authors( webdriver, flask_app, dbconn ):
    """Test searching for authors."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    # search for some authors
    _do_test_search( "pitcavage", ["The Jungle Isn't Neutral"] )
    _do_test_search( "davie", ["Jagdpanzer 38(t) Hetzer"] )
    _do_test_search( "pit* dav*", [] ) # nb: implied AND
    _do_test_search( "pit* OR dav*", ["The Jungle Isn't Neutral","Jagdpanzer 38(t) Hetzer"] )

# ---------------------------------------------------------------------

def test_search_scenarios( webdriver, flask_app, dbconn ):
    """Test searching for scenarios."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    # search for some scenarios
    _do_test_search( "foul", ["Hunting DUKWs and Buffalos"] )
    _do_test_search( "hs17", ["Hunting DUKWs and Buffalos"] )

# ---------------------------------------------------------------------

def test_search_tags( webdriver, flask_app, dbconn ):
    """Test searching for tags."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    # search for some publication tags
    _do_test_search( "#vftt", ["View From The Trenches (100)"] )

    # search for some article tags
    _do_test_search( "pto", ["The Jungle Isn't Neutral"] )
    _do_test_search( "#aslj", [
        "ASL Journal (4)", "ASL Journal (5)",
        "'Bolts From Above", "The Jungle Isn't Neutral", "Hunting DUKWs and Buffalos", "Hit 'Em High, Or Hit 'Em Low"
    ] )

# ---------------------------------------------------------------------

def test_empty_search( webdriver, flask_app, dbconn ):
    """Test handling of an empty search string."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # search for an empty string
    form = find_child( "#search-form" )
    find_child( ".query", form ).send_keys( "   " )
    find_child( "button[type='submit']", form ).click()
    dlg = wait_for_elem( 2, "#ask" )
    assert find_child( ".MuiDialogContent-root", dlg ).text == "Please enter something to search for."

# ---------------------------------------------------------------------

def test_multiple_search_results( webdriver, flask_app, dbconn ):
    """Test more complicated search queries."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    # do a search
    _do_test_search( "#asl", [
        "View From The Trenches",
        "ASL Journal (4)", "ASL Journal (5)",
        "Hunting DUKWs and Buffalos", "'Bolts From Above", "Hit 'Em High, Or Hit 'Em Low"
    ] )

    # do some searches
    _do_test_search( "infantry", [
        "'Bolts From Above", "Jagdpanzer 38(t) Hetzer"
    ] )
    _do_test_search( "infantry OR mortar", [
        "'Bolts From Above", "Jagdpanzer 38(t) Hetzer",
        "Hit 'Em High, Or Hit 'Em Low"
    ] )
    _do_test_search( "infantry AND mortar", [] )

# ---------------------------------------------------------------------

def test_highlighting( webdriver, flask_app, dbconn ):
    """Test highlighting search matches."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json", no_sr_hilite=0 )

    def find_highlighted( elems ):
        results = []
        for e in elems if isinstance(elems,list) else [elems]:
            results.extend( c.text for c in find_children( ".hilite", e ) )
        return results

    # test highlighting in publisher search results
    results = _do_test_search( "view britain", ["View From The Trenches"] )
    sr = results[0]
    assert find_highlighted( find_child( ".name", sr ) ) == [ "View" ]
    assert find_highlighted( find_child( ".description", sr ) ) == [ "Britain" ]

    def check_publication_highlights( query, expected, name, description, tags ):
        results = _do_test_search( query, [expected] )
        assert len(results) == 1
        sr = results[0]
        assert find_highlighted( find_child( ".name", sr ) ) == name
        assert find_highlighted( find_child( ".description", sr ) ) == description
        assert find_highlighted( find_children( ".tag", sr ) ) == tags

    # test highlighting in publication search results
    check_publication_highlights( "view fantastic",
        "View From The Trenches (100)",
        ["View"], ["Fantastic"], []
    )
    check_publication_highlights( "#vftt",
        "View From The Trenches (100)",
        [], [], ["vftt"]
    )

    def check_article_highlights( query, expected, title, subtitle, snippet, authors, scenarios, tags ):
        results = _do_test_search( query, [expected] )
        assert len(results) == 1
        sr = results[0]
        assert find_highlighted( find_child( ".title", sr ) ) == title
        assert find_highlighted( find_child( ".subtitle", sr ) ) == subtitle
        assert find_highlighted( find_child( ".snippet", sr ) ) == snippet
        assert find_highlighted( find_children( ".author", sr ) ) == authors
        assert find_highlighted( find_children( ".scenario", sr ) ) == scenarios
        assert find_highlighted( find_children( ".tag", sr ) ) == tags

    # test highlighting in article search results
    check_article_highlights( "hit light mortar",
        "Hit 'Em High, Or Hit 'Em Low",
        ["Hit","Hit"], ["light","mortars"], ["Light","mortars"], [], [], ["mortars"]
    )

    # repeat the article search using a quoted phrase
    check_article_highlights( '"light mortar"',
        "Hit 'Em High, Or Hit 'Em Low",
        [], ["light mortars"], ["Light mortars"], [], [], []
    )

    # test highlighting in article authors
    check_article_highlights( "pitcav*",
        "The Jungle Isn't Neutral",
        [], [], [], ["Pitcavage"], [], []
    )

    # test highlighting in article scenario names
    check_article_highlights( "foul",
        "Hunting DUKWs and Buffalos",
        [], ["Foul"], [], [], ["Foul"], []
    )

    # test highlighting in article scenario ID's
    check_article_highlights( "hs17",
        "Hunting DUKWs and Buffalos",
        [], ["HS17"], [], [], ["HS17"], []
    )

    # test highlighting in article tags
    check_article_highlights( "pto",
        "The Jungle Isn't Neutral",
        [], ["PTO"], [], [], [], ["PTO"]
    )

# ---------------------------------------------------------------------

def test_make_fts_query_string():
    """Test generating FTS query strings."""

    # initialize
    search_aliases = _load_search_aliases( [
        ( "mmp", "Multi-Man Publishing ; Multiman Publishing" )
    ] )

    def do_test( query, expected ):
        assert _make_fts_query_string( query, search_aliases ) == expected

    # test some query strings
    do_test( "", "" )
    do_test( "hello", "hello" )
    do_test( "  hello,  world!  ", "hello, AND world!" )
    do_test(
        "foo 1+2 A-T K# bar",
        'foo AND "1+2" AND "A-T" AND "K#" AND bar'
    )
    do_test(
        "a'b a''b",
        "\"a''b\" AND \"a''''b\""
    )
    do_test(
        'foo "set dc" bar',
        'foo AND "set dc" AND bar'
    )

    # test some quoted phrases
    do_test( '""', '' )
    do_test( ' " " ', '' )
    do_test(
        '"hello world"',
        '"hello world"'
    )
    do_test(
        '  foo  "hello  world"  bar  ',
        'foo AND "hello world" AND bar'
    )
    do_test(
        ' foo " xyz " bar ',
        'foo AND xyz AND bar'
    )
    do_test(
        ' foo " xyz 123 " bar ',
        'foo AND "xyz 123" AND bar'
    )

    # test some incorrectly quoted phrases
    do_test( '"', '' )
    do_test( ' " " " ', '' )
    do_test( ' a "b c d e', 'a AND "b c d e"' )
    do_test( ' a b" c d e ', 'a AND b AND c AND d AND e' )

    # test pass-through
    do_test( "AND", "AND" )
    do_test( "OR", "OR" )
    do_test( "NOT", "NOT" )
    do_test( "foo OR bar", "foo OR bar" )
    do_test( "(a OR b)", "(a OR b)" )

    # test search aliases
    do_test( "MMP", '("multi-man publishing" OR "multiman publishing" OR mmp)' )
    do_test( "Xmmp", "Xmmp" )
    do_test( "mmpX", "mmpX" )
    do_test( "multi-man publishing", '"multi-man" AND publishing' )
    do_test( 'abc "multi-man publishing" xyz',
        'abc AND ("multi-man publishing" OR "multiman publishing" OR mmp) AND xyz'
    )

# ---------------------------------------------------------------------

def _do_test_search( query, expected ):
    """Run a search and check the results."""
    results = do_search( query )
    assert set( get_search_result_names( results ) ) == set( expected )
    return results

def _do_test_searches( queries, expected ):
    """Run searches and check the results."""
    for query in queries:
        _do_test_search( query, expected )
