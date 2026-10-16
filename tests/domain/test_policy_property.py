import random
from collections import defaultdict
from decimal import Decimal as D

from closer.domain.classifier import classify
from closer.domain.decision import decide
from closer.domain.models import Action
from tests.helpers import AS_OF, inv, policy, txn


def test_limits_hold_over_500_random_cases():
    rnd = random.Random(7)
    for case in range(500):
        n = rnd.randint(1, 12)
        invs, txns = [], []
        for k in range(n):
            amt = D(rnd.randint(100, 5000))
            cur = rnd.choice(["USD", "EUR"])
            invs.append(inv(id=f"INV-{k}", amount=str(amt), cur=cur))
            fee = D(rnd.choice([0, 5, 20, 49, 80, 300]))
            txns.append(txn(id=f"t{k}", amount=str(amt), cur=cur, fee=str(fee), desc=f"INV-{k}"))
        pol = policy(item_limit={"USD": D("50"), "EUR": D("50")}, cycle_cap={"USD": D("100"), "EUR": D("120")})
        ds = decide(classify(invs, txns, AS_OF, pol), invs, pol)
        per = defaultdict(D)
        for d in ds:
            if d.action == Action.AUTO_ADJUST:
                assert d.amount <= pol.item_limit[d.currency], case
                per[d.currency] += d.amount
        for cur, tot in per.items():
            assert tot <= pol.cycle_cap[cur], case
