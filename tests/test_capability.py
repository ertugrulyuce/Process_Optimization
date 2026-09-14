"""
capability.py testleri.

I-MR kontrol limitleri ve Cp/Cpk, Faz 2'nin butun bulgularini uretiyor: hangi
output'un en dusuk capability'ye sahip oldugu, hangisinde kayma oldugu,
optimizasyonun hangi output'u hedefleyecegi. Formulde tek bir isaret ya da
sabit hatasi siralamayi hata vermeden degistirir. Testler sonucu elle
hesaplanabilen serilerle kuruldu; ham veriye dokunmaz.
"""
import math

import numpy as np
import pandas as pd
import pytest

import capability
from conftest import ROOT

# Cp/Cpk testleri icin: USL 10.2, LSL 9.8, bant genisligi 0.4, 3*sigma 0.15
SP, TOL, SIGMA = 10.0, 0.02, 0.05


def _alternating(n=20, lo=10.0, hi=12.0):
    """lo ile hi arasinda gidip gelen seri: her moving range tam hi - lo."""
    return pd.Series([lo, hi] * (n // 2))


# --- I-MR ---------------------------------------------------------------------

def test_d2_constant_matches_theory():
    """n=2 icin d2 = 2/sqrt(pi): iki normal gozlem arasi mutlak farkin beklenen degeri / sigma."""
    assert capability.D2_N2 == pytest.approx(2 / math.sqrt(math.pi), abs=1e-3)


def test_imr_sigma_and_limits_from_moving_range():
    s = capability.imr_stats(_alternating())
    sigma_st = 2.0 / capability.D2_N2

    assert s["n"] == 20
    assert s["mr_bar"] == pytest.approx(2.0)
    assert s["sigma_st"] == pytest.approx(sigma_st)
    assert s["sigma_lt"] == pytest.approx(math.sqrt(20 / 19))  # orneklem std'si
    assert s["mean"] == pytest.approx(11.0)
    assert s["ucl"] == pytest.approx(11.0 + 3 * sigma_st)
    assert s["lcl"] == pytest.approx(11.0 - 3 * sigma_st)


def test_imr_drops_nan_and_treats_remaining_as_consecutive():
    """Moving range, bir NaN boslugunun iki yanindaki gecerli olcumler arasinda alinir."""
    with_gap = capability.imr_stats(pd.Series([10.0, np.nan, 12.0] + [10.0, 12.0] * 5))
    without_gap = capability.imr_stats(pd.Series([10.0, 12.0] * 6))

    assert with_gap["n"] == without_gap["n"] == 12
    assert with_gap["mr_bar"] == pytest.approx(without_gap["mr_bar"])


@pytest.mark.parametrize("n,has_stats", [(10, True), (9, False)])
def test_imr_needs_minimum_observations(n, has_stats):
    assert bool(capability.imr_stats(pd.Series(np.arange(n, dtype=float)))) is has_stats


def test_nan_does_not_count_toward_minimum():
    assert capability.imr_stats(pd.Series(list(np.arange(9.0)) + [np.nan] * 5)) == {}


def test_out_of_control_counts_points_beyond_limits():
    # 19 moving range 1, sonuncusu 99 -> MR_bar 5.9, UCL ~20.9, LCL ~-10.5
    s = capability.imr_stats(pd.Series([0.0, 1.0] * 10 + [100.0]))

    assert s["ooc"] == 1
    assert s["ooc_pct"] == pytest.approx(100 / 21)


def test_lt_st_ratio_separates_drift_from_alternation():
    """
    Surukleyen seride ardisik farklar kucuk, genel yayilim buyuk: oran >> 1.
    Gidip gelen seride ardisik farklar genel yayilimdan buyuk: oran < 1.
    """
    drift = capability.imr_stats(pd.Series(np.arange(100, dtype=float)))
    alternating = capability.imr_stats(_alternating(n=100))

    assert drift["lt_st_ratio"] > 10
    assert alternating["lt_st_ratio"] < 1


# --- Cp / Cpk -----------------------------------------------------------------

def test_cp_is_band_width_over_six_sigma():
    cp, _ = capability.capability(SP, SIGMA, SP, TOL)
    assert cp == pytest.approx(0.4 / 0.3)


def test_cpk_equals_cp_when_centered():
    cp, cpk = capability.capability(SP, SIGMA, SP, TOL)
    assert cpk == pytest.approx(cp)


@pytest.mark.parametrize("mu,expected", [
    (10.1, 0.1 / 0.15),    # USL'e yakin
    (9.9, 0.1 / 0.15),     # LSL'e ayni mesafede: ayni sonuc
    (10.2, 0.0),           # tam limitte
    (10.3, -0.1 / 0.15),   # limit disinda: negatif
])
def test_cpk_uses_nearest_limit(mu, expected):
    cp, cpk = capability.capability(mu, SIGMA, SP, TOL)

    assert cpk == pytest.approx(expected, abs=1e-9)
    assert cp == pytest.approx(0.4 / 0.3)  # Cp merkezlemeden etkilenmez


def test_scenario_labels_match_tolerances():
    """Senaryo adi rapordaki kolon basligina yaziliyor; icindeki yuzde degerle ayni olmali."""
    for label, tol in capability.SPEC_SCENARIOS.items():
        assert f"+/-%{tol * 100:g})" in label


# --- rapor tutarliligi --------------------------------------------------------

def test_committed_table_matches_formulas():
    """
    reports/capability_table.csv repoya islenmis bir cikti. Formul ya da sabit
    degisip tablo yeniden uretilmezse rapor koddan ayrilir. Tablo istatistikleri
    4, Cp/Cpk'yi 2 basamaga yuvarliyor; toleranslar o yuvarlamayi karsilar.
    """
    table = pd.read_csv(ROOT / "reports" / "capability_table.csv")
    assert len(table) > 0

    for r in table.to_dict("records"):
        out = r["output"]
        assert r["sigma_st"] == pytest.approx(r["mr_bar"] / capability.D2_N2, abs=1e-4), out
        assert r["ucl"] == pytest.approx(r["mean"] + 3 * r["sigma_st"], abs=3e-4), out
        assert r["lcl"] == pytest.approx(r["mean"] - 3 * r["sigma_st"], abs=3e-4), out

        for label, tol in capability.SPEC_SCENARIOS.items():
            cp, cpk = capability.capability(r["mean"], r["sigma_st"], r["setpoint"], tol)
            assert r[f"Cp {label}"] == pytest.approx(cp, rel=1e-2, abs=0.01), (out, label)
            assert r[f"Cpk {label}"] == pytest.approx(cpk, rel=1e-2, abs=0.01), (out, label)
