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

### Versions and Branches

Metadata describes the latest version on the workflow's default branch unless
you select another one. `get_workflow_metadata` and `validate_workflow_input`
take the same optional selectors as `runs.start()`; set at most one (setting
both raises `ValueError`):

```python
# Highest release matching an exact version or semver range
metadata = client.workflows.get_workflow_metadata("workflow-123", workflow_version="^1.2.0")
print(metadata.version, metadata.version_id)

# Latest version on a branch
metadata = client.workflows.get_workflow_metadata(
    "workflow-123", workflow_branch_id="3f6c2a8e-6b1d-4c3e-9a51-2d7f0e8b4c19"
)

# Every version across all branches, newest first
for version in client.workflows.list_workflow_versions("workflow-123"):
    print(version.version, version.branch_id, version.version_note)

# Branches, oldest first; is_default marks the branch unpinned runs use
for branch in client.workflows.list_workflow_branches("workflow-123"):
    print(branch.id, branch.name, branch.is_default)
```

`metadata.version`, `metadata.version_id` and `metadata.branch_id` identify
the version that was described. Against an API without version selection, a
selector raises `RuntimeError` instead of returning the default branch's
schemas.

### Validating Workflow Input

The SDK can validate run payloads against a workflow version's input schema
before you start a run:

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
`instancePath`, `schemaPath`, `keyword`, and `message`.

`runs.start()` does not call this method. The server validates
`run_input_variables` against the input schema of the version that runs, and
its `run_input_variables_errors` are normalized into the same
`InputValidationError` and fields. Call `validate_workflow_input` yourself,
with the same `workflow_version` or `workflow_branch_id` you will start the run
with, to check a payload without starting a run.

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
