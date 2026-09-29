"""
Faz 2 - Otokorelasyon Duzeltmeli Korelasyon Analizi.

Karar degiskenleri (controlled) ile output deviation'lari arasindaki iliskiyi
olcer ve **istatistiksel anlamliligi efektif ornek buyuklugu ile duzeltir.**

IKI DUZELTME BIRDEN UYGULANIR
-----------------------------
1. OTOKORELASYON (K5). 14.088 gozlemle sirali test yapilirsa r = 0.02 bile
   p < 0.05 cikar. Ama ardisik gozlemler bagimsiz degil (lag-1 yuksek).
   Bartlett'in tam formulu:

       n_eff = n / (1 + 2 * sum_k (1 - k/n) * rho_x(k) * rho_y(k))

   Yalnizca lag-1 kullanan basitlestirilmis surum AR(1) varsayar; bu veride
   seriler cok daha uzun hafizali (MotorRPM lag-600'de hala 0.94), o yuzden
   tum lag'ler toplanir (kesim n/4).

2. COKLU KARSILASTIRMA. 600 cift test ediliyor; hicbir gercek iliski olmasa
   bile alpha=0.05 ile ~30 tanesi sans eseri "anlamli" cikardi.
   Benjamini-Hochberg FDR ile q-degeri hesaplanir.

Bu iki duzeltme yapilmazsa proje, gercekte gurultu olan yuzlerce "anlamli"
iliski raporlar. Bu, bu veri setiyle yapilan calismalarda en yaygin hatadir.

Calistirma:  python src/analysis/correlation.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "data_processing"))
import schema  # noqa: E402

PROC = ROOT / "data" / "processed" / "clean_v1.csv"
KPI_SUM = ROOT / "reports" / "output_kpi_summary.csv"
OUT = ROOT / "reports" / "04_correlation_report.md"

ALPHA = 0.05
# En az bu kadar efektif gozlem yoksa iliski hakkinda hukum verilmez.
MIN_N_EFF = 30
# K7: CV'si bu yuzdenin altindaki karar degiskeni "pasif" sayilir.
MIN_CV_PCT = 1.0
# BULGU R3'te "guclu" iliski esigi (|r|).
STRONG_R = 0.3
# Uzun hafizayi gostermek icin raporda anilan seri ve lag.
LONG_MEMORY_COL = "Machine1.MotorRPM.C.Actual"
LONG_MEMORY_LAG = 600


def bh_fdr(p: np.ndarray) -> np.ndarray:
    """
    Benjamini-Hochberg FDR duzeltmesi -> q-degerleri.

    600 cift test edildigi icin gerekli: alpha=0.05 ile hicbir gercek iliski
    olmasa bile ~30 cift sans eseri "anlamli" cikardi.
    """
    p = np.asarray(p, dtype=float)
    q = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    pv = p[ok]
    m = len(pv)
    if m == 0:
        return q
    order = np.argsort(pv)
    ranked = pv[order] * m / (np.arange(m) + 1)
    # monoton azalmayan hale getir (asagidan yukari kumulatif minimum)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.clip(ranked, 0, 1)
    q[ok] = out
    return q


def acf(x: np.ndarray, nlags: int) -> np.ndarray:
    """Lag 1..nlags otokorelasyonlari (FFT'siz, yeterince hizli)."""
    v = x - x.mean()
    denom = float(np.dot(v, v))
    if denom == 0:
        return np.zeros(nlags)
    return np.array([float(np.dot(v[:-k], v[k:])) / denom
                     for k in range(1, nlags + 1)])


def eff_n(n, rx, ry):
    """
    Bartlett'in TAM efektif ornek buyuklugu formulu:

        n_eff = n / (1 + 2 * sum_k (1 - k/n) * rho_x(k) * rho_y(k))

    Sadece lag-1 kullanan basitlestirilmis surum AR(1) varsayar. Bu veride
    seriler cok daha uzun hafizali (Machine1.MotorRPM lag-600'de hala 0.94),
    dolayisiyla lag-1 versiyonu otokorelasyonu ciddi sekilde EKSIK duzeltir.
    Tum lag'ler toplanir.
    """
    k = np.arange(1, len(rx) + 1)
    s = float(np.sum((1 - k / n) * rx * ry))
    factor = 1 + 2 * s
    if factor <= 1e-9:
        return float(n)
    return float(min(n, n / factor))


def eff_n_ar1(n, rx1, ry1):
    """
    AR(1) varsayan basitlestirilmis surum: n * (1 - rx1*ry1) / (1 + rx1*ry1).

    Analizde KULLANILMAZ; rapor, tam formulun neden gerektigini gostermek icin
    iki surumun medyanini yan yana yaziyor.
    """
    p = rx1 * ry1
    return float(min(n, n * (1 - p) / (1 + p)))


def corr_with_eff(x: pd.Series, y: pd.Series, nlags=None):
    """Pearson r + hem ham hem efektif n ile p-degeri."""
    m = x.notna() & y.notna()
    xs, ys = x[m], y[m]
    n = len(xs)
    if n < 10 or xs.std() == 0 or ys.std() == 0:
        return None
    r = float(np.corrcoef(xs, ys)[0, 1])
    # Bartlett icin lag kesimi: n/4 yaygin kural, ust sinir 1000.
    nl = nlags or int(min(1000, n // 4))
    rx, ry = acf(xs.to_numpy(float), nl), acf(ys.to_numpy(float), nl)
    ne = eff_n(n, rx, ry)

    def p_from(nn):
        if np.isnan(nn) or nn <= 3:
            return np.nan
        # Fisher z donusumu
        z = np.arctanh(np.clip(r, -0.999999, 0.999999))
        return float(2 * (1 - stats.norm.cdf(abs(z) * np.sqrt(nn - 3))))

    return dict(r=r, n=n, n_eff=ne, p_naive=p_from(n), p_eff=p_from(ne),
                n_eff_ar1=eff_n_ar1(n, rx[0], ry[0]))


def main():
    df = pd.read_csv(PROC)
    summary = pd.read_csv(KPI_SUM)
    ins = summary[summary.in_scope == "evet"]

    # Sadece gercekten oynatilmis karar degiskenleri anlamli sonuc verebilir (K7).
    dvs = [c for c in schema.decision_variables(df.columns) if c in df.columns]
    cv = {c: 100 * df[c].std() / df[c].mean() for c in dvs}
    active = [c for c in dvs if cv[c] >= MIN_CV_PCT]
    inactive = [c for c in dvs if cv[c] < MIN_CV_PCT]
    n_obs = len(df)
    n_obs_txt = f"{n_obs:,}".replace(",", ".")
    # audit.py'deki gibi pandas autocorr; acf() farkli paydayla daha dusuk verir
    long_ac = float(df[LONG_MEMORY_COL].autocorr(LONG_MEMORY_LAG))
    long_name = LONG_MEMORY_COL.replace(".C.Actual", "")
    lag1_dv = float(np.median([df[c].autocorr(1) for c in dvs]))
    lag1_dev = float(np.median([df[f"{o}.dev"].autocorr(1) for o in ins.output]))

    rows = []
    for _, orow in ins.iterrows():
        dev = df[f"{orow.output}.dev"]
        for c in dvs:
            res = corr_with_eff(df[c], dev)
            if res is None:
                continue
            rows.append(dict(
                output=orow.output, error_type=orow.error_type,
                driver=c.replace(".C.Actual", "")
                        .replace("FirstStage.CombinerOperation", "Combiner"),
                active="evet" if c in active else "hayir",
                cv_pct=round(cv[c], 2), **res))

    t = pd.DataFrame(rows)
    # yalnizca rapordaki karsilastirma icin; tabloya girmez
    med_neff_ar1 = float(t.pop("n_eff_ar1").median())
    med_neff = float(t.n_eff.median())
    t["abs_r"] = t.r.abs()
    t["sig_naive"] = t.p_naive < ALPHA
    t["sig_eff"] = (t.p_eff < ALPHA) & (t.n_eff >= MIN_N_EFF)
    # Coklu karsilastirma: 600 cift test ediliyor. alpha=0.05 ile sans eseri
    # ~30 tanesi "anlamli" cikar. Benjamini-Hochberg FDR ile duzeltilir.
    t["q_eff"] = bh_fdr(t.p_eff.to_numpy())
    t["sig_fdr"] = (t.q_eff < ALPHA) & (t.n_eff >= MIN_N_EFF)
    for c in ["r", "abs_r"]:
        t[c] = t[c].round(4)
    t["n_eff"] = t.n_eff.round(1)
    t["p_naive"] = t.p_naive.round(6)
    t["p_eff"] = t.p_eff.round(4)
    t["q_eff"] = t.q_eff.round(4)

    n_pairs = len(t)
    n_naive = int(t.sig_naive.sum())
    n_eff_sig = int(t.sig_eff.sum())
    n_fdr = int(t.sig_fdr.sum())

    lines = []
    w = lines.append
    w("# Faz 2 - Otokorelasyon Duzeltmeli Korelasyon Analizi\n")
    w("Kaynak: `data/processed/clean_v1.csv`  ")
    w("Uretildi: `python src/analysis/correlation.py`\n")
    w(f"{len(ins)} output deviation x {len(dvs)} karar degiskeni "
      f"= **{n_pairs} cift** incelendi.\n")

    w("## Yontem: neden efektif ornek buyuklugu\n")
    w(f"{n_obs_txt} gozlemle siradan bir anlamlilik testi yapilirsa `r = 0.02` bile")
    w(f"`p < {ALPHA}` verir. Ama ardisik gozlemler bagimsiz degil (K5: lag-1")
    w(f"otokorelasyon medyani karar degiskenlerinde {lag1_dv:.2f}, output sapmalarinda "
      f"{lag1_dev:.2f}). Bartlett'in **tam** duzeltmesi:\n")
    w("```")
    w("n_eff = n / (1 + 2 * sum_k (1 - k/n) * rho_x(k) * rho_y(k))")
    w("```")
    w("Yalnizca lag-1 kullanan basitlestirilmis surum AR(1) varsayar. Bu veride")
    w(f"seriler cok daha uzun hafizali (`{long_name}` lag-{LONG_MEMORY_LAG}'de "
      f"hala {long_ac:.2f}),")
    w("dolayisiyla lag-1 surumu otokorelasyonu ciddi sekilde eksik duzeltirdi --")
    w(f"ayni ciftlerde medyan n_eff'i {med_neff_ar1:.0f} verir; tam formul {med_neff:.0f}. "
      "Tum lag'ler")
    w("toplandi (kesim: n/4). Anlamlilik `n` yerine `n_eff` ile test edilir;")
    w(f"ayrica `n_eff < {MIN_N_EFF}` olan ciftler icin hic hukum verilmez.\n")

    w("## Duzeltmenin etkisi\n")
    w("![n_eff etkisi](figures/03_neff_effect.png)\n")
    w("| olcut | anlamli cift | oran |")
    w("|---|---|---|")
    w(f"| Ham n ile (**yanlis**) | {n_naive} / {n_pairs} | %{100*n_naive/n_pairs:.1f} |")
    w(f"| n_eff ile | {n_eff_sig} / {n_pairs} | %{100*n_eff_sig/n_pairs:.1f} |")
    w(f"| n_eff + FDR ile (**dogru**) | {n_fdr} / {n_pairs} | %{100*n_fdr/n_pairs:.1f} |")
    w("")
    w("Iki ayri duzeltme birlikte uygulaniyor:\n")
    w("1. **Otokorelasyon** (`n_eff`): her cift kendi icinde kac bagimsiz")
    w("   gozleme dayaniyor?")
    w(f"2. **Coklu karsilastirma** (Benjamini-Hochberg FDR): {n_pairs} cift test")
    w(f"   ediliyor. Hicbir gercek iliski olmasa bile alpha={ALPHA} ile ~"
      f"{int(ALPHA*n_pairs)} cift")
    w("   sans eseri anlamli cikardi. q-degeri bunu hesaba katar.\n")
    w(f"> **BULGU R1 - Duzeltme yapilmazsa {n_naive - n_fdr} sahte iliski")
    w("> raporlanirdi.** Ham testte ciftlerin %"
      f"{100*n_naive/n_pairs:.0f}'i 'anlamli' cikiyor; otokorelasyon ve coklu")
    w(f"> karsilastirma duzeltmelerinden sonra bu oran "
      f"%{100*n_fdr/n_pairs:.0f}'e dusuyor.")
    w("> Medyan efektif ornek buyuklugu **"
      f"{t.n_eff.median():.0f}** -- {n_obs_txt} degil. Yani veri seti, gorunen")
    w("> buyuklugune ragmen istatistiksel olarak kucuk bir ornektir (K1).\n")

    w("## Karar degiskenlerinin durumu\n")
    w("K7 geregi yalnizca gercekten oynatilmis degiskenler bilgi tasiyabilir.")
    w(f"**Aktif (CV >= %{MIN_CV_PCT:g}): {len(active)}**, **pasif: {len(inactive)}**.\n")
    w("| degisken | CV % | durum |")
    w("|---|---|---|")
    for c in sorted(dvs, key=lambda x: -cv[x]):
        short = c.replace(".C.Actual", "").replace("FirstStage.CombinerOperation", "Combiner")
        w(f"| `{short}` | {cv[c]:.2f} | {'aktif' if c in active else 'pasif'} |")
    w("")
    pas_sig = int(t[(t.active == 'hayir') & t.sig_fdr].shape[0])
    w(f"> **BULGU R2 - Pasif degiskenlerde bulunan {pas_sig} anlamli iliskiye")
    w("> temkinli yaklasilmali.** Bir degisken pratikte hic degismediyse, onunla")
    w("> output arasindaki korelasyon nedensel bir etkiden cok ortak zaman")
    w("> trendini yansitiyor olabilir. Bunlar Faz 3'te model uzerinden")
    w("> dogrulanmadan CPP sayilmayacak.\n")

    w("## En guclu iliskiler (n_eff duzeltmeli, anlamli olanlar)\n")
    sig = t[t.sig_fdr].nlargest(20, "abs_r")
    if len(sig):
        cols = ["output", "error_type", "driver", "active", "r", "n_eff",
                "p_eff", "q_eff"]
        w("| " + " | ".join(cols) + " |")
        w("|" + "|".join("---" for _ in cols) + "|")
        for _, r in sig.iterrows():
            w("| " + " | ".join(str(r[c]) for c in cols) + " |")
    else:
        w("*Duzeltmeden sonra anlamli kalan cift yok.*")
    w("")

    w("## Optimizasyon hedefi output'lar (variability-baskin)\n")
    w("Faz 4'un asil hedefi bunlar. Her biri icin en guclu **aktif** surukleyici:\n")
    vt = t[(t.error_type == "variability") & (t.active == "evet")]
    w("Iki sutun ayri tutuldu: en yuksek `|r|` gosteren surukleyici, cogu zaman")
    w("**anlamli olmayan** surukleyicidir -- cunku yuksek korelasyon genellikle")
    w("cok az bagimsiz gozleme dayaniyor. Karar icin sagdaki sutun kullanilir.\n")
    w("| output | en yuksek r | (r, n_eff) | FDR sonrasi anlamli en guclu | (r, n_eff) |")
    w("|---|---|---|---|---|")
    for out in ins[ins.error_type == "variability"].output:
        sub = vt[vt.output == out]
        if sub.empty:
            continue
        top = sub.loc[sub.abs_r.idxmax()]
        sig = sub[sub.sig_fdr]
        if len(sig):
            b = sig.loc[sig.abs_r.idxmax()]
            right = f"`{b.driver}` | ({b.r}, {b.n_eff})"
        else:
            right = "*yok* | -"
        w(f"| `{out}` | `{top.driver}` | ({top.r}, {top.n_eff}) | {right} |")
    w("")
    strong = vt[vt.sig_fdr & (vt.abs_r > STRONG_R)]
    w("> **BULGU R3 - Variability-baskin output'lar icin aktif karar")
    w(f"> degiskenleriyle abs(r) > {STRONG_R} olan **FDR-sonrasi anlamli** iliski "
      f"sayisi: **{len(strong)}**.")
    if len(strong) == 0:
        w("> Yani mevcut karar degiskenleri, optimize etmek istedigimiz")
        w("> output'lardaki yayilimi tek basina (dogrusal olarak) aciklamiyor.")
        w("> Bu, projeyi bitiren bir sonuc DEGIL -- dogrusal korelasyonun")
        w("> yakalayamadigi etkiler olabilir: gecikmeli etki, etkilesim,")
        w("> dogrusal olmayan iliski. Faz 3 tam olarak bunu test edecek.")
        w("> Ama beklentiyi simdiden dusurmek gerekir: **guclu ve basit bir")
        w("> surukleyici yok.**")
    else:
        for _, r in strong.nlargest(8, "abs_r").iterrows():
            w(f">   - `{r.output}` <- `{r.driver}`: r = {r.r} (n_eff {r.n_eff})")
    w("")

    n_full = 60
    w(f"## Tam tablo (ilk {n_full}, |r| azalan)\n")
    cols = ["output", "error_type", "driver", "active", "cv_pct", "r", "n",
            "n_eff", "p_naive", "p_eff", "q_eff", "sig_naive", "sig_eff",
            "sig_fdr"]
    w("| " + " | ".join(cols) + " |")
    w("|" + "|".join("---" for _ in cols) + "|")
    for _, r in t.nlargest(n_full, "abs_r").iterrows():
        w("| " + " | ".join(
            "" if pd.isna(r[c]) else str(r[c]) for c in cols) + " |")
    w("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    t.to_csv(ROOT / "reports" / "correlation_table.csv", index=False)

    print(f"yazildi: {OUT}")
    print("yazildi: reports/correlation_table.csv\n")
    print(f"cift sayisi        : {n_pairs}")
    print(f"ham n ile anlamli  : {n_naive} (%{100*n_naive/n_pairs:.1f})")
    print(f"n_eff ile anlamli  : {n_eff_sig} (%{100*n_eff_sig/n_pairs:.1f})")
    print(f"n_eff+FDR anlamli  : {n_fdr} (%{100*n_fdr/n_pairs:.1f})")
    print(f"medyan n_eff       : {t.n_eff.median():.0f}  (n = {n_obs})")
    print(f"\naktif karar degiskeni: {len(active)}/{len(dvs)}")
    print(f"variability-baskin output'lar icin |r|>{STRONG_R} anlamli iliski: {len(strong)}")


if __name__ == "__main__":
    main()
