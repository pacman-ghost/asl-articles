""" Provide access to external documents. """

import os

from flask import abort, send_from_directory

from asl_articles import app

# ---------------------------------------------------------------------

@app.route( "/docs/<path:path>" )
def get_external_doc( path ):
    """Return an external document."""
    base_dir = app.config.get( "EXTERNAL_DOCS_BASEDIR" )
    if not base_dir:
        abort( 404, "EXTERNAL_DOCS_BASEDIR not configured." )
    fname = os.path.join( base_dir, path )
    if not os.path.isfile( fname ):
        if app.config["_IS_CONTAINER"]:
            fname = os.path.join( os.environ["EXTERNAL_DOCS_BASEDIR"], path )
        abort( 404, "Can't find file: {}".format( fname ) )
    return send_from_directory( base_dir, path )
