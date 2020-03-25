""" Test previewing images. """

import os

from selenium.common.exceptions import ElementClickInterceptedException

from asl_articles.search import SEARCH_ALL_PUBLISHERS, SEARCH_ALL_PUBLICATIONS, SEARCH_ALL_ARTICLES
from asl_articles.tests.test_publishers import create_publisher, edit_publisher
from asl_articles.tests.test_publications import create_publication, edit_publication
from asl_articles.tests.test_articles import create_article, edit_article
from asl_articles.tests.utils import init_tests, find_child, find_children, wait_for, \
    do_search, get_search_results, call_with_retry

# ---------------------------------------------------------------------

def test_image_preview( webdriver, flask_app, dbconn ):
    """Test previewing images."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )

    def do_test( create, edit, refresh ):

        # create a new object
        webdriver.refresh()
        create()
        results = get_search_results()
        assert len(results) == 1
        sr = results[0]

        # add images to the object
        # NOTE: We're testing that images in an object already on-screen is updated correctly.
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/1.gif" )
        description = 'foo <img src="/images/app.png" style="height:2em;" class="preview"> bar'
        edit( sr, fname, description )
        _check_previewable_images( sr )

        # refresh the object
        # NOTE: We're testing that images in an object loaded afresh is set up correctly.
        webdriver.refresh()
        wait_for( 2, lambda: find_child( "#search-form" ) )
        results = refresh()
        assert len(results) == 1
        _check_previewable_images( results[0] )

    # do the tests
    do_test(
        lambda: create_publisher( { "name": "Test publisher" } ),
        lambda sr, fname, description: edit_publisher( sr, { "image": fname, "description": description } ),
        lambda: do_search( SEARCH_ALL_PUBLISHERS )
    )
    do_test(
        lambda: create_publication( { "name": "Test publication" } ),
        lambda sr, fname, description: edit_publication( sr, { "image": fname, "description": description } ),
        lambda: do_search( SEARCH_ALL_PUBLICATIONS )
    )
    do_test(
        lambda: create_article( { "title": "Test article" } ),
        lambda sr, fname, description: edit_article( sr, { "image": fname, "snippet": description } ),
        lambda: do_search( SEARCH_ALL_ARTICLES )
    )

# ---------------------------------------------------------------------

def _check_previewable_images( sr ):
    """Check that previewable images are working correctly."""
    images = list( find_children( "a.preview img", sr ) )
    assert len(images) == 2
    for img in images:
        assert find_child( ".jquery-image-zoom" ) is None
        img.click()
        preview = wait_for( 2, lambda: find_child( ".jquery-image-zoom" ) )
        call_with_retry( preview.click, [ElementClickInterceptedException] )
        wait_for( 2, lambda: find_child( ".jquery-image-zoom" ) is None )
