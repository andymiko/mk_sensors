"""Add direct object and user memberships for divisions.

Revision ID: f6b2d1097c44
Revises: e4f1a82c6b90
"""
from alembic import op
import sqlalchemy as sa


revision = "f6b2d1097c44"
down_revision = "e4f1a82c6b90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "division_objects",
        sa.Column("division_id", sa.String(36), sa.ForeignKey("divisions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("object_id", sa.BigInteger(), sa.ForeignKey("objects.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_division_objects_object_id", "division_objects", ["object_id"])
    op.create_table(
        "user_divisions",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("division_id", sa.String(36), sa.ForeignKey("divisions.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_user_divisions_division_id", "user_divisions", ["division_id"])
    op.execute(sa.text(
        "INSERT INTO division_objects (division_id, object_id) "
        "SELECT DISTINCT district_divisions.division_id, objects.id "
        "FROM objects JOIN district_divisions ON district_divisions.district_id = objects.district_id "
        "ON CONFLICT DO NOTHING"
    ))
    op.execute(sa.text(
        "INSERT INTO user_divisions (user_id, division_id) "
        "SELECT DISTINCT user_id, division_id FROM user_role_divisions "
        "ON CONFLICT DO NOTHING"
    ))
    op.execute(sa.text(
        "INSERT INTO user_divisions (user_id, division_id) "
        "SELECT DISTINCT scopes.user_id, links.division_id "
        "FROM user_role_districts AS scopes "
        "JOIN district_divisions AS links ON links.district_id = scopes.district_id "
        "ON CONFLICT DO NOTHING"
    ))
    op.execute(sa.text(
        "INSERT INTO user_divisions (user_id, division_id) "
        "SELECT DISTINCT scopes.user_id, links.division_id "
        "FROM user_role_objects AS scopes "
        "JOIN objects ON objects.id = scopes.object_id "
        "JOIN district_divisions AS links ON links.district_id = objects.district_id "
        "ON CONFLICT DO NOTHING"
    ))
    op.execute(sa.text(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT roles.id, permissions.id FROM roles CROSS JOIN permissions "
        "WHERE roles.code = 'manager' "
        "AND permissions.code NOT LIKE 'user.%' "
        "AND permissions.code NOT LIKE 'role.%' "
        "AND permissions.code NOT LIKE 'permission.%' "
        "AND permissions.code NOT IN ('audit.view', 'settings.view') "
        "ON CONFLICT DO NOTHING"
    ))


def downgrade():
    op.drop_index("ix_user_divisions_division_id", table_name="user_divisions")
    op.drop_index("ix_division_objects_object_id", table_name="division_objects")
    op.drop_table("user_divisions")
    op.drop_table("division_objects")
