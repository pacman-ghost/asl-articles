""" Handle scenario requests. """

from flask import jsonify

from asl_articles import app
from asl_articles.models import Scenario

# ---------------------------------------------------------------------

@app.route( "/scenarios" )
def get_scenarios():
    """Get all scenarios."""
    return jsonify( do_get_scenarios() )

def do_get_scenarios():
    """Get all scenarios."""
    return {
        s.scenario_id: _get_scenario_vals( s )
        for s in Scenario.query #pylint: disable=not-an-iterable
    }

def _get_scenario_vals( scenario ):
    """Extract public fields from a scenario record."""
    return {
        "scenario_id": scenario.scenario_id,
        "scenario_display_id": scenario.scenario_display_id,
        "scenario_name": scenario.scenario_name
    }
