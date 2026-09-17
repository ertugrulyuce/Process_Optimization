"""
clean.py testleri.

Temizlik kurallari (R1-R8) ve kapsam esikleri sonraki her fazin girdisini
belirliyor. Yanlislikla NaN'a cevrilen bir hucre ya da yanlislikla kapsam
disi birakilan bir output, capability ve optimizasyon sonuclarini hata
vermeden degistirir. Testler ham veriye dokunmaz; her kural, sonucu elle
hesaplanabilen kucuk tablolarla sabitlenir.
"""
import math

import audit
import clean
import numpy as np
import pandas as pd
import pytest
import schema
from conftest import ROOT

N = 200  # build_kpis tablolarinin satir sayisi; _pattern icin cift olmali
ACT = "Stage1.Output.Measurement0.U.Actual"


# --- yardimcilar --------------------------------------------------------------

def _mini(actual, setpoint=10.0):
    """clean() icin tek output'lu tablo. Stage1 setpoint'i R5 icin gerekli."""
    n = len(actual)
    return pd.DataFrame({
        "time_stamp": pd.date_range("2026-01-01", periods=n, freq="s"),
        "Machine1.Zone1Temperature.C.Actual": np.zeros(n),
        ACT: actual,
        "Stage1.Output.Measurement0.U.Setpoint": np.full(n, setpoint),
    })


def _pattern(n=N):
    """Ortalamasi tam 0, orneklem std'si ~1 olan +1/-1 dizisi."""
    return np.tile([1.0, -1.0], n // 2)


def _full(setpoint=10.0):
    """
    build_kpis() icin 30 output'un tamamini iceren tablo. Her output
    varsayilan olarak kapsam ici ve bias'siz; testler ilgilendikleri output'u
    degistirir.
    """
    data = {}
    for st in schema.STAGES:
        for i in range(schema.N_MEASUREMENTS):
            data[f"{st}.Output.Measurement{i}.U.Setpoint"] = np.full(N, setpoint)
            data[f"{st}.Output.Measurement{i}.U.Actual"] = setpoint + _pattern()
    return pd.DataFrame(data)


def _row(summary, name):
    return summary.set_index("output").loc[name]


# --- clean(): hucre kurallari -------------------------------------------------

def test_zero_negative_and_tiny_actuals_become_nan():
    df, log = clean.clean(_mini([10.2, 0.0, -1.0, 1e-300, 9.8]))

    assert df[ACT].isna().tolist() == [False, True, True, True, False]
    assert log["R1_zeros_to_nan"] == 1
    assert log["R2_negatives_to_nan"] == 1
    assert log["R8_tiny_to_nan"] == 1


def test_tiny_threshold_is_relative_to_setpoint():
    """R8 esigi mutlak degil, setpoint'in TINY_FRAC kati; esigin kendisi korunur."""
    sp = 10.0
    edge = sp * clean.TINY_FRAC
    df, _ = clean.clean(_mini([edge / 2, edge, edge * 2], setpoint=sp))

    assert df[ACT].isna().tolist() == [True, False, False]


def test_tiny_rule_needs_a_setpoint():
    """Setpoint kolonu yoksa R8 'kucuk'u tanimlayamaz; yalnizca R1/R2 uygulanir."""
    raw = _mini([10.0, 10.0, 10.0])
    raw["Stage2.Output.Measurement0.U.Actual"] = [1e-300, 0.0, 5.0]
    df, _ = clean.clean(raw)

    assert df["Stage2.Output.Measurement0.U.Actual"].isna().tolist() == [False, True, False]


def test_only_output_actuals_are_touched():
    """R1/R2 sensor dropout kurali; bir proses degiskeninin 0 olmasi gecerli olcumdur."""
    df, log = clean.clean(_mini([0.0, 10.0]))

    assert log["actual_cols"] == [ACT]
    assert (df["Machine1.Zone1Temperature.C.Actual"] == 0).all()


def test_no_rows_dropped_and_input_not_mutated():
    raw = _mini([0.0, -1.0, 10.0])
    before = raw.copy()
    df, _ = clean.clean(raw)

    assert len(df) == len(raw)
    pd.testing.assert_frame_equal(raw, before)


# --- clean(): satir ve kolon kurallari ----------------------------------------

def test_duplicate_column_dropped_when_present():
    raw = _mini([10.0, 10.0])
    for c in clean.DROP_DUPLICATE_COLS:
        raw[c] = [20.0, 21.0]
    df, log = clean.clean(raw)

    assert not set(clean.DROP_DUPLICATE_COLS) & set(df.columns)
    assert log["R3_dropped"] == clean.DROP_DUPLICATE_COLS

    _, log = clean.clean(_mini([10.0, 10.0]))
    assert log["R3_dropped"] == []


def test_duplicate_timestamps_flag_both_sides():
    """R4 keep=False kullanir: cakismanin ilk gorunumu de isaretlenir."""
    raw = _mini([10.0] * 4)
    raw["time_stamp"] = pd.to_datetime([
        "2026-01-01 00:00:00", "2026-01-01 00:00:01",
        "2026-01-01 00:00:01", "2026-01-01 00:00:02",
    ])
    df, log = clean.clean(raw)

    assert df["flag_dup_timestamp"].tolist() == [False, True, True, False]
    assert log["R4_dup_rows"] == 2
    assert df["seq"].tolist() == [0, 1, 2, 3]


def test_downtime_requires_every_stage1_setpoint_zero():
    raw = _mini([10.0, 10.0, 10.0])
    raw["Stage1.Output.Measurement0.U.Setpoint"] = [0.0, 0.0, 10.0]
    raw["Stage1.Output.Measurement1.U.Actual"] = [5.0, 5.0, 5.0]
    raw["Stage1.Output.Measurement1.U.Setpoint"] = [0.0, 5.0, 5.0]
    df, log = clean.clean(raw)

    assert df["flag_downtime"].tolist() == [True, False, False]
    assert log["R5_downtime_rows"] == 1


# --- build_kpis(): kapsam -----------------------------------------------------

def test_full_table_is_in_scope_by_default():
    """Yardimci tablonun kendisi dogru mu -- asagidaki testler buna dayaniyor."""
    _, summary = clean.build_kpis(_full())

    assert len(summary) == schema.N_OUTPUTS
    assert (summary.in_scope == "evet").all()


@pytest.mark.parametrize("offset,in_scope", [
    (0, "evet"),    # esigin kendisi kapsam ici
    (-1, "HAYIR"),  # bir gecerli olcum eksigi kapsam disi
])
def test_valid_ratio_threshold(offset, in_scope):
    n_valid = math.ceil(N * clean.MIN_VALID_RATIO) + offset
    df = _full()
    df.loc[n_valid:, "Stage1.Output.Measurement3.U.Actual"] = np.nan
    _, summary = clean.build_kpis(df)

    r = _row(summary, "Stage1.M3")
    assert r.n_valid == n_valid
    assert r.in_scope == in_scope
    if in_scope == "HAYIR":
        assert r.scope_reason.endswith("(R6)")
        assert r.error_type == "-"


def test_meaningless_setpoint_is_out_of_scope():
    """R7: gurultuden kucuk bir setpoint'e bolen oranlar patlar; output kapsam disi."""
    df = _full()
    df["Stage2.Output.Measurement6.U.Setpoint"] = 0.01
    df["Stage2.Output.Measurement6.U.Actual"] = 0.01 + 0.5 + _pattern()
    _, summary = clean.build_kpis(df)

    r = _row(summary, "Stage2.M6")
    assert not r.sp_meaningful
    assert np.isnan(r.bias_pct)
    assert r.scope_reason.endswith("(R7)")
    assert (r.in_scope, r.error_type) == ("HAYIR", "-")


def test_downtime_setpoint_excluded_from_deviation():
    """Durus blogunda setpoint 0; sapma 'olcum - 0' diye hesaplanirsa KPI'lar sisar."""
    df = _full()
    df.loc[:9, "Stage1.Output.Measurement0.U.Setpoint"] = 0.0
    kpi, summary = clean.build_kpis(df)

    assert kpi.loc[:9, "Stage1.M0.dev"].isna().all()
    assert kpi.loc[10:, "Stage1.M0.dev"].notna().all()
    assert _row(summary, "Stage1.M0").setpoint == 10.0


# --- build_kpis(): bias / variability ayrimi ----------------------------------

@pytest.mark.parametrize("share,expected", [
    (clean.BIAS_BAND[1] + 5, "bias"),
    (sum(clean.BIAS_BAND) / 2, "belirsiz"),
    (clean.BIAS_BAND[0] - 5, "variability"),
])
def test_error_type_uses_bias_band(share, expected):
    std = float(pd.Series(_pattern()).std())
    # bias_share_pct = 100 * b^2 / (b^2 + std^2) denkleminin b icin cozumu
    bias = std * math.sqrt(share / (100 - share))
    df = _full()
    df["Stage1.Output.Measurement4.U.Actual"] = 10.0 + bias + _pattern()
    _, summary = clean.build_kpis(df)

    r = _row(summary, "Stage1.M4")
    assert r.bias_share_pct == pytest.approx(share, abs=0.5)
    assert r.error_type == expected


def test_rmse_splits_into_bias_and_spread():
    """RMSE^2 = bias^2 + populasyon varyansi; dev_std orneklem std'si (ddof=1)."""
    df = _full()
    df["Stage1.Output.Measurement2.U.Actual"] = 10.0 + 0.7 + 0.3 * _pattern()
    _, summary = clean.build_kpis(df)

    r = _row(summary, "Stage1.M2")
    pop_var = r.dev_std ** 2 * (r.n_valid - 1) / r.n_valid
    assert r.rmse ** 2 == pytest.approx(r.bias ** 2 + pop_var, rel=1e-3)


# --- esik tutarliligi ---------------------------------------------------------

def test_audit_and_clean_share_valid_ratio():
    """
    audit.py 'modellenemez' listesini, clean.py R6 kapsamini ayni esikle
    ciziyor. Ikisi ayrisirsa rapor 01 ile rapor 02 farkli output'lari disarida
    birakir.
    """
    assert clean.MIN_VALID_RATIO == audit.MIN_VALID_RATIO


def test_committed_kpi_summary_matches_thresholds():
    """
    reports/output_kpi_summary.csv repoya islenmis bir cikti. Esiklerden biri
    degisip rapor yeniden uretilmezse tablodaki kapsam ve siniflandirma kodla
    celisir; bu test o celiskiyi yakalar.
    """
    summary = pd.read_csv(ROOT / "reports" / "output_kpi_summary.csv")
    lo, hi = clean.BIAS_BAND

    assert len(summary) == schema.N_OUTPUTS
    for r in summary.itertuples():
        in_scope = (r.valid_pct >= clean.MIN_VALID_RATIO * 100
                    and r.sp_over_std >= clean.MIN_SETPOINT_TO_STD)
        assert (r.in_scope == "evet") == in_scope, r.output

        if not in_scope:
            expected = "-"
        elif r.bias_share_pct > hi:
            expected = "bias"
        elif r.bias_share_pct < lo:
            expected = "variability"
        else:
            expected = "belirsiz"
        assert r.error_type == expected, r.output
