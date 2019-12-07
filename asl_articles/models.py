""" Define the database models. """

from asl_articles import db

#pylint: disable=no-member

# ---------------------------------------------------------------------

class Publisher( db.Model ):
    """Define the Publisher model."""

    publ_id = db.Column( db.Integer, primary_key=True )
    publ_name = db.Column( db.String(100), nullable=False )
    publ_description = db.Column( db.String(1000), nullable=True )
    publ_url = db.Column( db.String(500), nullable=True )
    # NOTE: time_created should be non-nullable, but getting this to work on SQlite and Postgres
    # is more trouble than it's worth :-/
    time_created = db.Column( db.TIMESTAMP(timezone=True), nullable=True )
    time_updated = db.Column( db.TIMESTAMP(timezone=True), nullable=True )
    #
    children = db.relationship( "Publication", backref="parent", passive_deletes=True )

    def __repr__( self ):
        return "<Publisher:{}|{}>".format( self.publ_id, self.publ_name )

# ---------------------------------------------------------------------

class Publication( db.Model ):
    """Define the Publication model."""

    pub_id = db.Column( db.Integer, primary_key=True )
    pub_name = db.Column( db.String(100), nullable=False )
    pub_edition = db.Column( db.String(100), nullable=True )
    pub_description = db.Column( db.String(1000), nullable=True )
    pub_url = db.Column( db.String(500), nullable=True )
    publ_id = db.Column( db.Integer,
        db.ForeignKey( Publisher.__table__.c.publ_id, ondelete="CASCADE" ),
        nullable=True
    )
    # NOTE: time_created should be non-nullable, but getting this to work on SQlite and Postgres
    # is more trouble than it's worth :-/
    time_created = db.Column( db.TIMESTAMP(timezone=True), nullable=True )
    time_updated = db.Column( db.TIMESTAMP(timezone=True), nullable=True )

    def __repr__( self ):
        return "<Publication:{}|{}>".format( self.pub_id, self.pub_name )
