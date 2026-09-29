"""
Faz 3 - Zaman-sirali bolme ve naive baseline'lar.

Bu modul projenin en kolay hata yapilan noktasini kapatiyor (K5).

NEDEN RASTGELE SPLIT YASAK
--------------------------
Karar degiskenlerinde lag-1 otokorelasyon medyani ~0.99. Rastgele split'te test satirinin komsulari
train'de olur; model "tahmin" degil "hatirlama" yapar ve R2 sahte sekilde
yukselir. Bu veri setiyle yapilan calismalarda en yaygin hata budur.

BLOKLU SPLIT + EMBARGO
----------------------
Train ve test zaman ekseninde ardisik bloklardir. Aralarina bir EMBARGO
(tampon) konur: sinirdaki test satirlarinin komsulari da train'de olmasin.
Embargo genisligi otokorelasyonun sonumlendigi mesafeye gore secilir, keyfi
degil -- `suggest_embargo()` bunu veriden hesaplar.

NAIVE BASELINE NEDEN SART
-------------------------
Otokorelasyonlu bir seride "son gozlenen degeri tekrarla" (persistence)
tahmini cok gucludur. Model bunu gecemiyorsa hicbir sey ogrenmemis demektir.
R2'yi sabit-ortalama baseline'ina gore raporlamak bu durumda yaniltir; bu
yuzden asagida her iki baseline da hesaplanir ve model ikisiyle de karsilastirilir.
"""
import numpy as np
import pandas as pd


def acf_decay_lag(x: pd.Series, threshold=0.2, max_lag=2000,
                  return_censored=False):
    """
    Otokorelasyonun `threshold` altina indigi ilk lag.

    Embargo genisligi icin kullanilir: bu mesafeden uzaktaki gozlemler
    pratik olarak bagimsiz sayilabilir.

    DIKKAT - SANSURLU SONUC: bazi seriler `max_lag` icinde esigin altina hic
    inmiyor. O durumda donen deger bir OLCUM degil, taramanin ust siniridir;
    gercek sonumlenme daha uzakta olabilir. `return_censored=True` ile bu
    ayirt edilebilir -- yoksa "2000" sayisi gercek bir tahmin sanilir.
    """
    v = x.dropna()
    if len(v) < 100:
        return (0, False) if return_censored else 0
    a = v.to_numpy(float)
    a = a - a.mean()
    denom = float(np.dot(a, a))
    if denom == 0:
        return (0, False) if return_censored else 0
    cap = min(max_lag, len(a) // 3)
    for lag in range(1, cap):
        r = float(np.dot(a[:-lag], a[lag:])) / denom
        if abs(r) < threshold:
            return (lag, False) if return_censored else lag
    return (cap, True) if return_censored else cap


def suggest_embargo(df: pd.DataFrame, cols, threshold=0.2) -> int:
    """Kolonlarin otokorelasyon sonumlenme mesafelerinin medyani."""
    lags = [acf_decay_lag(df[c], threshold) for c in cols if c in df.columns]
    lags = [x for x in lags if x > 0]
    return int(np.median(lags)) if lags else 0


def blocked_split(n: int, test_frac=0.30, embargo=0):
    """
    Tek bir zaman-sirali bolme: [train][embargo][test].

    Test HER ZAMAN serinin sonundadir -- gercek kullanimda model gecmisle
    egitilip gelecege uygulanacagi icin.
    """
    n_test = int(n * test_frac)
    test_start = n - n_test
    train_end = max(0, test_start - embargo)
    train = np.arange(0, train_end)
    test = np.arange(test_start, n)
    return train, test


def blocked_kfold(n: int, k=5, embargo=0):
    """
    Zaman-sirali k-fold: her fold'da test blogu ileriye kayar, train yalnizca
    o blogun ONCESIDIR (ileriye dogru zincirleme / walk-forward).

    Klasik KFold burada kullanilamaz: gelecekteki veriyle egitip gecmisi
    tahmin etmek sizinti olur.
    """
    fold = n // (k + 1)
    for i in range(1, k + 1):
        test_start = i * fold
        test_end = min(n, (i + 1) * fold)
        train_end = max(0, test_start - embargo)
        if train_end < 50 or test_end - test_start < 20:
            continue
        yield np.arange(0, train_end), np.arange(test_start, test_end)


# --------------------------------------------------------------------------
# Baseline'lar
# --------------------------------------------------------------------------

def baseline_mean(y_train: np.ndarray, n_test: int) -> np.ndarray:
    """Sabit tahmin: train ortalamasi. R2'nin tanim geregi 0 oldugu nokta."""
    return np.full(n_test, np.nanmean(y_train))


def baseline_persistence(y_full: np.ndarray, test_idx: np.ndarray) -> np.ndarray:
    """
    Persistence: her test noktasi icin bir onceki GOZLENEN degeri tahmin et.

    NaN'lar atlanarak son gecerli deger tasinir (forward fill mantigi).
    Otokorelasyonlu seride cok guclu bir rakiptir.
    """
    s = pd.Series(y_full).ffill()
    prev = s.shift(1).to_numpy()
    return prev[test_idx]


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    m = ~(np.isnan(y_true) | np.isnan(y_pred))
    yt, yp = y_true[m], y_pred[m]
    if len(yt) < 5:
        return dict(n=len(yt), mae=np.nan, rmse=np.nan, r2=np.nan)
    err = yt - yp
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((yt - yt.mean()) ** 2))
    return dict(
        n=len(yt),
        mae=float(np.mean(np.abs(err))),
        rmse=float(np.sqrt(np.mean(err ** 2))),
        r2=1 - ss_res / ss_tot if ss_tot > 0 else np.nan,
    )


def skill_score(model_rmse: float, ref_rmse: float) -> float:
    """
    Bir baseline'a gore beceri skoru: 1 - RMSE_model / RMSE_ref.

    0 -> baseline kadar iyi. Negatif -> baseline'dan KOTU.
    Otokorelasyonlu veride asil olcut budur, ham R2 degil.
    """
    if not ref_rmse or np.isnan(ref_rmse) or np.isnan(model_rmse):
        return np.nan
    return 1 - model_rmse / ref_rmse
