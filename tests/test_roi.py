from closer.application.roi import KRW_PER_MINUTE, MINUTES_PER_ITEM, roi_krw


def test_floor_assumptions_are_stated_constants():
    assert KRW_PER_MINUTE == 172 and MINUTES_PER_ITEM == 5


def test_roi_counts_only_items_moved_off_the_human_queue():
    r = roi_krw(baseline_exceptions=21, closer_human_items=13)
    assert r["items_moved"] == 8
    assert r["krw_per_cycle"] == 8 * 5 * 172
    assert r["share_pct"] == "38.1"
    assert r["krw_per_1000_exceptions"] == 381 * 5 * 172


def test_no_negative_roi():
    assert roi_krw(5, 9)["krw_per_cycle"] == 0
