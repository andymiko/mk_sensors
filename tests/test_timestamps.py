from app.dbapi.models.users import User


def test_timestamp_columns_have_database_defaults():
    table = User.__table__

    assert table.c.created_at.server_default is not None
    assert table.c.updated_at.server_default is not None
