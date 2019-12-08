""" Handle publication requests. """

import datetime
import logging

from flask import request, jsonify, abort

from asl_articles import app, db
from asl_articles.models import Publication, Article
from asl_articles.utils import get_request_args, clean_request_args, make_ok_response, apply_attrs

_logger = logging.getLogger( "db" )

_FIELD_NAMES = [ "pub_name", "pub_edition", "pub_description", "pub_url", "publ_id" ]

# ---------------------------------------------------------------------

@app.route( "/publications" )
def get_publications():
    """Get all publications."""
    return jsonify( do_get_publications() )

def do_get_publications():
    """Get all publications."""
    # NOTE: The front-end maintains a cache of the publications, so as a convenience,
    # we return the current list as part of the response to a create/update/delete operation.
    results = Publication.query.all()
    return { r.pub_id: get_publication_vals(r) for r in results }

# ---------------------------------------------------------------------

@app.route( "/publication/<pub_id>" )
def get_publication( pub_id ):
    """Get a publication."""
    _logger.debug( "Get publication: id=%s", pub_id )
    pub = Publication.query.get( pub_id )
    if not pub:
        abort( 404 )
    vals = get_publication_vals( pub )
    # include the number of associated articles
    query = Article.query.filter_by( pub_id = pub_id )
    vals[ "nArticles" ] = query.count()
    _logger.debug( "- %s ; #articles=%d", pub, vals["nArticles"] )
    return jsonify( vals )

def get_publication_vals( pub ):
    """Extract public fields from a Publication record."""
    return {
        "pub_id": pub.pub_id,
        "pub_name": pub.pub_name,
        "pub_edition": pub.pub_edition,
        "pub_description": pub.pub_description,
        "pub_url": pub.pub_url,
        "publ_id": pub.publ_id,
    }

# ---------------------------------------------------------------------

@app.route( "/publication/create", methods=["POST"] )
def create_publication():
    """Create a publication."""
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Create publication:" )
    )
    cleaned = clean_request_args( vals, _FIELD_NAMES, _logger )
    vals[ "time_created" ] = datetime.datetime.now()
    pub = Publication( **vals )
    db.session.add( pub ) #pylint: disable=no-member
    db.session.commit() #pylint: disable=no-member
    _logger.debug( "- New ID: %d", pub.pub_id )
    extras = { "pub_id": pub.pub_id }
    if request.args.get( "list" ):
        extras[ "publications" ] = do_get_publications()
    return make_ok_response( cleaned=cleaned, extras=extras )

# ---------------------------------------------------------------------

@app.route( "/publication/update", methods=["POST"] )
def update_publication():
    """Update a publication."""
    pub_id = request.json[ "pub_id" ]
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Update publication: id={}".format( pub_id ) )
    )
    cleaned = clean_request_args( vals, _FIELD_NAMES, _logger )
    vals[ "time_updated" ] = datetime.datetime.now()
    pub = Publication.query.get( pub_id )
    if not pub:
        abort( 404 )
    apply_attrs( pub, vals )
    db.session.commit() #pylint: disable=no-member
    extras = {}
    if request.args.get( "list" ):
        extras[ "publications" ] = do_get_publications()
    return make_ok_response( cleaned=cleaned, extras=extras )

# ---------------------------------------------------------------------

@app.route( "/publication/delete/<pub_id>" )
def delete_publication( pub_id ):
    """Delete a publication."""

    _logger.debug( "Delete publication: id=%s", pub_id )

    # get the publication
    pub = Publication.query.get( pub_id )
    if not pub:
        abort( 404 )
    _logger.debug( "- %s", pub )

    # figure out which associated articles will be deleted
    query = db.session.query( Article.article_id ).filter_by( pub_id = pub_id ) #pylint: disable=no-member
    deleted_articles = [ r[0] for r in query ]

    # delete the publication
    db.session.delete( pub ) #pylint: disable=no-member
    db.session.commit() #pylint: disable=no-member

    extras = { "deleteArticles": deleted_articles }
    if request.args.get( "list" ):
        extras[ "publications" ] = do_get_publications()
    return make_ok_response( extras=extras )
