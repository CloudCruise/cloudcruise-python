import unittest

from cloudcruise import (
    GetVaultEntriesFilters,
    VaultAdditionalField,
    VaultAdditionalFieldWarning,
    VaultEntryInput,
    VaultSecurityQuestion,
    VaultSecurityQuestionWarning,
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


if __name__ == "__main__":
    unittest.main()
