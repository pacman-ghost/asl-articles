""" Test author operations. """

import urllib.request
import json

from asl_articles.tests.utils import init_tests, find_child, find_children, wait_for_elem, find_search_result
from asl_articles.tests.react_select import ReactSelect

from asl_articles.tests.test_articles import _create_article, _edit_article

# ---------------------------------------------------------------------

def test_article_authors( webdriver, flask_app, dbconn ):
    """Test article author operations."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    # create some test articles
    _create_article( { "title": "article 1" } )
    _create_article( { "title": "article 2" } )
    all_authors = set()
    _check_authors( flask_app, all_authors, [ [], [] ] )

    # add an author to article #1
    _edit_article( find_search_result( "article 1" ), {
        "authors": [ "+andrew" ]
    } )
    _check_authors( flask_app, all_authors, [ ["andrew"], [] ] )

    # add authors to article #2
    _edit_article( find_search_result( "article 2" ), {
        "authors": [ "+bob", "+charlie" ]
    } )
    _check_authors( flask_app, all_authors, [ ["andrew"], ["bob","charlie"] ] )

    # add/remove authors to article #2
    _edit_article( find_search_result( "article 2" ), {
        "authors": [ "+dan", "-charlie", "+andrew" ]
    } )
    _check_authors( flask_app, all_authors, [ ["andrew"], ["bob","dan","andrew"] ] )

    # add new/existing authors to article #1
    # NOTE: The main thing we're checking here is that despite new and existing authors
    # being added to the article, their order is preserved.
    _edit_article( find_search_result( "article 1" ), {
        "authors": [ "+bob", "+new1", "+charlie", "+new2" ]
    } )
    _check_authors( flask_app, all_authors, [
        ["andrew","bob","new1","charlie","new2"], ["bob","dan","andrew"]
    ] )

# ---------------------------------------------------------------------

def _check_authors( flask_app, all_authors, expected ):
    """Check the authors of the test articles."""

    # update the complete list of authors
    # NOTE: Unlike tags, authors remain in the database even if no-one is referencing them,
    # so we need to track them over the life of the entire series of tests.
    for authors in expected:
        all_authors.update( authors )

    # check the authors in the UI
    for article_no,authors in enumerate( expected ):

        # check the authors in the article's search result
        sr = find_search_result( "article {}".format( 1+article_no ) )
        sr_authors = [ a.text for a in find_children( ".author", sr ) ]
        assert sr_authors == authors

        # check the authors in the article's config
        find_child( ".edit", sr ).click()
        dlg = wait_for_elem( 2, "#modal-form" )
        select = ReactSelect( find_child( ".authors .react-select", dlg ) )
        assert select.get_multiselect_values() == authors

        # check that the list of available authors is correct
        assert select.get_multiselect_choices() == sorted( all_authors.difference( authors ) )

        # close the dialog
        find_child( "button.cancel", dlg ).click()

    # check the authors in the database
    url = flask_app.url_for( "get_authors" )
    authors = json.load( urllib.request.urlopen( url ) )
    assert set( a["author_name"] for a in authors.values() ) == all_authors
