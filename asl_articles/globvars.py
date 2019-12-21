""" Global variables. """

from sqlite3 import Connection as SQLite3Connection

from flask import make_response
from sqlalchemy.engine import Engine
from sqlalchemy import event

from asl_articles import app
from asl_articles.config.constants import APP_NAME, APP_VERSION

# ---------------------------------------------------------------------

def _add_cors_headers( resp ):
    """Add the necessary headers to a response to allow CORS."""
    resp.headers[ "Access-Control-Allow-Origin" ] = "*"
    resp.headers[ "Access-Control-Allow-Headers" ] = "Origin, Accept, Content-Type"
    return resp

@app.after_request
def after_request( resp ):
    """Post-process a response before it is returned to the caller."""
    return _add_cors_headers( resp )

@app.errorhandler( Exception )
def handle_error( err ):
    """Post-process an error response before it is returned to the caller."""
    orig_exc = getattr( err, "original_exception", None ) #pylint: disable=unused-variable
    try:
        resp = err.get_response()
    except AttributeError:
        resp = make_response( str(err), 500 )
    return _add_cors_headers( resp )

# ---------------------------------------------------------------------

@app.context_processor
def inject_template_params():
    """Inject template parameters into Jinja2."""
    return {
        "APP_NAME": APP_NAME,
        "APP_VERSION": APP_VERSION,
    }

@event.listens_for( Engine, "connect" )
def on_db_connect( dbapi_connection, connection_record ): #pylint: disable=unused-argument
    """Database connection callback."""
    if isinstance( dbapi_connection, SQLite3Connection ):
        # foreign keys must be enabled manually for SQLite :-/
        curs = dbapi_connection.cursor()
        curs.execute( "PRAGMA foreign_keys = ON" )
        curs.close()
