"""
tests/test_encryption.py
Test suite for AES-256-GCM field-level encryption.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Use a test key
TEST_KEY = "a" * 64  # 64 hex chars = 32 bytes


def test_encrypt_decrypt_roundtrip():
    from encryption import FieldEncryptor
    enc = FieldEncryptor(TEST_KEY)
    plaintext = "Dr. Ramesh Iyer"
    encrypted = enc.encrypt(plaintext)
    assert encrypted != plaintext
    assert enc.decrypt(encrypted) == plaintext


def test_encrypt_produces_different_ciphertexts():
    """Each encryption should produce a unique ciphertext (nonce randomness)."""
    from encryption import FieldEncryptor
    enc = FieldEncryptor(TEST_KEY)
    ct1 = enc.encrypt("John Doe")
    ct2 = enc.encrypt("John Doe")
    assert ct1 != ct2  # Different nonces


def test_decrypt_tampered_raises():
    from encryption import FieldEncryptor
    enc = FieldEncryptor(TEST_KEY)
    encrypted = enc.encrypt("Test Patient")
    tampered = encrypted[:-5] + "XXXXX"
    with pytest.raises(ValueError, match="Decryption failed"):
        enc.decrypt(tampered)


def test_encrypt_empty_string():
    from encryption import FieldEncryptor
    enc = FieldEncryptor(TEST_KEY)
    assert enc.encrypt("") == ""


def test_encrypt_optional_none():
    from encryption import FieldEncryptor
    enc = FieldEncryptor(TEST_KEY)
    assert enc.encrypt_optional(None) is None
    assert enc.decrypt_optional(None) is None


def test_invalid_key_length():
    from encryption import FieldEncryptor
    with pytest.raises(ValueError, match="64 hex characters"):
        FieldEncryptor("tooshort")


def test_phi_masker_name():
    from encryption import PHIMasker
    m = PHIMasker()
    assert m.mask_name("Ramesh Iyer") == "R****** I***"
    assert m.mask_name("") == ""


def test_phi_masker_aadhaar():
    from encryption import PHIMasker
    m = PHIMasker()
    assert m.mask_aadhaar("1234-5678-9012").endswith("9012")
    assert "XXXX" in m.mask_aadhaar("1234-5678-9012")


def test_aadhaar_hash_deterministic():
    from encryption import hash_aadhaar
    h1 = hash_aadhaar("123456789012")
    h2 = hash_aadhaar("123456789012")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_large_phi_encrypt_decrypt():
    from encryption import FieldEncryptor
    enc = FieldEncryptor(TEST_KEY)
    long_text = "Patient with complex multi-line diagnosis: " + "A" * 1000
    assert enc.decrypt(enc.encrypt(long_text)) == long_text


def test_unicode_phi():
    from encryption import FieldEncryptor
    enc = FieldEncryptor(TEST_KEY)
    tamil_name = "ராமேஷ் குமார்"  # Tamil script
    assert enc.decrypt(enc.encrypt(tamil_name)) == tamil_name
