""" Helper utilities for the test suite. """

import os
import json

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql.expression
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

import asl_articles.models

_webdriver = None
_flask_app = None # nb: this may not be set (if we're talking to an existing Flask server)

# ---------------------------------------------------------------------

def init_tests( webdriver, flask_app ):
    """Prepare to run tests."""

    # initialize
    global _webdriver, _flask_app
    _webdriver = webdriver
    _flask_app = flask_app

    # load the home page
    webdriver.get( webdriver.make_url( "/" ) )
    wait_for_elem( 2, "#search-form" )

# ---------------------------------------------------------------------

def do_search( query ):
    """Run a search."""

    # get the current search seq#
    def get_seqno():
        elem = find_child( "#search-results" )
        if elem is None:
            return None
        return elem.get_attribute( "seqno" )
    curr_seqno = get_seqno()

    # submit the search query
    form = find_child( "#search-form" )
    assert form
    elem = find_child( ".query", form )
    elem.clear()
    elem.send_keys( query )
    find_child( "button[type='submit']", form ).click()

    # return the results
    wait_for( 2, lambda: get_seqno() != curr_seqno )
    return find_children( "#search-results .search-result" )

# ---------------------------------------------------------------------

def init_db( engine, fname ):
    """Load the database with test data."""

    # create a database session
    Session = sqlalchemy.orm.sessionmaker( bind=engine )
    session = Session()

    # load the test data
    dname = os.path.join( os.path.split(__file__)[0], "fixtures/" )
    fname = os.path.join( dname, fname )
    data = json.load( open( fname, "r" ) )

    # load the test data into the database
    for table_name,rows in data.items():
        model = getattr( asl_articles.models, table_name.capitalize() )
        session.query( model ).delete()
        session.bulk_insert_mappings( model, rows )
    session.commit()

    return session

# ---------------------------------------------------------------------

def wait_for( timeout, func ):
    """Wait for a condition to become true."""
    return WebDriverWait( _webdriver, timeout, 0.1 ).until(
        lambda wd: func()
    )

def wait_for_elem( timeout, elem_id, visible=True ):
    """Wait for an element to appear in the DOM."""
    func = EC.visibility_of_element_located if visible else EC.presence_of_element_located
    return WebDriverWait( _webdriver, timeout, 0.1 ).until(
        func( ( By.CSS_SELECTOR, elem_id ) )
    )

# ---------------------------------------------------------------------

def find_child( sel, parent=None ):
    """Find a child element."""
    try:
        return (parent if parent else _webdriver).find_element_by_css_selector( sel )
    except NoSuchElementException:
        return None

def find_children( sel, parent=None ):
    """Find child elements."""
    try:
        return (parent if parent else _webdriver).find_elements_by_css_selector( sel )
    except NoSuchElementException:
        return None
