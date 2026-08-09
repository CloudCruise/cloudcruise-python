# Workflows Client (Python)

The Workflows client lets you explore workflow definitions, fetch metadata,
and validate input payloads before executing a run. Use it to inspect schemas
and prevent invalid submissions.

---

## Usage

### Basic Operations

```python
from cloudcruise import CloudCruise, CloudCruiseParams

client = CloudCruise(
    CloudCruiseParams(
        api_key="your-api-key",
        encryption_key="your-encryption-key",
    )
)
# You can also set CLOUDCRUISE_API_KEY and CLOUDCRUISE_ENCRYPTION_KEY in the
# environment and instantiate with `client = CloudCruise()`.

# Retrieve all workflows visible to the API key
workflows = client.workflows.get_all_workflows()
print(workflows[0].id)

# Fetch metadata for a single workflow
metadata = client.workflows.get_workflow_metadata("workflow-123")
print(metadata.input_schema.required)
print(metadata.workspace_id)

for variable_name, credential in metadata.vault_schema.items():
    print(variable_name, credential.domain, credential.example)
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
    print("Missing:", exc.missingRequired)
    print("Type issues:", exc.invalidTypes)
    print("Schema errors:", exc.schemaErrors)
    raise

# If no exception is raised, the payload matches the schema.
```

Validation follows JSON Schema Draft-07, including nested schemas, `pattern`,
arrays and `items`, limits, `enum` and `const`, combinators, and local `$ref`
references. It matches server behavior in these areas:

- `format` is treated as an annotation and is not enforced.
- `$ref` may reference locations within the same schema (`#/...`), but the SDK
  will not fetch external schemas.
- Invalid schemas fail closed with `InputValidationError`.

`InputValidationError` retains `missingRequired`, `invalidTypes`, and
`unknownKeys` for compatibility. `schemaErrors` contains every failure with
`instancePath`, `schemaPath`, `keyword`, and `message`. If the server rejects
an input that passed local validation, its `run_input_variables_errors` are
normalized into the same exception and fields.

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
