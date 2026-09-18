"""
optimize.py testleri.

Faz 4'un butun onerileri iki kisitla ayakta duruyor:

  1. Arama uzayi gozlenen min-max araligiyla sinirli (K1: ekstrapolasyon yok).
     Bu kisit sessizce ihlal edilirse rapor, hicbir gozleme dayanmayan bir
     calisma noktasi onerir -- ve bu hicbir hata vermez.
  2. Optimizasyon yalnizca gercekten oynatilmis parametreler (K7) ve modelin
     bir sey yakaladigi output'lar uzerine kurulur.

Testler sklearn egitmiyor: model yerine tahminini bildigimiz bir vekil
kullaniliyor, boylece aramanin ne sectigi elle dogrulanabiliyor.
"""
import re

import numpy as np
import optimize
import pandas as pd
import pytest
from conftest import ROOT

RPM = "Machine1.MotorRPM.C.Actual"
PRESSURE = "Machine4.Pressure.C.Actual"
CPPS = [RPM, PRESSURE]


class _StubModel:
    """predict()'i bilinen vekil model."""

    def __init__(self, fn):
        self._fn = fn

    def predict(self, X):
        return np.asarray(self._fn(X), dtype=float)


def _observed(n=500, seed=0):
    """Gozlenen veri: arama yalnizca bu araliklarin icinden ornekleyebilir."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        RPM: rng.uniform(10.0, 12.0, n),
        PRESSURE: rng.uniform(14.0, 25.0, n),
    })


def _regions_frame(n, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        PRESSURE: rng.uniform(14, 25, n),
        "Stage2.M9.dev": rng.normal(0, 1, n),
    })


# --- karar degiskeni sinirlari -------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 7])
def test_search_result_is_inside_every_observed_range(seed):
    """K1: onerilen nokta her parametrede gozlenen araligin icinde kalmali."""
    Xv = _observed()
    mdl = _StubModel(lambda X: X[RPM] * 0 + 1.0)   # sabit tahmin: secim rastgele
    point, _ = optimize.model_search(mdl, Xv, CPPS, np.random.default_rng(seed))

    for c in CPPS:
        assert Xv[c].min() <= point[c] <= Xv[c].max()


def test_search_stops_at_the_observed_maximum():
    """
    Model ne kadar buyuk deger isterse istesin arama gozlenen maksimumda
    durur. Kisit baglayici oldugunda gorulen tek sey budur.
    """
    Xv = _observed()
    mdl = _StubModel(lambda X: X[PRESSURE] - 1e6)   # buyudukce |tahmin| kuculur
    point, _ = optimize.model_search(mdl, Xv, CPPS, np.random.default_rng(0))

    hi = Xv[PRESSURE].max()
    assert point[PRESSURE] <= hi
    assert point[PRESSURE] > hi - 0.05   # sinira dayaniyor ama asmiyor


def test_search_picks_the_smallest_absolute_prediction():
    """Amac sapmayi sifira yaklastirmak: |tahmin| en kucuk aday secilir."""
    Xv = _observed()
    mdl = _StubModel(lambda X: X[PRESSURE] - 20.0)
    point, pred = optimize.model_search(mdl, Xv, CPPS, np.random.default_rng(0))

    assert point[PRESSURE] == pytest.approx(20.0, abs=0.05)
    assert pred == pytest.approx(0.0, abs=0.05)


def test_search_is_reproducible_for_a_given_seed():
    Xv = _observed()
    first, _ = optimize.model_search(_StubModel(lambda X: X[RPM] - 11.0), Xv,
                                     CPPS, np.random.default_rng(3))
    again, _ = optimize.model_search(_StubModel(lambda X: X[RPM] - 11.0), Xv,
                                     CPPS, np.random.default_rng(3))

    assert first.tolist() == again.tolist()


def test_never_moved_parameter_collapses_to_its_single_value():
    """Hic oynatilmamis parametrede aralik tek nokta; arama onu tekrarlar."""
    Xv = _observed()
    Xv[RPM] = 11.0
    mdl = _StubModel(lambda X: X[PRESSURE] - 20.0)
    point, _ = optimize.model_search(mdl, Xv, CPPS, np.random.default_rng(0))

    assert point[RPM] == 11.0


# --- kapsam: hangi parametre, hangi output ------------------------------------

def test_active_cpps_keeps_only_parameters_that_actually_moved():
    """K7: CV esigi altinda kalan parametre optimizasyona girmez."""
    n = 200
    df = pd.DataFrame({
        RPM: np.linspace(10, 12, n),                                   # CV %5
        "Machine2.Zone1Temperature.C.Actual": np.linspace(100, 100.5, n),  # CV %0.1
        "Machine3.MaterialPressure.U.Actual": np.linspace(1, 50, n),   # measured
    })

    assert optimize.active_cpps(df) == [RPM]


def test_target_outputs_keeps_only_outputs_that_beat_persistence(tmp_path, monkeypatch):
    """
    Optimizasyon yalnizca modelin gercekten bir sey yakaladigi output'lara
    kurulur. Ayrica yalnizca `controlled` girdi seti sayilir: gecmis degerlerle
    (ctrl+lag) elde edilen basari optimizasyonun dayanagi degildir.
    """
    path = tmp_path / "modeling_results.csv"
    pd.DataFrame({
        "output": ["A", "A", "B", "C"],
        "feature_set": ["controlled", "ctrl+lag", "controlled", "controlled"],
        "model": ["rf", "rf", "hgb", "rf"],
        "skill_vs_pers": [0.3, 0.9, -0.1, 0.1],
    }).to_csv(path, index=False)
    monkeypatch.setattr(optimize, "RESULTS", path)

    out = optimize.target_outputs()

    assert out.output.tolist() == ["A", "C"]          # B persistence'i gecemedi
    assert out.skill_vs_pers.tolist() == [0.3, 0.1]   # ctrl+lag satiri sayilmadi


# --- ampirik bolgeler ---------------------------------------------------------

@pytest.mark.parametrize("n,rows", [(1000, 4), (400, 0)])
def test_empirical_regions_drops_bins_below_the_minimum(n, rows):
    """
    MIN_BIN_N altindaki dilim raporlanmaz: birkac gozlemden bolge hukmu
    cikarmak, gurultuyu bulgu diye yazmak olur.
    """
    out = optimize.empirical_regions(_regions_frame(n), "Stage2.M9", [PRESSURE])

    assert len(out) == rows


def test_empirical_regions_reports_bin_size_and_deviation():
    out = optimize.empirical_regions(_regions_frame(1000), "Stage2.M9", [PRESSURE])

    assert set(out.parametre) == {"Machine4.Pressure"}
    assert (out.n >= optimize.MIN_BIN_N).all()
    assert (out.mutlak_sapma >= 0).all()


# --- rapor tutarliligi --------------------------------------------------------

def _observed_ranges():
    """07_optimization_report.md'deki 'gozlenen aralik' tablosu."""
    text = (ROOT / "reports" / "07_optimization_report.md").read_text(encoding="utf-8")
    # Yalnizca kapsam bolumu: ampirik tablolarda da ayni kalipta satirlar var.
    section = text.split("## Kapsam")[1].split("## Yontem")[0]
    pattern = re.compile(r"\|\s*`([^`]+)`\s*\|\s*([\d.]+)\s*–\s*([\d.]+)\s*\|")
    return {m.group(1): (float(m.group(2)), float(m.group(3)))
            for m in (pattern.match(line) for line in section.splitlines()) if m}


def test_committed_points_stay_inside_the_observed_ranges():
    """
    Rapordaki her oneri, ayni raporun yazdigi gozlenen araligin icinde olmali.
    Disari tasan bir satir, hicbir gozleme dayanmayan bir calisma noktasinin
    onerildigi anlamina gelir (K1). Iki dosya da 2 basamaga yuvarladigi icin
    sinirlarda 0.01'lik tolerans birakildi.
    """
    ranges = _observed_ranges()
    points = pd.read_csv(ROOT / "reports" / "optimization_points.csv")

    assert ranges, "rapordan aralik tablosu okunamadi"
    assert set(ranges) <= set(points.columns)

    # itertuples kullanilmiyor: noktali kolon adlari konumsal adlara cevriliyor.
    for _, row in points.iterrows():
        for param, (lo, hi) in ranges.items():
            value = float(row[param])
            assert lo - 0.01 <= value <= hi + 0.01, (row.output, param, value)


# --- cozum bulunamadiginda ----------------------------------------------------

def test_no_active_parameter_is_reported_clearly():
    """Hicbir parametre oynatilmamissa arama uzayi tek noktaya coker."""
    with pytest.raises(optimize.NoSolutionError, match="aktif karar degiskeni yok"):
        optimize.check_preconditions([], pd.DataFrame({"output": ["A"]}))


def test_no_target_output_is_reported_clearly():
    """Modelin bir sey yakaladigi output yoksa arama gurultuyu optimize eder."""
    with pytest.raises(optimize.NoSolutionError, match="hedef output yok"):
        optimize.check_preconditions([RPM], pd.DataFrame())


def test_preconditions_pass_when_both_exist():
    optimize.check_preconditions([RPM], pd.DataFrame({"output": ["A"]}))


def test_main_stops_before_searching_when_there_is_no_target(tmp_path, monkeypatch):
    """
    Zemin yoksa main() arama yapmadan duruyor. Eskiden ilerler ve bos
    tablolarla pandas'tan anlasilmaz bir hata alirdi.
    """
    proc = tmp_path / "clean_v1.csv"
    _observed(600).to_csv(proc, index=False)
    results = tmp_path / "modeling_results.csv"
    pd.DataFrame({
        "output": ["Stage2.M9"],
        "feature_set": ["controlled"],
        "model": ["rf"],
        "skill_vs_pers": [-0.4],          # persistence gecilemedi
    }).to_csv(results, index=False)
    monkeypatch.setattr(optimize, "PROC", proc)
    monkeypatch.setattr(optimize, "RESULTS", results)

    with pytest.raises(optimize.NoSolutionError, match="persistence"):
        optimize.main()


def test_report_survives_when_nothing_could_be_compared(tmp_path, monkeypatch):
    """
    Ampirik ve duyarlilik tablolari hic uretilemediginde rapor yine de
    yazilmali. Bu durumda eskiden iki ayri cokme vardi: bos listede
    pd.concat ValueError firlatiyordu ve hic tanimlanmamis `consistent`
    degiskeni NameError veriyordu.
    """
    out = tmp_path / "07_optimization_report.md"
    monkeypatch.setattr(optimize, "OUT", out)
    opt = pd.DataFrame([{
        "output": "Stage2.M9", "error_type": "variability", "skill_vs_pers": 0.25,
        "mevcut_bias": 0.1, "mevcut_mutlak": 0.2, "model_tahmini": 0.0,
        "Machine1.MotorRPM": 11.0,
    }])

    optimize.write_report(_observed(), opt, {}, {}, [RPM], pd.DataFrame())

    text = out.read_text(encoding="utf-8")
    assert "Faz 4" in text
    assert "yok" in text   # "tutarli parametre: yok" satiri yazilabilmis
