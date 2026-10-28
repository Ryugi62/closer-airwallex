from datetime import date

from closer.adapters.scenario import scenario_pack
from closer.adapters.metrics import new_runtime
from closer.adapters.memory import ListAuditSink
from closer.application.run_cycle import run_cycle
from closer.infrastructure.cli import summary_line


def test_summary_counts_every_decision_including_none_rows():
    invoices, txns, as_of, policy = scenario_pack()
    ben = {i.counterparty: "ben-" + i.id for i in invoices}
    ex, store, _, appr = new_runtime(ben)
    r = run_cycle("SUM-1", as_of, invoices, txns, policy, ex, store, ListAuditSink(), appr)
    line = summary_line(r)
    n_none = sum(1 for d, _ in r.outcomes if d.action.value == "NONE")
    assert "%d decisions" % len(r.outcomes) in line
    assert "%d NONE" % n_none in line
    if n_none:
        shown = [d.subject_id for d, _ in r.outcomes if d.action.value == "NONE"]
        assert shown[0] in line
