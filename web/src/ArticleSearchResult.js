import React from "react" ;
import { ArticleSearchResult2 } from "./ArticleSearchResult2.js" ;
import { gAppRef } from "./index.js" ;
import { makeScenarioDisplayName, applyUpdatedVals, makeOptionalLink, makeCommaList } from "./utils.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class ArticleSearchResult extends React.Component
{

    render() {
        const pub = gAppRef.caches.publications[ this.props.data.pub_id ] ;
        const image_url = gAppRef.makeFlaskImageUrl( "article", this.props.data.article_image_id, true ) ;
        const authors = makeCommaList( this.props.data.article_authors,
            (a) => <span className="author" key={a}> {gAppRef.caches.authors[a].author_name} </span>
        ) ;
        const scenarios = makeCommaList( this.props.data.article_scenarios,
            (s) => <span className="scenario" key={s}> { makeScenarioDisplayName( gAppRef.caches.scenarios[s] ) } </span>
        ) ;
        let tags = [] ;
        if ( this.props.data.article_tags )
            this.props.data.article_tags.map( t => tags.push( <div key={t} className="tag"> {t} </div> ) ) ;
        // NOTE: The "title" field is also given the CSS class "name" so that the normal CSS will apply to it.
        // Some tests also look for a generic ".name" class name when checking search results.
        return ( <div className="search-result article"
                    ref = { r => gAppRef.setTestAttribute( r, "article_id", this.props.data.article_id ) }
            >
            <div className="title name">
                { image_url && <img src={image_url} className="image" alt="Article." /> }
                { makeOptionalLink( this.props.data.article_title, this.props.data.article_url ) }
                { pub && <span className="publication"> ({pub.pub_name}) </span> }
                <img src="/images/edit.png" className="edit" onClick={this.onEditArticle.bind(this)} alt="Edit this article." />
                <img src="/images/delete.png" className="delete" onClick={this.onDeleteArticle.bind(this)} alt="Delete this article." />
                { this.props.data.article_subtitle && <div className="subtitle" dangerouslySetInnerHTML={{ __html: this.props.data.article_subtitle }} /> }
                { authors.length > 0 && <div className="authors"> By {authors} </div> }
            </div>
            <div className="snippet" dangerouslySetInnerHTML={{__html: this.props.data.article_snippet}} />
            { scenarios.length > 0 && <div className="scenarios"> Scenarios: {scenarios} </div> }
            { tags.length > 0 && <div className="tags"> Tags: {tags} </div> }
        </div> ) ;
    }

    static onNewArticle( notify ) {
        ArticleSearchResult2._doEditArticle( {}, (newVals,refs) => {
            axios.post( gAppRef.makeFlaskUrl( "/article/create", {list:1} ), newVals )
            .then( resp => {
                // update the caches
                gAppRef.caches.authors = resp.data.authors ;
                gAppRef.caches.scenarios = resp.data.scenarios ;
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
        ArticleSearchResult2._doEditArticle( this.props.data, (newVals,refs) => {
            // send the updated details to the server
            newVals.article_id = this.props.data.article_id ;
            axios.post( gAppRef.makeFlaskUrl( "/article/update", {list:1} ), newVals )
            .then( resp => {
                // update the caches
                gAppRef.caches.authors = resp.data.authors ;
                gAppRef.caches.scenarios = resp.data.scenarios ;
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
