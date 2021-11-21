import React from "react" ;
import ReactDOM from "react-dom" ;
import "./SearchResults.css" ;
import { PublisherSearchResult } from "./PublisherSearchResult" ;
import { PublicationSearchResult } from "./PublicationSearchResult" ;
import { ArticleSearchResult } from "./ArticleSearchResult" ;
import { gAppRef } from "./App.js" ;

// --------------------------------------------------------------------

export class SearchResults extends React.Component
{

    render() {

        let results ;
        if ( this.props.searchResults && this.props.searchResults.error !== undefined ) {
            // show the error message
            results = "ERROR: " + this.props.searchResults.error ;
        } else if ( ! this.props.searchResults || this.props.searchResults.length === 0 ) {
            // show that no search results were found
            results = (this.props.seqNo === 0) ? null : <div className="no-results"> No results. </div> ;
        } else if ( this.props.searchResults === "(loading)" ) {
            // show the loading spinner
            results = ( <div className="loading">
                <img id="loading" src="/images/loading.gif" alt="Loading..." style={{display:"none"}} />
                </div> ) ;
            setTimeout( function() {
                let elem = document.getElementById( "loading" ) ;
                if ( elem )
                    elem.style.display = "block" ;
            }, 500 ) ;
        } else {
            // track articles
            let articleRefs = {} ;
            function scrollToArticle( article_id ) {
                const node = ReactDOM.findDOMNode( articleRefs[article_id] ) ;
                if ( node )
                    node.scrollIntoView() ;
                else
                    document.location = gAppRef.makeAppUrl( "/article/" + article_id ) ;
            }
            // render the search results
            results = [] ;
            this.props.searchResults.forEach( sr => {
                if ( sr._type === "publisher" ) {
                    results.push( <PublisherSearchResult key={"publisher:"+sr.publ_id} data={sr}
                        onDelete = { (n,v,i) => this.onDeleteSearchResult( n, v, i ) }
                    /> ) ;
                } else if ( sr._type === "publication" ) {
                    results.push( <PublicationSearchResult key={"publication:"+sr.pub_id} data={sr}
                        onDelete = { (n,v,i) => this.onDeleteSearchResult( n, v, i ) }
                        onArticleClick = { (a) => scrollToArticle(a) }
                    /> ) ;
                } else if ( sr._type === "article" ) {
                    results.push( <ArticleSearchResult key={"article:"+sr.article_id} data={sr}
                        onDelete = { (n,v,i) => this.onDeleteSearchResult( n, v, i ) }
                        ref = { r => articleRefs[sr.article_id] = r }
                    /> ) ;
                } else {
                    gAppRef.logInternalError( "Unknown search result type.", "srType = "+sr._type ) ;
                }
            } ) ;
        }
        return <div id="search-results" seqno={this.props.seqNo}> {results} </div> ;
    }

    onDeleteSearchResult( idName, idVal, ignoreNotFound ) {
        // look for the specified search result
        for ( let i=0 ; i < this.props.searchResults.length ; ++i ) {
            const sr = this.props.searchResults[ i ] ;
            if ( sr[idName] === idVal ) {
                // found it - remove it the UI
                this.props.searchResults.splice( i, 1 ) ;
                this.forceUpdate() ;
                return ;
            }
        }
        // the search result wasn't found
        // NOTE: This would normally indicate an internal coding error, but there is one case where
        // it can happen: when a publisher or publication is deleted, we want to also delete all
        // their child objects, but they may not necessarily be on-screen.
        if ( ! ignoreNotFound ) {
            gAppRef.logInternalError(
                "Tried to delete an unknown search result.", idName+" = "+idVal
            ) ;
        }
    }

}
