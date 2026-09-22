"""Add longitude and latitude in WGS84 decimal degrees.

Revision ID: c49e72b138d5
Revises: b37d81a029c4
"""
from alembic import op
import sqlalchemy as sa

revision = 'c49e72b138d5'
down_revision = 'b37d81a029c4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('objects', sa.Column('longitude', sa.Double(), nullable=True))
    op.add_column('objects', sa.Column('latitude', sa.Double(), nullable=True))
    op.create_check_constraint('ck_objects_longitude', 'objects', 'longitude BETWEEN -180 AND 180')
    op.create_check_constraint('ck_objects_latitude', 'objects', 'latitude BETWEEN -90 AND 90')


def downgrade():
    op.drop_constraint('ck_objects_latitude', 'objects', type_='check')
    op.drop_constraint('ck_objects_longitude', 'objects', type_='check')
    op.drop_column('objects', 'latitude')
    op.drop_column('objects', 'longitude')
