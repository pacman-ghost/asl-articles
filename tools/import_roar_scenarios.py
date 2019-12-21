#!/usr/bin/env python3
""" Import scenarios from ROAR into our database.

Download this file somewhere:
    https://vasl-templates.org/services/roar/scenario-index.json
Then pass it in to this program.

This script should be run to initialize a new database with a list of known scenarios, but we also
have to consider the possibilty that it will be run on a database that has been in use for a while,
and has new scenarios that have been added by the user i.e. we need to try to match scenarios
that are already in the database with what's in ROAR.
"""

import sys
import os
import json

import sqlalchemy
from sqlalchemy import text

# ---------------------------------------------------------------------

def main():
    """Import ROAR scenarios into our database."""

    # parse the command line arguments
    if len(sys.argv) != 3:
        print( "Usage: {} <dbconn> <scenario-index>".format( os.path.split(__file__)[0] ) )
        print( "  dbconn:         database connection string e.g. \"sqlite:///~/asl-articles.db\"" )
        print( "  scenario-index: the ROAR scenario index file." )
        sys.exit( 0 )
    dbconn = sys.argv[1]
    roar_fname = sys.argv[2]

    # load the ROAR scenario data
    stats, warnings = import_roar_scenarios( dbconn, roar_fname, progress=print )

    # output any warnings
    for warning in warnings:
        print()
        print( "\n".join( warning ) )

    # output stats
    row_count = lambda n: "1 row" if n == 1 else "{} rows".format(n)
    print()
    print( "New scenarios added: {}".format( row_count( stats["nInserts"] ) ) )
    print( "Scenarios updated:   {}".format( row_count( stats["nUpdates"] ) ) )
    print( "Duplicates ignored:  {}".format( row_count( stats["nDupes"] ) ) )

# ---------------------------------------------------------------------

def import_roar_scenarios( dbconn, roar_data, progress=None ):
    """Import scenarios from ROAR into our database."""

    # initialize
    stats = { "nInserts": 0, "nUpdates": 0, "nDupes": 0 }
    warnings = []
    def log_progress( msg, *args, **kwargs ):
        if progress:
            progress( msg.format( *args, **kwargs ) )

    # load the ROAR scenarios
    if isinstance( roar_data, str ):
        log_progress( "Loading scenarios: {}", roar_data )
        roar_data = json.load( open( roar_data, "r" ) )
    else:
        assert isinstance( roar_data, dict )
    log_progress( "- Last updated: {}".format( roar_data.get("_lastUpdated_","(unknown)") ) )
    scenarios = { k: v for k,v in roar_data.items() if k.isdigit() }
    log_progress( "- Loaded {} scenarios.".format( len(scenarios) ) )

    # update the database
    # NOTE: We can never delete rows from the scenario table, since Article's reference them by ID.
    engine = sqlalchemy.create_engine( dbconn )
    conn = engine.connect()
    with conn.begin():

        for roar_id,scenario in scenarios.items():

            # prepare the next scenario
            vals = { "roar_id": roar_id, "display_id": scenario["scenario_id"], "name": scenario["name"] }

            # check if we already have the scenario
            row = find_existing_scenario( conn, roar_id, scenario )
            if row:

                # yup - check if the details are the same
                if row["scenario_display_id"] == scenario["scenario_id"] and row["scenario_name"] == scenario["name"]:
                    # yup - nothing to do
                    stats[ "nDupes" ] += 1
                    continue

                # nope - update the row
                warnings.append( [
                    "Data mismatch for ROAR ID {}:".format( roar_id ),
                    "- Old details: {}: {}".format( row["scenario_display_id"], row["scenario_name"] ),
                    "- Updating to: {}: {}".format( scenario["scenario_id"], scenario["name"] )
                ] )
                conn.execute( text( "UPDATE scenario"
                    " SET scenario_display_id = :display_id, scenario_name = :name"
                    " WHERE scenario_id = :scenario_id" ),
                    scenario_id=row["scenario_id"], **vals
                )
                stats[ "nUpdates" ] += 1

            else:

                # nope - insert a new row
                conn.execute( text( "INSERT INTO scenario"
                    " ( scenario_roar_id, scenario_display_id, scenario_name )"
                    " VALUES ( :roar_id, :display_id, :name )" ),
                    **vals
                )
                stats[ "nInserts" ] += 1

    conn.close()

    return stats, warnings

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def find_existing_scenario( conn, roar_id, scenario ):
    """Check if the scenario is already in the database.

    Identifying existing scenarios in the database is complicated by the fact that the user can add scenarios
    from the webapp, and the only required field is the scenario name e.g. we have to handle things like:
    - this script is run to load an empty database
    - the user manually adds a new scenario, but only provides its name
    - the scenario is added to ROAR (with a ROAR ID and scenario ID)
    - this script is run again.
    In this case, we want to match the two scenarios and update the existing row, not create a new one.
    """

    def find_match( sql, **args ):
        rows = list( conn.execute( text(sql), **args ) )
        if rows:
            assert len(rows) == 1
            return rows[0]
        else:
            return None

    # try to match by ROAR ID
    row = find_match( "SELECT * FROM scenario WHERE scenario_roar_id = :roar_id",
        roar_id = roar_id
    )
    if row:
        return row

    # try to match by scenario display ID and name
    row = find_match( "SELECT * FROM scenario"
        " WHERE (scenario_roar_id IS NULL OR scenario_roar_id = '' )"
        " AND scenario_display_id = :scenario_id AND scenario_name = :name",
        scenario_id=scenario["scenario_id"], name=scenario["name"]
    )
    if row:
        return row

    # try to match by scenario name
    row = find_match( "SELECT * FROM scenario"
        " WHERE (scenario_roar_id IS NULL OR scenario_roar_id = '' )"
        " AND ( scenario_display_id IS NULL OR scenario_display_id = '' )"
        " AND scenario_name = :name",
        name=scenario["name"]
    )
    if row:
        return row

    return None

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main()
