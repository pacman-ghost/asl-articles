#!/usr/bin/env python3
""" Run the Flask backend server. """

import os
import threading
import urllib.request
import time
import glob

from flask import url_for

# ---------------------------------------------------------------------

# monitor extra files for changes
base_dir = os.path.abspath( os.path.join( os.path.dirname(__file__), "asl_articles" ) )
extra_files = []
for fspec in ["config","static","templates"] :
    fspec = os.path.join( base_dir, fspec )
    if os.path.isdir( fspec ):
        files = [ os.path.join(fspec,f) for f in os.listdir(fspec) ]
        files = [
            f for f in files
            if os.path.isfile(f) and os.path.splitext(f)[1] not in [".swp"]
        ]
    else:
        files = glob.glob( fspec )
    extra_files.extend( files )

# initialize
from asl_articles import app

# FUDGE! Startup can take some time (e.g. because we have to build the search index over a large database),
# and since we do that on first request, it's annoying to have started the server up, if we don't do that
# first request immediately, the server sits there idling, when it could be doing that startup initialization,
# and we then have to wait when we eventually do that first request.
# We fix this by doing the first request ourself here (something harmless).
def _force_init():
    time.sleep( 5 )
    try:
        # figoure out the URL for the request we're going to make
        with app.test_request_context() as req:
            url = url_for( "ping" )
            host = req.request.host_url
        # FUDGE! There doesn't seem to be a way to get the port number Flask is listening on :-/
        port = app.config.get( "FLASK_PORT_NO", 5000 )
        if host.endswith( "/" ):
            host = host[:-1]
        url = "{}:{}{}".format( host, port, url )
        # make the request
        _ = urllib.request.urlopen( url ).read()
    except Exception as ex: #pylint: disable=broad-except
        print( "WARNING: Startup ping failed: {}".format( ex ) )
threading.Thread( target=_force_init ).start()

# run the server
app.run(
    host = app.config.get( "FLASK_HOST", "localhost" ),
    port = app.config.get( "FLASK_PORT_NO" ),
    debug = app.config.get( "FLASK_DEBUG", False ),
    extra_files = extra_files
)
