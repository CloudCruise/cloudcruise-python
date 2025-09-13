import unittest

from cloudcruise.vault.utils import encrypt_data, decrypt_data

class TestVaultCrypto(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        key_hex = "a" * 64  # 32 bytes hex
        payload = {"user": "alice", "pwd": "secret", "n": 123}

        enc = encrypt_data(payload, key_hex)
        self.assertIsInstance(enc, str)
        self.assertGreater(len(enc), 56)

        dec = decrypt_data(enc, key_hex)
        self.assertEqual(dec, payload)

if __name__ == "__main__":
    unittest.main()
