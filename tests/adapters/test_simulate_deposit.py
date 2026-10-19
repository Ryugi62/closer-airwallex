"""Recorded-transport tests for the sandbox simulation deposit (SPEC section 6: one live deposit allowed, no transfer writes)."""
import json

from closer.adapters.airwallex_http import AirwallexGateway
from tests.adapters.test_airwallex_http import FakeTransport

GA = "0d685084-2ba2-4498-92b9-9aee7f2ea856"
RECORDED = {"id": "dep_rec_1", "status": "PENDING", "global_account_id": GA, "amount": 1000, "currency": "USD"}


def gw(status=201, body=RECORDED):
    t = FakeTransport({("POST", "/api/v1/simulation/deposit/create"): (status, {"x-request-id": "sim-r1"}, body)})
    return AirwallexGateway(t, client_id="cid", api_key="key"), t


def test_simulate_deposit_posts_to_simulation_endpoint_only():
    g, t = gw()
    out = g.simulate_deposit(GA, "1000.00", "USD", "LIVE-DEP-1")
    method, path, _, body = t.calls[-1]
    assert (method, path) == ("POST", "/api/v1/simulation/deposit/create")
    sent = json.loads(body)
    assert sent["global_account_id"] == GA and sent["currency"] == "USD" and float(sent["amount"]) == 1000.0
    assert out["id"] == "dep_rec_1"
    assert "/transfers/create" not in [c[1] for c in t.calls]


def test_simulate_deposit_logs_status_and_request_id():
    g, _ = gw()
    g.simulate_deposit(GA, "1000.00", "USD", "LIVE-DEP-1")
    row = g.call_log[-1]
    assert row["endpoint"] == "POST /api/v1/simulation/deposit/create" and row["status"] == 201 and row["request_id"] == "sim-r1"


def test_simulate_deposit_http_error_keeps_status_and_raw_body():
    import pytest
    from closer.adapters.airwallex_http import AirwallexError
    g, _ = gw(404, {"code": "not_found", "message": "nope"})
    with pytest.raises(AirwallexError) as e:
        g.simulate_deposit(GA, "1000.00", "USD", "LIVE-DEP-1")
    assert "404" in str(e.value) and "not_found" in str(e.value)
    assert g.call_log[-1]["status"] == 404
