#!/usr/bin/env python3
""" Run the Flask backend server. """

import os
import glob

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

# run the server
from asl_articles import app
app.run(
    host = app.config.get( "FLASK_HOST", "localhost" ),
    port = app.config.get( "FLASK_PORT_NO" ),
    debug = app.config.get( "FLASK_DEBUG", False ),
    extra_files = extra_files
)
