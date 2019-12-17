import React from "react" ;

// --------------------------------------------------------------------

export function unloadCreatableSelect( sel ) {
    // unload the values from a CreatableSelect
    if ( ! sel.state.value )
        return [] ;
    const vals = sel.state.value ;
    // dedupe the values (trying to preserve order)
    let vals2=[], used={} ;
    vals.forEach( val => {
        if ( ! used[ val.label ] ) {
            vals2.push( val ) ;
            used[ val.label ] = true ;
        }
    } ) ;
    return vals2 ;
}

// --------------------------------------------------------------------

export function applyUpdatedVals( vals, newVals, updated, refs ) {
    // NOTE: After the user has edited an object, we send the new values to the server to store in
    // the database, but the server will sometimes return modified values back e.g. because unsafe HTML
    // was removed, or the ID's of newly-created authors. This function applies these new values back
    // into the original table of values.
    for ( let r in refs )
        vals[ r ] = (updated && updated[r] !== undefined) ? updated[r] : newVals[r] ;
}

// --------------------------------------------------------------------

export function makeOptionalLink( caption, url ) {
    let link = <span dangerouslySetInnerHTML={{ __html: caption }} /> ;
    if ( url )
        link = <a href={url} target="_blank" rel="noopener noreferrer"> {link} </a> ;
    return link ;
}

export function bytesDisplayString( nBytes )
{
    if ( nBytes === 1 )
        return "1 byte" ;
    var vals = [ "bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB" ] ;
    for ( let i=1 ; i < vals.length ; i++ ) {
        if ( nBytes < Math.pow( 1024, i ) )
            return ( Math.round( ( nBytes / Math.pow(1024,i-1) ) * 100 ) / 100 ) + " " + vals[i-1] ;
    }
    return nBytes ;
}

export function slugify( val ) {
    return val.toLowerCase().replace( " ", "-" ) ;
}

export function pluralString( n, str1, str2 ) {
    if ( n === 1 )
        return n + " " + str1 ;
    else
        return n + " " + (str2 ? str2 : str1+"s") ;
}
