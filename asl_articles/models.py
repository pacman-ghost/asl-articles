""" Define the database models. """

from asl_articles import db

#pylint: disable=no-member

# ---------------------------------------------------------------------

class Publisher( db.Model ):
    """Define the Publisher model."""

    publ_id = db.Column( db.Integer, primary_key=True )
    publ_name = db.Column( db.String(100), nullable=False )

    def __repr__( self ):
        return "<Publisher:{}|{}>".format( self.publ_id, self.publ_name )
