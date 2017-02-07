"""empty message

Revision ID: 946a7f8137fd
Revises: 
Create Date: 2017-02-07 17:22:31.378001

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '946a7f8137fd'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('posts', sa.Column('picture', sa.String(length=20), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('posts', 'picture')
    # ### end Alembic commands ###
