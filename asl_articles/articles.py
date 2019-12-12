""" Handle article requests. """

import datetime
import logging

from flask import request, jsonify, abort

from asl_articles import app, db
from asl_articles.models import Article, Author, ArticleAuthor
from asl_articles.authors import do_get_authors
from asl_articles.tags import do_get_tags
from asl_articles.utils import get_request_args, clean_request_args, encode_tags, decode_tags, apply_attrs, \
    make_ok_response

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

def get_article_vals( article ):
    """Extract public fields from an Article record."""
    authors = sorted( article.article_authors,
        key = lambda a: a.seq_no
    )
    return {
        "article_id": article.article_id,
        "article_title": article.article_title,
        "article_subtitle": article.article_subtitle,
        "article_authors": [ a.author_id for a in authors ],
        "article_snippet": article.article_snippet,
        "article_url": article.article_url,
        "article_tags": decode_tags( article.article_tags ),
        "pub_id": article.pub_id,
    }

# ---------------------------------------------------------------------

@app.route( "/article/create", methods=["POST"] )
def create_article():
    """Create an article."""

    # parse the input
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Create article:" )
    )
    vals[ "article_tags" ] = encode_tags( vals.get( "article_tags" ) )
    warnings = []
    updated = clean_request_args( vals, _FIELD_NAMES, warnings, _logger )

    # create the new article
    vals[ "time_created" ] = datetime.datetime.now()
    article = Article( **vals )
    db.session.add( article ) #pylint: disable=no-member
    db.session.flush() #pylint: disable=no-member
    new_article_id = article.article_id
    _save_authors( article, updated )
    db.session.commit() #pylint: disable=no-member
    _logger.debug( "- New ID: %d", new_article_id )

    # generate the response
    extras = { "article_id": new_article_id }
    if request.args.get( "list" ):
        extras[ "authors" ] = do_get_authors()
        extras[ "tags" ] = do_get_tags()
    return make_ok_response( updated=updated, extras=extras, warnings=warnings )

def _save_authors( article, updated_fields ):
    """Save the article's authors."""

    # delete the existing article-author rows
    query = db.session.query( ArticleAuthor ) #pylint: disable=no-member
    query.filter( ArticleAuthor.article_id == article.article_id ).delete()

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
            assert isinstance( author, str )
            author = Author( author_name=author )
            db.session.add( author ) #pylint: disable=no-member
            db.session.flush() #pylint: disable=no-member
            author_id = author.author_id
            new_authors = True
            _logger.debug( "Created new author \"%s\": id=%d", author, author_id )
        db.session.add( #pylint: disable=no-member
            ArticleAuthor( seq_no=seq_no, article_id=article.article_id, author_id=author_id )
        )
        author_ids.append( author_id )

    # check if we created any new authors
    if new_authors:
        # yup - let the caller know about them
        updated_fields[ "article_authors"] = author_ids

# ---------------------------------------------------------------------

@app.route( "/article/update", methods=["POST"] )
def update_article():
    """Update an article."""

    # parse the input
    article_id = request.json[ "article_id" ]
    vals = get_request_args( request.json, _FIELD_NAMES,
        log = ( _logger, "Update article: id={}".format( article_id ) )
    )
    vals[ "article_tags" ] = encode_tags( vals.get( "article_tags" ) )
    warnings = []
    updated = clean_request_args( vals, _FIELD_NAMES, warnings, _logger )

    # update the article
    article = Article.query.get( article_id )
    if not article:
        abort( 404 )
    _save_authors( article, updated )
    vals[ "time_updated" ] = datetime.datetime.now()
    apply_attrs( article, vals )
    db.session.commit() #pylint: disable=no-member

    # generate the response
    extras = {}
    if request.args.get( "list" ):
        extras[ "authors" ] = do_get_authors()
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
    db.session.delete( article ) #pylint: disable=no-member
    db.session.commit() #pylint: disable=no-member

    # generate the response
    extras = {}
    if request.args.get( "list" ):
        extras[ "authors" ] = do_get_authors()
        extras[ "tags" ] = do_get_tags()
    return make_ok_response( extras=extras )
