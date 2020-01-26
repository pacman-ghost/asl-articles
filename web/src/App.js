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
        this._fakeUploads = this.isTestMode() && this.args.fake_uploads ;

        // initialize
        this._searchFormRef = React.createRef() ;
        this._modalFormRef = React.createRef() ;

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
            content = <div id="loading"> <img id="loading" src="/images/loading.gif" alt="Loading..." /></div> ;
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
                <SearchResults seqNo={this.state.searchSeqNo} searchResults={this.state.searchResults} />
            </div> ) ;
        }
        return ( <div> {content}
            { this.state.modalForm !== null &&
                <ModalForm show={true} formId={this.state.modalForm.formId}
                    title = {this.state.modalForm.title} titleColor = {this.state.modalForm.titleColor}
                    content = {this.state.modalForm.content}
                    buttons = {this.state.modalForm.buttons}
                    ref = {this._modalFormRef}
                />
            }
            { this.state.askDialog !== null &&
                <AskDialog show={true} content={this.state.askDialog.content} buttons={this.state.askDialog.buttons} />
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
        // initialize the caches
        // NOTE: We maintain caches of key objects, so that we can quickly populate droplists. The backend server returns
        // updated lists after any operation that could change them (create/update/delete), which is simpler and less error-prone
        // than trying to manually keep our caches in sync. It's less efficient, but it won't happen too often, there won't be
        // too many entries, and the database server is local.
        this.caches = {} ;
        ["publishers","publications","authors","scenarios","tags"].forEach( (type) => {
            axios.get( this.makeFlaskUrl( "/" + type ) )
            .then( resp => {
                this.caches[ type ] = resp.data ;
                this._onStartupTask( "caches." + type ) ;
            } )
            .catch( err => {
                this.showErrorToast( <div> Couldn't load the {type}: <div className="monospace"> {err.toString()} </div> </div> ) ;
            } ) ;
        } ) ;
        // install our key handler
        window.addEventListener( "keydown", this.onKeyDown.bind( this ) ) ;
    }

    componentWillUnmount() {
        // clean up
        window.removeEventListener( "keydown", this.onKeyDown ) ;
    }

    onSearch( query ) {
        // run the search
        query = query.trim() ;
        if ( query.length === 0 ) {
            this.focusQueryString() ;
            this.showErrorMsg( "Please enter something to search for." )
            return ;
        }
        axios.post( this.makeFlaskUrl( "/search" ), {
            query: query,
            no_hilite: this._disableSearchResultHighlighting,
        } )
        .then( resp => {
            this.setState( { searchResults: resp.data, searchSeqNo: this.state.searchSeqNo+1 } ) ;
            this.focusQueryString() ;
        } )
        .catch( err => {
            this.showErrorToast( <div> The search query failed: <div className="monospace"> {err.toString()} </div> </div> ) ;
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
        setTimeout( () => { this.focusQueryString() ; }, 100 ) ;
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

    showErrorMsg( content ) {
        // show the error message in a modal dialog
        this.ask( content, "error",
            { "OK": null }
        ) ;
    }

    showWarnings( caption, warnings ) {
        let content ;
        if ( !warnings || warnings.length === 0 )
            content = caption ;
        else if ( warnings.length === 1 )
            content = <div> {caption} <p> {warnings[0]} </p> </div> ;
        else {
            let bullets = warnings.map( (warning,i) => <li key={i}> {warning} </li> ) ;
            content = <div> {caption} <ul> {bullets} </ul> </div> ;
        }
        this.showWarningToast( content ) ;
    }

    ask( content, iconType, buttons ) {
        // prepare the buttons
        let buttons2 = [] ;
        for ( let b in buttons ) {
            let notify = buttons[ b ] ;
            buttons2[ b ] = () => {
                // a button was clicked - notify the caller
                if ( notify )
                    notify() ;
                // dismiss the dialog
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
    makeFlaskImageUrl( type, image_id, force ) {
        // generate an image URL for the Flask backend server
        if ( ! image_id )
            return null ;
        let url = this.makeFlaskUrl( "/images/" + type + "/" + image_id ) ;
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

    focusQueryString() { this._searchFormRef.current.focusQueryString() ; }

    isTestMode() { return process.env.REACT_APP_TEST_MODE ; }
    isFakeUploads() { return this._fakeUploads ; }
    setTestAttribute( obj, attrName, attrVal ) {
        // set an attribute on an element (for testing porpoises)
        if ( obj && this.isTestMode() )
            obj.setAttribute( "testing--"+attrName, attrVal ) ;
    }

}
