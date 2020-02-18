""" Helper utilities for the test suite. """

import os
import json
import itertools
import uuid
import base64
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
        if to_bool( kwargs.pop( "disable_constraints", True ) ):
            kwargs[ "disable_constraints" ] = 1
        if to_bool( kwargs.pop( "disable_confirm_discard_changes", True ) ):
            kwargs[ "disable_confirm_discard_changes" ] = 1
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

    # submit the search query
    curr_seqno = get_search_seqno()
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
    wait_for( 2, lambda: get_search_seqno() != curr_seqno )
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

def get_search_seqno():
    """Get the current search seq#."""
    elem = find_child( "#search-results" )
    if not elem:
        return None
    return elem.get_attribute( "seqno" )

# ---------------------------------------------------------------------

def do_test_confirm_discard_changes( menu_id, update_fields=None ): #pylint: disable=too-many-statements
    """Test confirmation of discarding changes made to a dialog."""

    # initialize
    image_fname = os.path.join( os.path.split(__file__)[0], "fixtures/images/1.gif" )

    def get_input_fields( dlg ):
        input_fields = itertools.chain(
            find_children( "input", dlg ),
            find_children( "textarea", dlg )
        )
        input_fields = { get_field_id(f): f for f in input_fields if f.is_displayed() }
        # NOTE: Publishers, publications and articles all have an image, but requires special handling.
        input_fields[ "image" ] = None
        return input_fields
    def get_field_id( elem ):
        if elem.get_attribute( "class" ) == "edition":
            # FUDGE! The publication dialog has a row with two fields ("name" and "edition").
            # We return the "edition" field, the "name" field is handled as a ReactSelect.
            return "edition"
        if elem.get_attribute( "class" ) == "pageno":
            # FUDGE! The article dialog has a row with two fields ("publication" and "pageno").
            # We return the "pageno" field, the "publication" field is handled as a ReactSelect.
            return "pageno"
        elem = find_parent_by_class( elem, "row" )
        classes = set( elem.get_attribute( "class" ).split() )
        classes.remove( "row" )
        assert len(classes) == 1
        return classes.pop()

    # locate all the input fields
    select_main_menu_option( menu_id )
    dlg = wait_for_elem( 2, ".MuiDialog-root" )
    field_ids = get_input_fields( dlg ).keys()
    find_child( ".cancel", dlg ).click()

    def update_field( field_id, dlg, elem, setVal, val=None ):
        # check if we're updating the image
        if field_id == "image":
            if setVal:
                change_image( dlg, image_fname )
            else:
                remove_image( dlg )
            return None
        # check if a custom update function has been provided
        if update_fields and field_id in update_fields:
            update_fields[ field_id ][ 0 if setVal else 1 ]( elem )
            return None
        # update the field as text
        prev_val = elem.get_attribute( "value" )
        if val is None:
            val = "TEST: {}".format( field_id ) if setVal else ""
        set_elem_text( elem, val )
        elem.send_keys( Keys.RETURN ) # nb: in case we have a ReactSelect
        return prev_val

    def do_test( open_dialog, setVals ):

        # test each input field
        for field_id in field_ids:

            # NOTE: We can't unset a publication's name once it's been set, so there's no point continuing.
            if menu_id == "new-publication" and field_id == "name" and not setVals:
                continue

            # open the form dialog
            open_dialog()
            dlg = wait_for_elem( 2, ".MuiDialog-root" )
            input_fields = get_input_fields( dlg )

            # change the next input field
            prev_val = update_field( field_id, dlg, input_fields[field_id], setVals )

            # try to cancel the dialog (should get a confirmation dialog)
            find_child( ".cancel", dlg ).click()
            ask = wait_for_elem( 2, "#ask" )
            assert "Do you want to discard your changes?" in find_child( ".MuiDialogContent-root", ask ).text
            find_child( ".cancel", ask ).click()

            # NOTE: We can't unset a publication's name once it's been set, so there's no point continuing.
            if menu_id == "new-publication" and field_id == "name":
                find_child( ".cancel", dlg ).click()
                ask = wait_for_elem( 2, "#ask" )
                find_child( ".ok", ask ).click()
                continue
            # NOTE: Changing the image will always trigger a confirmation dialog, so there's no point continuing.
            if field_id == "image" and not setVals:
                find_child( ".cancel", dlg ).click()
                ask = wait_for_elem( 2, "#ask" )
                find_child( ".ok", ask ).click()
                continue

            # restore the original value
            if isinstance( prev_val, str ):
                prev_val = "   {}   ".format( prev_val )
            update_field( field_id, dlg, input_fields[field_id], not setVals, prev_val )

            # try to cancel the dialog (should work without confirmation)
            find_child( ".cancel", dlg ).click()
            ask = wait_for_not_elem( 2, ".MuiDialog-root" )

    # test using a blank object
    do_test( lambda: select_main_menu_option( menu_id ), True )

    # test using an object with every field filled in
    select_main_menu_option( menu_id )
    dlg = wait_for_elem( 2, ".MuiDialog-root" )
    input_fields = get_input_fields( dlg )
    for field_id in input_fields:
        update_field( field_id, dlg, input_fields[field_id], True )
    find_child( ".ok", dlg ).click()
    results = wait_for( 2, get_search_results )
    assert len(results) == 1
    do_test( lambda: select_sr_menu_option( results[0], "edit" ), False )

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

def find_parent_by_class( elem, class_name ):
    """Find a parent element with the specified class."""
    while True:
        elem = elem.find_element_by_xpath( ".." )
        if not elem:
            return None
        classes = set( elem.get_attribute( "class" ).split() )
        if class_name in classes:
            return elem

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

def change_image( dlg, fname ):
    """Click on an image to change it."""
    # NOTE: This is a bit tricky since we started overlaying the image with the "remove image" icon :-/
    data = base64.b64encode( open( fname, "rb" ).read() )
    data = "{}|{}".format( os.path.split(fname)[1], data.decode("ascii") )
    elem = find_child( ".row.image img.image", dlg )
    _webdriver.execute_script( "arguments[0].scrollTo( 0, 0 )", find_child( ".MuiDialogContent-root", dlg ) )
    send_upload_data( data,
        lambda: ActionChains( _webdriver ) \
                .move_to_element_with_offset( elem, 1, 1 ) \
                .click().perform()
    )

def remove_image( dlg ):
    """Remove an image."""
    find_child( ".row.image .remove-image", dlg ).click()

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
    dlg = wait_for_elem( 2, "#ask" )
    assert find_child( ".caption", dlg ).text == expected_caption
    constraints = [ c.text for c in find_children( ".constraint", dlg ) ]
    assert set( constraints ) == set( expected_constraints )
    find_child( ".MuiDialogActions-root button.{}".format( click_on ), dlg ).click()

def check_string( val, expected, contains=False ):
    """Compare a value with its expected value."""
    if contains:
        return expected in val
    return val == expected
