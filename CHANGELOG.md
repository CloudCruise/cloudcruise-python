# Changelog

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
