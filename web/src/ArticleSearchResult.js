import React from "react" ;
import { Link } from "react-router-dom" ;
import { Menu, MenuList, MenuButton, MenuItem } from "@reach/menu-button" ;
import { ArticleSearchResult2 } from "./ArticleSearchResult2.js" ;
import "./ArticleSearchResult.css" ;
import { PublisherSearchResult } from "./PublisherSearchResult.js" ;
import { PublicationSearchResult } from "./PublicationSearchResult.js" ;
import { PreviewableImage } from "./PreviewableImage.js" ;
import { RatingStars } from "./RatingStars.js" ;
import { gAppRef } from "./App.js" ;
import { makeScenarioDisplayName, updateRecord, makeCommaList } from "./utils.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class ArticleSearchResult extends React.Component
{

    render() {

        // prepare the basic details
        const display_title = this.props.data[ "article_title!" ] || this.props.data.article_title ;
        const display_subtitle = this.props.data[ "article_subtitle!" ] || this.props.data.article_subtitle ;
        const display_snippet = PreviewableImage.adjustHtmlForPreviewableImages(
            this.props.data[ "article_snippet!" ] || this.props.data.article_snippet
        ) ;
        const parent_pub = this.props.data._parent_pub ;
        const parent_publ = this.props.data._parent_publ ;
        const image_url = gAppRef.makeFlaskImageUrl( "article", this.props.data.article_image_id ) ;

        // prepare the article's URL
        let article_url = this.props.data.article_url ;
        if ( article_url )
            article_url = gAppRef.makeExternalDocUrl( article_url ) ;
        else if ( parent_pub && parent_pub.pub_url ) {
            article_url = gAppRef.makeExternalDocUrl( parent_pub.pub_url ) ;
            if ( article_url.substr( article_url.length-4 ) === ".pdf" && this.props.data.article_pageno )
                article_url += "#page=" + this.props.data.article_pageno ;
        }

        // prepare the authors
        let authors = [] ;
        const author_names_hilite = this.props.data[ "authors!" ] ;
        for ( let i=0 ; i < this.props.data.article_authors.length ; ++i ) {
            const author = this.props.data.article_authors[ i ] ;
            const author_name = author_names_hilite ? author_names_hilite[i] : author.author_name ;
            authors.push( <Link key={i} className="author" title="Show articles from this author."
                to = { gAppRef.makeAppUrl( "/author/" + author.author_id ) }
                dangerouslySetInnerHTML = {{ __html: author_name }}
            /> ) ;
        }

        // prepare the scenarios
        let scenarios = [] ;
        const scenario_names_hilite = this.props.data[ "scenarios!" ] ;
        for ( let i=0 ; i < this.props.data.article_scenarios.length ; ++i ) {
            const scenario = this.props.data.article_scenarios[ i ] ;
            const scenario_display_name = scenario_names_hilite ? scenario_names_hilite[i] : makeScenarioDisplayName(scenario) ;
            scenarios.push( <span key={i} className="scenario"
                dangerouslySetInnerHTML = {{ __html: scenario_display_name }}
            /> ) ;
        }

        // prepare the tags
        let tags = [] ;
        if ( this.props.data[ "tags!" ] ) {
            // the backend has provided us with a list of tags (possibly highlighted) - use them directly
            // NOTE: We don't normally show HTML in tags, but in this case we need to, in order to be able to highlight
            // matching search terms. This will have the side-effect of rendering any HTML that may be in the tag,
            // but we can live with that.
            for ( let i=0 ; i < this.props.data["tags!"].length ; ++i ) {
                const tag = this.props.data.article_tags[ i ] ; // nb: this is the actual tag (without highlights)
                tags.push( <Link key={tag} className="tag" title="Search for this tag."
                    to = { gAppRef.makeAppUrl( "/tag/" + encodeURIComponent(tag) ) }
                    dangerouslySetInnerHTML = {{ __html: this.props.data["tags!"][i] }}
                /> ) ;
            }
        } else {
            if ( this.props.data.article_tags ) {
                this.props.data.article_tags.map(
                    tag => tags.push( <Link key={tag} className="tag" title="Search for this tag."
                        to = { gAppRef.makeAppUrl( "/tag/" + encodeURIComponent(tag) ) }
                    > {tag} </Link> )
                ) ;
            }
        }

        // prepare the menu
        const menu = ( <Menu>
            <MenuButton className="sr-menu" />
            <MenuList>
                <MenuItem className="edit" onSelect={ () => this.onEditArticle() } >
                    <img src="/images/edit.png" alt="Edit." /> Edit
                </MenuItem>
                <MenuItem className="delete" onSelect={ () => this.onDeleteArticle() } >
                    <img src="/images/delete.png" alt="Delete." /> Delete
                </MenuItem>
            </MenuList>
        </Menu> ) ;

        // NOTE: The "title" field is also given the CSS class "name" so that the normal CSS will apply to it.
        // Some tests also look for a generic ".name" class name when checking search results.
        const pub_display_name = parent_pub ? PublicationSearchResult.makeDisplayName( parent_pub ) : null ;
        const publ_display_name = parent_publ ? PublisherSearchResult.makeDisplayName( parent_publ ) : null ;
        return ( <div className="search-result article"
                    ref = { r => gAppRef.setTestAttribute( r, "article_id", this.props.data.article_id ) }
            >
            <div className="header">
                {menu}
                { pub_display_name &&
                    <Link className="publication" title="Show this publication."
                        to = { gAppRef.makeAppUrl( "/publication/" + this.props.data.pub_id ) }
                        dangerouslySetInnerHTML = {{ __html: pub_display_name }}
                    />
                }
                { publ_display_name &&
                    <Link className="publisher" title="Show this publisher."
                        to = { gAppRef.makeAppUrl( "/publisher/" + this.props.data.publ_id ) }
                        dangerouslySetInnerHTML = {{ __html: publ_display_name }}
                    />
                }
                <RatingStars rating={this.props.data.article_rating} title="Rate this article."
                    onChange = { this.onRatingChange.bind( this ) }
                />
                <Link className="title name" title="Show this article."
                    to = { gAppRef.makeAppUrl( "/article/" + this.props.data.article_id ) }
                    dangerouslySetInnerHTML = {{ __html: display_title }}
                />
                { article_url &&
                    <a href={article_url} className="open-link" target="_blank" rel="noopener noreferrer">
                        <img src="/images/open-link.png" alt="Open article." title="Open this article." />
                    </a>
                }
                { display_subtitle && <div className="subtitle" dangerouslySetInnerHTML={{ __html: display_subtitle }} /> }
            </div>
            <div className="content">
                { image_url && <PreviewableImage url={image_url} noActivate={true} className="image" alt="Article." /> }
                <div className="snippet" dangerouslySetInnerHTML={{__html: display_snippet}} />
            </div>
            <div className="footer">
                { authors.length > 0 &&
                    <div className="authors"> By {makeCommaList(authors)} </div>
                }
                { this.props.data.article_date &&
                    <div> <label>Published:</label> <span className="article_date"> {this.props.data.article_date} </span> </div>
                }
                { scenarios.length > 0 &&
                    <div className="scenarios"> Scenarios: {makeCommaList(scenarios)} </div>
                }
                { tags.length > 0 &&
                    <div className="tags"> Tags: {tags} </div>
                }
            </div>
        </div> ) ;
    }

    componentDidMount() {
        PreviewableImage.activatePreviewableImages( this ) ;
    }

    onRatingChange( newRating, onFailed ) {
        axios.post( gAppRef.makeFlaskUrl( "/article/update-rating", null ), {
            article_id: this.props.data.article_id,
            rating: newRating,
        } ).catch( err => {
            gAppRef.showErrorMsg( <div> Couldn't update the rating: <div className="monospace"> {err.toString()} </div> </div> ) ;
            if ( onFailed )
                onFailed() ;
        } ) ;
    }

    static onNewArticle() {
        gAppRef.dataCache.get( [ "publishers", "publications", "authors", "scenarios", "tags" ], () => {
            ArticleSearchResult2._doEditArticle( {}, (newVals,refs) => {
                axios.post(
                    gAppRef.makeFlaskUrl( "/article/create" ), newVals
                ).then( resp => {
                    gAppRef.dataCache.refresh( [ "authors", "scenarios", "tags" ] ) ;
                    // update the UI
                    const newArticle = resp.data.record ;
                    gAppRef.prependSearchResult( newArticle ) ;
                    if ( newArticle._parent_pub )
                        gAppRef.updatePublication( newArticle._parent_pub.pub_id ) ;
                    else if ( newArticle._parent_publ )
                        gAppRef.updatePublisher( newArticle._parent_publ.publ_id ) ;
                    // update the UI
                    if ( resp.data.warnings )
                        gAppRef.showWarnings( "The new article was created OK.", resp.data.warnings ) ;
                    else
                        gAppRef.showInfoToast( <div> The new article was created OK. </div> ) ;
                    gAppRef.closeModalForm() ;
                } ).catch( err => {
                    gAppRef.showErrorMsg( <div> Couldn't create the article: <div className="monospace"> {err.toString()} </div> </div> ) ;
                } ) ;
            } ) ;
        } ) ;
    }

    onEditArticle() {
        gAppRef.dataCache.get( [ "publishers", "publications", "authors", "scenarios", "tags" ], () => {
            ArticleSearchResult2._doEditArticle( this.props.data, (newVals,refs) => {
                // send the updated details to the server
                newVals.article_id = this.props.data.article_id ;
                axios.post(
                    gAppRef.makeFlaskUrl( "/article/update" ), newVals
                ).then( resp => {
                    gAppRef.dataCache.refresh( [ "authors", "scenarios", "tags" ] ) ;
                    // update the UI
                    const article = resp.data.record ;
                    const orig_parent_pub = this.props.data._parent_pub ;
                    const orig_parent_publ = this.props.data._parent_publ ;
                    updateRecord( this.props.data, article ) ;
                    if ( article._parent_pub )
                        gAppRef.updatePublication( article._parent_pub.pub_id ) ;
                    else if ( article._parent_publ )
                        gAppRef.updatePublisher( article._parent_publ.publ_id ) ;
                    if ( orig_parent_pub )
                        gAppRef.updatePublication( orig_parent_pub.pub_id ) ;
                    if ( orig_parent_publ )
                        gAppRef.updatePublisher( orig_parent_publ.publ_id ) ;
                    // update the UI
                    if ( newVals.imageData )
                        gAppRef.forceFlaskImageReload( "article", newVals.article_id ) ;
                    this.forceUpdate() ;
                    PreviewableImage.activatePreviewableImages( this ) ;
                    // update the UI
                    if ( resp.data.warnings )
                        gAppRef.showWarnings( "The article was updated OK.", resp.data.warnings ) ;
                    else
                        gAppRef.showInfoToast( <div> The article was updated OK. </div> ) ;
                    gAppRef.closeModalForm() ;
                } ).catch( err => {
                    gAppRef.showErrorMsg( <div> Couldn't update the article: <div className="monospace"> {err.toString()} </div> </div> ) ;
                } ) ;
            } );
        } ) ;
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
                axios.get(
                    gAppRef.makeFlaskUrl( "/article/delete/" + this.props.data.article_id )
                ).then( resp => {
                    gAppRef.dataCache.refresh( [ "authors", "tags" ] ) ;
                    // update the UI
                    this.props.onDelete( "article_id", this.props.data.article_id ) ;
                    if ( this.props.data._parent_pub )
                        gAppRef.updatePublication( this.props.data._parent_pub.pub_id ) ;
                    else if ( this.props.data._parent_publ )
                        gAppRef.updatePublisher( this.props.data._parent_publ.publ_id ) ;
                    // update the UI
                    if ( resp.data.warnings )
                        gAppRef.showWarnings( "The article was deleted.", resp.data.warnings ) ;
                    else
                        gAppRef.showInfoToast( <div> The article was deleted. </div> ) ;
                } ).catch( err => {
                    gAppRef.showErrorToast( <div> Couldn't delete the article: <div className="monospace"> {err.toString()} </div> </div> ) ;
                } ) ;
            },
            "Cancel": null,
        } ) ;
    }

}
