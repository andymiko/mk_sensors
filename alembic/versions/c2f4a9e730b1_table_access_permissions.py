"""Grant core table access to all roles and forecast testing to managers.

Revision ID: c2f4a9e730b1
Revises: b8e1c7d4a290
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert


revision = "c2f4a9e730b1"
down_revision = "b8e1c7d4a290"
branch_labels = None
depends_on = None

CORE = ("object.view", "channel.view", "event.view", "assignment.view", "forecast.view")


def upgrade():
    bind = op.get_bind()
    roles = sa.table("roles", sa.column("id"), sa.column("code"))
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    links = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    for role_id, role_code in bind.execute(sa.select(roles.c.id, roles.c.code)):
        codes = set(CORE)
        if role_code == "manager":
            codes.add("forecast.create")
        for permission_id in bind.scalars(
            sa.select(permissions.c.id).where(permissions.c.code.in_(codes))
        ):
            bind.execute(insert(links).values(
                role_id=role_id, permission_id=permission_id,
            ).on_conflict_do_nothing())


def downgrade():
    # Existing installations may have granted these permissions manually;
    # keep links intact on downgrade rather than revoking valid access.
    pass
