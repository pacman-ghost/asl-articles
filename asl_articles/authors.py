""" Handle author requests. """

from flask import jsonify

from asl_articles import app
from asl_articles.models import Author

# ---------------------------------------------------------------------

@app.route( "/authors" )
def get_authors():
    """Get all authors."""
    return jsonify( do_get_authors() )

def do_get_authors():
    """Get all authors."""

    # get all the authors
    return {
        r.author_id: _get_author_vals(r)
        for r in Author.query #pylint: disable=not-an-iterable
    }

def _get_author_vals( author ):
    """Extract public fields from an Author record."""
    return {
        "author_id": author.author_id,
        "author_name": author.author_name
    }
