import os
from cryptography.fernet import Fernet
import hashlib

# Key for symmetric encryption (Aadhaar).
# In production, this should be an environment variable.
# Example generated with Fernet.generate_key()
# We use a static one for the app to allow immediate testing without env files.
ENCRYPTION_KEY = os.environ.get('UCASE_ENCRYPTION_KEY', b'G7r9W1mZpB6yT3FvKxQsDcX1vR0HnM4lG5oN2jA9E8c=')
fernet = Fernet(ENCRYPTION_KEY)

def encrypt_data(data: str) -> str:
    """Encrypts string data returning an encoded string."""
    encrypted_bytes = fernet.encrypt(data.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_data(token: str) -> str:
    """Decrypts string data restoring the original string."""
    try:
        decrypted_bytes = fernet.decrypt(token.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        return ""

def hash_password(password: str) -> str:
    """Creates a SHA-256 hash of the password."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the hash."""
    return hash_password(plain_password) == hashed_password

def validate_aadhaar_format(aadhaar: str) -> bool:
    """Basic validation for 12 digit Aadhaar formatting."""
    aadhaar = aadhaar.strip()
    if len(aadhaar) == 12 and aadhaar.isdigit():
        return True
    return False
