""" Test article scenario operations. """

import urllib.request
import json

from asl_articles.tests.utils import init_tests, find_child, find_children, wait_for_elem, find_search_result
from asl_articles.tests.react_select import ReactSelect

from asl_articles.tests.test_articles import create_article, edit_article

# ---------------------------------------------------------------------

def test_article_scenarios( webdriver, flask_app, dbconn ):
    """Test article scenario operations."""

    # initialize
    init_tests( webdriver, flask_app, dbconn, fixtures="article-scenarios.json" )
    all_scenarios = set( [
        "Test Scenario 1 [TEST 1]", "Test Scenario 2 [TEST 2]", "Test Scenario 3 [TEST 3]",
        "No scenario ID"
    ] )

    # create some test articles
    create_article( { "title": "article 1" } )
    create_article( { "title": "article 2" } )
    _check_scenarios( flask_app, all_scenarios, [ [], [] ] )

    # add a scenario to article #1
    edit_article( find_search_result( "article 1" ), {
        "scenarios": [ "+Test Scenario 1 [TEST 1]" ]
    } )
    _check_scenarios( flask_app, all_scenarios, [
        [ "Test Scenario 1 [TEST 1]" ],
        []
    ] )

    # add scenarios to article #2
    edit_article( find_search_result( "article 2" ), {
        "scenarios": [ "+Test Scenario 3 [TEST 3]", "+No scenario ID" ]
    } )
    _check_scenarios( flask_app, all_scenarios, [
        [ "Test Scenario 1 [TEST 1]" ],
        [ "Test Scenario 3 [TEST 3]", "No scenario ID" ]
    ] )

    # add/remove scenarios to article #2
    edit_article( find_search_result( "article 2" ), {
        "scenarios": [ "+Test Scenario 1 [TEST 1]", "-Test Scenario 3 [TEST 3]" ]
    } )
    _check_scenarios( flask_app, all_scenarios, [
        [ "Test Scenario 1 [TEST 1]" ],
        [ "No scenario ID",  "Test Scenario 1 [TEST 1]" ]
    ] )

    # add an unknown scenario to article #1
    edit_article( find_search_result( "article 1" ), {
        "scenarios": [ "+new scenario [NEW]" ]
    } )
    _check_scenarios( flask_app, all_scenarios, [
        [ "Test Scenario 1 [TEST 1]", "new scenario [NEW]" ],
        [ "No scenario ID",  "Test Scenario 1 [TEST 1]" ]
    ] )

# ---------------------------------------------------------------------

def _check_scenarios( flask_app, all_scenarios, expected ):
    """Check the scenarios of the test articles."""

    # update the complete list of scenarios
    # NOTE: Unlike tags, scenarios remain in the database even if no-one is referencing them,
    # so we need to track them over the life of the entire series of tests.
    for scenarios in expected:
        all_scenarios.update( scenarios )

    # check the scenarios in the UI
    for article_no,scenarios in enumerate( expected ):

        # check the scenarios in the article's search result
        sr = find_search_result( "article {}".format( 1+article_no ) )
        sr_scenarios = [ s.text for s in find_children( ".scenario", sr ) ]
        assert sr_scenarios == scenarios

        # check the scenarios in the article's config
        find_child( ".edit", sr ).click()
        dlg = wait_for_elem( 2, "#modal-form" )
        select = ReactSelect( find_child( ".scenarios .react-select", dlg ) )
        assert select.get_multiselect_values() == scenarios

        # check that the list of available scenarios is correct
        assert select.get_multiselect_choices() == \
            sorted( all_scenarios.difference( scenarios ), key=lambda s: s.lower() )

        # close the dialog
        find_child( "button.cancel", dlg ).click()

    # check the scenarios in the database
    url = flask_app.url_for( "get_scenarios" )
    scenarios = json.load( urllib.request.urlopen( url ) )
    assert set( _make_scenario_display_name(a) for a in scenarios.values() ) == all_scenarios

def _make_scenario_display_name( scenario ):
    """Generate the display name for a scenario."""
    if scenario["scenario_display_id"]:
        return "{} [{}]".format( scenario["scenario_name"], scenario["scenario_display_id"] )
    else:
        return scenario["scenario_name"]
