""" Main handlers. """

from flask import request

from asl_articles import app

# ---------------------------------------------------------------------

@app.route( "/ping" )
def ping():
    """Let the caller know we're alive (for testing porpoises)."""
    return "pong"

# ---------------------------------------------------------------------

@app.route( "/shutdown" )
def shutdown():
    """Shutdown the server (for testing porpoises)."""
    request.environ.get( "werkzeug.server.shutdown" )()
    return ""
