""" Define the database models. """

from asl_articles import db

#pylint: disable=no-member

# ---------------------------------------------------------------------

class Publisher( db.Model ):
    """Define the Publisher model."""

    publ_id = db.Column( db.Integer, primary_key=True )
    publ_name = db.Column( db.String(100), nullable=False )
    publ_url = db.Column( db.String(500), nullable=True )
    publ_description = db.Column( db.String(1000), nullable=True )
    # NOTE: time_created should be non-nullable, but getting this to work on SQlite and Postgres
    # is more trouble than it's worth :-/
    time_created = db.Column( db.TIMESTAMP(timezone=True), nullable=True )
    time_updated = db.Column( db.TIMESTAMP(timezone=True), nullable=True )

    def __repr__( self ):
        return "<Publisher:{}|{}>".format( self.publ_id, self.publ_name )
