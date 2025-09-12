from __future__ import annotations

import json
from typing import Any, Dict
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets


def _hex_to_bytes(h: str) -> bytes:
    return bytes.fromhex(h)


def _bytes_to_hex(b: bytes) -> str:
    return b.hex()


def encrypt_data(data: Any, key_hex: str) -> str:
    try:
        key = _hex_to_bytes(key_hex)
        if len(key) != 32:
            raise ValueError("Invalid key length; expected 32-byte (256-bit) key in hex")
        iv = secrets.token_bytes(12)
        aesgcm = AESGCM(key)
        plaintext = json.dumps(data).encode("utf-8")
        ct_tag = aesgcm.encrypt(iv, plaintext, None)  # ciphertext + tag
        # Split tag (last 16 bytes)
        ciphertext, tag = ct_tag[:-16], ct_tag[-16:]
        return _bytes_to_hex(iv) + _bytes_to_hex(ciphertext) + _bytes_to_hex(tag)
    except Exception as e:
        raise RuntimeError(f"Encryption failed: {str(e)}")


def decrypt_data(encrypted_hex: str, key_hex: str) -> Any:
    try:
        if not isinstance(encrypted_hex, str) or len(encrypted_hex) < 56:
            raise ValueError("Invalid encrypted payload")
        key = _hex_to_bytes(key_hex)
        if len(key) != 32:
            raise ValueError("Invalid key length; expected 32-byte (256-bit) key in hex")
        iv = _hex_to_bytes(encrypted_hex[:24])
        tag = _hex_to_bytes(encrypted_hex[-32:])
        ciphertext = _hex_to_bytes(encrypted_hex[24:-32])
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(iv, ciphertext + tag, None)
        return json.loads(plaintext.decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Decryption failed: {str(e)}")


def encrypt_sensitive_fields(entry: Dict[str, Any], encryption_key: str) -> Dict[str, Any]:
    encrypted = dict(entry)
    if entry.get("user_name") is not None:
        encrypted["user_name"] = encrypt_data(entry["user_name"], encryption_key)
    if entry.get("password") is not None:
        encrypted["password"] = encrypt_data(entry["password"], encryption_key)
    if entry.get("tfa_secret") is not None:
        encrypted["tfa_secret"] = encrypt_data(entry["tfa_secret"], encryption_key)
    return encrypted


def decrypt_sensitive_fields(entry: Dict[str, Any], encryption_key: str) -> Dict[str, Any]:
    decrypted = dict(entry)
    val = entry.get("user_name")
    if isinstance(val, str):
        try:
            decrypted["user_name"] = decrypt_data(val, encryption_key)
        except Exception:
            pass
    val = entry.get("password")
    if isinstance(val, str):
        try:
            decrypted["password"] = decrypt_data(val, encryption_key)
        except Exception:
            pass
    val = entry.get("tfa_secret")
    if isinstance(val, str):
        try:
            decrypted["tfa_secret"] = decrypt_data(val, encryption_key)
        except Exception:
            pass
    return decrypted
