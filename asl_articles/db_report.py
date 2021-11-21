""" Generate the database report. """

import urllib.request
import urllib.error
import hashlib
from collections import defaultdict

from flask import request, jsonify, abort

from asl_articles import app, db

# ---------------------------------------------------------------------

@app.route( "/db-report/row-counts" )
def get_db_row_counts():
    """Get the database row counts."""
    results = {}
    for table_name in [
      "publisher", "publication", "article", "author",
      "publisher_image", "publication_image", "article_image",
      "scenario"
    ]:
        query = db.engine.execute( "SELECT count(*) FROM {}".format( table_name ) )
        results[ table_name ] = query.scalar()
    return jsonify( results )

# ---------------------------------------------------------------------

@app.route( "/db-report/links" )
def get_db_links():
    """Get all links in the database."""

    # initialize
    results = {}

    def find_db_links( table_name, col_names ):
        links = []
        query = db.engine.execute( "SELECT * FROM {}".format( table_name ) )
        for row in query:
            url = row[ col_names[1] ]
            if not url:
                continue
            obj_id = row[ col_names[0] ]
            name = col_names[2]( row ) if callable( col_names[2] ) else row[ col_names[2] ]
            links.append( [ obj_id, name, url ] )
        results[ table_name ] = links

    # find all links
    find_db_links( "publisher", [
        "publ_id", "publ_url", "publ_name"
    ] )
    find_db_links( "publication", [
        "pub_id", "pub_url", _get_pub_name
    ] )
    find_db_links( "article", [
        "article_id", "article_url", "article_title"
    ] )

    return jsonify( results )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/db-report/check-link", methods=["POST"] )
def check_db_link():
    """Check if a link appears to be working."""
    url = request.args.get( "url" )
    try:
        resp = urllib.request.urlopen(
            urllib.request.Request( url, method="HEAD" )
        )
    except urllib.error.URLError as ex:
        code = getattr( ex, "code", None )
        if code:
            abort( code )
        abort( 400 )
    if resp.code != 200:
        abort( resp.code )
    return "ok"

# ---------------------------------------------------------------------

@app.route( "/db-report/images" )
def get_db_images():
    """Analyze the images stored in the database."""

    # initialize
    results = {}
    image_hashes = defaultdict( list )

    def find_images( table_name, col_names, get_name ):

        # find rows in the specified table that have images
        sql = "SELECT {cols}, image_data" \
            " FROM {table}_image LEFT JOIN {table}" \
            " ON {table}_image.{id_col} = {table}.{id_col}".format(
            cols = ",".join( "{}.{}".format( table_name, c ) for c in col_names ),
            table = table_name,
            id_col = col_names[0]
        )
        rows = [
            dict( row )
            for row in db.engine.execute( sql )
        ]

        # save the image hashes
        for row in rows:
            image_hash = hashlib.md5( row["image_data"] ).hexdigest()
            image_hashes[ image_hash ].append( [
                table_name, row[col_names[0]], get_name(row)
            ] )

        # save the image sizes
        image_sizes = [
            [ len(row["image_data"]), row[col_names[0]], get_name(row) ]
            for row in rows
        ]
        image_sizes.sort( key = lambda r: r[0], reverse=True )
        results[ table_name ] = image_sizes

    # look for images in each table
    find_images( "publisher",
        [ "publ_id", "publ_name" ],
        lambda row: row["publ_name"]
    )
    find_images( "publication",
        [ "pub_id", "pub_name", "pub_edition" ],
        _get_pub_name
    )
    find_images( "article",
        [ "article_id", "article_title" ],
        lambda row: row["article_title"]
    )

    # look for duplicate images
    results["duplicates"] = {}
    for image_hash, images in image_hashes.items():
        if len(images) == 1:
            continue
        results["duplicates"][ image_hash ] = images

    return results

# ---------------------------------------------------------------------

def _get_pub_name( row ):
    """Get a publication's display name."""
    name = row["pub_name"]
    if row["pub_edition"]:
        name += " ({})".format( row["pub_edition"] )
    return name
