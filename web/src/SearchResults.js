import React from "react" ;
import "./SearchResults.css" ;
import { gAppRef } from "./index.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class SearchResults extends React.Component
{

    render() {
        if ( ! this.props.searchResults || this.props.searchResults.length === 0 )
            return null ;
        const elems = this.props.searchResults.map(
            sr => <SearchResult key={sr.publ_id} publ_id={sr.publ_id} data={sr}
                onDelete = { this.onDeleteSearchResult.bind( this ) }
            />
        ) ;
        return ( <div id="search-results" seqno={this.props.seqNo}>
            {elems}
        </div> ) ;
    }

    onDeleteSearchResult( id ) {
        for ( let i=0 ; i < this.props.searchResults.length ; ++i ) {
            const sr = this.props.searchResults[ i ] ;
            if ( sr.publ_id === id ) {
                this.props.searchResults.splice( i, 1 ) ;
                this.forceUpdate() ;
                return ;
            }
        }
        gAppRef.logInternalError( "Tried to delete an unknown search result", "id="+id ) ;
    }

}

// --------------------------------------------------------------------

export class SearchResult extends React.Component
{

    render() {
        function make_name( data ) {
            if ( data.publ_url )
                return ( <a href={data.publ_url} target="_blank" rel="noopener noreferrer">
                    {data.publ_name}
                    </a>
                ) ;
            else
                return <span dangerouslySetInnerHTML={{__html: data.publ_name}} /> ;
        }
        return ( <div className="search-result">
            <div className="name">
                { make_name( this.props.data ) }
                <img src="/images/edit.png" className="edit" onClick={this.onEditPublisher.bind(this)} alt="Edit this publisher." />
                <img src="/images/delete.png" className="delete" onClick={this.onDeletePublisher.bind(this)} alt="Delete this publisher." />
            </div>
            <div className="description" dangerouslySetInnerHTML={{__html: this.props.data.publ_description}} />
        </div> ) ;
    }

    onEditPublisher() {
        SearchResult._doEditPublisher( this.props.data, (newVals,refs) => {
            // send the updated details to the server
            newVals.publ_id = this.props.publ_id ;
            axios.post( gAppRef.state.flaskBaseUrl + "/publishers/update", newVals )
            .then( resp => {
                // update the UI with the new details
                for ( var r in refs )
                    this.props.data[ r ] = (resp.data.cleaned && resp.data.cleaned[r]) || newVals[r] ;
                this.forceUpdate() ;
                if ( resp.data.warning )
                    gAppRef.showWarningToast( <div> The publisher was updated OK. <p> {resp.data.warning} </p> </div> ) ;
                else
                    gAppRef.showInfoToast( <div> The publisher was updated OK. </div> ) ;
                gAppRef.closeModalForm() ;
            } )
            .catch( err => {
                gAppRef.showErrorMsg( <div> Couldn't update the publisher: <div className="monospace"> {err.toString()} </div> </div> ) ;
            } ) ;
        } );
    }

    static _doEditPublisher( vals, notify ) {
        let refs = {} ;
        const content = <div>
            <div className="row name"> <label> Name: </label>
                <input type="text" defaultValue={vals.publ_name} ref={(r) => refs.publ_name=r} />
            </div>
            <div className="row url"> <label> Web: </label>
                <input type="text" defaultValue={vals.publ_url} ref={(r) => refs.publ_url=r} />
            </div>
            <div className="row description"> <label> Description: </label>
                <textarea defaultValue={vals.publ_description} ref={(r) => refs.publ_description=r} />
            </div>
        </div> ;
        const buttons = {
            OK: () => {
                // unload the new values
                let newVals = {} ;
                for ( var r in refs )
                    newVals[ r ] = refs[r].value.trim() ;
                if ( newVals.publ_name === "" ) {
                    gAppRef.showErrorMsg( <div> Please specify the publisher's name. </div>) ;
                    return ;
                }
                // notify the caller about the new details
                notify( newVals, refs ) ;
            },
            Cancel: () => { gAppRef.closeModalForm() ; },
        } ;
        const isNew = Object.keys( vals ).length === 0 ;
        gAppRef.showModalForm( isNew?"New publisher":"Edit publisher", content, buttons ) ;
    }

    static onNewPublisher( notify ) {
        SearchResult._doEditPublisher( {}, (newVals,refs) => {
            axios.post( gAppRef.state.flaskBaseUrl + "/publishers/create", newVals )
            .then( resp => {
                // unload any cleaned values
                for ( var r in refs ) {
                    if ( resp.data.cleaned && resp.data.cleaned[r] )
                        newVals[ r ] = resp.data.cleaned[ r ] ;
                }
                // update the UI with the new details
                notify( resp.data.publ_id, newVals ) ;
                if ( resp.data.warning )
                    gAppRef.showWarningToast( <div> The new publisher was created OK. <p> {resp.data.warning} </p> </div> ) ;
                else
                    gAppRef.showInfoToast( <div> The new publisher was created OK. </div> ) ;
                gAppRef.closeModalForm() ;
            } )
            .catch( err => {
                gAppRef.showErrorMsg( <div> Couldn't create the publisher: <div className="monospace"> {err.toString()} </div> </div> ) ;
            } ) ;
        } ) ;
    }

    onDeletePublisher() {
        // confirm the operation
        const content = ( <div>
            Do you want to delete this publisher?
            <div style={{margin:"0.5em 0 0 2em",fontStyle:"italic"}} dangerouslySetInnerHTML={{__html: this.props.data.publ_name}} />
        </div> ) ;
        gAppRef.ask( content, {
            "OK": () => {
                // delete the publisher on the server
                axios.get( gAppRef.state.flaskBaseUrl + "/publishers/delete/" + this.props.data.publ_id )
                .then( resp => {
                    // update the UI
                    this.props.onDelete( this.props.data.publ_id ) ;
                    if ( resp.data.warning )
                        gAppRef.showWarningToast( <div> The publisher was deleted. <p> {resp.data.warning} </p> </div> ) ;
                    else
                        gAppRef.showInfoToast( <div> The publisher was deleted. </div> ) ;
                } )
                .catch( err => {
                    gAppRef.showErrorToast( <div> Couldn't delete the publisher: <div className="monospace"> {err.toString()} </div> </div> ) ;
                } ) ;
            },
            "Cancel": null,
        } ) ;
    }

}
