from datetime import datetime, timedelta
import hashlib
import hmac
import os
from jose import jwt

SECRET_KEY = "secret123"
ALGORITHM = "HS256"
HASH_ITERATIONS = 120_000


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ITERATIONS)
    return f"pbkdf2_sha256${HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_password):
    if not stored_password:
        return False

    if not stored_password.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(password, stored_password)

    try:
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
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=2)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except:
        return None
