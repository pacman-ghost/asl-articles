""" Handle article requests. """

import datetime
import base64
import logging

from flask import request, jsonify, abort
from sqlalchemy.sql.expression import func

from asl_articles import app, db
from asl_articles.models import Article, Author, ArticleAuthor, Scenario, ArticleScenario, ArticleImage
from asl_articles.authors import get_author_vals
from asl_articles.scenarios import get_scenario_vals
import asl_articles.publications
import asl_articles.publishers
from asl_articles import search
from asl_articles.utils import get_request_args, clean_request_args, clean_tags, encode_tags, decode_tags, \
    apply_attrs, make_ok_response

_logger = logging.getLogger( "db" )

_FIELD_NAMES = [ "*article_title", "article_subtitle", "article_snippet", "article_pageno",
    "article_url", "article_tags", "pub_id", "publ_id"
]

# ---------------------------------------------------------------------

@app.route( "/article/<article_id>" )
def get_article( article_id ):
    """Get an article."""
    _logger.debug( "Get article: id=%s", article_id )
    article = Article.query.get( article_id )
    if not article:
        abort( 404 )
    _logger.debug( "- %s", article )
    deep = request.args.get( "deep" )
    return jsonify( get_article_vals( article, deep ) )

def get_article_vals( article, deep ):
    """Extract public fields from an Article record."""
    authors = sorted( article.article_authors,
        key = lambda a: a.seq_no
    )
    scenarios = sorted( article.article_scenarios,
        key = lambda a: a.seq_no
    )
    vals = {
        "_type": "article",
        "article_id": article.article_id,
        "article_title": article.article_title,
        "article_subtitle": article.article_subtitle,
        "article_image_id": article.article_id if article.article_image else None,
        "article_authors": [ get_author_vals( a.parent_author ) for a in authors ],
        "article_snippet": article.article_snippet,
        "article_pageno": article.article_pageno,
        "article_url": article.article_url,
        "article_scenarios": [ get_scenario_vals( s.parent_scenario ) for s in scenarios ],
        "article_tags": decode_tags( article.article_tags ),
        "article_rating": article.article_rating,
        "pub_id": article.pub_id,
        "publ_id": article.publ_id,
    }
    if deep:
        vals["_parent_pub"] = asl_articles.publications.get_publication_vals(
                article.parent_pub, False, False
            ) if article.parent_pub else None
        vals["_parent_publ"] = asl_articles.publishers.get_publisher_vals(
                article.parent_publ, False, False
            ) if article.parent_publ else None
    return vals

def get_article_sort_key( article ):
    """Get an article's sort key."""
    # NOTE: This is used to sort articles within their parent publication.
    # NOTE: Articles should always have a seq# but sometimes they might not (e.g. created via a fixture).
    return 999 if article.article_seqno is None else article.article_seqno

# ---------------------------------------------------------------------

@app.route( "/article/create", methods=["POST"] )
def create_article():
    """Create an article."""

    # parse the input
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Create article:" )
    )
    warnings = []
    clean_request_args( vals, _FIELD_NAMES, warnings, _logger )

    # NOTE: Tags are stored in the database using \n as a separator, so we need to encode *after* cleaning them.
    cleaned_tags = clean_tags( vals.get("article_tags"), warnings )
    vals[ "article_tags" ] = encode_tags( cleaned_tags )

    # create the new article
    vals[ "time_created" ] = datetime.datetime.now()
    article = Article( **vals )
    db.session.add( article )
    db.session.flush()
    new_article_id = article.article_id
    _set_seqno( article, article.pub_id )
    _save_authors( article )
    _save_scenarios( article )
    _save_image( article )
    db.session.commit()
    _logger.debug( "- New ID: %d", new_article_id )
    search.add_or_update_article( None, article, None )

    # generate the response
    vals = get_article_vals( article, True )
    return make_ok_response( record=vals, warnings=warnings )

def _set_seqno( article, pub_id ):
    """Set an article's seq#."""
    if pub_id:
        max_seqno = db.session.query( func.max( Article.article_seqno ) ) \
            .filter( Article.pub_id == pub_id ) \
            .scalar()
        article.article_seqno = 1 if max_seqno is None else max_seqno+1
    else:
        article.article_seqno = None

def _save_authors( article ):
    """Save the article's authors."""

    # delete the existing article-author rows
    db.session.query( ArticleAuthor ) \
        .filter( ArticleAuthor.article_id == article.article_id ) \
        .delete()

    # add the article-author rows
    authors = request.json.get( "article_authors", [] )
    for seq_no,author in enumerate( authors ):
        if isinstance( author, int ):
            # this is an existing author
            author_id = author
        else:
            # this is a new author - create it
            if not isinstance( author, str ):
                raise RuntimeError( "Expected an author name: {}".format( author ) )
            author = Author( author_name=author )
            db.session.add( author )
            db.session.flush()
            author_id = author.author_id
            _logger.debug( "Created new author \"%s\": id=%d", author, author_id )
        db.session.add(
            ArticleAuthor( seq_no=seq_no, article_id=article.article_id, author_id=author_id )
        )

def _save_scenarios( article ):
    """Save the article's scenarios."""

    # delete the existing article-scenario rows
    db.session.query( ArticleScenario ) \
        .filter( ArticleScenario.article_id == article.article_id ) \
        .delete()

    # add the article-scenario rows
    scenarios = request.json.get( "article_scenarios", [] )
    for seq_no,scenario in enumerate( scenarios ):
        if isinstance( scenario, int ):
            # this is an existing scenario
            scenario_id = scenario
        else:
            # this is a new scenario - create it
            if not isinstance( scenario, list ):
                raise RuntimeError( "Expected a scenario ID and name: {}".format( scenario ) )
            new_scenario = Scenario( scenario_display_id=scenario[0], scenario_name=scenario[1] )
            db.session.add( new_scenario )
            db.session.flush()
            scenario_id = new_scenario.scenario_id
            _logger.debug( "Created new scenario \"%s [%s]\": id=%d", scenario[1], scenario[0], scenario_id )
        db.session.add(
            ArticleScenario( seq_no=seq_no, article_id=article.article_id, scenario_id=scenario_id )
        )

def _save_image( article ):
    """Save the article's image."""

    # check if a new image was provided
    image_data = request.json.get( "imageData" )
    if not image_data:
        return

    # yup - delete the old one from the database
    ArticleImage.query.filter( ArticleImage.article_id == article.article_id ).delete()
    if image_data == "{remove}":
        # NOTE: The front-end sends this if it wants the article to have no image.
        article.article_image_id = None
        return

    # add the new image to the database
    image_data = base64.b64decode( image_data )
    fname = request.json.get( "imageFilename" )
    img = ArticleImage( article_id=article.article_id, image_filename=fname, image_data=image_data )
    db.session.add( img )
    db.session.flush()
    _logger.debug( "Created new image: %s, #bytes=%d", fname, len(image_data) )

# ---------------------------------------------------------------------

@app.route( "/article/update", methods=["POST"] )
def update_article():
    """Update an article."""

    # parse the input
    article_id = request.json[ "article_id" ]
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Update article: id={}".format( article_id ) )
    )
    warnings = []
    clean_request_args( vals, _FIELD_NAMES, warnings, _logger )

    # NOTE: Tags are stored in the database using \n as a separator, so we need to encode *after* cleaning them.
    cleaned_tags = clean_tags( vals.get("article_tags"), warnings )
    vals[ "article_tags" ] = encode_tags( cleaned_tags )

    # update the article
    article = Article.query.get( article_id )
    if not article:
        abort( 404 )
    if vals["pub_id"] != article.pub_id:
        _set_seqno( article, vals["pub_id"] )
    vals[ "time_updated" ] = datetime.datetime.now()
    apply_attrs( article, vals )
    _save_authors( article )
    _save_scenarios( article )
    _save_image( article )
    db.session.commit()
    search.add_or_update_article( None, article, None )

    # generate the response
    vals = get_article_vals( article, True )
    return make_ok_response( record=vals, warnings=warnings )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/article/update-rating", methods=["POST"] )
def update_article_rating():
    """Update an article's rating."""

    # parse the input
    article_id = request.json[ "article_id" ]
    new_rating = int( request.json[ "rating" ] )
    if new_rating < 0 or new_rating > 3:
        raise ValueError( "Invalid rating." )

    # update the article's rating
    article = Article.query.get( article_id )
    if not article:
        abort( 404 )
    article.article_rating = new_rating
    db.session.commit()
    search.add_or_update_article( None, article, None )

    return "OK"

# ---------------------------------------------------------------------

@app.route( "/article/delete/<article_id>" )
def delete_article( article_id ):
    """Delete an article."""

    # parse the input
    _logger.debug( "Delete article: id=%s", article_id )
    article = Article.query.get( article_id )
    if not article:
        abort( 404 )
    _logger.debug( "- %s", article )

    # delete the article
    db.session.delete( article )
    db.session.commit()
    search.delete_articles( [ article ] )

    # generate the response
    return make_ok_response()
