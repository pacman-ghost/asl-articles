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

export function removeSpecialFields( vals ) {
    // NOTE: This removes special fields sent to us by the backend containing content that has search terms highlighted.
    // We only really need to remove author names for articles, since the backend sends us these (possibly highlighted)
    // as well as the ID's, but they could be incorrect after the user has edited an article. However, for consistency,
    // we remove all these special fields for everything.
    let keysToDelete = [] ;
    for ( let key in vals ) {
        if ( key[ key.length-1 ] === "!" )
            keysToDelete.push( key ) ;
    }
    keysToDelete.forEach( k => delete vals[k] ) ;
}

// --------------------------------------------------------------------

// NOTE: The format of a scenario display name is "SCENARIO NAME [SCENARIO ID]".

export function makeScenarioDisplayName( scenario ) {
    let scenario_display_id, scenario_name
    if ( Array.isArray( scenario ) ) {
        // we've been given a scenario ID/name
        scenario_display_id = scenario[0] ;
        scenario_name = scenario[1] ;
    } else {
        // we've been given a scenario object (dict)
        scenario_display_id = scenario.scenario_display_id ;
        scenario_name = scenario.scenario_name ;
    }
    if ( scenario_name && scenario_display_id )
        return scenario_name + " [" + scenario_display_id + "]" ;
    else if ( scenario_name )
        return scenario_name ;
    else if ( scenario_display_id )
        return scenario_display_id ;
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
    if ( vals ) {
        for ( let i=0 ; i < vals.length ; ++i ) {
            result.push( extract( vals[i] ) ) ;
            if ( i < vals.length-1 )
                result.push( ", " ) ;
        }
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
