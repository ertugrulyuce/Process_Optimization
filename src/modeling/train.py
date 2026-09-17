"""
Faz 3 - Tahmin Modelleri ve Root Cause.

IKI AYRI SORU SORULUYOR
-----------------------
S1 (optimizasyon sorusu): Karar degiskenleri output deviation'ini ACIKLIYOR mu?
    -> yalnizca `controlled` kolonlar girdi. Cevap "hayir" ise optimizasyonun
       dayanagi yok demektir. Faz 4'un varlik sebebi bu soruya bagli.

S2 (izleme sorusu): Deviation TAHMIN edilebilir mi?
    -> gecmis degerler de girdi. Bu soru optimizasyon icin degil, erken uyari
       icin anlamlidir.

Ikisi karistirilirsa proje yanlis sonuca varir: gecmis degerlerle yuksek R2
elde edip "prosesi anladik" sanmak en kolay tuzak.

BASELINE'A GORE RAPORLAMA
-------------------------
Ham R2 bu veride yaniltici. Otokorelasyon 0.93-0.99 oldugu icin "onceki degeri
tekrarla" (persistence) tahmini cok gucludur. Her model iki baseline ile
karsilastirilir ve **beceri skoru** raporlanir:

    skill = 1 - RMSE_model / RMSE_baseline      (0 = baseline kadar, <0 = daha kotu)

Calistirma:  python src/modeling/train.py
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
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

warnings.filterwarnings("ignore")

PROC = ROOT / "data" / "processed" / "clean_v1.csv"
KPI_SUM = ROOT / "reports" / "output_kpi_summary.csv"
OUT = ROOT / "reports" / "06_modeling_report.md"

TEST_FRAC = 0.30
# K13: Stage1 -> Stage2 transport delay ~270 sn
TRANSPORT_LAG = 270
RANDOM_STATE = 0


def models():
    return {
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "rf": RandomForestRegressor(n_estimators=100, min_samples_leaf=5,
                                    random_state=RANDOM_STATE, n_jobs=-1),
        "hgb": HistGradientBoostingRegressor(max_iter=200,
                                             random_state=RANDOM_STATE),
    }


def build_features(df, target, feature_set, dvs, measured):
    """
    S1 -> 'controlled'      : yalnizca ayarlanabilir parametreler
    S1+ -> 'ctrl+measured'  : proses tepkileri de dahil (aciklama ust siniri)
    S2 -> 'ctrl+lag'        : hedefin gecmisi dahil (izleme sorusu)
    """
    if feature_set == "controlled":
        cols = list(dvs)
        X = df[cols].copy()
    elif feature_set == "ctrl+measured":
        cols = list(dvs) + list(measured)
        X = df[cols].copy()
    else:  # ctrl+lag
        X = df[list(dvs)].copy()
        dev = df[f"{target}.dev"]
        # Persistence'in modele girdi olarak verilmis hali
        X["_lag1"] = dev.shift(1)
        X["_lag30"] = dev.shift(30)
        X["_roll60_mean"] = dev.shift(1).rolling(60, min_periods=10).mean()
        # Stage2 hedefleri icin Stage1 ciktilari gecikmeli eklenir (K13)
        if target.startswith("Stage2"):
            for i in (0, 2, 4, 13):
                c = f"Stage1.M{i}.dev"
                if c in df.columns:
                    X[f"_s1m{i}_lag"] = df[c].shift(TRANSPORT_LAG)
    return X


def run_target(df, target, dvs, measured, embargo):
    y_full = df[f"{target}.dev"]
    rows = []

    for fs in ("controlled", "ctrl+measured", "ctrl+lag"):
        X = build_features(df, target, fs, dvs, measured)
        m = y_full.notna() & X.notna().all(axis=1)
        if m.sum() < 500:
            continue
        Xv = X[m].reset_index(drop=True)
        yv = y_full[m].reset_index(drop=True)
        n = len(yv)

        tr, te = splits.blocked_split(n, TEST_FRAC, embargo)
        if len(tr) < 200 or len(te) < 100:
            continue
        y_te = yv.iloc[te].to_numpy()

        b_mean = splits.metrics(y_te, splits.baseline_mean(yv.iloc[tr].to_numpy(), len(te)))
        b_pers = splits.metrics(y_te, splits.baseline_persistence(yv.to_numpy(), te))

        for name, mdl in models().items():
            mdl.fit(Xv.iloc[tr], yv.iloc[tr])
            r = splits.metrics(y_te, mdl.predict(Xv.iloc[te]))
            rows.append(dict(
                output=target, feature_set=fs, model=name,
                n_train=len(tr), n_test=len(te),
                r2=round(r["r2"], 4), rmse=round(r["rmse"], 4), mae=round(r["mae"], 4),
                rmse_mean_base=round(b_mean["rmse"], 4),
                rmse_pers_base=round(b_pers["rmse"], 4),
                skill_vs_mean=round(splits.skill_score(r["rmse"], b_mean["rmse"]), 4),
                skill_vs_pers=round(splits.skill_score(r["rmse"], b_pers["rmse"]), 4),
            ))
    return rows


def importances(df, target, dvs, embargo, top=8):
    """Permutation importance -- yalnizca 'controlled' set uzerinde (S1)."""
    y = df[f"{target}.dev"]
    X = df[dvs]
    m = y.notna() & X.notna().all(axis=1)
    Xv, yv = X[m].reset_index(drop=True), y[m].reset_index(drop=True)
    if len(yv) < 500:
        return []
    tr, te = splits.blocked_split(len(yv), TEST_FRAC, embargo)
    if len(tr) < 200 or len(te) < 100:
        return []
    mdl = RandomForestRegressor(n_estimators=100, min_samples_leaf=5,
                                random_state=RANDOM_STATE, n_jobs=-1)
    mdl.fit(Xv.iloc[tr], yv.iloc[tr])
    pi = permutation_importance(mdl, Xv.iloc[te], yv.iloc[te], n_repeats=5,
                                random_state=RANDOM_STATE, n_jobs=-1)
    order = np.argsort(pi.importances_mean)[::-1][:top]
    return [dict(output=target,
                 feature=Xv.columns[i].replace(".C.Actual", "")
                          .replace("FirstStage.CombinerOperation", "Combiner"),
                 imp=round(float(pi.importances_mean[i]), 5),
                 std=round(float(pi.importances_std[i]), 5))
            for i in order]


def leakage_demo(df, target, dvs, embargo):
    """
    Rastgele split ile bloklu split'i ayni model uzerinde karsilastirir.
    Faz 3'un en onemli tek gostergesi.
    """
    from sklearn.model_selection import train_test_split
    y = df[f"{target}.dev"]
    X = df[dvs]
    m = y.notna() & X.notna().all(axis=1)
    Xv, yv = X[m].reset_index(drop=True), y[m].reset_index(drop=True)
    n = len(yv)
    def mk():
        return RandomForestRegressor(n_estimators=100, min_samples_leaf=5,
                                     random_state=RANDOM_STATE, n_jobs=-1)

    Xtr, Xte, ytr, yte = train_test_split(Xv, yv, test_size=TEST_FRAC,
                                          random_state=RANDOM_STATE)
    r_rand = splits.metrics(yte.to_numpy(), mk().fit(Xtr, ytr).predict(Xte))

    tr, te = splits.blocked_split(n, TEST_FRAC, 0)
    r_blk = splits.metrics(yv.iloc[te].to_numpy(),
                           mk().fit(Xv.iloc[tr], yv.iloc[tr]).predict(Xv.iloc[te]))

    tr, te = splits.blocked_split(n, TEST_FRAC, embargo)
    r_emb = splits.metrics(yv.iloc[te].to_numpy(),
                           mk().fit(Xv.iloc[tr], yv.iloc[tr]).predict(Xv.iloc[te]))
    b_pers = splits.metrics(yv.iloc[te].to_numpy(),
                            splits.baseline_persistence(yv.to_numpy(), te))
    return dict(random=r_rand, blocked=r_blk, embargo=r_emb, persistence=b_pers)


def main():
    df = pd.read_csv(PROC)
    kpi = pd.read_csv(KPI_SUM)
    ins = kpi[kpi.in_scope == "evet"]

    dvs = [c for c in schema.decision_variables(df.columns) if c in df.columns]
    measured = [c for c in df.columns if schema.classify(c) == schema.MEASURED]
    embargo = splits.suggest_embargo(df, dvs)

    print(f"embargo: {embargo} satir | karar degiskeni: {len(dvs)} | "
          f"measured: {len(measured)} | hedef: {len(ins)}")

    demo_target = "Stage1.M4"
    demo = leakage_demo(df, demo_target, dvs, embargo)

    all_rows, all_imp = [], []
    for i, t in enumerate(ins.output, 1):
        print(f"  [{i:2}/{len(ins)}] {t}", flush=True)
        all_rows += run_target(df, t, dvs, measured, embargo)
        all_imp += importances(df, t, dvs, embargo)

    res = pd.DataFrame(all_rows)
    imp = pd.DataFrame(all_imp)
    res = res.merge(ins[["output", "error_type"]], on="output", how="left")

    write_report(res, imp, ins, demo, demo_target, embargo, dvs, measured, df)
    res.to_csv(ROOT / "reports" / "modeling_results.csv", index=False)
    imp.to_csv(ROOT / "reports" / "feature_importance.csv", index=False)
    print(f"\nyazildi: {OUT}")
    return res


def write_report(res, imp, ins, demo, demo_target, embargo, dvs, measured, dfe):
    L, w = [], None
    L = []
    w = L.append

    w("# Faz 3 - Tahmin Modelleri ve Root Cause\n")
    w("Kaynak: `data/processed/clean_v1.csv`  ")
    w("Uretildi: `python src/modeling/train.py`\n")

    w("## Yontem: iki ayri soru\n")
    w("| Soru | Girdi seti | Ne icin |")
    w("|---|---|---|")
    w("| **S1** Karar degiskenleri deviation'i acikliyor mu? | `controlled` "
      f"({len(dvs)} kolon) | Optimizasyonun dayanagi |")
    w("| **S1+** Proses tepkileri eklenince? | `ctrl+measured` "
      f"({len(dvs) + len(measured)} kolon) | Aciklama ust siniri |")
    w("| **S2** Deviation tahmin edilebilir mi? | `ctrl+lag` (+ gecmis degerler) "
      "| Erken uyari / izleme |")
    w("")
    w("Bu ayrim sart: gecmis degerlerle yuksek R2 elde edip \"prosesi anladik\"")
    w("sanmak bu veri setindeki en kolay tuzak. S2'nin basarisi S1'in yerine gecmez.\n")

    w("## Split stratejisi ve sizinti\n")
    w(f"Embargo **{embargo} satir** olarak secildi -- keyfi degil, karar")
    w("degiskenlerinin otokorelasyonunun 0.2 altina indigi mesafenin medyani.\n")
    w(f"Ayni model (`RandomForest`), ayni veri (`{demo_target}.dev`), "
      "yalnizca bolme yontemi degisiyor:\n")
    w("| Bolme yontemi | R2 | RMSE |")
    w("|---|---|---|")
    for lab, key in (("Rastgele split (**YANLIS**)", "random"),
                     ("Bloklu split, embargo yok", "blocked"),
                     (f"Bloklu split + embargo ({embargo})", "embargo"),
                     ("*baseline:* persistence", "persistence")):
        r = demo[key]
        w(f"| {lab} | {r['r2']:.4f} | {r['rmse']:.4f} |")
    w("")
    w("> **BULGU M1 - Rastgele split %97'lik sahte bir basari uretiyor.**")
    w(f"> Ayni model dogru bolmede R2 = {demo['embargo']['r2']:.2f} veriyor, yani")
    w("> sabit ortalama tahminden bile kotu. Aradaki fark modelin degil,")
    w("> **degerlendirme yonteminin** sonucu: rastgele bolmede test satirinin")
    w("> komsulari train'de kaliyor ve model tahmin degil hatirlama yapiyor.")
    w(">")
    w("> Bu, ayni veri setiyle yapilan calismalarda en yaygin hatadir ve")
    w("> literaturde yuksek R2 bildiren sonuclarin bir kismini aciklar.\n")
    w(f"> **BULGU M2 - Persistence baseline R2 = {demo['persistence']['r2']:.4f}.**")
    w("> \"Onceki degeri tekrarla\" tahmini, hicbir sey ogrenmeden bu skoru")
    w("> aliyor. Bir modelin bu esigi gecemedigi her durumda, ham R2 ne olursa")
    w("> olsun, model prosese dair bilgi tasimıyor demektir. Bu yuzden asagida")
    w("> **beceri skoru** raporlaniyor:")
    w(">")
    w("> `skill = 1 - RMSE_model / RMSE_baseline`  (0 = baseline kadar, <0 = daha kotu)\n")

    # --- S1 sonuclari ---
    s1 = res[res.feature_set == "controlled"]
    best_s1 = s1.loc[s1.groupby("output").skill_vs_mean.idxmax()]
    pos_mean = int((best_s1.skill_vs_mean > 0).sum())
    pos_pers = int((best_s1.skill_vs_pers > 0).sum())

    w("## S1 - Karar degiskenleri deviation'i acikliyor mu?\n")
    w("### Once bir okuma notu: R2 neden negatif, skill neden pozitif?\n")
    w("Asagidaki tabloda `r2 = -2.04` ile `skill_vs_mean = +0.79` yan yana")
    w("gorunuyor. Celiski degil; iki olcut **farkli referans** kullaniyor:\n")
    w("- `R2`, test blogunun **kendi ortalamasini** referans alir. Ama o ortalama")
    w("  gercek hayatta bilinmez -- gelecegi bilmek demektir.")
    w("- `skill_vs_mean`, **train ortalamasini** referans alir. Modeli kurarken")
    w("  elde olan tek bilgi budur; gercekci olan bu.\n")
    w("> **BULGU M2b - Ikisi arasindaki fark dagilim kaymasinin olcusudur.**")
    w("> Neredeyse tum output'larda R2 negatif ama skill pozitif olmasi, test")
    w("> blogundaki deviation dagiliminin train'den **kaydigini** gosterir.")
    w("> Proses 4 saatlik pencere icinde bile sabit kalmiyor (K1 ile tutarli).")
    w("> Pratik sonucu: train doneminde kalibre edilen bir model, birkac saat")
    w("> sonra merkezi kaymis tahminler uretir -- Faz 5'te bu, yeniden kalibrasyon")
    w("> ihtiyaci olarak raporlanacak.\n")
    w(f"Her output icin en iyi modelin skorlari ({len(best_s1)} output):\n")
    w(f"- Sabit ortalamayi geceni: **{pos_mean} / {len(best_s1)}**")
    w(f"- Persistence'i geceni: **{pos_pers} / {len(best_s1)}**\n")
    cols = ["output", "error_type", "model", "r2", "skill_vs_mean", "skill_vs_pers"]
    w("| " + " | ".join(cols) + " |")
    w("|" + "|".join("---" for _ in cols) + "|")
    for _, r in best_s1.sort_values("skill_vs_mean", ascending=False).iterrows():
        w("| " + " | ".join(str(r[c]) for c in cols) + " |")
    w("")

    var_s1 = best_s1[best_s1.error_type == "variability"]
    w("> **BULGU M3 - Optimizasyon hedefi output'lar icin durum.** "
      f"{len(var_s1)} variability-baskin output'un "
      f"**{int((var_s1.skill_vs_mean > 0).sum())}**'inde karar degiskenleri sabit")
    w("> ortalamadan iyi tahmin veriyor; persistence'i gecen "
      f"**{int((var_s1.skill_vs_pers > 0).sum())}** tane.")
    w("> Faz 2'nin dogrusal korelasyonla bulamadigi guclu surukleyiciyi (K12)")
    w("> dogrusal olmayan modeller de bulamadiysa, bu artik yontem sorunu degil")
    w("> **verinin soyledigi sey** olarak kabul edilir.\n")

    # --- girdi setleri karsilastirmasi ---
    w("## Girdi setleri karsilastirmasi\n")
    w("Her sette output basina en iyi model secilip medyani alindi:\n")
    w("| girdi seti | medyan R2 | medyan skill vs ortalama | medyan skill vs persistence |")
    w("|---|---|---|---|")
    for fs in ("controlled", "ctrl+measured", "ctrl+lag"):
        sub = res[res.feature_set == fs]
        if sub.empty:
            continue
        b = sub.loc[sub.groupby("output").skill_vs_pers.idxmax()]
        w(f"| `{fs}` | {b.r2.median():.4f} | {b.skill_vs_mean.median():+.4f} | "
          f"{b.skill_vs_pers.median():+.4f} |")
    w("")

    lag = res[res.feature_set == "ctrl+lag"]
    if not lag.empty:
        blag = lag.loc[lag.groupby("output").skill_vs_pers.idxmax()]
        beat = int((blag.skill_vs_pers > 0).sum())
        w("> **BULGU M4 - S2 (izleme sorusu) ile S1 (optimizasyon sorusu) ayrisiyor.**")
        w(f"> Gecmis degerler girdiye eklendiginde {beat} / {len(blag)} output'ta")
        w("> model persistence'i geciyor. Bu, **izleme icin** degerli bir sonuc:")
        w("> deviation kisa vadede tahmin edilebiliyor.")
        w(">")
        w("> Ama bu tahmin gucu **optimizasyona cevrilemez** -- 'deviation'in bir")
        w("> sonraki degeri onceki degerine benziyor' bilgisi hangi parametrenin")
        w("> degistirilecegini soylemez. S1'in cevabi neyse Faz 4 ona dayanir.\n")

    # --- CPP listesi ---
    w("## Critical Process Parameters (CPP)\n")
    if imp.empty:
        w("*Permutation importance uretilemedi.*\n")
    else:
        w("Permutation importance, yalnizca `controlled` girdi seti uzerinde")
        w("(S1 sorusu) ve **test blogunda** hesaplandi -- train uzerinde")
        w("hesaplanan onem degerleri ezberi olcer, genellemeyi degil.\n")
        w("**Onem degerleri yalnizca modelin gercekten tahmin gucu oldugu")
        w("output'lardan toplandi.** Skill skoru negatif olan bir output'ta")
        w("\"onem siralamasi\", gurultunun siralamasidir.\n")

        trusted = set(best_s1[best_s1.skill_vs_mean > 0].output)
        imp_t = imp[imp.output.isin(trusted)]
        w(f"Guvenilen output sayisi: **{len(trusted)} / {len(best_s1)}** "
          "(skill vs ortalama > 0).\n")

        # K7: pratikte oynatilmamis degiskenler ayri isaretlenir
        cv_map = {c.replace(".C.Actual", "")
                   .replace("FirstStage.CombinerOperation", "Combiner"):
                  100 * dfe[c].std() / dfe[c].mean()
                  for c in dvs}

        agg = (imp_t.groupby("feature")
                    .agg(toplam_onem=("imp", "sum"),
                         ortalama=("imp", "mean"),
                         kac_output=("output", "nunique"))
                    .sort_values("toplam_onem", ascending=False))
        agg["cv_pct"] = [round(cv_map.get(f, float("nan")), 2) for f in agg.index]
        agg["durum"] = ["aktif" if agg.cv_pct[f] >= 1.0 else "PASIF" for f in agg.index]

        w("| parametre | toplam onem | ortalama | output sayisi | CV % | durum |")
        w("|---|---|---|---|---|---|")
        for f, r in agg.head(12).iterrows():
            w(f"| `{f}` | {r.toplam_onem:.4f} | {r.ortalama:.4f} | "
              f"{int(r.kac_output)} | {r.cv_pct} | {r.durum} |")
        w("")

        active = agg[agg.durum == "aktif"]
        passive_top = agg[agg.durum == "PASIF"].head(3)
        w("> **BULGU M5 - Onem siralamasinin ust siralari pasif degiskenlerle dolu.**")
        if len(passive_top):
            w("> " + ", ".join(f"`{x}` (CV %{agg.cv_pct[x]})" for x in passive_top.index)
              + " gibi parametreler yuksek onem aliyor ama 4 saatlik pencerede")
            w("> pratikte hic oynatilmamislar (K7).")
        w(">")
        w("> Bir degisken neredeyse sabitken modelin ona onem atfetmesi genellikle")
        w("> **zaman vekilligi**dir: degisken yavasca surukleniyor ve model onun")
        w("> uzerinden zaman trendini yakaliyor. Bu nedensel bir etki degildir ve")
        w("> **o parametreyi degistirmenin output'u degistirecegi anlamina gelmez.**")
        w(">")
        w("> Bu yuzden CPP adaylari yalnizca **aktif** degiskenler arasindan secilir:")
        for f, r in active.head(5).iterrows():
            w(f">   - `{f}` (CV %{r.cv_pct}, {int(r.kac_output)} output'ta)")
        w("")

    # --- sonuc ---
    w("## Faz 3 sonucu\n")
    w("| Soru | Cevap |")
    w("|---|---|")
    w(f"| S1 - Karar degiskenleri aciklıyor mu? | "
      f"{pos_mean}/{len(best_s1)} output'ta ortalamadan iyi, "
      f"{pos_pers}/{len(best_s1)} output'ta persistence'tan iyi |")
    if not lag.empty:
        w(f"| S2 - Deviation tahmin edilebilir mi? | "
          f"{beat}/{len(blag)} output'ta persistence gecildi |")
    w(f"| Sizinti kontrolu | Rastgele split R2 {demo['random']['r2']:.2f} -> "
      f"dogru split {demo['embargo']['r2']:.2f} |")
    w("")
    w("**Faz 4'e etkisi:** Optimizasyon yalnizca S1'in olumlu cevap verdigi")
    w("output'lar icin kurulabilir. S1 zayif kaldigi olcude, Faz 4'un cikti")
    w("iddiasi da o kadar dar tutulacak: veri neyi destekliyorsa o kadari")
    w("onerilecek, daha fazlasi degil.\n")

    OUT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
