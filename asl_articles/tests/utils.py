""" Helper utilities for the test suite. """

import os
import json
import uuid
import logging

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql.expression
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException

from asl_articles import search
from asl_articles.utils import to_bool
import asl_articles.models

_webdriver = None
_flask_app = None # nb: this may not be set (if we're talking to an existing Flask server)

# ---------------------------------------------------------------------

def init_tests( webdriver, flask_app, dbconn, **kwargs ):
    """Prepare to run tests."""

    # initialize
    global _webdriver, _flask_app
    _webdriver = webdriver
    _flask_app = flask_app

    # initialize the database
    fixtures = kwargs.pop( "fixtures", None )
    if dbconn:
        Session = sqlalchemy.orm.sessionmaker( bind=dbconn )
        session = Session()
        load_fixtures( session, fixtures )
    else:
        assert fixtures is None
        session = None

    # never highlight search results unless explicitly enabled
    if "no_sr_hilite" not in kwargs:
        kwargs[ "no_sr_hilite" ] = 1

    # load the home page
    if webdriver:
        if not to_bool( kwargs.pop( "enable_constraints", False ) ):
            kwargs[ "disable_constraints" ] = 1
        webdriver.get( webdriver.make_url( "/", **kwargs ) )
        wait_for_elem( 2, "#search-form" )

    return session

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def load_fixtures( session, fname ):
    """Load fixtures into the database."""

    # load the fixtures
    if fname:
        dname = os.path.join( os.path.split(__file__)[0], "fixtures/" )
        fname = os.path.join( dname, fname )
        data = json.load( open( fname, "r" ) )
    else:
        data = {}

    # save the fixture data in the database
    table_names = [ "publisher", "publication", "article" ]
    table_names.extend( [ "author", "article_author" ] )
    table_names.extend( [ "publisher_image", "publication_image", "article_image" ] )
    table_names.extend( [ "scenario", "article_scenario" ] )
    for table_name in table_names:
        model = asl_articles.models.get_model_from_table_name( table_name )
        session.query( model ).delete()
        if table_name in data:
            session.bulk_insert_mappings( model, data[table_name] )
    session.commit()

    # rebuild the search index
    search.init_search( session, logging.getLogger("search") )

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
    return get_search_results()

def get_search_results():
    """Get the search results."""
    return find_children( "#search-results .search-result" )

def get_search_result_names( results=None ):
    """Get the names from the search results."""
    if not results:
        results = get_search_results()
    return [ find_child( ".name", r ).text for r in results ]

def find_search_result( name, results=None ):
    """Find a search result."""
    if not results:
        results = get_search_results()
    results = [ r for r in results if find_child( ".name", r ).text == name ]
    assert len(results) == 1
    return results[0]

def check_search_result( sr, check, expected ):
    """Check a search result in the UI."""

    # figure out which search result to check
    if not sr:
        # NOTE: If the caller doesn't explicitly provide a search result, we assume we're working with
        # a single search result that is already on-screen.
        results = get_search_results()
        assert len(results) == 1
        sr = results[0]
    elif isinstance( sr, str ):
        sr = find_search_result( sr )
    else:
        assert isinstance( sr, WebElement )

    # wait for the search result to match what we expect
    def check_sr():
        try:
            if check( sr, expected ):
                return sr
            return None
        except StaleElementReferenceException:
            return None # nb: the web page updated while we were checking it
    return wait_for( 2, check_sr )

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

def wait_for_not_elem( timeout, sel ):
    """Wait for an element to be removed from the DOM."""
    return WebDriverWait( _webdriver, timeout, 0.1 ).until(
        EC.invisibility_of_element_located( ( By.CSS_SELECTOR, sel ) )
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

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def send_upload_data( data, func ):
    """Send data to the front-end, to simulate uploading a file.

    Because Selenium can't control a browser's native "open file" dialog, we need a different mechanism
    to test features that require uploading a file. We store the data we want to upload as a base64-encoded
    string in a hidden textarea, and the front-end Javascript loads it from there.
    """
    # send the data to the front-end
    set_stored_msg( "upload", data )
    func() # nb: the caller must initiate the upload process
    # wait for the front-end to acknowledge receipt of the data
    wait_for( 2, lambda: get_stored_msg("upload") == "" )

# ---------------------------------------------------------------------

def select_sr_menu_option( sr, menu_id ):
    """Select an option from a search result's menu."""
    _do_select_menu_option( find_child("button.sr-menu",sr), "."+menu_id )

def select_main_menu_option( menu_id ):
    """Select an option from the main application menu."""
    _do_select_menu_option( find_child("#menu-button--app"), "#menu-"+menu_id )

def _do_select_menu_option( menu, sel ):
    """Select an option from a dropdown menu."""
    for _ in range(0,5):
        # FUDGE! This is very weird, clicking on the menu button doesn't always register?!?
        menu.click()
        portal = None
        try:
            portal = wait_for_elem( 1, "reach-portal" )
        except TimeoutException:
            continue
        assert portal
        # FUDGE! Also very weird, the menu seems to occasionally close up by itself (especially when running headless).
        try:
            find_child( sel, portal ).click()
            return
        except StaleElementReferenceException:
            continue
    assert False, "Couldn't select menu option: {}".format( sel )

# ---------------------------------------------------------------------

# FUDGE! We can't use prepared statements here, since the syntax is different for SQLite and Postgres :-/

def get_publisher_row( dbconn, publ_id, fields ):
    """Get a row from the publisher table."""
    assert publ_id
    return dbconn.execute(
        "SELECT {} FROM publisher WHERE publ_id={}".format(
            ",".join(fields), publ_id
        )
    ).fetchone()

def get_publication_row( dbconn, pub_id, fields ):
    """Get a row from the publication table."""
    assert pub_id
    return dbconn.execute(
        "SELECT {} FROM publication WHERE pub_id={}".format(
            ",".join(fields), pub_id
        )
    ).fetchone()

def get_article_row( dbconn, article_id, fields ):
    """Get a row from the article table."""
    assert article_id
    return dbconn.execute(
        "SELECT {} FROM article WHERE article_id={}".format(
            ",".join(fields), article_id
        )
    ).fetchone()

# ---------------------------------------------------------------------

def change_image( elem, image_data ):
    """Click on an image to change it."""
    # NOTE: This is a bit tricky since we started overlaying the image with the "remove image" icon :-/
    send_upload_data( image_data,
        lambda: ActionChains( _webdriver ) \
                .move_to_element_with_offset( elem, 1, 1 ) \
                .click().perform()
    )

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

def check_constraint_warnings( expected_caption, expected_constraints, click_on ):
    """Check that a constraints warning dialog is being shown, and its contents."""
    dlg = find_child( "#ask" )
    assert find_child( ".caption", dlg ).text == expected_caption
    constraints = [ c.text for c in find_children( ".constraint", dlg ) ]
    assert set( constraints ) == set( expected_constraints )
    find_child( ".MuiDialogActions-root button.{}".format( click_on ), dlg ).click()

def check_string( val, expected, contains=False ):
    """Compare a value with its expected value."""
    if contains:
        return expected in val
    return val == expected
