"""Contract tests for SSE reconnect after a clean server EOF.

The backend bounds how long it will hold a run-events SSE stream open (60-75 minutes) and then
completes the response cleanly, because an orphaned stream is otherwise retained for the life of
the pod. That cap is only safe while this SDK treats a clean EOF as "reconnect" rather than "the
stream is over". These tests pin that contract against a stand-in server, so a change to the
reconnect logic fails here instead of silently stranding long-running consumers in production.

ConnectionManager is driven directly rather than the public client: the contract under test is the
transport's reconnect behaviour, and the higher-level client applies base-URL restrictions that
have nothing to do with it.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from cloudcruise.utils.connection_manager import ConnectionManager

API_KEY = "sk_test_example"
SESSION_ID = "sess_contract_test"

# The SDK's first retry delay is 1.0s; allow margin without making the suite slow.
RECONNECT_WINDOW_S = 2.5


class _CountingSSEHandler(BaseHTTPRequestHandler):
    """Answers every request with one SSE event, then ends the response cleanly.

    Ending the response — rather than erroring or dropping the socket — is byte-for-byte what the
    backend's stream-lifetime cap does when it completes the Observable.
    """

    connections = 0
    lock = threading.Lock()

    def do_GET(self):  # noqa: N802 - name mandated by BaseHTTPRequestHandler
        with _CountingSSEHandler.lock:
            _CountingSSEHandler.connections += 1
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        envelope = {"data": {"payload": {"session_id": SESSION_ID, "status": "execution.started"}}}
        self.wfile.write(f"event: run.event\ndata: {json.dumps(envelope)}\n\n".encode())
        self.wfile.flush()
        # Returning closes the response cleanly: no exception, no socket destroy.

    def log_message(self, *args):
        """Silence per-request logging so test output stays readable."""
        return


@pytest.fixture
def sse_server():
    _CountingSSEHandler.connections = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CountingSSEHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield f"http://{host}:{port}", _CountingSSEHandler
    finally:
        server.shutdown()
        server.server_close()


def test_reconnects_after_clean_server_eof(sse_server):
    """A compliant SDK opens a replacement connection after the server ends the stream.

    One that treated EOF as end-of-stream would stop after the first connection, and the consumer
    would never receive another event once the backend cycled the stream.
    """
    base_url, handler = sse_server
    manager = ConnectionManager(base_url, API_KEY)
    subscription = manager.subscribe(SESSION_ID)

    time.sleep(RECONNECT_WINDOW_S)
    subscription.close()

    assert handler.connections >= 2, (
        f"expected the SDK to reconnect after a clean EOF, but the server saw "
        f"{handler.connections} connection(s). If this fails, the backend stream-lifetime cap "
        f"will strand this SDK every 60-75 minutes."
    )


def test_keeps_reconnecting_across_repeated_clean_eofs(sse_server):
    """The cap fires repeatedly over a long-running consumer's life, so one retry is not enough."""
    base_url, handler = sse_server
    manager = ConnectionManager(base_url, API_KEY)
    subscription = manager.subscribe(SESSION_ID)

    # Long enough to cover the SDK's [1s, 3s, 10s] retry ladder more than once.
    time.sleep(6.0)
    subscription.close()

    assert handler.connections >= 3, (
        f"expected repeated reconnects, but the server saw only {handler.connections} connection(s)"
    )


def test_delivers_events_received_before_a_clean_eof(sse_server):
    """Events sent before the EOF must still reach the consumer.

    A reconnect that dropped the final event of each cycle would be worse than no reconnect at
    all, because the loss would be invisible rather than obvious.
    """
    base_url, _ = sse_server
    manager = ConnectionManager(base_url, API_KEY)
    subscription = manager.subscribe(SESSION_ID)

    received = []
    subscription.on("run.event", lambda msg: received.append(msg))

    time.sleep(RECONNECT_WINDOW_S)
    subscription.close()

    assert received, "expected at least one run.event to be delivered before the stream was cycled"
