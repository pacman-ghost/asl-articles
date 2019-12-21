""" Initialize the package. """

import os
import configparser
import logging
import logging.config

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import yaml

from asl_articles.config.constants import BASE_DIR
from asl_articles.utils import to_bool

# ---------------------------------------------------------------------

def _load_config( cfg, fname, section ):
    """Load config settings from a file."""
    if not os.path.isfile( fname ):
        return
    config_parser = configparser.ConfigParser()
    config_parser.optionxform = str # preserve case for the keys :-/
    config_parser.read( fname )
    cfg.update( dict( config_parser.items( section ) ) )

# ---------------------------------------------------------------------

# initialize
_cfg = {}

# load the application configuration
config_dir = os.path.join( BASE_DIR, "config" )
_fname = os.path.join( config_dir, "app.cfg" )
_load_config( _cfg, _fname, "System" )

# load any site configuration
_fname = os.path.join( config_dir, "site.cfg" )
_load_config( _cfg, _fname, "Site Config" )

# load any debug configuration
_fname = os.path.join( config_dir, "debug.cfg" )
_load_config( _cfg, _fname, "Debug" )

# initialize logging
_fname = os.path.join( config_dir, "logging.yaml" )
if os.path.isfile( _fname ):
    with open( _fname, "r" ) as fp:
        logging.config.dictConfig( yaml.safe_load( fp ) )
else:
    # stop Flask from logging every request :-/
    logging.getLogger( "werkzeug" ).setLevel( logging.WARNING )

# initialize Flask
base_dir = os.path.join( BASE_DIR, ".." )
app = Flask( __name__ )
app.config.update( _cfg )

# connect to the database
# NOTE: We assume that this web server will only be handling a single user. If we ever have
# multiple concurrent users, we will need to change to per-session database connections.
if _cfg.get( "IS_CONTAINER" ):
    # if we are running in a container, the database must be specified in an env variable e.g.
    #   docker run -e DBCONN=...
    _dbconn_string = os.environ.get( "DBCONN" )
else:
    _dbconn_string = app.config[ "DB_CONN_STRING" ]
app.config[ "SQLALCHEMY_DATABASE_URI" ] = _dbconn_string
app.config[ "SQLALCHEMY_TRACK_MODIFICATIONS" ] = False
app.config[ "SQLALCHEMY_ECHO" ] = to_bool( app.config.get( "SQLALCHEMY_ECHO" ) )
db = SQLAlchemy( app )

# load the application
import asl_articles.globvars #pylint: disable=cyclic-import
import asl_articles.main #pylint: disable=cyclic-import
import asl_articles.search #pylint: disable=cyclic-import
import asl_articles.publishers #pylint: disable=cyclic-import
import asl_articles.publications #pylint: disable=cyclic-import
import asl_articles.articles #pylint: disable=cyclic-import
import asl_articles.authors #pylint: disable=cyclic-import
import asl_articles.scenarios #pylint: disable=cyclic-import
import asl_articles.images #pylint: disable=cyclic-import
import asl_articles.tags #pylint: disable=cyclic-import
import asl_articles.utils #pylint: disable=cyclic-import

# initialize
asl_articles.utils.load_html_whitelists( app )
