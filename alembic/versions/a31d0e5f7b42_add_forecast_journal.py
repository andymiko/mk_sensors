"""Add forecast journal and event ingestion sequence.

Revision ID: a31d0e5f7b42
Revises: 9c4f6a1d2e30
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert


revision = "a31d0e5f7b42"
down_revision = "9c4f6a1d2e30"
branch_labels = None
depends_on = None

PERMISSION_CODE = "forecast.create"


def _permission_id(code):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"mk_sensors/rbac/permission/{code}"))


def upgrade():
    op.execute(sa.text("CREATE SEQUENCE events_ingest_id_seq"))
    op.execute(sa.text(
        "SELECT setval('events_ingest_id_seq', "
        "GREATEST(COALESCE((SELECT MAX(id) FROM events), 0) + 1, 1), false)"
    ))
    op.alter_column(
        "events", "id",
        existing_type=sa.BigInteger(),
        server_default=sa.text("nextval('events_ingest_id_seq')"),
    )
    op.create_table(
        "forecasts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("events.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("channel_id", sa.BigInteger(), sa.ForeignKey("channels.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("object_id", sa.BigInteger(), sa.ForeignKey("objects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("model_key", sa.String(30), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("forecast_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("target_from", sa.DateTime(timezone=False), nullable=False),
        sa.Column("target_until", sa.DateTime(timezone=False), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("warning", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())::bigint")),
        sa.Column("updated_at", sa.BigInteger(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())::bigint")),
    )
    op.create_index("ix_forecasts_object_created", "forecasts", ["object_id", "created_at"])
    op.create_index("ix_forecasts_channel_created", "forecasts", ["channel_id", "created_at"])

    bind = op.get_bind()
    permissions = sa.table(
        "permissions", sa.column("id"), sa.column("code"),
        sa.column("name"), sa.column("description"),
    )
    roles = sa.table("roles", sa.column("id"), sa.column("code"))
    links = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    permission_id = _permission_id(PERMISSION_CODE)
    bind.execute(insert(permissions).values(
        id=permission_id,
        code=PERMISSION_CODE,
        name="Создание прогноза по показанию датчика",
        description="Сохранение показания датчика и запуск модели прогнозирования",
    ).on_conflict_do_nothing(index_elements=["code"]))
    permission_id = bind.scalar(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)
    )
    role_ids = bind.scalars(sa.select(roles.c.id).where(roles.c.code.in_(("dispatcher", "admin"))))
    for role_id in role_ids:
        bind.execute(insert(links).values(
            role_id=role_id, permission_id=permission_id,
        ).on_conflict_do_nothing())


def downgrade():
    bind = op.get_bind()
    bind.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE code = 'forecast.create')"
    ))
    bind.execute(sa.text("DELETE FROM permissions WHERE code = 'forecast.create'"))
    op.drop_index("ix_forecasts_channel_created", table_name="forecasts")
    op.drop_index("ix_forecasts_object_created", table_name="forecasts")
    op.drop_table("forecasts")
    op.alter_column(
        "events", "id",
        existing_type=sa.BigInteger(),
        server_default=None,
    )
    op.execute(sa.text("DROP SEQUENCE events_ingest_id_seq"))
