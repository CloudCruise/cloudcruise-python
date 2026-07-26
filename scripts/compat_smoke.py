"""Live compatibility smoke test: exercises the current published SDK
surface against a real, running CloudCruise backend. Read-only call only.

Requires CLOUDCRUISE_API_KEY and COMPAT_TEST_BASE_URL. CLOUDCRUISE_ENCRYPTION_KEY
is optional (a placeholder is used if unset, since no vault operations are
exercised here).
"""

import os
import sys

from cloudcruise import CloudCruise, CloudCruiseParams

base_url = os.environ.get("COMPAT_TEST_BASE_URL")
api_key = os.environ.get("CLOUDCRUISE_API_KEY")
encryption_key = os.environ.get("CLOUDCRUISE_ENCRYPTION_KEY") or "0" * 64

if not base_url:
    print("FAIL: COMPAT_TEST_BASE_URL is required")
    sys.exit(1)
if not api_key:
    print("FAIL: CLOUDCRUISE_API_KEY is required")
    sys.exit(1)

client = CloudCruise(
    CloudCruiseParams(api_key=api_key, base_url=base_url, encryption_key=encryption_key)
)

try:
    workflows = client.workflows.get_all_workflows()
    print(f"OK: workflows.get_all_workflows() -> {len(workflows)} workflows")
except Exception as e:
    print(f"FAIL: workflows.get_all_workflows() -> {e}")
    sys.exit(1)
