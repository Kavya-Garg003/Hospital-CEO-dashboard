"""
backend/encryption.py
---------------------
AES-256-GCM field-level encryption for Protected Health Information (PHI).

Fields encrypted at rest:
  patients.name, patients.phone, patients.aadhaar_hash,
  patients.diagnosis, insurance_claims.notes

The key is loaded from ENCRYPTION_KEY env var (64 hex chars = 32 bytes = 256-bit).
Nonce is randomly generated per encryption call (12 bytes = 96-bit, prepended to ciphertext).

Usage:
    from encryption import encryptor
    encrypted = encryptor.encrypt("John Doe")
    plain     = encryptor.decrypt(encrypted)

Security notes:
  - AES-GCM provides both confidentiality and integrity (authenticated encryption).
  - Nonce uniqueness is critical — os.urandom(12) ensures this.
  - The key must NEVER be stored in source code or version control.
  - For key rotation: re-encrypt all rows with the new key.
"""

import base64
import hashlib
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import settings


class FieldEncryptor:
    """AES-256-GCM field-level encryptor for PHI."""

    NONCE_SIZE = 12  # 96 bits — standard for GCM

    def __init__(self, key_hex: str):
        if len(key_hex) != 64:
            raise ValueError(
                "ENCRYPTION_KEY must be exactly 64 hex characters (32 bytes / 256 bits). "
                "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        self._key = bytes.fromhex(key_hex)
        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string field.
        Returns base64(nonce || ciphertext_with_tag).
        """
        if not plaintext:
            return plaintext
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, ciphertext_b64: str) -> str:
        """
        Decrypt a base64-encoded AES-GCM ciphertext.
        Raises ValueError if the ciphertext is tampered (GCM authentication fails).
        """
        if not ciphertext_b64:
            return ciphertext_b64
        try:
            raw = base64.b64decode(ciphertext_b64)
            nonce = raw[: self.NONCE_SIZE]
            ct = raw[self.NONCE_SIZE :]
            plaintext = self._aesgcm.decrypt(nonce, ct, None)
            return plaintext.decode("utf-8")
        except Exception as exc:
            raise ValueError(f"Decryption failed — data may be tampered: {exc}") from exc

    def encrypt_optional(self, value: Optional[str]) -> Optional[str]:
        """Encrypt only if value is not None."""
        return self.encrypt(value) if value is not None else None

    def decrypt_optional(self, value: Optional[str]) -> Optional[str]:
        """Decrypt only if value is not None."""
        return self.decrypt(value) if value is not None else None


class PHIMasker:
    """
    Masks PHI for non-privileged roles.
    CEO sees full data; dept_head / finance sees masked data.
    """

    @staticmethod
    def mask_name(name: str) -> str:
        """'Ramesh Iyer' → 'R****** I***'"""
        if not name:
            return name
        parts = name.split()
        return " ".join(p[0] + "*" * (len(p) - 1) if len(p) > 1 else p for p in parts)

    @staticmethod
    def mask_phone(phone: str) -> str:
        """'+91-9876543210' → '+91-XXXXXX3210'"""
        if not phone or len(phone) < 4:
            return phone
        return phone[:-4].replace(phone[2:-4], "X" * len(phone[2:-4])) + phone[-4:]

    @staticmethod
    def mask_aadhaar(aadhaar: str) -> str:
        """'1234-5678-9012' → 'XXXX-XXXX-9012'"""
        if not aadhaar:
            return aadhaar
        return "XXXX-XXXX-" + aadhaar[-4:]


def hash_aadhaar(aadhaar: str) -> str:
    """
    One-way SHA-256 hash of Aadhaar number for deduplication
    without storing the actual number in plaintext.
    The actual Aadhaar is stored AES-encrypted separately.
    """
    return hashlib.sha256(aadhaar.encode("utf-8")).hexdigest()


# ── Module-level singleton ────────────────────────────────────────────────────
encryptor = FieldEncryptor(settings.ENCRYPTION_KEY)
masker = PHIMasker()
