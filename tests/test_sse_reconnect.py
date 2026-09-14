"""Contract tests for SSE reconnect after a clean server EOF.

The CloudCruise backend bounds how long it will hold a run-events SSE stream open (60-75 minutes)
and then completes the response cleanly, because an orphaned stream is otherwise retained for the
life of the pod. That cap is only safe while this SDK treats a clean EOF as "reconnect" rather
than "the stream is over". These tests pin that contract against a stand-in server, so a change to
the reconnect logic fails here instead of silently stranding long-running consumers in production.

ConnectionManager is driven directly rather than the public client: the contract under test is the
transport's reconnect behaviour, and the higher-level client applies base-URL restrictions that
have nothing to do with it.

No network access: the stand-in server binds to a loopback ephemeral port.
"""

import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cloudcruise.utils.connection_manager import ConnectionManager

API_KEY = "sk_test_example"
SESSION_ID = "sess_contract_test"

# Generous ceilings: every assertion polls and returns as soon as it is satisfied, so these bound
# the failure case rather than the happy path. Fixed sleeps were deliberately avoided — subscribe()
# returns before the background connection is established, so a fixed wait races a slow CI worker.
CONNECT_TIMEOUT_S = 15.0
REPEAT_TIMEOUT_S = 30.0
POLL_INTERVAL_S = 0.05


def wait_until(predicate, timeout_s):
    """Poll until predicate() is truthy or the deadline passes; returns the final value."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(POLL_INTERVAL_S)
    return predicate()


class _CountingSSEHandler(BaseHTTPRequestHandler):
    """Answers every request with one SSE event, then ends the response cleanly.

    Ending the response — rather than erroring or dropping the socket — is byte-for-byte what the
    backend's stream-lifetime cap does when it completes the Observable.

    `gate` lets a test hold the write until it has finished wiring up its listener. Without it the
    event can be emitted before the listener exists and is then discarded, which would make a
    delivery assertion pass only by accident on some later reconnect.
    """

    connections = 0
    lock = threading.Lock()
    gate = threading.Event()

    def do_GET(self):  # noqa: N802 - name mandated by BaseHTTPRequestHandler
        with _CountingSSEHandler.lock:
            _CountingSSEHandler.connections += 1
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        _CountingSSEHandler.gate.wait(timeout=CONNECT_TIMEOUT_S)
        envelope = {"data": {"payload": {"session_id": SESSION_ID, "status": "execution.started"}}}
        self.wfile.write(f"event: run.event\ndata: {json.dumps(envelope)}\n\n".encode())
        self.wfile.flush()
        # Returning closes the response cleanly: no exception, no socket destroy.

    def log_message(self, *args):
        """Silence per-request logging so test output stays readable."""
        return


class SSEReconnectContractTest(unittest.TestCase):
    """unittest, per AGENTS.md: the documented suite command is `python -m unittest discover`."""

    def setUp(self):
        _CountingSSEHandler.connections = 0
        _CountingSSEHandler.gate = threading.Event()
        _CountingSSEHandler.gate.set()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _CountingSSEHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base_url = f"http://{host}:{port}"
        self.subscription = None

    def tearDown(self):
        if self.subscription is not None:
            self.subscription.close()
        self.server.shutdown()
        self.server.server_close()

    def _subscribe(self):
        manager = ConnectionManager(self.base_url, API_KEY)
        self.subscription = manager.subscribe(SESSION_ID)
        return self.subscription

    def _connections(self):
        with _CountingSSEHandler.lock:
            return _CountingSSEHandler.connections

    def test_reconnects_after_clean_server_eof(self):
        """A compliant SDK opens a replacement connection after the server ends the stream.

        One that treated EOF as end-of-stream would stop after the first connection, and the
        consumer would never receive another event once the backend cycled the stream.
        """
        self._subscribe()

        wait_until(lambda: self._connections() >= 2, CONNECT_TIMEOUT_S)

        self.assertGreaterEqual(
            self._connections(),
            2,
            "expected the SDK to reconnect after a clean EOF; if this fails, the backend "
            "stream-lifetime cap will strand this SDK every 60-75 minutes",
        )

    def test_keeps_reconnecting_across_repeated_clean_eofs(self):
        """The cap fires repeatedly over a long-running consumer's life, so one retry is not
        enough — the SDK has to keep re-establishing the stream each time the server cycles it."""
        self._subscribe()

        wait_until(lambda: self._connections() >= 3, REPEAT_TIMEOUT_S)

        self.assertGreaterEqual(
            self._connections(), 3, "expected the SDK to keep reconnecting across repeated EOFs"
        )

    def test_delivers_events_received_before_a_clean_eof(self):
        """Events sent before the EOF must still reach the consumer.

        A reconnect that dropped the final event of each cycle would be worse than no reconnect at
        all, because the loss would be invisible rather than obvious. The server is gated until
        the listener is registered so this asserts first-connection delivery, not delivery on some
        later reconnect.
        """
        _CountingSSEHandler.gate.clear()
        subscription = self._subscribe()

        received = []
        subscription.on("run.event", lambda msg: received.append(msg))
        _CountingSSEHandler.gate.set()

        wait_until(lambda: len(received) >= 1, CONNECT_TIMEOUT_S)

        self.assertGreaterEqual(
            len(received),
            1,
            "expected a run.event delivered on the connection that was open when the listener "
            "was registered",
        )


if __name__ == "__main__":
    unittest.main()
