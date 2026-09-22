"""RBAC roles, territories and role-specific assignments.

Revision ID: d82a64e913f0
Revises: 75c03db184ee
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

revision = "d82a64e913f0"
down_revision = "75c03db184ee"
branch_labels = None
depends_on = None

# Frozen migration data: do not import the application's changing catalog.
PERMISSIONS = {
    "object.view": "Просмотр объектов",
    "object.edit": "Редактирование справочника объектов",
    "channel.view": "Просмотр каналов",
    "channel.edit": "Редактирование справочника каналов",
    "event.view": "Просмотр событий и неисправностей",
    "dashboard.analytics": "Аналитический дашборд",
    "dashboard.summary": "Сводный дашборд",
    "map.view": "Просмотр карты доступных объектов",
    "forecast.view": "Просмотр прогнозов и журнала прогнозов",
    "forecast.verify": "Верификация прогноза",
    "forecast.decide": "Фиксация решения по прогнозу",
    "risk.view": "Просмотр уровней риска и статистики",
    "warning.view": "Просмотр предупреждений",
    "notification.view": "Просмотр уведомлений",
    "incident.view": "Просмотр статистики инцидентов",
    "ticket.view": "Просмотр заявок и результатов",
    "ticket.accept": "Принятие назначенной заявки в работу",
    "ticket.update_status": "Изменение статуса назначенной заявки",
    "ticket.record_result": "Запись результата проверки или ремонта",
    "ticket.comment": "Комментирование назначенной заявки",
    "maintenance.view": "Просмотр рекомендаций по обслуживанию",
    "repair.view": "Просмотр истории ремонтов",
    "report.export_pdf": "Экспорт отчётов PDF",
    "report.export_xlsx": "Экспорт отчётов XLSX",
    "access.manage": "Управление территориями и назначениями доступа",
    "audit.view": "Просмотр журнала действий пользователей",
    "settings.view": "Просмотр системных параметров",
    "user.view": "Просмотр пользователей",
    "user.edit": "Изменение пользователей и их ролей",
    "role.view": "Просмотр ролей",
    "role.create": "Создание ролей",
    "role.edit": "Изменение ролей и их разрешений",
    "permission.view": "Просмотр разрешений",
    "permission.create": "Создание разрешений",
    "permission.edit": "Изменение разрешений",
    "file.upload": "Загрузка файлов",
    "file.download": "Просмотр и скачивание файлов",
}
ROLES = {
    "user": ("Пользователь", ["file.upload", "file.download"]),
    "dispatcher": ("Диспетчер", [
        "object.view", "channel.view", "event.view", "dashboard.analytics", "map.view",
        "forecast.view", "forecast.verify", "forecast.decide", "risk.view",
        "warning.view", "notification.view",
    ]),
    "technician": ("Техник", [
        "object.view", "channel.view", "event.view", "map.view", "ticket.view",
        "ticket.accept", "ticket.update_status", "ticket.record_result", "ticket.comment",
        "maintenance.view", "repair.view",
    ]),
    "manager": ("Руководитель", [
        "object.view", "channel.view", "event.view", "dashboard.summary", "map.view",
        "risk.view", "incident.view", "ticket.view", "repair.view",
        "report.export_pdf", "report.export_xlsx",
    ]),
    "admin": ("Администратор", list(PERMISSIONS)),
}


def _id(kind, code):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"mk_sensors/rbac/{kind}/{code}"))


def seed_rbac(bind):
    roles = sa.table("roles", sa.column("id"), sa.column("code"), sa.column("name"), sa.column("description"))
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("name"), sa.column("description"))
    links = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    for code, name in PERMISSIONS.items():
        bind.execute(insert(permissions).values(
            id=_id("permission", code), code=code, name=name, description=name,
        ).on_conflict_do_nothing(index_elements=["code"]))
    for code, (name, codes) in ROLES.items():
        bind.execute(insert(roles).values(
            id=_id("role", code), code=code, name=name, description=name,
        ).on_conflict_do_nothing(index_elements=["code"]))
        # Resolve IDs by code to preserve pre-existing roles and permissions.
        role_id = bind.scalar(sa.select(roles.c.id).where(roles.c.code == code))
        permission_ids = bind.scalars(sa.select(permissions.c.id).where(permissions.c.code.in_(codes)))
        for permission_id in permission_ids:
            bind.execute(insert(links).values(role_id=role_id, permission_id=permission_id).on_conflict_do_nothing())


def _timestamps():
    return [
        sa.Column(name, sa.BigInteger(), nullable=False, server_default=sa.text("EXTRACT(EPOCH FROM now())::bigint"))
        for name in ("created_at", "updated_at")
    ]


def upgrade():
    op.create_table(
        "divisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "districts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("division_id", sa.String(36), sa.ForeignKey("divisions.id", ondelete="RESTRICT"), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_districts_division_id", "districts", ["division_id"])
    op.add_column("objects", sa.Column("district_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_objects_district", "objects", "districts", ["district_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_objects_district_id", "objects", ["district_id"])
    for table, column, column_type, target in [
        ("user_role_divisions", "division_id", sa.String(36), "divisions.id"),
        ("user_role_districts", "district_id", sa.String(36), "districts.id"),
        ("user_role_objects", "object_id", sa.BigInteger(), "objects.id"),
    ]:
        op.create_table(
            table,
            sa.Column("user_id", sa.String(36), primary_key=True),
            sa.Column("role_id", sa.String(36), primary_key=True),
            sa.Column(column, column_type, sa.ForeignKey(target, ondelete="CASCADE"), primary_key=True),
            sa.ForeignKeyConstraint(["user_id", "role_id"], ["user_roles.user_id", "user_roles.role_id"], ondelete="CASCADE"),
        )
    seed_rbac(op.get_bind())


def downgrade():
    # Keep role/permission data: it may already be assigned to real users.
    for table in ("user_role_objects", "user_role_districts", "user_role_divisions"):
        op.drop_table(table)
    op.drop_index("ix_objects_district_id", table_name="objects")
    op.drop_constraint("fk_objects_district", "objects", type_="foreignkey")
    op.drop_column("objects", "district_id")
    op.drop_table("districts")
    op.drop_table("divisions")
