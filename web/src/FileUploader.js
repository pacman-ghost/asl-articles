import { MAX_IMAGE_UPLOAD_SIZE } from "./constants.js" ;
import { bytesDisplayString } from "./utils.js" ;
import { gAppRef } from "./index.js" ;

// --------------------------------------------------------------------

export class FileUploader {

    // Because Selenium can't control a browser's native "open file" dialog, we need a different mechanism
    // to test features that require uploading a file. The test suite stores the data it wants to upload
    // as a base64-encoded string in a hidden textarea, and we load it from there.

    getFile( evt, maxSize, onLoad ) {

        function onLoadWrapper( fname, data ) {
            // check that the uploaded file is not too big
            if ( maxSize && data.length > maxSize ) {
                gAppRef.showErrorMsg( "The file must be no more than " + bytesDisplayString(maxSize) + " in size." ) ;
                return ;
            }
            // notify the caller about the uploaded data
            onLoad( fname, data ) ;
        }

        // check if we're being run by the test suite
        if ( gAppRef.isFakeUploads()  ) {
            // yup - load the file data sent to us by the test suite
            let data = gAppRef.getStoredMsg( "upload" ) ;
            let pos = data.indexOf( "|" ) ;
            let fname = data.substr( 0, pos ) ;
            data = data.substr( pos+1 ) ;
            onLoadWrapper( fname, data ) ;
            // let the test suite know we've received the data
            gAppRef.setStoredMsg( "upload", "" ) ;
            return ;
        } else {
            // nope - read the file data normally
            let fname = evt.target.files[0].name ;
            let fileReader = new FileReader() ;
            fileReader.onload = () => { onLoadWrapper( fname, fileReader.result ) } ;
            fileReader.readAsDataURL( evt.target.files[0] ) ;
        }
    }

}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

export class ImageFileUploader {

    getFile( evt, imageRef, removeImageRef, onLoad ) {

        let fileUploader = new FileUploader() ;
        let maxSize = MAX_IMAGE_UPLOAD_SIZE ;
        if ( gAppRef.isTestMode() && gAppRef.args.max_image_upload_size )
            maxSize = gAppRef.args.max_image_upload_size ;
        fileUploader.getFile( evt, maxSize, (fname,data) => {
            // fix-up the image data received
            let prefix ;
            if ( gAppRef.isFakeUploads() )
                prefix = "data:image/unknown;base64," ;
            else {
                let pos = data.indexOf( ";base64," ) ;
                prefix = data.substr( 0, pos+8 ) ;
                data = data.substring( pos+8 ) ;
            }
            // update the UI
            imageRef.src = prefix + data ;
            removeImageRef.style.display = "inline" ;
            // notify the caller
            onLoad( fname, data ) ;
        } ) ;

    }

}
