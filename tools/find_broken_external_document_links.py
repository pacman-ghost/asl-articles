#!/usr/bin/env python3
""" Check the database for broken external document links. """

import sys
import os
import urllib.request

import sqlalchemy
from sqlalchemy import text

# ---------------------------------------------------------------------

def main():
    """Check the database for broken external document links."""

    # parse the command line arguments
    if len(sys.argv) != 3:
        print( "Usage: {} <dbconn> <url-base>".format( os.path.split(__file__)[0] ) )
        print( "  dbconn:    database connection string e.g. \"sqlite:///~/asl-articles.db\"" )
        print( "  url-base:  Base URL for external documents e.g. http://localhost:3000/api/docs" )
        sys.exit( 0 )
    dbconn = sys.argv[1]
    url_base = sys.argv[2]

    # connect to the database
    engine = sqlalchemy.create_engine( dbconn )
    conn = engine.connect()

    def pub_name( row ):
        name = row["pub_name"]
        if row["pub_edition"]:
            name += " ({})".format( row["pub_edition"] )
        return name

    # look for broken links
    find_broken_links( conn, url_base, "publisher", [
        "publ_id", "publ_url", "publ_name"
    ] )
    find_broken_links( conn, url_base, "publication", [
        "pub_id", "pub_url", pub_name
    ] )
    find_broken_links( conn, url_base, "article", [
        "article_id", "article_url", "article_title"
    ] )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def find_broken_links( conn, url_base, table_name, col_names ):
    """Look for broken links."""

    def check_url( url, row_id, name ):

        if not url.startswith( ( "http://", "https://" ) ):
            url = os.path.join( url_base, url )
        url = url.replace( " ", "%20" ).replace( "#", "%23" )

        try:
            buf =  urllib.request.urlopen( url ).read()
        except urllib.error.HTTPError:
            buf = ""
        if not buf:
            print( "Broken link for \"{}\" (id={}): {}".format( name, row_id, url ))

    # check each row in the specified table
    query = conn.execute( text( "SELECT * FROM {}".format( table_name ) ) )
    for row in query:
        url = row[ col_names[1] ]
        if not url:
            continue
        row_id = row[ col_names[0] ]
        name = col_names[2]( row ) if callable( col_names[2] ) else row[ col_names[2] ]
        check_url( url, row_id, name )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main()
