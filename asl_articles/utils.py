""" Helper utilities. """

import re
import logging

import lxml.html.clean

_html_whitelists = None
_startup_logger = logging.getLogger( "startup" )

# ---------------------------------------------------------------------

def get_request_args( vals, keys, log=None ):
    """Unload the arguments from a Flask request."""
    vals = { k: vals.get( k ) for k in keys }
    vals = {
        k: v.strip() if isinstance(v,str) else v
        for k,v in vals.items()
    }
    if log:
        log[0].debug( "%s", log[1] )
        for k in keys:
            log[0].debug( "- %s = %s", k, str(vals[k]) )
    return vals

def apply_attrs( obj, vals ):
    """Update an object's attributes."""
    for k,v in vals.items():
        setattr( obj, k, v )

# ---------------------------------------------------------------------

def clean_html( val ):
    """Sanitize HTML using a whitelist."""

    # strip the HTML
    val = val.strip()
    if not val:
        return val
    args = {}
    if _html_whitelists["tags"]:
        args[ "allow_tags" ] = _html_whitelists["tags"]
        args[ "remove_unknown_tags" ] = None
    if _html_whitelists["attrs"]:
        args[ "safe_attrs" ] = _html_whitelists["attrs"]
    cleaner = lxml.html.clean.Cleaner( **args )
    buf = cleaner.clean_html( val )

    # clean up the results
    buf = re.sub( r"\s+", " ", buf )
    buf = re.sub( r"^\s+", "", buf, re.MULTILINE )
    buf = re.sub( r"\s+$", "", buf, re.MULTILINE )
    if buf.startswith( "<p>" ) and buf.endswith( "</p>" ):
        buf = buf[3:-4]
    if buf.startswith( "<div>" ) and buf.endswith( "</div>" ):
        buf = buf[5:-6]
    if buf.startswith( "<span>" ) and buf.endswith( "</span>" ):
        buf = buf[6:-7]
    return buf.strip()

def load_html_whitelists( app ):
    """Load the HTML whitelists."""
    global _html_whitelists
    assert _html_whitelists is None
    def parse_whitelist( key ):
        whitelist = app.config.get( key, "" )
        whitelist = whitelist.replace( ",", " " )
        whitelist = [ s.strip() for s in whitelist.split(" ") ]
        whitelist = [ s for s in whitelist if s ]
        _startup_logger.debug( "Configured %s: %s", key, whitelist )
        return whitelist
    _html_whitelists = {
        "tags": parse_whitelist( "HTML_TAG_WHITELIST" ),
        "attrs": parse_whitelist( "HTML_ATTR_WHITELIST" )
    }

# ---------------------------------------------------------------------

def to_bool( val ):
    """Interpret a value as a boolean."""
    if val is None:
        return None
    val = str( val ).lower()
    if val in ["yes","true","enabled","1"]:
        return True
    if val in ["no","false","disabled","0"]:
        return False
    return None
