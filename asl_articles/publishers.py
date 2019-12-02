""" Handle publisher requests. """

import datetime
import logging

from flask import request, jsonify, abort

from asl_articles import app, db
from asl_articles.models import Publisher
from asl_articles.utils import get_request_args, apply_attrs, clean_html

_logger = logging.getLogger( "db" )

_FIELD_NAMES = [ "publ_name", "publ_url", "publ_description" ]

# ---------------------------------------------------------------------

@app.route( "/publishers/create", methods=["POST"] )
def create_publisher():
    """Create a publisher."""
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Create publisher:" )
    )
    cleaned = _clean_vals( vals )
    vals[ "time_created" ] = datetime.datetime.now()
    publ = Publisher( **vals )
    db.session.add( publ ) #pylint: disable=no-member
    db.session.commit() #pylint: disable=no-member
    _logger.debug( "- New ID: %d", publ.publ_id )
    return _make_ok_response( cleaned, { "publ_id": publ.publ_id } )

# ---------------------------------------------------------------------

@app.route( "/publishers/update", methods=["POST"] )
def update_publisher():
    """Update a publisher."""
    publ_id = request.json[ "publ_id" ]
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Update publisher: id={}".format( publ_id ) )
    )
    cleaned = _clean_vals( vals )
    vals[ "time_updated" ] = datetime.datetime.now()
    publ = Publisher.query.get( publ_id )
    if not publ:
        abort( 404 )
    apply_attrs( publ, vals )
    db.session.commit() #pylint: disable=no-member
    return _make_ok_response( cleaned )

# ---------------------------------------------------------------------

@app.route( "/publishers/delete/<publ_id>" )
def delete_publisher( publ_id ):
    """Delete a publisher."""
    _logger.debug( "Delete publisher: %s", publ_id )
    publ = Publisher.query.get( publ_id )
    if not publ:
        abort( 404 )
    _logger.debug( "- %s", publ )
    db.session.delete( publ ) #pylint: disable=no-member
    db.session.commit() #pylint: disable=no-member
    return _make_ok_response( None )

# ---------------------------------------------------------------------

def _make_ok_response( cleaned, extras=None ):
    """Generate a Flask 'success' response."""
    # generate the basic response
    resp = { "status": "OK" }
    if extras:
        resp.update( extras )
    # check if any values were cleaned
    if cleaned:
        # yup - return the updated values to the caller
        resp[ "warning" ] = "Some values had HTML removed."
        resp[ "cleaned" ] = cleaned
    return jsonify( resp )

def _clean_vals( vals ):
    """Clean incoming data."""
    cleaned = {}
    for f in _FIELD_NAMES:
        val2 = clean_html( vals[f] )
        if val2 != vals[f]:
            _logger.debug( "Cleaned HTML: %s => %s", f, val2 )
            vals[f] = val2
            cleaned[f] = val2
    return cleaned
