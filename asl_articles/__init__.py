""" Initialize the package. """

import os
import configparser
import logging
import logging.config

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
import yaml

from asl_articles.config.constants import BASE_DIR
from asl_articles.utils import to_bool

_disable_db_startup = False

# ---------------------------------------------------------------------

def _on_startup():
    """Do startup initialization."""

    if not _disable_db_startup:

        # check if we have a working database connection
        if _dbconn_string.startswith( "sqlite:///" ):
            # NOTE: If the SQLite database is not there, a zero-byte file will be created the first time
            # we try to use it, so we can't use the normal check we use below for other databases.
            # NOTE: We could automatically set up a new database file and install the schema into it,
            # but that's probably more trouble than it's worth, and possibly a cause of problems in itself :-/
            fname = _dbconn_string[10:]
            if not os.path.isfile( fname ):
                asl_articles.startup.log_startup_msg( "error", "Missing SQLite database:\n{}", fname )
                return
        else:
            try:
                db.session.execute( "SELECT 1" )
            except SQLAlchemyError as ex:
                asl_articles.startup.log_startup_msg( "error", "Can't connect to the database:\n{}", ex )
                return

        # initialize the search index
        _logger = logging.getLogger( "startup" )
        asl_articles.search.init_search( db.session, _logger )

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

# initialize the database connection
app.config[ "_IS_CONTAINER" ] = _cfg.get( "IS_CONTAINER" )
if _cfg.get( "IS_CONTAINER" ):
    # if we are running in a container, the database must be specified in an env variable e.g.
    #   docker run -e DBCONN=...
    _dbconn_string = os.environ.get( "DBCONN" )
else:
    _dbconn_string = app.config.get( "DB_CONN_STRING" )
app.config[ "SQLALCHEMY_DATABASE_URI" ] = _dbconn_string
app.config[ "SQLALCHEMY_TRACK_MODIFICATIONS" ] = False
app.config[ "SQLALCHEMY_ECHO" ] = to_bool( app.config.get( "SQLALCHEMY_ECHO" ) )
db = SQLAlchemy( app )

# load the application
import asl_articles.globvars #pylint: disable=cyclic-import
import asl_articles.startup #pylint: disable=cyclic-import
import asl_articles.main #pylint: disable=cyclic-import
import asl_articles.search #pylint: disable=cyclic-import
import asl_articles.publishers #pylint: disable=cyclic-import
import asl_articles.publications #pylint: disable=cyclic-import
import asl_articles.articles #pylint: disable=cyclic-import
import asl_articles.authors #pylint: disable=cyclic-import
import asl_articles.scenarios #pylint: disable=cyclic-import
import asl_articles.images #pylint: disable=cyclic-import
import asl_articles.tags #pylint: disable=cyclic-import
import asl_articles.docs #pylint: disable=cyclic-import
import asl_articles.db_report #pylint: disable=cyclic-import
import asl_articles.utils #pylint: disable=cyclic-import

# initialize
asl_articles.utils.load_html_whitelists( app )

# register startup initialization
app.before_first_request( _on_startup )
