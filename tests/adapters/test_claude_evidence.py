import json

import pytest

from closer.adapters.claude_evidence import ClaudeEvidenceReader, EvidenceKeyMissing


class FakeHttp:
    def __init__(self, status=200, payload=None):
        self.status, self.payload, self.calls = status, payload, []

    def __call__(self, url, headers, body):
        self.calls.append((url, dict(headers), body))
        return self.status, json.dumps(self.payload)


OK = {"content": [{"type": "text", "text": '{"claim": "DISPUTE", "quote": "we dispute"}'}]}


def test_missing_key_raises_clear_error_and_makes_no_request():
    http = FakeHttp(payload=OK)
    with pytest.raises(EvidenceKeyMissing) as e:
        ClaudeEvidenceReader(api_key=None, http=http)
    assert "ANTHROPIC_API_KEY" in str(e.value) and http.calls == []


def test_request_has_key_in_header_not_url_and_text_inside_prompt():
    http = FakeHttp(payload=OK)
    out = ClaudeEvidenceReader("K3Y", http=http).read("we dispute this")
    url, headers, body = http.calls[0]
    assert "K3Y" not in url and "K3Y" not in body and headers["x-api-key"] == "K3Y"
    assert "we dispute this" in body and url.endswith("/v1/messages")
    assert json.loads(out)["claim"] == "DISPUTE"


def test_http_error_raises_without_leaking_key():
    http = FakeHttp(status=429, payload={"error": {"message": "quota"}})
    with pytest.raises(RuntimeError) as e:
        ClaudeEvidenceReader("K3Y", http=http).read("x")
    assert "429" in str(e.value) and "K3Y" not in str(e.value)


def test_empty_content_raises():
    with pytest.raises(RuntimeError):
        ClaudeEvidenceReader("K", http=FakeHttp(payload={"content": []})).read("x")
