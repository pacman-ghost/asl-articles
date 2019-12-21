""" Test importing ROAR scenarios into our database. """

import sys
import os
import json

from asl_articles.models import Scenario
from asl_articles.tests.utils import init_db

sys.path.append( os.path.join( os.path.split(__file__)[0], "../../tools/" ) )
from import_roar_scenarios import import_roar_scenarios

# ---------------------------------------------------------------------

def test_import_roar_scenarios( dbconn ):
    """Test importing ROAR scenarios."""

    # initialize
    session = init_db( dbconn, None )
    roar_fname = os.path.join( os.path.split(__file__)[0], "fixtures/roar-scenarios.json" )
    roar_data = json.load( open( roar_fname, "r" ) )

    # do the first import
    _do_import( dbconn, session, roar_fname,
        { "nInserts": 3, "nUpdates": 0, "nDupes": 0 }, [
            [ "1", "1", "Fighting Withdrawal" ],
            [ "99", "FOO BAR", "test scenario" ],
            [ "129", "E", "Hill 621" ]
    ] )

    # repeat the import (nothing should happen)
    _do_import( dbconn, session, roar_fname,
        { "nInserts": 0, "nUpdates": 0, "nDupes": 3 }, [
            [ "1", "1", "Fighting Withdrawal" ],
            [ "99", "FOO BAR", "test scenario" ],
            [ "129", "E", "Hill 621" ]
    ] )

    # simulate a scenario's details being updated in ROAR (we should update accordingly)
    roar_data["1"]["scenario_id"] += "u"
    roar_data["1"]["name"] += " (updated)"
    _do_import( dbconn, session, roar_data,
        { "nInserts": 0, "nUpdates": 1, "nDupes": 2 }, [
            [ "1", "1u", "Fighting Withdrawal (updated)" ],
            [ "99", "FOO BAR", "test scenario" ],
            [ "129", "E", "Hill 621" ],
        ],
        [ "Data mismatch for ROAR ID 1:" ]
    )

    # add a new ROAR scenario (we should import the new scenario)
    roar_data[ "42" ] = { "scenario_id": "NEW", "name": "new scenario" }
    _do_import( dbconn, session, roar_data,
        { "nInserts": 1, "nUpdates": 0, "nDupes": 3 }, [
            [ "1", "1u", "Fighting Withdrawal (updated)" ],
            [ "99", "FOO BAR", "test scenario" ],
            [ "129", "E", "Hill 621" ],
            [ "42", "NEW", "new scenario" ]
    ] )

    # delete all ROAR scenarios (nothing should happen)
    _do_import( dbconn, session, {},
        { "nInserts": 0, "nUpdates": 0, "nDupes": 0 }, [
            [ "1", "1u", "Fighting Withdrawal (updated)" ],
            [ "99", "FOO BAR", "test scenario" ],
            [ "129", "E", "Hill 621" ],
            [ "42", "NEW", "new scenario" ]
    ] )

# ---------------------------------------------------------------------

def test_scenario_matching( dbconn ):
    """Test matching ROAR scenarios with scenarios in the database."""

    # initialize
    session = init_db( dbconn, None )
    roar_fname = os.path.join( os.path.split(__file__)[0], "fixtures/roar-scenarios.json" )

    # put a scenario in the database that has no ROAR ID
    session.add( Scenario( scenario_display_id="1", scenario_name="Fighting Withdrawal" ) )
    session.commit()

    # do an import
    # NOTE: The scenario we created above will be matched to the corresponding ROAR scenario,
    # since the ROAR ID is not considered when matching scenarios.
    _do_import( dbconn, session, roar_fname,
        { "nInserts": 2, "nUpdates": 0, "nDupes": 1 }, [
            [ None, "1", "Fighting Withdrawal" ],
            [ "99", "FOO BAR", "test scenario" ],
            [ "129", "E", "Hill 621" ]
    ] )

    # put a scenario in the database that only has a name
    session.query( Scenario ).delete()
    session.add( Scenario( scenario_name="Hill 621" ) )
    session.commit()

    # do an import
    # NOTE: The scenario we created above will be matched to the corresponding ROAR scenario,
    # and also updated with the scenario ID (as reported by ROAR).
    _do_import( dbconn, session, roar_fname,
        { "nInserts": 2, "nUpdates": 1, "nDupes": 0 }, [
            [ "1", "1", "Fighting Withdrawal" ],
            [ "99", "FOO BAR", "test scenario" ],
            [ None, "E", "Hill 621" ]
        ],
        [ "Data mismatch for ROAR ID 129:" ]
    )

# ---------------------------------------------------------------------

def _do_import( dbconn, session, roar_data, expected_stats, expected_scenarios, expected_warnings=None ):
    """Import the ROAR scenarios and check the results."""

    # import the ROAR scenarios
    stats, warnings = import_roar_scenarios( dbconn.url, roar_data )

    # check that the import went as expected
    assert stats == expected_stats
    if expected_warnings:
        assert warnings[0][0] == expected_warnings[0]
    else:
        assert not warnings

    # check the scenarios in the database
    rows = [
        [ s.scenario_roar_id, s.scenario_display_id, s.scenario_name ]
        for s in session.query( Scenario ) #pylint: disable=not-an-iterable
    ]
    sort_rows = lambda rows: sorted( rows, key=lambda r: r[2] )
    assert sort_rows( rows ) == sort_rows( expected_scenarios )
