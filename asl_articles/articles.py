""" Handle article requests. """

import datetime
import base64
import logging

from flask import request, jsonify, abort

from asl_articles import app, db
from asl_articles.models import Article, Author, ArticleAuthor, Scenario, ArticleScenario, ArticleImage
from asl_articles.authors import do_get_authors
from asl_articles.scenarios import do_get_scenarios
from asl_articles.tags import do_get_tags
from asl_articles import search
from asl_articles.utils import get_request_args, clean_request_args, clean_tags, encode_tags, decode_tags, \
    apply_attrs, make_ok_response

_logger = logging.getLogger( "db" )

_FIELD_NAMES = [ "*article_title", "article_subtitle", "article_snippet", "article_url", "article_tags", "pub_id" ]

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

def get_article_vals( article, add_type=False ):
    """Extract public fields from an Article record."""
    authors = sorted( article.article_authors,
        key = lambda a: a.seq_no
    )
    scenarios = sorted( article.article_scenarios,
        key = lambda a: a.seq_no
    )
    vals = {
        "article_id": article.article_id,
        "article_title": article.article_title,
        "article_subtitle": article.article_subtitle,
        "article_image_id": article.article_id if article.article_image else None,
        "article_authors": [ a.author_id for a in authors ],
        "article_snippet": article.article_snippet,
        "article_url": article.article_url,
        "article_scenarios": [ s.scenario_id for s in scenarios ],
        "article_tags": decode_tags( article.article_tags ),
        "pub_id": article.pub_id,
    }
    if add_type:
        vals[ "type" ] = "article"
    return vals

# ---------------------------------------------------------------------

@app.route( "/article/create", methods=["POST"] )
def create_article():
    """Create an article."""

    # parse the input
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Create article:" )
    )
    warnings = []
    updated = clean_request_args( vals, _FIELD_NAMES, warnings, _logger )

    # NOTE: Tags are stored in the database using \n as a separator, so we need to encode *after* cleaning them.
    cleaned_tags = clean_tags( vals.get("article_tags"), warnings )
    vals[ "article_tags" ] = encode_tags( cleaned_tags )
    if cleaned_tags != vals.get( "article_tags" ):
        updated[ "article_tags" ] = decode_tags( vals["article_tags"] )

    # create the new article
    vals[ "time_created" ] = datetime.datetime.now()
    article = Article( **vals )
    db.session.add( article )
    db.session.flush()
    new_article_id = article.article_id
    _save_authors( article, updated )
    _save_scenarios( article, updated )
    _save_image( article, updated )
    db.session.commit()
    _logger.debug( "- New ID: %d", new_article_id )
    search.add_or_update_article( None, article )

    # generate the response
    extras = { "article_id": new_article_id }
    if request.args.get( "list" ):
        extras[ "authors" ] = do_get_authors()
        extras[ "scenarios" ] = do_get_scenarios()
        extras[ "tags" ] = do_get_tags()
    return make_ok_response( updated=updated, extras=extras, warnings=warnings )

def _save_authors( article, updated_fields ):
    """Save the article's authors."""

    # delete the existing article-author rows
    db.session.query( ArticleAuthor ) \
        .filter( ArticleAuthor.article_id == article.article_id ) \
        .delete()

    # add the article-author rows
    authors = request.json.get( "article_authors", [] )
    author_ids = []
    new_authors = False
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
            new_authors = True
            _logger.debug( "Created new author \"%s\": id=%d", author, author_id )
        db.session.add(
            ArticleAuthor( seq_no=seq_no, article_id=article.article_id, author_id=author_id )
        )
        author_ids.append( author_id )

    # check if we created any new authors
    if new_authors:
        # yup - let the caller know about them
        updated_fields[ "article_authors"] = author_ids

def _save_scenarios( article, updated_fields ):
    """Save the article's scenarios."""

    # delete the existing article-scenario rows
    db.session.query( ArticleScenario ) \
        .filter( ArticleScenario.article_id == article.article_id ) \
        .delete()

    # add the article-scenario rows
    scenarios = request.json.get( "article_scenarios", [] )
    scenario_ids = []
    new_scenarios = False
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
            new_scenarios = True
            _logger.debug( "Created new scenario \"%s [%s]\": id=%d", scenario[1], scenario[0], scenario_id )
        db.session.add(
            ArticleScenario( seq_no=seq_no, article_id=article.article_id, scenario_id=scenario_id )
        )
        scenario_ids.append( scenario_id )

    # check if we created any new scenarios
    if new_scenarios:
        # yup - let the caller know about them
        updated_fields[ "article_scenarios"] = scenario_ids

def _save_image( article, updated ):
    """Save the article's image."""

    # check if a new image was provided
    image_data = request.json.get( "imageData" )
    if not image_data:
        return

    # yup - delete the old one from the database
    ArticleImage.query.filter( ArticleImage.article_id == article.article_id ).delete()
    if image_data == "{remove}":
        # NOTE: The front-end sends this if it wants the article to have no image.
        updated[ "article_image_id" ] = None
        return

    # add the new image to the database
    image_data = base64.b64decode( image_data )
    fname = request.json.get( "imageFilename" )
    img = ArticleImage( article_id=article.article_id, image_filename=fname, image_data=image_data )
    db.session.add( img )
    db.session.flush()
    _logger.debug( "Created new image: %s, #bytes=%d", fname, len(image_data) )
    updated[ "article_image_id" ] = article.article_id

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
    updated = clean_request_args( vals, _FIELD_NAMES, warnings, _logger )

    # NOTE: Tags are stored in the database using \n as a separator, so we need to encode *after* cleaning them.
    cleaned_tags = clean_tags( vals.get("article_tags"), warnings )
    vals[ "article_tags" ] = encode_tags( cleaned_tags )
    if cleaned_tags != vals.get( "article_tags" ):
        updated[ "article_tags" ] = decode_tags( vals["article_tags"] )

    # update the article
    article = Article.query.get( article_id )
    if not article:
        abort( 404 )
    vals[ "time_updated" ] = datetime.datetime.now()
    apply_attrs( article, vals )
    _save_authors( article, updated )
    _save_scenarios( article, updated )
    _save_image( article, updated )
    db.session.commit()
    search.add_or_update_article( None, article )

    # generate the response
    extras = {}
    if request.args.get( "list" ):
        extras[ "authors" ] = do_get_authors()
        extras[ "scenarios" ] = do_get_scenarios()
        extras[ "tags" ] = do_get_tags()
    return make_ok_response( updated=updated, extras=extras, warnings=warnings )

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
    extras = {}
    if request.args.get( "list" ):
        extras[ "authors" ] = do_get_authors()
        extras[ "tags" ] = do_get_tags()
    return make_ok_response( extras=extras )
