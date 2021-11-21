import React from "react" ;
import { Link } from "react-router-dom" ;
import { Tabs, TabList, TabPanel, Tab } from 'react-tabs';
import 'react-tabs/style/react-tabs.css';
import "./DbReport.css" ;
import { PreviewableImage } from "./PreviewableImage" ;
import { gAppRef } from "./App.js" ;
import { makeCollapsibleList, pluralString, isLink } from "./utils.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class DbReport extends React.Component
{
    // render the component
    render() {
        return ( <div id="db-report">
            <div className="section"> <DbRowCounts /> </div>
            <div className="section"> <DbLinks /> </div>
            <div className="section"> <DbImages /> </div>
            </div>
        ) ;
    }
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class DbRowCounts extends React.Component
{

    constructor( props ) {

        // initialize
        super( props ) ;
        this.state = {
            dbRowCounts: null,
        } ;

        // get the database row counts
        axios.get(
            gAppRef.makeFlaskUrl( "/db-report/row-counts" )
        ).then( resp => {
            this.setState( { dbRowCounts: resp.data } ) ;
        } ).catch( err => {
            gAppRef.showErrorResponse( "Can't get the database row counts", err ) ;
        } ) ;

    }

    render() {

        // initialize
        const dbRowCounts = this.state.dbRowCounts ;

        // render the table rows
        function makeRowCountRow( tableName ) {
            const tableName2 = tableName[0].toUpperCase() + tableName.substring(1) ;
            let nRows ;
            if ( dbRowCounts ) {
                nRows = dbRowCounts[ tableName ] ;
                const nImages = dbRowCounts[ tableName+"_image" ] ;
                if ( nImages > 0 )
                    nRows = ( <span>
                        {nRows} <span className="images">({pluralString(nImages,"image")})</span>
                        </span>
                    ) ;
            }
            return ( <tr key={tableName}>
                <td style={{paddingRight:"0.5em",fontWeight:"bold"}}> {tableName2}s: </td>
                <td> {nRows} </td>
                </tr>
            ) ;
        }
        let tableRows = [ "publisher", "publication", "article", "author", "scenario" ].map(
            (tableName) => makeRowCountRow( tableName )
        ) ;

        // render the component
        return ( <div className="db-row-counts">
            <h2> Content { !dbRowCounts && <img src="/images/loading.gif" className="loading" alt="Loading..." /> } </h2>
            <table><tbody>{tableRows}</tbody></table>
            </div>
        ) ;
    }

}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class DbLinks extends React.Component
{

    constructor( props ) {

        // initialize
        super( props ) ;
        this.state = {
            dbLinks: null,
            linksToCheck: null, currLinkToCheck: null, isFirstLinkCheck: true,
            checkLinksInProgress: false, checkLinksStatusMsg: null,
            linkErrors: {},
        } ;

        // initialize
        this._getLinksToCheck() ;

    }

    render() {

        // initialize
        const dbLinks = this.state.dbLinks ;

        // render the table rows
        let tableRows = [] ;
        for ( let key of [ "publisher", "publication", "article" ] ) {
            const nDbLinks = dbLinks && dbLinks[key] ? dbLinks[key].length : null ;
            const key2 = key[0].toUpperCase() + key.substring(1) + "s" ;
            tableRows.push( <tr key={key}>
                <td style={{paddingRight:"0.5em",fontWeight:"bold"}}> {key2}: </td>
                <td style={{width:"100%"}}> {nDbLinks} </td>
                </tr>
            ) ;
            if ( this.state.linkErrors[ key ] ) {
                // NOTE: Showing all the errors at once (e.g. not as a collapsible list) will be unwieldy
                // if there are a lot of them, but this shouldn't happen often, and if it does, the user
                // is likely to stop the check, fix the problem, then try again.
                let rows = [] ;
                for ( let linkError of this.state.linkErrors[ key ] ) {
                    const url = gAppRef.makeAppUrl( "/" + linkError[0][0] + "/" + linkError[0][1] ) ;
                    const targetUrl = linkError[0][3] ;
                    const target = isLink( targetUrl )
                        ? <a href={targetUrl}>{targetUrl}</a>
                        : targetUrl ;
                    let errorMsg = linkError[1] && linkError[1] + ": " ;
                    rows.push( <li key={linkError[0]}>
                        <Link to={url} dangerouslySetInnerHTML={{__html:linkError[0][2]}} />
                        <span className="status"> ({errorMsg}{target}) </span>
                        </li>
                    ) ;
                }
                tableRows.push( <tr key={key+"-errors"}>
                    <td colSpan="2">
                        <ul className="link-errors"> {rows} </ul>
                    </td>
                    </tr>
                ) ;
            }
        }

        // render the component
        const nLinksToCheck = this.state.linksToCheck ? this.state.linksToCheck.length - this.state.currLinkToCheck : null ;
        const imageUrl = this.state.checkLinksInProgress ? "/images/loading.gif" : "/images/icons/check-db-links.png" ;
        return ( <div className="db-links">
            <h2> Links { !dbLinks && <img src="/images/loading.gif" className="loading" alt="Loading..." /> } </h2>
            { this.state.linksToCheck && this.state.linksToCheck.length > 0 && (
                <div className="check-links-frame">
                    <button className="check-links" style={{display:"flex"}} onClick={() => this.checkDbLinks()} >
                        <img src={imageUrl} style={{height:"1.25em",marginRight:"0.5em"}} alt="Check database links." />
                        { this.state.checkLinksInProgress ? "Stop checking" : "Check links (" + nLinksToCheck + ")" }
                    </button>
                    <div className="status-msg"> {this.state.checkLinksStatusMsg} </div>
                </div>
            ) }
            <table className="db-links" style={{width:"100%"}}><tbody>{tableRows}</tbody></table>
            </div>
        ) ;
    }

    checkDbLinks() {
        // start/stop checking links
        const inProgress = ! this.state.checkLinksInProgress ;
        this.setState( { checkLinksInProgress: inProgress } ) ;
        if ( inProgress )
            this._checkNextLink() ;
    }

    _checkNextLink( force ) {

        // check if this is the start of a new run
        if ( this.state.currLinkToCheck === 0 && !force ) {
            // yup - reset the UI
            this.setState( { linkErrors: {} } ) ;
            // NOTE: If the user is checking the links *again*, it could be because some links were flagged
            // during the first run, they've fixed them up, and want to check everything again. In this case,
            // we need to re-fetch the links from the database.
            if ( ! this.state.isFirstLinkCheck ) {
                this._getLinksToCheck(
                    () => { this._checkNextLink( true ) ; },
                    () => { this.setState( { checkLinksInProgress: false } ) ; }
                ) ;
                return ;
            }
        }

        // check if this is the end of a run
        if ( this.state.currLinkToCheck >= this.state.linksToCheck.length ) {
            // yup - reset the UI
            this.setState( {
                checkLinksStatusMsg: "Checked " + pluralString( this.state.linksToCheck.length, "link" ) + ".",
                currLinkToCheck: 0, // nb: to allow the user to check again
                checkLinksInProgress: false,
                isFirstLinkCheck: false,
            } ) ;
            return ;
        }

        // get the next link to check
        const linkToCheck = this.state.linksToCheck[ this.state.currLinkToCheck ] ;
        this.setState( { currLinkToCheck: this.state.currLinkToCheck + 1 } ) ;

        let continueCheckLinks = () => {
            // update the UI
            this.setState( { checkLinksStatusMsg:
                "Checked " + this.state.currLinkToCheck + " of " + pluralString( this.state.linksToCheck.length, "link" ) + "..."
            } ) ;
            // check the next link
            if ( this.state.checkLinksInProgress )
                this._checkNextLink() ;
        }

        // check the next link
        let url = linkToCheck[3] ;
        if ( url.substr( 0, 14 ) === "http://{FLASK}" )
            url = gAppRef.makeFlaskUrl( url.substr( 14 ) ) ;
        // NOTE: Because of CORS, we have to proxy URL's that don't belong to us via the backend :-/
        let req = isLink( url )
            ? axios.post( gAppRef.makeFlaskUrl( "/db-report/check-link", {url:url} ) )
            : axios.head( gAppRef.makeExternalDocUrl( url ) ) ;
        req.then( resp => {
            // the link worked - continue checking links
            continueCheckLinks() ;
        } ).catch( err => {
            // the link failed - record the error
            let newLinkErrors = this.state.linkErrors ;
            if ( newLinkErrors[ linkToCheck[0] ] === undefined )
                newLinkErrors[ linkToCheck[0] ] = [] ;
            const errorMsg = err.response ? "HTTP " + err.response.status : null ;
            newLinkErrors[ linkToCheck[0] ].push( [ linkToCheck, errorMsg ] ) ;
            this.setState( { linkErrors: newLinkErrors } ) ;
            // continue checking links
            continueCheckLinks() ;
        } ) ;

    }

    _getLinksToCheck( onOK, onError ) {
        // get the links in the database
        axios.get(
            gAppRef.makeFlaskUrl( "/db-report/links" )
        ).then( resp => {
            const dbLinks = resp.data ;
            // flatten the links to a list
            let linksToCheck = [] ;
            for ( let key of [ "publisher", "publication", "article" ] ) {
                for ( let row of dbLinks[key] ) {
                    linksToCheck.push( [
                        key, row[0], row[1], row[2]
                    ] ) ;
                }
            }
            this.setState( {
                dbLinks: resp.data,
                linksToCheck: linksToCheck,
                currLinkToCheck: 0,
            } ) ;
            if ( onOK )
                onOK() ;
        } ).catch( err => {
            gAppRef.showErrorResponse( "Can't get the database links", err ) ;
            if ( onError )
                onError() ;
        } ) ;
    }

}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class DbImages extends React.Component
{

    constructor( props ) {

        // initialize
        super( props ) ;
        this.state = {
            dbImages: null,
        } ;

        // get the database images
        axios.get(
            gAppRef.makeFlaskUrl( "/db-report/images" )
        ).then( resp => {
            this.setState( { dbImages: resp.data } ) ;
        } ).catch( err => {
            gAppRef.showErrorResponse( "Can't get the database images", err ) ;
        } ) ;

    }

    render() {

        // initialize
        const dbImages = this.state.dbImages ;

        // render any duplicate images
        let dupeImages = [] ;
        if ( dbImages ) {
            for ( let hash in dbImages.duplicates ) {
                let parents = [] ;
                for ( let row of dbImages.duplicates[hash] ) {
                    const url = gAppRef.makeAppUrl( "/" + row[0] + "/" + row[1] ) ;
                    parents.push(
                        <Link to={url} dangerouslySetInnerHTML={{__html:row[2]}} />
                    ) ;
                }
                // NOTE: We just use the first row's image since, presumably, they will all be the same.
                const row = dbImages.duplicates[hash][ 0 ] ;
                const imageUrl = gAppRef.makeFlaskImageUrl( row[0], row[1] ) ;
                const caption = ( <span>
                    Found a duplicate image <span className="hash">(md5:{hash})</span>
                    </span>
                ) ;
                dupeImages.push( <div className="dupe-image" style={{display:"flex"}} key={hash} >
                    <PreviewableImage url={imageUrl} style={{width:"3em",marginTop:"0.1em",marginRight:"0.5em"}} />
                    { makeCollapsibleList( caption,  parents, 5, {flexGrow:1}, hash ) }
                    </div>
                ) ;
            }
        }

        // render the image sizes
        let tabList = [] ;
        let tabPanels = [] ;
        if ( dbImages ) {
            function toKB( n ) { return ( n / 1024 ).toFixed( 1 ) ; }
            for ( let key of [ "publisher", "publication", "article" ] ) {
                const tableName2 = key[0].toUpperCase() + key.substring(1) ;
                tabList.push(
                    <Tab key={key}> {tableName2+"s"} </Tab>
                ) ;
                let rows = [] ;
                for ( let row of dbImages[key] ) {
                    const url = gAppRef.makeAppUrl( "/" + key + "/" + row[1] ) ;
                    // NOTE: Loading every image will be expensive, but we assume we're talking to a local server.
                    // Otherwise, we could use a generic "preview" image, and expand it out to the real image
                    // when the user clicks on it.
                    const imageUrl = gAppRef.makeFlaskImageUrl( key, row[1] ) ;
                    rows.push( <tr key={row}>
                        <td> <PreviewableImage url={imageUrl} /> </td>
                        <td> {toKB(row[0])} </td>
                        <td> <Link to={url} dangerouslySetInnerHTML={{__html:row[2]}} /> </td>
                        </tr>
                    ) ;
                }
                tabPanels.push( <TabPanel key={key}>
                    { rows.length === 0 ? "No images found." :
                        <table className="image-sizes"><tbody>
                            <tr><th style={{width:"1.25em"}}/><th style={{paddingRight:"0.5em"}}> Size (KB) </th><th> {tableName2} </th></tr>
                            {rows}
                        </tbody></table>
                    }
                    </TabPanel>
                ) ;
            }
        }
        const imageSizes = tabList.length > 0 && ( <Tabs>
            <TabList> {tabList} </TabList>
            {tabPanels}
            </Tabs>
        ) ;

        // render the component
        return ( <div className="db-images">
            <h2> Images { !dbImages && <img src="/images/loading.gif" className="loading" alt="Loading..." /> } </h2>
            { dupeImages.length > 0 &&
                <div className="dupe-analysis"> {dupeImages} </div>
            }
            {imageSizes}
            </div>
        ) ;

    }

}
