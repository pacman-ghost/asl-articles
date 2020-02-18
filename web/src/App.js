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
import { makeSmartBulletList } from "./utils.js" ;
import "./App.css" ;

const axios = require( "axios" ) ;
const queryString = require( "query-string" ) ;

// --------------------------------------------------------------------

export default class App extends React.Component
{
    constructor( props ) {

        // initialize the App
        super( props ) ;
        this.state = {
            searchResults: [],
            searchSeqNo: 0,
            modalForm: null,
            askDialog: null,
            startupTasks: [ "caches.publishers", "caches.publications", "caches.authors", "caches.scenarios", "caches.tags" ],
        } ;

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
                    <MenuItem id="menu-new-publisher"
                        onSelect = { () => PublisherSearchResult.onNewPublisher( this._onNewPublisher.bind(this) ) }
                    >New publisher</MenuItem>
                    <MenuItem id="menu-new-publication"
                        onSelect = { () => PublicationSearchResult.onNewPublication( this._onNewPublication.bind(this) ) }
                    >New publication</MenuItem>
                    <MenuItem id="menu-new-article"
                        onSelect = { () => ArticleSearchResult.onNewArticle( this._onNewArticle.bind(this) ) }
                    >New article</MenuItem>
                </MenuList>
            </Menu> ) ;
            // generate the main content
            content = ( <div>
                <div id="header">
                    <img className="logo" src="/images/app.png" alt="Logo" />
                    <div className="app-name"> ASL Articles </div>
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
        // install our key handler
        window.addEventListener( "keydown", this.onKeyDown.bind( this ) ) ;

        // check if the server started up OK
        let on_startup_ok = () => {
            // the backend server started up OK, continue our startup process
            // initialize the caches
            // NOTE: We maintain caches of key objects, so that we can quickly populate droplists. The backend server returns
            // updated lists after any operation that could change them (create/update/delete), which is simpler and less error-prone
            // than trying to manually keep our caches in sync. It's less efficient, but it won't happen too often, there won't be
            // too many entries, and the database server is local.
            this.caches = {} ;
            [ "publishers", "publications", "authors", "scenarios", "tags" ].forEach( type => {
                axios.get( this.makeFlaskUrl( "/" + type ) )
                .then( resp => {
                    this.caches[ type ] = resp.data ;
                    this._onStartupTask( "caches." + type ) ;
                } )
                .catch( err => {
                    this.showErrorToast( <div> Couldn't load the {type}: <div className="monospace"> {err.toString()} </div> </div> ) ;
                } ) ;
            } ) ;
        }
        let on_startup_failure = () => {
            // the backend server had problems during startup; we hide the spinner
            // and leave the error message(s) on-screen.
            document.getElementById( "loading" ).style.display = "none" ;
        }
        axios.get( this.makeFlaskUrl( "/startup-messages" ) )
        .then( resp => {
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
        } )
        .catch( err => {
            this.showErrorToast( <div> Couldn't get the startup messages: <div className="monospace"> {err.toString()} </div> </div> ) ;
            on_startup_failure() ;
        } ) ;
    }

    componentDidUpdate() {
        // we've finished rendering the page, check if we should set focus
        if ( this._setFocusTo ) {
            if ( this._setFocusTo.current )
                this._setFocusTo.current.focus() ;
            else
                this._setFocusTo.focus() ;
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
    searchForPublisher( publ_id ) { this._onSpecialSearch( "/search/publisher/" + publ_id ) ; }
    searchForPublication( pub_id ) { this._onSpecialSearch( "/search/publication/" + pub_id ) ; }
    searchForArticle( article_id ) { this._onSpecialSearch( "/search/article/" + article_id ) ; }
    searchForAuthor( author_id ) { this._onSpecialSearch( "/search/author/" + author_id ) ; }
    searchForTag( tag ) { this._onSpecialSearch( "/search/tag/" + encodeURIComponent(tag) ) ; }
    _onSpecialSearch( url ) {
        // run the search
        this._searchFormRef.current.setState( { queryString: "" } ) ;
        this._doSearch( url, {} ) ;
    }
    _doSearch( url, args ) {
        // do the search
        this.setState( { searchResults: "(loading)" } ) ;
        args.no_hilite = this._disableSearchResultHighlighting ;
        axios.post(
            this.makeFlaskUrl( url ), args
        )
        .then( resp => {
            ReactDOM.findDOMNode( this._searchResultsRef.current ).scrollTo( 0, 0 ) ;
            this._setFocusTo = this._searchFormRef.current.queryStringRef.current ;
            this.setState( { searchResults: resp.data, searchSeqNo: this.state.searchSeqNo+1 } ) ;
        } )
        .catch( err => {
            this.showErrorResponse( "The search query failed", err ) ;
            this.setState( { searchResults: null, searchSeqNo: this.state.searchSeqNo+1 } ) ;
        } ) ;
    }

    _onNewPublisher( publ_id, vals ) { this._addNewSearchResult( vals, "publisher", "publ_id", publ_id ) ; }
    _onNewPublication( pub_id, vals ) { this._addNewSearchResult( vals, "publication", "pub_id", pub_id ) ; }
    _onNewArticle( article_id, vals ) { this._addNewSearchResult( vals, "article", "article_id", article_id ) ; }
    _addNewSearchResult( vals, srType, idName, idVal ) {
        // add the new search result to the start of the search results
        // NOTE: This isn't really the right thing to do, since the new object might not actually be
        // a result for the current search, but it's nice to give the user some visual feedback.
        vals.type = srType ;
        vals[ idName ] = idVal ;
        let newSearchResults = [ vals ] ;
        newSearchResults.push( ...this.state.searchResults ) ;
        this.setState( { searchResults: newSearchResults } ) ;
    }

    updatePublications( pubs ) {
        // update the cache
        let pubs2 = {} ;
        for ( let i=0 ; i < pubs.length ; ++i ) {
            const pub = pubs[ i ] ;
            this.caches.publications[ pub.pub_id ] = pub ;
            pubs2[ pub.pub_id ] = pub ;
        }
        // update the UI
        let newSearchResults = this.state.searchResults ;
        for ( let i=0 ; i < newSearchResults.length ; ++i ) {
            if ( newSearchResults[i].type === "publication" && pubs2[ newSearchResults[i].pub_id ] ) {
                newSearchResults[i] = pubs2[ newSearchResults[i].pub_id ] ;
                newSearchResults[i].type = "publication" ;
            }
        }
        this.setState( { searchResults: newSearchResults } ) ;
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
        this._setFocusTo = this._searchFormRef.current.queryStringRef ;
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
                this._setFocusTo = setFocusTo ? setFocusTo : this._searchFormRef.current.queryStringRef ;
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
        if ( this._modalFormRef && evt.keyCode === 13 && evt.ctrlKey ) {
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

    makeTagLists( tags ) {
        // convert the tags into a list suitable for CreatableSelect
        // NOTE: react-select uses the "value" field to determine which choices have already been selected
        // and thus should not be shown in the droplist of available choices.
        let tagList = [] ;
        if ( tags )
            tags.map( tag => tagList.push( { value: tag, label: tag } ) ) ;
        // create another list for all known tags
        let allTags = this.caches.tags.map( tag => { return { value: tag[0], label: tag[0] } } ) ;
        return [ tagList, allTags ] ;
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
    makeFlaskImageUrl( type, imageId, force ) {
        // generate an image URL for the Flask backend server
        if ( ! imageId )
            return null ;
        let url = this.makeFlaskUrl( "/images/" + type + "/" + imageId ) ;
        if ( force )
            url += "?foo=" + Math.random() ; // FUDGE! To bypass the cache :-/
        return url ;
    }

    _onStartupTask( taskId ) {
        // flag that the specified startup task has completed
        let pos = this.state.startupTasks.indexOf( taskId ) ;
        if ( pos === -1 ) {
            this.logInternalError( "Unknown startup task.", "taskId = "+taskId ) ;
            return ;
        }
        this.state.startupTasks.splice( pos, 1 ) ;
        this.setState( { startupTasks: this.state.startupTasks } ) ;
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
