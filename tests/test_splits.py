"""
splits.py testleri.

Bu modul projenin en kritik iddiasini tasiyor: modeller gelecekten bilgi
gormeden degerlendiriliyor (K5). Sizinti sessizdir -- R2 yukselir, hicbir
hata mesaji cikmaz, sonuc "basarili" gorunur. Bu yuzden bolme fonksiyonlari
ozellik olarak test ediliyor: train'in her satiri test'ten once gelmeli ve
aralarinda tam embargo kadar satir bulunmali.
"""
import numpy as np
import pandas as pd
import pytest
import splits


def _blocks(block, n=5000, seed=0):
    """Her degeri `block` kez tekrarlayan seri: otokorelasyon ~block kadar surer."""
    rng = np.random.default_rng(seed)
    return pd.Series(np.repeat(rng.normal(size=n // block + 1), block)[:n])


# --- blocked_split ------------------------------------------------------------

def test_blocked_split_puts_test_at_the_end():
    train, test = splits.blocked_split(1000, test_frac=0.30)

    assert train.tolist() == list(range(0, 700))
    assert test.tolist() == list(range(700, 1000))


def test_embargo_shrinks_train_not_test():
    train0, test0 = splits.blocked_split(1000, 0.30, embargo=0)
    train, test = splits.blocked_split(1000, 0.30, embargo=50)

    assert test.tolist() == test0.tolist()   # test blogu yerinde kalir
    assert train[-1] == train0[-1] - 50      # kesilen yalnizca train'in sonu


@pytest.mark.parametrize("n", [200, 1000, 14088])
@pytest.mark.parametrize("frac", [0.2, 0.3, 0.5])
@pytest.mark.parametrize("embargo", [0, 1, 49, 300])
def test_blocked_split_never_leaks(n, frac, embargo):
    """Train tamamen test'ten once; arada tam embargo kadar satir var."""
    train, test = splits.blocked_split(n, frac, embargo)

    assert not set(train) & set(test)
    assert test.max() == n - 1
    if len(train):
        assert train.max() < test.min()
        assert test.min() - train.max() - 1 == embargo


def test_blocked_split_can_leave_train_empty():
    """
    Embargo test blogunun basini asarsa train bos doner. Fonksiyon hata
    vermez; uzunluk kontrolu cagiran tarafta (train.py: len(tr) < 200).
    """
    train, test = splits.blocked_split(100, 0.30, embargo=200)

    assert len(train) == 0
    assert test.tolist() == list(range(70, 100))


# --- blocked_kfold (walk-forward) ---------------------------------------------

def test_kfold_trains_only_on_the_past():
    """Walk-forward'in tanimi: train her zaman test blogunun ONCESI."""
    folds = list(splits.blocked_kfold(6000, k=5, embargo=0))

    assert len(folds) == 5
    for train, test in folds:
        assert train[0] == 0
        assert train.max() < test.min()


def test_kfold_windows_move_forward_and_train_grows():
    folds = list(splits.blocked_kfold(6000, k=5, embargo=0))
    tests = [te for _, te in folds]
    trains = [tr for tr, _ in folds]

    for earlier, later in zip(tests, tests[1:]):
        assert earlier.max() < later.min()     # test penceresi ileri kayar
    for earlier, later in zip(trains, trains[1:]):
        assert len(earlier) < len(later)       # train ileriye dogru buyur


def test_kfold_test_blocks_are_equal_sized_and_contiguous():
    folds = list(splits.blocked_kfold(6000, k=5))

    assert {len(te) for _, te in folds} == {1000}
    covered = np.concatenate([te for _, te in folds])
    assert covered.tolist() == list(range(1000, 6000))


@pytest.mark.parametrize("n,k,embargo", [
    (6000, 5, 0),
    (6000, 5, 49),
    (9876, 5, 354),    # validation.py'nin gercek fold buyuklugu
    (2000, 3, 10),
    (14088, 5, 49),
])
def test_kfold_never_leaks(n, k, embargo):
    folds = list(splits.blocked_kfold(n, k, embargo))

    assert folds
    for train, test in folds:
        assert not set(train) & set(test)
        assert train.max() < test.min()
        assert test.min() - train.max() - 1 == embargo


def test_kfold_skips_folds_without_enough_data():
    """Train blogu 50 satirin altina duserse fold uretilmez (embargo=60 -> ilk fold 40 satir)."""
    assert len(list(splits.blocked_kfold(600, k=5, embargo=0))) == 5
    assert len(list(splits.blocked_kfold(600, k=5, embargo=60))) == 4
    assert list(splits.blocked_kfold(100, k=5)) == []


# --- baseline'lar -------------------------------------------------------------

def test_baseline_mean_is_the_train_mean():
    pred = splits.baseline_mean(np.array([1.0, 2.0, 3.0, np.nan]), 3)

    assert pred.tolist() == [2.0, 2.0, 2.0]


def test_persistence_predicts_the_previous_observed_value():
    pred = splits.baseline_persistence(np.array([10.0, 11.0, 12.0, 13.0]),
                                       np.array([2, 3]))

    assert pred.tolist() == [11.0, 12.0]


def test_persistence_carries_the_last_valid_value_over_gaps():
    pred = splits.baseline_persistence(np.array([1.0, np.nan, np.nan, 5.0]),
                                       np.array([2, 3]))

    assert pred.tolist() == [1.0, 1.0]


def test_persistence_does_not_peek_at_the_future():
    """
    Baseline yalnizca bir onceki gozlemi kullanmali. Test penceresinden SONRAKI
    degerler degistiginde tahminler degismiyorsa ileriye bakmiyor demektir.
    """
    y = np.arange(100, dtype=float)
    test_idx = np.arange(50, 60)
    before = splits.baseline_persistence(y, test_idx)

    tampered = y.copy()
    tampered[60:] = -999.0

    assert splits.baseline_persistence(tampered, test_idx).tolist() == before.tolist()


# --- metrikler ----------------------------------------------------------------

def test_metrics_on_a_perfect_prediction():
    y = np.arange(1.0, 7.0)

    assert splits.metrics(y, y.copy()) == dict(n=6, mae=0.0, rmse=0.0, r2=1.0)


def test_metrics_drops_pairs_with_nan():
    y_true = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0])
    y_pred = np.array([1.0, 2.0, 3.0, np.nan, 5.0, 6.0])

    assert splits.metrics(y_true, y_pred)["n"] == 4


def test_metrics_needs_five_points():
    y = np.arange(4, dtype=float)
    m = splits.metrics(y, y.copy())

    assert m["n"] == 4
    assert np.isnan(m["mae"]) and np.isnan(m["rmse"]) and np.isnan(m["r2"])


def test_r2_is_undefined_for_a_constant_target():
    """R2'nin paydasi test blogunun kendi varyansi; sabit seride tanimsiz."""
    y = np.full(10, 3.0)

    assert np.isnan(splits.metrics(y, y + 0.1)["r2"])


@pytest.mark.parametrize("model_rmse,ref_rmse,expected", [
    (1.0, 1.0, 0.0),     # baseline kadar iyi
    (0.5, 1.0, 0.5),     # baseline'dan iyi
    (2.0, 1.0, -1.0),    # baseline'dan kotu
])
def test_skill_score(model_rmse, ref_rmse, expected):
    assert splits.skill_score(model_rmse, ref_rmse) == pytest.approx(expected)


@pytest.mark.parametrize("model_rmse,ref_rmse", [
    (1.0, 0.0), (1.0, np.nan), (np.nan, 1.0),
])
def test_skill_score_is_undefined_without_a_reference(model_rmse, ref_rmse):
    assert np.isnan(splits.skill_score(model_rmse, ref_rmse))


# --- embargo genisligi --------------------------------------------------------

def test_decay_lag_grows_with_the_length_of_memory():
    noise = pd.Series(np.random.default_rng(0).normal(size=5000))

    assert splits.acf_decay_lag(noise) == 1   # hafizasiz seri: lag-1'de biter
    assert splits.acf_decay_lag(_blocks(20)) < splits.acf_decay_lag(_blocks(100))


def test_higher_threshold_gives_shorter_embargo():
    x = _blocks(100)

    assert splits.acf_decay_lag(x, threshold=0.5) <= splits.acf_decay_lag(x, threshold=0.2)


def test_censored_result_is_flagged():
    """
    Seri tarama siniri icinde esigin altina inmiyorsa donen sayi bir olcum
    degil, taramanin durdugu yerdir; return_censored bunu ayirt eder.
    Tarama siniri: min(max_lag, len(x) // 3).
    """
    x = pd.Series(np.arange(600, dtype=float))

    assert splits.acf_decay_lag(x, threshold=0.05, return_censored=True) == (200, True)
    assert splits.acf_decay_lag(x, threshold=0.05, max_lag=5,
                                return_censored=True) == (5, True)
    # ayni seri, gevsek esikte gercekten olculuyor -- bayrak ayrimi yapiyor
    assert splits.acf_decay_lag(x, threshold=0.2, return_censored=True)[1] is False


@pytest.mark.parametrize("x", [
    pd.Series(np.arange(99, dtype=float)),   # 100 gozlemden az
    pd.Series(np.full(500, 7.0)),            # sabit seri: varyans yok
])
def test_decay_lag_returns_zero_when_undefined(x):
    assert splits.acf_decay_lag(x) == 0


def test_suggest_embargo_is_the_median_of_usable_columns():
    df = pd.DataFrame({
        "a": _blocks(20),
        "b": _blocks(100),
        "c": _blocks(60),
        "sabit": np.full(5000, 1.0),   # sonumlenme lag'i 0 -> hesaba katilmaz
    })
    lags = sorted(splits.acf_decay_lag(df[c]) for c in ("a", "b", "c"))

    assert splits.suggest_embargo(df, list(df.columns)) == lags[1]


def test_suggest_embargo_counts_censored_columns_as_measured():
    """
    suggest_embargo sansur bayragina bakmaz; sansurlu kolon tarama siniriyla
    hesaba girer. Sinir gercek sonumlenmeden KUCUK oldugu icin bu, embargoyu
    kucultmez -- medyani yukari ceker, yani daha temkinli bir embargo verir.
    Gercek veride 24 karar degiskeninin 6'si sansurlu (bkz. BULGU V0).
    """
    df = pd.DataFrame({
        "trend1": np.arange(600, dtype=float),
        "trend2": np.arange(600, dtype=float) ** 1.5,
        "noise": np.random.default_rng(0).normal(size=600),
    })
    censored = [splits.acf_decay_lag(df[c], threshold=0.05, return_censored=True)[1]
                for c in df.columns]

    assert censored.count(True) == 2
    assert splits.suggest_embargo(df, list(df.columns), threshold=0.05) == 600 // 3


def test_suggest_embargo_without_usable_columns():
    df = pd.DataFrame({"a": np.full(200, 1.0)})

    assert splits.suggest_embargo(df, ["a", "olmayan_kolon"]) == 0
