"""Hand-written expected decision per subject of the SYNTHETIC pack, derived from SPEC section 4 and the
pack policy (item limit 50 USD, cycle cap 100 USD), not copied from Closer output.
Author-labelled: this measures agreement with the SPEC, not accuracy on real customer data."""
A, H, E, N = "AUTO_ADJUST", "HOLD_FOR_APPROVAL", "ESCALATE", "NONE"
SCENARIO_LABELS = {"syn_0028": ("NOT_SETTLED", N), "syn_0026": ("UNMATCHED_TXN", E), "syn_0027": ("UNMATCHED_TXN", E)}
SCENARIO_LABELS.update({"INV-1%02d" % k: ("MATCHED", N) for k in range(1, 9)})
SCENARIO_LABELS.update({
    "INV-201": ("FEE_DEDUCTED", A), "INV-202": ("FEE_DEDUCTED", A), "INV-203": ("FEE_DEDUCTED", A),
    "INV-204": ("FEE_DEDUCTED", A),
    "INV-205": ("FEE_DEDUCTED", E),   # 30+35 would breach the 100 cycle cap after 84 already used
    "INV-206": ("FEE_DEDUCTED", E),   # 75 > item limit 50
    "INV-301": ("FX_DIFFERENCE", A), "INV-302": ("FX_DIFFERENCE", A),
    "INV-303": ("FX_DIFFERENCE", E),  # 7.4% drift > 1% tolerance
    "INV-401": ("DUPLICATE_PAYMENT", H), "INV-402": ("DUPLICATE_PAYMENT", H),
    "INV-501": ("MISSING_PAYMENT", E), "INV-502": ("MISSING_PAYMENT", E), "INV-503": ("MISSING_PAYMENT", E),
    "INV-601": ("NOT_DUE", N), "INV-602": ("NOT_DUE", N),
    "INV-701": ("AMOUNT_MISMATCH", A),  # 0.30 <= rounding tolerance 0.50
    "INV-702": ("AMOUNT_MISMATCH", E), "INV-703": ("AMOUNT_MISMATCH", E),
    "INV-801": ("FEE_DEDUCTED", E),   # inferred link is never auto-adjusted (SPEC 4.11)
})
