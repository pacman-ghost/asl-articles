import React from "react" ;
import SearchForm from "./SearchForm" ;
import SearchResults from "./SearchResults" ;
import "./App.css" ;

const axios = require( "axios" ) ;
const queryString = require( "query-string" ) ;

// --------------------------------------------------------------------

export default class App extends React.Component
{

    constructor( props ) {
        // figure out the base URL of the Flask backend server
        // NOTE: We allow the caller to do this since the test suite will usually spin up
        // it's own Flask server, but talks to an existing React server, so we need some way
        // for pytest to change which Flask server the React frontend code should tak to.
        const args = queryString.parse( window.location.search ) ;
        let baseUrl = process.env.REACT_APP_TEST_MODE ? args._flask : null ;
        if ( ! baseUrl )
            baseUrl = process.env.REACT_APP_FLASK_URL ;

        super( props ) ;
        this.state = {
            baseUrl: baseUrl,
            searchResults: [],
            seqNo: 0,
        } ;
    }

    render() {
        return ( <div>
            <SearchForm onSearch={this.onSearch.bind(this)} />
            <SearchResults seqNo={this.state.seqNo} searchResults={this.state.searchResults} />
        </div> ) ;
    }

    onSearch( query ) {
        // run the search
        console.log( "SEARCH: " + query ) ;
        axios.post( this.state.baseUrl + "/search", {
            query: query
        } )
        .then( resp => {
            console.log( "RESPONSE:", resp.data ) ;
            this.setState( { searchResults: resp.data, seqNo: this.state.seqNo+1 } ) ;
        } )
        .catch( err => {
            console.log( "ERROR:", err ) ;
            this.setState( { searchResults: null, seqNo: this.state.seqNo+1 } ) ;
        } ) ;
    }

}
