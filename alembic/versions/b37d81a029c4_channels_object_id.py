"""Link channels to objects.

Revision ID: b37d81a029c4
Revises: 262305f91666
"""
from alembic import op
import sqlalchemy as sa

revision = 'b37d81a029c4'
down_revision = '262305f91666'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('channels', sa.Column('object_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('fk_channels_object', 'channels', 'objects', ['object_id'], ['id'])
    op.create_index('idx_channels_object_id', 'channels', ['object_id'])


def downgrade():
    op.drop_index('idx_channels_object_id', table_name='channels')
    op.drop_constraint('fk_channels_object', 'channels', type_='foreignkey')
    op.drop_column('channels', 'object_id')
