import React from "react" ;
import Select from "react-select" ;
import CreatableSelect from "react-select/creatable" ;
import { NEW_ARTICLE_PUB_PRIORITY_CUTOFF } from "./constants.js" ;
import { PublicationSearchResult } from "./PublicationSearchResult.js" ;
import { gAppRef } from "./index.js" ;
import { ImageFileUploader } from "./FileUploader.js" ;
import { makeScenarioDisplayName, parseScenarioDisplayName, checkConstraints, sortSelectableOptions, unloadCreatableSelect, isNumeric } from "./utils.js" ;

// --------------------------------------------------------------------

export class ArticleSearchResult2
{

    static _doEditArticle( vals, notify ) {

        // initialize
        let refs = {} ;
        const isNew = Object.keys( vals ).length === 0 ;

        // initialize the image
        let imageFilename=null, imageData=null ;
        let imageRef=null, uploadImageRef=null, removeImageRef=null ;
        let imageUrl = gAppRef.makeFlaskUrl( "/images/article/" + vals.article_id ) ;
        imageUrl += "?foo=" + Math.random() ; // FUDGE! To bypass the cache :-/
        let onMissingImage = (evt) => {
            imageRef.src = "/images/placeholder.png" ;
            removeImageRef.style.display = "none" ;
        } ;
        let onUploadImage = (evt) => {
            if ( evt === null && !gAppRef.isFakeUploads() ) {
                // nb: the article image was clicked - trigger an upload request
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

        // initialize the publications
        let publications = [ { value: null, label: <i>(none)</i> } ] ;
        let mostRecentPub = null ;
        for ( let p of Object.entries(gAppRef.caches.publications) ) {
            const pub_display_name = PublicationSearchResult.makeDisplayName( p[1] ) ;
            const pub = {
                value: p[1].pub_id,
                label: <span dangerouslySetInnerHTML={{__html: pub_display_name}} />,
            } ;
            publications.push( pub ) ;
            if ( mostRecentPub === null || p[1].time_created > mostRecentPub[1] )
                mostRecentPub = [ pub, p[1].time_created ] ;
        }
        sortSelectableOptions( publications ) ;
        if ( isNew && mostRecentPub ) {
            // NOTE: If the user is creating a new article, we check for the most recently-created publication
            // and put that at the the top of list. This makes things easier in the most common use-case:
            // the user has received a new magazine and is entering all the articles from it.
            const now = new Date() / 1000 | 0 ;
            const delta = now - mostRecentPub[1] ; // nb: we ignore server/client time zones
            if ( delta <= NEW_ARTICLE_PUB_PRIORITY_CUTOFF ) {
                publications = publications.filter( p => p !== mostRecentPub[0] ) ;
                publications.splice( 1, 0, mostRecentPub[0] ) ;
            }
        }
        let currPub = publications[0] ;
        for ( let i=1; i < publications.length ; ++i ) {
            if ( publications[i].value === vals.pub_id ) {
                currPub = publications[i] ;
                break ;
            }
        }

        // initialize the authors
        let allAuthors = [] ;
        for ( let a of Object.entries(gAppRef.caches.authors) )
            allAuthors.push( { value: a[1].author_id, label: a[1].author_name }  );
        allAuthors.sort( (lhs,rhs) => { return lhs.label.localeCompare( rhs.label ) ; } ) ;
        let currAuthors = [] ;
        if ( vals.article_authors ) {
            currAuthors = vals.article_authors.map( a => {
                return { value: a, label: gAppRef.caches.authors[a].author_name }
            } ) ;
        }

        // initialize the scenarios
        let allScenarios = [] ;
        for ( let s of Object.entries(gAppRef.caches.scenarios) )
            allScenarios.push( { value: s[1].scenario_id, label: makeScenarioDisplayName(s[1]) } ) ;
        allScenarios.sort( (lhs,rhs) => { return lhs.label.localeCompare( rhs.label ) ; } ) ;
        let currScenarios = [] ;
        if ( vals.article_scenarios ) {
            currScenarios = vals.article_scenarios.map( s => {
                return { value: s, label: makeScenarioDisplayName(gAppRef.caches.scenarios[s]) }
            } ) ;
        }

        // initialize the tags
        const tags = gAppRef.makeTagLists( vals.article_tags ) ;

        // prepare the form content
        /* eslint-disable jsx-a11y/img-redundant-alt */
        const content = <div>
            <div className="image-container">
                <div className="row image">
                    <img src={imageUrl} className="image" onError={onMissingImage} onClick={() => onUploadImage(null)} ref={r => imageRef=r} alt="Upload image." title="Click to upload an image for this article." />
                    <img src="/images/delete.png" className="remove-image" onClick={onRemoveImage} ref={r => removeImageRef=r} alt="Remove image." title="Remove the article's image." />
                    <input type="file" accept="image/*" onChange={onUploadImage} style={{display:"none"}} ref={r => uploadImageRef=r} />
                </div>
            </div>
            <div className="row title"> <label className="top"> Title: </label>
                <input type="text" defaultValue={vals.article_title} autoFocus ref={r => refs.article_title=r} />
            </div>
            <div className="row subtitle"> <label className="top"> Subtitle: </label>
                <input type="text" defaultValue={vals.article_subtitle} ref={r => refs.article_subtitle=r} />
            </div>
            <div className="row publication"> <label className="select top"> Publication: </label>
                <Select className="react-select" classNamePrefix="react-select" options={publications} isSearchable={true}
                    defaultValue = {currPub}
                    ref = { r => refs.pub_id=r }
                />
                <input className="pageno" type="text" defaultValue={vals.article_pageno} ref={r => refs.article_pageno=r} title="Page number." />
            </div>
            <div className="row snippet"> <label> Snippet: </label>
                <textarea defaultValue={vals.article_snippet} ref={r => refs.article_snippet=r} />
            </div>
            <div className="row authors"> <label className="select"> Authors: </label>
                <CreatableSelect className="react-select" classNamePrefix="react-select" options={allAuthors} isMulti
                    defaultValue = {currAuthors}
                    ref = { r => refs.article_authors=r }
                />
            </div>
            <div className="row scenarios"> <label className="select"> Scenarios: </label>
                <CreatableSelect className="react-select" classNamePrefix="react-select" options={allScenarios} isMulti
                    defaultValue = {currScenarios}
                    ref = { r => refs.article_scenarios=r }
                />
            </div>
            <div className="row tags"> <label className="select"> Tags: </label>
                <CreatableSelect className="react-select" classNamePrefix="react-select" options={tags[1]} isMulti
                    defaultValue = {tags[0]}
                    ref = { r => refs.article_tags=r }
                />
            </div>
            <div className="row url"> <label> Web: </label>
                <input type="text" defaultValue={vals.article_url} ref={r => refs.article_url=r} />
            </div>
        </div> ;

        // prepare the form buttons
        const buttons = {
            OK: () => {
                // unload the new values
                let newVals = {} ;
                for ( let r in refs ) {
                    if ( r === "pub_id" )
                        newVals[ r ] = refs[r].state.value && refs[r].state.value.value ;
                    else if ( r === "article_authors" ) {
                        let vals = unloadCreatableSelect( refs[r] ) ;
                        newVals.article_authors = [] ;
                        vals.forEach( v => {
                            if ( v.__isNew__ )
                                newVals.article_authors.push( v.label ) ; // nb: string = new author name
                            else
                                newVals.article_authors.push( v.value ) ; // nb: integer = existing author ID
                        } ) ;
                    } else if ( r === "article_scenarios" ) {
                        let vals =  unloadCreatableSelect( refs[r] ) ;
                        newVals.article_scenarios = [] ;
                        vals.forEach( v => {
                            if ( v.__isNew__ )
                                newVals.article_scenarios.push( parseScenarioDisplayName( v.label ) ) ; // nb: array = new scenario
                            else
                                newVals.article_scenarios.push( v.value ) ; // nb: integer = existing scenario ID
                        } ) ;
                    } else if ( r === "article_tags" ) {
                        let vals =  unloadCreatableSelect( refs[r] ) ;
                        newVals[ r ] =  vals.map( v => v.label ) ;
                    } else
                        newVals[ r ] = refs[r].value.trim() ;
                }
                if ( imageData ) {
                    newVals.imageData = imageData ;
                    newVals.imageFilename = imageFilename ;
                }
                // check the new values
                const required = [
                    [ () => newVals.article_title === "", "Please give it a title.", refs.article_title ],
                ] ;
                const optional = [
                    [ () => newVals.pub_id === null, "No publication was specified.", refs.pub_id ],
                    [ () => newVals.article_pageno === "" && newVals.pub_id !== null, "No page number was specified.", refs.article_pageno ],
                    [ () => newVals.article_pageno !== "" && newVals.pub_id === null, "A page number was specified but no publication.", refs.pub_id ],
                    [ () => newVals.article_pageno !== "" && !isNumeric(newVals.article_pageno), "The page number is not numeric.", refs.article_pageno ],
                    [ () => newVals.article_snippet === "", "No snippet was provided.", refs.article_snippet ],
                    [ () => newVals.article_authors.length === 0, "No authors were specified.", refs.article_authors ],
                ] ;
                const verb = isNew ? "create" : "update" ;
                checkConstraints(
                    required, "Can't " + verb + " this article.",
                    optional, "Do you want to " + verb + " this article?",
                    () => notify( newVals, refs )
                ) ;
            },
            Cancel: () => { gAppRef.closeModalForm() ; },
        } ;

        // show the form
        gAppRef.showModalForm( "article-form", isNew?"New article":"Edit article", "#d3edfc", content, buttons ) ;
    }

}
