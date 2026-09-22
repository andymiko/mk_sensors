from unittest.mock import AsyncMock, Mock

import pytest

from app.api import admin


@pytest.mark.asyncio
async def test_list_all_files_uses_unfiltered_repository_page(monkeypatch):
    page = AsyncMock(return_value=([], 0))
    monkeypatch.setattr(admin.Files, "page", page)

    current_user = Mock()
    current_user.is_admin.return_value = True

    db = AsyncMock()
    result = await admin.list_all_files(
        db=db,
        current_user=current_user,
        page=1,
        page_size=100,
        search=None,
    )

    page.assert_awaited_once_with(
        page=1,
        page_size=100,
        search=None,
        db=db,
    )
    assert result.items == []
    assert result.total == 0
