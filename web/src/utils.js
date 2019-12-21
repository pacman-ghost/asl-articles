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
    // NOTE: We sometimes want to force an entry into the vals that doesn't have
    // an associated ref (i.e. UI element) e.g. XXX_image_id.
    for ( let key in updated )
        vals[ key ] = updated[ key ] ;
}

// --------------------------------------------------------------------

// NOTE: The format of a scenario display name is "SCENARIO NAME [SCENARIO ID]".

export function makeScenarioDisplayName( scenario ) {
    if ( scenario.scenario_name && scenario.scenario_display_id )
        return scenario.scenario_name + " [" + scenario.scenario_display_id + "]" ;
    else if ( scenario.scenario_name )
        return scenario.scenario_name ;
    else if ( scenario.scenario_display_id )
        return scenario.scenario_display_id ;
    else
        return "???" ;
}

export function parseScenarioDisplayName( displayName ) {
    // try to locate the scenario ID
    displayName = displayName.trim() ;
    let scenarioId=null, scenarioName=displayName ;
    if ( displayName[ displayName.length-1 ] === "]" ) {
        let pos = displayName.lastIndexOf( "[" ) ;
        if ( pos !== -1 ) {
            // found it - separate it from the scenario name
            scenarioId = displayName.substr( pos+1, displayName.length-pos-2 ).trim() ;
            scenarioName = displayName.substr( 0, pos ).trim() ;
        }
    }
    return [ scenarioId, scenarioName ] ;
}

// --------------------------------------------------------------------

export function makeOptionalLink( caption, url ) {
    let link = <span dangerouslySetInnerHTML={{ __html: caption }} /> ;
    if ( url )
        link = <a href={url} target="_blank" rel="noopener noreferrer"> {link} </a> ;
    return link ;
}

export function makeCommaList( vals, extract ) {
    let result = [] ;
    for ( let i=0 ; i < vals.length ; ++i ) {
        result.push( extract( vals[i] ) ) ;
        if ( i < vals.length-1 )
            result.push( ", " ) ;
    }
    return result ;
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
