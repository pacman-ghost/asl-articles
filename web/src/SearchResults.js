import React from "react" ;
import "./SearchResults.css" ;

// --------------------------------------------------------------------

export default class SearchResults extends React.Component
{
    render() {
        if ( ! this.props.searchResults || this.props.searchResults.length === 0 )
            return null ;
        const elems = this.props.searchResults.map(
            sr => <SearchResult key={sr.id} data={sr} />
        ) ;
        return ( <div id="search-results" seqno={this.props.seqNo}>
            {elems}
        </div> ) ;
    }
}

// --------------------------------------------------------------------

class SearchResult extends React.Component
{
    render() {
        return (
            <div className="search-result">
            { JSON.stringify( this.props.data ) }
            </div>
        ) ;
    }
}
