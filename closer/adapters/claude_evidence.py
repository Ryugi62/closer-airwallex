"""Claude adapter for the EvidenceReader port. HTTP is injected so the adapter is testable offline.

The key is read from ANTHROPIC_API_KEY (or the macOS keychain) by the composition root and passed in;
it is sent in a header, never put in a URL, a log line or an error message. The domain never sees this module.
"""
from __future__ import annotations

import json
from typing import Optional

from closer.adapters.gemini_evidence import PROMPT, Http, EvidenceKeyMissing, urllib_http

MODEL = "claude-haiku-4-5"
URL = "https://api.anthropic.com/v1/messages"

__all__ = ["ClaudeEvidenceReader", "EvidenceKeyMissing", "MODEL"]


class ClaudeEvidenceReader:
    def __init__(self, api_key: Optional[str], http: Http = urllib_http) -> None:
        if not api_key:
            raise EvidenceKeyMissing("no Claude key: set ANTHROPIC_API_KEY")
        self._key, self._http = api_key, http

    def read(self, text: str) -> str:
        body = json.dumps({"model": MODEL, "max_tokens": 300, "temperature": 0,
                           "messages": [{"role": "user", "content": PROMPT + text}]})
        status, raw = self._http(URL, {"Content-Type": "application/json", "x-api-key": self._key,
                                       "anthropic-version": "2023-06-01"}, body)
        if status != 200:
            raise RuntimeError("Claude HTTP %d" % status)
        try:
            return json.loads(raw)["content"][0]["text"]
        except (KeyError, IndexError, ValueError):
            raise RuntimeError("Claude reply had no text")
