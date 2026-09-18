"""
Faz 4 - Dar Kapsamli Optimizasyon.

KAPSAM NEDEN DAR
----------------
Faz 3, S1 sorusuna zayif cevap verdi: karar degiskenleri 25 output'un yalnizca
5'inde persistence baseline'ini geciyor ve hicbirinde R2 pozitif degil (K15).
Bu yuzden optimizasyon TUM prosese degil, yalnizca modelin gercekten bir sey
yakaladigi output'lara ve gercekten oynatilmis parametrelere kuruluyor.

IKI BAGIMSIZ YOL
----------------
1. MODEL-TABANLI: egitilmis model uzerinde arama. Hizli ama modelin R2'si
   negatif oldugu icin TEK BASINA DAYANAK DEGIL.
2. AMPIRIK: modele hic guvenmeden, gozlenen veride parametre bolgelerini
   dogrudan karsilastirma. "Bu bolgede calisildiginda gercekte ne olmus?"

Ikisi ayni bolgeyi isaret ediyorsa oneri guclenir; ayrisiyorsa bu da
raporlanir ve oneri zayif sayilir. Modelin dedigi, verinin gosterdiginin
yerine gecmez.

Calistirma:  python src/optimization/optimize.py
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
OUT = ROOT / "reports" / "07_optimization_report.md"

TEST_FRAC = 0.30
RANDOM_STATE = 0
N_SEARCH = 4000          # model-tabanli aramada denenen aday nokta
MIN_BIN_N = 200          # ampirik analizde bir bolgenin sayilmasi icin min gozlem
CV_ACTIVE = 1.0          # K7: aktif karar degiskeni esigi


class NoSolutionError(RuntimeError):
    """
    Optimizasyonun uzerine kurulacagi zemin yok.

    Bu bir cokme degil bir SONUCTUR: veri, optimizasyon icin gereken
    kontrasti ya da tahmin gucunu tasimiyor demektir. Sessizce bos bir rapor
    uretmek yaniltici olur -- bos tablo, "optimizasyon yapildi ama bir sey
    bulunamadi" gibi degil, "optimizasyon yapildi" gibi okunur.
    """


def check_preconditions(cpps, targets):
    """
    Arama baslamadan once iki on kosul.

    Ikisinden biri saglanmazsa arama anlamsizdir ve sonraki adimlar anlasilmaz
    hatalarla coker (bos tabloda pd.concat, bos gruplamada idxmin). Onun
    yerine nedeni yazan tek bir hata veriliyor.
    """
    if not cpps:
        raise NoSolutionError(
            f"aktif karar degiskeni yok (K7: CV >= %{CV_ACTIVE:.0f}). Hicbir "
            "parametre pratikte oynatilmamis; arama uzayi tek noktaya coker.")
    if len(targets) == 0:
        raise NoSolutionError(
            "hedef output yok: Faz 3'te hicbir output persistence baseline'ini "
            "gecemedi (skill_vs_pers > 0). Modelin bir sey yakaladigi output "
            "olmadan optimizasyon, gurultuyu optimize etmek olur.")


def active_cpps(df):
    dvs = [c for c in schema.decision_variables(df.columns) if c in df.columns]
    return [c for c in dvs if 100 * df[c].std() / df[c].mean() >= CV_ACTIVE]


def target_outputs():
    r = pd.read_csv(RESULTS)
    s1 = r[r.feature_set == "controlled"]
    best = s1.loc[s1.groupby("output").skill_vs_pers.idxmax()]
    return best[best.skill_vs_pers > 0].sort_values("skill_vs_pers", ascending=False)


def fit_model(df, target, cpps, model_name):
    """Faz 3'te o output icin en iyi cikan modeli, ayni split ile yeniden kurar."""
    y = df[f"{target}.dev"]
    X = df[cpps]
    m = y.notna() & X.notna().all(axis=1)
    Xv, yv = X[m].reset_index(drop=True), y[m].reset_index(drop=True)
    tr, te = splits.blocked_split(len(yv), TEST_FRAC,
                                  splits.suggest_embargo(df, cpps))
    mdl = (HistGradientBoostingRegressor(max_iter=200, random_state=RANDOM_STATE)
           if model_name == "hgb" else
           RandomForestRegressor(n_estimators=100, min_samples_leaf=5,
                                 random_state=RANDOM_STATE, n_jobs=-1))
    mdl.fit(Xv.iloc[tr], yv.iloc[tr])
    return mdl, Xv, yv, tr, te


def model_search(mdl, Xv, cpps, rng):
    """
    Gozlenen aralik icinde rastgele arama.

    K1 geregi ekstrapolasyon YOK: her parametre yalnizca veride gorulmus
    min-max araliginda ornekleniyor. Disina cikan bir oneri, hicbir gozleme
    dayanmayan bir tahmindir.
    """
    lo, hi = Xv.min(), Xv.max()
    cand = pd.DataFrame(
        {c: rng.uniform(lo[c], hi[c], N_SEARCH) for c in cpps})
    pred = mdl.predict(cand)
    # Amac: sapmayi sifira yaklastirmak (bias) -- mutlak deger minimize
    best_i = int(np.argmin(np.abs(pred)))
    return cand.iloc[best_i], float(pred[best_i])


def empirical_regions(df, target, cpps, n_bins=4):
    """
    Modele hic guvenmeden: her CPP'yi kantillere bolup o dilimde GERCEKLESEN
    performansi olcer. "Bu bolgede calisildiginda ne olmus?"
    """
    dev = df[f"{target}.dev"]
    rows = []
    for c in cpps:
        try:
            q = pd.qcut(df[c], n_bins, duplicates="drop")
        except ValueError:
            continue
        g = dev.groupby(q, observed=True)
        for interval, sub in g:
            sub = sub.dropna()
            if len(sub) < MIN_BIN_N:
                continue
            rows.append(dict(
                parametre=c.replace(".C.Actual", "")
                           .replace("FirstStage.CombinerOperation", "Combiner"),
                aralik=f"{interval.left:.2f} – {interval.right:.2f}",
                n=len(sub),
                ort_sapma=round(float(sub.mean()), 4),
                mutlak_sapma=round(float(sub.abs().mean()), 4),
                std=round(float(sub.std()), 4),
            ))
    return pd.DataFrame(rows)


def sensitivity_a1(df, target, model_name, all_cpps):
    """
    A1 duyarlilik analizi (K9).

    A1 yanlissa karar degiskeni seti degisir. Sonucun bu varsayima ne kadar
    bagli oldugunu olcmek icin set daraltilip genisletiliyor ve modelin
    beceri skoru karsilastiriliyor.
    """
    y = df[f"{target}.dev"]
    measured = [c for c in df.columns if schema.classify(c) == schema.MEASURED]
    variants = {
        "dar (yalnizca aktif CPP)": all_cpps,
        "genis (tum controlled)": [c for c in schema.decision_variables(df.columns)
                                   if c in df.columns],
        "A1 yanlissa (measured dahil)": all_cpps + measured,
    }
    rows = []
    for label, cols in variants.items():
        X = df[cols]
        m = y.notna() & X.notna().all(axis=1)
        Xv, yv = X[m].reset_index(drop=True), y[m].reset_index(drop=True)
        if len(yv) < 500:
            continue
        emb = splits.suggest_embargo(df, cols)
        tr, te = splits.blocked_split(len(yv), TEST_FRAC, emb)
        mdl = (HistGradientBoostingRegressor(max_iter=200, random_state=RANDOM_STATE)
               if model_name == "hgb" else
               RandomForestRegressor(n_estimators=100, min_samples_leaf=5,
                                     random_state=RANDOM_STATE, n_jobs=-1))
        mdl.fit(Xv.iloc[tr], yv.iloc[tr])
        r = splits.metrics(yv.iloc[te].to_numpy(), mdl.predict(Xv.iloc[te]))
        b = splits.metrics(yv.iloc[te].to_numpy(),
                           splits.baseline_persistence(yv.to_numpy(), te))
        rows.append(dict(varyant=label, n_feature=len(cols),
                         r2=round(r["r2"], 4),
                         skill_vs_pers=round(splits.skill_score(r["rmse"], b["rmse"]), 4)))
    return pd.DataFrame(rows)


def main():
    df = pd.read_csv(PROC)
    cpps = active_cpps(df)
    targets = target_outputs()
    check_preconditions(cpps, targets)
    rng = np.random.default_rng(RANDOM_STATE)

    print(f"aktif CPP: {len(cpps)} | hedef output: {len(targets)}")

    opt_rows, emp_tables, sens_tables = [], {}, {}
    for _, t in targets.iterrows():
        name = t.output
        print(f"  {name} ...", flush=True)
        mdl, Xv, yv, tr, te = fit_model(df, name, cpps, t.model)
        point, pred = model_search(mdl, Xv, cpps, rng)

        cur_bias = float(yv.iloc[te].mean())
        cur_abs = float(yv.iloc[te].abs().mean())
        opt_rows.append(dict(
            output=name, error_type=t.error_type, model=t.model,
            skill_vs_pers=t.skill_vs_pers,
            mevcut_bias=round(cur_bias, 4),
            mevcut_mutlak=round(cur_abs, 4),
            model_tahmini=round(pred, 4),
            **{c.replace(".C.Actual", "").replace("FirstStage.CombinerOperation", "Combiner"):
               round(float(point[c]), 2) for c in cpps}))

        emp_tables[name] = empirical_regions(df, name, cpps)
        sens_tables[name] = sensitivity_a1(df, name, t.model, cpps)

    opt = pd.DataFrame(opt_rows)
    write_report(df, opt, emp_tables, sens_tables, cpps, targets)
    opt.to_csv(ROOT / "reports" / "optimization_points.csv", index=False)
    print(f"\nyazildi: {OUT}")


def write_report(df, opt, emp_tables, sens_tables, cpps, targets):
    L = []
    w = L.append
    def short(c):
        return (c.replace(".C.Actual", "")
                 .replace("FirstStage.CombinerOperation", "Combiner"))

    w("# Faz 4 - Dar Kapsamli Optimizasyon\n")
    w("Kaynak: `data/processed/clean_v1.csv`  ")
    w("Uretildi: `python src/optimization/optimize.py`\n")

    w("## Kapsam ve neden bu kadar dar\n")
    w("Faz 3 (K15), karar degiskenlerinin 25 output'un yalnizca **5**'inde")
    w("persistence baseline'ini gectigini gosterdi; hicbirinde R2 pozitif degil.")
    w("Optimizasyon bu yuzden tum prosese degil, yalnizca **modelin gercekten bir")
    w("sey yakaladigi output'lara** ve **gercekten oynatilmis parametrelere**")
    w("kuruluyor.\n")
    w(f"- Hedef output: **{len(opt)}** (S1'de persistence gecilenler)")
    w(f"- Karar degiskeni: **{len(cpps)}** aktif CPP (K7: CV >= %{CV_ACTIVE:.0f})")
    w("- Arama uzayi: her parametre yalnizca **gozlenen min-max araliginda**")
    w("  (K1 geregi ekstrapolasyon yok)\n")
    w("| CPP | gozlenen aralik | CV % |")
    w("|---|---|---|")
    for c in cpps:
        w(f"| `{short(c)}` | {df[c].min():.2f} – {df[c].max():.2f} | "
          f"{100*df[c].std()/df[c].mean():.2f} |")
    w("")

    w("## Yontem: iki bagimsiz yol\n")
    w("Model R2'si negatif oldugu icin model-tabanli optimizasyon **tek basina**")
    w("dayanak sayilmadi. Ayni soru modele hic guvenmeden de soruldu:\n")
    w("| Yol | Nasil | Guclu yani | Zayif yani |")
    w("|---|---|---|---|")
    w("| **Model-tabanli** | egitilmis model uzerinde 4.000 aday nokta | "
      "parametreleri birlikte degerlendirir | modelin R2'si negatif |")
    w("| **Ampirik** | gozlenen veride kantil bolgeleri | "
      "gercek olculere dayanir | parametreleri tek tek gorur |")
    w("")
    w("> Ikisi ayni bolgeyi isaret ederse oneri guclenir. Ayrisirsa bu da")
    w("> raporlanir ve oneri **zayif** sayilir.\n")

    w("## Model-tabanli optimum noktalar\n")
    cols = ["output", "error_type", "skill_vs_pers", "mevcut_bias",
            "mevcut_mutlak", "model_tahmini"] + [short(c) for c in cpps]
    w("| " + " | ".join(cols) + " |")
    w("|" + "|".join("---" for _ in cols) + "|")
    for _, r in opt.iterrows():
        w("| " + " | ".join(str(r[c]) for c in cols) + " |")
    w("")
    w("> `mevcut_bias` test blogundaki gerceklesen ortalama sapma;")
    w("> `model_tahmini` ise modelin onerilen noktada bekledigi sapma.")
    w("> **Bu iki sayi ayni olcegi paylasmiyor** -- biri gozlem, digeri zayif bir")
    w("> modelin tahmini. Aralarindaki fark bir \"iyilesme yuzdesi\" olarak")
    w("> okunmamalidir; oyle okumak projenin bastan reddettigi seydir.\n")

    w("## Ampirik kontrol: veride gercekte ne olmus?\n")
    w("Her CPP kantillere bolundu ve o dilimde **gerceklesen** sapma olculdu.")
    w(f"Modele hic guvenilmiyor. En az {MIN_BIN_N} gozlemi olan dilimler alindi.\n")
    for name, tbl in emp_tables.items():
        if tbl.empty:
            continue
        w(f"### {name}\n")
        best = tbl.loc[tbl.groupby("parametre").mutlak_sapma.idxmin()]
        worst = tbl.loc[tbl.groupby("parametre").mutlak_sapma.idxmax()]
        w("| parametre | en iyi dilim | mutlak sapma | en kotu dilim | "
          "mutlak sapma | fark |")
        w("|---|---|---|---|---|---|")
        for p in best.parametre:
            b = best[best.parametre == p].iloc[0]
            x = worst[worst.parametre == p].iloc[0]
            gain = x.mutlak_sapma - b.mutlak_sapma
            w(f"| `{p}` | {b.aralik} | {b.mutlak_sapma} | {x.aralik} | "
              f"{x.mutlak_sapma} | **{gain:+.4f}** |")
        w("")

    # --- iki yolun uzlasmasi: asil sonuc ---
    w("## Iki yol uzlasiyor mu?\n")
    w("Faz 4'un asil ciktisi bu tablo. Model-tabanli aramanin onerdigi deger,")
    w("ampirik olarak **en iyi cikan dilimin icinde** mi?\n")
    agree_rows = []
    for name, tbl in emp_tables.items():
        if tbl.empty or name not in set(opt.output):
            continue
        orow = opt[opt.output == name].iloc[0]
        best = tbl.loc[tbl.groupby("parametre").mutlak_sapma.idxmin()]
        for _, b in best.iterrows():
            lo, hi = [float(x) for x in b.aralik.split("–")]
            val = float(orow[b.parametre])
            inside = lo <= val <= hi
            agree_rows.append(dict(output=name, parametre=b.parametre,
                                   model_onerisi=val, ampirik_en_iyi=b.aralik,
                                   uzlasma="EVET" if inside else "hayir"))
    agree = pd.DataFrame(agree_rows)
    # Asagidaki blok calismasa da sonuc tablosu bu listeyi okuyor.
    consistent = []
    if not agree.empty:
        n_ok = int((agree.uzlasma == "EVET").sum())
        w("| output | parametre | model onerisi | ampirik en iyi dilim | uzlasma |")
        w("|---|---|---|---|---|")
        for _, r in agree.iterrows():
            w(f"| {r.output} | `{r.parametre}` | {r.model_onerisi} | "
              f"{r.ampirik_en_iyi} | {r.uzlasma} |")
        w("")
        pct = 100 * n_ok / len(agree)
        w(f"> **BULGU O1 - {n_ok} / {len(agree)} durumda (%{pct:.0f}) iki yol ayni")
        w("> bolgeyi isaret ediyor.** Model ve ham gozlem birbirinden bagimsiz")
        w("> yontemler; ayni yere isaret ettikleri parametreler icin oneri")
        w("> **desteklenmis** sayilir.")
        w(">")
        w("> Uzlasmayan satirlar oneri listesinden **cikarilmadi, isaretlendi.**")
        w("> Bir modelin R2'si negatifken onun onerisini ampirik kanita ragmen")
        w("> savunmak, projenin bastan reddettigi seydir. Uzlasmayan yerlerde")
        w("> **ampirik bulgu esas alinir.**\n")

        # ampirik olarak en guclu kazanimlar
        w("### Ampirik olarak en guclu bulgular\n")
        w("Modele hic guvenmeden, yalnizca gozlenen veriden:\n")
        gains = []
        for name, tbl in emp_tables.items():
            if tbl.empty:
                continue
            b = tbl.loc[tbl.groupby("parametre").mutlak_sapma.idxmin()]
            x = tbl.loc[tbl.groupby("parametre").mutlak_sapma.idxmax()]
            for p in b.parametre:
                bi = b[b.parametre == p].iloc[0]
                xi = x[x.parametre == p].iloc[0]
                gains.append(dict(output=name, parametre=p,
                                  iyi_dilim=bi.aralik, iyi=bi.mutlak_sapma,
                                  kotu_dilim=xi.aralik, kotu=xi.mutlak_sapma,
                                  fark=round(xi.mutlak_sapma - bi.mutlak_sapma, 4),
                                  oran=round(xi.mutlak_sapma / bi.mutlak_sapma, 2)
                                  if bi.mutlak_sapma else np.nan))
        g = pd.DataFrame(gains).sort_values("oran", ascending=False).head(8)
        w("| output | parametre | iyi dilim | mutlak sapma | kotu dilim | "
          "mutlak sapma | kat fark |")
        w("|---|---|---|---|---|---|---|")
        for _, r in g.iterrows():
            w(f"| {r.output} | `{r.parametre}` | {r.iyi_dilim} | {r.iyi} | "
              f"{r.kotu_dilim} | {r.kotu} | **{r.oran}x** |")
        w("")
        w("> **BULGU O2 - En guclu ampirik bulgu: "
          f"`{g.iloc[0].parametre}` / {g.iloc[0].output}.** Iyi dilimde mutlak")
        w(f"> sapma {g.iloc[0].iyi}, kotu dilimde {g.iloc[0].kotu} -- "
          f"**{g.iloc[0].oran} kat** fark.")
        w(">")
        w("> **Bu bir nedensellik iddiasi DEGILDIR.** Gozlemsel veriden geliyor;")
        w("> parametre ile output arasinda ucuncu bir degisken araciligi")
        w("> olabilir. Dogru okuma su: *bu bolgede calisildiginda gecmiste daha")
        w("> iyi sonuc alinmis.* Nedenselligi dogrulamanin tek yolu kontrollu")
        w("> deneydir (DOE) -- Faz 5'te oneri olarak yer alacak.\n")

        # --- caprazlama tutarlilik: en guclu kanit ---
        w("### Output'lar arasi tutarlilik\n")
        w("Tek bir output'ta bulunan bir bolge rastlanti olabilir. Ama **farkli")
        w("output'lar ayni parametre icin ayni bolgeyi isaret ediyorsa**, bu")
        w("rastlanti olma ihtimalini ciddi sekilde azaltir. Ampirik en iyi")
        w("dilimlerin orta noktalari:\n")
        mids = []
        for name, tbl in emp_tables.items():
            if tbl.empty:
                continue
            b = tbl.loc[tbl.groupby("parametre").mutlak_sapma.idxmin()]
            for _, r in b.iterrows():
                lo, hi = [float(x) for x in r.aralik.split("–")]
                mids.append(dict(output=name, parametre=r.parametre,
                                 orta=(lo + hi) / 2, aralik=r.aralik))
        md = pd.DataFrame(mids)
        w("| parametre | " + " | ".join(sorted(emp_tables)) + " | yayilim |")
        w("|" + "|".join("---" for _ in range(len(emp_tables) + 2)) + "|")
        consistent = []
        for p, grp in md.groupby("parametre"):
            cells = []
            for o in sorted(emp_tables):
                row = grp[grp.output == o]
                cells.append(row.iloc[0].aralik if len(row) else "—")
            span = grp.orta.max() - grp.orta.min()
            rng_full = df[[c for c in cpps if short(c) == p][0]]
            rel = span / (rng_full.max() - rng_full.min()) if len(grp) > 1 else np.nan
            flag = "**tutarli**" if rel < 0.35 else "dagilmis"
            if rel < 0.35:
                consistent.append(p)
            w(f"| `{p}` | " + " | ".join(cells) + f" | {flag} |")
        w("")
        if consistent:
            w("> **BULGU O3 - Su parametrelerde output'lar birbirini dogruluyor:** "
              + ", ".join(f"`{x}`" for x in consistent) + ".")
            w("> Farkli olcumler bagimsiz olarak ayni calisma bolgesini isaret")
            w("> ediyor.\n")

            # Tutarli parametreler icin etki buyuklugu ve isaret testi
            w("#### Ne kadar guclu bir bulgu?\n")
            w("\"Hepsi ayni dilimi secti\" tek basina yeterli degil: dilimler esit")
            w("buyuklukte olmayabilir ve etki kucuk olabilir. Her ikisi de kontrol")
            w("edildi.\n")
            for p in consistent:
                col = [c for c in cpps if short(c) == p][0]
                try:
                    q = pd.qcut(df[col], 4, duplicates="drop")
                except ValueError:
                    continue
                vc = q.value_counts().sort_index()
                shares = (100 * vc / vc.sum()).round(1)
                w(f"**`{p}`** — istenen 4 dilim, olusan **{len(vc)}** "
                  "(bagli degerler nedeniyle). Dilim paylari: "
                  + ", ".join(f"%{s}" for s in shares) + ".\n")
                w("| output | en iyi dilim | mutlak sapma | digerlerinin en iyisi | "
                  "goreli fark |")
                w("|---|---|---|---|---|")
                same_dir = 0
                for o in sorted(emp_tables):
                    d = df[f"{o}.dev"].abs()
                    g = d.groupby(q, observed=True).mean()
                    if g.empty:
                        continue
                    best_iv = g.idxmin()
                    rest = g.drop(best_iv)
                    if rest.empty:
                        continue
                    rel = 100 * (rest.min() - g[best_iv]) / g[best_iv]
                    if str(best_iv) == str(g.index[0]):
                        same_dir += 1
                    w(f"| {o} | {best_iv} | {g[best_iv]:.4f} | {rest.min():.4f} | "
                      f"**+%{rel:.1f}** |")
                w("")
                n_out = len(emp_tables)
                p_sign = 0.5 ** n_out if same_dir == n_out else np.nan
                if same_dir == n_out:
                    w(f"> {n_out} output'un **{same_dir}'i de ayni dilimi** en iyi")
                    w("> buluyor. Output'lar bagimsiz olsaydi bunun sans eseri olma")
                    w(f"> olasiligi `0.5^{n_out}` = **%{100*p_sign:.1f}**.")
                    w(">")
                    w("> **Ama bu isaret testinin varsayimi burada tam saglanmiyor:**")
                    w("> ayni hattin ayni anindaki olcumleri tamamen bagimsiz degil.")
                    w("> Yani gercek olasilik %"
                      f"{100*p_sign:.1f}'den yuksek. Yon tutarliligi bir isarettir,")
                    w("> kanit degil.")
                    w(">")
                    w("> **Etki buyuklugu kucuk** (yukaridaki goreli fark sutunu) ve")
                    w("> en iyi dilim gozlemlerin buyuk cogunlugunu iceriyor -- yani")
                    w("> \"iyi bolge\" aslinda prosesin zaten calistigi yer.")
                    w("> Pratik okuma: **mevcut calisma bolgesinden cikmamak**,")
                    w("> yeni bir optimum kesfetmek degil.\n")
        else:
            w("> **BULGU O3 - Output'lar arasi tutarlilik yok.** Her output farkli")
            w("> bir bolge isaret ediyor; ortak bir calisma noktasi onerilemez.")
            w("")

    w("## A1 duyarlilik analizi\n")
    w("K9: `.C.` / `.U.` ekinin anlami dogrulanamadi. A1 yanlissa karar")
    w("degiskeni seti degisir. Sonucun bu varsayima ne kadar bagli oldugu:\n")
    for name, tbl in sens_tables.items():
        if tbl.empty:
            continue
        w(f"**{name}**\n")
        w("| varyant | ozellik sayisi | R2 | skill vs persistence |")
        w("|---|---|---|---|")
        for _, r in tbl.iterrows():
            w(f"| {r.varyant} | {r.n_feature} | {r.r2} | {r.skill_vs_pers} |")
        w("")

    # duyarlilik yorumu
    # pd.concat bos listede ValueError firlatir; duyarlilik tablosu hic
    # uretilemediginde rapor bu bolumu atlamali, cokmemeli.
    frames = [t.assign(output=k) for k, t in sens_tables.items() if not t.empty]
    allsens = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not allsens.empty:
        piv = allsens.pivot(index="output", columns="varyant",
                            values="skill_vs_pers")
        col_meas = [c for c in piv.columns if "A1 yanlissa" in c]
        col_wide = [c for c in piv.columns if "genis" in c]
        col_narrow = [c for c in piv.columns if "dar" in c]
        if col_meas and col_wide:
            worse = int((piv[col_meas[0]] < piv[col_wide[0]]).sum())
            w(f"> **BULGU O4 - `measured` degiskenleri eklemek modeli "
              f"{worse}/{len(piv)} output'ta KOTULESTIRIYOR.**")
            w("> A1 yanlis olsaydi -- yani `.U.` kolonlar da ayarlanabilir olsaydi --")
            w("> onlari eklemek tahmin gucunu artirmaliydi. Tersi oluyor.")
            w(">")
            w("> Bu, A1'i **kanitlamaz**; o kolonlarin tahmin gucu katmadigini")
            w("> gosterir. Ama pratik sonuc ayni: karar degiskeni setini `.C.`")
            w("> kolonlarla sinirlamak, veriye gore savunulabilir bir tercih.")
            w("> **K9 riski dusuruldu, kapatilmadi.**\n")
        if col_narrow and col_wide:
            drops = piv[piv[col_narrow[0]] < piv[col_wide[0]] - 0.05]
            if len(drops):
                w("> **BULGU O5 - 5 CPP'ye daralmak bazi output'lara zarar veriyor.**")
                for o, r in drops.iterrows():
                    w(f">   - `{o}`: dar set {r[col_narrow[0]]:+.3f} vs "
                      f"genis set {r[col_wide[0]]:+.3f}")
                w("> Bu output'lar icin 5 aktif CPP yetersiz; tahmin gucu diger")
                w("> `controlled` kolonlardan geliyor. Optimizasyon onerisi bu")
                w("> output'lar icin **gecerli sayilmamali** -- dar set uzerinde")
                w("> kurulan arama, modelin zaten beceremedigi bir uzayda yapiliyor.\n")

    # --- sonuc ---
    w("## Faz 4 sonucu\n")
    w("| Ne soruldu | Cevap |")
    w("|---|---|")
    w(f"| Kac output icin optimizasyon kurulabildi? | {len(opt)} / 25 |")
    if not agree.empty:
        w(f"| Model ve ampirik yol uzlasti mi? | {n_ok}/{len(agree)} durumda (%{pct:.0f}) |")
    w("| Output'lar arasi tutarli parametre | "
      + (", ".join(f"`{c}`" for c in consistent) if consistent else "yok") + " |")
    w("| A1 varsayimina duyarlilik | dusuk (BULGU O4) |")
    w("")
    w("**Dürüst ozet:** Bu veriden \"su parametreleri su degerlere cekin, sapma")
    w("su kadar azalir\" turu bir oneri **cikmiyor.** Cikan sey daha mutevazi ama")
    w("gercek:\n")
    w("1. Proses zaten iyi calistigi bolgede duruyor; `Machine4.Pressure` icin")
    w("   5 output'un 5'i de mevcut ana calisma araligini (14–17) en iyi buluyor.")
    w("   Bu bir **kesif** degil, mevcut ayarin **dogrulanmasi**dir.")
    w("2. Etki buyuklukleri kucuk (%2–26) ve gozlemsel; nedensellik iddia edilemez.")
    w("3. Asil kisit veri: 4 saatlik pencerede karar degiskenleri yeterince")
    w("   oynatilmamis (K7), dolayisiyla optimizasyonun ogrenecegi kontrast yok.\n")
    w("> **Faz 5'e devredilen:** Bu sonucun kendisi bir bulgudur. Optimizasyonun")
    w("> onunu acacak sey daha iyi model degil, **daha iyi veri**: kontrollu bir")
    w("> deney (DOE) ile parametreleri bilincli olarak genis araliklarda oynatmak.")
    w("> Faz 5 bunu somut bir veri toplama onerisine cevirecek.\n")

    OUT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
