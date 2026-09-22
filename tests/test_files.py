import pytest
from fastapi import HTTPException

from app.api.files import _safe_extension
from app.config import settings


def test_extension_is_normalized():
    assert _safe_extension("Report.PDF") == ".pdf"


def test_extension_allowlist(monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_EXTENSIONS", [".pdf"])
    with pytest.raises(HTTPException) as error:
        _safe_extension("payload.exe")
    assert error.value.status_code == 415
