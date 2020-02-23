""" Provide access to external documents. """

from flask import abort, send_from_directory

from asl_articles import app

# ---------------------------------------------------------------------

@app.route( "/docs/<path:path>" )
def get_external_doc( path ):
    """Return an external document."""
    base_dir = app.config.get( "EXTERNAL_DOCS_BASEDIR" )
    if not base_dir:
        abort( 404 )
    return send_from_directory( base_dir, path )
