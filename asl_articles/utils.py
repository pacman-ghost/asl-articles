""" Helper utilities. """

import re
import configparser
import typing
import itertools
import logging

from flask import jsonify, abort
import lxml.html.clean

_html_whitelists = None
_startup_logger = logging.getLogger( "startup" )

_CONTROL_CHARS = list( ch for ch in itertools.chain( range(0,31+1), range(127,159+1) )
    if ch not in (10,13)
)

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
        if f.endswith( "_url" ):
            continue # nb: don't clean URL's
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

def clean_html( val, allow_tags=None, safe_attrs=None ): #pylint: disable=too-many-locals,too-many-branches,too-many-statements
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
            # FUDGE! pylint is incorrectly flagging isinstance() when checking against typing.XXX.
            #   https://github.com/PyCQA/pylint/issues/3537
            if isinstance( t, typing.Pattern ): #pylint: disable=isinstance-second-argument-not-valid-type
                val = t.sub( ch, val )
            else:
                assert isinstance( t, str )
                val = val.replace( t, ch )
        return val
    val = replace_chars( val, '"', [ "\u00ab", "\u00bb", "\u201c", "\u201d", "\u201e", "\u201f" ] )
    val = replace_chars( val, "'", [ "\u2018", "\u2019", "\u201a", "\u201b", "\u2039", "\u203a" ] )
    val = replace_chars( val, r"\1 - \2", [ re.compile( r"(\S+)\u2014(\S+)" ) ] )
    val = replace_chars( val, "-", [ "\u2013", "\u2014" ] )
    val = replace_chars( val, "...", [ "\u2026" ] )

    # remove control characters
    val = val.replace( "\t", " " )
    val = "".join( ch for ch in val if ord(ch) not in _CONTROL_CHARS )

    # FUDGE! lxml replaces HTML entities with their actual character :-/ It's possible to stop it from doing this,
    # by passing in an ElementTree, which gives us an ElementTree back, and we can then control how it is serialized
    # back into a string e.g.
    #   html = lxml.html.fromstring( val )
    #   html = cleaner.clean_html( html )
    #   val = lxml.html.tostring( html, encoding="ascii" ).decode( encoding="ascii" )
    # but the original HTML entities are converted into numeric e.g. "&egrave;" => "&#232;" :-/
    # We hack around this by replacing all HTML entities with a special marker string, clean the HTML,
    # then replace all the marker strings with their original HTML entities :-/
    markers = {}
    matches = list( re.finditer( "&[a-z][a-z0-9]+;", val ) )
    matches = reversed( matches )
    for n,mo in enumerate(matches):
        marker = "[!${}$!]".format( n )
        markers[ marker ] = mo.group()
        val = val[:mo.start()] + marker + val[mo.end():]

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
        if safe_attrs:
            safe_attrs.extend( lxml.html.defs.safe_attrs )
    elif safe_attrs == []:
        safe_attrs = [ "" ] # nb: this is how we remove everything :-/
    if safe_attrs:
        args[ "safe_attrs" ] = safe_attrs
    cleaner = lxml.html.clean.Cleaner( **args )
    buf = cleaner.clean_html( val )

    # restore the HTML entities
    for marker,entity in markers.items():
        buf = buf.replace( marker, entity )

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
    return "\n".join( tags )

def decode_tags( tags ):
    """Decode tags after loading them from the database."""
    if not tags:
        return None
    return tags.split( "\n" )

# ---------------------------------------------------------------------

class AppConfigParser():
    """Wrapper around the standard ConfigParser."""
    def __init__( self, fname ):
        self._configparser = configparser.ConfigParser()
        self._configparser.optionxform = str # preserve case for the keys :-/
        self._configparser.read( fname )
    def get_section( self, section_name ):
        """Read a section from the config."""
        try:
            return self._configparser.items( section_name )
        except configparser.NoSectionError:
            return []

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

def squash_spaces( val ):
    """Squash multiple spaces down into a single space."""
    return " ".join( val.split() )
