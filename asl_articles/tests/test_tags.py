""" Test tag operations. """

import urllib.request
import json

from asl_articles.tests.utils import init_tests, wait_for_elem, find_child, find_children, \
    find_search_result, get_result_names
from asl_articles.tests.react_select import ReactSelect

from asl_articles.tests.test_publications import create_publication, edit_publication
from asl_articles.tests.test_articles import create_article, edit_article

# ---------------------------------------------------------------------

def test_tags( webdriver, flask_app, dbconn ):
    """Test tag operations."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create a test publication and article
    create_publication( { "name": "publication 1" } )
    create_article( { "title": "article 1" } )
    _check_tags( flask_app, {
        "publication 1": [],
        "article 1": []
    } )

    # add some tags to the publication
    edit_publication( find_search_result( "publication 1" ), {
        "tags": [ "+aaa", "+bbb" ]
    } )
    _check_tags( flask_app, {
        "publication 1": [ "aaa", "bbb" ],
        "article 1": []
    } )

    # add some tags to the article
    edit_article( find_search_result( "article 1" ), {
        "tags": [ "+bbb", "+ccc" ]
    } )
    _check_tags( flask_app, {
        "publication 1": [ "aaa", "bbb" ],
        "article 1": [ "bbb", "ccc" ]
    } )

    # remove some tags from the publication
    edit_article( find_search_result( "publication 1" ), {
        "tags": [ "-bbb" ]
    } )
    _check_tags( flask_app, {
        "publication 1": [ "aaa" ],
        "article 1": [ "bbb", "ccc" ]
    } )

    # remove some tags from the article
    edit_article( find_search_result( "article 1" ), {
        "tags": [ "-ccc", "-bbb" ]
    } )
    _check_tags( flask_app, {
        "publication 1": [ "aaa" ],
        "article 1": []
    } )

    # add duplicate tags to the publication
    edit_article( find_search_result( "publication 1" ), {
        "tags": [ "+bbb", "+aaa", "+eee" ]
    } )
    _check_tags( flask_app, {
        "publication 1": [ "aaa","bbb","eee" ],
        "article 1": []
    } )

# ---------------------------------------------------------------------

def test_clean_html( webdriver, flask_app, dbconn ):
    """Test cleaning HTML from tags."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # try to create a publication with HTML tags
    create_publication( {
        "name": "test publication",
        "tags": [ "+<b>bold</b>" ]
    }, toast_type="warning" )
    _check_tags( flask_app, {
        "test publication": [ "bold" ]
    } )

    # try to create an article with HTML tags
    create_article( {
        "title": "test article",
        "tags": [ "+<i>italic</i>" ]
    }, toast_type="warning" )
    _check_tags( flask_app, {
        "test publication": [ "bold" ],
        "test article": [ "italic" ]
    } )

# ---------------------------------------------------------------------

def _check_tags( flask_app, expected ):
    """Check the tags in the UI and database."""

    # get the complete list of expected tags
    expected_available = set()
    for tags in expected.values():
        expected_available.update( tags )

    # check the tags in the UI
    elems = find_children( "#search-results .search-result" )
    assert set( get_result_names( elems ) ) == set( expected.keys() )
    for sr in elems:

        # check the tags in the search result
        name = find_child( ".name span", sr ).text
        tags = [ t.text for t in find_children( ".tag", sr ) ]
        assert tags == expected[ name ]

        # check the tags in the publication/article
        find_child( ".edit", sr ).click()
        dlg = wait_for_elem( 2, "#modal-form" )
        select = ReactSelect( find_child( ".tags .react-select", dlg ) )
        assert select.get_multiselect_values() == expected[ name ]

        # check that the list of available tags is correct
        # NOTE: We don't bother checking the tag order here.
        assert set( select.get_multiselect_choices() ) == expected_available.difference( expected[name] )

        # close the dialog
        find_child( "button.cancel", dlg ).click()

    def fixup_tags( tags ):
        return [] if tags is None else tags

    # check the tags in the database
    for sr in elems:
        if sr.text.startswith( "publication" ):
            pub_id = sr.get_attribute( "testing--pub_id" )
            url = flask_app.url_for( "get_publication", pub_id=pub_id )
            pub = json.load( urllib.request.urlopen( url ) )
            assert expected[ pub["pub_name"] ] == fixup_tags( pub["pub_tags"] )
        elif sr.text.startswith( "article" ):
            article_id = sr.get_attribute( "testing--article_id" )
            url = flask_app.url_for( "get_article", article_id=article_id )
            article = json.load( urllib.request.urlopen( url ) )
            assert expected[ article["article_title"] ] == fixup_tags( article["article_tags"] )
