import React from "react" ;
import { PublisherSearchResult2 } from "./PublisherSearchResult2.js"
import { gAppRef } from "./index.js" ;
import { makeOptionalLink, pluralString, applyUpdatedVals, removeSpecialFields } from "./utils.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class PublisherSearchResult extends React.Component
{

    render() {
        const display_name = this.props.data[ "publ_name!" ] || this.props.data.publ_name ;
        const display_description = this.props.data[ "publ_description!" ] || this.props.data.publ_description ;
        const image_url = gAppRef.makeFlaskImageUrl( "publisher", this.props.data.publ_image_id, true ) ;
        return ( <div className="search-result publisher"
                    ref = { r => gAppRef.setTestAttribute( r, "publ_id", this.props.data.publ_id ) }
            >
            <div className="name">
                { image_url && <img src={image_url} className="image" alt="Publisher." /> }
                { makeOptionalLink( display_name, this.props.data.publ_url ) }
                <img src="/images/edit.png" className="edit" onClick={this.onEditPublisher.bind(this)} alt="Edit this publisher." />
                <img src="/images/delete.png" className="delete" onClick={this.onDeletePublisher.bind(this)} alt="Delete this publisher." />
            </div>
            <div className="description" dangerouslySetInnerHTML={{__html: display_description}} />
        </div> ) ;
    }

    static onNewPublisher( notify ) {
        PublisherSearchResult2._doEditPublisher( {}, (newVals,refs) => {
            axios.post( gAppRef.makeFlaskUrl( "/publisher/create", {list:1} ), newVals )
            .then( resp => {
                // update the cached publishers
                gAppRef.caches.publishers = resp.data.publishers ;
                // unload any updated values
                applyUpdatedVals( newVals, newVals, resp.data.updated, refs ) ;
                // update the UI with the new details
                notify( resp.data.publ_id, newVals ) ;
                if ( resp.data.warnings )
                    gAppRef.showWarnings( "The new publisher was created OK.", resp.data.warnings ) ;
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
        PublisherSearchResult2._doEditPublisher( this.props.data, (newVals,refs) => {
            // send the updated details to the server
            newVals.publ_id = this.props.data.publ_id ;
            axios.post( gAppRef.makeFlaskUrl( "/publisher/update", {list:1} ), newVals )
            .then( resp => {
                // update the cached publishers
                gAppRef.caches.publishers = resp.data.publishers ;
                // update the UI with the new details
                applyUpdatedVals( this.props.data, newVals, resp.data.updated, refs ) ;
                removeSpecialFields( this.props.data ) ;
                this.forceUpdate() ;
                if ( resp.data.warnings )
                    gAppRef.showWarnings( "The publisher was updated OK.", resp.data.warnings ) ;
                else
                    gAppRef.showInfoToast( <div> The publisher was updated OK. </div> ) ;
                gAppRef.closeModalForm() ;
            } )
            .catch( err => {
                gAppRef.showErrorMsg( <div> Couldn't update the publisher: <div className="monospace"> {err.toString()} </div> </div> ) ;
            } ) ;
        } );
    }

    onDeletePublisher() {
        let doDelete = ( nPubs, nArticles ) => {
            // confirm the operation
            let warning ;
            if ( typeof nPubs !== "number" ) {
                // something went wrong when getting the number of associated publications/articles
                // (we can continue, but we warn the user)
                warning = ( <div> <img className="icon" src="/images/error.png" alt="Error." />
                    WARNING: Couldn't check if any publications or articles will also be deleted:
                    <div className="monospace"> {nPubs.toString()} </div>
                </div> ) ;
            } else if ( nPubs === 0 && nArticles === 0 )
                warning = <div> No publications nor articles will be deleted. </div> ;
            else {
                let vals = [] ;
                if ( nPubs > 0 )
                    vals.push( pluralString( nPubs, "publication" ) ) ;
                if ( nArticles > 0 )
                    vals.push( pluralString( nArticles, "article" ) ) ;
                warning = <div> {warning} { vals.join(" and ") + " will also be deleted." } </div> ;
            }
            let content = ( <div>
                Delete this publisher?
                <div style={{margin:"0.5em 0 0.5em 2em",fontStyle:"italic"}} dangerouslySetInnerHTML={{__html: this.props.data.publ_name}} />
                {warning}
            </div> ) ;
            gAppRef.ask( content, "ask", {
                "OK": () => {
                    // delete the publisher on the server
                    axios.get( gAppRef.makeFlaskUrl( "/publisher/delete/" + this.props.data.publ_id, {list:1} ) )
                    .then( resp => {
                        // update the cached publishers
                        gAppRef.caches.publishers = resp.data.publishers ;
                        gAppRef.caches.publications = resp.data.publications ; // nb: because of cascading deletes
                        // update the UI
                        this.props.onDelete( "publ_id", this.props.data.publ_id ) ;
                        resp.data.deletedPublications.forEach( pub_id => {
                            this.props.onDelete( "pub_id", pub_id ) ;
                        } ) ;
                        resp.data.deletedArticles.forEach( article_id => {
                            this.props.onDelete( "article_id", article_id ) ;
                        } ) ;
                        if ( resp.data.warnings )
                            gAppRef.showWarnings( "The publisher was deleted.", resp.data.warnings ) ;
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
        axios.get( gAppRef.makeFlaskUrl( "/publisher/" + this.props.data.publ_id ) )
        .then( resp => {
            doDelete( resp.data.nPublications, resp.data.nArticles ) ;
        } )
        .catch( err => {
            doDelete( err ) ;
        } ) ;
    }

}
