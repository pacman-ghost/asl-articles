import React from "react" ;
import "./RatingStars.css" ;

// --------------------------------------------------------------------

export class RatingStars extends React.Component
{

    constructor( props ) {
        // initialize
        super( props ) ;
        this.state = {
            rating: props.rating,
        } ;
    }

    render() {

        let changeRating = ( starIndex ) => {
            // update the rating
            let newRating ;
            if ( starRefs[starIndex].src.indexOf( "rating-star-disabled.png" ) !== -1 )
                newRating = starIndex + 1 ;
            else {
                // NOTE: We get here if the clicked-on star is enabled. If this is the highest enabled star,
                // we disable it (i.e. set the rating to N-1), otherwise we make it the highest star (i.e. set
                // the rating to N). This has the down-side that if the user wants to set a rating of 0,
                // they have to set the rating to 1 first, then set it to 0, but this is unlikely to be an issue
                // i.e. going from 1 to 0 will be far more common than 3 to 0.
                if ( starIndex+1 === this.state.rating )
                    newRating = starIndex ;
                else
                    newRating = starIndex + 1 ;
            }
            const prevRating = this.state.rating ;
            this.setState( { rating: newRating } ) ;
            // notify the parent
            if ( this.props.onChange ) {
                this.props.onChange( newRating, () => {
                    this.setState( { rating: prevRating } ) ; // nb: the update failed, rollback
                } ) ;
            }
        }

        // prepare the rating stars
        let stars=[], starRefs={} ;
        for ( let i=0 ; i < 3 ; ++i ) {
            const fname = this.state.rating > i ? "rating-star.png" : "rating-star-disabled.png" ;
            stars.push(
                <img src={"/images/"+fname} key={i} alt="Rating star."
                    ref = { r => starRefs[i] = r }
                    onClick={ () => changeRating(i) }
                />
            ) ;
        }

        // render the component
        return ( <span className="rating-stars" title={this.props.title} >
            {stars}
        </span> ) ;
    }

}
