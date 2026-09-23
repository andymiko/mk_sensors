"""Add per-channel assignment items.

Revision ID: b8e1c7d4a290
Revises: a31d0e5f7b42
"""
from alembic import op
import sqlalchemy as sa


revision = "b8e1c7d4a290"
down_revision = "a31d0e5f7b42"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assignment_items",
        sa.Column("assignment_id", sa.String(36), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.BigInteger(), server_default=sa.text("EXTRACT(EPOCH FROM now())::bigint"), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), server_default=sa.text("EXTRACT(EPOCH FROM now())::bigint"), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'completed')", name="ck_assignment_items_status"),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("assignment_id", "channel_id"),
    )
    op.execute(sa.text("""
        INSERT INTO assignment_items
            (assignment_id, channel_id, status, completed_at, created_at, updated_at)
        SELECT a.id, c.id, a.status, a.completed_at, a.created_at, a.updated_at
        FROM assignments a
        JOIN channels c ON c.id = a.channel_id
        WHERE a.channel_id IS NOT NULL
        UNION ALL
        SELECT a.id, c.id, a.status, a.completed_at, a.created_at, a.updated_at
        FROM assignments a
        JOIN channels c ON c.object_id = a.object_id
        WHERE a.channel_id IS NULL
    """))


def downgrade():
    op.drop_table("assignment_items")
