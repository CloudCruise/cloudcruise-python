# Changelog

## 1.5.0

### Added

- `StartRunRequest.workflow_version` pins a run to the highest tagged release matching an exact version or semver range, and `StartRunRequest.workflow_branch_id` runs the head of a workflow branch instead of the default branch. Setting both raises `ValueError`; unset pins are omitted from the `POST /run` payload. Requires a backend with run version pinning.
- `workflows.get_workflow_metadata()` and `workflows.validate_workflow_input()` take the same optional keyword-only `workflow_version` / `workflow_branch_id` selectors, so schemas can be read and checked for the version a pinned run executes. `WorkflowMetadata` gains `version_id`, `version` and `branch_id`. A selector against an API without version selection raises `RuntimeError` instead of returning the default branch's schemas.
- `workflows.list_workflow_versions()` returns `WorkflowVersion` entries (including their `branch_id`) and `workflows.list_workflow_branches()` returns `WorkflowBranch` entries with `is_default`. The module-level `cloudcruise.workflows` functions take the same selectors and add `list_workflow_versions()` / `list_workflow_branches()`.

### Changed

- `runs.start()` no longer fetches workflow metadata to validate `run_input_variables` locally before `POST /run`. The server validates them against the version that actually runs and its errors are raised as the same `InputValidationError`, so runs pinned to a version or branch with a different input schema are no longer rejected, and every run saves one request. `workflows.validate_workflow_input()` is unchanged for callers who want to check a payload up front.

## 1.4.0

### Added

- Requests send `X-CloudCruise-Client: sdk-python/<version>`.

## 1.3.1

### Fixed

- Return `workspace_id` and typed `vault_schema` entries from `get_workflow_metadata()` instead of discarding them from the API response.

## 1.3.0

### Added

- Full JSON Schema Draft-07 validation for workflow inputs, including nested schemas, patterns, arrays, limits, combinators, enums, and local references.
- Structured `InputValidationError.schemaErrors` details for both local and backend validation failures.

### Changed

- Backend `run_input_variables_errors` are surfaced as `InputValidationError` instead of a generic `RuntimeError`.
- Added `jsonschema` as a runtime dependency.

## 1.2.1

### Added

- `runs.get_live_view_connection(session_id)` fetches a fresh live-view URL + single-use auth token for watching an active session's browser stream. Call it again to renew after a previously issued token has been consumed.

## 1.1.0

### Added

- Vault entries support `proxy_setting` (`random`/`static`/`country`/`custom`) and `proxy_value`. For the Enterprise `custom` (bring-your-own) proxy, `proxy_value` is encrypted client-side with the workspace key (like `password`/`tfa_secret`) and decrypted on read; for `static`/`country` it is sent as plaintext (target IP / country code).

## 1.0.0

First stable release of the CloudCruise Python SDK.

### Changed

- Return dataclass instances from workflow and run response APIs so runtime behavior matches the public type hints.
- Return `RunResult` from `handle.wait()` and `runs.get_results()`.
- Return `Workflow` and `WorkflowMetadata` from workflow APIs.
- Return `WebhookReplayResponse` from webhook replay APIs.
- Return `WebhookPayload` from webhook signature verification.
- Deliver typed `FlattenedRunEvent` objects to run event callbacks.

### Added

- Live E2E scripts for local and PyPI-installed SDK smoke testing.
- Unit coverage for dataclass response conversion and typed run event callbacks.
