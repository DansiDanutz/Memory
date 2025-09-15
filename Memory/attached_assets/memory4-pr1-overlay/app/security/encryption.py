import os, base64, hashlib, logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

log = logging.getLogger(__name__)

ENC_PREFIX = "ENC::"

class EncryptionService:
    """Fernet encryption with per-user/per-tier derived keys."""
    def __init__(self, master_key_env: str = "ENCRYPTION_MASTER_KEY"):
        self.master_key_b64 = os.getenv(master_key_env, "").strip()

    def _is_enabled(self) -> bool:
        return bool(self.master_key_b64)

    def _derive_key(self, user_phone: str, category: str) -> bytes:
        # Derive per-user/per-category key from the base64 master key using PBKDF2
        raw_master = base64.urlsafe_b64decode(self.master_key_b64.encode("utf-8"))
        salt_src = f"{user_phone}:{category}:{self.master_key_b64}".encode("utf-8")
        salt = hashlib.sha256(salt_src).digest()
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000)
        derived = kdf.derive(raw_master)
        return base64.urlsafe_b64encode(derived)

    async def encrypt(self, plaintext: str, user_phone: str, category: str) -> str:
        if not self._is_enabled():
            return plaintext
        try:
            f = Fernet(self._derive_key(user_phone, category))
            token = f.encrypt(plaintext.encode("utf-8")).decode("utf-8")
            return ENC_PREFIX + token
        except Exception as e:
            log.exception("encrypt failed; storing plaintext")
            return plaintext

    def decrypt(self, value: str, user_phone: str, category: str) -> Optional[str]:
        if not value or not value.startswith(ENC_PREFIX):
            return value
        if not self._is_enabled():
            return None
        token = value[len(ENC_PREFIX):]
        try:
            f = Fernet(self._derive_key(user_phone, category))
            return f.decrypt(token.encode("utf-8")).decode("utf-8")
        except Exception:
            log.exception("decrypt failed")
            return None
