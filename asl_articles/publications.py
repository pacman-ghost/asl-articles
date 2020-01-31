""" Handle publication requests. """

import datetime
import base64
import logging

from flask import request, jsonify, abort

from asl_articles import app, db
from asl_articles.models import Publication, PublicationImage, Article
from asl_articles.articles import get_article_vals
from asl_articles.tags import do_get_tags
from asl_articles import search
from asl_articles.utils import get_request_args, clean_request_args, clean_tags, encode_tags, decode_tags, \
    apply_attrs, make_ok_response

_logger = logging.getLogger( "db" )

_FIELD_NAMES = [ "*pub_name", "pub_edition", "pub_description", "pub_date", "pub_url", "pub_tags", "publ_id" ]

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

def get_publication_vals( pub, add_type=False ):
    """Extract public fields from a Publication record."""
    vals = {
        "pub_id": pub.pub_id,
        "pub_name": pub.pub_name,
        "pub_edition": pub.pub_edition,
        "pub_date": pub.pub_date,
        "pub_description": pub.pub_description,
        "pub_url": pub.pub_url,
        "pub_image_id": pub.pub_id if pub.pub_image else None,
        "pub_tags": decode_tags( pub.pub_tags ),
        "publ_id": pub.publ_id,
        "time_created": int( pub.time_created.timestamp() ) if pub.time_created else None,
    }
    if add_type:
        vals[ "type" ] = "publication"
    return vals

# ---------------------------------------------------------------------

@app.route( "/publication/create", methods=["POST"] )
def create_publication():
    """Create a publication."""

    # parse the input
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Create publication:" )
    )
    warnings = []
    updated = clean_request_args( vals, _FIELD_NAMES, warnings, _logger )

    # NOTE: Tags are stored in the database using \n as a separator, so we need to encode *after* cleaning them.
    cleaned_tags = clean_tags( vals.get("pub_tags"), warnings )
    vals[ "pub_tags" ] = encode_tags( cleaned_tags )
    if cleaned_tags != vals.get( "pub_tags" ):
        updated[ "pub_tags" ] = decode_tags( vals["pub_tags"] )

    # create the new publication
    vals[ "time_created" ] = datetime.datetime.now()
    pub = Publication( **vals )
    db.session.add( pub )
    _save_image( pub, updated )
    db.session.commit()
    _logger.debug( "- New ID: %d", pub.pub_id )
    search.add_or_update_publication( None, pub )

    # generate the response
    extras = { "pub_id": pub.pub_id }
    if request.args.get( "list" ):
        extras[ "publications" ] = do_get_publications()
        extras[ "tags" ] = do_get_tags()
    return make_ok_response( updated=updated, extras=extras, warnings=warnings )

def _save_image( pub, updated ):
    """Save the publication's image."""

    # check if a new image was provided
    image_data = request.json.get( "imageData" )
    if not image_data:
        return

    # yup - delete the old one from the database
    PublicationImage.query.filter( PublicationImage.pub_id == pub.pub_id ).delete()
    if image_data == "{remove}":
        # NOTE: The front-end sends this if it wants the publication to have no image.
        updated[ "pub_image_id" ] = None
        return

    # add the new image to the database
    image_data = base64.b64decode( image_data )
    fname = request.json.get( "imageFilename" )
    img = PublicationImage( pub_id=pub.pub_id, image_filename=fname, image_data=image_data )
    db.session.add( img )
    db.session.flush()
    _logger.debug( "Created new image: %s, #bytes=%d", fname, len(image_data) )
    updated[ "pub_image_id" ] = pub.pub_id

# ---------------------------------------------------------------------

@app.route( "/publication/update", methods=["POST"] )
def update_publication():
    """Update a publication."""

    # parse the input
    pub_id = request.json[ "pub_id" ]
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Update publication: id={}".format( pub_id ) )
    )
    warnings = []
    updated = clean_request_args( vals, _FIELD_NAMES, warnings, _logger )
    article_order = request.json.get( "article_order" )

    # NOTE: Tags are stored in the database using \n as a separator, so we need to encode *after* cleaning them.
    cleaned_tags = clean_tags( vals.get("pub_tags"), warnings )
    vals[ "pub_tags" ] = encode_tags( cleaned_tags )
    if cleaned_tags != vals.get( "pub_tags" ):
        updated[ "pub_tags" ] = decode_tags( vals["pub_tags"] )

    # update the publication
    pub = Publication.query.get( pub_id )
    if not pub:
        abort( 404 )
    vals[ "time_updated" ] = datetime.datetime.now()
    apply_attrs( pub, vals )
    _save_image( pub, updated )
    if article_order:
        query = Article.query.filter( Article.pub_id == pub_id )
        articles = { int(a.article_id): a for a in query }
        for n,article_id in enumerate(article_order):
            if article_id not in articles:
                _logger.warning( "Can't set seq# for article %d, not in publication %d: %s",
                    article_id, pub_id, article_order
                )
                continue
            articles[ article_id ].article_seqno = n
            del articles[ article_id ]
        if articles:
            _logger.warning( "seq# was not set for some articles in publication %d: %s",
                pub_id, ", ".join(str(k) for k in articles)
            )
    db.session.commit()
    search.add_or_update_publication( None, pub )

    # generate the response
    extras = {}
    if request.args.get( "list" ):
        extras[ "publications" ] = do_get_publications()
        extras[ "tags" ] = do_get_tags()
    return make_ok_response( updated=updated, extras=extras, warnings=warnings )

# ---------------------------------------------------------------------

@app.route( "/publication/delete/<pub_id>" )
def delete_publication( pub_id ):
    """Delete a publication."""

    # parse the input
    _logger.debug( "Delete publication: id=%s", pub_id )
    pub = Publication.query.get( pub_id )
    if not pub:
        abort( 404 )
    _logger.debug( "- %s", pub )

    # figure out which associated articles will be deleted
    query = db.session.query( Article.article_id ) \
        .filter_by( pub_id = pub_id )
    deleted_articles = [ r[0] for r in query ]

    # delete the publication
    db.session.delete( pub )
    db.session.commit()
    search.delete_publications( [ pub ] )
    search.delete_articles( deleted_articles )

    # generate the response
    extras = { "deleteArticles": deleted_articles }
    if request.args.get( "list" ):
        extras[ "publications" ] = do_get_publications()
        extras[ "tags" ] = do_get_tags()
    return make_ok_response( extras=extras )

# ---------------------------------------------------------------------

@app.route( "/publication/<pub_id>/articles" )
def get_publication_articles( pub_id ):
    """Get the articles for a publication."""
    pub = Publication.query.get( pub_id )
    if not pub:
        abort( 404 )
    articles = sorted( pub.articles, key=lambda a: 999 if a.article_seqno is None else a.article_seqno )
    return jsonify( [ get_article_vals(a) for a in articles ] )
