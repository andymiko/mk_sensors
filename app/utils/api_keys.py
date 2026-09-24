import hashlib
import secrets


def generate_api_token() -> str:
    """Return a high-entropy token suitable for an HTTP header."""
    return secrets.token_urlsafe(48)


def hash_api_token(token: str) -> str:
    """Create the irreversible lookup value stored in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
