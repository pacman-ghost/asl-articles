""" Handle search requests. """

import logging

from flask import request, jsonify

from asl_articles import app
from asl_articles.models import Publisher, Publication
from asl_articles.publishers import get_publisher_vals
from asl_articles.publications import get_publication_vals

_logger = logging.getLogger( "search" )

# ---------------------------------------------------------------------

@app.route( "/search", methods=["POST"] )
def search():
    """Run a search query."""

    # initialize
    query_string = request.json.get( "query" ).strip()
    _logger.debug( "SEARCH: [%s]", query_string )
    results = []

    # return all publishers
    query = Publisher.query
    if query_string:
        query = query.filter(
            Publisher.publ_name.ilike( "%{}%".format( query_string ) )
        )
    query = query.order_by( Publisher.publ_name.asc() )
    publishers = list( query )
    _logger.debug( "- Found: %s", " ; ".join( str(p) for p in publishers ) )
    for publ in publishers:
        publ = get_publisher_vals( publ )
        publ["type"] = "publisher"
        results.append( publ )

    # return all publications
    query = Publication.query
    if query_string:
        query = query.filter(
            Publication.pub_name.ilike( "%{}%".format( query_string ) )
        )
    query = query.order_by( Publication.pub_name.asc() )
    publications = list( query )
    _logger.debug( "- Found: %s", " ; ".join( str(p) for p in publications ) )
    for pub in publications:
        pub = get_publication_vals( pub )
        pub[ "type" ] = "publication"
        results.append( pub )

    return jsonify( results )
