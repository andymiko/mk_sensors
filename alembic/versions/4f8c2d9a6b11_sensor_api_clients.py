"""Add sensor API clients and remove the obsolete user role.

Revision ID: 4f8c2d9a6b11
Revises: c2f4a9e730b1
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert


revision = "4f8c2d9a6b11"
down_revision = "c2f4a9e730b1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "api_clients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", sa.String(36), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_used_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())::bigint")),
        sa.Column("updated_at", sa.BigInteger(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())::bigint")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_api_clients_token_hash", "api_clients", ["token_hash"], unique=True)
    op.execute(sa.text("DELETE FROM roles WHERE code = 'user'"))


def downgrade():
    op.drop_index("ix_api_clients_token_hash", table_name="api_clients")
    op.drop_table("api_clients")

    bind = op.get_bind()
    roles = sa.table(
        "roles", sa.column("id"), sa.column("code"),
        sa.column("name"), sa.column("description"),
    )
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    links = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    role_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "mk_sensors/rbac/role/user"))
    bind.execute(insert(roles).values(
        id=role_id, code="user", name="Пользователь",
        description="Базовая роль зарегистрированного пользователя",
    ).on_conflict_do_nothing(index_elements=["code"]))
    actual_role_id = bind.scalar(sa.select(roles.c.id).where(roles.c.code == "user"))
    for permission_id in bind.scalars(sa.select(permissions.c.id).where(
        permissions.c.code.in_((
            "object.view", "channel.view", "event.view",
            "assignment.view", "forecast.view",
        ))
    )):
        bind.execute(insert(links).values(
            role_id=actual_role_id, permission_id=permission_id,
        ).on_conflict_do_nothing())
