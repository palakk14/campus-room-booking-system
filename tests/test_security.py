import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from security.security import (
    hash_password, verify_password,
    sanitize_input, is_valid_email, is_strong_password,
    generate_csrf_token, validate_csrf_token,
    is_rate_limited
)


# ─────────────────────────────────────────────
# PASSWORD TESTS
# ─────────────────────────────────────────────

class TestPasswordHashing:

    def test_hash_is_not_plain_text(self):
        hashed = hash_password("MyPassword1")
        assert hashed != "MyPassword1"

    def test_correct_password_verifies(self):
        hashed = hash_password("MyPassword1")
        assert verify_password("MyPassword1", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("MyPassword1")
        assert verify_password("WrongPass1", hashed) is False

    def test_hash_has_salt_colon_format(self):
        hashed = hash_password("Test1234")
        parts = hashed.split(":")
        assert len(parts) == 2

    def test_same_password_gives_different_hashes(self):
        h1 = hash_password("SamePass1")
        h2 = hash_password("SamePass1")
        assert h1 != h2   # different salts

    def test_empty_password_hashes_safely(self):
        hashed = hash_password("")
        assert ":" in hashed  # still salted, no crash


# ─────────────────────────────────────────────
# INPUT SANITIZATION TESTS
# ─────────────────────────────────────────────

class TestSanitizeInput:

    def test_strips_whitespace(self):
        assert sanitize_input("  hello  ") == "hello"

    def test_removes_null_bytes(self):
        assert "\x00" not in sanitize_input("abc\x00def")

    def test_truncates_to_max_length(self):
        long_str = "a" * 300
        assert len(sanitize_input(long_str)) == 255

    def test_custom_max_length(self):
        assert len(sanitize_input("hello world", max_length=5)) == 5

    def test_non_string_returns_empty(self):
        assert sanitize_input(None) == ""    # type: ignore
        assert sanitize_input(123) == ""     # type: ignore

    def test_normal_string_unchanged(self):
        assert sanitize_input("John Doe") == "John Doe"


# ─────────────────────────────────────────────
# EMAIL VALIDATION TESTS
# ─────────────────────────────────────────────

class TestEmailValidation:

    def test_valid_email(self):
        assert is_valid_email("user@example.com") is True

    def test_valid_email_with_dots(self):
        assert is_valid_email("first.last@domain.org") is True

    def test_invalid_no_at(self):
        assert is_valid_email("userexample.com") is False

    def test_invalid_no_domain(self):
        assert is_valid_email("user@") is False

    def test_invalid_empty(self):
        assert is_valid_email("") is False

    def test_invalid_spaces(self):
        assert is_valid_email("user @example.com") is False


# ─────────────────────────────────────────────
# PASSWORD STRENGTH TESTS
# ─────────────────────────────────────────────

class TestPasswordStrength:

    def test_strong_password(self):
        valid, msg = is_strong_password("Secure123")
        assert valid is True
        assert msg == ""

    def test_too_short(self):
        valid, msg = is_strong_password("Ab1")
        assert valid is False
        assert "8" in msg

    def test_no_uppercase(self):
        valid, msg = is_strong_password("password123")
        assert valid is False
        assert "uppercase" in msg.lower()

    def test_no_number(self):
        valid, msg = is_strong_password("Password")
        assert valid is False
        assert "number" in msg.lower()

    def test_boundary_8_chars_valid(self):
        valid, _ = is_strong_password("Passw0rd")
        assert valid is True


# ─────────────────────────────────────────────
# RATE LIMITING TESTS
# ─────────────────────────────────────────────

class TestRateLimiting:

    def test_first_request_not_limited(self):
        # Use a unique IP to avoid state contamination
        assert is_rate_limited("10.0.0.1") is False

    def test_exceeds_limit(self):
        ip = "10.0.0.99"
        # 10 requests should be fine, 11th should be limited
        for _ in range(10):
            is_rate_limited(ip)
        assert is_rate_limited(ip) is True

    def test_different_ips_independent(self):
        ip_a = "192.168.1.1"
        ip_b = "192.168.1.2"
        for _ in range(10):
            is_rate_limited(ip_a)
        # ip_a is now limited, ip_b should still be free
        assert is_rate_limited(ip_b) is False
