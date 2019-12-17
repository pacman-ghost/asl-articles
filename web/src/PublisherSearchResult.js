import React from "react" ;
import { gAppRef } from "./index.js" ;
import { ImageFileUploader } from "./FileUploader.js" ;
import { makeOptionalLink, pluralString, applyUpdatedVals } from "./utils.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class PublisherSearchResult extends React.Component
{

    render() {
        return ( <div className="search-result publisher"
                    ref = { r => gAppRef.setTestAttribute( r, "publ_id", this.props.data.publ_id ) }
            >
            <div className="name"> { makeOptionalLink( this.props.data.publ_name, this.props.data.publ_url ) }
                <img src="/images/edit.png" className="edit" onClick={this.onEditPublisher.bind(this)} alt="Edit this publisher." />
                <img src="/images/delete.png" className="delete" onClick={this.onDeletePublisher.bind(this)} alt="Delete this publisher." />
            </div>
            <div className="description" dangerouslySetInnerHTML={{__html: this.props.data.publ_description}} />
        </div> ) ;
    }

    static onNewPublisher( notify ) {
        PublisherSearchResult._doEditPublisher( {}, (newVals,refs) => {
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
        PublisherSearchResult._doEditPublisher( this.props.data, (newVals,refs) => {
            // send the updated details to the server
            newVals.publ_id = this.props.data.publ_id ;
            axios.post( gAppRef.makeFlaskUrl( "/publisher/update", {list:1} ), newVals )
            .then( resp => {
                // update the cached publishers
                gAppRef.caches.publishers = resp.data.publishers ;
                // update the UI with the new details
                applyUpdatedVals( this.props.data, newVals, resp.data.updated, refs ) ;
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

    static _doEditPublisher( vals, notify ) {
        let refs = {} ;
        // initialize the image
        let imageFilename=null, imageData=null ;
        let imageRef=null, uploadImageRef=null, removeImageRef=null ;
        let imageUrl = gAppRef.makeFlaskUrl( "/images/publisher/" + vals.publ_id ) ;
        imageUrl += "?foo=" + Math.random() ; // FUDGE! To bypass the cache :-/
        let onMissingImage = (evt) => {
            imageRef.src = "/images/placeholder.png" ;
            removeImageRef.style.display = "none" ;
        } ;
        let onUploadImage = (evt) => {
            if ( evt === null && !gAppRef.isFakeUploads() ) {
                // nb: the publisher image was clicked - trigger an upload request
                uploadImageRef.click() ;
                return ;
            }
            let fileUploader = new ImageFileUploader() ;
            fileUploader.getFile( evt, imageRef, removeImageRef, (fname,data) => {
                imageFilename = fname ;
                imageData = data ;
            } ) ;
        } ;
        let onRemoveImage = () => {
            imageData = "{remove}" ;
            imageRef.src = "/images/placeholder.png" ;
            removeImageRef.style.display = "none" ;
        } ;
        // prepare the form content
        /* eslint-disable jsx-a11y/img-redundant-alt */
        const content = <div>
            <div className="row image">
                <img src={imageUrl} className="image" onError={onMissingImage} onClick={() => onUploadImage(null)} ref={r => imageRef=r} alt="Click to upload an image for this publisher." />
                <img src="/images/delete.png" className="remove-image" onClick={onRemoveImage} ref={r => removeImageRef=r} alt="Remove the publisher's image." />
                <input type="file" accept="image/*" onChange={onUploadImage} style={{display:"none"}} ref={r => uploadImageRef=r} />
            </div>
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
                if ( imageData ) {
                    newVals.imageData = imageData ;
                    newVals.imageFilename = imageFilename ;
                }
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
