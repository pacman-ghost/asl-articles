import React from "react" ;
import { Menu, MenuList, MenuButton, MenuItem } from "@reach/menu-button" ;
import { ArticleSearchResult2 } from "./ArticleSearchResult2.js" ;
import "./ArticleSearchResult.css" ;
import { PublicationSearchResult } from "./PublicationSearchResult.js" ;
import { gAppRef } from "./index.js" ;
import { makeScenarioDisplayName, applyUpdatedVals, removeSpecialFields, makeCommaList } from "./utils.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class ArticleSearchResult extends React.Component
{

    render() {
        const display_title = this.props.data[ "article_title!" ] || this.props.data.article_title ;
        const display_subtitle = this.props.data[ "article_subtitle!" ] || this.props.data.article_subtitle ;
        const display_snippet = this.props.data[ "article_snippet!" ] || this.props.data.article_snippet ;
        const pub = gAppRef.caches.publications[ this.props.data.pub_id ] ;
        const image_url = gAppRef.makeFlaskImageUrl( "article", this.props.data.article_image_id, true ) ;
        let authors ;
        if ( this.props.data[ "authors!" ] ) {
            // the backend has provided us with a list of author names (possibly highlighted) - use them directly
            authors = makeCommaList( this.props.data["authors!"],
                (a) => <span className="author" key={a} dangerouslySetInnerHTML={{__html: a}} />
            ) ;
        } else {
            // we only have a list of author ID's (the normal case) - figure out what the corresponding names are
            authors = makeCommaList( this.props.data.article_authors,
                (a) => <span className="author" key={a} dangerouslySetInnerHTML={{__html: gAppRef.caches.authors[a].author_name}} />
            ) ;
        }
        let scenarios ;
        if ( this.props.data[ "scenarios!" ] ) {
            // the backend has provided us with a list of scenarios (possibly highlighted) - use them directly
            let scenarios2 = [];
            this.props.data["scenarios!"].forEach( s => scenarios2.push( makeScenarioDisplayName(s) ) ) ;
            scenarios = makeCommaList( scenarios2,
                (s) => <span className="scenario" key={s} dangerouslySetInnerHTML={{__html: s}} />
            ) ;
        } else {
            // we only have a list of scenario ID's (the normal case) - figure out what the corresponding names are
            scenarios = makeCommaList( this.props.data.article_scenarios,
                (s) => <span className="scenario" key={s} dangerouslySetInnerHTML={{__html: makeScenarioDisplayName(gAppRef.caches.scenarios[s])}} />
            ) ;
        }
        let tags = [] ;
        if ( this.props.data[ "tags!" ] ) {
            // the backend has provided us with a list of tags (possibly highlighted) - use them directly
            // NOTE: We don't normally show HTML in tags, but in this case we need to, in order to be able to highlight
            // matching search terms. This will have the side-effect of rendering any HTML that may be in the tag,
            // but we can live with that.
            this.props.data[ "tags!" ].map(
                t => tags.push( <div key={t} className="tag" dangerouslySetInnerHTML={{__html: t}} /> )
            ) ;
        } else {
            if ( this.props.data.article_tags ) {
                this.props.data.article_tags.map(
                    t => tags.push( <div key={t} className="tag"> {t} </div> )
                ) ;
            }
        }
        // NOTE: The "title" field is also given the CSS class "name" so that the normal CSS will apply to it.
        // Some tests also look for a generic ".name" class name when checking search results.
        const pub_display_name = pub ? PublicationSearchResult.makeDisplayName( pub ) : null ;
        const menu = ( <Menu>
            <MenuButton className="sr-menu" />
            <MenuList>
                <MenuItem className="edit"
                    onSelect = { this.onEditArticle.bind( this ) }
                >Edit</MenuItem>
                <MenuItem className="delete"
                    onSelect = { this.onDeleteArticle.bind( this ) }
                >Delete</MenuItem>
            </MenuList>
        </Menu> ) ;
        return ( <div className="search-result article"
                    ref = { r => gAppRef.setTestAttribute( r, "article_id", this.props.data.article_id ) }
            >
            <div className="header">
                {menu}
                { pub_display_name && <span className="publication"> {pub_display_name} </span> }
                <span className="title name" dangerouslySetInnerHTML={{ __html: display_title }} />
                { this.props.data.article_url && <a href={this.props.data.article_url} className="open-link" target="_blank" rel="noopener noreferrer"><img src="/images/open-link.png" alt="Open article." title="Open this article." /></a> }
                { display_subtitle && <div className="subtitle" dangerouslySetInnerHTML={{ __html: display_subtitle }} /> }
            </div>
            <div className="content">
                { image_url && <img src={image_url} className="image" alt="Article." /> }
                <div className="snippet" dangerouslySetInnerHTML={{__html: display_snippet}} />
            </div>
            <div className="footer">
                { authors.length > 0 && <div className="authors"> By {authors} </div> }
                { scenarios.length > 0 && <div className="scenarios"> Scenarios: {scenarios} </div> }
                { tags.length > 0 && <div className="tags"> Tags: {tags} </div> }
            </div>
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
                removeSpecialFields( this.props.data ) ;
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
