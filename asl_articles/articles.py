""" Handle article requests. """

import datetime
import logging

from flask import request, jsonify, abort

from asl_articles import app, db
from asl_articles.models import Article
from asl_articles.utils import get_request_args, clean_request_args, make_ok_response, apply_attrs

_logger = logging.getLogger( "db" )

_FIELD_NAMES = [ "article_title", "article_subtitle", "article_snippet", "article_url", "pub_id" ]

# ---------------------------------------------------------------------

@app.route( "/article/<article_id>" )
def get_article( article_id ):
    """Get an article."""
    _logger.debug( "Get article: id=%s", article_id )
    article = Article.query.get( article_id )
    if not article:
        abort( 404 )
    _logger.debug( "- %s", article )
    return jsonify( get_article_vals( article ) )

def get_article_vals( article ):
    """Extract public fields from an Article record."""
    return {
        "article_id": article.article_id,
        "article_title": article.article_title,
        "article_subtitle": article.article_subtitle,
        "article_snippet": article.article_snippet,
        "article_url": article.article_url,
        "pub_id": article.pub_id,
    }

# ---------------------------------------------------------------------

@app.route( "/article/create", methods=["POST"] )
def create_article():
    """Create an article."""
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Create article:" )
    )
    cleaned = clean_request_args( vals, _FIELD_NAMES, _logger )
    vals[ "time_created" ] = datetime.datetime.now()
    article = Article( **vals )
    db.session.add( article ) #pylint: disable=no-member
    db.session.commit() #pylint: disable=no-member
    _logger.debug( "- New ID: %d", article.article_id )
    return make_ok_response( cleaned=cleaned,
        extras = { "article_id": article.article_id }
    )

# ---------------------------------------------------------------------

@app.route( "/article/update", methods=["POST"] )
def update_article():
    """Update an article."""
    article_id = request.json[ "article_id" ]
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Update article: id={}".format( article_id ) )
    )
    cleaned = clean_request_args( vals, _FIELD_NAMES, _logger )
    vals[ "time_updated" ] = datetime.datetime.now()
    article = Article.query.get( article_id )
    if not article:
        abort( 404 )
    apply_attrs( article, vals )
    db.session.commit() #pylint: disable=no-member
    return make_ok_response( cleaned=cleaned )

# ---------------------------------------------------------------------

@app.route( "/article/delete/<article_id>" )
def delete_article( article_id ):
    """Delete an article."""
    _logger.debug( "Delete article: id=%s", article_id )
    article = Article.query.get( article_id )
    if not article:
        abort( 404 )
    _logger.debug( "- %s", article )
    db.session.delete( article ) #pylint: disable=no-member
    db.session.commit() #pylint: disable=no-member
    return make_ok_response( extras={} )
