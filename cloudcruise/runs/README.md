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

# Listen to specific events
def on_run_event(event):
    data = (event or {}).get("data") or {}
    print("Event:", data.get("event"))
    print("Payload:", data.get("payload"))

handle.on("run.event", on_run_event) # or use lambdas
handle.on("error", lambda err: print("Stream error:", err))
handle.on("end", lambda info=None: print("Workflow ended:", (info or {}).get("type")))

# Use iteration for streaming messages (run.event + ping)
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
def maybe_submit_input(event):
    data = (event or {}).get("data") or {}
    if data.get("event") == "interaction.waiting":
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

Run events emit the following terminal statuses:

- `execution.success`
- `execution.failed`
- `execution.stopped`

Non-terminal events include `execution.queued`, `execution.start`,
`execution.step`, `interaction.waiting`, and more. Inspect
`cloudcruise/runs/types.py` (`EventType`) for the full list.

---

## Additional Resources

- [API reference](https://docs.cloudcruise.com)
- [`cloudcruise/runs/client.py`](./client.py) – Implementation details
- [`cloudcruise/runs/types.py`](./types.py) – Typed request/response schemas
