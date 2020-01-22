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
        this._queryStringRef = React.createRef() ;
    }

    render() {
        return (
            <form id="search-form" onSubmit={this.onSearch.bind(this)}>
            <label className="caption"> Search&nbsp;for: </label>
            <input type="text" className="query"
                value = {this.state.queryString}
                onChange = { e => this.setState( { queryString: e.target.value } ) }
                ref = {this._queryStringRef}
                autoFocus
            />
            <button type="submit" alt="Search the database." />
            </form>
        ) ;
    }

    onSearch( evt ) {
        evt.preventDefault() ;
        this.props.onSearch( this.state.queryString ) ;
    }

    focusQueryString() { this._queryStringRef.current.focus() ; }

}
