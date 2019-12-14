""" Handle tag requests. """

from collections import defaultdict

from flask import jsonify

from asl_articles import app, db
from asl_articles.models import Publication, Article

# ---------------------------------------------------------------------

@app.route( "/tags" )
def get_tags():
    """Get all tags."""
    return jsonify( do_get_tags() )

def do_get_tags():
    """Get all tags."""

    # get all the tags
    # NOTE: This is pretty inefficient, since an article/publication's tags are munged into one big string
    # and stored in a single column, so we need to manually unpack everything, but we'll see how it goes...
    tags = defaultdict( int )
    def count_tags( query ):
        for row in query:
            if not row[0]:
                continue
            for tag in row[0].split( ";" ):
                tags[ tag ] = tags[ tag ] + 1
    count_tags( db.session.query( Publication.pub_tags ) )
    count_tags( db.session.query( Article.article_tags ) )

    # sort the results
    tags = sorted( tags.items(),
        key = lambda v: ( -v[1], v[0] ) # sort by # instances, then name
    )

    return tags
