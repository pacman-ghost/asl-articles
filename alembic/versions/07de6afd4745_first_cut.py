"""first cut

Revision ID: 07de6afd4745
Revises:
Create Date: 2019-11-18 07:15:11.213346

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "07de6afd4745"
down_revision = None
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------

def upgrade():
    op.create_table(
        "publisher",
        sa.Column( "publ_id", sa.Integer, primary_key=True ),
        sa.Column( "publ_name", sa.String(100), nullable=False ),
    )

def downgrade():
    op.drop_table( "publisher" )
