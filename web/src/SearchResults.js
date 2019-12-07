import React from "react" ;
import "./SearchResults.css" ;
import { PublisherSearchResult } from "./PublisherSearchResult" ;
import { PublicationSearchResult } from "./PublicationSearchResult" ;
import { gAppRef } from "./index.js" ;

// --------------------------------------------------------------------

export class SearchResults extends React.Component
{

    render() {
        if ( ! this.props.searchResults || this.props.searchResults.length === 0 )
            return null ;
        let elems = [] ;
        this.props.searchResults.forEach( sr => {
            if ( sr.type === "publisher" ) {
                elems.push( <PublisherSearchResult key={"publisher:"+sr.publ_id} data={sr}
                    onDelete = { this.onDeleteSearchResult.bind( this ) }
                /> ) ;
            } else if ( sr.type === "publication" ) {
                elems.push( <PublicationSearchResult key={"publication:"+sr.pub_id} data={sr}
                    onDelete = { this.onDeleteSearchResult.bind( this ) }
                /> ) ;
            } else {
                gAppRef.logInternalError( "Unknown search result type.", sr.type ) ;
            }
        } ) ;
        return <div id="search-results" seqno={this.props.seqNo}> {elems} </div> ;
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
        gAppRef.logInternalError( "Tried to delete an unknown search result", idName+"="+idVal ) ;
    }

}
