import bcrypt
from jose import jwt, JWTError
from datetime import datetime,timedelta, timezone
from fastapi import HTTPException
from cryptography.fernet import Fernet
from .config import settings

SECRET_KEY = settings.SECRET_KEY
ENCRYPTION_KEY = settings.ENCRYPTION_KEY
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

def hash_password(password: str) -> str:
    """ hashing the password before storing"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """checks the password hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def create_jwt_token(user_id: str, tenant_id: str | None, email: str) -> str:
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)    
        }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
def encrypt_api_key(key: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(key.encode()).decode()

def decrypt_api_key(key: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.decrypt(key.encode()).decode()
