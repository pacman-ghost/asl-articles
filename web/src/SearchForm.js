import React from "react" ;
import "./SearchForm.css" ;

// --------------------------------------------------------------------

export default class SearchForm extends React.Component
{

    constructor( props ) {
        // initialize
        super( props ) ;
        this.state = {
            queryString: "",
        } ;

        // initialize
        this.queryStringRef = React.createRef() ;
    }

    render() {
        return (
            <form id="search-form" onSubmit={this.onSearch.bind(this)}>
            <label className="caption"> Sea<u>r</u>ch&nbsp;for: </label>
            <input type="text" className="query"
                value = {this.state.queryString}
                onChange = { e => this.setState( { queryString: e.target.value } ) }
                onKeyDown = { this.onKeyDown.bind( this ) }
                ref = {this.queryStringRef}
                autoFocus
            />
            <button type="submit" title="Search the database." />
            </form>
        ) ;
    }

    onSearch( evt ) {
        evt.preventDefault() ;
        this.props.onSearch( this.state.queryString ) ;
    }

    onKeyDown( evt ) {
        // forward up/down/PgUp/PgDown to the search results pane
        if ( evt.keyCode === 38 || evt.keyCode === 40 || evt.keyCode === 33 || evt.keyCode === 34 ) {
            let elem = document.getElementById( "search-results" ) ;
            elem.focus() ;
            elem.dispatchEvent(
                new KeyboardEvent( "keypress", { key: evt.key, code: evt.code } )
            ) ;
        }
    }

}
