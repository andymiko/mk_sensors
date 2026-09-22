import pytest

from app.utils.security import create_access_token, decode_access_token, get_password_hash, verify_password


def test_password_hash_roundtrip():
    hashed = get_password_hash("StrongPassword123")
    assert hashed != "StrongPassword123"
    assert verify_password("StrongPassword123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token = create_access_token({"sub": "user-id"})
    assert decode_access_token(token)["sub"] == "user-id"


def test_invalid_access_token_is_rejected():
    with pytest.raises(ValueError):
        decode_access_token("not-a-token")
