import React from "react" ;
import { Link } from "react-router-dom" ;
import { Menu, MenuList, MenuButton, MenuItem } from "@reach/menu-button" ;
import "./PublicationSearchResult.css" ;
import { PublicationSearchResult2 } from "./PublicationSearchResult2.js" ;
import { PreviewableImage } from "./PreviewableImage.js" ;
import { PUBLICATION_EXCESS_ARTICLE_THRESHOLD } from "./constants.js" ;
import { gAppRef } from "./App.js" ;
import { makeCollapsibleList, pluralString, updateRecord, isLink } from "./utils.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class PublicationSearchResult extends React.Component
{

    render() {

        // prepare the basic details
        const display_description = PreviewableImage.adjustHtmlForPreviewableImages(
            this.props.data[ "pub_description!" ] || this.props.data.pub_description
        ) ;
        const parent_publ = this.props.data._parent_publ ;
        const image_url = PublicationSearchResult._makeImageUrl( this.props.data ) ;

        // prepare the publication's URL
        let pub_url = this.props.data.pub_url  ;
        if ( pub_url && ! isLink(pub_url) )
            pub_url = gAppRef.makeExternalDocUrl( pub_url ) ;

        // prepare the tags
        let tags = [] ;
        if ( this.props.data[ "tags!" ] ) {
            // the backend has provided us with a list of tags (possibly highlighted) - use them directly
            // NOTE: We don't normally show HTML in tags, but in this case we need to, in order to be able to highlight
            // matching search terms. This will have the side-effect of rendering any HTML that may be in the tag,
            // but we can live with that.
            for ( let i=0 ; i < this.props.data["tags!"].length ; ++i ) {
                const tag = this.props.data.pub_tags[ i ] ; // nb: this is the actual tag (without highlights)
                tags.push( <Link key={tag} className="tag" title="Search for this tag."
                    to = { gAppRef.makeAppUrl( "/tag/" + encodeURIComponent(tag) ) }
                    dangerouslySetInnerHTML = {{ __html: this.props.data["tags!"][i] }}
                /> ) ;
            }
        } else {
            if ( this.props.data.pub_tags ) {
                this.props.data.pub_tags.map(
                    tag => tags.push( <Link key={tag} className="tag" title="Search for this tag."
                        to = { gAppRef.makeAppUrl( "/tag/" + encodeURIComponent(tag) ) }
                    > {tag} </Link> )
                ) ;
            }
        }

        // prepare the articles
        let articles = [] ;
        if ( this.props.data.articles ) {
            for ( let i=0 ; i < this.props.data.articles.length ; ++i ) {
                const article = this.props.data.articles[ i ] ;
                if ( this.props.onArticleClick ) {
                    // forward clicks on the article to the parent
                    articles.push( <div
                        dangerouslySetInnerHTML = {{__html: article.article_title}}
                        onClick = { () => this.props.onArticleClick( article.article_id ) }
                        style = {{ cursor: "pointer" }}
                        title = "Go to this article."
                    /> ) ;
                } else {
                    // handle clicks on the article normally
                    articles.push( <Link title="Show this article."
                        to = { gAppRef.makeAppUrl( "/article/" + article.article_id ) }
                        dangerouslySetInnerHTML = {{ __html: article.article_title }}
                    /> ) ;
                }
            }
        }

        // prepare the menu
        const menu = ( <Menu>
            <MenuButton className="sr-menu" />
            <MenuList>
                <MenuItem className="edit" onSelect={ () => this.onEditPublication() } >
                    <img src="/images/icons/edit.png" alt="Edit." /> Edit
                </MenuItem>
                <MenuItem className="delete" onSelect={ () => this.onDeletePublication() } >
                    <img src="/images/icons/delete.png" alt="Delete." /> Delete
                </MenuItem>
            </MenuList>
        </Menu> ) ;

        return ( <div className="search-result publication"
                    ref = { r => gAppRef.setTestAttribute( r, "pub_id", this.props.data.pub_id ) }
            >
            <div className="header">
                {menu}
                { parent_publ &&
                    <Link className="publisher" title="Show this publisher."
                        to = { gAppRef.makeAppUrl( "/publisher/" + this.props.data.publ_id ) }
                        dangerouslySetInnerHTML={{ __html: parent_publ.publ_name }}
                    />
                }
                <Link className="name" title="Show this publication."
                    to = { gAppRef.makeAppUrl( "/publication/" + this.props.data.pub_id ) }
                    dangerouslySetInnerHTML = {{ __html: this._makeDisplayName( true ) }}
                />
                { pub_url &&
                    <a href={pub_url} className="open-link" target="_blank" rel="noopener noreferrer">
                        <img src="/images/open-link.png" alt="Open publication." title="Open this publication." />
                    </a>
                }
            </div>
            <div className="content">
                { image_url && <PreviewableImage url={image_url} className="image" alt="Publication." /> }
                <div className="description" dangerouslySetInnerHTML={{__html: display_description}} />
                { makeCollapsibleList( "Articles", articles, PUBLICATION_EXCESS_ARTICLE_THRESHOLD, {float:"left",marginBottom:"0.25em"} ) }
            </div>
            <div className="footer">
                { this.props.data.pub_date && <div> <label>Published:</label> <span className="pub_date"> {this.props.data.pub_date} </span> </div> }
                { tags.length > 0 && <div className="tags"> <label>Tags:</label> {tags} </div> }
            </div>
        </div> ) ;
    }

    componentDidMount() {
        PreviewableImage.activatePreviewableImages( this ) ;
    }

    static onNewPublication() {
        gAppRef.dataCache.get( [ "publishers", "publications", "tags" ], () => {
            PublicationSearchResult2._doEditPublication( {}, null, (newVals,refs) => {
                axios.post(
                    gAppRef.makeFlaskUrl( "/publication/create" ), newVals
                ).then( resp => {
                    gAppRef.dataCache.refresh( [ "publications", "tags" ], () => {
                        // update the UI
                        const newPub = resp.data.record ;
                        gAppRef.prependSearchResult( newPub ) ;
                        if ( newPub._parent_publ )
                            gAppRef.updatePublisher( newPub._parent_publ.publ_id ) ;
                        // update the UI
                        if ( resp.data.warnings )
                            gAppRef.showWarnings( "The new publication was created OK.", resp.data.warnings ) ;
                        else
                            gAppRef.showInfoToast( <div> The new publication was created OK. </div> ) ;
                        gAppRef.closeModalForm() ;
                    } ) ;
                } ).catch( err => {
                    gAppRef.showErrorMsg( <div> Couldn't create the publication: <div className="monospace"> {err.toString()} </div> </div> ) ;
                } ) ;
            } ) ;
        } ) ;
    }

    onEditPublication() {
        gAppRef.dataCache.get( [ "publishers", "publications", "tags" ], () => {
            // get the articles for this publication
            let articles = this.props.data.articles ; // nb: _doEditPublication() might change the order of this list
            PublicationSearchResult2._doEditPublication( this.props.data, articles, (newVals,refs) => {
                // send the updated details to the server
                newVals.pub_id = this.props.data.pub_id ;
                if ( articles )
                    newVals.article_order = articles.map( a => a.article_id ) ;
                axios.post(
                    gAppRef.makeFlaskUrl( "/publication/update" ), newVals
                ).then( resp => {
                    // update the UI
                    gAppRef.dataCache.refresh( [ "publications", "tags" ], () => {
                        // update the UI
                        const pub = resp.data.record ;
                        const orig_parent_publ = this.props.data._parent_publ ;
                        updateRecord( this.props.data, pub ) ;
                        if ( pub._parent_publ )
                            gAppRef.updatePublisher( pub._parent_publ.publ_id ) ;
                        if ( orig_parent_publ )
                            gAppRef.updatePublisher( orig_parent_publ.publ_id ) ;
                        // update the UI
                        if ( newVals.imageData )
                            gAppRef.forceFlaskImageReload( "publication", newVals.pub_id ) ;
                        this.forceUpdate() ;
                        PreviewableImage.activatePreviewableImages( this ) ;
                        // update the UI
                        if ( resp.data.warnings )
                            gAppRef.showWarnings( "The publication was updated OK.", resp.data.warnings ) ;
                        else
                            gAppRef.showInfoToast( <div> The publication was updated OK. </div> ) ;
                        gAppRef.closeModalForm() ;
                    } ) ;
                } ).catch( err => {
                    gAppRef.showErrorMsg( <div> Couldn't update the publication: <div className="monospace"> {err.toString()} </div> </div> ) ;
                } ) ;
            } ) ;
        } ) ;
    }

    onDeletePublication() {
        let doDelete = ( nArticles ) => {
            // confirm the operation
            let warning ;
            if ( typeof nArticles === "number" ) {
                if ( nArticles === 0 )
                    warning = <div> No articles will be deleted. </div> ;
                else
                    warning = <div> { pluralString(nArticles,"associated article") + " will also be deleted." } </div> ;
            } else {
                warning = ( <div> <img className="icon" src="/images/error.png" alt="Error." />
                    WARNING: Couldn't check if any associated articles will be deleted:
                    <div className="monospace"> {nArticles.toString()} </div>
                </div> ) ;
            }
            const content = ( <div>
                Delete this publication?
                <div style={{margin:"0.5em 0 0.5em 2em",fontStyle:"italic"}} dangerouslySetInnerHTML = {{ __html: this._makeDisplayName(false) }} />
                {warning}
            </div> ) ;
            gAppRef.ask( content, "ask", {
                "OK": () => {
                    // delete the publication on the server
                    axios.get(
                        gAppRef.makeFlaskUrl( "/publication/delete/" + this.props.data.pub_id )
                    ).then( resp => {
                        gAppRef.dataCache.refresh( [ "publications", "tags" ] ) ;
                        // update the UI
                        this.props.onDelete( "pub_id", this.props.data.pub_id ) ;
                        resp.data.deletedArticles.forEach( article_id => {
                            this.props.onDelete( "article_id", article_id ) ;
                        } ) ;
                        if ( this.props.data._parent_publ )
                            gAppRef.updatePublisher( this.props.data._parent_publ.publ_id ) ;
                        // update the UI
                        if ( resp.data.warnings )
                            gAppRef.showWarnings( "The publication was deleted.", resp.data.warnings ) ;
                        else
                            gAppRef.showInfoToast( <div> The publication was deleted. </div> ) ;
                    } ).catch( err => {
                        gAppRef.showErrorToast( <div> Couldn't delete the publication: <div className="monospace"> {err.toString()} </div> </div> ) ;
                    } ) ;
                },
                "Cancel": null,
            } ) ;
        }
        // get the publication details
        axios.get(
            gAppRef.makeFlaskUrl( "/publication/" + this.props.data.pub_id )
        ).then( resp => {
            doDelete( resp.data.nArticles ) ;
        } ).catch( err => {
            doDelete( err ) ;
        } ) ;
    }

    static makeDisplayName( vals, allowAlternateContent ) {
        let pub_name = null ;
        if ( allowAlternateContent && vals["pub_name!"] )
            pub_name = vals[ "pub_name!" ] ;
        if ( ! pub_name )
            pub_name = vals.pub_name ;
        if ( vals.pub_edition )
            return pub_name + " (" + vals.pub_edition + ")" ;
        else
            return pub_name ;
    }
    _makeDisplayName( allowAlternateContent ) { return PublicationSearchResult.makeDisplayName( this.props.data, allowAlternateContent ) ; }

    static _makeImageUrl( vals ) {
        let image_url = gAppRef.makeFlaskImageUrl( "publication", vals.pub_image_id ) ;
        if ( ! image_url ) {
            // check if the parent publisher has an image
            const parent_publ = vals._parent_publ ;
            if ( parent_publ )
                image_url = gAppRef.makeFlaskImageUrl( "publisher", parent_publ.publ_image_id ) ;
        }
        return image_url ;
    }

}
