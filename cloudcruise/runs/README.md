# Runs Client (Python)

The Runs client powers workflow execution and realtime monitoring via
Server-Sent Events (SSE). Launch workflows, stream events, submit user inputs,
and manage workflow sessions directly from Python.

---

## Usage

### Basic Workflow Execution

```python
from cloudcruise import CloudCruise
from cloudcruise.runs.types import StartRunRequest

# Generate keys in the CloudCruise portal under Settings → API Keys and
# Settings → Encryption Keys.
client = CloudCruise(
    api_key="your-api-key",
    encryption_key="your-encryption-key",
)
# Alternatively, set CLOUDCRUISE_API_KEY and CLOUDCRUISE_ENCRYPTION_KEY and
# instantiate with `client = CloudCruise()`.

# Start a workflow run.
# run_input_variables are validated against the workflow's input schema when
# metadata is available.
handle = client.runs.start(
    StartRunRequest(
        workflow_id="workflow-123",
        run_input_variables={
            "variable_1": "https://example.com",
            "variable_2": "john_doe",
        },
    )
)

print("Session ID:", handle.sessionId)

# Wait for completion and fetch results
result = handle.wait()
print("Run completed:", result.status)
print("Output data:", result.data)
```

### Realtime Event Streaming

```python
handle = client.runs.start(
    StartRunRequest(
        workflow_id="workflow-123",
        run_input_variables={"target_url": "https://example.com"},
    )
)

# Listen to all events with flattened structure
def on_run_event(event):
    print("Event type:", event["type"])
    print("Payload:", event["payload"])
    print("Timestamp:", event["timestamp"])

handle.on("run.event", on_run_event)

# Or use type-specific listeners for cleaner code
handle.on("execution.start", lambda e: print(f"Started: {e['payload']['workflow_id']}"))
handle.on("execution.step", lambda e: print(f"Step: {e['payload']['current_step']} -> {e['payload']['next_step']}"))
handle.on("screenshot.uploaded", lambda e: print(f"Screenshot: {e['payload']['screenshot_id']}"))
handle.on("execution.success", lambda e: print(f"Success! Data: {e['payload'].get('data')}"))
handle.on("execution.failed", lambda e: print(f"Failed: {e['payload'].get('errors')}"))

# Handle errors and completion
handle.on("error", lambda err: print("Stream error:", err))
handle.on("end", lambda info: print("Workflow ended:", info.get("type")))

# Use iteration for streaming raw SSE messages (for advanced use cases)
for message in handle:
    if message.get("event") == "run.event":
        event_name = (message.get("data") or {}).get("event")
        print("Received event:", event_name)
        if event_name == "execution.success":
            break
```

### User Interactions

See the [CloudCruise documentation](https://docs.cloudcruise.com/run-api/submit-user-interaction-data)
for additional context.

```python
# Using type-specific listener (recommended)
def on_interaction_waiting(event):
    print("Workflow paused, submitting input...")
    print("Missing fields:", event["payload"]["missing_properties"])
    client.runs.submit_user_interaction(
        handle.sessionId,
        {
            "field1": "user_provided_value",
            "field2": 42,
            "confirmation": True,
        },
    )

handle.on("interaction.waiting", on_interaction_waiting)

# Or using generic listener
def maybe_submit_input(event):
    if event["type"] == "interaction.waiting":
        print("Workflow paused, submitting input...")
        client.runs.submit_user_interaction(
            handle.sessionId,
            {
                "field1": "user_provided_value",
                "field2": 42,
                "confirmation": True,
            },
        )

handle.on("run.event", maybe_submit_input)
```

### Advanced Options

```python
from cloudcruise.runs.types import DryRun, RunSpecificWebhook

# Dry run mode with additional output context
dry_run_handle = client.runs.start(
    StartRunRequest(
        workflow_id="test-workflow",
        run_input_variables={"url": "https://example.com"},
        dry_run=DryRun(enabled=True, add_to_output={"test_mode": True}),
    )
)

# Workflow execution with webhook notifications
webhook_handle = client.runs.start(
    StartRunRequest(
        workflow_id="monitored-workflow",
        run_input_variables={"target": "https://example.com"},
        webhook=RunSpecificWebhook(
            url="https://your-app.com/webhook",
            event_types_subscribed=["execution.success", "execution.failed"],
            secret="webhook-secret",  # configure in the CloudCruise portal
            validity=3600,  # seconds
        ),
    )
)
```

### Session Utilities

- `client.runs.get_results(session_id)` – Retrieve the latest run snapshot.
- `client.runs.interrupt(session_id)` – Request that the workflow stop.
- `client.runs.replay_webhooks(session_id)` – Re-send run-specific webhooks.

Each `RunHandle` also exposes:

- `on(event, handler)` – Register event listeners (`run.event`, `ping`, `error`, `end`, `message`, ...).
- `wait()` – Block until completion and return `RunResult`.
- `close()` – Stop streaming events and release resources.
- Iteration (`for message in handle`) – Consume SSE messages as they arrive.

---

## Event Types

### Flattened Event Structure

All events are delivered with a flattened structure for improved developer experience:

```python
{
    "type": "execution.start",        # Event type
    "payload": {...},                  # Event-specific data
    "timestamp": 1234567890,           # Event timestamp
    "expires_at": 1234567890,          # Expiration timestamp
    "_raw": {...}                      # Original SSE message (for advanced use)
}
```

### Type-Specific Listeners

You can listen to specific event types instead of filtering manually:

```python
# Instead of this:
handle.on("run.event", lambda e: print(e["payload"]) if e["type"] == "execution.start" else None)

# Do this:
handle.on("execution.start", lambda e: print(e["payload"]))
```

### Available Event Types

**Terminal events** (workflow ends after these):
- `execution.success` – Workflow completed successfully
- `execution.failed` – Workflow failed with errors
- `execution.stopped` – Workflow was interrupted

**Non-terminal events**:
- `execution.queued` – Workflow queued for execution
- `execution.start` – Workflow execution started
- `execution.step` – Workflow progressed to next step
- `execution.requeued` – Workflow requeued for retry
- `interaction.waiting` – Workflow waiting for user input
- `interaction.finished` – User input received
- `screenshot.uploaded` – Screenshot captured
- `file.uploaded` – File uploaded
- `agent.error_analysis` – Error analysis completed

See `cloudcruise/runs/types.py` (`EventType`) and `cloudcruise/events/types.py` for complete type definitions and payload structures.

---

## Additional Resources

- [API reference](https://docs.cloudcruise.com)
- [`cloudcruise/runs/client.py`](./client.py) – Implementation details
- [`cloudcruise/runs/types.py`](./types.py) – Typed request/response schemas
