"""Allow districts to belong to multiple divisions.

Revision ID: a7e4c19b2d61
Revises: d82a64e913f0
"""
from alembic import op
import sqlalchemy as sa

revision = "a7e4c19b2d61"
down_revision = "d82a64e913f0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "district_divisions",
        sa.Column(
            "district_id", sa.String(36),
            sa.ForeignKey("districts.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column(
            "division_id", sa.String(36),
            sa.ForeignKey("divisions.id", ondelete="RESTRICT"), primary_key=True,
        ),
    )
    op.execute(sa.text(
        "INSERT INTO district_divisions (district_id, division_id) "
        "SELECT id, division_id FROM districts ON CONFLICT DO NOTHING"
    ))


def downgrade():
    op.drop_table("district_divisions")
