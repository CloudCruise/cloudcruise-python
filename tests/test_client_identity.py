import unittest
from importlib.metadata import PackageNotFoundError, version
from unittest.mock import MagicMock, patch

from cloudcruise import CloudCruise, CloudCruiseParams
from cloudcruise._client_identity import _client_header_value
from cloudcruise.utils.connection_manager import ConnectionManager


def _installed_version():
    try:
        return version("cloudcruise")
    except PackageNotFoundError:
        return None


@unittest.skipUnless(_installed_version(), "cloudcruise distribution is not installed")
class TestClientIdentity(unittest.TestCase):
    def setUp(self):
        self.expected_client_header = f"sdk-python/{_installed_version()}"

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
            self.expected_client_header,
        )

    def test_run_events_sse_connection_identifies_the_python_sdk(self):
        """Run events stream over a separate SSE connection that bypasses the REST request
        path; it is API traffic too and must carry the same identification."""
        with patch("cloudcruise.utils.connection_manager.open_sse") as open_sse:
            ConnectionManager("https://api.example.test", "test-key").subscribe("sess_1")

        self.assertEqual(
            open_sse.call_args.kwargs["headers"]["X-CloudCruise-Client"],
            self.expected_client_header,
        )


class TestClientIdentityFallback(unittest.TestCase):
    def test_client_header_omits_the_version_when_the_distribution_is_not_installed(self):
        """A source checkout has no distribution metadata to read a version from; the SDK
        must still identify itself rather than fail on import."""
        with patch(
            "cloudcruise._client_identity.version", side_effect=PackageNotFoundError("cloudcruise")
        ):
            self.assertEqual(_client_header_value(), "sdk-python")


if __name__ == "__main__":
    unittest.main()
