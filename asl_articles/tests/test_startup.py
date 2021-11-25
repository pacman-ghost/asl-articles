""" Test the startup process. """

import pytest

import asl_articles.startup

from asl_articles.tests.utils import init_tests, wait_for, find_child, set_toast_marker, check_toast
from asl_articles.tests import pytest_options

# ---------------------------------------------------------------------

@pytest.mark.skipif( pytest_options.flask_url is not None, reason="Testing against a remote Flask server." )
def test_startup_messages( webdriver, flask_app, dbconn ):
    """Test startup messages."""

    # initialize
    init_tests( webdriver, flask_app, dbconn )
    startup_msgs = asl_articles.startup._startup_msgs #pylint: disable=protected-access

    def do_test( msg_type ):

        # check that the startup message was shown in the UI correctly
        set_toast_marker( msg_type )
        assert startup_msgs[ msg_type ] == []
        asl_articles.startup.log_startup_msg( msg_type, "TEST: {}", msg_type )
        webdriver.refresh()
        expected = startup_msgs[ msg_type ][0]
        wait_for( 2, lambda: check_toast( msg_type, expected ) )
        startup_msgs[ msg_type ] = []

        # check if the webapp started up or not
        if msg_type == "error":
            assert not find_child( "#search-form" )
        else:
            assert find_child( "#search-form" )

    # test each type of startup message
    do_test( "info" )
    do_test( "warning" )
    do_test( "error" )
