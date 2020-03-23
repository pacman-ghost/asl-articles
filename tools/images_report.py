#!/usr/bin/env python3
""" Geenrate a report on images in the database. """

import sys
import os
import hashlib
from collections import defaultdict

import sqlalchemy
from sqlalchemy import text

# ---------------------------------------------------------------------

def main():
    """Report on images in the database."""

    # parse the command line arguments
    if len(sys.argv) != 2:
        print( "Usage: {} <dbconn> <url-base>".format( os.path.split(__file__)[0] ) )
        print( "  dbconn:  database connection string e.g. \"sqlite:///~/asl-articles.db\"" )
        sys.exit( 0 )
    dbconn = sys.argv[1]

    # connect to the database
    engine = sqlalchemy.create_engine( dbconn )
    conn = engine.connect()

    # initialize
    image_hashes = defaultdict( list )

    def find_images( conn, table_name, col_names, get_name ):

        # find rows in the specified table that have images
        sql = "SELECT {cols}, image_data" \
            " FROM {table}_image LEFT JOIN {table}" \
            " ON {table}_image.{id_col} = {table}.{id_col}".format(
            cols = ",".join( "{}.{}".format( table_name, c ) for c in col_names ),
            table=table_name, id_col=col_names[0]
        )
        rows = [ dict(row) for row in conn.execute( text( sql ) ) ]

        # save the image hashes
        for row in rows:
            image_hash = hashlib.md5( row["image_data"] ).hexdigest()
            name = get_name( row )
            image_hashes[ image_hash ].append( name )

        # output the results
        rows = [
            [ len(row["image_data"]), row[col_names[0]], get_name(row) ]
            for row in rows
        ]
        rows.sort( key = lambda r: r[0], reverse=True )
        print( "=== {}s ({}) ===".format( table_name, len(rows) ) )
        print()
        print( "{:>6}   {:>5}".format( "size", "ID" ) )
        for row in rows:
            print( "{:-6.1f} | {:5} | {}".format( row[0]/1024, row[1], row[2] ) )
        print()

    def get_pub_name( row ):
        name = row["pub_name"]
        if row["pub_edition"]:
            name += " ({})".format( row["pub_edition"] )
        return name

    # look for images in each table
    find_images( conn, "publisher",
        [ "publ_id", "publ_name" ],
        lambda r: r["publ_name"]
    )
    find_images( conn, "publication",
        [ "pub_id", "pub_name", "pub_edition" ],
        get_pub_name
    )
    find_images( conn, "article",
        [ "article_id", "article_title" ],
        lambda r: r["article_title"]
    )

    # report on any duplicate images
    for image_hash,images in image_hashes.items():
        if len(images) == 1:
            continue
        print( "Found duplicate images ({}):".format( image_hash ) )
        for image in images:
            print( "- {}".format( image ) )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main()
