"""
stage_link.lag_histogram testleri.

Rapordaki gecikme dagilimi tablosu, guvenilir cift sayisiyla ayni toplami
vermeli. Eskiden son aralik [800, 900) idi ve tam tarama sinirinda (900 sn)
tepe yapan 2 cift tablodan sessizce dusuyordu (146 / 148).
"""
import pandas as pd
import stage_link


def test_upper_scan_limit_is_counted():
    counts = stage_link.lag_histogram(pd.Series([0, 850, 900, 900]), max_lag=900)

    assert counts["800-900"] == 3
    assert counts.sum() == 4


def test_total_matches_input_for_every_lag_on_grid():
    lags = pd.Series(stage_link.LAGS)

    assert stage_link.lag_histogram(lags, max(stage_link.LAGS)).sum() == len(lags)


def test_labels_stay_within_scan_range():
    counts = stage_link.lag_histogram(pd.Series([10]), max_lag=900)

    assert list(counts.index)[0] == "0-100"
    assert list(counts.index)[-1] == "800-900"
    assert counts["0-100"] == 1
