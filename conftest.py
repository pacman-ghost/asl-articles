""" pytest support functions. """

import os
import threading
import tempfile
import urllib.request
import urllib.parse
from urllib.error import URLError

import pytest
import flask
import sqlalchemy
from flask_sqlalchemy import SQLAlchemy
import alembic
import alembic.config

import asl_articles
from asl_articles import app
from asl_articles.utils import to_bool
from asl_articles.tests import utils

_FLASK_SERVER_URL = ( "localhost", 5001 ) # nb: for the test Flask server we spin up

# ---------------------------------------------------------------------

def pytest_addoption( parser ):
    """Configure pytest options."""

    # NOTE: This file needs to be in the project root for this to work :-/
    #   https://docs.pytest.org/en/latest/reference.html#initialization-hooks

    # add test options
    parser.addoption(
        # NOTE: We assume that the React frontend server is already running.
        "--web-url", action="store", dest="web_url", default="http://localhost:3000",
        help="React server to test against."
    )
    parser.addoption(
        "--flask-url", action="store", dest="flask_url", default=None,
        help="Flask server to test against."
    )
    parser.addoption(
        "--webdriver", action="store", dest="webdriver", default="chrome",
        help="Webdriver to use (chrome|firefox)."
    )

    # add test options
    parser.addoption(
        "--headless", action="store_true", dest="headless", default=False,
        help="Run the tests headless."
    )
    parser.addoption(
        "--window", action="store", dest="window_size", default="1000x700",
        help="Browser window size."
    )

    # add test options
    parser.addoption(
        "--dbconn", action="store", dest="dbconn", default=None,
        help="Database connection string."
    )

# ---------------------------------------------------------------------

@pytest.fixture( scope="session" )
def flask_app( request ):
    """Prepare the Flask server."""

    # initialize
    flask_url = request.config.getoption( "--flask-url" ) #pylint: disable=no-member

    # initialize
    # WTF?! https://github.com/pallets/flask/issues/824
    def make_flask_url( endpoint, **kwargs ):
        """Generate a URL for the Flask backend server."""
        with app.test_request_context():
            url = flask.url_for( endpoint, _external=True, **kwargs )
            if flask_url:
                url = url.replace( "http://localhost", flask_url )
            else:
                url = url.replace( "localhost/", "{}:{}/".format(*_FLASK_SERVER_URL) )
            return url
    app.url_for = make_flask_url

    # check if we need to start a local Flask server
    if not flask_url:
        # yup - make it so
        thread = threading.Thread(
            target = lambda: app.run(
                host=_FLASK_SERVER_URL[0], port=_FLASK_SERVER_URL[1],
                use_reloader=False
            )
        )
        thread.start()
        # wait for the server to start up
        def is_ready():
            """Try to connect to the Flask server."""
            try:
                resp = urllib.request.urlopen( app.url_for( "ping" ) ).read()
                assert resp == b"pong"
                return True
            except URLError:
                return False
            except Exception as ex: #pylint: disable=broad-except
                assert False, "Unexpected exception: {}".format( ex )
        utils.wait_for( 5, is_ready )

    # return the server to the caller
    try:
        yield app
    finally:
        # shutdown the local Flask server
        if not flask_url:
            urllib.request.urlopen( app.url_for("shutdown") ).read()
            thread.join()

# ---------------------------------------------------------------------

@pytest.fixture( scope="session" )
def webdriver( request ):
    """Prepare a webdriver that can be used to control a browser."""

    # initialize
    driver = request.config.getoption( "--webdriver" )
    headless = request.config.getoption( "--headless" )
    from selenium import webdriver as wb #pylint: disable=import-outside-toplevel
    if driver == "firefox":
        options = wb.FirefoxOptions()
        if headless:
            options.add_argument( "--headless" ) #pylint: disable=no-member
        driver = wb.Firefox(
            options = options,
            service_log_path = os.path.join( tempfile.gettempdir(), "geckodriver.log" )
        )
    elif driver == "chrome":
        options = wb.ChromeOptions()
        if headless:
            options.add_argument( "--headless" ) #pylint: disable=no-member
        driver = wb.Chrome( options=options )
    else:
        raise RuntimeError( "Unknown webdriver: {}".format( driver ) )

    # set the browser size
    window_size = request.config.getoption( "--window" )
    if window_size:
        words = window_size.split( "x" ) #pylint: disable=no-member
        driver.set_window_size( int(words[0]), int(words[1]) )

    # figure out which Flask backend server the React frontend should talk to
    flask_url = request.config.getoption( "--flask-url" )
    if not flask_url:
        # we're talking to our own test Flask server
        flask_url = "http://{}:{}".format( *_FLASK_SERVER_URL )

    # initialize
    web_url = request.config.getoption( "--web-url" )
    assert web_url
    def make_web_url( url ):
        """Generate a URL for the React frontend."""
        url = "{}/{}".format( web_url, url )
        url += "&" if "?" in url else "?"
        url += urllib.parse.urlencode( { "_flask": flask_url } )
        return url
    driver.make_url = make_web_url

    # return the webdriver to the caller
    try:
        yield driver
    finally:
        driver.quit()

# ---------------------------------------------------------------------

@pytest.fixture( scope="function" )
def dbconn( request ):
    """Prepare a database connection."""

    # initialize
    conn_string = request.config.getoption( "--dbconn" )
    temp_fname = None
    if conn_string:
        if os.path.isfile( conn_string ):
            # a file was specified - we assume it's an SQLite database
            conn_string = "sqlite:///{}".format( conn_string )
    else:
        # create a temp file and install our database schema into it
        with tempfile.NamedTemporaryFile( delete=False ) as temp_file:
            temp_fname = temp_file.name
        dname = os.path.join( os.path.split(__file__)[0], "alembic/" )
        cfg = alembic.config.Config( os.path.join( dname, "alembic.ini" ) )
        cfg.set_main_option( "script_location", dname )
        conn_string = "sqlite:///{}".format( temp_fname )
        cfg.set_main_option( "sqlalchemy.url", conn_string )
        alembic.command.upgrade( cfg, "head" )

    # connect to the database
    engine = sqlalchemy.create_engine( conn_string,
        echo = to_bool( app.config.get( "SQLALCHEMY_ECHO" ) )
    )

    # IMPORTANT! The test suite often loads the database with test data, and then runs searches to see what happens.
    # In the normal case, this works fine:
    # - we use either an existing database, or create a temp file as an sqlite database (see above)
    # - this database is then installed into the temp Flask server that the "flask_app" fixture spun up, thus ensuring
    #   that both the backend server and test code are working with the same database.
    # However, this doesn't work when the test suite is talking to a remote Flask server (via the --flask-url argument),
    # since it has no way of ensuring that the remote Flask server is talking to the same database. In this case,
    # it's the developer's responsibility to make sure that this is the case (by configuring the database in site.cfg).

    prev_db_state = None
    try:
        flask_url = request.config.getoption( "--flask-url" ) #pylint: disable=no-member
        if flask_url:
            # we are talking to a remote Flask server, we assume it's already talking to the database we are
            pass
        else:
            # remember the database our temp Flask server is currently using
            prev_db_state = ( app.config["SQLALCHEMY_DATABASE_URI"], asl_articles.db )
            # replace the database the temp Flask server with ours
            app.config[ "SQLALCHEMY_DATABASE_URI" ] = conn_string
            app.db = SQLAlchemy( app )
        # return the database connection to the caller
        yield engine
    finally:
        # restore the original database into our temp Flask server
        if prev_db_state:
            app.config[ "SQLALCHEMY_DATABASE_URI" ] = prev_db_state[0]
            asl_articles.db = prev_db_state[1]
        # clean up
        if temp_fname:
            os.unlink( temp_fname )
