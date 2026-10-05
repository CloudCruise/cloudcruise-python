import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from unittest.mock import MagicMock, patch

from cloudcruise import CloudCruise, CloudCruiseParams
from cloudcruise.utils.connection_manager import ConnectionManager

EXPECTED_CLIENT_HEADER = f"sdk-python/{version('cloudcruise')}"


class _HeaderCapturingHandler(BaseHTTPRequestHandler):
    received = None

    def do_GET(self):
        _HeaderCapturingHandler.received = dict(self.headers)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

    def log_message(self, *args):
        return


class TestClientIdentity(unittest.TestCase):
    def test_rest_requests_identify_the_python_sdk_and_its_installed_version(self):
        """The backend counts API usage per calling surface and client version from
        X-CloudCruise-Client; without it SDK traffic is indistinguishable from raw API calls.
        The version is the installed package's, so it cannot drift from the release."""
        client = CloudCruise(CloudCruiseParams(api_key="test-key", encryption_key="00" * 32))
        response = MagicMock(ok=True, status_code=200, text="[]")
        response.json.return_value = []

        with patch("cloudcruise.cloudcruise.requests.request", return_value=response) as request:
            client._make_request("GET", "/workflows")

        self.assertEqual(
            request.call_args.kwargs["headers"]["X-CloudCruise-Client"],
            EXPECTED_CLIENT_HEADER,
        )

    def test_run_events_sse_connection_identifies_the_python_sdk(self):
        """Run events stream over a separate SSE connection that bypasses the REST request
        path; it is API traffic too and must carry the same identification."""
        _HeaderCapturingHandler.received = None
        server = ThreadingHTTPServer(("127.0.0.1", 0), _HeaderCapturingHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        host, port = server.server_address[:2]
        subscription = ConnectionManager(f"http://{host}:{port}", "test-key").subscribe("sess_1")
        try:
            deadline = time.monotonic() + 15
            while _HeaderCapturingHandler.received is None and time.monotonic() < deadline:
                time.sleep(0.025)
            self.assertEqual(
                (_HeaderCapturingHandler.received or {}).get("X-CloudCruise-Client"),
                EXPECTED_CLIENT_HEADER,
            )
        finally:
            subscription.close()
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
