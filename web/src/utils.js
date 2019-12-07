import React from "react" ;

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
