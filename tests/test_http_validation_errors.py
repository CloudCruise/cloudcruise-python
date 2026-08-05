import unittest
from unittest.mock import patch

from cloudcruise import CloudCruise, CloudCruiseParams, InputValidationError


class _ErrorResponse:
    ok = False
    status_code = 400
    reason = "Bad Request"
    text = "validation failed"
    headers = {"content-type": "application/json"}

    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


class TestHttpValidationErrors(unittest.TestCase):
    def setUp(self):
        self.client = CloudCruise(
            CloudCruiseParams(
                api_key="test-key",
                encryption_key="00" * 32,
            )
        )

    def test_backend_pattern_error_becomes_input_validation_error(self):
        response = _ErrorResponse({
            "message": "Validation failed for run_input_variables",
            "run_input_variables_errors": [
                {
                    "field": "/npi_number",
                    "message": 'must match pattern "^\\d{10}$"',
                    "keyword": "pattern",
                    "expected": {"pattern": "^\\d{10}$"},
                    "received": None,
                },
            ],
            "input_schema": {
                "type": "object",
                "properties": {
                    "npi_number": {
                        "type": "string",
                        "pattern": "^\\d{10}$",
                    },
                },
            },
        })

        with patch(
            "cloudcruise.cloudcruise.requests.request",
            return_value=response,
        ):
            with self.assertRaises(InputValidationError) as caught:
                self.client._make_request(
                    "POST",
                    "/run",
                    {"run_input_variables": {"npi_number": "abc"}},
                )

        error = caught.exception
        self.assertIn("/npi_number", str(error))
        self.assertEqual(error.schemaErrors[0].instancePath, "/npi_number")
        self.assertEqual(
            error.schemaErrors[0].schemaPath,
            "#/properties/npi_number/pattern",
        )
        self.assertEqual(error.schemaErrors[0].keyword, "pattern")

    def test_backend_errors_populate_legacy_fields(self):
        response = _ErrorResponse({
            "message": "Validation failed for run_input_variables",
            "run_input_variables_errors": [
                {
                    "field": "#/required",
                    "message": "must have required property 'name'",
                    "keyword": "required",
                    "expected": {"missingProperty": "name"},
                },
                {
                    "field": "/count",
                    "message": "must be integer",
                    "keyword": "type",
                    "expected": {"type": "integer"},
                },
                {
                    "field": "",
                    "message": "must NOT have additional properties",
                    "keyword": "additionalProperties",
                    "expected": {"additionalProperty": "extra"},
                },
            ],
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "count": {"type": "integer"},
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        })

        with patch(
            "cloudcruise.cloudcruise.requests.request",
            return_value=response,
        ):
            with self.assertRaises(InputValidationError) as caught:
                self.client._make_request(
                    "POST",
                    "/run",
                    {
                        "run_input_variables": {
                            "count": "wrong",
                            "extra": True,
                        },
                    },
                )

        error = caught.exception
        self.assertEqual(error.missingRequired, ["name"])
        self.assertEqual(error.invalidTypes[0].field, "count")
        self.assertEqual(error.invalidTypes[0].actual, "string")
        self.assertEqual(error.unknownKeys, ["extra"])


if __name__ == "__main__":
    unittest.main()
