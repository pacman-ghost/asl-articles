import React from "react" ;
import ReactDOMServer from "react-dom/server" ;
import Select from "react-select" ;
import CreatableSelect from "react-select/creatable" ;
import { gAppRef } from "./index.js" ;
import { makeOptionalLink, unloadCreatableSelect, applyUpdatedVals } from "./utils.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class ArticleSearchResult extends React.Component
{

    render() {
        const pub = gAppRef.caches.publications[ this.props.data.pub_id ] ;
        let tags = [] ;
        if ( this.props.data.article_tags )
            this.props.data.article_tags.map( t => tags.push( <div key={t} className="tag"> {t} </div> ) ) ;
        // NOTE: The "title" field is also given the CSS class "name" so that the normal CSS will apply to it.
        // Some tests also look for a generic ".name" class name when checking search results.
        return ( <div className="search-result article"
                    ref = { r => gAppRef.setTestAttribute( r, "article_id", this.props.data.article_id ) }
            >
            <div className="title name"> { makeOptionalLink( this.props.data.article_title, this.props.data.article_url ) }
            { pub && <span className="publication"> ({pub.pub_name}) </span> }
                <img src="/images/edit.png" className="edit" onClick={this.onEditArticle.bind(this)} alt="Edit this article." />
                <img src="/images/delete.png" className="delete" onClick={this.onDeleteArticle.bind(this)} alt="Delete this article." />
                { this.props.data.article_subtitle && <div className="subtitle" dangerouslySetInnerHTML={{ __html: this.props.data.article_subtitle }} /> }
            </div>
            <div className="snippet" dangerouslySetInnerHTML={{__html: this.props.data.article_snippet}} />
            { tags.length > 0 && <div className="tags"> <label>Tags:</label> {tags} </div> }
        </div> ) ;
    }

    static onNewArticle( notify ) {
        ArticleSearchResult._doEditArticle( {}, (newVals,refs) => {
            axios.post( gAppRef.makeFlaskUrl( "/article/create", {list:1} ), newVals )
            .then( resp => {
                // update the caches
                gAppRef.caches.authors = resp.data.authors ;
                gAppRef.caches.tags = resp.data.tags ;
                // unload any updated values
                applyUpdatedVals( newVals, newVals, resp.data.updated, refs ) ;
                // update the UI with the new details
                notify( resp.data.article_id, newVals ) ;
                if ( resp.data.warnings )
                    gAppRef.showWarnings( "The new article was created OK.", resp.data.warnings ) ;
                else
                    gAppRef.showInfoToast( <div> The new article was created OK. </div> ) ;
                gAppRef.closeModalForm() ;
            } )
            .catch( err => {
                gAppRef.showErrorMsg( <div> Couldn't create the article: <div className="monospace"> {err.toString()} </div> </div> ) ;
            } ) ;
        } ) ;
    }

    onEditArticle() {
        ArticleSearchResult._doEditArticle( this.props.data, (newVals,refs) => {
            // send the updated details to the server
            newVals.article_id = this.props.data.article_id ;
            axios.post( gAppRef.makeFlaskUrl( "/article/update", {list:1} ), newVals )
            .then( resp => {
                // update the caches
                gAppRef.caches.authors = resp.data.authors ;
                gAppRef.caches.tags = resp.data.tags ;
                // update the UI with the new details
                applyUpdatedVals( this.props.data, newVals, resp.data.updated, refs ) ;
                this.forceUpdate() ;
                if ( resp.data.warnings )
                    gAppRef.showWarnings( "The article was updated OK.", resp.data.warnings ) ;
                else
                    gAppRef.showInfoToast( <div> The article was updated OK. </div> ) ;
                gAppRef.closeModalForm() ;
            } )
            .catch( err => {
                gAppRef.showErrorMsg( <div> Couldn't update the article: <div className="monospace"> {err.toString()} </div> </div> ) ;
            } ) ;
        } );
    }

    static _doEditArticle( vals, notify ) {
        let refs = {} ;
        // initialize the publications
        let publications = [ { value: null, label: <i>(none)</i> } ] ;
        let currPub = 0 ;
        for ( let p of Object.entries(gAppRef.caches.publications) ) {
            publications.push( {
                value: p[1].pub_id,
                label: <span dangerouslySetInnerHTML={{__html: p[1].pub_name}} />
            } ) ;
            if ( p[1].pub_id === vals.pub_id )
                currPub = publications.length - 1 ;
        }
        publications.sort( (lhs,rhs) => {
            return ReactDOMServer.renderToStaticMarkup( lhs.label ).localeCompare( ReactDOMServer.renderToStaticMarkup( rhs.label ) ) ;
        } ) ;
        // initialize the authors
        let authors = [] ;
        for ( let a of Object.entries(gAppRef.caches.authors) )
            authors.push( { value: a[1].author_id, label: a[1].author_name }  );
        authors.sort( (lhs,rhs) => { return lhs.label.localeCompare( rhs.label ) ; } ) ;
        let currAuthors = [] ;
        if ( vals.article_authors ) {
            currAuthors = vals.article_authors.map( a => {
                return { value: a, label: gAppRef.caches.authors[a].author_name }
            } ) ;
        }
        // initialize the tags
        const tags = gAppRef.makeTagLists( vals.article_tags ) ;
        // prepare the form content
        const content = <div>
            <div className="row title"> <label> Title: </label>
                <input type="text" defaultValue={vals.article_title} ref={(r) => refs.article_title=r} />
            </div>
            <div className="row subtitle"> <label> Subtitle: </label>
                <input type="text" defaultValue={vals.article_subtitle} ref={(r) => refs.article_subtitle=r} />
            </div>
            <div className="row authors"> <label> Authors: </label>
                <CreatableSelect className="react-select" classNamePrefix="react-select" options={authors} isMulti
                    defaultValue = {currAuthors}
                    ref = { (r) => refs.article_authors=r }
                />
            </div>
            <div className="row publication"> <label> Publication: </label>
                <Select className="react-select" classNamePrefix="react-select" options={publications} isSearchable={true}
                    defaultValue = { publications[ currPub ] }
                    ref = { (r) => refs.pub_id=r }
                />
            </div>
            <div className="row tags"> <label> Tags: </label>
                <CreatableSelect className="react-select" classNamePrefix="react-select" options={tags[1]} isMulti
                    defaultValue = {tags[0]}
                    ref = { (r) => refs.article_tags=r }
                />
            </div>
            <div className="row snippet"> <label> Snippet: </label>
                <textarea defaultValue={vals.article_snippet} ref={(r) => refs.article_snippet=r} />
            </div>
            <div className="row url"> <label> Web: </label>
                <input type="text" defaultValue={vals.article_url} ref={(r) => refs.article_url=r} />
            </div>
        </div> ;
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
                    }
                    else if ( r === "article_tags" ) {
                        let vals=  unloadCreatableSelect( refs[r] ) ;
                        newVals[ r ] =  vals.map( v => v.label ) ;
                    } else
                        newVals[ r ] = refs[r].value.trim() ;
                }
                if ( newVals.article_title === "" ) {
                    gAppRef.showErrorMsg( <div> Please specify the article's title. </div>) ;
                    return ;
                }
                // notify the caller about the new details
                notify( newVals, refs ) ;
            },
            Cancel: () => { gAppRef.closeModalForm() ; },
        } ;
        const isNew = Object.keys( vals ).length === 0 ;
        gAppRef.showModalForm( isNew?"New article":"Edit article", content, buttons ) ;
    }

    onDeleteArticle() {
        // confirm the operation
        const content = ( <div>
            Delete this article?
            <div style={{margin:"0.5em 0 0 2em",fontStyle:"italic"}} dangerouslySetInnerHTML = {{ __html: this.props.data.article_title }} />
        </div> ) ;
        gAppRef.ask( content, "ask", {
            "OK": () => {
                // delete the article on the server
                axios.get( gAppRef.makeFlaskUrl( "/article/delete/" + this.props.data.article_id, {list:1} ) )
                .then( resp => {
                    // update the caches
                    gAppRef.caches.authors = resp.data.authors ;
                    gAppRef.caches.tags = resp.data.tags ;
                    // update the UI
                    this.props.onDelete( "article_id", this.props.data.article_id ) ;
                    if ( resp.data.warnings )
                        gAppRef.showWarnings( "The article was deleted.", resp.data.warnings ) ;
                    else
                        gAppRef.showInfoToast( <div> The article was deleted. </div> ) ;
                } )
                .catch( err => {
                    gAppRef.showErrorToast( <div> Couldn't delete the article: <div className="monospace"> {err.toString()} </div> </div> ) ;
                } ) ;
            },
            "Cancel": null,
        } ) ;
    }

}
