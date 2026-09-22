import pytest

from app.dbapi.models import Events
from app.dbapi.models.access import Districts


@pytest.mark.asyncio
async def test_new_district_requires_at_least_one_division():
    with pytest.raises(ValueError, match="Укажите хотя бы одно подразделение"):
        await Districts.insert_new_district(
            code="district",
            name="Район",
            division_ids=[],
        )


@pytest.mark.asyncio
async def test_primary_division_must_be_linked_to_district():
    with pytest.raises(ValueError, match="Основное подразделение должно входить"):
        await Districts.insert_new_district(
            code="district",
            name="Район",
            division_ids=["division-1"],
            primary_division_id="division-2",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("offset", "limit", "message"),
    [(-1, 100, "offset"), (0, 0, "limit"), (0, 1001, "limit")],
)
async def test_crud_page_validates_bounds_before_query(offset, limit, message):
    with pytest.raises(ValueError, match=message):
        await Events.get_events_page(offset=offset, limit=limit)
