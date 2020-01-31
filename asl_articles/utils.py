""" Helper utilities. """

import re
import typing
import logging

from flask import jsonify, abort
import lxml.html.clean

_html_whitelists = None
_startup_logger = logging.getLogger( "startup" )

# ---------------------------------------------------------------------

def get_request_args( vals, arg_names, log=None ):
    """Unload the arguments from a Flask request."""
    arg_names = [ _parse_arg_name( k ) for k in arg_names ]
    vals = { a[0]: vals.get( a[0] ) for a in arg_names }
    vals = {
        k: v.strip() if isinstance(v,str) else v
        for k,v in vals.items()
    }
    if log:
        log[0].debug( "%s", log[1] )
        for a in arg_names:
            log[0].debug( "- %s = %s", a[0], str(vals[a[0]]) )
    # check for required arguments
    required = [ a[0] for a in arg_names if a[1] ]
    required = [ r for r in required if r not in vals or not vals[r] ]
    if required:
        abort( 400, "Missing required values: {}".format( ", ".join( required ) ) )
    return vals

def clean_request_args( vals, fields, warnings, logger ):
    """Clean incoming data."""
    cleaned = {}
    for f in fields:
        f = _parse_arg_name( f )[ 0 ]
        if isinstance( vals[f], str ):
            val2 = clean_html( vals[f] )
            if val2 != vals[f]:
                vals[f] = val2
                cleaned[f] = val2
                logger.debug( "Cleaned HTML: %s => %s", f, val2 )
                warnings.append( "Some values had HTML cleaned up." )
    return cleaned

def _parse_arg_name( arg_name ):
    """Parse a request argument name."""
    if arg_name[0] == "*":
        return ( arg_name[1:], True ) # required argument
    return ( arg_name, False ) # optional argument

def make_ok_response( extras=None, updated=None, warnings=None ):
    """Generate a Flask 'success' response."""
    resp = { "status": "OK" }
    if extras:
        resp.update( extras )
    if updated:
        resp[ "updated" ] = updated
    if warnings:
        resp[ "warnings" ] = list( set( warnings ) ) # nb: remove duplicate messages
    return jsonify( resp )

# ---------------------------------------------------------------------

def clean_html( val, allow_tags=None, safe_attrs=None ): #pylint: disable=too-many-branches
    """Sanitize HTML using a whitelist."""

    # check if we need to do anything
    if val is None:
        return None
    val = val.strip()
    if not val:
        return val

    # fixup smart quotes and dashes
    def replace_chars( val, ch, targets ):
        for t in targets:
            if isinstance( t, typing.Pattern ):
                val = t.sub( ch, val )
            else:
                assert isinstance( t, str )
                val = val.replace( t, ch )
        return val
    val = replace_chars( val, '"', [ "\u00ab", "\u00bb", "\u201c", "\u201d", "\u201e", "\u201f" ] )
    val = replace_chars( val, "'", [ "\u2018", "\u2019", "\u201a", "\u201b", "\u2039", "\u203a" ] )
    val = replace_chars( val, r"\1 - \2", [ re.compile( r"(\S+)\u2014(\S+)" ) ] )
    val = replace_chars( val, "-", [ "\u2014" ] )

    # strip the HTML
    args = {}
    if allow_tags is None:
        allow_tags = _html_whitelists.get( "tags" )
    elif allow_tags == []:
        allow_tags = [ "" ] # nb: this is how we remove everything :-/
    if allow_tags:
        args[ "allow_tags" ] = allow_tags
        args[ "remove_unknown_tags" ] = None
    if safe_attrs is None:
        safe_attrs = _html_whitelists.get( "attrs" )
    elif safe_attrs == []:
        safe_attrs = [ "" ] # nb: this is how we remove everything :-/
    if safe_attrs:
        args[ "safe_attrs" ] = safe_attrs
    cleaner = lxml.html.clean.Cleaner( **args )
    buf = cleaner.clean_html( val )

    # clean up the results
    while True:
        buf = buf.strip()
        prev_buf = buf
        buf = re.sub( " +", " ", buf ) # nb: we don't use "\s+" to preserve newlines
        buf = re.sub( r"^\s+", "", buf, re.MULTILINE )
        buf = re.sub( r"\s+$", "", buf, re.MULTILINE )
        for tag in ["body","div","span"]:
            if buf.startswith( "<{}>".format(tag) ) and buf.endswith( "</{}>".format(tag) ):
                buf = buf[ len(tag)+2 : -len(tag)-3 ]
        if buf == prev_buf:
            break
    if buf.startswith( "<p>" ) and buf.endswith( "</p>" ):
        buf2 = buf[ 3: -4 ]
        if "<p>" not in buf2 and "</p>" not in buf2:
            buf = buf2
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

def clean_tags( tags, warnings ):
    """Remove HTML from tags."""
    cleaned_tags = [ clean_html( t, allow_tags=[], safe_attrs=[] ) for t in tags ]
    if cleaned_tags != tags:
        warnings.append( "Some values had HTML removed." )
    return cleaned_tags

def encode_tags( tags ):
    """Encode tags prior to storing them in the database."""
    if not tags:
        return None
    return "\n".join( t.lower() for t in tags )

def decode_tags( tags ):
    """Decode tags after loading them from the database."""
    if not tags:
        return None
    return tags.split( "\n" )

# ---------------------------------------------------------------------

def apply_attrs( obj, vals ):
    """Update an object's attributes."""
    for k,v in vals.items():
        setattr( obj, k, v )

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
