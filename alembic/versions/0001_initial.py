"""Initial reusable application schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    def timestamps():
        return [sa.Column("created_at", sa.BigInteger(), nullable=False), sa.Column("updated_at", sa.BigInteger(), nullable=False)]

    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("email", sa.String(255), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), *timestamps())
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("auth", sa.Column("id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True), sa.Column("email", sa.String(255), nullable=False), sa.Column("password", sa.String(255), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), *timestamps())
    op.create_index("ix_auth_email", "auth", ["email"], unique=True)
    op.create_table("roles", sa.Column("id", sa.String(36), primary_key=True), sa.Column("code", sa.String(100), nullable=False), sa.Column("name", sa.String(100), nullable=False), sa.Column("description", sa.String(500)), *timestamps())
    op.create_index("ix_roles_code", "roles", ["code"], unique=True)
    op.create_table("permissions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("code", sa.String(100), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("description", sa.String(500)), *timestamps())
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)
    op.create_table("user_roles", sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True), sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("role_permissions", sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True), sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("files", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("original_name", sa.String(255), nullable=False), sa.Column("stored_name", sa.String(255), nullable=False, unique=True), sa.Column("path", sa.String(512), nullable=False, unique=True), sa.Column("size", sa.BigInteger(), nullable=False), sa.Column("content_type", sa.String(255), nullable=False), sa.Column("status", sa.String(20), nullable=False), *timestamps())
    op.create_index("ix_files_user_id", "files", ["user_id"])

    roles = sa.table("roles", sa.column("id", sa.String), sa.column("code", sa.String), sa.column("name", sa.String), sa.column("description", sa.String), sa.column("created_at", sa.BigInteger), sa.column("updated_at", sa.BigInteger))
    permissions = sa.table("permissions", sa.column("id", sa.String), sa.column("code", sa.String), sa.column("name", sa.String), sa.column("description", sa.String), sa.column("created_at", sa.BigInteger), sa.column("updated_at", sa.BigInteger))
    now = 0
    op.bulk_insert(roles, [{"id": "role-user", "code": "user", "name": "Пользователь", "description": "Базовый доступ", "created_at": now, "updated_at": now}, {"id": "role-admin", "code": "admin", "name": "Администратор", "description": "Полное управление", "created_at": now, "updated_at": now}])
    rows = [
        ("file.upload", "Загрузка файлов"), ("file.download", "Скачивание файлов"),
        ("user.view", "Просмотр пользователей"), ("user.edit", "Управление пользователями"),
        ("role.view", "Просмотр ролей"), ("role.create", "Создание ролей"), ("role.edit", "Изменение ролей"),
        ("permission.view", "Просмотр разрешений"), ("permission.create", "Создание разрешений"), ("permission.edit", "Изменение разрешений"),
    ]
    op.bulk_insert(permissions, [{"id": f"permission-{index}", "code": code, "name": name, "description": name, "created_at": now, "updated_at": now} for index, (code, name) in enumerate(rows, 1)])
    role_permissions = sa.table("role_permissions", sa.column("role_id", sa.String), sa.column("permission_id", sa.String))
    op.bulk_insert(role_permissions, [{"role_id": "role-user", "permission_id": "permission-1"}, {"role_id": "role-user", "permission_id": "permission-2"}, *[{"role_id": "role-admin", "permission_id": f"permission-{index}"} for index in range(1, len(rows) + 1)]])


def downgrade() -> None:
    for table in ("files", "role_permissions", "user_roles", "permissions", "roles", "auth", "users"):
        op.drop_table(table)
