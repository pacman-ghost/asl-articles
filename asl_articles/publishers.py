""" Handle publisher requests. """

import datetime
import base64
import logging

from flask import request, jsonify, abort

from asl_articles import app, db
from asl_articles.models import Publisher, PublisherImage, Publication, Article
from asl_articles.publications import get_publication_vals, get_publication_sort_key
from asl_articles.articles import get_article_vals, get_article_sort_key
from asl_articles import search
from asl_articles.utils import get_request_args, clean_request_args, make_ok_response, apply_attrs

_logger = logging.getLogger( "db" )

_FIELD_NAMES = [ "*publ_name", "publ_description", "publ_url" ]

# ---------------------------------------------------------------------

@app.route( "/publishers" )
def get_publishers():
    """Get all publishers."""
    return jsonify( {
        publ.publ_id: get_publisher_vals( publ, False, False )
        for publ in Publisher.query.all()
    } )

# ---------------------------------------------------------------------

@app.route( "/publisher/<publ_id>" )
def get_publisher( publ_id ):
    """Get a publisher."""
    _logger.debug( "Get publisher: id=%s", publ_id )
    # get the publisher
    publ = Publisher.query.get( publ_id )
    if not publ:
        abort( 404 )
    vals = get_publisher_vals( publ,
        request.args.get( "include_pubs" ),
        request.args.get( "include_articles" )
    )
    # include the number of associated publications
    query = Publication.query.filter_by( publ_id = publ_id )
    vals[ "nPublications" ] = query.count()
    # include the number of associated articles
    query = db.session.query( Article, Publication ) \
        .filter( Publication.publ_id == publ_id ) \
        .filter( Article.pub_id == Publication.pub_id )
    nArticles = query.count()
    nArticles2 = Article.query.filter_by( publ_id = publ_id ).count()
    vals[ "nArticles" ] = nArticles + nArticles2
    _logger.debug( "- %s ; #publications=%d ; #articles=%d", publ, vals["nPublications"], vals["nArticles"] )
    return jsonify( vals )

def get_publisher_vals( publ, include_pubs, include_articles ):
    """Extract public fields from a Publisher record."""
    vals = {
        "_type": "publisher",
        "publ_id": publ.publ_id,
        "publ_name": publ.publ_name,
        "publ_description": publ.publ_description,
        "publ_url": publ.publ_url,
        "publ_image_id": publ.publ_id if publ.publ_image else None,
    }
    if include_pubs:
        pubs = sorted( publ.publications, key=get_publication_sort_key )
        vals[ "publications" ] = [ get_publication_vals( p, False, False ) for p in pubs ]
    if include_articles:
        articles = sorted( publ.articles, key=get_article_sort_key )
        vals[ "articles" ] = [ get_article_vals( a, False ) for a in articles ]
    return vals

# ---------------------------------------------------------------------

@app.route( "/publisher/create", methods=["POST"] )
def create_publisher():
    """Create a publisher."""

    # parse the input
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Create publisher:" )
    )
    warnings = []
    clean_request_args( vals, _FIELD_NAMES, warnings, _logger )

    # create the new publisher
    vals[ "time_created" ] = datetime.datetime.now()
    publ = Publisher( **vals )
    db.session.add( publ )
    _save_image( publ )
    db.session.commit()
    _logger.debug( "- New ID: %d", publ.publ_id )
    search.add_or_update_publisher( None, publ, None )

    # generate the response
    vals = get_publisher_vals( publ, True, True )
    return make_ok_response( record=vals, warnings=warnings )

def _save_image( publ ):
    """Save the publisher's image."""

    # check if a new image was provided
    image_data = request.json.get( "imageData" )
    if not image_data:
        return

    # yup - delete the old one from the database
    PublisherImage.query.filter( PublisherImage.publ_id == publ.publ_id ).delete()
    if image_data == "{remove}":
        # NOTE: The front-end sends this if it wants the publisher to have no image.
        publ.publ_image_id = None
        return

    # add the new image to the database
    image_data = base64.b64decode( image_data )
    fname = request.json.get( "imageFilename" )
    img = PublisherImage( publ_id=publ.publ_id, image_filename=fname, image_data=image_data )
    db.session.add( img )
    db.session.flush()
    _logger.debug( "Created new image: %s, #bytes=%d", fname, len(image_data) )

# ---------------------------------------------------------------------

@app.route( "/publisher/update", methods=["POST"] )
def update_publisher():
    """Update a publisher."""

    # parse the input
    publ_id = request.json[ "publ_id" ]
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Update publisher: id={}".format( publ_id ) )
    )
    warnings = []
    clean_request_args( vals, _FIELD_NAMES, warnings, _logger )

    # update the publisher
    publ = Publisher.query.get( publ_id )
    if not publ:
        abort( 404 )
    _save_image( publ )
    vals[ "time_updated" ] = datetime.datetime.now()
    apply_attrs( publ, vals )
    db.session.commit()
    search.add_or_update_publisher( None, publ, None )

    # generate the response
    vals = get_publisher_vals( publ, True, True )
    return make_ok_response( record=vals, warnings=warnings )

# ---------------------------------------------------------------------

@app.route( "/publisher/delete/<publ_id>" )
def delete_publisher( publ_id ):
    """Delete a publisher."""

    # parse the input
    _logger.debug( "Delete publisher: id=%s", publ_id )
    publ = Publisher.query.get( publ_id )
    if not publ:
        abort( 404 )
    _logger.debug( "- %s", publ )

    # figure out which associated publications will be deleted
    query = db.session.query( Publication.pub_id ) \
        .filter_by( publ_id = publ_id )
    deleted_pubs = [ r[0] for r in query ]

    # figure out which associated articles will be deleted
    query = db.session.query( Article.article_id ).join( Publication ) \
        .filter( Publication.publ_id == publ_id ) \
        .filter( Article.pub_id == Publication.pub_id )
    deleted_articles = [ r[0] for r in query ]

    # delete the publisher
    db.session.delete( publ )
    db.session.commit()
    search.delete_publishers( [ publ ] )
    search.delete_publications( deleted_pubs )
    search.delete_articles( deleted_articles )

    extras = { "deletedPublications": deleted_pubs, "deletedArticles": deleted_articles }
    return make_ok_response( extras=extras )
