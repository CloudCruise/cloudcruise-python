import unittest
import warnings
from types import SimpleNamespace
from unittest import mock

import cloudcruise
import cloudcruise._default
import cloudcruise.vault

from cloudcruise import (
    GetVaultEntriesFilters,
    VaultAdditionalField,
    VaultAdditionalFieldWarning,
    VaultEntryInput,
    VaultSecurityQuestion,
    VaultEntry,
    VaultSecurityQuestionWarning,
    SiteSettings,
    SiteSettingsEntry,
    SiteSettingsEntryOverrides,
    SiteSettingsValues,
)
from cloudcruise.vault.client import VaultClient
from cloudcruise.vault.utils import decrypt_data, encrypt_sensitive_fields

KEY = "0123456789abcdef" * 4

ADDITIONAL_FIELDS = [
    VaultAdditionalField(name="Note", type="Text", value="front desk"),
    VaultAdditionalField(name="Recovery email", type="Email", value="backup@example.com"),
    VaultAdditionalField(name="Portal", type="Url", value="https://portal.example.com"),
    VaultAdditionalField(name="Phone", type="Phone", value="+1 555 0100"),
    VaultAdditionalField(name="Birthday", type="Date", value="1990-04-01"),
    VaultAdditionalField(name="Card expiry", type="MonthYear", value="04/2030"),
    VaultAdditionalField(
        name="Billing address",
        type="Address",
        value={
            "street": "1 Main St",
            "city": "Springfield",
            "state": "IL",
            "zip": "62701",
            "country": "US",
        },
    ),
    VaultAdditionalField(name="PIN", type="Concealed", value="4321"),
    VaultAdditionalField(
        name="Backup authenticator",
        type="Totp",
        value="JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP",
    ),
]


class EchoServer:
    """Records each request and answers with the request body, like the API
    answers a create or update with the stored entry."""

    def __init__(self, response=None):
        self.calls = []
        self.response = response

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        return body if self.response is None else self.response


class TestVaultAdditionalFields(unittest.TestCase):
    def test_create_sends_every_additional_field_value_encrypted_and_returns_it_decrypted(self):
        """The API rejects plaintext additional field values, so every value
        of every type must reach the server as ciphertext of the plain value
        (an Address as its JSON object), and the caller gets plain values back."""
        server = EchoServer()
        client = VaultClient(server, KEY)

        result = client.create(
            VaultEntryInput(
                domain="example.com",
                permissioned_user_id="user123",
                additional_fields=ADDITIONAL_FIELDS,
            )
        )

        sent = server.calls[0][2]["additional_fields"]
        self.assertEqual(len(sent), len(ADDITIONAL_FIELDS))
        for sent_field, field in zip(sent, ADDITIONAL_FIELDS):
            self.assertEqual(sent_field["name"], field.name)
            self.assertEqual(sent_field["type"], field.type)
            self.assertIsInstance(sent_field["value"], str)
            self.assertEqual(decrypt_data(sent_field["value"], KEY), field.value)
        self.assertEqual(result.additional_fields, ADDITIONAL_FIELDS)


    def test_create_sends_only_name_type_and_value_of_an_additional_field(self):
        """The API rejects unknown keys on an additional field with 400, so
        extra keys a caller carries on a dict (e.g. a UI id) are not sent."""
        server = EchoServer()
        VaultClient(server, KEY).create(
            VaultEntryInput(
                domain="example.com",
                permissioned_user_id="user123",
                additional_fields=[{"id": 7, "name": "Note", "type": "Text", "value": "x"}],
            )
        )
        self.assertEqual(
            set(server.calls[0][2]["additional_fields"][0]), {"name", "type", "value"}
        )

    def test_create_names_the_additional_field_that_lacks_a_value(self):
        """An item without a value cannot be encrypted; the error says which
        item and key are missing instead of a bare KeyError."""
        client = VaultClient(EchoServer(), KEY)
        with self.assertRaisesRegex(ValueError, r"additional_fields\[0\]\.value is required"):
            client.create(
                VaultEntryInput(
                    domain="example.com",
                    permissioned_user_id="user123",
                    additional_fields=[{"name": "Note", "type": "Text"}],
                )
            )


class TestVaultSecurityQuestions(unittest.TestCase):
    def test_create_sends_questions_and_answers_encrypted_in_order_and_returns_them_decrypted(self):
        """The API stores both the question and the answer encrypted and
        rejects plaintext, so the SDK encrypts both and keeps the caller's order."""
        server = EchoServer()
        client = VaultClient(server, KEY)
        questions = [
            VaultSecurityQuestion(question="What is your mother's maiden name?", answer="Smith"),
            VaultSecurityQuestion(question="What was your first pet called?", answer="Rex"),
        ]

        result = client.create(
            VaultEntryInput(
                domain="example.com",
                permissioned_user_id="user123",
                security_questions=questions,
            )
        )

        sent = server.calls[0][2]["security_questions"]
        self.assertEqual(len(sent), 2)
        for sent_item, item in zip(sent, questions):
            self.assertNotEqual(sent_item["question"], item.question)
            self.assertNotEqual(sent_item["answer"], item.answer)
            self.assertEqual(decrypt_data(sent_item["question"], KEY), item.question)
            self.assertEqual(decrypt_data(sent_item["answer"], KEY), item.answer)
        self.assertEqual(result.security_questions, questions)

    def test_create_names_the_security_question_that_lacks_an_answer(self):
        """A question without an answer cannot be encrypted; the error says
        which item and key are missing instead of a bare KeyError."""
        client = VaultClient(EchoServer(), KEY)
        with self.assertRaisesRegex(ValueError, r"security_questions\[1\]\.answer is required"):
            client.create(
                VaultEntryInput(
                    domain="example.com",
                    permissioned_user_id="user123",
                    security_questions=[
                        {"question": "Pet?", "answer": "Rex"},
                        {"question": "Colour?"},
                    ],
                )
            )


class TestVaultPositionalArguments(unittest.TestCase):
    def test_existing_positional_arguments_keep_their_fields(self):
        """The new fields come after every existing field, so constructors
        called positionally before they existed still fill the same fields."""
        entry_input = VaultEntryInput(
            "example.com", "u1", None, "alice", "pw", None, None, None, "seed", "EMAIL", "agent"
        )
        self.assertEqual(entry_input.tfa_method, "EMAIL")
        self.assertEqual(entry_input.user_agent, "agent")
        self.assertIsNone(entry_input.tfa_methods)

        entry = VaultEntry(
            "example.com", "u1", "id1", None, None, None, None, None, None,
            None, None, None, "seed", "EMAIL", "tfa@example.com",
        )
        self.assertEqual(entry.tfa_method, "EMAIL")
        self.assertEqual(entry.tfa_email, "tfa@example.com")
        self.assertIsNone(entry.tfa_methods)


class TestVaultTfaMethodDeprecation(unittest.TestCase):
    def test_writing_tfa_method_warns_that_it_is_deprecated(self):
        """The API ignores tfa_method when tfa_methods is sent and otherwise
        replaces the whole list with it, so writing it warns callers to move
        to tfa_methods."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            VaultClient(EchoServer(), KEY).create(
                VaultEntryInput(
                    domain="example.com", permissioned_user_id="u1", tfa_method="EMAIL"
                )
            )
        self.assertTrue(
            any(issubclass(w.category, DeprecationWarning) and "tfa_methods" in str(w.message)
                for w in caught)
        )

    def test_tfa_method_warning_is_attributed_to_the_callers_file_on_every_entry_point(self):
        """Python's default filters show a DeprecationWarning only when it is
        attributed to __main__, so the warning must point at the caller's line,
        never at an SDK file, whether the caller uses a client or the
        module-level cloudcruise.vault functions."""
        client = VaultClient(EchoServer(), KEY)
        entry = VaultEntryInput(domain="example.com", permissioned_user_id="u1", tfa_method="EMAIL")
        entry_points = {
            "client.create": lambda: client.create(entry),
            "client.update": lambda: client.update(entry),
            "cloudcruise.vault.create": lambda: cloudcruise.vault.create(entry),
            "cloudcruise.vault.update": lambda: cloudcruise.vault.update(entry),
        }
        with mock.patch.object(cloudcruise._default, "_default_client", SimpleNamespace(vault=client)):
            for name, call in entry_points.items():
                with self.subTest(name), warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    call()
                    [warning] = [w for w in caught if issubclass(w.category, DeprecationWarning)]
                    self.assertEqual(warning.filename, __file__)


class TestVaultProviderBackedLists(unittest.TestCase):
    PROVIDER = {"secret_provider_id": "provider-1", "secret_ref": "op://vault/item"}

    def test_create_rejects_additional_fields_on_a_provider_backed_entry(self):
        """A provider-backed entry takes its additional fields from the bound
        item and the API rejects stored ones, so the SDK fails before sending."""
        client = VaultClient(EchoServer(), KEY)
        with self.assertRaisesRegex(ValueError, "cannot include additional_fields"):
            client.create(
                VaultEntryInput(
                    domain="example.com",
                    permissioned_user_id="user123",
                    additional_fields=[ADDITIONAL_FIELDS[7]],
                    **self.PROVIDER,
                )
            )

    def test_create_rejects_security_questions_on_a_provider_backed_entry(self):
        """Security questions of a provider-backed entry come from the bound
        item, so the SDK rejects stored ones like the API does."""
        client = VaultClient(EchoServer(), KEY)
        with self.assertRaisesRegex(ValueError, "cannot include security_questions"):
            client.create(
                VaultEntryInput(
                    domain="example.com",
                    permissioned_user_id="user123",
                    security_questions=[VaultSecurityQuestion(question="Q?", answer="A")],
                    **self.PROVIDER,
                )
            )

    def test_create_accepts_empty_lists_on_a_provider_backed_entry(self):
        """Empty lists are what the API itself expects on a provider-backed
        entry, so they pass through."""
        server = EchoServer()
        VaultClient(server, KEY).create(
            VaultEntryInput(
                domain="example.com",
                permissioned_user_id="user123",
                additional_fields=[],
                security_questions=[],
                **self.PROVIDER,
            )
        )
        body = server.calls[0][2]
        self.assertEqual(body["additional_fields"], [])
        self.assertEqual(body["security_questions"], [])


class TestVaultRead(unittest.TestCase):
    def _encrypted_entry(self):
        return encrypt_sensitive_fields(
            {
                "domain": "example.com",
                "permissioned_user_id": "user123",
                "tfa_methods": ["AUTHENTICATOR", "EMAIL"],
                "tfa_method": "AUTHENTICATOR",
                "additional_fields": [
                    {"name": f.name, "type": f.type, "value": f.value}
                    for f in ADDITIONAL_FIELDS
                ],
                "security_questions": [{"question": "Pet?", "answer": "Rex"}],
            },
            KEY,
        )

    def test_get_decrypts_lists_and_keeps_warnings_and_tfa_methods(self):
        """GET returns additional field values and security questions
        encrypted; warnings and TFA methods are plaintext and stay untouched.
        Every list item becomes its dataclass."""
        response = {
            **self._encrypted_entry(),
            "additional_field_warnings": [{"name": "Dup", "reason": "duplicate_name"}],
            "security_question_warnings": [
                {"question": "Long?", "reason": "question_too_long"}
            ],
        }
        client = VaultClient(EchoServer(response=[response]), KEY)

        [entry] = client.get()

        self.assertEqual(entry.additional_fields, ADDITIONAL_FIELDS)
        self.assertEqual(
            entry.security_questions,
            [VaultSecurityQuestion(question="Pet?", answer="Rex")],
        )
        self.assertEqual(entry.tfa_methods, ["AUTHENTICATOR", "EMAIL"])
        self.assertEqual(
            entry.additional_field_warnings,
            [VaultAdditionalFieldWarning(name="Dup", reason="duplicate_name")],
        )
        self.assertEqual(
            entry.security_question_warnings,
            [VaultSecurityQuestionWarning(question="Long?", reason="question_too_long")],
        )

    def test_get_keeps_an_entry_whose_list_item_lacks_a_key(self):
        """A list item missing a key must not fail the whole read; the key
        reads as None, like any other absent field of the entry."""
        response = {
            "domain": "example.com",
            "permissioned_user_id": "user123",
            "additional_field_warnings": [{"name": "Dup"}],
        }
        [entry] = VaultClient(EchoServer(response=[response]), KEY).get()
        self.assertEqual(
            entry.additional_field_warnings,
            [VaultAdditionalFieldWarning(name="Dup", reason=None)],
        )

    def test_get_without_decryption_returns_lists_as_ciphertext(self):
        """decryptCredentials=False promises the raw API values, so the
        encrypted lists stay ciphertext too."""
        encrypted = self._encrypted_entry()
        client = VaultClient(EchoServer(response=[encrypted]), KEY)

        [entry] = client.get(GetVaultEntriesFilters(decryptCredentials=False))

        self.assertEqual(
            [f.value for f in entry.additional_fields],
            [f["value"] for f in encrypted["additional_fields"]],
        )
        self.assertEqual(
            entry.security_questions[0].answer,
            encrypted["security_questions"][0]["answer"],
        )


class TestVaultUpdate(unittest.TestCase):
    def test_update_sends_tfa_methods_as_given_and_replacement_lists_encrypted(self):
        """PUT replaces the stored lists, so an update carries the full new
        lists: tfa_methods as plaintext enum values, additional fields and
        security questions encrypted like on create."""
        server = EchoServer()
        result = VaultClient(server, KEY).update(
            VaultEntryInput(
                domain="example.com",
                permissioned_user_id="user123",
                tfa_methods=["AUTHENTICATOR", "SMS"],
                additional_fields=[ADDITIONAL_FIELDS[6], ADDITIONAL_FIELDS[8]],
                security_questions=[VaultSecurityQuestion(question="Colour?", answer="Teal")],
            )
        )

        method, path, body = server.calls[0]
        self.assertEqual((method, path), ("PUT", "/vault"))
        self.assertEqual(body["tfa_methods"], ["AUTHENTICATOR", "SMS"])
        self.assertEqual(
            decrypt_data(body["additional_fields"][0]["value"], KEY),
            ADDITIONAL_FIELDS[6].value,
        )
        self.assertEqual(decrypt_data(body["security_questions"][0]["answer"], KEY), "Teal")
        self.assertEqual(result.additional_fields, [ADDITIONAL_FIELDS[6], ADDITIONAL_FIELDS[8]])


class TestVaultTfaCode(unittest.TestCase):
    CODE = {"type": "authenticator", "code": "123456", "expires_in_seconds": 20}

    def test_get_tfa_code_sends_method_and_field_as_query_parameters(self):
        """An entry with several TFA methods needs ``method`` (else the API
        answers 400), and ``field`` selects a Totp additional field instead of
        the built-in seed."""
        server = EchoServer(response=self.CODE)
        client = VaultClient(server, KEY)

        client.get_tfa_code("user123", "example.com", method="EMAIL")
        client.get_tfa_code(
            "user123", "example.com", method="AUTHENTICATOR", field="Backup authenticator"
        )

        self.assertEqual(
            [path for _, path, _ in server.calls],
            [
                "/vault/tfa-code?permissioned_user_id=user123&domain=example.com&method=EMAIL",
                "/vault/tfa-code?permissioned_user_id=user123&domain=example.com"
                "&method=AUTHENTICATOR&field=Backup+authenticator",
            ],
        )

    def test_get_tfa_code_without_options_sends_only_the_entry_identity(self):
        """Without method or field the request is unchanged, so single-method
        entries keep working."""
        server = EchoServer(response=self.CODE)

        code = VaultClient(server, KEY).get_tfa_code("user123", "example.com")

        self.assertEqual(
            server.calls[0][1],
            "/vault/tfa-code?permissioned_user_id=user123&domain=example.com",
        )
        self.assertEqual(code.code, "123456")

    def test_get_tfa_code_rejects_field_with_a_method_other_than_authenticator(self):
        """A Totp field is an authenticator seed, so the API always answers
        400 for field with another method; the SDK fails before sending."""
        server = EchoServer(response=self.CODE)
        with self.assertRaisesRegex(ValueError, "field requires method AUTHENTICATOR"):
            VaultClient(server, KEY).get_tfa_code(
                "user123", "example.com", method="EMAIL", field="Backup authenticator"
            )
        self.assertEqual(server.calls, [])

    def test_get_tfa_code_sends_an_empty_field_instead_of_dropping_it(self):
        """Dropping an empty field would silently return the built-in seed's
        code; sending it lets the API reject the unknown field."""
        server = EchoServer(response=self.CODE)
        VaultClient(server, KEY).get_tfa_code("user123", "example.com", field="")
        self.assertTrue(server.calls[0][1].endswith("&field="))


class TestVaultOptionalDomain(unittest.TestCase):
    def test_create_without_a_domain_leaves_domain_out_of_the_request(self):
        """An entry without a domain is addressed by its user ID alone, and
        the API rejects a null domain, so the key must be absent."""
        server = EchoServer()
        result = VaultClient(server, KEY).create(
            VaultEntryInput(permissioned_user_id="user123", user_name="alice")
        )
        self.assertNotIn("domain", server.calls[0][2])
        self.assertIsNone(result.domain)

    def test_input_keeps_domain_then_user_id_positional_order(self):
        """Existing callers pass VaultEntryInput("example.com", "user123")."""
        entry = VaultEntryInput("example.com", "user123")
        self.assertEqual((entry.domain, entry.permissioned_user_id), ("example.com", "user123"))

    def test_input_still_requires_the_user_id(self):
        """The user ID is the only required identifier now; omitting it must
        fail at construction like before, not later at the API."""
        with self.assertRaises(TypeError):
            VaultEntryInput(domain="example.com")

    def test_update_without_a_domain_leaves_domain_out_of_the_request(self):
        server = EchoServer()
        VaultClient(server, KEY).update(
            VaultEntryInput(permissioned_user_id="user123", user_alias="Main")
        )
        self.assertEqual(server.calls[0][0], "PUT")
        self.assertNotIn("domain", server.calls[0][2])

    def test_get_with_a_user_id_alone_sends_only_the_user_id(self):
        server = EchoServer(response={"permissioned_user_id": "user123", "domain": None})
        entries = VaultClient(server, KEY).get(
            GetVaultEntriesFilters(permissioned_user_id="user123")
        )
        self.assertEqual(server.calls[0][1], "/vault?permissioned_user_id=user123")
        self.assertIsNone(entries[0].domain)

    def test_get_with_a_domain_but_no_user_id_raises_before_sending(self):
        """The API only accepts domain together with permissioned_user_id."""
        server = EchoServer(response=[])
        with self.assertRaisesRegex(ValueError, "domain requires permissioned_user_id"):
            VaultClient(server, KEY).get(GetVaultEntriesFilters(domain="example.com"))
        self.assertEqual(server.calls, [])

    def test_delete_with_a_user_id_alone_sends_only_the_user_id(self):
        server = EchoServer()
        VaultClient(server, KEY).delete({"permissioned_user_id": "user123"})
        self.assertEqual(server.calls[0], ("DELETE", "/vault", {"permissioned_user_id": "user123"}))

    def test_delete_still_sends_the_domain_when_given(self):
        server = EchoServer()
        params = {"permissioned_user_id": "user123", "domain": "example.com"}
        VaultClient(server, KEY).delete(params)
        self.assertEqual(server.calls[0][2], params)

    def test_delete_requires_a_user_id(self):
        server = EchoServer()
        with self.assertRaisesRegex(ValueError, "permissioned_user_id is required"):
            VaultClient(server, KEY).delete({"domain": "example.com"})
        self.assertEqual(server.calls, [])

    def test_get_tfa_code_with_a_user_id_alone_sends_only_the_user_id(self):
        server = EchoServer(response={"type": "authenticator", "code": "123456"})
        VaultClient(server, KEY).get_tfa_code("user123")
        self.assertEqual(server.calls[0][1], "/vault/tfa-code?permissioned_user_id=user123")

    def test_get_tfa_code_with_a_method_and_no_domain_keeps_the_method(self):
        server = EchoServer(response={"type": "email", "code": "884512"})
        VaultClient(server, KEY).get_tfa_code("user123", method="EMAIL")
        self.assertEqual(
            server.calls[0][1], "/vault/tfa-code?permissioned_user_id=user123&method=EMAIL"
        )


SITE_SETTINGS = {
    "id": "00000000-0000-0000-0000-000000000001",
    "domain": "example.com",
    "settings": {"max_concurrency": 3, "persist_cookies": True},
    "entry_count": 4,
    "overrides": {"max_concurrency": 1},
    "unknown_future_key": 1,
}


class TestSiteSettings(unittest.TestCase):
    def test_list_site_settings_returns_dataclasses_with_unset_values_as_none(self):
        """A domain default the API reports as null (or omits) means the
        platform default applies, and is None on the dataclass."""
        server = EchoServer(response=[SITE_SETTINGS])
        result = VaultClient(server, KEY).list_site_settings()

        self.assertEqual(server.calls[0], ("GET", "/vault/site-settings", None))
        self.assertIsInstance(result[0], SiteSettings)
        self.assertIsInstance(result[0].settings, SiteSettingsValues)
        self.assertEqual(result[0].settings.max_concurrency, 3)
        self.assertIs(result[0].settings.persist_cookies, True)
        self.assertIsNone(result[0].settings.login_workflow_id)
        self.assertEqual(result[0].entry_count, 4)
        self.assertEqual(result[0].overrides, {"max_concurrency": 1})

    def test_update_site_settings_sends_only_the_settings_that_were_given(self):
        """A setting that is not passed must stay out of the PATCH body so the
        domain keeps its value."""
        server = EchoServer(response=SITE_SETTINGS)
        result = VaultClient(server, KEY).update_site_settings(
            "example.com", max_concurrency=3, persist_cookies=False
        )
        self.assertEqual(
            server.calls[0],
            (
                "PATCH",
                "/vault/site-settings",
                {"domain": "example.com", "max_concurrency": 3, "persist_cookies": False},
            ),
        )
        self.assertIsInstance(result, SiteSettings)

    def test_update_site_settings_sends_none_as_an_explicit_null(self):
        """None clears a default so the platform default applies; it only
        reaches the API as a null, not as an omitted key."""
        server = EchoServer(response=SITE_SETTINGS)
        VaultClient(server, KEY).update_site_settings(
            "example.com",
            max_concurrency=None,
            expiry_time_from_last_use=None,
            login_workflow_id=None,
        )
        self.assertEqual(
            server.calls[0][2],
            {
                "domain": "example.com",
                "max_concurrency": None,
                "expiry_time_from_last_use": None,
                "login_workflow_id": None,
            },
        )

    def test_update_site_settings_requires_a_domain(self):
        server = EchoServer(response=SITE_SETTINGS)
        with self.assertRaisesRegex(ValueError, "domain is required"):
            VaultClient(server, KEY).update_site_settings("")
        self.assertEqual(server.calls, [])

    def test_list_site_settings_entries_queries_by_domain_and_parses_entries(self):
        server = EchoServer(
            response=[
                {"id": "e1", "permissioned_user_id": "u1", "overridden": ["max_concurrency"]},
                {"id": "e2", "permissioned_user_id": "u2", "overridden": []},
            ]
        )
        result = VaultClient(server, KEY).list_site_settings_entries("example.com")
        self.assertEqual(
            server.calls[0], ("GET", "/vault/site-settings/entries?domain=example.com", None)
        )
        self.assertEqual(
            result,
            [
                SiteSettingsEntry(id="e1", permissioned_user_id="u1", overridden=["max_concurrency"]),
                SiteSettingsEntry(id="e2", permissioned_user_id="u2", overridden=[]),
            ],
        )

    def test_apply_site_settings_defaults_without_entry_ids_omits_the_key(self):
        """Omitting entry_ids resets every entry on the domain."""
        server = EchoServer(response=SITE_SETTINGS)
        result = VaultClient(server, KEY).apply_site_settings_defaults("example.com")
        self.assertEqual(
            server.calls[0],
            ("PATCH", "/vault/site-settings/entries", {"domain": "example.com"}),
        )
        self.assertIsInstance(result, SiteSettings)

    def test_apply_site_settings_defaults_sends_the_given_entry_ids(self):
        server = EchoServer(response=SITE_SETTINGS)
        VaultClient(server, KEY).apply_site_settings_defaults("example.com", ["e1", "e2"])
        self.assertEqual(server.calls[0][2], {"domain": "example.com", "entry_ids": ["e1", "e2"]})

    def test_apply_site_settings_defaults_rejects_an_empty_entry_id_list(self):
        """The API requires at least one id when entry_ids is present; an empty
        list must not silently mean "every entry" either."""
        server = EchoServer(response=SITE_SETTINGS)
        with self.assertRaisesRegex(ValueError, "entry_ids must not be empty"):
            VaultClient(server, KEY).apply_site_settings_defaults("example.com", [])
        self.assertEqual(server.calls, [])

    def test_get_site_settings_overrides_queries_by_user_id_and_optional_domain(self):
        server = EchoServer(
            response={"id": "e1", "domain": None, "overridden": ["max_concurrency"]}
        )
        client = VaultClient(server, KEY)
        result = client.get_site_settings_overrides("user123")
        client.get_site_settings_overrides("user123", "example.com")

        self.assertEqual(
            server.calls[0][1], "/vault/site-settings/overrides?permissioned_user_id=user123"
        )
        self.assertEqual(
            server.calls[1][1],
            "/vault/site-settings/overrides?permissioned_user_id=user123&domain=example.com",
        )
        self.assertEqual(
            result,
            SiteSettingsEntryOverrides(id="e1", domain=None, overridden=["max_concurrency"]),
        )

    def test_reset_site_settings_overrides_sends_user_id_keys_and_optional_domain(self):
        server = EchoServer(response={"id": "e1", "domain": "example.com", "overridden": []})
        client = VaultClient(server, KEY)
        client.reset_site_settings_overrides("user123", ["max_concurrency"])
        client.reset_site_settings_overrides(
            "user123", ["persist_cookies", "login_workflow_id"], domain="example.com"
        )
        self.assertEqual(
            server.calls[0],
            (
                "PATCH",
                "/vault/site-settings/overrides",
                {"permissioned_user_id": "user123", "keys": ["max_concurrency"]},
            ),
        )
        self.assertEqual(
            server.calls[1][2],
            {
                "permissioned_user_id": "user123",
                "keys": ["persist_cookies", "login_workflow_id"],
                "domain": "example.com",
            },
        )

    def test_reset_site_settings_overrides_requires_at_least_one_key(self):
        server = EchoServer()
        with self.assertRaisesRegex(ValueError, "keys must name at least one"):
            VaultClient(server, KEY).reset_site_settings_overrides("user123", [])
        self.assertEqual(server.calls, [])

    def test_module_level_helpers_delegate_to_the_default_client(self):
        fake = SimpleNamespace(vault=mock.Mock())
        with mock.patch.object(cloudcruise._default, "get_client", return_value=fake):
            cloudcruise.vault.update_site_settings("example.com", max_concurrency=None)
            cloudcruise.vault.apply_site_settings_defaults("example.com", ["e1"])
        update_kwargs = fake.vault.update_site_settings.call_args
        self.assertEqual(update_kwargs.args, ("example.com",))
        self.assertIsNone(update_kwargs.kwargs["max_concurrency"])
        self.assertIs(
            update_kwargs.kwargs["persist_cookies"], cloudcruise.vault.UNSET
        )
        fake.vault.apply_site_settings_defaults.assert_called_once_with("example.com", ["e1"])


if __name__ == "__main__":
    unittest.main()
