# Changelog

## Unreleased

### Added

- `EventType` covers every event the API sends: `agent.recovery`, `execution.password_recovery`, `execution.password_updated`, and `agent.tfa_setup_recovery`, with typed payloads for the first three. The `agent.recovery` payload is `AgentRecoveryPayload`: category, sub-type, outcome and resume node title, plus session and workflow ids.
- Decision Required events `agent.decision_requested` and `agent.decision_answered`, typed as `AgentDecisionRequestedPayload` and `AgentDecisionAnsweredPayload`. `agent.decision_requested` carries `decision_id`, `question`, `context`, `fields` (ids, labels, types, options), `free_text` and `respond_url` (POST the answer there); `agent.decision_answered` carries `outcome` (`answered`, `declined`, `expired`, `cancelled`, `failed`) and, when someone answered, `answered_via`, `answered_by` and `answer` (`values`, `text`, `directive`). Session and workflow ids come first, the run's metadata is in the envelope, and optional keys are omitted rather than null.

### Changed

- The API no longer sends `execution.input_required`: runs do not pause to wait for corrected input variables. A consequential popup is reported through `agent.decision_requested` / `agent.decision_answered` when Decision Required handles the run, and otherwise fails the run with `execution.failed`. The event type, its payload types and the input-variable handlers stay for compatibility and for the history of earlier runs.

## 1.4.1

### Fixed

- The paused run event is `execution.paused`, matching what the API sends. It was typed as `execution.pause`, so handlers comparing against the SDK value never matched.

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
