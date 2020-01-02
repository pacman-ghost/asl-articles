import React from "react" ;
import "./SearchForm.css" ;

// --------------------------------------------------------------------

export default class SearchForm extends React.Component
{

    constructor( props ) {
        super( props ) ;
        this.state = {
            queryString: "",
        } ;
    }

    render() {
        return (
            <form id="search-form" onSubmit={this.onSearch.bind(this)}>
            <label className="caption"> Search for: </label>
            <input type="text" className="query"
                value = {this.state.queryString}
                onChange = { e => this.setState( { queryString: e.target.value } ) }
                ref = "queryString"
                autoFocus
            />
            <button type="submit"> Go </button>
            </form>
        ) ;
    }

    onSearch( evt ) {
        evt.preventDefault() ;
        this.props.onSearch( this.state.queryString ) ;
    }

    focusQueryString() { this.refs.queryString.focus() ; }

}
