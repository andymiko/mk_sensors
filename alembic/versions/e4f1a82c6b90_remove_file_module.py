"""Remove the file storage module.

Revision ID: e4f1a82c6b90
Revises: a7e4c19b2d61
"""
from alembic import op
import sqlalchemy as sa


revision = "e4f1a82c6b90"
down_revision = "a7e4c19b2d61"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE code IN ('file.upload', 'file.download'))"
    ))
    connection.execute(sa.text(
        "DELETE FROM permissions WHERE code IN ('file.upload', 'file.download')"
    ))
    op.drop_index(op.f("ix_files_user_id"), table_name="files")
    op.drop_table("files")


def downgrade():
    op.create_table(
        "files",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(255), nullable=False),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.BigInteger(), server_default=sa.text("EXTRACT(EPOCH FROM now())::bigint"), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), server_default=sa.text("EXTRACT(EPOCH FROM now())::bigint"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path"),
        sa.UniqueConstraint("stored_name"),
    )
    op.create_index(op.f("ix_files_user_id"), "files", ["user_id"], unique=False)

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "INSERT INTO permissions (id, code, name, description) VALUES "
            "(:upload_id, 'file.upload', 'Загрузка файлов', 'Загрузка файлов'), "
            "(:download_id, 'file.download', 'Просмотр и скачивание файлов', 'Просмотр и скачивание файлов') "
            "ON CONFLICT (code) DO NOTHING"
        ),
        {"upload_id": "file-upload", "download_id": "file-download"},
    )
    connection.execute(sa.text(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT roles.id, permissions.id FROM roles CROSS JOIN permissions "
        "WHERE roles.code = 'admin' "
        "AND permissions.code IN ('file.upload', 'file.download') "
        "ON CONFLICT DO NOTHING"
    ))
