# Changelog

## Unreleased

### Added

- Vault entries carry `additional_fields` (`VaultAdditionalField`, nine types incl. `Address` and `Totp`), `security_questions` (`VaultSecurityQuestion`) and `tfa_methods`. The SDK encrypts every additional field value and every security question and answer before sending and decrypts them on read. A single-entry `get()` of a provider-backed entry returns `additional_field_warnings` and `security_question_warnings` when items were skipped. A payload carrying a provider binding and non-empty `additional_fields` or `security_questions` raises `ValueError`. Requires CloudCruise/monorepo#12158.
- `client.vault.get_tfa_code(permissioned_user_id, domain, method=None, field=None)` picks the 2FA method of an entry with several, or the `Totp` additional field to read. `field` with a `method` other than `AUTHENTICATOR` raises `ValueError`.
- Decision Required events `agent.decision_requested` and `agent.decision_answered`, typed as `AgentDecisionRequestedPayload` and `AgentDecisionAnsweredPayload`. `agent.decision_requested` carries `decision_id`, `answer_by` (the decision deadline), `question`, `context`, `fields` (ids, labels, types, options), `free_text`, `respond_url` (POST the answer there) and, when available, `signed_screenshot_url` / `signed_screenshot_url_expires`; `agent.decision_answered` carries `outcome` (`answered`, `declined`, `expired`, `cancelled`, `failed`) and, when someone answered, `answered_via`, `answered_by` and `answer` (`values`, `text`, `directive`). Session and workflow ids come first, the run's metadata is in the envelope, and optional keys are omitted rather than null.
- `client.runs.get_pending_decision(session_id)` reads the decision a run is waiting on, in the shape of `agent.decision_requested` (`{"decision", "answered_decision_id"}`), through `GET /run/{session_id}/decision/pending`. That route ships with CloudCruise/monorepo#12130; until it is deployed the call answers 404.
- `client.runs.respond_to_decision(session_id, decision_id, answer)` answers a decision through `POST /run/{session_id}/decision/respond`, with the answer typed as `DecisionWebhookAnswer`.

### Deprecated

- `tfa_method` on `VaultEntryInput` and `VaultEntry`. Use `tfa_methods`; `tfa_method` reads as its first entry. Writing it emits a `DeprecationWarning`.
- `execution.input_required` is no longer sent by the API, and `POST /run/{session_id}/new_input_variables` no longer exists. The `execution.input_required` event type, `ExecutionInputRequiredPayload`, `PopupContext`, `AvailableAction`, `PopupRetry` and the `runs` helpers `submit_modal_action`, `submit_input_variables`, `on_popup_decision_required` and `on_input_variables_required` stay importable so existing code keeps running, and the helpers emit a `DeprecationWarning`: the submit helpers get an error response and the listeners never fire. Consequential popups arrive as `agent.decision_requested`; answer them at the event's `respond_url` (see `cloudcruise/runs/README.md`, Decision Required). They will be removed in 2.0.0.

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
