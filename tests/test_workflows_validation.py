import unittest

from cloudcruise.workflows.client import WorkflowsClient
from cloudcruise.workflows.types import WorkflowMetadata, WorkflowInputSchema, InputValidationError

class _FakeClient(WorkflowsClient):
    def __init__(self):
        super().__init__(lambda *args, **kwargs: None)
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
        with self.assertRaises(InputValidationError):
            c.validate_workflow_input("wf-1", {"url": "x", "extra": 1})

if __name__ == "__main__":
    unittest.main()
