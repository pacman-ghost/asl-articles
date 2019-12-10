""" Control a react-select droplist. """

from selenium.webdriver.common.keys import Keys

from asl_articles.tests.utils import find_child, find_children

# ---------------------------------------------------------------------

class ReactSelect:
    """Control a react-select droplist."""

    def __init__( self, elem ):
        self.select = elem

    def select_by_name( self, val ):
        """Select an option by name."""
        find_child( ".react-select__dropdown-indicator", self.select ).click()
        options = [ e for e in find_children( ".react-select__option", self.select )
            if e.text == val
        ]
        assert len( options ) == 1
        options[0].click()

    def get_multiselect_choices( self ):
        """Get the available multi-select choices."""
        btn = find_child( ".react-select__dropdown-indicator", self.select )
        btn.click() # show the dropdown
        choices = [ e.text for e in find_children( ".react-select__option", self.select ) ]
        btn.click() # close the dropdown
        return choices

    def get_multiselect_values( self ):
        """Get the current multi-select values."""
        return [ e.text for e in find_children( ".react-select__multi-value", self.select ) ]

    def update_multiselect_values( self, *vals ):
        """Add/remove multi-select values."""
        for v in vals:
            if v.startswith( "+" ):
                self.add_multiselect_value( v[1:] )
            elif v.startswith( "-" ):
                self.remove_multiselect_value( v[1:] )
            else:
                assert False, "Multi-select values must start with +/-."

    def add_multiselect_value( self, val ):
        """Add a multi-select value."""
        elem = find_child( "input", self.select )
        elem.clear()
        elem.send_keys( val )
        elem.send_keys( Keys.RETURN )

    def remove_multiselect_value( self, val ):
        """Remove a multi-select value."""
        for elem in find_children( ".react-select__multi-value", self.select ):
            if elem.text == val:
                find_child( ".react-select__multi-value__remove", elem ).click()
                return
        assert False, "Can't find multi-select value: {}".format( val )
