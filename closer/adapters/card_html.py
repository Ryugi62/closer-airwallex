"""Static HTML for one approval card. The page shows exactly the four items an approval is bound to."""
from __future__ import annotations

from html import escape

from closer.domain.approval import ApprovalCard

_CSS = """
:root{--bg:#f4f5f7;--fg:#191f28;--mut:#4e5968;--card:#fff;--line:#e5e8eb;--blue:#1b64da}
@media(prefers-color-scheme:dark){:root{--bg:#17171c;--fg:#f2f4f6;--mut:#9ea4ad;--card:#202027;--line:#2c2c35}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,sans-serif;padding:24px 16px}
.wrap{max-width:460px;margin:0 auto}.tag{font-size:12px;color:var(--mut);margin-bottom:8px}
.card{background:var(--card);border-radius:20px;padding:24px;border:1px solid var(--line)}
h1{font-size:20px;margin:0 0 4px}.amt{font-size:34px;font-weight:700;margin:8px 0 20px}
dl{margin:0}.row{display:flex;justify-content:space-between;gap:16px;padding:12px 0;border-top:1px solid var(--line)}
dt{color:var(--mut)}dd{margin:0;text-align:right;font-weight:600;word-break:break-all}
.hash{font:12px ui-monospace,monospace;color:var(--mut);margin-top:16px;word-break:break-all}
.note{font-size:13px;color:var(--mut);margin-top:16px}
.btn{display:block;width:100%;min-height:52px;margin-top:20px;padding:14px;border:0;border-radius:14px;background:var(--blue);color:#fff;font-size:16px;font-weight:600}
.btn.ghost{min-height:52px;background:transparent;color:var(--mut);border:1px solid var(--line);margin-top:8px}
"""


def render_card(c: ApprovalCard) -> str:
    e = escape
    ev = "".join("<div>%s</div>" % e(t) for t in c.evidence_txn_ids)
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Closer approval card</title><style>%s</style></head><body><div class="wrap">
<div class="tag">SYNTHETIC data, Airwallex sandbox, no real money</div>
<div class="card"><h1>Approve refund of surplus payment</h1>
<div>Invoice %s was paid twice. Approve one refund for the surplus only.</div>
<div class="amt" data-bound="amount">%s %s</div>
<dl>
<div class="row"><dt>Amount</dt><dd>%s</dd></div>
<div class="row"><dt>Currency</dt><dd data-bound="currency">%s</dd></div>
<div class="row"><dt>Counterparty</dt><dd data-bound="counterparty">%s</dd></div>
<div class="row"><dt>Evidence (transaction ids)</dt><dd data-bound="evidence">%s</dd></div>
</dl>
<div class="hash">approval binds to sha256 %s...</div>
<div class="note">Change any of these four items after approving and the approval is rejected (audit: APPROVAL_MISMATCH or APPROVAL_SIGNATURE_INVALID). The amount is computed by code, not by a model.</div>
<button class="btn" type="button">Approve this card</button><button class="btn ghost" type="button">Reject</button>
</div></div></body></html>
""" % (_CSS, e(c.invoice_id), e("%.2f" % c.amount), e(c.currency), e("%.2f" % c.amount), e(c.currency), e(c.counterparty), ev,
       c.digest()[:16])
