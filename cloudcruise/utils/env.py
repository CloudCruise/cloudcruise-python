from __future__ import annotations

import os
from typing import Optional
from typing import Literal


CloudCruiseEnvVar = Literal[
    "CLOUDCRUISE_API_KEY",
    "CLOUDCRUISE_BASE_URL",
    "CLOUDCRUISE_ENCRYPTION_KEY",
]


def get_env(key: CloudCruiseEnvVar) -> Optional[str]:
    return os.environ.get(key)
