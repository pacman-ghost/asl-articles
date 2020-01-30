import React from "react" ;
import { Menu, MenuList, MenuButton, MenuItem } from "@reach/menu-button" ;
import "./PublicationSearchResult.css" ;
import { PublicationSearchResult2 } from "./PublicationSearchResult2.js" ;
import { gAppRef } from "./index.js" ;
import { pluralString, applyUpdatedVals, removeSpecialFields } from "./utils.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class PublicationSearchResult extends React.Component
{

    render() {
        const display_description = this.props.data[ "pub_description!" ] || this.props.data.pub_description ;
        const publ = gAppRef.caches.publishers[ this.props.data.publ_id ] ;
        const image_url = gAppRef.makeFlaskImageUrl( "publication", this.props.data.pub_image_id, true ) ;
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
            if ( this.props.data.pub_tags ) {
                this.props.data.pub_tags.map(
                    t => tags.push( <div key={t} className="tag"> {t} </div> )
                ) ;
            }
        }
        const menu = ( <Menu>
            <MenuButton className="sr-menu" />
            <MenuList>
                <MenuItem className="edit"
                    onSelect = { this.onEditPublication.bind( this ) }
                >Edit</MenuItem>
                <MenuItem className="delete"
                    onSelect = { this.onDeletePublication.bind( this ) }
                >Delete</MenuItem>
            </MenuList>
        </Menu> ) ;
        return ( <div className="search-result publication"
                    ref = { r => gAppRef.setTestAttribute( r, "pub_id", this.props.data.pub_id ) }
            >
            <div className="header">
                {menu}
                { publ && <span className="publisher"> {publ.publ_name} </span> }
                <span className="name" dangerouslySetInnerHTML={{ __html: this._makeDisplayName(true) }} />
                { this.props.data.pub_url && <a href={this.props.data.pub_url} className="open-link" target="_blank" rel="noopener noreferrer"><img src="/images/open-link.png" alt="Open publication." title="Open this publication." /></a> }
            </div>
            <div className="content">
                { image_url && <img src={image_url} className="image" alt="Publication." /> }
                <div className="description" dangerouslySetInnerHTML={{__html: display_description}} />
            </div>
            <div className="footer">
                { tags.length > 0 && <div className="tags"> <label>Tags:</label> {tags} </div> }
            </div>
        </div> ) ;
    }

    static onNewPublication( notify ) {
        PublicationSearchResult2._doEditPublication( {}, null, (newVals,refs) => {
            axios.post( gAppRef.makeFlaskUrl( "/publication/create", {list:1} ), newVals )
            .then( resp => {
                // update the caches
                gAppRef.caches.publications = resp.data.publications ;
                gAppRef.caches.tags = resp.data.tags ;
                // unload any updated values
                applyUpdatedVals( newVals, newVals, resp.data.updated, refs ) ;
                // update the UI with the new details
                notify( resp.data.pub_id, newVals ) ;
                if ( resp.data.warnings )
                    gAppRef.showWarnings( "The new publication was created OK.", resp.data.warnings ) ;
                else
                    gAppRef.showInfoToast( <div> The new publication was created OK. </div> ) ;
                gAppRef.closeModalForm() ;
            } )
            .catch( err => {
                gAppRef.showErrorMsg( <div> Couldn't create the publication: <div className="monospace"> {err.toString()} </div> </div> ) ;
            } ) ;
        } ) ;
    }

    onEditPublication() {
        // get the articles for this publication
        axios.get( gAppRef.makeFlaskUrl( "/publication/" + this.props.data.pub_id + "/articles" ) )
        .then( resp => {
            let articles = resp.data ; // nb: _doEditPublication() might modify this list
            PublicationSearchResult2._doEditPublication( this.props.data, articles, (newVals,refs) => {
                // send the updated details to the server
                newVals.pub_id = this.props.data.pub_id ;
                newVals.article_order = articles.map( a => a.article_id ) ;
                axios.post( gAppRef.makeFlaskUrl( "/publication/update", {list:1} ), newVals )
                .then( resp => {
                    // update the caches
                    gAppRef.caches.publications = resp.data.publications ;
                    gAppRef.caches.tags = resp.data.tags ;
                    // update the UI with the new details
                    applyUpdatedVals( this.props.data, newVals, resp.data.updated, refs ) ;
                    removeSpecialFields( this.props.data ) ;
                    this.forceUpdate() ;
                    if ( resp.data.warnings )
                        gAppRef.showWarnings( "The publication was updated OK.", resp.data.warnings ) ;
                    else
                        gAppRef.showInfoToast( <div> The publication was updated OK. </div> ) ;
                    gAppRef.closeModalForm() ;
                } )
                .catch( err => {
                    gAppRef.showErrorMsg( <div> Couldn't update the publication: <div className="monospace"> {err.toString()} </div> </div> ) ;
                } ) ;
            } ) ;
        } )
        .catch( err => {
            gAppRef.showErrorMsg( <div> Couldn't load the articles: <div className="monospace"> {err.toString()} </div> </div> ) ;
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
                    axios.get( gAppRef.makeFlaskUrl( "/publication/delete/" + this.props.data.pub_id, {list:1} ) )
                    .then( resp => {
                        // update the caches
                        gAppRef.caches.publications = resp.data.publications ;
                        gAppRef.caches.tags = resp.data.tags ;
                        // update the UI
                        this.props.onDelete( "pub_id", this.props.data.pub_id ) ;
                        resp.data.deleteArticles.forEach( article_id => {
                            this.props.onDelete( "article_id", article_id ) ;
                        } ) ;
                        if ( resp.data.warnings )
                            gAppRef.showWarnings( "The publication was deleted.", resp.data.warnings ) ;
                        else
                            gAppRef.showInfoToast( <div> The publication was deleted. </div> ) ;
                    } )
                    .catch( err => {
                        gAppRef.showErrorToast( <div> Couldn't delete the publication: <div className="monospace"> {err.toString()} </div> </div> ) ;
                    } ) ;
                },
                "Cancel": null,
            } ) ;
        }
        // get the publication details
        axios.get( gAppRef.makeFlaskUrl( "/publication/" + this.props.data.pub_id ) )
        .then( resp => {
            doDelete( resp.data.nArticles ) ;
        } )
        .catch( err => {
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

}
