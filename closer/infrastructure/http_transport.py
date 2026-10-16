from __future__ import annotations

import urllib.error
import urllib.request
from typing import Dict, Optional, Tuple

BASE = "https://api-demo.airwallex.com"


def urllib_transport(method: str, path: str, headers: Dict[str, str], body: Optional[str]) -> Tuple[int, Dict[str, str], str]:
    data = body.encode() if body is not None else (b"" if method == "POST" else None)
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, dict(resp.headers.items()), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()), e.read().decode()
