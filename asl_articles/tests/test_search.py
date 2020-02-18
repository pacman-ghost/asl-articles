""" Test search operations. """

from asl_articles.search import _load_search_aliases, _make_fts_query_string
from asl_articles.search import SEARCH_ALL

from asl_articles.tests.test_publishers import create_publisher, edit_publisher
from asl_articles.tests.test_publications import create_publication, edit_publication
from asl_articles.tests.test_articles import create_article, edit_article
from asl_articles.tests.utils import init_tests, select_sr_menu_option, \
    wait_for, wait_for_elem, find_child, find_children, check_ask_dialog, \
    do_search, get_search_results, get_search_result_names, find_search_result, get_search_seqno

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

def test_publisher_search( webdriver, flask_app, dbconn ):
    """Test searching for publishers."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    def click_on_publisher( sr, expected ):
        elem = find_child( ".header .publisher", sr )
        assert elem.text == expected
        seq_no = get_search_seqno()
        elem.click()
        wait_for( 2, lambda: get_search_seqno() != seq_no )
        assert find_child( "#search-form input.query" ).get_attribute( "value" ) == ""
        return get_search_results()

    # find a publication and click on its parent publisher
    results = do_search( "fantastic" )
    assert len(results) == 1
    click_on_publisher( results[0], "View From The Trenches" )
    assert get_search_result_names() == [
        "View From The Trenches", "View From The Trenches (100)"
    ]

# ---------------------------------------------------------------------

def test_publication_search( webdriver, flask_app, dbconn ):
    """Test searching for publications."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    def click_on_publication( sr, expected ):
        classes = sr.get_attribute( "class" ).split()
        if "article" in classes:
            elem = find_child( ".header .publication", sr )
        elif "publisher" in classes:
            elems = find_children( ".content .collapsible li", sr )
            elem = elems[0] # nb: we just use the first one
        else:
            assert "publication" in classes
            elem = find_child( ".header .name", sr )
        assert elem.text == expected
        seq_no = get_search_seqno()
        elem.click()
        wait_for( 2, lambda: get_search_seqno() != seq_no )
        assert find_child( "#search-form input.query" ).get_attribute( "value" ) == ""
        return get_search_results()

    # find a publication and click on it
    results = do_search( "vftt" )
    sr = find_search_result( "View From The Trenches (100)", results )
    click_on_publication( sr, "View From The Trenches (100)" )
    assert get_search_result_names() == [
        "View From The Trenches (100)", "Jagdpanzer 38(t) Hetzer"
    ]

    # find an article and click on its parent publication
    results = do_search( "neutral" )
    assert len(results) == 1
    click_on_publication( results[0], "ASL Journal (5)" )
    assert get_search_result_names() == [
        "ASL Journal (5)", "The Jungle Isn't Neutral", "Hunting DUKWs and Buffalos"
    ]

    # find a publisher and click on one of its publications
    results = do_search( "mmp" )
    assert len(results) == 1
    click_on_publication( results[0], "ASL Journal (4)" )
    assert get_search_result_names() == [
        "ASL Journal (4)", "Hit 'Em High, Or Hit 'Em Low", "'Bolts From Above"
    ]

# ---------------------------------------------------------------------

def test_article_search( webdriver, flask_app, dbconn ):
    """Test searching for articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    def click_on_article( sr, expected ):
        elems = find_children( ".content .collapsible li", sr )
        elem = elems[0] # nb: we just use the first one
        assert elem.text == expected
        seq_no = get_search_seqno()
        elem.click()
        wait_for( 2, lambda: get_search_seqno() != seq_no )
        assert find_child( "#search-form input.query" ).get_attribute( "value" ) == ""
        return get_search_results()

    # find a publication and click on one of its articles
    results = do_search( "vftt" )
    sr = find_search_result( "View From The Trenches (100)", results )
    click_on_article( sr, "Jagdpanzer 38(t) Hetzer" )
    assert get_search_result_names() == [
        "Jagdpanzer 38(t) Hetzer", "View From The Trenches (100)"
    ]

# ---------------------------------------------------------------------

def test_author_search( webdriver, flask_app, dbconn ):
    """Test searching for authors."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    def click_on_author( sr, expected ):
        authors = find_children( ".authors .author", sr )
        assert len(authors) == 1
        assert authors[0].text == expected
        seq_no = get_search_seqno()
        authors[0].click()
        wait_for( 2, lambda: get_search_seqno() != seq_no )
        assert find_child( "#search-form input.query" ).get_attribute( "value" ) == ""
        return get_search_results()

    # find an article and click on the author
    results = do_search( SEARCH_ALL )
    sr = find_search_result( "Jagdpanzer 38(t) Hetzer" )
    results = click_on_author( sr, "Michael Davies" )
    assert get_search_result_names( results ) == [
        "Jagdpanzer 38(t) Hetzer"
    ]

# ---------------------------------------------------------------------

def test_tag_search( webdriver, flask_app, dbconn ):
    """Test searching for tags."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    def click_on_tag( tag ):
        seq_no = get_search_seqno()
        tag.click()
        wait_for( 2, lambda: get_search_seqno() != seq_no )
        assert find_child( "#search-form input.query" ).get_attribute( "value" ) == ""
        return get_search_results()
    def get_tags( sr ):
        return find_children( ".tags .tag", sr )

    # find an article and click on the "#aslj" tag
    results = do_search( "high low" )
    assert len(results) == 1
    tags = get_tags( results[0] )
    assert [ t.text for t in tags ] == [ "#aslj", "#mortars" ]
    results = click_on_tag( tags[0] )
    expected = [
        "ASL Journal (4)", "ASL Journal (5)",
        "'Bolts From Above", "The Jungle Isn't Neutral", "Hunting DUKWs and Buffalos", "Hit 'Em High, Or Hit 'Em Low"
    ]
    assert get_search_result_names( results ) == expected

    # click on another "#aslj" tag
    tags = get_tags( results[0] )
    assert [ t.text for t in tags ] == [ "#aslj" ]
    results = click_on_tag( tags[0] )
    assert get_search_result_names( results ) == expected

    # click on a "#PTO" tag
    sr = find_search_result( "The Jungle Isn't Neutral" )
    tags = get_tags( sr )
    assert [ t.text for t in tags ] == [ "#aslj", "#PTO" ]
    results = click_on_tag( tags[1] )
    assert get_search_result_names( results ) == [ "The Jungle Isn't Neutral" ]

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
