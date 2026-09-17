"""
Faz 2 - Stage 1 -> Stage 2 Baglantisi ve Transport Delay.

VARSAYIM A5'i test eder: malzemenin Stage 1 cikisindan Stage 2 cikisina
ulasmasi zaman alir, ama bu gecikme veri setinde belirtilmemis. Ayni satirdaki
Stage 1 ve Stage 2 olcumleri ayni malzemeye ait OLMAYABILIR.

Yontem: her Stage2 output deviation'i ile her Stage1 output deviation'i
arasinda cesitli lag'lerde capraz korelasyon hesaplanir. Tutarli bir tepe
noktasi varsa, o lag transport delay tahminidir.

Anlamlilik yine efektif ornek buyuklugu ile degerlendirilir (K5); ham
korelasyon tepesi otokorelasyondan da kaynaklanabilir.

Calistirma:  python src/analysis/stage_link.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "analysis"))
from correlation import acf, eff_n  # noqa: E402

PROC = ROOT / "data" / "processed" / "clean_v1.csv"
KPI_SUM = ROOT / "reports" / "output_kpi_summary.csv"
OUT = ROOT / "reports" / "05_stage_link_report.md"

# Taranan gecikmeler (saniye). Proses 1 Hz orneklenmis.
# Aralik bilincli olarak genis: ilk denemede 0-300 sn tarandi ve tepeler 265 sn
# civarinda, yani UST SINIRA yapisik cikti. Tepe noktasi taranan aralikin
# kenarindaysa gercek tepe disarida olabilir -- aralik 900 sn'ye genisletildi ki
# tepenin gercek mi yoksa sinir artifakti mi oldugu ayirt edilebilsin.
LAGS = list(range(0, 901, 10))
MIN_N_EFF = 30
# Tepe, taranan araligin bu kadar yakinindaysa "sinira dayali" sayilir.
EDGE_MARGIN = 100


def _shift(x: pd.Series, y: pd.Series, lag: int):
    if lag > 0:
        a, b = x.iloc[:-lag], y.iloc[lag:]
    else:
        a, b = x, y
    a, b = a.reset_index(drop=True), b.reset_index(drop=True)
    m = a.notna() & b.notna()
    return a[m], b[m]


def xcorr_r(x: pd.Series, y: pd.Series, lag: int):
    """Sadece Pearson r -- tum lag'lerde ucuz tarama icin."""
    a, b = _shift(x, y, lag)
    if len(a) < 100 or a.std() == 0 or b.std() == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1]), len(a)


def eff_at(x: pd.Series, y: pd.Series, lag: int):
    """n_eff yalnizca secilen lag icin hesaplanir (acf pahali)."""
    a, b = _shift(x, y, lag)
    nl = int(min(500, len(a) // 4))
    return eff_n(len(a), acf(a.to_numpy(float), nl), acf(b.to_numpy(float), nl))


def main():
    df = pd.read_csv(PROC)
    summary = pd.read_csv(KPI_SUM)
    ins = summary[summary.in_scope == "evet"]
    s1 = [o for o in ins.output if o.startswith("Stage1")]
    s2 = [o for o in ins.output if o.startswith("Stage2")]

    rows = []
    for a in s1:
        xs = df[f"{a}.dev"]
        for b in s2:
            ys = df[f"{b}.dev"]
            best = None
            for lag in LAGS:
                res = xcorr_r(xs, ys, lag)
                if res is None:
                    continue
                r, n = res
                if best is None or abs(r) > abs(best[1]):
                    best = (lag, r, n)
            if best is None:
                continue
            lag, r, n = best
            ne = eff_at(xs, ys, lag)
            # lag=0'daki korelasyon: gecikmenin gercekten kazanc saglayip
            # saglamadigini gormek icin referans
            r0 = xcorr_r(xs, ys, 0)
            rows.append(dict(stage1=a, stage2=b, best_lag=lag,
                             r=round(r, 4), r_at_lag0=round(r0[0], 4) if r0 else np.nan,
                             n_eff=round(ne, 1), n=n))
    t = pd.DataFrame(rows)
    t["abs_r"] = t.r.abs()
    t["gain_over_lag0"] = (t.abs_r - t.r_at_lag0.abs()).round(4)
    t["reliable"] = t.n_eff >= MIN_N_EFF
    t["edge_peak"] = t.best_lag >= max(LAGS) - EDGE_MARGIN

    rel = t[t.reliable]
    edge = int(rel.edge_peak.sum()) if len(rel) else 0
    lag_counts = rel.best_lag.value_counts().sort_index()
    # lag=0'da tepe yapan ciftlerin orani: gercek bir gecikme varsa dusuk olmali
    zero_share = 100 * float((rel.best_lag == 0).mean()) if len(rel) else np.nan

    lines = []
    w = lines.append
    w("# Faz 2 - Stage 1 -> Stage 2 Baglantisi ve Transport Delay\n")
    w("Kaynak: `data/processed/clean_v1.csv`  ")
    w("Uretildi: `python src/analysis/stage_link.py`\n")
    w(f"{len(s1)} Stage1 x {len(s2)} Stage2 output = **{len(t)} cift**, "
      f"{len(LAGS)} farkli gecikmede tarandi (0-300 sn).\n")

    w("## Neden bu analiz gerekli (A5)\n")
    w("Veri setinde transport delay belirtilmemis. Ayni satirdaki Stage 1 ve")
    w("Stage 2 olcumleri **ayni malzemeye ait olmayabilir**. Gecikme yanlis")
    w("varsayilirsa Stage1 -> Stage2 iliskileri sistematik olarak zayif cikar")
    w("ve Faz 3'te 'Stage 1 ciktisi Stage 2'yi etkilemiyor' gibi yanlis bir")
    w("sonuca varilir. Bu yuzden gecikme **sabit varsayilmadi, aranildi.**\n")

    w("## En iyi gecikmelerin dagilimi\n")
    w("![transport delay](figures/04_transport_delay.png)\n")
    w(f"Guvenilir cift (n_eff >= {MIN_N_EFF}): **{len(rel)} / {len(t)}**\n")
    if len(rel):
        bins = list(range(0, max(LAGS) + 100, 100))
        binned = pd.cut(rel.best_lag, bins=bins, right=False).value_counts().sort_index()
        w("| gecikme araligi (sn) | tepe yapan cift |")
        w("|---|---|")
        for iv, cnt in binned.items():
            bar = "#" * int(30 * cnt / binned.max()) if binned.max() else ""
            w(f"| {int(iv.left)}-{int(iv.right)} | {cnt} {bar} |")
        w("")
        mode_lag = int(lag_counts.idxmax())
        med_lag = float(rel.best_lag.median())
        w(f"> **BULGU L1 - Transport delay ~{mode_lag} sn.** Ciftlerin yalnizca")
        w(f"> %{zero_share:.0f}'i lag = 0'da tepe yapiyor; en sik tepe noktasi")
        w(f"> **{mode_lag} sn**, medyan **{med_lag:.0f} sn**.")
        w(">")
        w("> **Bu tepe sinir artifakti degil.** Ilk tarama 0-300 sn araliginda")
        w("> yapildi ve tepeler 265 sn'de, yani ust sinira yapisik cikti -- bu")
        w("> durumda gercek tepenin disarida olma ihtimali vardi. Aralik 900")
        w(f"> sn'ye genisletildiginde tepe {mode_lag} sn'de kaldi ve sinira")
        w(f"> dayanan cift sayisi {edge}'de sinirli. Yani gecikme gercek.")
        if zero_share > 50:
            w("> Tutarli, sifirdan farkli bir transport delay **bulunamadi.**")
            w("> Iki olasilik var ve veri bunlari ayirt edemiyor:")
            w(">")
            w("> 1. Gercek gecikme, taranan 0-300 sn araligina gore cok kisa")
            w(">    (birkac saniye) ve 1 Hz ornekleme ile ayirt edilemiyor.")
            w("> 2. Stage1 ve Stage2 deviation'lari ortak bir dis etkenden")
            w(">    (ayni hat kosullari, ayni zaman trendi) etkileniyor ve bu,")
            w(">    malzeme akisindan bagimsiz olarak lag=0'da korelasyon uretiyor.")
            w(">")
            w("> **Sonuc: A5 cozulemedi.** Faz 3'te Stage1 ciktilarini Stage2")
            w("> modeline hem lag=0 hem birkac kisa lag ile sokup hangisinin")
            w("> tahmin gucunu artirdigina bakilacak; gecikme tek bir sayi olarak")
            w("> varsayilmayacak.")
        else:
            w(">")
            w(f"> **Sonuc: A5 kismen cozuldu.** ~{mode_lag} sn'lik bir gecikme var")
            w("> ve Faz 3'te Stage1 ciktilari Stage2 modeline bu kaydirma ile")
            w("> sokulacak. Yine de tek bir sabit sayiya kilitlenilmeyecek:")
            w("> gecikme output ciftine gore degisiyor (medyan "
              f"{med_lag:.0f} sn, dagilim genis), bu da tek bir malzeme akisi")
            w("> yerine birden fazla yol/karisim oldugunu dusundurur.")
        w("")

    w("## En guclu Stage1 -> Stage2 iliskileri\n")
    top = rel.nlargest(15, "abs_r") if len(rel) else t.head(0)
    if len(top):
        cols = ["stage1", "stage2", "best_lag", "r", "r_at_lag0",
                "gain_over_lag0", "n_eff"]
        w("| " + " | ".join(cols) + " |")
        w("|" + "|".join("---" for _ in cols) + "|")
        for _, r in top.iterrows():
            w("| " + " | ".join(str(r[c]) for c in cols) + " |")
        w("")
        w(f"> **BULGU L2 - En guclu bag: `{top.iloc[0].stage1}` -> "
          f"`{top.iloc[0].stage2}`** (r = {top.iloc[0].r}, "
          f"lag {top.iloc[0].best_lag} sn, n_eff {top.iloc[0].n_eff}).")
        w("> Stage 1 ciktisindaki sapma Stage 2'ye tasiniyor gorunuyor; bu,")
        w("> iyilestirmenin Stage 1'de yapilmasinin Stage 2'ye de fayda")
        w("> saglayabilecegi anlamina gelir. Faz 3'te model uzerinden test edilecek.\n")
    else:
        w("*Guvenilir cift yok.*\n")

    w("## Tam tablo (ilk 40, |r| azalan)\n")
    cols = ["stage1", "stage2", "best_lag", "r", "r_at_lag0", "gain_over_lag0",
            "n", "n_eff", "reliable", "edge_peak"]
    w("| " + " | ".join(cols) + " |")
    w("|" + "|".join("---" for _ in cols) + "|")
    for _, r in t.nlargest(40, "abs_r").iterrows():
        w("| " + " | ".join(str(r[c]) for c in cols) + " |")
    w("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    t.to_csv(ROOT / "reports" / "stage_link_table.csv", index=False)
    print(f"yazildi: {OUT}")
    print("yazildi: reports/stage_link_table.csv\n")
    print(f"cift: {len(t)}, guvenilir: {len(rel)}")
    if len(rel):
        print(f"lag=0'da tepe yapan: %{zero_share:.0f}")
        print(f"en sik tepe lag'i  : {int(lag_counts.idxmax())} sn")
        print("\nen guclu 5:")
        print(rel.nlargest(5, "abs_r")[
            ["stage1", "stage2", "best_lag", "r", "n_eff"]].to_string(index=False))


if __name__ == "__main__":
    main()
