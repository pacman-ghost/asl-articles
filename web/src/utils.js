import React from "react" ;
import ReactDOMServer from "react-dom/server" ;
import { gAppRef } from "./index.js" ;

const isEqual = require( "lodash.isequal" ) ;

// --------------------------------------------------------------------

export function checkConstraints( required, requiredCaption, optional, optionalCaption, accept ) {

    // check if constraints have been disabled (for testing porpoises only)
    if ( gAppRef.isDisableConstraints() ) {
        accept() ;
        return ;
    }

    // check the required constraints
    let msgs=[], setFocusTo=null ;
    if ( required ) {
        for ( let constraint of required ) {
            if ( constraint[0]() ) {
                msgs.push( constraint[1] ) ;
                if ( constraint[2] && !setFocusTo )
                    setFocusTo = constraint[2] ;
            }
        }
    }
    if ( msgs.length > 0 ) {
        gAppRef.showErrorMsg(
            makeSmartBulletList( requiredCaption, msgs, "constraint" ),
            setFocusTo
        ) ;
        return ;
    }

    // check the optional constraints
    if ( optional ) {
        for ( let constraint of optional ) {
            if ( constraint[0]() ) {
                msgs.push( constraint[1] ) ;
                if ( constraint[2] && !setFocusTo )
                    setFocusTo = constraint[2] ;
            }
        }
    }
    if ( msgs.length > 0 ) {
        // some constraints failed - ask the user if they want to continue
        let content = <div style={{float:"left"}}> { makeSmartBulletList( optionalCaption, msgs, "constraint" ) } </div> ;
        gAppRef.ask( content, "ask", {
            OK: () => { accept() },
            Cancel: null
        }, setFocusTo ) ;
        return ;
    }

    // everything passed - accept the values
    accept() ;
}

export function confirmDiscardChanges( oldVals, newVals, accept ) {
    // check if confirmations have been disabled (for testing porpoises only)
    if ( gAppRef.isDisableConfirmDiscardChanges() ) {
        accept() ;
        return ;
    }
    // check if the values have changed
    if ( isEqual( oldVals, newVals ) ) {
        // nope - just do it
        accept() ;
    } else {
        // yup - ask the user to confirm first
        gAppRef.ask( "Do you want to discard your changes?", "ask", {
            OK: accept,
            Cancel: null,
        } ) ;
    }
}

export function sortSelectableOptions( options ) {
    options.sort( (lhs,rhs) => {
        lhs = ReactDOMServer.renderToStaticMarkup( lhs.label ) ;
        rhs = ReactDOMServer.renderToStaticMarkup( rhs.label ) ;
        return lhs.localeCompare( rhs ) ;
    } ) ;
}

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

export function makeCollapsibleList( caption, vals, maxItems, style ) {
    if ( ! vals || vals.length === 0 )
        return null ;
    let items=[], excessItems=[] ;
    let excessItemsRef=null, flipButtonRef=null ;
    for ( let i=0 ; i < vals.length ; ++i ) {
        let item ;
        if ( typeof vals[i] === "string" )
            item = <li key={i} dangerouslySetInnerHTML={{ __html: vals[i] }} /> ;
        else
            item = <li key={i}> {vals[i]} </li> ; // nb: we assume we were given JSX
        ( i < maxItems ? items : excessItems ).push( item ) ;
    }
    function flipExcessItems() {
        const pos = flipButtonRef.src.lastIndexOf( "/" ) ;
        const show = flipButtonRef.src.substr( pos ) === "/collapsible-down.png" ;
        excessItemsRef.style.display = show ? "block" : "none" ;
        flipButtonRef.src = flipButtonRef.src.substr( 0, pos ) + (show ? "/collapsible-up.png" : "/collapsible-down.png") ;
    }
    if ( excessItems.length === 0 )
        caption = <span> {caption+":"} </span> ;
    else
        caption = <span> {caption} <span className="count"> ({vals.length}) </span> </span> ;
    return ( <div className="collapsible" style={style}>
        <div className="caption" onClick={flipExcessItems}> {caption}
            { excessItems.length > 0 && <img src="images/collapsible-down.png" ref={r => flipButtonRef=r} alt="Show/hide extra items." /> }
        </div>
        <ul> {items} </ul>
        { excessItems.length > 0 &&
            <ul className="excess" ref={r => excessItemsRef=r} style={{display:"none"}}>
                {excessItems}
            </ul>
        }
        </div> ) ;
}

export function makeCommaList( vals ) {
    let result = [] ;
    if ( vals ) {
        for ( let i=0 ; i < vals.length ; ++i ) {
            result.push( vals[i] ) ;
            if ( i < vals.length-1 )
                result.push( ", " ) ;
        }
    }
    return result ;
}

export function makeSmartBulletList( caption, vals, className ) {
    caption = <div className="caption"> {caption} </div> ;
    if ( !vals || vals.length === 0 )
        return caption ;
    else if ( vals.length === 1 )
        return <div> {caption} <p className={className}> {vals[0]} </p> </div> ;
    else {
        let bullets = vals.map( (v,i) => <li key={i} className={className}> {v} </li> ) ;
        return <div> {caption} <ul> {bullets} </ul> </div> ;
    }
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

export function ciCompare( lhs, rhs ) {
    return lhs.localeCompare( rhs, undefined, { sensitivity: "base" } ) ;
}

export function isNumeric( val ) {
    if ( val === null || val === undefined )
        return false ;
    val = val.trim() ;
    if ( val === "" )
        return false ;
    return ! isNaN( val ) ;
}

export function isLink( val ) {
    if ( val.substr(0,7) === "http://" || val.substr(0,8) === "https://" )
        return true ;
    if ( val.substr(0,7) === "file://" )
        return true ;
    return false ;
}
