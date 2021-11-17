""" Define the database models. """

# NOTE: Don't forget to keep the list of tables in init_tests() in sync with the models defined here.

from sqlalchemy.orm import deferred
from sqlalchemy.schema import UniqueConstraint

from asl_articles import db

# ---------------------------------------------------------------------

class Publisher( db.Model ):
    """Define the Publisher model."""

    publ_id = db.Column( db.Integer, primary_key=True )
    publ_name = db.Column( db.String(100), nullable=False )
    publ_description = db.Column( db.String(1000) )
    publ_url = db.Column( db.String(500) )
    # NOTE: time_created should be non-nullable, but getting this to work on both SQLite and Postgres
    # is more trouble than it's worth :-/
    time_created = db.Column( db.TIMESTAMP(timezone=True) )
    time_updated = db.Column( db.TIMESTAMP(timezone=True) )
    #
    publ_image = db.relationship( "PublisherImage", backref="parent_publ", passive_deletes=True )
    publications = db.relationship( "Publication", backref="parent_publ", passive_deletes=True )
    articles = db.relationship( "Article", backref="parent_publ", passive_deletes=True )

    def __repr__( self ):
        return "<Publisher:{}|{}>".format( self.publ_id, self.publ_name )

# ---------------------------------------------------------------------

class Publication( db.Model ):
    """Define the Publication model."""

    pub_id = db.Column( db.Integer, primary_key=True )
    pub_name = db.Column( db.String(100), nullable=False )
    pub_edition = db.Column( db.String(100) )
    pub_date = db.Column( db.String(100) ) # nb: this is just a display string
    pub_description = db.Column( db.String(1000) )
    pub_url = db.Column( db.String(500) )
    pub_seqno = db.Column( db.Integer )
    pub_tags = db.Column( db.String(1000) )
    publ_id = db.Column( db.Integer,
        db.ForeignKey( Publisher.__table__.c.publ_id, ondelete="CASCADE" )
    )
    # NOTE: time_created should be non-nullable, but getting this to work on both SQLite and Postgres
    # is more trouble than it's worth :-/
    time_created = db.Column( db.TIMESTAMP(timezone=True) )
    time_updated = db.Column( db.TIMESTAMP(timezone=True) )
    #
    pub_image = db.relationship( "PublicationImage", backref="parent_pub", passive_deletes=True )
    articles = db.relationship( "Article", backref="parent_pub", passive_deletes=True )

    def __repr__( self ):
        return "<Publication:{}|{}>".format( self.pub_id, self.pub_name )

# ---------------------------------------------------------------------

class Article( db.Model ):
    """Define the Article model."""

    article_id = db.Column( db.Integer, primary_key=True )
    article_title = db.Column( db.String(200), nullable=False )
    article_subtitle = db.Column( db.String(200) )
    article_date = db.Column( db.String(100) ) # nb: this is just a display string
    article_snippet = db.Column( db.String(5000) )
    article_seqno = db.Column( db.Integer )
    article_pageno = db.Column( db.String(20) )
    article_url = db.Column( db.String(500) )
    article_tags = db.Column( db.String(1000) )
    article_rating = db.Column( db.Integer )
    pub_id = db.Column( db.Integer,
        db.ForeignKey( Publication.__table__.c.pub_id, ondelete="CASCADE" )
    )
    publ_id = db.Column( db.Integer,
        db.ForeignKey( Publisher.__table__.c.publ_id, ondelete="CASCADE" )
    )
    # NOTE: time_created should be non-nullable, but getting this to work on both SQLite and Postgres
    # is more trouble than it's worth :-/
    time_created = db.Column( db.TIMESTAMP(timezone=True) )
    time_updated = db.Column( db.TIMESTAMP(timezone=True) )
    #
    article_image = db.relationship( "ArticleImage", backref="parent_article", passive_deletes=True )
    article_authors = db.relationship( "ArticleAuthor", backref="parent_article", passive_deletes=True )
    article_scenarios = db.relationship( "ArticleScenario", backref="parent_article", passive_deletes=True )

    def __repr__( self ):
        return "<Article:{}|{}>".format( self.article_id, self.article_title )

# ---------------------------------------------------------------------

class Author( db.Model ):
    """Define the Author model."""

    author_id = db.Column( db.Integer, primary_key=True )
    author_name = db.Column( db.String(100), nullable=False, unique=True )
    #
    article_authors = db.relationship( "ArticleAuthor", backref="parent_author", passive_deletes=True )

    def __repr__( self ):
        return "<Author:{}|{}>".format( self.author_id, self.author_name )

class ArticleAuthor( db.Model ):
    """Define the link between Article's and Author's."""

    article_author_id = db.Column( db.Integer, primary_key=True )
    seq_no = db.Column( db.Integer, nullable=False )
    article_id = db.Column( db.Integer,
        db.ForeignKey( Article.__table__.c.article_id, ondelete="CASCADE" ),
        nullable = False
    )
    author_id = db.Column( db.Integer,
        db.ForeignKey( Author.__table__.c.author_id, ondelete="CASCADE" ),
        nullable = False
    )

    def __repr__( self ):
        return "<ArticleAuthor:{}|{}:{},{}>".format( self.article_author_id,
            self.seq_no, self.article_id, self.author_id
        )

# ---------------------------------------------------------------------

# NOTE: I initially put all the images in a single table, but this makes cascading deletes tricky,
# since we can't set up a foreign key relationship between these rows and their parent.
# While it probably won't matter for a database this size, keeping large blobs in the main tables
# is a bit icky, so we create separate tables for each type of image.

class PublisherImage( db.Model ):
    """Define the PublisherImage model."""

    publ_id = db.Column( db.Integer,
        db.ForeignKey( Publisher.__table__.c.publ_id, ondelete="CASCADE" ),
        primary_key = True
    )
    image_filename = db.Column( db.String(500), nullable=False )
    image_data = deferred( db.Column( db.LargeBinary, nullable=False ) )

    def __repr__( self ):
        return "<PublisherImage:{}|{}>".format( self.publ_id, len(self.image_data) )

class PublicationImage( db.Model ):
    """Define the PublicationImage model."""

    pub_id = db.Column( db.Integer,
        db.ForeignKey( Publication.__table__.c.pub_id, ondelete="CASCADE" ),
        primary_key = True
    )
    image_filename = db.Column( db.String(500), nullable=False )
    image_data = deferred( db.Column( db.LargeBinary, nullable=False ) )

    def __repr__( self ):
        return "<PublicationImage:{}|{}>".format( self.pub_id, len(self.image_data) )

class ArticleImage( db.Model ):
    """Define the ArticleImage model."""

    article_id = db.Column( db.Integer,
        db.ForeignKey( Article.__table__.c.article_id, ondelete="CASCADE" ),
        primary_key = True
    )
    image_filename = db.Column( db.String(500), nullable=False )
    image_data = deferred( db.Column( db.LargeBinary, nullable=False ) )

    def __repr__( self ):
        return "<ArticleImage:{}|{}>".format( self.article_id, len(self.image_data) )

# ---------------------------------------------------------------------

class Scenario( db.Model ):
    """Define the Scenario model."""

    scenario_id = db.Column( db.Integer, primary_key=True )
    scenario_roar_id = db.Column( db.String(50) )
    scenario_display_id = db.Column( db.String(50) )
    scenario_name = db.Column( db.String(200), nullable=False )
    #
    article_scenarios = db.relationship( "ArticleScenario", backref="parent_scenario", passive_deletes=True )
    #
    # We would like to make rows unique by display ID and name, but there are some scenarios that have
    # duplicate values for these e.g. "The T-Patchers [180]" was released in multiple publications.
    __table_args__ = (
        UniqueConstraint( "scenario_roar_id", "scenario_display_id", "scenario_name", name="unq_id_name" ),
    )

    def __repr__( self ):
        return "<Scenario:{}|{}:{}>".format( self.scenario_id, self.scenario_display_id, self.scenario_name )

class ArticleScenario( db.Model ):
    """Define the link between Article's and Scenario's."""

    article_scenario_id = db.Column( db.Integer, primary_key=True )
    seq_no = db.Column( db.Integer, nullable=False )
    article_id = db.Column( db.Integer,
        db.ForeignKey( Article.__table__.c.article_id, ondelete="CASCADE" ),
        nullable = False
    )
    scenario_id = db.Column( db.Integer,
        db.ForeignKey( Scenario.__table__.c.scenario_id, ondelete="CASCADE" ),
        nullable = False
    )

    def __repr__( self ):
        return "<ArticleScenario:{}|{}:{},{}>".format( self.article_scenario_id,
            self.seq_no, self.article_id, self.scenario_id
        )

# ---------------------------------------------------------------------

def get_model_from_table_name( table_name ):
    """Return the model class for the specified table."""
    pos = table_name.find( "_" )
    if pos >= 0:
        model_name = table_name[:pos].capitalize() + table_name[pos+1:].capitalize()
    else:
        model_name = table_name.capitalize()
    return globals()[ model_name ]
