""" Helper utilities for the test suite. """

import os
import json
import uuid

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql.expression
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

import asl_articles.models

_webdriver = None
_flask_app = None # nb: this may not be set (if we're talking to an existing Flask server)

# ---------------------------------------------------------------------

def init_tests( webdriver, flask_app, dbconn, fixtures_fname=None ):
    """Prepare to run tests."""

    # initialize
    global _webdriver, _flask_app
    _webdriver = webdriver
    _flask_app = flask_app

    # initialize the database
    if dbconn:
        init_db( dbconn, fixtures_fname )
    else:
        assert fixtures_fname is None

    # load the home page
    webdriver.get( webdriver.make_url( "/" ) )
    wait_for_elem( 2, "#search-form" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def init_db( dbconn, fixtures_fname ):
    """Load the database with test data."""

    # create a database session
    Session = sqlalchemy.orm.sessionmaker( bind=dbconn )
    session = Session()

    # load the test data
    if fixtures_fname:
        dname = os.path.join( os.path.split(__file__)[0], "fixtures/" )
        fname = os.path.join( dname, fixtures_fname )
        data = json.load( open( fname, "r" ) )
    else:
        data = {}

    # load the test data into the database
    for table_name in ["publisher","publication","article"]:
        model = getattr( asl_articles.models, table_name.capitalize() )
        session.query( model ).delete()
        if table_name in data:
            session.bulk_insert_mappings( model, data[table_name] )
    session.commit()

    return session

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
    # FUDGE! Calling elem.clear() then send_keys(query) has a weird effect in Chromium if the query
    # is empty. The previous query gets repeated instead - is the browser auto-filling the field?
    actions = ActionChains( _webdriver ).move_to_element( elem ).click() \
        .key_down( Keys.CONTROL ).send_keys( "a" ).key_up( Keys.CONTROL ) \
        .send_keys( Keys.DELETE )
    if query:
        actions = actions.send_keys( query )
    actions.perform()
    find_child( "button[type='submit']", form ).click()

    # return the results
    wait_for( 2, lambda: get_seqno() != curr_seqno )
    return find_children( "#search-results .search-result" )

def get_result_names( results ):
    """Get the names from a list of search results."""
    return [
        find_child( ".name", r ).text
        for r in results
    ]

# ---------------------------------------------------------------------

def wait_for( timeout, func ):
    """Wait for a condition to become true."""
    return WebDriverWait( _webdriver, timeout, 0.1 ).until(
        lambda wd: func()
    )

def wait_for_elem( timeout, sel, visible=True ):
    """Wait for an element to appear in the DOM."""
    func = EC.visibility_of_element_located if visible else EC.presence_of_element_located
    return WebDriverWait( _webdriver, timeout, 0.1 ).until(
        func( ( By.CSS_SELECTOR, sel ) )
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

# ---------------------------------------------------------------------

def get_stored_msg( msg_id ):
    """Get a message stored for us by the front-end."""
    elem = find_child( _make_stored_msg_elem_id( msg_id ), _webdriver )
    assert elem.tag_name == "textarea"
    return elem.get_attribute( "value" )

def set_stored_msg( msg_id, val ):
    """Set a message for the front-end."""
    elem = find_child( _make_stored_msg_elem_id( msg_id ), _webdriver )
    assert elem.tag_name == "textarea"
    _webdriver.execute_script( "arguments[0].value = arguments[1]", elem, val )

def set_stored_msg_marker( msg_id ):
    """Store something in the message buffer (so we can tell if the front-end changes it)."""
    marker = "marker:{}:{}".format( msg_id, uuid.uuid4() )
    set_stored_msg( msg_id, marker )
    return marker

def _make_stored_msg_elem_id( msg_id ):
    return "#_stored_msg-{}_".format( msg_id )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

_TOAST_TYPES = [ "info", "warning", "error" ]

def get_toast( toast_type ):
    """Get a toast message stored for us by the front-end."""
    buf = get_stored_msg( _make_toast_stored_msg_id( toast_type ) )
    if buf.startswith( "<div>" ) and buf.endswith( "</div>" ):
        buf = buf[5:-6].strip()
    return buf

def set_toast_marker( toast_type, clear_others=True ):
    """Store marker text in the toast message buffer."""
    marker = None
    for t in _TOAST_TYPES:
        msg_id = _make_toast_stored_msg_id( t )
        if t == toast_type:
            # set the specified stored message marker
            marker = set_stored_msg_marker( msg_id )
        else:
            if clear_others:
                # clear all other stored messages
                set_stored_msg( msg_id, "" )
    assert marker
    return marker

def check_toast( toast_type, expected, contains=False, check_others=True ):
    """Check the contents of a stored toast message."""
    rc = None
    for t in _TOAST_TYPES:
        if t == toast_type:
            # check the specified toast message
            rc = check_string( get_toast(t), expected, contains=contains )
        else:
            # check that all other toast messages have not been set
            if check_others:
                assert get_toast( t ) == ""
    assert rc is not None
    return rc

def _make_toast_stored_msg_id( toast_type ):
    return "{}_toast".format( toast_type )

# ---------------------------------------------------------------------

class ReactSelect:
    """Control a react-select droplist."""
    def __init__( self, elem ):
        self.select = elem
    def select_by_name( self, val ):
        """Select an option by name."""
        find_child( "svg", self.select ).click()
        options = [ e for e in find_children( ".react-select__option", self.select )
            if e.text == val
        ]
        assert len( options ) == 1
        options[0].click()

# ---------------------------------------------------------------------

def set_elem_text( elem, val ):
    """Set the text for an element."""
    elem.clear()
    elem.send_keys( val )

def check_ask_dialog( expected, click_on ):
    """Check that the ASK dialog is being shown, and its contents."""
    # check the ASK dialog
    elem = wait_for_elem( 2, "#ask .MuiPaper-root" )
    buf = elem.get_attribute( "innerHTML" )
    for e in [expected] if isinstance(expected,str) else expected:
        assert e in buf
    # dismiss the dialog
    if click_on:
        find_child( "button.{}".format( click_on ), elem ).click()
        wait_for( 2, lambda: find_child( "#ask" ) is None )

def check_error_msg( expected ):
    """Check that an error dialog is being shown, and its contents."""
    check_ask_dialog( expected, None )
    # check that the error icon is shown
    elem = find_child( "#ask img.icon" )
    assert elem.get_attribute( "src" ).endswith( "/error.png" )
    find_child( "#ask .MuiDialogActions-root button.ok" ).click()
    wait_for( 2, lambda: find_child( "#ask" ) is None )

def check_string( val, expected, contains=False ):
    """Compare a value with its expected value."""
    if contains:
        return expected in val
    return val == expected
