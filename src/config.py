"""Central environment configuration.

All external endpoints, model names and credentials come from the environment
(see ``.env``). Nothing is hardcoded in the source tree, so the repository never
leaks server IPs, model identifiers or keys. ``require_env`` fails loudly when a
needed value is missing instead of silently falling back to a baked-in default.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def require_env(name: str) -> str:
    """Return the value of env var ``name`` or raise if it is unset/empty."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "Configure it in your .env file."
        )
    return value
