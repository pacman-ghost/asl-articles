import React from "react" ;
import { PublicationSearchResult2 } from "./PublicationSearchResult2.js" ;
import { gAppRef } from "./index.js" ;
import { makeOptionalLink, pluralString, applyUpdatedVals } from "./utils.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class PublicationSearchResult extends React.Component
{

    render() {
        const publ = gAppRef.caches.publishers[ this.props.data.publ_id ] ;
        const image_url = gAppRef.makeFlaskImageUrl( "publication", this.props.data.pub_image_id, true ) ;
        let tags = [] ;
        if ( this.props.data.pub_tags )
            this.props.data.pub_tags.map( t => tags.push( <div key={t} className="tag"> {t} </div> ) ) ;
        return ( <div className="search-result publication"
                    ref = { r => gAppRef.setTestAttribute( r, "pub_id", this.props.data.pub_id ) }
            >
            <div className="name">
                { image_url && <img src={image_url} className="image" alt="Publication." /> }
                { makeOptionalLink( this._makeDisplayName(), this.props.data.pub_url ) }
                { publ && <span className="publisher"> ({publ.publ_name}) </span> }
                <img src="/images/edit.png" className="edit" onClick={this.onEditPublication.bind(this)} alt="Edit this publication." />
                <img src="/images/delete.png" className="delete" onClick={this.onDeletePublication.bind(this)} alt="Delete this publication." />
            </div>
            <div className="description" dangerouslySetInnerHTML={{__html: this.props.data.pub_description}} />
            { tags.length > 0 && <div className="tags"> <label>Tags:</label> {tags} </div> }
        </div> ) ;
    }

    static onNewPublication( notify ) {
        PublicationSearchResult2._doEditPublication( {}, (newVals,refs) => {
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
        PublicationSearchResult2._doEditPublication( this.props.data, (newVals,refs) => {
            // send the updated details to the server
            newVals.pub_id = this.props.data.pub_id ;
            axios.post( gAppRef.makeFlaskUrl( "/publication/update", {list:1} ), newVals )
            .then( resp => {
                // update the caches
                gAppRef.caches.publications = resp.data.publications ;
                gAppRef.caches.tags = resp.data.tags ;
                // update the UI with the new details
                applyUpdatedVals( this.props.data, newVals, resp.data.updated, refs ) ;
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
        } );
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
                <div style={{margin:"0.5em 0 0.5em 2em",fontStyle:"italic"}} dangerouslySetInnerHTML = {{ __html: this._makeDisplayName() }} />
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

    _makeDisplayName() {
        if ( this.props.data.pub_edition )
            return this.props.data.pub_name + " (" + this.props.data.pub_edition + ")" ;
        else
            return this.props.data.pub_name ;
    }

}
