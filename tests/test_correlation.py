"""
correlation.py testleri.

Raporun en guclu iddiasi burada: ciftlerin buyuk cogunlugu "anlamli"
GORUNUYOR ama degil. Bu hukum iki duzeltmeye dayaniyor -- efektif ornek
buyuklugu (Bartlett n_eff) ve Benjamini-Hochberg FDR. Ikisinden birindeki
sessiz bir hata, rapordaki butun anlamlilik ifadelerini gecersiz kilar.
Testler ham veriye dokunmaz; formuller elle hesaplanabilen girdilerle
sabitlenir.
"""
import numpy as np
import pandas as pd
import pytest

import correlation
from conftest import ROOT


def _autocorrelated(n=2000, rho=0.99, seed=0):
    """AR(1) seri: ardisik gozlemler bagimsiz degil."""
    rng = np.random.default_rng(seed)
    e = rng.normal(size=n)
    x = np.empty(n)
    x[0] = e[0]
    for i in range(1, n):
        x[i] = rho * x[i - 1] + e[i]
    return pd.Series(x)


def _committed_table():
    return pd.read_csv(ROOT / "reports" / "correlation_table.csv")


# --- Benjamini-Hochberg FDR ---------------------------------------------------

def test_bh_fdr_hand_computed():
    """q_i = min_{j >= i} p_j * m / j (p'ye gore sirali)."""
    q = correlation.bh_fdr(np.array([0.001, 0.5]))

    assert q.tolist() == pytest.approx([0.002, 0.5])


def test_bh_fdr_enforces_monotonicity():
    """Ham p*m/i dizisi azalabilir; BH bunu sondan kumulatif minimumla duzeltir."""
    # ham: [0.4*2/1, 0.5*2/2] = [0.8, 0.5] -> duzeltilmis: [0.5, 0.5]
    q = correlation.bh_fdr(np.array([0.4, 0.5]))

    assert q.tolist() == pytest.approx([0.5, 0.5])


def test_bh_fdr_keeps_input_order():
    p = np.array([0.5, 0.001, 0.2])
    q = correlation.bh_fdr(p)

    assert np.argsort(q).tolist() == np.argsort(p).tolist()
    assert q[1] == pytest.approx(correlation.bh_fdr(np.sort(p))[0])


def test_bh_fdr_never_reports_less_than_the_raw_p():
    """Duzeltmenin yonu tek tarafli: q >= p, ve q hicbir zaman 1'i asmaz."""
    p = np.random.default_rng(0).uniform(size=500)
    q = correlation.bh_fdr(p)

    assert np.all(q >= p - 1e-12)
    assert np.all(q <= 1.0)


def test_bh_fdr_scales_with_the_number_of_tests():
    """Ayni p-degeri, daha cok test icinde daha az anlamlidir."""
    q_few = correlation.bh_fdr(np.array([0.01, 0.9]))
    q_many = correlation.bh_fdr(np.array([0.01] + [0.9] * 99))

    assert q_many[0] > q_few[0]


def test_bh_fdr_ignores_nan_p_values():
    """
    Test edilemeyen cift m'e sayilmaz; sayilsaydi duzeltme gereksiz yere
    sertlesir ve gercek iliskiler de elenirdi.
    """
    q = correlation.bh_fdr(np.array([0.001, np.nan, 0.5]))

    assert np.isnan(q[1])
    assert q[0] == pytest.approx(0.002)   # m = 2, 3 degil


def test_bh_fdr_without_any_valid_p():
    assert np.isnan(correlation.bh_fdr(np.array([np.nan, np.nan]))).all()
    assert correlation.bh_fdr(np.array([])).shape == (0,)


# --- otokorelasyon ve efektif ornek buyuklugu ---------------------------------

def test_acf_of_an_alternating_series():
    """+1/-1 serisinde lag-1 tam ters, lag-2 tam ayni; degerler (n-k)/n ile olcekli."""
    r = correlation.acf(np.tile([1.0, -1.0], 50), 3)

    assert r == pytest.approx([-0.99, 0.98, -0.97])


def test_acf_of_a_constant_series_is_zero():
    assert correlation.acf(np.full(50, 4.0), 5).tolist() == [0.0] * 5


def test_eff_n_equals_n_without_autocorrelation():
    assert correlation.eff_n(1000, np.zeros(10), np.zeros(10)) == 1000


def test_eff_n_hand_computed():
    """n_eff = n / (1 + 2 * sum_k (1 - k/n) * rho_x(k) * rho_y(k))."""
    n = 100
    expected = n / (1 + 2 * (1 - 1 / n) * 0.5 * 0.5)

    assert correlation.eff_n(n, np.array([0.5]), np.array([0.5])) == pytest.approx(expected)


def test_eff_n_shrinks_as_autocorrelation_grows():
    n = 1000
    weak = correlation.eff_n(n, np.full(50, 0.2), np.full(50, 0.2))
    strong = correlation.eff_n(n, np.full(50, 0.9), np.full(50, 0.9))

    assert strong < weak < n


def test_lag1_only_correction_is_weaker_than_the_full_sum():
    """
    Modulun temel gerekcesi: yalnizca lag-1 kullanan surum AR(1) varsayar ve
    uzun hafizali seride otokorelasyonu eksik duzeltir (daha buyuk n_eff).
    """
    rho = np.full(500, 0.9)
    lag1_only = correlation.eff_n(14088, rho[:1], rho[:1])
    full_sum = correlation.eff_n(14088, rho, rho)

    assert lag1_only > full_sum


@pytest.mark.parametrize("rx,ry", [
    (np.full(10, 0.8), np.full(10, -0.8)),   # factor negatif
    (np.array([0.2]), np.array([-0.2])),     # 0 < factor < 1
])
def test_eff_n_is_capped_at_n(rx, ry):
    """Zit isaretli otokorelasyonlar n_eff'i gercek gozlem sayisinin uzerine cikaramaz."""
    assert correlation.eff_n(500, rx, ry) == 500


# --- korelasyon + duzeltilmis p-degeri ----------------------------------------

@pytest.mark.parametrize("x,y", [
    (pd.Series(np.arange(9.0)), pd.Series(np.arange(9.0))),          # n < 10
    (pd.Series(np.full(50, 3.0)), pd.Series(np.arange(50.0))),       # sabit seri
])
def test_corr_returns_none_when_undefined(x, y):
    assert correlation.corr_with_eff(x, y) is None


def test_corr_uses_only_rows_valid_in_both_series():
    x = pd.Series([1.0, 2.0, np.nan, 4.0] + list(np.arange(10.0, 30.0)))
    y = pd.Series([1.0, np.nan, 3.0, 4.0] + list(np.arange(10.0, 30.0)))

    assert correlation.corr_with_eff(x, y)["n"] == 22   # 24 satirin ikisi eksik


def test_perfect_correlation_is_reported_as_r_one():
    x = pd.Series(np.arange(100.0))
    res = correlation.corr_with_eff(x, 3 * x + 5)

    assert res["r"] == pytest.approx(1.0)
    assert res["p_naive"] == 0.0


def test_independent_series_keep_their_sample_size():
    rng = np.random.default_rng(0)
    res = correlation.corr_with_eff(pd.Series(rng.normal(size=1000)),
                                    pd.Series(rng.normal(size=1000)))

    assert res["n"] == 1000
    assert res["n_eff"] > 900    # hafizasiz seride duzeltmenin etkisi kucuk
    assert res["p_eff"] == pytest.approx(res["p_naive"], abs=0.05)


def test_autocorrelation_shrinks_n_eff_and_weakens_significance():
    """
    Otokorelasyonlu iki bagimsiz seride ham p cok kucuk cikar; n_eff duzeltmesi
    o guveni geri alir. Raporun butun "anlamli degil" hukumleri buna dayaniyor.
    """
    res = correlation.corr_with_eff(_autocorrelated(seed=1), _autocorrelated(seed=2))

    assert res["n_eff"] < res["n"] / 10
    assert res["p_eff"] > res["p_naive"]


def test_nlags_argument_limits_the_correction():
    """Daha az lag toplanirsa duzeltme zayiflar ve n_eff buyur."""
    x, y = _autocorrelated(seed=1), _autocorrelated(seed=2)

    assert (correlation.corr_with_eff(x, y, nlags=1)["n_eff"]
            > correlation.corr_with_eff(x, y, nlags=500)["n_eff"])


# --- rapor tutarliligi --------------------------------------------------------

def test_committed_table_flags_match_thresholds():
    """
    reports/correlation_table.csv repoya islenmis bir cikti. ALPHA ya da
    MIN_N_EFF degisip tablo yeniden uretilmezse rapordaki anlamlilik sutunlari
    kodun kuralindan ayrilir.
    """
    t = _committed_table()
    assert len(t) > 0

    assert (t.sig_naive == (t.p_naive < correlation.ALPHA)).all()
    assert (t.sig_eff == ((t.p_eff < correlation.ALPHA)
                          & (t.n_eff >= correlation.MIN_N_EFF))).all()
    assert (t.sig_fdr == ((t.q_eff < correlation.ALPHA)
                          & (t.n_eff >= correlation.MIN_N_EFF))).all()


def test_committed_table_corrections_point_one_way():
    """Her cift icin n_eff <= n ve q >= p; ikisi de duzeltmenin yonu."""
    t = _committed_table().dropna(subset=["p_eff", "q_eff"])
    assert len(t) > 0

    assert (t.n_eff <= t.n).all()
    assert (t.q_eff >= t.p_eff - 1e-4).all()   # ikisi de 4 basamaga yuvarli


def test_committed_table_corrections_are_nested():
    """
    Iki duzeltme de yalnizca eleyebilir: n_eff <= n oldugu icin p_eff >= p_naive,
    q >= p oldugu icin de FDR sonrasi kalanlar n_eff ile anlamli olanlarin alt
    kumesidir. Rapordaki "ham -> n_eff -> n_eff+FDR" daralmasi bu ozelligin
    sayisal hali; zincir bozulursa duzeltmelerden biri yon degistirmis demektir.
    """
    t = _committed_table()
    naive = set(t.index[t.sig_naive])
    eff = set(t.index[t.sig_eff])
    fdr = set(t.index[t.sig_fdr])

    assert fdr <= eff <= naive
    assert len(fdr) < len(eff) < len(naive)
