""" Handle scenario requests. """

from flask import jsonify

from asl_articles import app
from asl_articles.models import Scenario

# ---------------------------------------------------------------------

@app.route( "/scenarios" )
def get_scenarios():
    """Get all scenarios."""
    return jsonify( {
        scenario.scenario_id: get_scenario_vals( scenario )
        for scenario in Scenario.query.all()
    } )

def get_scenario_vals( scenario ):
    """Extract public fields from a scenario record."""
    return {
        "scenario_id": scenario.scenario_id,
        "scenario_display_id": scenario.scenario_display_id,
        "scenario_name": scenario.scenario_name
    }
