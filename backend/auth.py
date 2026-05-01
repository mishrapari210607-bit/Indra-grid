from datetime import datetime, timedelta
import hashlib
import hmac
import os
from jose import jwt

SECRET_KEY = os.getenv("INDRA_GRID_SECRET_KEY", "dev-only-change-me")
ALGORITHM = "HS256"
HASH_ITERATIONS = 120_000


def hash_password(password):
    # Store passwords as salted PBKDF2 hashes instead of plain text.
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ITERATIONS)
    return f"pbkdf2_sha256${HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_password):
    # Empty passwords never authenticate.
    if not stored_password:
        return False

    # Backward compatibility for old demo users that were saved as plain text.
    if not stored_password.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(password, stored_password)

    try:
        # Recreate the PBKDF2 digest with the stored salt and compare safely.
        _, iterations, salt_hex, digest_hex = stored_password.split("$", 3)
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except ValueError:
        return False

def create_token(username):
    # JWT carries the username and expires after two hours.
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=2)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token):
    # Return the username from a valid token; invalid/expired tokens become None.
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except Exception:
        return None
