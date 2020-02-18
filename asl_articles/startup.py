""" Manage the startup process. """

from flask import jsonify

from asl_articles import app

_startup_msgs = {
    "info": [],
    "warning": [],
    "error": []
}

# ---------------------------------------------------------------------

@app.route( "/startup-messages" )
def get_startup_msgs():
    """Return any messages logged during startup."""
    return jsonify( _startup_msgs )

def log_startup_msg( msg_type, msg, *args, **kwargs ):
    """Log a startup message."""
    _startup_msgs[ msg_type ].append( msg.format( *args, **kwargs ) )
