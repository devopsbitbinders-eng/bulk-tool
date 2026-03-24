import hashlib
import os
import secrets
from datetime import datetime, timedelta

# Simple secret key for session signing (should be in .env in production)
SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "Bitbinders_Messenger_Secret_2026_!@#")

def hash_password(password: str, salt: str = None):
    """Hashes a password with a salt using SHA-256."""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Use PBKDF2 for better security than plain SHA-256
    pwdhash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000
    ).hex()
    
    return pwdhash, salt

def verify_password(password: str, salt: str, password_hash: str):
    """Verifies a password against a hash and salt."""
    check_hash, _ = hash_password(password, salt)
    return check_hash == password_hash

def create_session_token(username: str):
    """Creates a simple signed session token: username:expiry:signature"""
    expiry = (datetime.utcnow() + timedelta(days=7)).timestamp()
    data = f"{username}:{expiry}"
    signature = hashlib.sha256(f"{data}:{SECRET_KEY}".encode()).hexdigest()
    return f"{data}:{signature}"

def verify_session_token(token: str):
    """Verifies a session token and returns the username if valid."""
    if not token:
        return None
    
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return None
            
        username, expiry_str, signature = parts
        expiry = float(expiry_str)
        
        # Check signature
        expected_sig = hashlib.sha256(f"{username}:{expiry_str}:{SECRET_KEY}".encode()).hexdigest()
        if not secrets.compare_digest(signature, expected_sig):
            return None
            
        # Check expiry
        if datetime.utcnow().timestamp() > expiry:
            return None
            
        return username
    except Exception:
        return None
