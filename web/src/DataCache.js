import React from "react" ;
import { gAppRef } from "./App.js" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

export class DataCache
{

    constructor() {
        // initialize
        this.data = {} ;
    }

    get( keys, onOK ) {

        // initialize
        if ( onOK === undefined )
            onOK = () => {} ;

        let nOK = 0 ;
        function onPartialOK() {
            if ( ++nOK === keys.length ) {
                onOK() ;
            }
        }

        // refresh each key
        for ( let key of keys ) {
            // check if we already have the data in the cache
            if ( this.data[ key ] !== undefined ) {
                onPartialOK() ;
            } else {
                // nope - get the specified data from the backend
                axios.get(
                    gAppRef.makeFlaskUrl( "/" + key )
                ).then( resp => {
                    // got it - update the cache
                    this.data[ key ] = resp.data ;
                    onPartialOK() ;
                } ).catch( err => {
                    gAppRef.showErrorToast(
                        <div> Couldn't load the {key}: <div className="monospace"> {err.toString()} </div> </div>
                    ) ;
                } ) ;
            }
        }

    }

    refresh( keys, onOK ) {
        // refresh the specified keys
        for ( let key of keys )
            delete this.data[ key ] ;
        this.get( keys, onOK ) ;
    }

}
