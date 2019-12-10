import React from "react" ;

// --------------------------------------------------------------------

export function unloadCreatableSelect( sel ) {
    // unload the values from a CreatableSelect
    if ( ! sel.state.value )
        return [] ;
    const vals = sel.state.value.map( v => v.label ) ;
    // dedupe the values (trying to preserve order)
    let vals2=[], used={} ;
    for ( let i=0 ; i < vals.length ; ++i ) {
        if ( ! used[ vals[i] ] ) {
            vals2.push( vals[i] ) ;
            used[ vals[i] ] = true ;
        }
    }
    return vals2 ;
}

// --------------------------------------------------------------------

export function makeOptionalLink( caption, url ) {
    let link = <span dangerouslySetInnerHTML={{ __html: caption }} /> ;
    if ( url )
        link = <a href={url} target="_blank" rel="noopener noreferrer"> {link} </a> ;
    return link ;
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
