import hashlib
import hmac
import os
import re
import time
from functools import wraps
from flask import session, redirect, request, abort, g
from collections import defaultdict

# ─────────────────────────────────────────────
# PASSWORD HASHING  (no plain-text passwords!)
# ─────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Return a salted SHA-256 hash for storage."""
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + plain_password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify a plain password against the stored salt:hash string."""
    try:
        salt, hashed = stored_hash.split(":")
        check = hashlib.sha256((salt + plain_password).encode()).hexdigest()
        return hmac.compare_digest(check, hashed)
    except Exception:
        return False


# ─────────────────────────────────────────────
# INPUT SANITIZATION
# ─────────────────────────────────────────────

def sanitize_input(value: str, max_length: int = 255) -> str:
    """Strip dangerous characters and trim length."""
    if not isinstance(value, str):
        return ""
    # Remove null bytes and strip leading/trailing whitespace
    value = value.replace("\x00", "").strip()
    # Allow only printable characters
    value = re.sub(r"[^\x20-\x7E]", "", value)
    return value[:max_length]


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))


def is_strong_password(password: str) -> tuple[bool, str]:
    """Return (is_valid, error_message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    return True, ""


# ─────────────────────────────────────────────
# CSRF PROTECTION
# ─────────────────────────────────────────────

def generate_csrf_token() -> str:
    """Generate a CSRF token and store in session."""
    if "csrf_token" not in session:
        session["csrf_token"] = os.urandom(24).hex()
    return session["csrf_token"]


def validate_csrf_token() -> bool:
    """Check that the POST form's token matches the session token."""
    token = request.form.get("csrf_token", "")
    return hmac.compare_digest(token, session.get("csrf_token", ""))


def csrf_protect(f):
    """Decorator: abort(403) if CSRF token is missing or wrong on POST."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "POST":
            if not validate_csrf_token():
                abort(403)
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# RATE LIMITING  (in-memory, per IP)
# ─────────────────────────────────────────────

_rate_store: dict = defaultdict(list)   # ip -> [timestamp, ...]
RATE_LIMIT = 10       # max requests
RATE_WINDOW = 60      # seconds


def is_rate_limited(ip: str) -> bool:
    now = time.time()
    # Keep only requests inside the window
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < RATE_WINDOW]
    if len(_rate_store[ip]) >= RATE_LIMIT:
        return True
    _rate_store[ip].append(now)
    return False


def rate_limit(f):
    """Decorator: 429 if the caller exceeds RATE_LIMIT requests / RATE_WINDOW s."""
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr or "unknown"
        if is_rate_limited(ip):
            abort(429)
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# LOGIN REQUIRED DECORATOR
# ─────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        if session.get("role") != "admin":
            return redirect("/dashboard")
        return f(*args, **kwargs)
    return decorated
