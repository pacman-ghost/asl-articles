import React from "react" ;
import ReactDOM from "react-dom" ;
import ReactDOMServer from "react-dom/server" ;
import { Menu, MenuList, MenuButton, MenuItem } from "@reach/menu-button" ;
import "@reach/menu-button/styles.css" ;
import { ToastContainer, toast } from "react-toastify" ;
import "react-toastify/dist/ReactToastify.min.css" ;
import SearchForm from "./SearchForm" ;
import { SearchResults } from "./SearchResults" ;
import { PublisherSearchResult } from "./PublisherSearchResult" ;
import { PublicationSearchResult } from "./PublicationSearchResult" ;
import { ArticleSearchResult } from "./ArticleSearchResult" ;
import ModalForm from "./ModalForm";
import AskDialog from "./AskDialog" ;
import { DataCache } from "./DataCache" ;
import { PreviewableImage } from "./PreviewableImage" ;
import { makeSmartBulletList } from "./utils.js" ;
import { APP_NAME } from "./constants.js" ;
import "./App.css" ;

const axios = require( "axios" ) ;
const queryString = require( "query-string" ) ;
window.$ = window.jQuery = require( "jquery" ) ;

export let gAppRef = null ;

// --------------------------------------------------------------------

export class App extends React.Component
{
    constructor( props ) {

        // initialize the App
        super( props ) ;
        this.state = {
            searchResults: [],
            searchSeqNo: 0,
            modalForm: null,
            askDialog: null,
            startupTasks: [ "dummy" ], // FUDGE! We need at least one startup task.
        } ;
        gAppRef = this ;
        this.setWindowTitle( null ) ;

        // initialize the data cache
        this.dataCache = new DataCache() ;

        // initialize
        this.args = queryString.parse( window.location.search ) ;
        this._storeMsgs = this.isTestMode() && this.args.store_msgs ;
        this._disableSearchResultHighlighting = this.isTestMode() && this.args.no_sr_hilite ;
        this._disableConstraints = this.isTestMode() && this.args.disable_constraints ;
        this._disableConfirmDiscardChanges = this.isTestMode() && this.args.disable_confirm_discard_changes ;
        this._fakeUploads = this.isTestMode() && this.args.fake_uploads ;

        // initialize
        this._searchFormRef = React.createRef() ;
        this._searchResultsRef = React.createRef() ;
        this._modalFormRef = React.createRef() ;
        this._setFocusTo = null ;

        // figure out the base URL of the Flask backend server
        // NOTE: We allow the caller to do this since the test suite will usually spin up
        // it's own Flask server, but talks to an existing React server, so we need some way
        // for pytest to change which Flask server the React frontend code should tak to.
        this._flaskBaseUrl = this.isTestMode() ? this.args._flask : null ;
        if ( ! this._flaskBaseUrl ) {
            // NOTE: We used to use process.env.REACT_APP_FLASK_URL here, but this means that the client
            // needs to have access to the Flask backend server. We now proxy all backend requests via
            // "/api/..." endpoints, which we handle ourself (by setupProxy.js for the dev environment,
            // and nginx proxying for production), so the client only needs access to the React front-end.
            // This also has the nice side-effect of removing CORS issues :-/
            this._flaskBaseUrl = "/api" ;
        }

        // NOTE: Managing publisher/publication/article images is a bit tricky, since they are accessed via a URL
        // such as "/articles/images/123", so if the user uploads a new image, the browser has no way of knowing
        // that it can't use what's in its cache and must get a new one. We can add something to the URL to force
        // a reload (e.g. "?foo=" + Math.random()), but this forces the image to be reloaded *every* time, which is
        // pretty inefficient.
        // Instead, we track a unique cache-busting value for each image URL, and change it when necessary.
        this._flaskImageUrlVersions = {} ;
    }

    render() {
        let content ;
        if ( this.state.startupTasks.length > 0 ) {
            // we are still starting up
            content = <div id="loading"> <img id="loading" src="/images/loading.gif" alt="Loading..." /> </div> ;
        } else {
            // generate the menu
            const menu = ( <Menu id="app">
                <MenuButton />
                <MenuList>
                    <MenuItem id="menu-show-publishers" onSelect={ () => this._showPublishers() } >
                        <img src="/images/icons/publisher.png" alt="Show publishers." /> Show publishers
                    </MenuItem>
                    <MenuItem id="menu-search-technique" onSelect={ () => this._showTechniqueArticles() } >
                        <img src="/images/icons/technique.png" alt="Show technique articles." /> Show technique
                    </MenuItem>
                    <MenuItem id="menu-search-tips" onSelect={ () => this._showTipsArticles() } >
                        <img src="/images/icons/tips.png" alt="Show tip articles." /> Show tips
                    </MenuItem>
                    <div className="divider" />
                    <MenuItem id="menu-new-publisher" onSelect={PublisherSearchResult.onNewPublisher} >
                        <img src="/images/icons/publisher.png" alt="New publisher." /> New publisher
                    </MenuItem>
                    <MenuItem id="menu-new-publication" onSelect={PublicationSearchResult.onNewPublication} >
                        <img src="/images/icons/publication.png" alt="New publication." /> New publication
                    </MenuItem>
                    <MenuItem id="menu-new-article" onSelect={ArticleSearchResult.onNewArticle} >
                        <img src="/images/icons/article.png" alt="New article." /> New article
                    </MenuItem>
                </MenuList>
            </Menu> ) ;
            // generate the main content
            content = ( <div>
                <div id="header">
                    <a href={gAppRef.makeAppUrl("/")} title="Home page.">
                        <img className="logo" src="/images/app.png" alt="Logo" />
                    </a>
                    <div className="app-name"> {APP_NAME} </div>
                    <SearchForm onSearch={this.onSearch.bind(this)} ref={this._searchFormRef} />
                </div>
                {menu}
                <SearchResults ref={this._searchResultsRef}
                    seqNo = {this.state.searchSeqNo}
                    searchResults = {this.state.searchResults}
                />
            </div> ) ;
        }
        return ( <div> {content}
            { this.state.modalForm !== null &&
                <ModalForm show={true} formId={this.state.modalForm.formId}
                    {...this.state.modalForm}
                    ref = {this._modalFormRef}
                />
            }
            { this.state.askDialog !== null &&
                <AskDialog show={true} {...this.state.askDialog} />
            }
            <ToastContainer position="bottom-right" hideProgressBar={true} />
            { this._storeMsgs && <div>
                <textarea id="_stored_msg-info_toast_" ref="_stored_msg-info_toast_" defaultValue="" hidden={true} />
                <textarea id="_stored_msg-warning_toast_" ref="_stored_msg-warning_toast_" defaultValue="" hidden={true} />
                <textarea id="_stored_msg-error_toast_" ref="_stored_msg-error_toast_" defaultValue="" hidden={true} />
            </div> }
            { this._fakeUploads && <div>
                <textarea id="_stored_msg-upload_" ref="_stored_msg-upload_" defaultValue="" hidden={true} />
            </div> }
        </div> ) ;
    }

    componentDidMount() {

        // initialize
        PreviewableImage.initPreviewableImages() ;
        window.addEventListener( "keydown", this.onKeyDown.bind( this ) ) ;

        // check if the server started up OK
        let on_startup_ok = () => {
            // the backend server started up OK, continue our startup process
            this._onStartupTask( "dummy" ) ;
        }
        let on_startup_failure = () => {
            // the backend server had problems during startup; we hide the spinner
            // and leave the error message(s) on-screen.
            document.getElementById( "loading" ).style.display = "none" ;
        }
        axios.get(
            this.makeFlaskUrl( "/startup-messages" )
        ).then( resp => {
            // show any messages logged by the backend server as it started up
            [ "info", "warning", "error" ].forEach( msgType => {
                if ( resp.data[ msgType ] ) {
                    resp.data[ msgType ].forEach( msg => {
                        const pos = msg.indexOf( ":\n" ) ;
                        if ( pos !== -1 ) {
                            msg = ( <div> {msg.substr(0,pos+1)}
                                <div className="monospace"> {msg.substr(pos+2)} </div>
                                </div> ) ;
                        }
                        const funcName = "show" + msgType[0].toUpperCase() + msgType.substr(1) + "Toast" ;
                        this[ funcName ]( msg ) ;
                    } ) ;
                }
            } ) ;
            if ( resp.data.error && resp.data.error.length > 0 )
                on_startup_failure() ;
            else
                on_startup_ok() ;
        } ).catch( err => {
            let errorMsg = err.toString() ;
            if ( errorMsg.indexOf( "502" ) !== -1 || errorMsg.indexOf( "504" ) !== -1 )
                this.showErrorToast( <div> Couldn't connect to the backend Flask server. </div> ) ;
            else
                this.showErrorToast( <div> Couldn't get the startup messages: <div className="monospace"> {errorMsg} </div> </div> ) ;
            on_startup_failure() ;
        } ) ;
    }

    componentDidUpdate() {
        // we've finished rendering the page, check if we should set focus
        if ( this._setFocusTo ) {
            // yup - set focus to the requested control
            if ( this._setFocusTo.current )
                this._setFocusTo.current.focus() ;
            else
                this._setFocusTo.focus() ;
        }
        else {
            // nope - set focus to the search results (so that Page Up/Down et.al. will work)
            if ( ! this._modalFormRef.current ) {
                let elem = document.getElementById( "search-results" ) ;
                if ( elem )
                    setTimeout( () => elem.focus(), 10 ) ;
            }
        }
        this._setFocusTo = null ;
    }

    componentWillUnmount() {
        // clean up
        window.removeEventListener( "keydown", this.onKeyDown ) ;
    }

    onSearch( query ) {
        // run the search
        query = query.trim() ;
        if ( query.length === 0 ) {
            this.showErrorMsg( "Please enter something to search for.", this._searchFormRef.current.queryStringRef.current )
            return ;
        }
        this._doSearch( "/search", { query: query } ) ;
    }
    _doSearch( url, args, onDone ) {
        // do the search
        this.setWindowTitle( null ) ;
        this.setState( { searchResults: "(loading)" } ) ;
        args.no_hilite = this._disableSearchResultHighlighting ;
        axios.post(
            this.makeFlaskUrl( url ), args
        ).then( resp => {
            ReactDOM.findDOMNode( this._searchResultsRef.current ).scrollTo( 0, 0 ) ;
            this.setState( { searchResults: resp.data, searchSeqNo: this.state.searchSeqNo+1 } ) ;
            if ( onDone )
                onDone() ;
        } ).catch( err => {
            this.showErrorResponse( "The search query failed", err ) ;
            this.setState( { searchResults: null, searchSeqNo: this.state.searchSeqNo+1 } ) ;
        } ) ;
    }

    runSpecialSearch( url, args, onDone ) {
        // run the search
        this._searchFormRef.current.setState( { queryString: "" } ) ;
        if ( ! args )
            args = {} ;
        this._doSearch( url, args, onDone ) ;
    }
    _showPublishers() {
        this.runSpecialSearch( "/search/publishers", null,
            () => { this.setWindowTitle( "All publishers" ) }
        )
    }
    _showTechniqueArticles() {
        this.runSpecialSearch( "/search/tag/technique", {randomize:1},
            () => { this.setWindowTitle( "Technique" ) }
        )
    }
    _showTipsArticles() {
        this.runSpecialSearch( "/search/tag/tips", {randomize:1},
            () => { this.setWindowTitle( "Tips" ) }
        )
    }

    prependSearchResult( sr ) {
        // add a new entry to the start of the search results
        // NOTE: We do this after creating a new object, and while it isn't really the right thing
        // to do (since the new object might not actually be a result for the current search), it's nice
        // to give the user some visual feedback.
        let newSearchResults = [ sr ] ;
        newSearchResults.push( ...this.state.searchResults ) ;
        this.setState( { searchResults: newSearchResults } ) ;
    }

    updatePublisher( publ_id ) {
        // update the specified publisher in the UI
        this._doUpdateSearchResult(
            (sr) => ( sr._type === "publisher" && sr.publ_id === publ_id ),
            this.makeFlaskUrl( "/publisher/" + publ_id, {include_pubs:1,include_articles:1} )
        ) ;
        this.forceFlaskImageReload( "publisher", publ_id ) ;
    }
    updatePublication( pub_id ) {
        // update the specified publication in the UI
        this._doUpdateSearchResult(
            (sr) => ( sr._type === "publication" && sr.pub_id === pub_id ),
            this.makeFlaskUrl( "/publication/" + pub_id, {include_articles:1,deep:1} )
        ) ;
        this.forceFlaskImageReload( "publication", pub_id ) ;
    }
    _doUpdateSearchResult( srCheck, url ) {
        // find the target search result in the UI
        let newSearchResults = this.state.searchResults ;
        for ( let i=0 ; i < newSearchResults.length ; ++i ) {
            if ( srCheck( newSearchResults[i] ) ) {
                // found it - get the latest details from the backend
                axios.get( url ).then( resp => {
                    newSearchResults[i] = resp.data ;
                    this.setState( { searchResults: newSearchResults } ) ;
                } ).catch( err => {
                    this.showErrorResponse( "Can't get the updated search result details", err ) ;
                } ) ;
                break ; // nb: we assume there's only 1 instance
            }
        }
    }

    showModalForm( formId, title, titleColor, content, buttons ) {
        // prepare the buttons
        let buttons2 = [] ;
        for ( let b in buttons ) {
            let notify = buttons[ b ] ;
            buttons2[ b ] = () => {
                // a button was clicked - notify the caller
                if ( notify )
                    notify() ;
                // NOTE: We don't automatically dismiss the dialog here, since the form might not want to close
                // e.g. if it had problems updating something on the server. The form must dismiss the dialog manually.
            } ;
        }
        // show the dialog
        this.setState( {
            modalForm: { formId: formId, title: title, titleColor: titleColor, content: content, buttons: buttons2 },
        } ) ;
    }

    closeModalForm() {
        this.setState( { modalForm: null } ) ;
    }

    showInfoToast( msg ) { this._doShowToast( "info", msg, 5*1000 ) ; }
    showWarningToast( msg ) { this._doShowToast( "warning", msg, 15*1000 ) ; }
    showErrorToast( msg ) { this._doShowToast( "error", msg, false ) ; }
    _doShowToast( type, msg, autoClose ) {
        if ( this._storeMsgs ) {
            // save the message for the test suite to retrieve (nb: we also don't show the toast itself
            // since these build up when tests are running at high speed, and obscure elements that
            // we want to click on :-/
            this.setStoredMsg( type+"_toast", ReactDOMServer.renderToStaticMarkup(msg) ) ;
            return ;
        }
        toast( msg, { type: type, autoClose: autoClose } ) ;
    }

    setStoredMsg( msgType, msgData ) { this.refs[ "_stored_msg-" + msgType + "_" ].value = msgData ; }
    getStoredMsg( msgType ) { return this.refs[ "_stored_msg-" + msgType + "_" ].value }

    showErrorResponse( caption, err ) {
        let content ;
        if ( ! err.response )
            content = <div className="monospace"> {err.toString()} </div> ;
        else {
            if ( err.response.data.indexOf( "<!DOCTYPE" ) !== -1 || err.response.data.indexOf( "<html" ) !== -1 )
                content = <iframe title="error-response" srcDoc={err.response.data} /> ;
            else
                content = <div className="monospace"> {err.response.data} </div> ;
        }
        const msg = err.response ? err.response.statusText : err ;
        const buttons = { Close: () => this.closeModalForm() } ;
        this.showModalForm( "error-response", msg, "red",
            <div> {caption}: {content} </div>,
            buttons
        ) ;
    }

    showErrorMsg( content, setFocusTo ) {
        // show the error message in a modal dialog
        this.ask( content, "error",
            { "OK": null },
            setFocusTo
        ) ;
    }

    showWarnings( caption, warnings ) {
        this.showWarningToast( makeSmartBulletList( caption, warnings ) ) ;
    }

    ask( content, iconType, buttons, setFocusTo ) {
        // prepare the buttons
        let buttons2 = [] ;
        for ( let b in buttons ) {
            let notify = buttons[ b ] ;
            buttons2[ b ] = () => {
                // a button was clicked - notify the caller
                if ( notify )
                    notify() ;
                // dismiss the dialog
                this._setFocusTo = setFocusTo ;
                this.setState( { askDialog: null } ) ;
            } ;
        }
        // show the dialog
        this.setState( { askDialog: {
            content: <div> <img src={"/images/"+iconType+".png"} className="icon" alt={iconType+" icon"} /> {content} </div>,
            buttons: buttons2
        } } ) ;
    }

    onKeyDown( evt ) {
        // check if a modal dialog is open and Ctrl-Enter was pressed
        if ( this._modalFormRef.current && evt.keyCode === 13 && evt.ctrlKey ) {
            let dlg = ReactDOM.findDOMNode( this._modalFormRef.current ) ;
            if ( dlg ) {
                // yup - accept the dialog
                let btn = dlg.querySelector( ".MuiButton-root.ok" ) ;
                if ( btn )
                    btn.click() ;
                else
                    console.log( "ERROR: Can't find default button." ) ;
            }
        }
        // check for other shortcuts
        if ( ! this._modalFormRef.current ) {
            // Alt-R: set focus to query string
            if ( evt.key === "r" && evt.altKey ) {
                if ( this._searchFormRef.current ) {
                    let elem = this._searchFormRef.current.queryStringRef.current ;
                    if ( elem ) {
                        elem.focus() ;
                        elem.select() ;
                    }
                }
            }
        }
    }

    logInternalError( msg, detail ) {
        // log an internal error
        this.showErrorToast( <div>
            INTERNAL ERROR! <div>{msg}</div>
            {detail && <div className="monospace">{detail}</div>}
        </div> ) ;
        console.log( "INTERNAL ERROR: " + msg ) ;
        if ( detail )
            console.log( "  " + detail ) ;
    }

    makeAppUrl( url ) {
        // FUDGE! The test suite needs any URL parameters to passed on to the next page if a link is clicked.
        if ( this.isTestMode() )
            url += window.location.search ;
        return url ;
    }

    makeFlaskUrl( url, args ) {
        // generate a URL for the Flask backend server
        url = this._flaskBaseUrl + url ;
        if ( args ) {
            let args2 = [] ;
            for ( let a in args )
                args2.push( a + "=" + encodeURIComponent( args[a] ) ) ;
            url = url + "?" + args2.join("&") ;
        }
        return url ;
    }
    makeExternalDocUrl( url ) {
        // generate a URL for an external document
        if ( url.substr( 0, 2 ) === "$/" )
            url = url.substr( 2 ) ;
        return this.makeFlaskUrl( "/docs/" + encodeURIComponent(url) ) ;
    }

    makeFlaskImageUrl( type, imageId ) {
        // generate an image URL for the Flask backend server
        if ( ! imageId )
            return null ;
        let url = this.makeFlaskUrl( "/images/" + type + "/" + imageId ) ;
        const key = this._makeFlaskImageKey( type, imageId ) ;
        if ( ! this._flaskImageUrlVersions[ key ] ) {
            // NOTE: It would be nice to only add this if necessary (i.e. the user has changed
            // the image, thus requiring us to fetch the new image), but not doing so causes problems
            // in a dev environment, since we are constantly changing things in the database
            // outside the app (e.g. in tests) and the browser cache will get out of sync.
            this.forceFlaskImageReload( type, imageId ) ;
        }
        url += "?v=" + this._flaskImageUrlVersions[key] ;
        return url ;
    }
    forceFlaskImageReload( type, imageId ) {
        // bump the image's version#, which will force a new URL the next time makeFlaskImageUrl() is called
        const key = this._makeFlaskImageKey( type, imageId ) ;
        const version = this._flaskImageUrlVersions[ key ] ;
        // NOTE: It would be nice to start at 1, but this causes problems in a dev environment, since
        // we are constantly changing things in the database, and the browser cache will get out of sync.
        this._flaskImageUrlVersions[ key ] = version ? version+1 : Math.floor(Date.now()/1000) ;
    }
    _makeFlaskImageKey( type, imageId ) { return type + ":" + imageId ; }

    _onStartupTask( taskId ) {
        // flag that the specified startup task has completed
        let pos = this.state.startupTasks.indexOf( taskId ) ;
        if ( pos === -1 ) {
            this.logInternalError( "Unknown startup task.", "taskId = "+taskId ) ;
            return ;
        }
        this.state.startupTasks.splice( pos, 1 ) ;
        this.setState( { startupTasks: this.state.startupTasks } ) ;
        if ( this.state.startupTasks.length === 0 )
            this._onStartupComplete() ;
    }
    _onStartupComplete() {
        // startup has completed, we're ready to go
        if ( this.props.warning )
            this.showWarningToast( this.props.warning ) ;
        if ( this.props.doSearch )
            this.props.doSearch() ;
        // NOTE: We could preload the DataCache here (i.e. where it won't affect startup time),
        // but it will happen on every page load (e.g. /article/NNN or /publication/NNN),
        // which would probably hurt more than it helps (since the data isn't needed if the user
        // is only searching for stuff i.e. most of the time).
    }

    setWindowTitleFromSearchResults( srType, idField, idVal, nameField ) {
        for ( let sr of Object.entries( this.state.searchResults ) ) {
            if ( sr[1]._type === srType && String(sr[1][idField]) === idVal ) {
                this.setWindowTitle( typeof nameField === "function" ? nameField(sr[1]) : sr[1][nameField] ) ;
                return ;
            }
        }
        this.setWindowTitle( null ) ;
    }
    setWindowTitle( caption ) {
        document.title = caption ? APP_NAME + " - " + caption : APP_NAME ;
    }

    isTestMode() { return process.env.REACT_APP_TEST_MODE ; }
    isDisableConstraints() { return this._disableConstraints ; }
    isDisableConfirmDiscardChanges() { return this._disableConfirmDiscardChanges ; }
    isFakeUploads() { return this._fakeUploads ; }
    setTestAttribute( obj, attrName, attrVal ) {
        // set an attribute on an element (for testing porpoises)
        if ( obj && this.isTestMode() )
            obj.setAttribute( "testing--"+attrName, attrVal ) ;
    }

}
