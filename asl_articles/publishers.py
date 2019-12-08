""" Handle publisher requests. """

import datetime
import logging

from flask import request, jsonify, abort

from asl_articles import app, db
from asl_articles.models import Publisher, Publication, Article
from asl_articles.publications import do_get_publications
from asl_articles.utils import get_request_args, clean_request_args, make_ok_response, apply_attrs

_logger = logging.getLogger( "db" )

_FIELD_NAMES = [ "publ_name", "publ_description", "publ_url" ]

# ---------------------------------------------------------------------

@app.route( "/publishers" )
def get_publishers():
    """Get all publishers."""
    return jsonify( _do_get_publishers() )

def _do_get_publishers():
    """Get all publishers."""
    # NOTE: The front-end maintains a cache of the publishers, so as a convenience,
    # we return the current list as part of the response to a create/update/delete operation.
    results = Publisher.query.all()
    return { r.publ_id: get_publisher_vals(r) for r in results }

# ---------------------------------------------------------------------

@app.route( "/publisher/<publ_id>" )
def get_publisher( publ_id ):
    """Get a publisher."""
    _logger.debug( "Get publisher: id=%s", publ_id )
    # get the publisher
    publ = Publisher.query.get( publ_id )
    if not publ:
        abort( 404 )
    vals = get_publisher_vals( publ )
    # include the number of associated publications
    query = Publication.query.filter_by( publ_id = publ_id )
    vals[ "nPublications" ] = query.count()
    # include the number of associated articles
    query = db.session.query #pylint: disable=no-member
    query = query( Article, Publication ) \
        .filter( Publication.publ_id == publ_id ) \
        .filter( Article.pub_id == Publication.pub_id )
    vals[ "nArticles" ] = query.count()
    _logger.debug( "- %s ; #publications=%d ; #articles=%d", publ, vals["nPublications"], vals["nArticles"] )
    return jsonify( vals )

def get_publisher_vals( publ ):
    """Extract public fields from a Publisher record."""
    return {
        "publ_id": publ.publ_id,
        "publ_name": publ.publ_name,
        "publ_description": publ.publ_description,
        "publ_url": publ.publ_url,
    }

# ---------------------------------------------------------------------

@app.route( "/publisher/create", methods=["POST"] )
def create_publisher():
    """Create a publisher."""
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Create publisher:" )
    )
    cleaned = clean_request_args( vals, _FIELD_NAMES, _logger )
    vals[ "time_created" ] = datetime.datetime.now()
    publ = Publisher( **vals )
    db.session.add( publ ) #pylint: disable=no-member
    db.session.commit() #pylint: disable=no-member
    _logger.debug( "- New ID: %d", publ.publ_id )
    extras = { "publ_id": publ.publ_id }
    if request.args.get( "list" ):
        extras[ "publishers" ] = _do_get_publishers()
    return make_ok_response( cleaned=cleaned, extras=extras )

# ---------------------------------------------------------------------

@app.route( "/publisher/update", methods=["POST"] )
def update_publisher():
    """Update a publisher."""
    publ_id = request.json[ "publ_id" ]
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Update publisher: id={}".format( publ_id ) )
    )
    cleaned = clean_request_args( vals, _FIELD_NAMES, _logger )
    vals[ "time_updated" ] = datetime.datetime.now()
    publ = Publisher.query.get( publ_id )
    if not publ:
        abort( 404 )
    apply_attrs( publ, vals )
    db.session.commit() #pylint: disable=no-member
    extras = {}
    if request.args.get( "list" ):
        extras[ "publishers" ] = _do_get_publishers()
    return make_ok_response( cleaned=cleaned, extras=extras )

# ---------------------------------------------------------------------

@app.route( "/publisher/delete/<publ_id>" )
def delete_publisher( publ_id ):
    """Delete a publisher."""

    _logger.debug( "Delete publisher: id=%s", publ_id )

    # get the publisher
    publ = Publisher.query.get( publ_id )
    if not publ:
        abort( 404 )
    _logger.debug( "- %s", publ )

    # figure out which associated publications will be deleted
    query = db.session.query( Publication.pub_id ).filter_by( publ_id = publ_id ) #pylint: disable=no-member
    deleted_pubs = [ r[0] for r in query ]

    # figure out which associated articles will be deleted
    query = db.session.query #pylint: disable=no-member
    query = query( Article.article_id ).join( Publication ) \
        .filter( Publication.publ_id == publ_id ) \
        .filter( Article.pub_id == Publication.pub_id )
    deleted_articles = [ r[0] for r in query ]

    # delete the publisher
    db.session.delete( publ ) #pylint: disable=no-member
    db.session.commit() #pylint: disable=no-member

    extras = { "deletedPublications": deleted_pubs, "deletedArticles": deleted_articles }
    if request.args.get( "list" ):
        extras[ "publishers" ] = _do_get_publishers()
        extras[ "publications" ] = do_get_publications()
    return make_ok_response( extras=extras )
