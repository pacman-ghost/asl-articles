import React from "react" ;
import "./SearchResults.css" ;
import { PublisherSearchResult } from "./PublisherSearchResult" ;
import { PublicationSearchResult } from "./PublicationSearchResult" ;
import { ArticleSearchResult } from "./ArticleSearchResult" ;
import { gAppRef } from "./index.js" ;

// --------------------------------------------------------------------

export class SearchResults extends React.Component
{

    render() {
        let results ;
        if ( this.props.searchResults && this.props.searchResults.error !== undefined )
            results = "ERROR: " + this.props.searchResults.error ;
        else if ( ! this.props.searchResults || this.props.searchResults.length === 0 )
            results = (this.props.seqNo === 0) ? null : <div className="no-results"> No results. </div> ;
        else {
            results = [] ;
            this.props.searchResults.forEach( sr => {
                if ( sr.type === "publisher" ) {
                    results.push( <PublisherSearchResult key={"publisher:"+sr.publ_id} data={sr}
                        onDelete = { this.onDeleteSearchResult.bind( this ) }
                    /> ) ;
                } else if ( sr.type === "publication" ) {
                    results.push( <PublicationSearchResult key={"publication:"+sr.pub_id} data={sr}
                        onDelete = { this.onDeleteSearchResult.bind( this ) }
                    /> ) ;
                } else if ( sr.type === "article" ) {
                    results.push( <ArticleSearchResult key={"article:"+sr.article_id} data={sr}
                        onDelete = { this.onDeleteSearchResult.bind( this ) }
                    /> ) ;
                } else {
                    gAppRef.logInternalError( "Unknown search result type.", "srType = "+sr.type ) ;
                }
            } ) ;
        }
        return <div id="search-results" seqno={this.props.seqNo}> {results} </div> ;
    }

    onDeleteSearchResult( idName, idVal ) {
        for ( let i=0 ; i < this.props.searchResults.length ; ++i ) {
            const sr = this.props.searchResults[ i ] ;
            if ( sr[idName] === idVal ) {
                this.props.searchResults.splice( i, 1 ) ;
                this.forceUpdate() ;
                return ;
            }
        }
        gAppRef.logInternalError( "Tried to delete an unknown search result.", idName+" = "+idVal ) ;
    }

}
