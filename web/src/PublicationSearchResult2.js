import React from "react" ;
import Select from "react-select" ;
import CreatableSelect from "react-select/creatable" ;
import ReactDragListView from "react-drag-listview/lib/index.js" ;
import { gAppRef } from "./App.js" ;
import { ImageFileUploader } from "./FileUploader.js" ;
import { checkConstraints, confirmDiscardChanges, sortSelectableOptions, unloadCreatableSelect, makeTagLists, ciCompare, isNumeric } from "./utils.js" ;

// --------------------------------------------------------------------

export class PublicationSearchResult2
{

    static _doEditPublication( vals, articles, notify ) {

        // initialize
        let refs = {} ;
        let imageFilename=null, imageData=null ;
        let imageRef=null, uploadImageRef=null, removeImageRef=null ;

        // prepare to save the initial values
        let initialVals = null ;
        function onReady() {
            if ( ! initialVals )
                initialVals = unloadVals() ;
        }

        function doRender() {

            // NOTE: We implement this as a function so that we can re-render the form after articles have been re-ordered.

            // initialize the image
            let imageUrl ;
            if ( initialVals )
                imageUrl = imageRef.src ; // nb: leave whatever's there already
            else
                imageUrl = gAppRef.makeFlaskImageUrl( "publication", vals.pub_id ) || "/force-404" ;
            function onImageLoaded() { onReady() ; }
            function onMissingImage() {
                imageRef.src = "/images/placeholder.png" ;
                removeImageRef.style.display = "none" ;
                onReady() ;
            } ;
            function onUploadImage( evt ) {
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
            function onRemoveImage() {
                imageData = "{remove}" ;
                imageRef.src = "/images/placeholder.png" ;
                removeImageRef.style.display = "none" ;
            } ;

            // initialize the publishers
            let publishers = [ { value: null, label: <i>(none)</i>, textLabel: "" } ] ;
            let currPubl = publishers[0] ;
            for ( let p of Object.entries( gAppRef.dataCache.data.publishers ) ) {
                publishers.push( {
                    value: p[1].publ_id,
                    label: <span dangerouslySetInnerHTML={{__html: p[1].publ_name}} />,
                    textLabel: p[1].publ_name
                } ) ;
                if ( p[1].publ_id === vals.publ_id )
                    currPubl = publishers[ publishers.length-1 ] ;
            }
            sortSelectableOptions( publishers ) ;

            // initialize the publications
            // NOTE: As a convenience, we provide a droplist of known publication names (without edition #'s),
            // to make it easier to add a new edition of an existing publication.
            let publications = {} ;
            for ( let p of Object.entries( gAppRef.dataCache.data.publications ) )
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
            const tags = makeTagLists( vals.pub_tags ) ;

            // initialize the articles
            function make_article_display_name( article ) {
                let pageno = null ;
                if ( article.article_pageno ) {
                    pageno = ( <span className="pageno">
                        { article.article_pageno.substr( 0, 1 ) === "p" || "p" }
                        {article.article_pageno}
                    </span> ) ;
                }
                return ( <span>
                    <span dangerouslySetInnerHTML={{__html: article.article_title}} />
                    { pageno && <span className="pageno"> ({pageno}) </span> }
                </span> ) ;
            }
            const dragProps = {
                onDragEnd( fromIndex, toIndex ) {
                    const item = articles.splice( fromIndex, 1 )[0] ;
                    articles.splice( toIndex, 0, item ) ;
                    gAppRef._modalFormRef.current.forceUpdate() ;
                },
                nodeSelector: "li",
                lineClassName: "dragLine",
            } ;

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
                            alt="Upload image." title="Click to upload an image for this publication."
                        />
                        <img src="/images/delete.png" className="remove-image"
                            onClick = {onRemoveImage}
                            ref = { r => removeImageRef=r }
                            alt="Remove image." title="Remove the publication's image."
                        />
                        <input type="file" accept="image/*" style={{display:"none"}}
                            onChange = {onUploadImage}
                            ref = { r => uploadImageRef=r }
                        />
                    </div>
                </div>
                <div className="row name"> <label className="select top"> Name: </label>
                    <CreatableSelect className="react-select" classNamePrefix="react-select" options={publications2} autoFocus
                        defaultValue = {currPub}
                        ref = { r => refs.pub_name=r }
                    />
                    <input className="edition" type="text" defaultValue={vals.pub_edition} ref={r => refs.pub_edition=r} title="Publication edition." />
                </div>
                <div className="row pub_date"> <label className="select top"> Date: </label>
                    <input className="pub_date" type="text" defaultValue={vals.pub_date} ref={r => refs.pub_date=r} />
                </div>
                <div className="row publisher"> <label className="select top"> Publisher: </label>
                    <Select className="react-select" classNamePrefix="react-select" options={publishers} isSearchable={true} getOptionValue={o => o.textLabel}
                        defaultValue = {currPubl}
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

                { articles && articles.length > 0 &&
                    <fieldset className="articles"> <legend> Articles </legend>
                        <ReactDragListView {...dragProps}> <ul>
                            { articles.map( a => (
                                <li key={a.article_id} className="draggable"> {make_article_display_name(a)} </li>
                            ) ) }
                        </ul> </ReactDragListView>
                    </fieldset>
                }
            </div> ;

            return content ;
        }

        function unloadVals() {
            // unload the form values
            let newVals = {} ;
            for ( let r in refs ) {
                if ( r === "publ_id" )
                    newVals[ r ] = refs[r].state.value && refs[r].state.value.value ;
                else if ( r === "pub_name" ) {
                    if ( refs[r].state.value )
                        newVals[ r ] = refs[r].state.value.label.trim() ;
                } else if ( r === "pub_tags" ) {
                    let tags = unloadCreatableSelect( refs[r] ) ;
                    newVals[ r ] = tags.map( v => v.label ) ;
                } else
                    newVals[ r ] = refs[r].value.trim() ;
            }
            newVals._hasImage = ( removeImageRef.style.display !== "none" ) ;
            return newVals ;
        }

        function checkForDupe( vals ) {
            // check for an existing publication name/edition
            for ( let pub of Object.entries( gAppRef.dataCache.data.publications ) ) {
                if ( ciCompare( pub[1].pub_name, vals.pub_name ) !== 0 )
                    continue ;
                if ( ! pub[1].pub_edition && ! vals.pub_edition )
                    return true ;
                if ( ! pub[1].pub_edition || ! vals.pub_edition )
                    continue ;
                if ( ciCompare( pub[1].pub_edition, vals.pub_edition ) === 0 )
                    return true ;
            }
            return false ;
        }
        function checkArticlePageNumbers( articles ) {
            // check the order of the article page numbers
            let curr_pageno = null ;
            if ( ! articles  )
                return false ;
            for ( let i=0 ; i < articles.length ; ++i ) {
                if ( ! isNumeric( articles[i].article_pageno ) )
                    continue ;
                const pageno = parseInt( articles[i].article_pageno, 10 ) ;
                if ( curr_pageno !== null ) {
                    if ( pageno < curr_pageno )
                        return true ;
                }
                curr_pageno = pageno ;
            }
            return false ;
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
                    [ () => newVals.pub_name === undefined, "Please give it a name.", refs.pub_name ],
                    [ () => isNew && checkForDupe(newVals), "There is already a publication with this name/edition.", refs.pub_edition ],
                ] ;
                const optional = [
                    [ () => newVals.pub_name !== undefined && newVals.pub_edition === "", "The publication's edition was not specified.", refs.pub_edition ],
                    [ () => newVals.pub_date === "", "The publication date was not specified.", refs.pub_date ],
                    [ () => newVals.publ_id === null, "A publisher was not specified.", refs.publ_id ],
                    [ () => checkArticlePageNumbers(articles), "Some article page numbers are out of order.", null ],
                ] ;
                const verb = isNew ? "create" : "update" ;
                checkConstraints(
                    required, "Can't " + verb + " this publication.",
                    optional, "Do you want to " + verb + " this publication?",
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
        const title = ( <div style={{display:"flex"}}>
            <img src="/images/icons/publication.png" alt="Dialog icon." />
            {isNew ? "New publication" : "Edit publication"}
        </div> ) ;
        gAppRef.showModalForm( "publication-form",
            title, "#e5cea0",
            doRender, buttons
        ) ;
    }

}
