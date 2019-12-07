import React from "react" ;
import { gAppRef } from "./index.js" ;
import { makeOptionalLink, pluralString } from "./utils.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class PublisherSearchResult extends React.Component
{

    render() {
        return ( <div className="search-result publisher">
            <div className="name"> { makeOptionalLink( this.props.data.publ_name, this.props.data.publ_url ) }
                <img src="/images/edit.png" className="edit" onClick={this.onEditPublisher.bind(this)} alt="Edit this publisher." />
                <img src="/images/delete.png" className="delete" onClick={this.onDeletePublisher.bind(this)} alt="Delete this publisher." />
            </div>
            <div className="description" dangerouslySetInnerHTML={{__html: this.props.data.publ_description}} />
        </div> ) ;
    }

    static onNewPublisher( notify ) {
        PublisherSearchResult._doEditPublisher( {}, (newVals,refs) => {
            axios.post( gAppRef.state.flaskBaseUrl + "/publisher/create?list=1", newVals )
            .then( resp => {
                // update the cached publishers
                gAppRef.caches.publishers = resp.data.publishers ;
                // unload any cleaned values
                for ( let r in refs ) {
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

    onEditPublisher() {
        PublisherSearchResult._doEditPublisher( this.props.data, (newVals,refs) => {
            // send the updated details to the server
            newVals.publ_id = this.props.data.publ_id ;
            axios.post( gAppRef.state.flaskBaseUrl + "/publisher/update?list=1", newVals )
            .then( resp => {
                // update the cached publishers
                gAppRef.caches.publishers = resp.data.publishers ;
                // update the UI with the new details
                for ( let r in refs )
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
            <div className="row description"> <label> Description: </label>
                <textarea defaultValue={vals.publ_description} ref={(r) => refs.publ_description=r} />
            </div>
            <div className="row url"> <label> Web: </label>
                <input type="text" defaultValue={vals.publ_url} ref={(r) => refs.publ_url=r} />
            </div>
        </div> ;
        const buttons = {
            OK: () => {
                // unload the new values
                let newVals = {} ;
                for ( let r in refs )
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

    onDeletePublisher() {
        let doDelete = ( nPubs ) => {
            let warning ;
            if ( typeof nPubs === "number" ) {
                if ( nPubs === 0 )
                    warning = <div> No publications will be deleted. </div> ;
                else
                    warning = <div> { pluralString(nPubs,"associated publication") + " will also be deleted." } </div> ;
            } else {
                warning = ( <div> <img className="icon" src="/images/error.png" alt="Error." />
                    WARNING: Couldn't check if any associated publications will be deleted:
                    <div className="monospace"> {nPubs.toString()} </div>
                </div> ) ;
            }
            let content = ( <div>
                Do you want to delete this publisher?
                <div style={{margin:"0.5em 0 0.5em 2em",fontStyle:"italic"}} dangerouslySetInnerHTML={{__html: this.props.data.publ_name}} />
                {warning}
            </div> ) ;
            gAppRef.ask( content, {
                "OK": () => {
                    // delete the publisher on the server
                    axios.get( gAppRef.state.flaskBaseUrl + "/publisher/delete/" + this.props.data.publ_id + "?list=1" )
                    .then( resp => {
                        // update the cached publishers
                        gAppRef.caches.publishers = resp.data.publishers ;
                        gAppRef.caches.publications = resp.data.publications ; // nb: because of cascading deletes
                        // update the UI
                        this.props.onDelete( "publ_id", this.props.data.publ_id ) ;
                        resp.data.deletedPublications.forEach( pub_id => {
                            this.props.onDelete( "pub_id", pub_id ) ;
                        } ) ;
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
        } ;
        // get the publisher details
        axios.get( gAppRef.state.flaskBaseUrl + "/publisher/" + this.props.data.publ_id )
        .then( resp => {
            doDelete( resp.data.nPublications ) ;
        } )
        .catch( err => {
            doDelete( err ) ;
        } ) ;
    }

}
