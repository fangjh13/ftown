"""empty message

Revision ID: e0617918d6d3
Revises: 29a5a4380abf
Create Date: 2017-09-20 15:35:43.926290

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e0617918d6d3'
down_revision = '29a5a4380abf'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def upgrade_collection():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('books', sa.Column('image', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade_collection():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('books', 'image')
    # ### end Alembic commands ###

