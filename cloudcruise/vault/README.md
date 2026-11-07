# Vault Client (Python)

The Vault client provides secure credential storage with client-side
AES-256-GCM encryption. Create, fetch, update, and delete credentials while the
SDK transparently encrypts/decrypts sensitive fields.

---

## Usage

### Basic Operations

```python
from cloudcruise import (
    CloudCruise,
    CloudCruiseParams,
    VaultEntryInput,
    GetVaultEntriesFilters,
    ProxyConfig,
)

client = CloudCruise(
    CloudCruiseParams(
        api_key="your-api-key",
        encryption_key="your-hex-encryption-key",  # required for vault ops
    )
)
# Alternatively, export CLOUDCRUISE_API_KEY and CLOUDCRUISE_ENCRYPTION_KEY and
# create the client with `client = CloudCruise()`.

# Create a vault entry
# Sensitive values (user_name, password, tfa_secret, additional field values,
# security questions and answers) are encrypted before transport.
entry = client.vault.create(
    VaultEntryInput(
        domain="https://example.com",
        permissioned_user_id="user123",
        user_name="john_doe",
        password="secure_password",
        tfa_secret="ABCDEF123456",
        user_alias="John's Main Account",
    )
)

# Get all vault entries (decrypted by default)
all_entries = client.vault.get()

# Retrieve filtered vault entries (permissioned_user_id + domain together)
filtered_entries = client.vault.get(
    GetVaultEntriesFilters(
        permissioned_user_id="user123",
        domain="https://example.com",
    )
)

# Fetch entries without decrypting sensitive fields on the client
encrypted_entries = client.vault.get(
    GetVaultEntriesFilters(
        permissioned_user_id="user123",
        domain="https://example.com",
        decryptCredentials=False,
    )
)

# Update a vault entry. ``domain`` and ``permissioned_user_id`` identify it.
updated_entry = client.vault.update(
    VaultEntryInput(
        domain=entry.domain,
        permissioned_user_id=entry.permissioned_user_id,
        user_name=entry.user_name,
        password="new_secure_password",
        user_alias="Updated Account Name",
        allow_multiple_sessions=True,
    )
)

# Delete a vault entry
client.vault.delete(
    {
        "permissioned_user_id": "user123",
        "domain": "https://example.com",
    }
)

# Get the current 2FA code for an entry with one 2FA method
tfa = client.vault.get_tfa_code("user123", "https://example.com")
# authenticator -> VaultTfaCode(type="authenticator", code="123456", expires_in_seconds=23)
# email         -> VaultTfaCode(type="email", code="884512", received_at="...")
# (SMS and magic-link codes are not supported.)

# Entry with several 2FA methods: pick one
client.vault.get_tfa_code("user123", "https://example.com", method="EMAIL")

# Code of a Totp additional field instead of the built-in seed (implies AUTHENTICATOR)
client.vault.get_tfa_code("user123", "https://example.com", field="Backup authenticator")
```

### Additional Fields, 2FA Methods and Security Questions

Every additional field `value` and every security question and answer is
encrypted client-side, like `password`. Both lists replace the stored lists on
`create` and `update`.

```python
from cloudcruise import VaultAdditionalField, VaultSecurityQuestion

client.vault.create(
    VaultEntryInput(
        domain="https://example.com",
        permissioned_user_id="user123",
        user_name="john_doe",
        password="secure_password",
        tfa_secret="JBSWY3DPEHPK3PXP",
        tfa_methods=["AUTHENTICATOR", "EMAIL"],
        additional_fields=[
            VaultAdditionalField(name="Member ID", type="Text", value="A-1029"),
            VaultAdditionalField(
                name="Backup authenticator",
                type="Totp",
                value="JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP",
            ),
            VaultAdditionalField(
                name="Billing address",
                type="Address",
                value={"street": "1 Main St", "city": "Springfield", "state": "IL", "zip": "62701", "country": "US"},
            ),
        ],
        security_questions=[
            VaultSecurityQuestion(question="What was your first pet called?", answer="Rex"),
        ],
    )
)
```

Field types: `Text`, `Email`, `Url`, `Phone`, `Date`, `MonthYear`, `Address`,
`Concealed`, `Totp`. `tfa_method` is deprecated; it reads as the first of
`tfa_methods`. Writing it emits a `DeprecationWarning`; the API ignores it when
`tfa_methods` is set and otherwise replaces the stored methods with it.

Entries bound to a secret provider take additional fields and security
questions from the bound item. `get()` with both `domain` and
`permissioned_user_id` reports skipped ones in `additional_field_warnings` and
`security_question_warnings` when there are any.

### Provider-Backed Credentials

Use `secret_providers` to find a connected 1Password account and item ref, then
bind a vault entry to that item instead of sending `user_name` / `password`.

```python
providers = client.secret_providers.list()
items = client.secret_providers.list_items(providers[0].id)

entry = client.vault.create(
    VaultEntryInput(
        domain="https://example.com",
        permissioned_user_id="user123",
        secret_provider_id=providers[0].id,
        secret_ref=items[0].ref,
        secret_cache_ttl_seconds=300,
    )
)
```

### Advanced Configuration

```python
entry = client.vault.create(
    VaultEntryInput(
        domain="https://app.example.com",
        permissioned_user_id="user123",
        user_name="john_doe",
        password="secure_password",
        tfa_secret="JBSWY3DPEHPK3PXP",
        tfa_methods=["AUTHENTICATOR"],
        user_alias="Production Account",
        allow_multiple_sessions=False,
        # Browser state persistence
        persist_cookies=True,
        persist_local_storage=True,
        persist_session_storage=True,
        # Proxy configuration
        proxy=ProxyConfig(enable=True, target_ip="192.168.1.100"),
    )
)
```

### Input vs. response types

- `VaultEntryInput` — fields you can set on create/update. Omits server-managed
  and server-computed fields (`id`, `created_at`, `workspace_id`,
  `organization_id`, `site_identifier`, `tfa_email`, `tfa_phone_number`,
  `session_data_set_at`, `effective_expires_at`).
- `VaultEntry` — full shape returned by the API, including the fields above.

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
- [Get 2FA Code](https://docs.cloudcruise.com/vault-api/get-vault-tfa-code.md)

SDK capabilities may evolve with the API; consult the docs for the latest
support matrix.
