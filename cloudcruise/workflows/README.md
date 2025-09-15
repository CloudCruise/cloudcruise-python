# Workflows Client (Python)

The Workflows client lets you explore workflow definitions, fetch metadata,
and validate input payloads before executing a run. Use it to inspect schemas
and prevent invalid submissions.

---

## Usage

### Basic Operations

```python
from cloudcruise import CloudCruise

client = CloudCruise(
    api_key="your-api-key",
    encryption_key="your-encryption-key",
)
# You can also set CLOUDCRUISE_API_KEY and CLOUDCRUISE_ENCRYPTION_KEY in the
# environment and instantiate with `client = CloudCruise()`.

# Retrieve all workflows visible to the API key
workflows = client.workflows.get_all_workflows()
print(workflows)

# Fetch metadata for a single workflow
metadata = client.workflows.get_workflow_metadata("workflow-123")
print(metadata)
```

### Validating Workflow Input

The SDK can proactively validate run payloads against the workflow's input
schema. `RunsClient.start` calls this automatically when metadata is available,
but you can use it directly:

```python
from cloudcruise.workflows.types import InputValidationError

payload = {
    "url": "https://example.com",
    "attempts": 2,
}

try:
    client.workflows.validate_workflow_input("workflow-123", payload)
except InputValidationError as exc:
    print("Validation failed:", exc)
    print("Missing:", exc.missing_required)
    print("Type issues:", exc.invalid_types)
    raise

# If no exception is raised, the payload matches the schema.
```

During validation the client checks:

- Required fields
- Allowed value types (string, number, object, etc.)
- Whether additional keys are permitted when the schema disallows extras

### Combining with Runs

```python
from cloudcruise.runs.types import StartRunRequest

payload = {"email": "user@example.com"}

client.workflows.validate_workflow_input("workflow-123", payload)
handle = client.runs.start(
    StartRunRequest(workflow_id="workflow-123", run_input_variables=payload)
)
```

---

## Types & References

- [`cloudcruise/workflows/client.py`](./client.py) – client implementation.
- [`cloudcruise/workflows/types.py`](./types.py) – data models for workflows,
  input schemas, and validation errors.

---

## Official Documentation

Consult the CloudCruise docs for definitions, schema construction, and portal
guides. The SDK mirrors the API but the documentation is the authoritative
source for supported fields and behaviors.
