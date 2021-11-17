""" Test search operations. """

from asl_articles.search import _load_search_aliases, _make_fts_query_string, _find_aslrb_ruleids
from asl_articles.search import SEARCH_ALL

from asl_articles.tests.test_publishers import create_publisher, edit_publisher
from asl_articles.tests.test_publications import create_publication, edit_publication
from asl_articles.tests.test_articles import create_article, edit_article
from asl_articles.tests.utils import init_tests, select_main_menu_option, select_sr_menu_option, \
    wait_for, wait_for_elem, find_child, find_children, check_ask_dialog, \
    do_search, get_search_results, get_search_result_names, find_search_result

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
    _do_test_search( "#aslj", [
        "ASL Journal (4)", "ASL Journal (5)",
        "Hunting DUKWs and Buffalos", "'Bolts From Above", "Hit 'Em High, Or Hit 'Em Low", "The Jungle Isn't Neutral"
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

    def click_on_publisher( sr, expected_publ, expected_sr ):
        elem = find_child( ".header .publisher", sr )
        assert elem.text == expected_publ
        elem.click()
        wait_for( 2, lambda: get_search_result_names() == expected_sr )

    # find a publication and click on its parent publisher
    results = do_search( "fantastic" )
    assert len(results) == 1
    click_on_publisher( results[0], "View From The Trenches", [
        "View From The Trenches", "View From The Trenches (100)"
    ] )

# ---------------------------------------------------------------------

def test_publication_search( webdriver, flask_app, dbconn ):
    """Test searching for publications."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    def click_on_publication( sr, expected_pub, expected_sr ):
        classes = sr.get_attribute( "class" ).split()
        if "article" in classes:
            elem = find_child( ".header .publication", sr )
        elif "publisher" in classes:
            elems = find_children( ".content .collapsible li", sr )
            elem = elems[0] # nb: we just use the first one
        else:
            assert "publication" in classes
            elem = find_child( ".header .name", sr )
        assert elem.text == expected_pub
        elem.click()
        wait_for( 2, lambda: get_search_result_names() == expected_sr )

    # find a publication and click on it
    results = do_search( "vftt" )
    sr = find_search_result( "View From The Trenches (100)", results )
    click_on_publication( sr, "View From The Trenches (100)", [
        "View From The Trenches (100)", "Jagdpanzer 38(t) Hetzer"
    ] )

    # find an article and click on its parent publication
    results = do_search( "neutral" )
    assert len(results) == 1
    click_on_publication( results[0], "ASL Journal (5)", [
        "ASL Journal (5)", "The Jungle Isn't Neutral", "Hunting DUKWs and Buffalos"
    ] )

    # find a publisher and click on one of its publications
    results = do_search( "mmp" )
    assert len(results) == 1
    click_on_publication( results[0], "ASL Journal (4)", [
        "ASL Journal (4)", "Hit 'Em High, Or Hit 'Em Low", "'Bolts From Above"
    ] )

# ---------------------------------------------------------------------

def test_article_search( webdriver, flask_app, dbconn ):
    """Test searching for articles."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    def click_on_article( sr, expected_pub, expected_sr ):
        elems = find_children( ".content .collapsible li", sr )
        elem = elems[0] # nb: we just use the first one
        assert elem.text == expected_pub
        elem.click()
        wait_for( 2, lambda: get_search_result_names() == expected_sr )
        assert find_child( "#search-form input.query" ).get_attribute( "value" ) == ""

    # find a publication and click on one of its articles
    results = do_search( "vftt" )
    sr = find_search_result( "View From The Trenches (100)", results )
    click_on_article( sr, "Jagdpanzer 38(t) Hetzer", [
        "Jagdpanzer 38(t) Hetzer", "View From The Trenches (100)"
    ] )

# ---------------------------------------------------------------------

def test_author_search( webdriver, flask_app, dbconn ):
    """Test searching for authors."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    def click_on_author( sr, expected_author, expected_sr ):
        authors = find_children( ".authors .author", sr )
        assert len(authors) == 1
        assert authors[0].text == expected_author
        authors[0].click()
        wait_for( 2, lambda: get_search_result_names() == expected_sr )
        return get_search_results()

    # find an article and click on the author
    results = do_search( SEARCH_ALL )
    sr = find_search_result( "Jagdpanzer 38(t) Hetzer", results )
    click_on_author( sr, "Michael Davies", [
        "Jagdpanzer 38(t) Hetzer"
    ] )

# ---------------------------------------------------------------------

def test_tag_search( webdriver, flask_app, dbconn ):
    """Test searching for tags."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    def click_on_tag( tag, expected ):
        tag.click()
        wait_for( 2, lambda: get_search_result_names() == expected )
        return get_search_results()
    def get_tags( sr ):
        return find_children( ".tags .tag", sr )

    # find an article and click on the "#aslj" tag
    results = do_search( "high low" )
    assert len(results) == 1
    tags = get_tags( results[0] )
    assert [ t.text for t in tags ] == [ "#aslj", "#mortars" ]
    expected = [
        "ASL Journal (4)", "ASL Journal (5)",
        "'Bolts From Above", "The Jungle Isn't Neutral", "Hunting DUKWs and Buffalos", "Hit 'Em High, Or Hit 'Em Low"
    ]
    results = click_on_tag( tags[0], expected )

    # click on another "#aslj" tag
    tags = get_tags( results[0] )
    assert [ t.text for t in tags ] == [ "#aslj" ]
    results = click_on_tag( tags[0], expected )

    # click on a "#PTO" tag
    sr = find_search_result( "The Jungle Isn't Neutral", results )
    tags = get_tags( sr )
    assert [ t.text for t in tags ] == [ "#aslj", "#PTO" ]
    click_on_tag( tags[1], [ "The Jungle Isn't Neutral" ] )

# ---------------------------------------------------------------------

def test_special_searches( webdriver, flask_app, dbconn ):
    """Test special searches."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="search.json" )

    # initialize
    def get_url():
        url = webdriver.current_url
        pos = url.find( "?" )
        if pos >= 0:
            url = url[:pos]
        while url.endswith( "/" ):
            url = url[:-1]
        return url
    url_stem = get_url()

    title_stem = "ASL Articles"
    def check_title( expected ):
        if expected:
            return webdriver.title == "{} - {}".format( title_stem, expected )
        else:
            return webdriver.title == title_stem

    def check_results( expected_url, expected_title, expected_sr ):
        wait_for( 2, lambda: check_title( expected_title ) )
        assert get_url() == "{}/{}".format( url_stem, expected_url ) if expected_url else url_stem
        results = get_search_results()
        assert get_search_result_names( results ) == expected_sr
        return results

    # test showing "technique" articles
    select_main_menu_option( "search-technique" )
    check_results( "", "Technique", [ "A technique article" ] )

    # test showing "tip" articles
    select_main_menu_option( "search-tips" )
    check_results( "", "Tips", [ "A tip article" ] )

    # test showing all publishers
    select_main_menu_option( "show-publishers" )
    results = check_results( "", "All publishers", [
        "Multi-Man Publishing", "View From The Trenches"
    ] )

    # test showing a single publication
    pubs = find_children( ".collapsible li", results[1] )
    assert [ p.text for p in pubs ] == [ "View From The Trenches (100)" ]
    pubs[0].click()
    results = check_results( "publication/12", "View From The Trenches (100)", [
        "View From The Trenches (100)", "Jagdpanzer 38(t) Hetzer"
    ] )

    # test showing a single publisher
    publ = find_child( "a.publisher", results[0] )
    assert publ.text == "View From The Trenches"
    publ.click()
    results = check_results( "publisher/2", "View From The Trenches", [
        "View From The Trenches", "View From The Trenches (100)"
    ] )

    # test showing a single article
    articles = find_children( ".collapsible li", results[1] )
    assert [ a.text for a in articles ] == [ "Jagdpanzer 38(t) Hetzer" ]
    articles[0].click()
    results = check_results( "article/520", "Jagdpanzer 38(t) Hetzer" , [
        "Jagdpanzer 38(t) Hetzer", "View From The Trenches (100)"
    ] )

    # test showing an author's articles
    authors = find_children( "a.author", results[0] )
    assert [ a.text for a in authors ] == [ "Michael Davies" ]
    authors[0].click()
    results = check_results( "author/1003", "Michael Davies" , [
        "Jagdpanzer 38(t) Hetzer"
    ] )

    # test searching for a tag
    tags = find_children( "a.tag", results[0] )
    assert [ t.text for t in tags ] == [ "jagdpanzer" ]
    tags[0].click()
    check_results( "tag/jagdpanzer", "jagdpanzer" , [
        "Jagdpanzer 38(t) Hetzer"
    ] )

# ---------------------------------------------------------------------

def test_author_aliases( webdriver, flask_app, dbconn ):
    """Test author aliases."""

    # initialize
    # NOTE: We can't monkeypatch the author aliases table, since we might be talking to
    # a remote Flask server not under our control (e.g. in a Docker container). Instead,
    # we define the aliases we need in a test config file, which is always loaded.
    init_tests( webdriver, flask_app, dbconn, fixtures="author-aliases.json" )

    def do_test( author_names ):

        # test each author in the alias group
        expected = set( "By {}".format(a) for a in author_names )
        for author_name in author_names:

            # find the author's article
            results = do_search( '"{}"'.format( author_name ) )
            assert len(results) == 1

            # click on the author's name
            authors = find_children( ".author", results[0] )
            assert len(authors) == 1
            authors[0].click()

            # check that we found all the articles by the aliased names
            wait_for( 2, lambda: set( get_search_result_names() ) == expected )

    # test author aliases
    do_test( [ "Charles M. Jones", "Chuck Jones", "Charles Martin Jones" ] )
    do_test( [ "Joseph Blow", "Joe Blow" ] )
    do_test( [ "John Doe" ] )

# ---------------------------------------------------------------------

def test_make_fts_query_string():
    """Test generating FTS query strings."""

    def do_test( query, expected ):
        assert _make_fts_query_string( query, {} ) == expected

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
    # NOTE: We used to handle this case, but it's debatable what the right thing to do is :-/
    # do_test(
    #     ' foo " xyz 123 " bar ',
    #     'foo AND "xyz 123" AND bar'
    # )

    # test some quoted phrases that wrap special characters
    do_test( 'Mr. Jones', '"Mr." AND Jones' )
    do_test( '"Mr. Jones"', '"Mr. Jones"' )
    do_test( 'foo "Mr. Jones" bar', 'foo AND "Mr. Jones" AND bar' )

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

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_search_aliases():
    """Test search aliases in query strings."""

    # initialize
    search_aliases = _load_search_aliases(
        [ # one-way aliases
            ( "aa", "bbb ; cccc" ),
            ( "xXx", "x1 X2 ; x3"),
            ( "foo", "{FOO}" ),
            ( " foo  bar ", " {FOO  BAR} " ), # nb: spaces will be squashed and stripped
        ],
        [ # two-way aliases
            ( " joe's   nose  ", " Joes  Nose = Joseph's  Nose " ) # nb: spaces will be squashed and stripped
        ]
    )

    def do_test( query, expected ):
        assert _make_fts_query_string( query, search_aliases ) == expected

    # test one-way aliases
    do_test( "a", "a" )
    do_test( "XaX", "XaX" )
    do_test( "aa", "(aa OR bbb OR cccc)" )
    do_test( 'abc "aa" xyz', "abc AND (aa OR bbb OR cccc) AND xyz" )
    do_test( "XaaX", "XaaX" )
    do_test( "aaa", "aaa" )
    do_test( "XaaaX", "XaaaX" )
    do_test( "bbb", "bbb" )
    do_test( "cccc", "cccc" )

    # test one-way aliases with spaces in the replacement text
    do_test( "XxX", '(xXx OR "x1 X2" OR x3)' )
    do_test( "x1 X2", "x1 AND X2" )

    # test one-way aliases with overlapping text in the keys ("foo" vs. "foo bar")
    do_test( "foo bar", '("foo bar" OR "{FOO BAR}")' )
    do_test( "abc foo bar xyz", 'abc AND ("foo bar" OR "{FOO BAR}") AND xyz' )
    do_test( "Xfoo bar", "Xfoo AND bar" )
    do_test( "foo barX", '(foo OR {FOO}) AND barX' )
    do_test( "Xfoo barX", "Xfoo AND barX" )

    # test two-way aliases
    do_test( "joe's nose", '("joe\'\'s nose" OR "Joes Nose" OR "Joseph\'\'s Nose")' )
    do_test( "abc joe's nose xyz", 'abc AND ("joe\'\'s nose" OR "Joes Nose" OR "Joseph\'\'s Nose") AND xyz' )
    do_test( " JOES  NOSE ", '("joe\'\'s nose" OR "Joes Nose" OR "Joseph\'\'s Nose")' )
    do_test( "Xjoes  nose ", "Xjoes AND nose" )
    do_test( "joes  noseX", "joes AND noseX" )
    do_test( "Xjoes  noseX", "Xjoes AND noseX" )
    do_test( "Joseph's Nose", '("joe\'\'s nose" OR "Joes Nose" OR "Joseph\'\'s Nose")' )

    # check that raw queries still have alias processing done
    do_test( "foo AND bar", "(foo OR {FOO}) AND bar" )

# ---------------------------------------------------------------------

def test_aslrb_links():
    """Test creating links to the ASLRB."""

    def do_test( snippet, expected ):
        matches = _find_aslrb_ruleids( snippet )
        if expected:
            assert len(matches) == len(expected)
            for match,exp in zip(matches,expected):
                startpos, endpos, ruleid, caption = match
                if isinstance( exp, str ):
                    assert exp == ruleid == caption
                    assert exp == snippet[ startpos : endpos ]
                else:
                    assert isinstance( exp, tuple )
                    assert exp[0] == ruleid
                    assert exp[1] == caption
        else:
            assert matches == []

    # test detecting ruleid's
    do_test( "A1.23", ["A1.23"] )
    do_test( " A1.23 ", ["A1.23"] )
    do_test( ".A1.23,", ["A1.23"] )
    do_test( "xA1.23,", None )
    do_test( "A1.23 B.4 C5. D6", ["A1.23","B.4"] )
    do_test( "A1.23 B.4,C5.;D6", ["A1.23","B.4"] )

    # test ruleid ranges
    do_test( "A1.23-", ["A1.23"] )
    do_test( "A1.23-4", [ ("A1.23","A1.23-4") ] )
    do_test( "A1.23-45", [ ("A1.23","A1.23-45") ] )
    do_test( "A1.23-.6", [ ("A1.23","A1.23-.6") ] )
    do_test( "A1.23-.6.7", [ ("A1.23","A1.23-.6") ] )

    # test manually created links
    do_test( "A1.23 Z9.99",
        [ "A1.23", "Z9.99" ]
    )
    do_test( "A1.23 {:D5.6|foo:} Z9.99",
        [ "A1.23", ("D5.6","foo"), "Z9.99" ]
    )
    do_test( "A1.23 {:|foo:} Z9.99",
        [ "A1.23", ("","foo"), "Z9.99" ]
    )
    # NOTE: Because the following manual link has no caption, it won't get detected as a manual link,
    # and so the ruleid is detected as a normal ruleid.
    do_test( "A1.23 {:D5.6|:} Z9.99",
        [ "A1.23", "D5.6", "Z9.99" ]
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
