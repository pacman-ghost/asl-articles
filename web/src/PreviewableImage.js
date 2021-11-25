import React from "react" ;
import ReactDOM from "react-dom" ;
import $ from "jquery" ;

// --------------------------------------------------------------------

export class PreviewableImage extends React.Component
{
    // NOTE: While the "react-modal-image" component seems to work nicely, how can we use it
    // on arbitrary images in user-defined content?
    // This class is a wrapper around the jQuery-based imageZoom plugin.

    render() {
        return ( <a href={this.props.url} className="preview" target="_blank" rel="noopener noreferrer">
            <img src={this.props.url} className={this.props.className} style={this.props.style} alt={this.props.altText} />
        </a> ) ;
    }

    static initPreviewableImages() {
        // load the imageZoom script
        $.getScript( {
            url: "/jQuery/imageZoom/jquery.imageZoom.js",
            cache: true,
        } ) ;
        // load the imageZoom CSS
        let cssNode = document.createElement( "link" ) ;
        cssNode.type = "text/css" ;
        cssNode.rel = "stylesheet" ;
        cssNode.href = "/jQuery/imageZoom/jquery.imageZoom.css" ;
        let headNode = document.getElementsByTagName( "head" )[0] ;
        headNode.appendChild( cssNode ) ;
    }

    static adjustHtmlForPreviewableImages( html ) {
        // FUDGE! The imageZoom plugin requires images to be wrapped with a <a class="preview"> tag.
        // I was hoping to be able to let the user enable the preview functionality for images
        // by simply adding a "preview" attribute to their <img> tags, then locating them after render
        // and dynamically wrapping them with the necessary <a class="preview"> tag, but React doesn't
        // seem to like that :-/
        // We instead look for such images in the HTML returned to us by the backend server, and fix it up
        // before rendering it.

        // initialize
        if ( ! html )
            return "" ;

        // locate <img> tags with a class of "preview", and wrap them in a <a class="preview">.
        let buf=[], pos=0 ;
        const img_regex = /<img [^>]*class\s*=\s*["']preview["'][^>]*>/g ;
        const url_regex = /src\s*=\s*["'](.*?)['"]/
        for ( const match of html.matchAll( img_regex ) ) {
            buf.push( html.substr( pos, match.index-pos ) ) ;
            const match2 = url_regex.exec( match[0] ) ;
            if ( match2 ) {
                buf.push(
                    "<a href='" + match2[1] + "' class='preview'>",
                    match[0],
                    "</a>"
                ) ;
            } else
                buf.push( match[0] ) ;
            pos = match.index + match[0].length ;
        }
        buf.push( html.substr( pos ) ) ;

        return buf.join( "" ) ;
    }

    componentDidMount() {
        if ( this.props.manualActivate ) {
            // NOTE: We normally want PreviewableImage's to automatically activate themselves, but there is
            // a common case where we don't want this to happen: when raw HTML is received from the backend
            // and inserted like that into the page.
            // In this case, <img> tags are fixed up by adjustHtmlForPreviewableImages() as raw HTML (i.e. not
            // as a PreviewableImage instance), and so the page still needs to call activatePreviewableImages()
            // to activate these. Since it's probably not a good idea to activate an image twice, in this case
            // PreviewableImage instances should be created as "manually activated".
            return ;
        }
        let $elem = $( ReactDOM.findDOMNode( this ) ) ;
        $elem.imageZoom() ;
    }

    static activatePreviewableImages( rootNode ) {
        // locate images marked as previewable and activate them
        let $elems = $( ReactDOM.findDOMNode( rootNode ) ).find( "a.preview" ) ;
        $elems.imageZoom() ;
    }

}
