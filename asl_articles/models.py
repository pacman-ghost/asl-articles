""" Define the database models. """

from asl_articles import db

#pylint: disable=no-member

# ---------------------------------------------------------------------

class Publisher( db.Model ):
    """Define the Publisher model."""

    publ_id = db.Column( db.Integer, primary_key=True )
    publ_name = db.Column( db.String(100), nullable=False )
    publ_description = db.Column( db.String(1000) )
    publ_url = db.Column( db.String(500) )
    # NOTE: time_created should be non-nullable, but getting this to work on SQlite and Postgres
    # is more trouble than it's worth :-/
    time_created = db.Column( db.TIMESTAMP(timezone=True) )
    time_updated = db.Column( db.TIMESTAMP(timezone=True) )
    #
    publications = db.relationship( "Publication", backref="parent", passive_deletes=True )

    def __repr__( self ):
        return "<Publisher:{}|{}>".format( self.publ_id, self.publ_name )

# ---------------------------------------------------------------------

class Publication( db.Model ):
    """Define the Publication model."""

    pub_id = db.Column( db.Integer, primary_key=True )
    pub_name = db.Column( db.String(100), nullable=False )
    pub_edition = db.Column( db.String(100) )
    pub_description = db.Column( db.String(1000) )
    pub_url = db.Column( db.String(500) )
    pub_tags = db.Column( db.String(1000) )
    publ_id = db.Column( db.Integer,
        db.ForeignKey( Publisher.__table__.c.publ_id, ondelete="CASCADE" )
    )
    # NOTE: time_created should be non-nullable, but getting this to work on SQlite and Postgres
    # is more trouble than it's worth :-/
    time_created = db.Column( db.TIMESTAMP(timezone=True) )
    time_updated = db.Column( db.TIMESTAMP(timezone=True) )
    #
    articles = db.relationship( "Article", backref="parent", passive_deletes=True )

    def __repr__( self ):
        return "<Publication:{}|{}>".format( self.pub_id, self.pub_name )

# ---------------------------------------------------------------------

class Article( db.Model ):
    """Define the Article model."""

    article_id = db.Column( db.Integer, primary_key=True )
    article_title = db.Column( db.String(200), nullable=False )
    article_subtitle = db.Column( db.String(200) )
    article_snippet = db.Column( db.String(5000) )
    article_url = db.Column( db.String(500) )
    article_tags = db.Column( db.String(1000) )
    pub_id = db.Column( db.Integer,
        db.ForeignKey( Publication.__table__.c.pub_id, ondelete="CASCADE" )
    )
    # NOTE: time_created should be non-nullable, but getting this to work on SQlite and Postgres
    # is more trouble than it's worth :-/
    time_created = db.Column( db.TIMESTAMP(timezone=True) )
    time_updated = db.Column( db.TIMESTAMP(timezone=True) )
    #
    article_authors = db.relationship( "ArticleAuthor", backref="parent_article", passive_deletes=True )

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
