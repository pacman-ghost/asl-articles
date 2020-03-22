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

# ---------------------------------------------------------------------

@app.route( "/user-files/<path:path>" )
def get_user_file( path ):
    """Return a user-defined file."""
    base_dir = app.config.get( "USER_FILES_BASEDIR" )
    if not base_dir:
        abort( 404, "USER_FILES_BASEDIR not configured." )
    fname = os.path.join( base_dir, path )
    if not os.path.isfile( fname ):
        if app.config["_IS_CONTAINER"]:
            fname = os.path.join( os.environ["USER_FILES_BASEDIR"], path )
        abort( 404, "Can't find file: {}".format( fname ) )
    return send_from_directory( base_dir, path )
