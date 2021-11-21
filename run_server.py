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
flask_host = app.config.get( "FLASK_HOST", "localhost" )
flask_port = app.config.get( "FLASK_PORT_NO", 5000 )
flask_debug = app.config.get( "FLASK_DEBUG", False )

# FUDGE! Startup can take some time (e.g. because we have to build the search index over a large database),
# and since we do that on first request, it's annoying to have started the server up, if we don't do that
# first request immediately, the server sits there idling, when it could be doing that startup initialization,
# and we then have to wait when we eventually do that first request.
# We fix this by doing the first request ourself here (something harmless).
def _force_init():
    time.sleep( 5 )
    try:
        # figure out the URL for the request we're going to make
        with app.test_request_context() as req:
            url = url_for( "ping" )
            host = req.request.host_url
        if host.endswith( "/" ):
            host = host[:-1]
        url = "{}:{}{}".format( host, flask_port, url )
        # make the request
        _ = urllib.request.urlopen( url ).read()
    except Exception as ex: #pylint: disable=broad-except
        print( "WARNING: Startup ping failed: {}".format( ex ) )
threading.Thread( target=_force_init ).start()

# run the server
if flask_debug:
    # NOTE: It's useful to run the webapp using the Flask development server, since it will
    # automatically reload itself when the source files change.
    app.run(
        host=flask_host, port=flask_port,
        debug=flask_debug,
        extra_files=extra_files
    )
else:
    import waitress
    # FUDGE! Browsers tend to send a max. of 6-8 concurrent requests per server, so we increase
    # the number of worker threads to avoid task queue warnings :-/
    nthreads = app.config.get( "WAITRESS_THREADS", 8 )
    waitress.serve( app,
        host=flask_host, port=flask_port,
        threads=nthreads
    )
