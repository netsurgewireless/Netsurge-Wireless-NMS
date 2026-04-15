"""Authentication and security module."""

import logging
import secrets
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class User:
    username: str
    password_hash: str
    role: str = "viewer"
    api_keys: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    enabled: bool = True


@dataclass
class APIKey:
    key: str
    name: str
    user: str
    permissions: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    enabled: bool = True


class AuthManager:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("auth.json")
        self.users: dict[str, User] = {}
        self.api_keys: dict[str, APIKey] = {}
        self.session_timeout = 3600
        self._load()
    
    def _load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                    
                    for username, user_data in data.get("users", {}).items():
                        self.users[username] = User(
                            username=username,
                            password_hash=user_data["password_hash"],
                            role=user_data.get("role", "viewer"),
                            api_keys=user_data.get("api_keys", []),
                            created_at=datetime.fromisoformat(user_data.get("created_at", datetime.now().isoformat())),
                            last_login=datetime.fromisoformat(user_data["last_login"]) if user_data.get("last_login") else None,
                            enabled=user_data.get("enabled", True),
                        )
                    
                    for key_data in data.get("api_keys", []):
                        api_key = APIKey(
                            key=key_data["key"],
                            name=key_data["name"],
                            user=key_data["user"],
                            permissions=key_data.get("permissions", []),
                            created_at=datetime.fromisoformat(key_data.get("created_at", datetime.now().isoformat())),
                            expires_at=datetime.fromisoformat(key_data["expires_at"]) if key_data.get("expires_at") else None,
                            last_used=datetime.fromisoformat(key_data["last_used"]) if key_data.get("last_used") else None,
                            enabled=key_data.get("enabled", True),
                        )
                        self.api_keys[key_data["key"]] = api_key
                        
            except Exception as e:
                logger.warning(f"Failed to load auth config: {e}")
    
    def save(self):
        data = {
            "users": {},
            "api_keys": [],
        }
        
        for user in self.users.values():
            data["users"][user.username] = {
                "password_hash": user.password_hash,
                "role": user.role,
                "api_keys": user.api_keys,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "enabled": user.enabled,
            }
        
        for api_key in self.api_keys.values():
            data["api_keys"].append({
                "key": api_key.key,
                "name": api_key.name,
                "user": api_key.user,
                "permissions": api_key.permissions,
                "created_at": api_key.created_at.isoformat(),
                "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                "last_used": api_key.last_used.isoformat() if api_key.last_used else None,
                "enabled": api_key.enabled,
            })
        
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        if salt is None:
            salt = secrets.token_hex(16)
        
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            100000,
        )
        return key.hex(), salt
    
    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        key, _ = AuthManager.hash_password(password, salt)
        return hmac.compare_digest(key, password_hash)
    
    def create_user(self, username: str, password: str, role: str = "viewer") -> bool:
        if username in self.users:
            return False
        
        password_hash, salt = self.hash_password(password)
        
        self.users[username] = User(
            username=username,
            password_hash=salt + ":" + password_hash,
            role=role,
        )
        self.save()
        return True
    
    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        user = self.users.get(username)
        if not user or not user.enabled:
            return None
        
        try:
            salt, password_hash = user.password_hash.split(":")
            if self.verify_password(password, password_hash, salt):
                user.last_login = datetime.now()
                self.save()
                return user.role
        except ValueError:
            pass
        
        return None
    
    def create_api_key(self, name: str, user: str, permissions: list[str] = None, expires_days: Optional[int] = None) -> str:
        api_key = secrets.token_urlsafe(32)
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        self.api_keys[api_key] = APIKey(
            key=api_key,
            name=name,
            user=user,
            permissions=permissions or ["read"],
            expires_at=expires_at,
        )
        
        self.save()
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[dict]:
        key = self.api_keys.get(api_key)
        if not key or not key.enabled:
            return None
        
        if key.expires_at and key.expires_at < datetime.now():
            return None
        
        key.last_used = datetime.now()
        self.save()
        
        return {
            "user": key.user,
            "permissions": key.permissions,
            "name": key.name,
        }
    
    def revoke_api_key(self, api_key: str) -> bool:
        if api_key in self.api_keys:
            del self.api_keys[api_key]
            self.save()
            return True
        return False
    
    def delete_user(self, username: str) -> bool:
        if username in self.users:
            del self.users[username]
            self.save()
            return True
        return False
    
    def require_auth(self, role: str = "viewer"):
        def decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator


class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[datetime]] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        self.requests[identifier] = [
            t for t in self.requests[identifier] if t > cutoff
        ]
        
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        self.requests[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str) -> int:
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        if identifier not in self.requests:
            return self.max_requests
        
        count = len([
            t for t in self.requests[identifier] if t > cutoff
        ])
        
        return max(0, self.max_requests - count)


class TokenManager:
    def __init__(self, secret_key: str = None, expiry_seconds: int = 3600):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.expiry_seconds = expiry_seconds
        self.tokens: dict[str, dict] = {}
    
    def create_token(self, user: str, role: str = "viewer") -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(seconds=self.expiry_seconds)
        
        self.tokens[token] = {
            "user": user,
            "role": role,
            "expires_at": expires_at,
            "created_at": datetime.now(),
        }
        
        return token
    
    def verify_token(self, token: str) -> Optional[dict]:
        if token not in self.tokens:
            return None
        
        token_data = self.tokens[token]
        
        if token_data["expires_at"] < datetime.now():
            del self.tokens[token]
            return None
        
        return {
            "user": token_data["user"],
            "role": token_data["role"],
        }
    
    def revoke_token(self, token: str) -> bool:
        if token in self.tokens:
            del self.tokens[token]
            return True
        return False


class TLSManager:
    def __init__(self):
        self.cert_path = Path("cert.pem")
        self.key_path = Path("key.pem")
    
    def generate_self_signed(self, common_name: str = "localhost", days: int = 365):
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Organization"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(common_name),
                x509.DNSName("localhost"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        with open(self.cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open(self.key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        return self.cert_path, self.key_path