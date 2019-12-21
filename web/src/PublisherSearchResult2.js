import React from "react" ;
import { gAppRef } from "./index.js" ;
import { ImageFileUploader } from "./FileUploader.js" ;

// --------------------------------------------------------------------

export class PublisherSearchResult2
{

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

        // prepare the form buttons
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

        // show the form
        const isNew = Object.keys( vals ).length === 0 ;
        gAppRef.showModalForm( isNew?"New publisher":"Edit publisher", content, buttons ) ;
    }

}
