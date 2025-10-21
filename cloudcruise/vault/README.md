# Vault Client (Python)

The Vault client provides secure credential storage with client-side
AES-256-GCM encryption. Create, fetch, update, and delete credentials while the
SDK transparently encrypts/decrypts sensitive fields.

---

## Usage

### Basic Operations

```python
from cloudcruise import CloudCruise

client = CloudCruise(
    api_key="your-api-key",
    encryption_key="your-hex-encryption-key",  # required for vault ops
)
# Alternatively, export CLOUDCRUISE_API_KEY and CLOUDCRUISE_ENCRYPTION_KEY and
# create the client with `client = CloudCruise()`.

# Create a vault entry
# Sensitive values (user_name, password, tfa_secret, etc.) are encrypted
entry = client.vault.create(
    domain="https://example.com",
    permissioned_user_id="user123",
    credentials={
        "user_name": "john_doe",
        "password": "secure_password",
        "tfa_secret": "ABCDEF123456",
        "user_alias": "John's Main Account",
    },
)

# Get all vault entries (decrypted by default)
all_entries = client.vault.get()

# Retrieve filtered vault entries (permissioned_user_id + domain together)
filtered_entries = client.vault.get(
    permissioned_user_id="user123",
    domain="https://example.com",
)

# Fetch entries without decrypting sensitive fields on the client
encrypted_entries = client.vault.get(
    permissioned_user_id="user123",
    domain="https://example.com",
    decrypt_credentials=False,
)

# Update a vault entry
updated_entry = client.vault.update(
    permissioned_user_id=entry.permissioned_user_id,
    user_name=entry.user_name,      # required, re-encrypted automatically
    password="new_secure_password", # required, re-encrypted automatically
    domain=entry.domain,            # required
    user_alias="Updated Account Name",
    allow_multiple_sessions=True,
)

# Delete a vault entry
client.vault.delete(
    permissioned_user_id="user123",
    domain="https://example.com",
)
```

### Advanced Configuration

```python
entry = client.vault.create(
    domain="https://app.example.com",
    permissioned_user_id="user123",
    credentials={
        "user_name": "john_doe",
        "password": "secure_password",
        "tfa_secret": "JBSWY3DPEHPK3PXP",
        "user_alias": "Production Account",
        "allow_multiple_sessions": False,
        # Browser state persistence
        "persist_cookies": True,
        "persist_local_storage": True,
        "persist_session_storage": True,
        # Basic proxy configuration
        "proxy": {
            "enable": True,
            "target_ip": "192.168.1.100",
        },
    },
)
```

### Low-level Encryption Helpers

If you need direct access to the encryption primitives, see
`cloudcruise/vault/utils.py` for AES-256-GCM helpers and KDF utilities.

---

## Official API Documentation

For the authoritative list of parameters and behaviors, refer to the CloudCruise
API docs:

- [Create Vault Entry](https://docs.cloudcruise.com/vault-api/create-vault-entry.md)
- [Get Vault Entries](https://docs.cloudcruise.com/vault-api/get-vault-entries.md)
- [Update Vault Entry](https://docs.cloudcruise.com/vault-api/update-vault-entry.md)
- [Delete Vault Entry](https://docs.cloudcruise.com/vault-api/delete-vault-entry.md)

SDK capabilities may evolve with the API; consult the docs for the latest
support matrix.
