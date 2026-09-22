"""Add technician assignments.

Revision ID: 9c4f6a1d2e30
Revises: f6b2d1097c44
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert


revision = "9c4f6a1d2e30"
down_revision = "f6b2d1097c44"
branch_labels = None
depends_on = None

PERMISSIONS = {
    "assignment.view": "Просмотр заданий",
    "assignment.create": "Создание заданий техникам",
    "assignment.complete": "Завершение назначенных заданий",
}
ROLE_PERMISSIONS = {
    "dispatcher": ("assignment.view", "assignment.create"),
    "technician": ("assignment.view", "assignment.complete"),
    "manager": ("assignment.view",),
    "admin": tuple(PERMISSIONS),
}


def _permission_id(code):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"mk_sensors/rbac/permission/{code}"))


def upgrade():
    op.create_table(
        "assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("object_id", sa.BigInteger(), sa.ForeignKey("objects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), sa.ForeignKey("channels.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("technician_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("dispatcher_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())::bigint")),
        sa.Column("updated_at", sa.BigInteger(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())::bigint")),
        sa.CheckConstraint("status IN ('pending', 'completed')", name="ck_assignments_status"),
        sa.UniqueConstraint("object_id", "scheduled_date", name="uq_assignments_object_date"),
    )
    op.create_index("ix_assignments_technician_status", "assignments", ["technician_id", "status"])

    bind = op.get_bind()
    permissions = sa.table(
        "permissions", sa.column("id"), sa.column("code"),
        sa.column("name"), sa.column("description"),
    )
    roles = sa.table("roles", sa.column("id"), sa.column("code"))
    links = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    for code, name in PERMISSIONS.items():
        bind.execute(insert(permissions).values(
            id=_permission_id(code), code=code, name=name, description=name,
        ).on_conflict_do_nothing(index_elements=["code"]))
    for role_code, permission_codes in ROLE_PERMISSIONS.items():
        role_id = bind.scalar(sa.select(roles.c.id).where(roles.c.code == role_code))
        if role_id is None:
            continue
        permission_ids = bind.scalars(
            sa.select(permissions.c.id).where(permissions.c.code.in_(permission_codes))
        )
        for permission_id in permission_ids:
            bind.execute(insert(links).values(
                role_id=role_id, permission_id=permission_id,
            ).on_conflict_do_nothing())


def downgrade():
    op.drop_index("ix_assignments_technician_status", table_name="assignments")
    op.drop_table("assignments")
    bind = op.get_bind()
    bind.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE code LIKE 'assignment.%')"
    ))
    bind.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'assignment.%'"))
