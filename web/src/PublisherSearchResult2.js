import React from "react" ;
import { gAppRef } from "./index.js" ;
import { ImageFileUploader } from "./FileUploader.js" ;
import { checkConstraints, confirmDiscardChanges, ciCompare } from "./utils.js" ;

// --------------------------------------------------------------------

export class PublisherSearchResult2
{

    static _doEditPublisher( vals, notify ) {

        // initialize
        let refs = {} ;

        // prepare to save the initial values
        let initialVals = null ;
        function onReady() {
            if ( ! initialVals )
                initialVals = unloadVals() ;
        }

        // initialize the image
        let imageFilename=null, imageData=null ;
        let imageRef=null, uploadImageRef=null, removeImageRef=null ;
        let imageUrl = gAppRef.makeFlaskUrl( "/images/publisher/" + vals.publ_id ) ;
        imageUrl += "?foo=" + Math.random() ; // FUDGE! To bypass the cache :-/
        function onImageLoaded() { onReady() ; }
        function onMissingImage() {
            imageRef.src = "/images/placeholder.png" ;
            removeImageRef.style.display = "none" ;
            onReady() ;
        } ;
        function onUploadImage( evt ) {
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
        function onRemoveImage() {
            imageData = "{remove}" ;
            imageRef.src = "/images/placeholder.png" ;
            removeImageRef.style.display = "none" ;
        }

        // prepare the form content
        /* eslint-disable jsx-a11y/img-redundant-alt */
        const content = <div>
            <div className="image-container">
                <div className="row image">
                    <img src={imageUrl} className="image"
                        onLoad = {onImageLoaded}
                        onError = {onMissingImage}
                        onClick = { () => onUploadImage(null) }
                        ref = { r => imageRef=r }
                        alt="Upload image." title="Click to upload an image for this publisher."
                    />
                    <img src="/images/delete.png" className="remove-image"
                        onClick = {onRemoveImage}
                        ref = { r => removeImageRef=r }
                        alt="Remove image." title="Remove the publisher's image."
                    />
                    <input type="file" accept="image/*" style={{display:"none"}}
                        onChange = {onUploadImage}
                        ref = { r => uploadImageRef=r }
                    />
                </div>
            </div>
            <div className="row name"> <label className="top"> Name: </label>
                <input type="text" defaultValue={vals.publ_name} autoFocus ref={r => refs.publ_name=r} />
            </div>
            <div className="row description"> <label className="top"> Description: </label>
                <textarea defaultValue={vals.publ_description} ref={r => refs.publ_description=r} />
            </div>
            <div className="row url"> <label> Web: </label>
                <input type="text" defaultValue={vals.publ_url} ref={r => refs.publ_url=r} />
            </div>
        </div> ;

        function checkForDupe( publName ) {
            // check for an existing publisher
            for ( let publ of Object.entries(gAppRef.caches.publishers) ) {
                if ( ciCompare( publName, publ[1].publ_name ) === 0 )
                    return true ;
            }
            return false ;
        }

        function unloadVals() {
            // unload the form values
            let newVals = {} ;
            for ( let r in refs )
                newVals[ r ] = refs[r].value.trim() ;
            newVals._hasImage = ( removeImageRef.style.display !== "none" ) ;
            return newVals ;
        }

        // prepare the form buttons
        const buttons = {
            OK: () => {
                // unload and validate the new values
                let newVals = unloadVals() ;
                if ( imageData ) {
                    newVals.imageData = imageData ;
                    newVals.imageFilename = imageFilename ;
                }
                const required = [
                    [ () => newVals.publ_name === "", "Please give them a name.", refs.publ_name ],
                    [ () => isNew && checkForDupe(newVals.publ_name), "There is already a publisher with this name.", refs.publ_name ],
                ] ;
                const verb = isNew ? "create" : "update" ;
                checkConstraints(
                    required, "Can't " + verb + " this publisher.",
                    null, null,
                    () => notify( newVals, refs )
                ) ;
            },
            Cancel: () => {
                let newVals = unloadVals() ;
                if ( initialVals._hasImage && newVals._hasImage && imageData ) {
                    // FUDGE! The image was changed, but we have no way to tell if it's the same image or not,
                    // so we play it safe and force a confirmation.
                    newVals._justDoIt = true ;
                }
                confirmDiscardChanges( initialVals, newVals,
                    () => { gAppRef.closeModalForm() }
                ) ;
            },
        } ;

        // show the form
        const isNew = Object.keys( vals ).length === 0 ;
        gAppRef.showModalForm( "publisher-form",
            isNew ? "New publisher" : "Edit publisher", "#eabe51",
            content, buttons
        ) ;
    }

}
