""" Handle image requests. """

import io

from flask import send_file, abort

from asl_articles import app
#from asl_articles.models import PublisherImage, PublicationImage, ArticleImage
import asl_articles.models

# ---------------------------------------------------------------------

@app.route( "/images/<image_type>/<image_id>" )
def get_image( image_type, image_id ):
    """Return an image."""
    model = getattr( asl_articles.models, image_type.capitalize()+"Image" )
    if not model:
        abort( 404 )
    img = model.query.get( image_id )
    if not img:
        abort( 404 )
    return send_file(
        io.BytesIO( img.image_data ),
        attachment_filename = img.image_filename # nb: so that Flask can set the MIME type
    )
