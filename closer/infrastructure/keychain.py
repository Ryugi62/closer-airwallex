"""Reads sandbox credentials from the macOS keychain. Values are returned, never printed."""
from __future__ import annotations

import os
import subprocess
from typing import Optional, Tuple

API_KEY_SERVICE = "airwallex-sandbox-api-key"
CLIENT_ID_SERVICE = "airwallex-sandbox-client-id"


def _kc(service: str) -> Optional[str]:
    try:
        out = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def credentials() -> Optional[Tuple[str, str]]:
    """(client_id, api_key) from env AIRWALLEX_CLIENT_ID / AIRWALLEX_API_KEY, else keychain; None if absent."""
    cid = os.environ.get("AIRWALLEX_CLIENT_ID") or _kc(CLIENT_ID_SERVICE)
    key = os.environ.get("AIRWALLEX_API_KEY") or _kc(API_KEY_SERVICE)
    return (cid, key) if cid and key else None
