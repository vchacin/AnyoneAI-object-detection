from datetime import timedelta

from app.backend.core.security import create_token, hash_password, verify_password, decode_token


def test_password_hash_is_not_reversible_and_verifies():
    encoded = hash_password("correct horse battery staple")
    assert encoded.startswith("scrypt$")
    assert encoded != "correct horse battery staple"
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong", encoded)


def test_access_token_contains_tenant_claims():
    token = create_token(subject="user-1", role="employee", store_id="store-a",
                         token_type="access", expires_delta=timedelta(minutes=5))
    claims = decode_token(token)
    assert claims["sub"] == "user-1"
    assert claims["role"] == "employee"
    assert claims["store_id"] == "store-a"
    assert claims["type"] == "access"
