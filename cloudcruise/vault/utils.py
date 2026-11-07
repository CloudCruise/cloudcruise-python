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


def _required(item: Any, key: str, path: str) -> Any:
    if not isinstance(item, dict) or item.get(key) is None:
        raise ValueError(f"{path}.{key} is required")
    return item[key]


def encrypt_sensitive_fields(entry: Dict[str, Any], encryption_key: str) -> Dict[str, Any]:
    encrypted = dict(entry)
    if entry.get("user_name") is not None:
        encrypted["user_name"] = encrypt_data(entry["user_name"], encryption_key)
    if entry.get("password") is not None:
        encrypted["password"] = encrypt_data(entry["password"], encryption_key)
    if entry.get("tfa_secret") is not None:
        encrypted["tfa_secret"] = encrypt_data(entry["tfa_secret"], encryption_key)
    if isinstance(entry.get("additional_fields"), list):
        encrypted["additional_fields"] = [
            {
                "name": _required(field, "name", f"additional_fields[{i}]"),
                "type": _required(field, "type", f"additional_fields[{i}]"),
                "value": encrypt_data(
                    _required(field, "value", f"additional_fields[{i}]"), encryption_key
                ),
            }
            for i, field in enumerate(entry["additional_fields"])
        ]
    if isinstance(entry.get("security_questions"), list):
        encrypted["security_questions"] = [
            {
                key: encrypt_data(
                    _required(item, key, f"security_questions[{i}]"), encryption_key
                )
                for key in ("question", "answer")
            }
            for i, item in enumerate(entry["security_questions"])
        ]
    # proxy_value is meaningless to the backend without proxy_setting, which is
    # also the discriminator that decides whether to encrypt. Fail closed so a
    # custom proxy URL (often with embedded credentials) is never sent in
    # plaintext because the caller omitted the mode on a partial update.
    if entry.get("proxy_value") is not None and not entry.get("proxy_setting"):
        raise ValueError(
            "proxy_value requires proxy_setting. Pass proxy_setting='custom' for a "
            "bring-your-own proxy URL (so it is encrypted before sending), or "
            "'static'/'country' for a managed proxy."
        )
    if entry.get("proxy_setting") == "custom" and entry.get("proxy_value") is not None:
        encrypted["proxy_value"] = encrypt_data(entry["proxy_value"], encryption_key)
    return encrypted


def _decrypt_or_keep(value: Any, encryption_key: str) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return decrypt_data(value, encryption_key)
    except Exception:
        return value


def decrypt_sensitive_fields(entry: Dict[str, Any], encryption_key: str) -> Dict[str, Any]:
    decrypted = dict(entry)
    for key in ("user_name", "password", "tfa_secret"):
        if key in entry:
            decrypted[key] = _decrypt_or_keep(entry[key], encryption_key)
    if isinstance(entry.get("additional_fields"), list):
        decrypted["additional_fields"] = [
            {**field, "value": _decrypt_or_keep(field.get("value"), encryption_key)}
            if isinstance(field, dict)
            else field
            for field in entry["additional_fields"]
        ]
    if isinstance(entry.get("security_questions"), list):
        decrypted["security_questions"] = [
            {
                **item,
                "question": _decrypt_or_keep(item.get("question"), encryption_key),
                "answer": _decrypt_or_keep(item.get("answer"), encryption_key),
            }
            if isinstance(item, dict)
            else item
            for item in entry["security_questions"]
        ]
    if entry.get("proxy_setting") == "custom" and "proxy_value" in entry:
        decrypted["proxy_value"] = _decrypt_or_keep(entry["proxy_value"], encryption_key)
    return decrypted
