""" Test the database reports. """

import os
import itertools
import re

from asl_articles.search import SEARCH_ALL
from asl_articles.tests.test_publishers import edit_publisher
from asl_articles.tests.test_publications import edit_publication
from asl_articles.tests.test_articles import edit_article
from asl_articles.tests.utils import init_tests, \
    select_main_menu_option, select_sr_menu_option, check_ask_dialog, \
    do_search, find_search_result, \
    wait_for, wait_for_elem, find_child, find_children

# ---------------------------------------------------------------------

def test_db_report( webdriver, flask_app, dbconn ):
    """Test the database report."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="db-report.json" )

    # check the initial report
    row_counts, links, dupe_images, image_sizes = _get_db_report()
    assert row_counts == {
        "publishers": 2, "publications": 3, "articles": 5,
        "authors": 3, "scenarios": 2
    }
    assert links == {
        "publishers": [ 2, [] ],
        "publications": [ 2, [] ],
        "articles": [ 2, [] ],
    }
    assert dupe_images == []
    assert image_sizes == {}

    # add some images
    results = do_search( SEARCH_ALL )
    publ_sr = find_search_result( "Avalon Hill", results )
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/1.gif" )
    edit_publisher( publ_sr, { "image": fname } )
    pub_sr = find_search_result( "ASL Journal (1)", results )
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/2.gif" )
    edit_publication( pub_sr, { "image": fname } )
    article_sr = find_search_result( "ASLJ article 1", results )
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/3.gif" )
    edit_article( article_sr, { "image": fname } )
    article_sr = find_search_result( "ASLJ article 2", results )
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/3.gif" )
    edit_article( article_sr, { "image": fname } )

    # check the updated report
    row_counts, _, dupe_images, image_sizes = _get_db_report()
    assert row_counts == {
        "publishers": 2, "publisher_images": 1,
        "publications": 3, "publication_images": 1,
        "articles": 5, "article_images": 2,
        "authors": 3, "scenarios": 2
    }
    assert dupe_images == [
        [ "f0457ea742376e76ff276ce62c7a8540", "/images/article/100",
          ( "ASLJ article 1", "/article/100" ),
          ( "ASLJ article 2", "/article/101" ),
        ]
    ]
    assert image_sizes == {
        "publishers": [
            ( "Avalon Hill", "/publisher/1", "/images/publisher/1" ),
        ],
        "publications": [
            ( "ASL Journal (1)", "/publication/10", "/images/publication/10" ),
        ],
        "articles": [
            ( "ASLJ article 1", "/article/100", "/images/article/100" ),
            ( "ASLJ article 2", "/article/101", "/images/article/101" ),
        ]
    }

    # delete all the publishers (and associated objects), then check the updated report
    results = do_search( SEARCH_ALL )
    publ_sr = find_search_result( "Avalon Hill", results )
    select_sr_menu_option( publ_sr, "delete" )
    check_ask_dialog( "Delete this publisher?", "ok" )
    publ_sr = find_search_result( "Multiman Publishing" )
    select_sr_menu_option( publ_sr, "delete" )
    check_ask_dialog( "Delete this publisher?", "ok" )
    row_counts, links, dupe_images, image_sizes = _get_db_report()
    assert row_counts == {
        "publishers": 0, "publications": 0, "articles": 0,
        "authors": 3, "scenarios": 2
    }
    assert links == {
        "publishers": [ 0, [] ],
        "publications": [ 0, [] ],
        "articles": [ 0, [] ],
    }
    assert dupe_images == []
    assert image_sizes == {}

# ---------------------------------------------------------------------

def test_check_db_links( webdriver, flask_app, dbconn ):
    """Test checking links in the database."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, docs="docs/", fixtures="db-report.json" )

    # check the initial report
    _, links, _, _ = _get_db_report()
    assert links == {
        "publishers": [ 2, [] ],
        "publications": [ 2, [] ],
        "articles": [ 2, [] ],
    }

    # check the links
    btn = find_child( "#db-report button.check-links" )
    btn.click()
    status = find_child( "#db-report .db-links .status-msg" )
    wait_for( 10, lambda: status.text == "Checked 6 links." )

    # check the updated report
    _, links, _, _ = _get_db_report()
    assert links == {
        "publishers": [ 2, [
            ( "Multiman Publishing", "/publisher/2", "HTTP 404: http://{FLASK}/unknown" )
        ] ],
        "publications": [ 2, [] ],
        "articles": [ 2, [
            ( "MMP publisher article", "/article/299", "HTTP 404: /unknown" )
        ] ],
    }

# ---------------------------------------------------------------------

def _get_db_report(): #pylint: disable=too-many-locals
    """Generate the database report."""

    # generate the report
    select_main_menu_option( "db-report" )
    wait_for_elem( 2, "#db-report .db-images" )

    # unload the row counts
    row_counts = {}
    table = find_child( "#db-report .db-row-counts" )
    for row in find_children( "tr", table ):
        cells = find_children( "td", row )
        mo = re.search( r"^(\d+)( \((\d+) images?\))?$", cells[1].text )
        key = cells[0].text.lower()[:-1]
        row_counts[ key ] = int( mo.group(1) )
        if mo.group( 3 ):
            row_counts[ key[:-1] + "_images" ] = int( mo.group(3) )

    # unload the links
    links = {}
    table = find_child( "#db-report .db-links" )
    last_key = None
    for row in find_children( "tr", table ):
        cells = find_children( "td", row )
        if len(cells) == 2:
            last_key = cells[0].text.lower()[:-1]
            links[ last_key ] = [ int( cells[1].text ) , [] ]
        else:
            mo = re.search( r"^(.+) \((.+)\)$", cells[0].text )
            tags = find_children( "a", cells[0] )
            url = _fixup_url( tags[0].get_attribute( "href" ) )
            links[ last_key ][1].append( ( mo.group(1), url, mo.group(2) ) )

    # unload duplicate images
    dupe_images = []
    for row in find_children( "#db-report .dupe-analysis .dupe-image" ):
        elem = find_child( ".caption .hash", row )
        mo = re.search( r"^\(md5:(.+)\)$", elem.text )
        image_hash = mo.group(1)
        image_url = _fixup_url( find_child( "img", row ).get_attribute( "src" ) )
        parents = []
        for entry in find_children( ".collapsible li", row ):
            url = _fixup_url( find_child( "a", entry ).get_attribute( "href" ) )
            parents.append( ( entry.text, url ) )
        dupe_images.append( list( itertools.chain(
            [ image_hash, image_url ], parents
        ) ) )

    # unload the image sizes
    tab_ctrl = find_child( "#db-report .db-images .react-tabs" )
    image_sizes = {}
    for tab in find_children( ".react-tabs__tab", tab_ctrl ):
        key = tab.text.lower()
        tab_id = tab.get_attribute( "id" )
        tab.click()
        sel = ".react-tabs__tab-panel[aria-labelledby='{}'].react-tabs__tab-panel--selected".format( tab_id )
        tab_page = wait_for( 2,
            lambda: find_child( sel, tab_ctrl ) #pylint: disable=cell-var-from-loop
        )
        parents = []
        for row_no, row in enumerate( find_children( "table.image-sizes tr", tab_page ) ):
            if row_no == 0:
                continue
            cells = find_children( "td", row )
            image_url = _fixup_url( find_child( "img", cells[0] ).get_attribute( "src" ) )
            url = _fixup_url( find_child( "a", cells[2] ).get_attribute( "href" ) )
            parents.append( ( cells[2].text, url, image_url ) )
        if parents:
            image_sizes[ key ] = parents
        else:
            assert tab_page.text == "No images found."

    return row_counts, links, dupe_images, image_sizes

# ---------------------------------------------------------------------

def _fixup_url( url ):
    """Fixup a URL to make it independent of its server."""
    url = re.sub( r"^http://[^/]+", "", url )
    pos = url.find( "?" )
    if pos >= 0:
        url = url[:pos]
    return url
