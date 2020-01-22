import React from "react" ;
import Select from "react-select" ;
import CreatableSelect from "react-select/creatable" ;
import { gAppRef } from "./index.js" ;
import { ImageFileUploader } from "./FileUploader.js" ;
import { sortSelectableOptions, unloadCreatableSelect } from "./utils.js" ;

// --------------------------------------------------------------------

export class PublicationSearchResult2
{

    static _doEditPublication( vals, notify ) {

        let refs = {} ;

        // initialize the image
        let imageFilename=null, imageData=null ;
        let imageRef=null, uploadImageRef=null, removeImageRef=null ;
        let imageUrl = gAppRef.makeFlaskUrl( "/images/publication/" + vals.pub_id ) ;
        imageUrl += "?foo=" + Math.random() ; // FUDGE! To bypass the cache :-/
        let onMissingImage = (evt) => {
            imageRef.src = "/images/placeholder.png" ;
            removeImageRef.style.display = "none" ;
        } ;
        let onUploadImage = (evt) => {
            if ( evt === null && !gAppRef.isFakeUploads() ) {
                // nb: the publication image was clicked - trigger an upload request
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

        // initialize the publishers
        let publishers = [ { value: null, label: <i>(none)</i> } ] ;
        let currPubl = 0 ;
        for ( let p of Object.entries(gAppRef.caches.publishers) ) {
            publishers.push( {
                value: p[1].publ_id,
                label: <span dangerouslySetInnerHTML={{__html: p[1].publ_name}} />
            } ) ;
            if ( p[1].publ_id === vals.publ_id )
                currPubl = publishers.length - 1 ;
        }
        sortSelectableOptions( publishers ) ;

        // initialize the publications
        // NOTE: As a convenience, we provide a droplist of known publication names (without edition #'s),
        // to make it easier to add a new edition of an existing publication.
        let publications = {} ;
        for ( let p of Object.entries(gAppRef.caches.publications) )
            publications[ p[1].pub_name ] = p[1] ;
        let publications2 = [] ;
        for ( let pub_name in publications ) {
            const pub = publications[ pub_name ] ;
            publications2.push( { value: pub.pub_id, label: pub.pub_name } ) ;
        }
        sortSelectableOptions( publications2 ) ;
        let currPub = null ;
        for ( let pub of publications2 ) {
            if ( pub.label === vals.pub_name ) {
                currPub = pub ;
                break ;
            }
        }

        // initialize the tags
        const tags = gAppRef.makeTagLists( vals.pub_tags ) ;

        // prepare the form content
        /* eslint-disable jsx-a11y/img-redundant-alt */
        const content = <div>
            <div className="image-container">
                <div className="row image">
                    <img src={imageUrl} className="image" onError={onMissingImage} onClick={() => onUploadImage(null)} ref={r => imageRef=r} alt="Click to upload an image for this publication." />
                    <img src="/images/delete.png" className="remove-image" onClick={onRemoveImage} ref={r => removeImageRef=r} alt="Remove the publication's image." />
                    <input type="file" accept="image/*" onChange={onUploadImage} style={{display:"none"}} ref={r => uploadImageRef=r} />
                </div>
            </div>
            <div className="row name"> <label className="select top"> Name: </label>
                <CreatableSelect className="react-select" classNamePrefix="react-select" options={publications2} autoFocus
                    defaultValue = {currPub}
                    ref = { r => refs.pub_name=r }
                />
            </div>
            <div className="row edition"> <label className="top"> Edition: </label>
                <input type="text" defaultValue={vals.pub_edition} ref={r => refs.pub_edition=r} />
            </div>
            <div className="row publisher"> <label className="select top"> Publisher: </label>
                <Select className="react-select" classNamePrefix="react-select" options={publishers} isSearchable={true}
                    defaultValue = { publishers[ currPubl ] }
                    ref = { r => refs.publ_id=r }
                />
            </div>
            <div className="row description"> <label> Description: </label>
                <textarea defaultValue={vals.pub_description} ref={r => refs.pub_description=r} />
            </div>
            <div className="row tags"> <label className="select"> Tags: </label>
                <CreatableSelect className="react-select" classNamePrefix="react-select" options={tags[1]} isMulti
                    defaultValue = {tags[0]}
                    ref = { r => refs.pub_tags=r }
                />
            </div>
            <div className="row url"> <label> Web: </label>
                <input type="text" defaultValue={vals.pub_url} ref={r => refs.pub_url=r} />
            </div>
        </div> ;

        // prepare the form buttons
        const buttons = {
            OK: () => {
                // unload the new values
                let newVals = {} ;
                for ( let r in refs ) {
                    if ( r === "publ_id" )
                        newVals[ r ] = refs[r].state.value && refs[r].state.value.value ;
                    else if ( r === "pub_name" ) {
                        if ( refs[r].state.value )
                            newVals[ r ] = refs[r].state.value.label.trim() ;
                    } else if ( r === "pub_tags" ) {
                        let vals = unloadCreatableSelect( refs[r] ) ;
                        newVals[ r ] = vals.map( v => v.label ) ;
                    } else
                        newVals[ r ] = refs[r].value.trim() ;
                }
                if ( imageData ) {
                    newVals.imageData = imageData ;
                    newVals.imageFilename = imageFilename ;
                }
                if ( newVals.pub_name === undefined || newVals.pub_name === "" ) {
                    gAppRef.showErrorMsg( <div> Please specify the publication's name. </div>) ;
                    return ;
                }
                // notify the caller about the new details
                notify( newVals, refs ) ;
            },
            Cancel: () => { gAppRef.closeModalForm() ; },
        } ;

        // show the form
        const isNew = Object.keys( vals ).length === 0 ;
        gAppRef.showModalForm( "publication-form", isNew?"New publication":"Edit publication", "#e5f700", content, buttons ) ;
    }

}
