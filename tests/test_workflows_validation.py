import unittest

from cloudcruise.workflows.client import WorkflowsClient
from cloudcruise.workflows.types import WorkflowMetadata, WorkflowInputSchema, InputValidationError

class _FakeClient(WorkflowsClient):
    def __init__(self, schema=None):
        super().__init__(lambda *args, **kwargs: None)
        if schema is None:
            self._meta = WorkflowMetadata(
                input_schema=WorkflowInputSchema(
                    type="object",
                    properties={
                        "url": {"type": "string"},
                        "count": {"type": ["integer", "null"]},
                    },
                    required=["url"],
                    additionalProperties=False,
                )
            )
        else:
            self._meta = {"input_schema": schema}

    def get_workflow_metadata(self, workflow_id: str):
        return self._meta

class TestWorkflowValidation(unittest.TestCase):
    def test_validate_success(self):
        c = _FakeClient()
        c.validate_workflow_input("wf-1", {"url": "https://example.com", "count": 3})

    def test_validate_missing_required(self):
        c = _FakeClient()
        with self.assertRaises(InputValidationError):
            c.validate_workflow_input("wf-1", {"count": 3})

    def test_validate_unknown_key(self):
        c = _FakeClient()
        with self.assertRaises(InputValidationError) as caught:
            c.validate_workflow_input("wf-1", {"url": "x", "extra": 1})
        self.assertEqual(caught.exception.unknownKeys, ["extra"])

    def test_validate_nested_pattern_and_additional_properties(self):
        c = _FakeClient({
            "type": "object",
            "properties": {
                "profile": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "pattern": "^[A-Z]{3}$"},
                    },
                    "required": ["code"],
                    "additionalProperties": False,
                },
            },
        })

        with self.assertRaises(InputValidationError) as caught:
            c.validate_workflow_input(
                "wf-1",
                {"profile": {"code": "abc", "extra": True}},
            )

        self.assertEqual(caught.exception.unknownKeys, ["/profile/extra"])
        self.assertIn(
            "pattern",
            [error.keyword for error in caught.exception.schemaErrors],
        )

    def test_validate_arrays_items_and_limits(self):
        c = _FakeClient({
            "type": "object",
            "properties": {
                "scores": {
                    "type": "array",
                    "minItems": 2,
                    "items": {"type": "integer", "minimum": 0},
                },
            },
        })

        with self.assertRaises(InputValidationError) as caught:
            c.validate_workflow_input("wf-1", {"scores": [-1]})

        keywords = {error.keyword for error in caught.exception.schemaErrors}
        self.assertEqual(keywords, {"minimum", "minItems"})

    def test_validate_enum_const_and_local_ref(self):
        c = _FakeClient({
            "type": "object",
            "definitions": {
                "status": {"type": "string", "enum": ["ready", "running"]},
            },
            "properties": {
                "status": {"$ref": "#/definitions/status"},
                "version": {"const": 2},
            },
        })

        c.validate_workflow_input(
            "wf-1",
            {"status": "ready", "version": 2},
        )
        with self.assertRaises(InputValidationError) as caught:
            c.validate_workflow_input(
                "wf-1",
                {"status": "done", "version": 1},
            )

        self.assertEqual(
            {error.keyword for error in caught.exception.schemaErrors},
            {"const", "enum"},
        )

    def test_validate_combinators(self):
        cases = [
            (
                {"allOf": [{"type": "integer"}, {"type": "number", "minimum": 5}]},
                3,
                "minimum",
            ),
            (
                {"anyOf": [{"type": "string"}, {"type": "integer", "minimum": 5}]},
                False,
                "anyOf",
            ),
            ({"oneOf": [{"type": "integer"}, {"type": "number"}]}, 3, "oneOf"),
            ({"not": {"const": "blocked"}}, "blocked", "not"),
        ]
        for value_schema, value, expected_keyword in cases:
            with self.subTest(keyword=expected_keyword):
                c = _FakeClient({
                    "type": "object",
                    "properties": {"value": value_schema},
                })
                with self.assertRaises(InputValidationError) as caught:
                    c.validate_workflow_input("wf-1", {"value": value})
                self.assertIn(
                    expected_keyword,
                    [error.keyword for error in caught.exception.schemaErrors],
                )

    def test_format_is_not_enforced(self):
        c = _FakeClient({
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email"}},
        })
        c.validate_workflow_input("wf-1", {"email": "not-an-email"})

    def test_invalid_schema_fails_closed(self):
        c = _FakeClient({"type": "not-a-json-schema-type"})
        with self.assertRaises(InputValidationError) as caught:
            c.validate_workflow_input("wf-1", {})
        self.assertEqual(caught.exception.schemaErrors[0].keyword, "schema")

    def test_external_ref_is_blocked(self):
        c = _FakeClient({
            "type": "object",
            "properties": {
                "value": {"$ref": "https://example.com/value.schema.json"},
            },
        })
        with self.assertRaises(InputValidationError) as caught:
            c.validate_workflow_input("wf-1", {"value": 1})
        self.assertEqual(caught.exception.schemaErrors[0].keyword, "$ref")

if __name__ == "__main__":
    unittest.main()
