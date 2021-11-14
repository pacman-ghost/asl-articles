""" Handle author requests. """

import logging

from flask import jsonify, abort

from asl_articles import app
from asl_articles.models import Author

_logger = logging.getLogger( "db" )

# ---------------------------------------------------------------------

@app.route( "/authors" )
def get_authors():
    """Get all authors."""
    return jsonify( {
        author.author_id: get_author_vals( author )
        for author in Author.query.all()
    } )

# ---------------------------------------------------------------------

@app.route( "/author/<author_id>" )
def get_author( author_id ):
    """Get an author."""
    _logger.debug( "Get author: id=%s", author_id )
    author = Author.query.get( author_id )
    if not author:
        abort( 404 )
    vals = get_author_vals( author )
    _logger.debug( "- %s", author )
    return jsonify( vals )

def get_author_vals( author ):
    """Extract public fields from an Author record."""
    return {
        "author_id": author.author_id,
        "author_name": author.author_name
    }
