from collections import Counter

from app.schemas.auths import RegisterRequest
from scripts.seed_users import USERS


def test_seed_catalog_contains_required_users():
    roles = Counter(user.role_code for user in USERS)

    assert len(USERS) == 30
    assert roles == {
        "dispatcher": 4,
        "technician": 24,
        "admin": 1,
        "manager": 1,
    }
    technician_divisions = Counter(
        user.division_codes[0] for user in USERS if user.role_code == "technician"
    )
    assert set(technician_divisions.values()) == {3}


def test_registration_accepts_any_valid_email_domain():
    for email in ("user@example.com", "employee@company.org", "worker@gmail.com"):
        request = RegisterRequest(email=email, password="password123", name="Пользователь")
        assert str(request.email) == email
