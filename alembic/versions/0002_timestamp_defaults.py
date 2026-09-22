"""Add database-managed timestamp defaults and update triggers."""

from alembic import op
import sqlalchemy as sa


revision = "0002_timestamp_defaults"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


TABLES = ("users", "auth", "roles", "permissions", "files")
EPOCH_NOW = sa.text("EXTRACT(EPOCH FROM now())::bigint")


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(table, "created_at", server_default=EPOCH_NOW)
        op.alter_column(table, "updated_at", server_default=EPOCH_NOW)

    op.execute(
        """
        CREATE FUNCTION base_project_set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = EXTRACT(EPOCH FROM now())::bigint;
            RETURN NEW;
        END;
        $$
        """
    )

    for table in TABLES:
        op.execute(
            f"""
            CREATE TRIGGER set_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION base_project_set_updated_at()
            """
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP TRIGGER set_updated_at ON {table}")

    op.execute("DROP FUNCTION base_project_set_updated_at()")

    for table in TABLES:
        op.alter_column(table, "created_at", server_default=None)
        op.alter_column(table, "updated_at", server_default=None)
