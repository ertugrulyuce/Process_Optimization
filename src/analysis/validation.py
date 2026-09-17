"""
Faz 5 - Validation ve Dayaniklilik.

NE TEST EDILIYOR
----------------
Faz 3 ve 4'un butun sonuclari TEK bir bolmeye dayaniyordu: son %30 test.
Eger o donem atipikse, tum sonuclar yaniltici olur. Bu script ayni sorulari
zaman ekseni boyunca ILERLEYEN birden fazla pencerede tekrar soruyor
(walk-forward) ve sonuclarin fold'dan fold'a ne kadar oynadigina bakiyor.

Uc ayri dayaniklilik testi:

  V1  Model becerisi fold'lar arasinda tutarli mi?
      Tek split'te pozitif cikan skill, baska donemlerde de pozitif mi?

  V2  Ampirik optimizasyon bulgusu (Faz 4) zamanda tutuyor mu?
      `Machine4.Pressure` 14-17 bulgusu her donemde mi gecerli, yoksa
      tek bir donemin artifakti mi?

  V3  Dagilim kaymasi (K16) ne kadar buyuk?
      Ardisik pencerelerde deviation ortalamasi ne kadar oynuyor?

Calistirma:  python src/analysis/validation.py
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "modeling"))
sys.path.insert(0, str(ROOT / "src" / "data_processing"))
import schema  # noqa: E402
import splits  # noqa: E402
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor  # noqa: E402

warnings.filterwarnings("ignore")

PROC = ROOT / "data" / "processed" / "clean_v1.csv"
RESULTS = ROOT / "reports" / "modeling_results.csv"
OUT = ROOT / "reports" / "08_validation_report.md"

N_FOLDS = 5
CV_ACTIVE = 1.0
MIN_BIN_N = 150


def make_model(name):
    if name == "hgb":
        return HistGradientBoostingRegressor(max_iter=200, random_state=0)
    if name == "rf":
        return RandomForestRegressor(n_estimators=100, min_samples_leaf=5,
                                     random_state=0, n_jobs=-1)
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return make_pipeline(StandardScaler(), Ridge(alpha=1.0))


def v1_walk_forward(df, targets, cols, embargo):
    """Her hedef icin walk-forward fold'larda beceri skoru."""
    rows = []
    for _, t in targets.iterrows():
        y = df[f"{t.output}.dev"]
        X = df[cols]
        m = y.notna() & X.notna().all(axis=1)
        Xv, yv = X[m].reset_index(drop=True), y[m].reset_index(drop=True)
        for k, (tr, te) in enumerate(splits.blocked_kfold(len(yv), N_FOLDS,
                                                          embargo), 1):
            mdl = make_model(t.model)
            mdl.fit(Xv.iloc[tr], yv.iloc[tr])
            r = splits.metrics(yv.iloc[te].to_numpy(), mdl.predict(Xv.iloc[te]))
            b = splits.metrics(yv.iloc[te].to_numpy(),
                               splits.baseline_persistence(yv.to_numpy(), te))
            rows.append(dict(
                output=t.output, fold=k, n_train=len(tr), n_test=len(te),
                r2=round(r["r2"], 4),
                skill_vs_pers=round(splits.skill_score(r["rmse"], b["rmse"]), 4)))
    return pd.DataFrame(rows)


def v2_empirical_stability(df, targets, param, n_parts=4):
    """
    Faz 4'un ampirik bulgusu zamanda tutuyor mu?

    Veri ardisik parcalara bolunur; her parcada, ilgili parametrenin en dusuk
    dilimi gercekten en iyi mi diye bakilir.
    """
    rows = []
    edges = np.linspace(0, len(df), n_parts + 1).astype(int)
    try:
        q_all = pd.qcut(df[param], 4, duplicates="drop")
    except ValueError:
        return pd.DataFrame()
    first_bin = q_all.cat.categories[0]

    for _, t in targets.iterrows():
        dev = df[f"{t.output}.dev"].abs()
        for p in range(n_parts):
            sl = slice(edges[p], edges[p + 1])
            sub_dev, sub_q = dev.iloc[sl], q_all.iloc[sl]
            g = sub_dev.groupby(sub_q, observed=True).agg(["mean", "count"])
            g = g[g["count"] >= MIN_BIN_N]
            if len(g) < 2 or first_bin not in g.index:
                continue
            best = g["mean"].idxmin()
            rows.append(dict(
                output=t.output, parca=f"{p+1}/{n_parts}",
                ilk_dilim_ort=round(float(g.loc[first_bin, "mean"]), 4),
                en_iyi_dilim=str(best),
                ilk_dilim_en_iyi_mi="EVET" if best == first_bin else "hayir"))
    return pd.DataFrame(rows)


def v3_drift(df, targets, n_parts=8):
    """Ardisik pencerelerde deviation ortalamasi ne kadar kayiyor?"""
    edges = np.linspace(0, len(df), n_parts + 1).astype(int)
    rows = []
    for _, t in targets.iterrows():
        dev = df[f"{t.output}.dev"]
        means = []
        for p in range(n_parts):
            v = dev.iloc[edges[p]:edges[p + 1]].dropna()
            means.append(float(v.mean()) if len(v) > 50 else np.nan)
        means = np.array(means, dtype=float)
        ok = ~np.isnan(means)
        if ok.sum() < 3:
            continue
        overall_std = float(dev.std())
        rows.append(dict(
            output=t.output,
            pencere_min=round(float(np.nanmin(means)), 4),
            pencere_max=round(float(np.nanmax(means)), 4),
            kayma=round(float(np.nanmax(means) - np.nanmin(means)), 4),
            # kayma, serinin kendi std'sine gore ne kadar buyuk?
            kayma_sigma=round(float((np.nanmax(means) - np.nanmin(means))
                                    / overall_std), 2) if overall_std else np.nan))
    return pd.DataFrame(rows)


def main():
    df = pd.read_csv(PROC)
    r = pd.read_csv(RESULTS)
    s1 = r[r.feature_set == "controlled"]
    best = s1.loc[s1.groupby("output").skill_vs_pers.idxmax()]
    targets = best[best.skill_vs_pers > 0].sort_values("skill_vs_pers",
                                                       ascending=False)

    dvs = [c for c in schema.decision_variables(df.columns) if c in df.columns]
    cpps = [c for c in dvs if 100 * df[c].std() / df[c].mean() >= CV_ACTIVE]
    embargo = splits.suggest_embargo(df, cpps)
    param = "Machine4.Pressure.C.Actual"

    print(f"hedef: {len(targets)} | fold: {N_FOLDS} | embargo: {embargo}")
    print("  V1 walk-forward ...", flush=True)
    v1 = v1_walk_forward(df, targets, cpps, embargo)
    print("  V2 ampirik kararlilik ...", flush=True)
    v2 = v2_empirical_stability(df, targets, param)
    print("  V3 drift ...", flush=True)
    v3 = v3_drift(df, targets)

    cpp_lags = [(c, *splits.acf_decay_lag(df[c], return_censored=True))
                for c in cpps]
    write_report(v1, v2, v3, targets, param, embargo, cpp_lags, len(df))
    v1.to_csv(ROOT / "reports" / "validation_folds.csv", index=False)
    print(f"\nyazildi: {OUT}")


def write_report(v1, v2, v3, targets, param, embargo, cpp_lags, df_len):
    L = []
    w = L.append
    w("# Faz 5 - Validation ve Dayaniklilik\n")
    w("Kaynak: `data/processed/clean_v1.csv`  ")
    w("Uretildi: `python src/analysis/validation.py`\n")
    w("Faz 3 ve 4'un butun sonuclari **tek bir bolmeye** dayaniyordu (son %30).")
    w("O donem atipikse tum sonuclar yaniltici olur. Burada ayni sorular zaman")
    w(f"ekseni boyunca ilerleyen **{N_FOLDS} ayri pencerede** tekrar soruluyor.\n")

    # ---- V0: embargo hesabinin kendisi bir bulgu ----
    w("## V0 - Embargo hesabi beklenmedik bir sey gosterdi\n")
    w("Embargo, karar degiskenlerinin otokorelasyonunun 0.2 altina indigi")
    w(f"mesafeye gore secilir. Aktif CPP'ler icin bu deger **{embargo} satir**")
    w("cikti. Faz 3'te 24 `controlled` kolonun medyani 49 satirdi.\n")
    w("| parametre | sonumlenme lag'i | durum |")
    w("|---|---|---|")
    for c, lag, cens in cpp_lags:
        short = c.replace(".C.Actual", "")
        w(f"| `{short}` | {lag} | "
          + ("**SANSURLU** — tarama siniri" if cens else "olculdu") + " |")
    w("")
    n_cens = sum(1 for _, _, c in cpp_lags if c)
    w(f"> **BULGU V0 - {n_cens} / {len(cpp_lags)} aktif CPP'nin otokorelasyonu")
    w("> tarama siniri icinde hic sonmuyor.** Donen sayi bir olcum degil,")
    w("> aramanin durdugu yer; gercek sonumlenme daha uzakta.")
    w(">")
    w("> Bunun anlami K5'in sanilandan agir olmasi: karar degiskenleri **33+")
    w("> dakika** boyunca otokorelasyonlu. 14.088 satirlik veri, bu parametreler")
    w(f"> acisindan yaklasik **{df_len // embargo if embargo else 0} bagimsiz blok**")
    w("> demek -- 14.088 degil.")
    w(">")
    w("> Faz 2'de olculen medyan `n_eff` = 465 bu tabloyla birlikte okunmali:")
    w("> o deger output serilerini de iceriyordu. **Optimizasyonun ogrenmesi")
    w("> gereken sey karar degiskenlerinin etkisi ve orada elde bir avuc")
    w("> bagimsiz gozlem var.** Faz 4'un zayif sonucu buradan geliyor.\n")

    # ---- V1 ----
    w("## V1 - Model becerisi fold'lar arasinda tutarli mi?\n")
    if v1.empty:
        w("*Fold uretilemedi.*\n")
    else:
        # Fold 1'in train seti cok kucuk; onu ayirmadan yapilan karsilastirma
        # adaletsiz olur (tek split ~9.700 satirla egitiliyor).
        f1_n = int(v1[v1.fold == 1].n_train.iloc[0])
        w("**Once bir adalet duzeltmesi.** Walk-forward'da train seti ileriye")
        w("dogru buyuyor; ilk fold yalnizca "
          f"**{f1_n:,} satirla** egitiliyor, tek split ise ~9.700 satirla.")
        w("Fold 1'i digerleriyle ayni kefeye koymak modeli haksiz yere kotu")
        w("gosterir. Asagida ayri tutuldu.\n")
        w("| fold | train | test |")
        w("|---|---|---|")
        for f, g in v1.groupby("fold"):
            w(f"| {f} | {int(g.n_train.iloc[0]):,} | {int(g.n_test.iloc[0]):,} |")
        w("")

        main_folds = v1[v1.fold > 1]
        agg = (main_folds.groupby("output")
                 .agg(fold=("fold", "count"),
                      medyan=("skill_vs_pers", "median"),
                      en_dusuk=("skill_vs_pers", "min"),
                      en_yuksek=("skill_vs_pers", "max"),
                      pozitif=("skill_vs_pers", lambda s: int((s > 0).sum())))
                 .reset_index())
        agg = agg.merge(targets[["output", "skill_vs_pers"]], on="output")
        agg = agg.rename(columns={"skill_vs_pers": "tek_split"})
        f1 = v1[v1.fold == 1].set_index("output").skill_vs_pers

        w("`tek_split` = Faz 3/4'te kullanilan tek bolmenin sonucu.  ")
        w("`fold 1` ayri sutunda: yetersiz train, yorum disi.\n")
        w("| output | tek_split | fold 1 (yetersiz) | fold 2-5 medyani | "
          "en dusuk | en yuksek | pozitif |")
        w("|---|---|---|---|---|---|---|")
        for _, r in agg.iterrows():
            w(f"| {r.output} | {r.tek_split:+.4f} | {f1.get(r.output, float('nan')):+.4f} | "
              f"{r.medyan:+.4f} | {r.en_dusuk:+.4f} | {r.en_yuksek:+.4f} | "
              f"{r.pozitif}/{r.fold} |")
        w("")
        stable = agg[agg.pozitif == agg.fold]
        fragile = agg[agg.pozitif <= agg.fold / 2]
        w("> **BULGU V1 - Tek split sonuclari kirilgan.** Fold 1 disarida")
        w(f"> birakildiginda bile, {len(agg)} output'un yalnizca **{len(stable)}**'i")
        w("> her fold'da pozitif kaliyor.")
        if len(fragile):
            w(">")
            w("> Su output'lar fold'larin yarisinda veya daha azinda pozitif --")
            w("> tek split sonucu bunlar icin **gecersiz sayilmali**:")
            for _, r in fragile.iterrows():
                w(f">   - `{r.output}`: {r.pozitif}/{r.fold} fold, "
                  f"medyan {r.medyan:+.4f} (tek split {r.tek_split:+.4f})")
        w(">")
        w("> **Bu, Faz 3 ve 4'un sonuclarini dogrudan etkiliyor.** \"5 output'ta")
        w("> persistence gecildi\" ifadesi tek bolmeye dayaniyordu; walk-forward")
        w("> bu ifadeyi desteklemiyor. Faz 4'un optimizasyon onerileri de ayni")
        w("> zemine dayandigi icin **guven derecesi dusurulmelidir.**\n")

    # ---- V2 ----
    w("## V2 - Ampirik optimizasyon bulgusu zamanda tutuyor mu?\n")
    w(f"Faz 4'un tek tutarli bulgusu: `{param.replace('.C.Actual','')}` en dusuk")
    w("dilimi (14-17) butun output'larda en iyiydi. Bu bulgu tek bir donemin")
    w("artifakti mi, yoksa veri boyunca tutuyor mu?\n")
    if v2.empty:
        w("*Yeterli gozlem yok.*\n")
    else:
        piv = v2.pivot(index="output", columns="parca",
                       values="ilk_dilim_en_iyi_mi")
        w("| output | " + " | ".join(piv.columns) + " | tutma orani |")
        w("|" + "|".join("---" for _ in range(len(piv.columns) + 2)) + "|")
        holds = []
        for o, row in piv.iterrows():
            n_ok = int((row == "EVET").sum())
            n_tot = int(row.notna().sum())
            holds.append(n_ok / n_tot if n_tot else np.nan)
            w(f"| {o} | " + " | ".join(str(x) for x in row) +
              f" | **{n_ok}/{n_tot}** |")
        w("")
        mean_hold = float(np.nanmean(holds))
        w(f"> **BULGU V2 - Bulgu zaman parcalarinin ortalama %{100*mean_hold:.0f}"
          "'inde tutuyor.**")
        if mean_hold >= 0.75:
            w("> Faz 4'un `Machine4.Pressure` bulgusu tek bir donemin artifakti")
            w("> degil; veri boyunca tekrarlaniyor. Bu, K18'i **guclendirir** --")
            w("> etki kucuk olsa da yon kararli.")
        elif mean_hold >= 0.5:
            w("> Bulgu kismen tutuyor. Bazi donemlerde tersine donuyor, yani")
            w("> **kosula bagli**: parametrenin etkisi diger kosullara gore")
            w("> degisiyor olabilir. K18 zayiflar.")
        else:
            w("> Bulgu **tutmuyor.** Faz 4'un tek tutarli bulgusu bile zamanda")
            w("> kararli degil; `Machine4.Pressure` onerisi geri cekilmelidir.")
        w("")

    # ---- V3 ----
    w("## V3 - Dagilim kaymasi ne kadar buyuk?\n")
    w("K16'da fark edilen kayma burada olculuyor: veri 8 ardisik pencereye")
    w("bolunup her birinde deviation ortalamasi hesaplandi. `kayma_sigma`,")
    w("pencereler arasi farkin serinin kendi standart sapmasina orani.\n")
    if v3.empty:
        w("*Hesaplanamadi.*\n")
    else:
        w("| output | en dusuk pencere | en yuksek pencere | kayma | kayma / sigma |")
        w("|---|---|---|---|---|")
        for _, r in v3.sort_values("kayma_sigma", ascending=False).iterrows():
            w(f"| {r.output} | {r.pencere_min} | {r.pencere_max} | {r.kayma} | "
              f"**{r.kayma_sigma}** |")
        w("")
        big = v3[v3.kayma_sigma > 1.0]
        w(f"> **BULGU V3 - {len(big)} / {len(v3)} output'ta pencereler arasi kayma,")
        w("> serinin kendi standart sapmasindan buyuk.** Yani prosesin ortalamasi,")
        w("> 4 saatlik pencere icinde bile gurultuden daha fazla oynuyor.")
        w(">")
        w("> Pratik sonucu: **sabit bir setpoint onerisi kisa omurludur.** Bir")
        w("> donemde dogru olan ayar, saatler sonra merkezi kaymis olabilir.")
        w("> Endustriyel oneri bu yuzden \"su degere ayarlayin\" degil,")
        w("> **\"duzenli yeniden kalibrasyon\"** yonunde olmalidir.\n")

    OUT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
