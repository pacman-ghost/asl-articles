""" Handle search requests. """

import os
import sqlite3
import configparser
import itertools
import random
import tempfile
import re
import logging

from flask import request, jsonify

import asl_articles
from asl_articles import app, db
from asl_articles.models import Publisher, Publication, Article, Author, Scenario, ArticleAuthor, ArticleScenario, \
    get_model_from_table_name
from asl_articles.publishers import get_publisher_vals
from asl_articles.publications import get_publication_vals, get_publication_sort_key
from asl_articles.articles import get_article_vals, get_article_sort_key
from asl_articles.utils import decode_tags, to_bool

_search_index_path = None
_search_aliases = {}
_search_weights = {}
_logger = logging.getLogger( "search" )

_SQLITE_FTS_SPECIAL_CHARS = "+-#':/.@$"

# NOTE: The column order defined here is important, since we have to access row results by column index.
_SEARCHABLE_COL_NAMES = [ "name", "name2", "description", "authors", "scenarios", "tags" ]

_get_publisher_vals = lambda p: get_publisher_vals( p, True )
_get_publication_vals = lambda p: get_publication_vals( p, True, True )
_get_article_vals = lambda a: get_article_vals( a, True )

_PASSTHROUGH_REGEXES = set( [
    re.compile( r"\bAND\b" ),
    re.compile( r"\bOR\b" ),
    re.compile( r"\bNOT\b" ),
    re.compile( r"\((?![Rr]\))" ),
] )

# NOTE: The following are special search terms used by the test suite.
SEARCH_ALL = "<!all!>"
SEARCH_ALL_PUBLISHERS = "<!publishers!>"
SEARCH_ALL_PUBLICATIONS = "<!publications!>"
SEARCH_ALL_ARTICLES = "<!articles!>"

BEGIN_HILITE = '<span class="hilite">'
END_HILITE = "</span>"

# ---------------------------------------------------------------------

class SearchDbConn:
    """Context manager to handle SQLite transactions."""
    def __init__( self ):
        self.conn = sqlite3.connect( _search_index_path )
    def __enter__( self ):
        return self
    def __exit__( self, exc_type, exc_value, traceback ):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()

# ---------------------------------------------------------------------

def _get_authors( article ):
    """Return the searchable authors for an article."""
    query = db.session.query( Author, ArticleAuthor ) \
        .filter( ArticleAuthor.article_id == article.article_id ) \
        .join( Author, ArticleAuthor.author_id == Author.author_id ) \
        .order_by( ArticleAuthor.seq_no )
    return "\n".join( a[0].author_name for a in query )

def _get_scenarios( article ):
    """Return the searchable scenarios for an article."""
    query = db.session.query( Scenario, ArticleScenario ) \
        .filter( ArticleScenario.article_id == article.article_id ) \
        .join( Scenario, ArticleScenario.scenario_id == Scenario.scenario_id ) \
        .order_by( ArticleScenario.seq_no )
    return "\n".join( "{}\t{}".format( s[0].scenario_display_id, s[0].scenario_name ) if s[0].scenario_display_id
        else s[0].scenario_name
        for s in query
    )

def _get_tags( tags ):
    """Return the searchable tags for an article or publication."""
    if not tags:
        return None
    tags = decode_tags( tags )
    return "\n".join( tags )

# map search index columns to ORM fields
_FIELD_MAPPINGS = {
    "publisher": { "name": "publ_name", "description": "publ_description" },
    "publication": { "name": "pub_name", "description": "pub_description",
        "tags": lambda pub: _get_tags( pub.pub_tags )
    },
    "article": { "name": "article_title", "name2": "article_subtitle", "description": "article_snippet",
        "authors": _get_authors, "scenarios": _get_scenarios,
        "tags": lambda article: _get_tags( article.article_tags ),
        "rating": "article_rating"
    }
}

# ---------------------------------------------------------------------

@app.route( "/search", methods=["POST"] )
def search():
    """Run a search."""
    query_string = request.json.get( "query" ).strip()
    return _do_search( query_string, None )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/search/publishers", methods=["POST","GET"] )
def search_publishers():
    """Return all publishers."""
    publs = sorted( Publisher.query.all(), key=lambda p: p.publ_name.lower() )
    results = [ get_publisher_vals( p, True ) for p in publs ]
    return jsonify( results )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/search/publisher/<publ_id>", methods=["POST","GET"] )
def search_publisher( publ_id ):
    """Search for a publisher."""
    publ = Publisher.query.get( publ_id )
    if not publ:
        return jsonify( [] )
    results = [ get_publisher_vals( publ, True ) ]
    pubs = sorted( publ.publications, key=get_publication_sort_key, reverse=True )
    for pub in pubs:
        results.append( get_publication_vals( pub, True, True ) )
    return jsonify( results )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/search/publication/<pub_id>", methods=["POST","GET"] )
def search_publication( pub_id ):
    """Search for a publication."""
    pub = Publication.query.get( pub_id )
    if not pub:
        return jsonify( [] )
    results = [ get_publication_vals( pub, True, True ) ]
    articles = sorted( pub.articles, key=get_article_sort_key )
    for article in articles:
        article =  get_article_vals( article, True )
        _create_aslrb_links( article )
        results.append( article )
    return jsonify( results )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/search/article/<article_id>", methods=["POST","GET"] )
def search_article( article_id ):
    """Search for an article."""
    article = Article.query.get( article_id )
    if not article:
        return jsonify( [] )
    article = get_article_vals( article, True )
    _create_aslrb_links( article )
    results = [ article ]
    if article["pub_id"]:
        pub = Publication.query.get( article["pub_id"] )
        if pub:
            results.append( get_publication_vals( pub, True, True ) )
    return jsonify( results )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/search/author/<author_id>", methods=["POST","GET"] )
def search_author( author_id ):
    """Search for an author."""
    author = Author.query.get( author_id )
    if not author:
        return jsonify( [] )
    author_name = '"{}"'.format( author.author_name.replace( '"', '""' ) )
    return _do_search( author_name, [ "authors" ] )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/search/tag/<tag>", methods=["POST","GET"] )
def search_tag( tag ):
    """Search for a tag."""
    tag = '"{}"'.format( tag.replace( '"', '""' ) )
    return _do_search( tag, [ "tags" ] )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_search( query_string, col_names ):
    """Run a search."""
    try:
        return _do_search2( query_string, col_names )
    except Exception as exc: #pylint: disable=broad-except
        msg = str( exc )
        if isinstance( exc, sqlite3.OperationalError ):
            if msg.startswith( "fts5: " ):
                msg = msg[5:]
        if not msg:
            msg = str( type(exc) )
        return jsonify( { "error": msg } )

def _do_search2( query_string, col_names ):
    """Run a search."""

    # parse the request parameters
    if not query_string:
        raise RuntimeError( "Missing query string." )
    _logger.info( "SEARCH REQUEST: %s", query_string )

    # check for special query terms (for testing porpoises)
    results = []
    def find_special_term( term ):
        nonlocal query_string
        pos = query_string.find( term )
        if pos >= 0:
            query_string = query_string[:pos] + query_string[pos+len(term):]
            return True
        return False
    special_terms = {
        SEARCH_ALL_PUBLISHERS:
            lambda: [ _get_publisher_vals(p) for p in Publisher.query ], #pylint: disable=not-an-iterable
        SEARCH_ALL_PUBLICATIONS:
            lambda: [ _get_publication_vals(p) for p in Publication.query ], #pylint: disable=not-an-iterable
        SEARCH_ALL_ARTICLES:
            lambda: [ _get_article_vals(a) for a in Article.query ] #pylint: disable=not-an-iterable
    }
    if find_special_term( SEARCH_ALL ):
        for term,func in special_terms.items():
            results.extend( func() )
    else:
        for term,func in special_terms.items():
            if find_special_term( term ):
                results.extend( func() )
    query_string = query_string.strip()
    if not query_string:
        return jsonify( results )

    # do the search
    fts_query_string = _make_fts_query_string( query_string, _search_aliases )
    return _do_fts_search( fts_query_string, col_names, results=results )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_fts_search( fts_query_string, col_names, results=None ): #pylint: disable=too-many-locals
    """Run an FTS search."""

    _logger.debug( "FTS query string: %s", fts_query_string )
    if results is None:
        results = []
    no_hilite = request.json and to_bool( request.json.get( "no_hilite" ) )

    # NOTE: We would like to cache the connection, but SQLite connections can only be used
    # in the same thread they were created in.
    with SearchDbConn() as dbconn:

        # generate the search weights
        weights = []
        weights.append( 0.0 ) # nb: this is for the "owner" column
        for col_name in _SEARCHABLE_COL_NAMES:
            weights.append( _search_weights.get( col_name, 1.0 ) )

        # run the search
        hilites = [ "", "" ] if no_hilite else [ BEGIN_HILITE, END_HILITE ]
        def highlight( n ):
            return "highlight( searchable, {}, '{}', '{}' )".format(
                n, hilites[0], hilites[1]
            )
        sql = "SELECT owner, bm25(searchable,{}) AS rank, {}, {}, {}, {}, {}, {}, rating FROM searchable" \
            " WHERE searchable MATCH ?" \
            " ORDER BY rating DESC, rank".format(
                ",".join( str(w) for w in weights ),
                highlight(1), highlight(2), highlight(3), highlight(4), highlight(5), highlight(6)
            )
        match = "{{ {} }}: {}".format(
            " ".join( col_names or _SEARCHABLE_COL_NAMES ),
            fts_query_string
        )
        curs = dbconn.conn.execute( sql, (match,) )

        # get the results
        for row in curs:

            # get the next result
            owner_type, owner_id = row[0].split( ":" )
            model = get_model_from_table_name( owner_type )
            obj = model.query.get( owner_id )
            _logger.debug( "- {} ({:.3f})".format( obj, row[1] ) )

            # prepare the result for the front-end
            result = globals()[ "_get_{}_vals".format( owner_type ) ]( obj )
            result[ "type" ] = owner_type
            result[ "rank" ] = row[1]

            # return highlighted versions of the content to the caller
            fields = _FIELD_MAPPINGS[ owner_type ]
            assert _SEARCHABLE_COL_NAMES[:3] == [ "name", "name2", "description" ]
            for col_no,col_name in enumerate(_SEARCHABLE_COL_NAMES[:3]):
                field = fields.get( col_name )
                if not field:
                    continue
                if row[2+col_no] and BEGIN_HILITE in row[2+col_no]:
                    # NOTE: We have to return both the highlighted and non-highlighted versions, since the front-end
                    # will show the highlighted version in the search results, but the non-highlighted version elsewhere
                    # e.g. an article's title in the titlebar of its edit dialog.
                    result[ field+"!" ] = row[ 2+col_no ]
            if row[5] and BEGIN_HILITE in row[5]:
                result[ "authors!" ] = row[5].split( "\n" )
            if row[6] and BEGIN_HILITE in row[6]:
                result[ "scenarios!" ] = [ s.split("\t") for s in row[6].split("\n") ]
            if row[7] and BEGIN_HILITE in row[7]:
                result[ "tags!" ] = row[7].split( "\n" )

            # create links to the eASLRB
            if owner_type == "article":
                _create_aslrb_links( result )

            # add the result to the list
            results.append( result )

    # check if we should randomize the results
    if request.json and to_bool( request.json.get( "randomize" ) ):
        random.shuffle( results )

    return jsonify( results )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _make_fts_query_string( query_string, search_aliases ):
    """Generate the SQLite query string."""

    # check if this looks like a raw FTS query
    if any( regex.search(query_string) for regex in _PASSTHROUGH_REGEXES ):
        return query_string

    # split the query string (taking into account quoted phrases)
    words = query_string.split()
    i = 0
    while True:
        if i >= len(words):
            break
        if i > 0 and words[i-1].startswith('"'):
            words[i-1] += " {}".format( words[i] )
            del words[i]
            if words[i-1].startswith('"') and words[i-1].endswith('"'):
                words[i-1] = words[i-1][1:-1]
            continue
        i += 1

    # clean up quoted phrases
    words = [ w[1:] if w.startswith('"') else w for w in words ]
    words = [ w[:-1] if w.endswith('"') else w for w in words ]
    words = [ w.strip() for w in words ]
    words = [ w for w in words if w ]

    # quote any phrases that need it
    def has_special_char( word ):
        return any( ch in word for ch in _SQLITE_FTS_SPECIAL_CHARS+" " )
    def quote_word( word ):
        return '"{}"'.format(word) if has_special_char(word) else word
    words = [ quote_word(w) for w in words ]

    # handle search aliases
    for i,word in enumerate(words):
        word = word.lower()
        if word.startswith( '"' ) and word.endswith( '"' ):
            word = word[1:-1]
        aliases = search_aliases.get( word )
        if aliases:
            aliases = [ quote_word( a ) for a in aliases ]
            aliases.sort() # nb: so that tests will work reliably
            words[i] = "({})".format(
                " OR ".join( aliases )
            )

    # escape any special characters
    words = [ w.replace("'","''") for w in words ]

    return " AND ".join( words )

# ---------------------------------------------------------------------

# regex's that specify what a ruleid looks like
_RULEID_REGEXES = [
    re.compile( r"\b[A-Z]\d{0,3}\.\d{1,5}[A-Za-z]?\b" ),
    # nb: while there are ruleid's like "C5", it's far more likely this is referring to a hex :-/
    #re.compile( r"\b[A-Z]\d{1,4}[A-Za-z]?\b" ),
]

def _create_aslrb_links( article ):
    """Create links to the ASLRB for ruleid's."""

    # initialize
    base_url = app.config.get( "ASLRB_BASE_URL",  os.environ.get("ASLRB_BASE_URL") )
    if not base_url:
        return
    if "article_snippet!" in article:
        snippet = article[ "article_snippet!" ]
    else:
        snippet = article[ "article_snippet" ]

    def make_link( startpos, endpos, ruleid, caption ):
        nonlocal snippet
        if ruleid:
            link = "<a href='{}#{}' class='aslrb' target='_blank'>{}</a>".format(
                base_url, ruleid, caption
            )
            snippet = snippet[:startpos] + link + snippet[endpos:]
        else:
            # NOTE: We can get here when a manually-created link has no ruleid e.g. because the content
            # contains something that is incorrectly being detected as a ruleid, and the user has fixed it up.
            snippet = snippet[:startpos] + caption + snippet[endpos:]

    # find ruleid's in the snippet and replace them with links to the ASLRB
    matches = _find_aslrb_ruleids( snippet )
    for match in reversed(matches):
        startpos, endpos, ruleid, caption = match
        make_link( startpos, endpos, ruleid, caption )
    article[ "article_snippet!" ] = snippet

def _find_aslrb_ruleids( val ): #pylint: disable=too-many-branches
    """Find ruleid's."""

    # locate any manually-created links; format is "{:ruleid|caption:}"
    # NOTE: The ruleid is optional, so that if something is incorrectly being detected as a ruleid,
    # the user can disable the link by creating one of these with no ruleid.
    manual = list( re.finditer( r"{:(.*?)\|(.+?):}", val ) )
    def is_manual( target ):
        return any(
            target.start() >= mo.start() and target.end() <= mo.end()
            for mo in manual
        )

    # look for ruleid's
    matches = []
    for regex in _RULEID_REGEXES:
        for mo in regex.finditer( val ):
            if is_manual( mo ):
                continue # nb: ignore any ruleid's that are part of a manually-created link
            matches.append( mo )

    # FUDGE! Remove overlapping matches e.g. if we have "B1.23", we will have matches for "B1" and "B1.23".
    matches2, prev_mo = [], None
    matches.sort( key=lambda mo: mo.start() )
    for mo in matches:
        if prev_mo and mo.start() == prev_mo.start() and len(mo.group()) < len(prev_mo.group()):
            continue
        matches2.append( mo )
        prev_mo = mo

    # extract the start/end positions of each match, ruleid and caption
    matches = [
        [ mo.start(), mo.end(), mo.group(), mo.group() ]
        for mo in matches2
    ]

    # NOTE: If we have something like "C1.23-.45", we want to link to "C1.23",
    # but have the <a> tag wrap the whole thing.
    # NOTE: This won't work if the user searched for "C1.23", since it will be wrapped
    # in a highlight <span>.
    for match in matches:
        endpos = match[1]
        if endpos == len(val) or val[endpos] != "-":
            continue
        nchars, allow_dot = 1, True
        while endpos + nchars < len(val):
            ch = val[ endpos + nchars ]
            if ch.isdigit():
                nchars += 1
            elif ch == "." and allow_dot:
                nchars += 1
                allow_dot = False
            else:
                break
        if nchars > 1:
            match[1] += nchars
            match[3] = val[ match[0] : match[1] ]

    # add any manually-created links
    for mo in manual:
        matches.append( [ mo.start(), mo.end(), mo.group(1), mo.group(2) ] )

    return sorted( matches, key=lambda m: m[0] )

# ---------------------------------------------------------------------

def init_search( session, logger ):
    """Initialize the search engine."""

    # initialize the database
    global _search_index_path
    _search_index_path = app.config.get( "SEARCH_INDEX_PATH" )
    if not _search_index_path:
        # FUDGE! We should be able to create a shared, in-memory database using this:
        #   file::memory:?mode=memory&cache=shared
        # but it doesn't seem to work (on Linux) and ends up creating a file with this name :-/
        # We manually create a temp file, which has to have the same name each time, so that we don't
        # keep creating a new database each time we start up. Sigh...
        _search_index_path = os.path.join( tempfile.gettempdir(), "asl-articles.searchdb" )
    if os.path.isfile( _search_index_path ):
        os.unlink( _search_index_path )

    logger.info( "Creating search index: %s", _search_index_path )
    with SearchDbConn() as dbconn:

        # NOTE: We would like to make "owner" the primary key, but FTS doesn't support primary keys
        # (nor UNIQUE constraints), so we have to manage this manually :-(
        # IMPORTANT: The column order is important here, since we use the column index to generate
        # the bm25() clause when doing searches.
        dbconn.conn.execute(
            "CREATE VIRTUAL TABLE searchable USING fts5"
            " ( owner, {}, rating, tokenize='porter unicode61' )".format(
                ", ".join( _SEARCHABLE_COL_NAMES )
            )
        )

        # load the searchable content
        # NOTE: We insert content in reverse chronological order to get more recent
        # content to appear before other equally-ranked content.
        logger.debug( "Loading the search index..." )
        logger.debug( "- Loading publishers." )
        for publ in session.query( Publisher ).order_by( Publisher.time_created.desc() ):
            add_or_update_publisher( dbconn, publ )
        logger.debug( "- Loading publications." )
        for pub in session.query( Publication ).order_by( Publication.time_created.desc() ):
            add_or_update_publication( dbconn, pub )
        logger.debug( "- Loading articles." )
        for article in session.query( Article ).order_by( Article.time_created.desc() ):
            add_or_update_article( dbconn, article )

    # load the search aliases
    cfg = configparser.ConfigParser()
    fname = os.path.join( asl_articles.config_dir, "app.cfg" )
    _logger.debug( "Loading search aliases: %s", fname )
    cfg.read( fname )
    global _search_aliases
    def get_section( section_name ):
        try:
            return cfg.items( section_name )
        except configparser.NoSectionError:
            return []
    _search_aliases = _load_search_aliases( get_section("Search aliases"), get_section("Search aliases 2") )

    # load the search weights
    _logger.debug( "Loading search weights:" )
    global _search_weights
    for row in get_section( "Search weights" ):
        if row[0] not in _SEARCHABLE_COL_NAMES:
            asl_articles.startup.log_startup_msg( "warning",
                "Unknown search weight field: {}", row[0],
                logger = _logger
            )
            continue
        try:
            _search_weights[ row[0] ] = float( row[1] )
            _logger.debug( "- %s = %s", row[0], row[1] )
        except ValueError:
            asl_articles.startup.log_startup_msg( "warning",
                "Invalid search weight for \"{}\": {}", row[0], row[1],
                logger = _logger
            )

def _load_search_aliases( aliases, aliases2 ):
    """Load the search aliases."""

    # initialize
    search_aliases = {}

    def add_search_alias( key, vals ):
        if key in search_aliases:
            asl_articles.startup.log_startup_msg( "warning",
                "Found duplicate search alias: {}", key,
                logger = _logger
            )
        search_aliases[ key ] =vals

    # load the search aliases
    for row in aliases:
        vals = [ row[0] ]
        vals.extend( v.strip() for v in row[1].split( ";" ) )
        add_search_alias( row[0], vals )
        _logger.debug( "- %s => %s", row[0], vals )

    # load the search aliases
    for row in aliases2:
        vals = itertools.chain( [row[0]], row[1].split("=") )
        vals = [ v.strip().lower() for v in vals ]
        _logger.debug( "- %s", vals )
        for v in vals:
            add_search_alias( v, vals )

    return search_aliases

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def add_or_update_publisher( dbconn, publ ):
    """Add/update a publisher in the search index."""
    _do_add_or_update_searchable( dbconn, "publisher",
        _make_publisher_key(publ), publ
    )

def add_or_update_publication( dbconn, pub ):
    """Add/update a publication in the search index."""
    _do_add_or_update_searchable( dbconn, "publication",
        _make_publication_key(pub.pub_id), pub
    )

def add_or_update_article( dbconn, article ):
    """Add/update an article in the search index."""
    _do_add_or_update_searchable( dbconn, "article",
        _make_article_key(article.article_id), article
    )

def _do_add_or_update_searchable( dbconn, owner_type, owner, obj ):
    """Add or update a record in the search index."""

    # prepare the fields
    fields = _FIELD_MAPPINGS[ owner_type ]
    vals = {
        f: getattr( obj,fields[f] ) if isinstance( fields[f], str ) else fields[f]( obj )
        for f in fields
    }
    # NOTE: We used to strip HTML here, but we prefer to see formatted content
    # when search results are presented to the user.

    def do_add_or_update( dbconn ):
        sql = "INSERT INTO searchable" \
              " ( owner, {}, rating )" \
              " VALUES (?,?,?,?,?,?,?,?)".format(
            ",".join( _SEARCHABLE_COL_NAMES )
        )
        dbconn.conn.execute( sql, (
            owner,
            vals.get("name"), vals.get("name2"), vals.get("description"),
            vals.get("authors"), vals.get("scenarios"), vals.get("tags"),
            vals.get("rating")
        ) )

    # update the database
    if dbconn:
        # NOTE: If  we are passed a connection to use, we assume we are starting up and are doing
        # the initial build of the search index, and therefore don't need to check for an existing row.
        # The caller is responsible for committing the transaction.
        do_add_or_update( dbconn )
    else:
        with SearchDbConn() as dbconn2:
            # NOTE: Because we can't have a UNIQUE constraint on "owner", we can't use UPSERT nor INSERT OR UPDATE,
            # so we have to delete any existing row manually, then insert :-/
            _logger.debug( "Updating searchable: %s", owner )
            _logger.debug( "- %s", " ; ".join( "{}=\"{}\"".format( k, repr(v) ) for k,v in vals.items() if v ) )
            dbconn2.conn.execute( "DELETE FROM searchable WHERE owner = ?", (owner,) )
            do_add_or_update( dbconn2 )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def delete_publishers( publs ):
    """Remove publishers from the search index."""
    with SearchDbConn() as dbconn:
        for publ in publs:
            _do_delete_searchable( dbconn, _make_publisher_key( publ ) )

def delete_publications( pubs ):
    """Remove publications from the search index."""
    with SearchDbConn() as dbconn:
        for pub in pubs:
            _do_delete_searchable( dbconn, _make_publication_key( pub ) )

def delete_articles( articles ):
    """Remove articles from the search index."""
    with SearchDbConn() as dbconn:
        for article in articles:
            _do_delete_searchable( dbconn, _make_article_key( article ) )

def _do_delete_searchable( dbconn, owner ):
    """Remove an entry from the search index."""
    dbconn.conn.execute( "DELETE FROM searchable WHERE owner = ?", (owner,) )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _make_publisher_key( publ ):
    """Generate the owner key for a Publisher."""
    return "publisher:{}".format( publ.publ_id if isinstance(publ,Publisher) else publ )

def _make_publication_key( pub ):
    """Generate the owner key for a Publication."""
    return "publication:{}".format( pub.pub_id if isinstance(pub,Publication) else pub )

def _make_article_key( article ):
    """Generate the owner key for an Article."""
    return "article:{}".format( article.article_id if isinstance(article,Article) else article )
