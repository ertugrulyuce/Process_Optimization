"""
Faz 1 - Cleaning Pipeline.

Ham CSV -> data/processed/clean_v1.csv + deviation KPI'lari.

Her temizlik kuralinin gerekcesi audit bulgularina dayanir; hicbiri "genel
uygulama" diye uygulanmaz. Kurallar CLEANING_RULES icinde numaralanmis ve
uygulanan her kural rapora islenir.

Calistirma:  python src/data_processing/clean.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import schema  # noqa: E402
# K2: bu esigin altinda gecerli verisi olan output modellenemez (A3). Esik
# audit.py'de tanimli; burada ayrica yazilirsa audit'in "modellenemez" listesi
# ile R6 kapsami sessizce ayrisabilir.
from audit import MIN_VALID_RATIO  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "continuous_factory_process.csv"
PROC = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "02_cleaning_report.md"

# Bir setpoint'in anlamli hedef sayilabilmesi icin, sapmanin standart
# sapmasindan buyuk olmasi gerekir. Altinda kalirsa hedef olcum gurultusunden
# ayirt edilemez ve ona bolen her oran (rel_dev, bias_pct) patlar.
# Esik veriden dogruluyor: Stage2.M6 orani 0.05, bir sonraki output 3.79 --
# arada buyuk bosluk var, yani 1.0 keyfi bir kesim degil.
MIN_SETPOINT_TO_STD = 1.0

# Bias / variability ayriminin belirsiz kaldigi bant. Disinda kalanlar net
# siniflandirilir; icine dusen output "belirsiz" sayilir ve tek bir esige
# dayanarak kategoriye zorlanmaz.
BIAS_BAND = (40.0, 60.0)

# R8: bir olcum, setpoint'inin bu kesrinden kucukse fiziksel sayilmaz.
# Veride tam sifir olmayan ama 1e-100..1e-306 mertebesinde degerler var --
# float underflow artifakti. Gercek olcumler setpoint'in %50-150'si
# civarinda oldugu icin %1 esigi genis bir bosluga dusuyor, keyfi degil.
TINY_FRAC = 0.01

# K8: birebir ozdes kolon ciftlerinden dusurulecek olan.
# Machine4.Temperature4 (14-25) diger Machine4 sicakliklariyla (260-396)
# uyumsuz, Pressure ile (14-25) birebir ayni -> yanlis adlandirilmis kopya.
DROP_DUPLICATE_COLS = ["Machine4.Temperature4.C.Actual"]

CLEANING_RULES = {
    "R1": "Output Actual'lardaki tam 0 -> NaN (K2/A2: sensor dropout, olcum degil)",
    "R2": "Output Actual'lardaki negatif degerler -> NaN (K2/O3: boyut negatif olamaz)",
    "R3": "Birebir ozdes kolon dusuruldu (K8: yapay multicollinearity)",
    "R4": "Duplicate timestamp'ler isaretlendi, satir silinmedi (veri kaybi olmasin)",
    "R5": "Stage1 setpoint == 0 olan satirlar durus blogu olarak isaretlendi (K3)",
    # R6-R8 metinleri esiklerden uretiliyor: esik degisip metin eski kalirsa
    # rapordaki kural tablosu kodun yapmadigi bir seyi anlatir.
    "R6": f"Gecerli veri orani < %{MIN_VALID_RATIO * 100:.0f} olan output'lar "
          "'kapsam disi' isaretlendi (A3)",
    # not: 'abs(setpoint)' yazimi bilincli -- '|setpoint|' markdown tablosunda
    # hucre ayraci sanilip satiri bolerdi.
    "R7": f"abs(setpoint)/dev_std < {MIN_SETPOINT_TO_STD} olan output'lar "
          "'setpoint anlamsiz' olarak kapsam disi birakildi -- oransal KPI'lari "
          "tanimsiz (A8)",
    "R8": f"abs(olcum) < {TINY_FRAC} x abs(setpoint) olan (ama sifir olmayan) "
          "olcumler -> NaN. Float underflow artifakti; sadece '== 0' testi "
          "bunlari kaciriyordu.",
}


def load_raw():
    df = pd.read_csv(RAW)
    df["time_stamp"] = pd.to_datetime(df["time_stamp"])
    return df


def clean(df):
    log = {}
    df = df.copy()

    # --- R3: ozdes kolonlari dusur ---
    present = [c for c in DROP_DUPLICATE_COLS if c in df.columns]
    df = df.drop(columns=present)
    log["R3_dropped"] = present

    # --- R4: duplicate timestamp isaretle ---
    df["flag_dup_timestamp"] = df["time_stamp"].duplicated(keep=False)
    log["R4_dup_rows"] = int(df["flag_dup_timestamp"].sum())
    # Satir sirasi asil zaman eksenidir; jitter'a ragmen sira monotonik.
    df["seq"] = np.arange(len(df))

    # --- R5: durus blogu (Stage1 setpoint 0) ---
    sp1 = [c for c in df.columns
           if c.startswith("Stage1.Output") and c.endswith(".Setpoint")]
    df["flag_downtime"] = (df[sp1] == 0).all(axis=1)
    log["R5_downtime_rows"] = int(df["flag_downtime"].sum())

    # --- R1 + R2 + R8: output actual temizligi ---
    actual_cols = [c for c in df.columns
                   if schema.classify(c) == schema.OUT_ACTUAL]
    n_zero = n_neg = n_tiny = 0
    for c in actual_cols:
        sp_col = c.replace(".Actual", ".Setpoint")
        sp = abs(float(df[sp_col].max())) if sp_col in df.columns else 0.0
        v = df[c]
        z = v == 0
        n = v < 0
        # R8: tam sifir olmayan ama fiziksel olarak imkansiz derecede kucuk
        # degerler (float underflow artifakti: 1e-100, 1e-306 gibi). Sadece
        # `== 0` testi bunlari kaciriyordu.
        tiny = (~z) & (v.abs() > 0) & (v.abs() < sp * TINY_FRAC)
        n_zero += int(z.sum())
        n_neg += int(n.sum())
        n_tiny += int(tiny.sum())
        df.loc[z | n | tiny, c] = np.nan
    log["R1_zeros_to_nan"] = n_zero
    log["R2_negatives_to_nan"] = n_neg
    log["R8_tiny_to_nan"] = n_tiny
    log["actual_cols"] = actual_cols

    return df, log


def build_kpis(df):
    """
    Her output icin deviation KPI'lari.

    K6 geregi bias (merkezleme) ve variability (dagilim) AYRI tutulur:
    ikisi farkli muhendislik problemleridir ve farkli aksiyon gerektirir.
    Toplam hatayi tek sayida birlestirmek optimizasyonun yanlis seyi
    kovalamasina yol acar.
    """
    kpi = pd.DataFrame(index=df.index)
    rows = []

    for st in schema.STAGES:
        for i in range(schema.N_MEASUREMENTS):
            a_col = f"{st}.Output.Measurement{i}.U.Actual"
            s_col = f"{st}.Output.Measurement{i}.U.Setpoint"
            name = f"{st}.M{i}"

            a = df[a_col]
            s = df[s_col].replace(0, np.nan)  # durus blogunda hedef tanimsiz

            dev = a - s
            kpi[f"{name}.dev"] = dev
            kpi[f"{name}.abs_dev"] = dev.abs()
            kpi[f"{name}.rel_dev_pct"] = 100 * dev / s

            valid = a.notna()
            n_valid = int(valid.sum())
            valid_ratio = n_valid / len(a)
            sp = float(s.dropna().iloc[0]) if s.notna().any() else np.nan
            dev_std = float(dev.std())

            # R7: setpoint olcum gurultusunden ayirt edilebiliyor mu?
            sp_over_std = abs(sp) / dev_std if dev_std else np.nan
            sp_meaningful = bool(sp_over_std >= MIN_SETPOINT_TO_STD)

            rows.append(dict(
                output=name,
                setpoint=round(sp, 3),
                n_valid=n_valid,
                valid_pct=round(100 * valid_ratio, 1),
                sp_over_std=round(sp_over_std, 2),
                # bias: ortalama isaretli sapma (merkezleme hatasi)
                bias=round(float(dev.mean()), 4),
                # setpoint anlamsizsa oransal KPI da anlamsiz -> hesaplanmaz
                bias_pct=round(float(100 * dev.mean() / sp), 2) if sp_meaningful else np.nan,
                # variability: sapmanin dagilimi (kararlilik)
                dev_std=round(dev_std, 4),
                mae=round(float(dev.abs().mean()), 4),
                rmse=round(float(np.sqrt((dev ** 2).mean())), 4),
                cv_pct=round(float(100 * a.std() / a.mean()), 2) if a.notna().any() else np.nan,
                sp_meaningful=sp_meaningful,
            ))

    summary = pd.DataFrame(rows)

    # RMSE'yi bias ve variability bilesenlerine ayir: RMSE^2 = bias^2 + std^2
    summary["bias_share_pct"] = (
        100 * summary.bias ** 2 / (summary.bias ** 2 + summary.dev_std ** 2)
    ).round(1)

    # --- kapsam: iki ayri gerekce, hangisi oldugu kayitli kalir ---
    def scope_reason(r):
        if r.valid_pct < MIN_VALID_RATIO * 100:
            return f"kapsam disi: gecerli veri %{r.valid_pct} < %{MIN_VALID_RATIO*100:.0f} (R6)"
        if not r.sp_meaningful:
            # not: 'abs(sp)' yazimi bilincli -- '|sp|' markdown tablosunda
            # hucre ayraci sanilip satiri bolerdi.
            return (f"kapsam disi: setpoint anlamsiz, "
                    f"abs(sp)/std={r.sp_over_std} < {MIN_SETPOINT_TO_STD} (R7)")
        return "kapsam ici"

    summary["scope_reason"] = summary.apply(scope_reason, axis=1)
    summary["in_scope"] = np.where(summary.scope_reason == "kapsam ici", "evet", "HAYIR")

    # --- bias / variability siniflandirmasi, belirsiz bandi ile ---
    lo, hi = BIAS_BAND

    def err_type(r):
        if r.in_scope != "evet":
            return "-"
        if r.bias_share_pct > hi:
            return "bias"
        if r.bias_share_pct < lo:
            return "variability"
        return "belirsiz"

    summary["error_type"] = summary.apply(err_type, axis=1)
    return kpi, summary


def write_report(df_raw, df, log, summary):
    lines = []
    w = lines.append
    w("# Faz 1 - Cleaning Report\n")
    w("Kaynak: `data/raw/continuous_factory_process.csv`  ")
    w("Uretildi: `python src/data_processing/clean.py`\n")

    w("## Uygulanan kurallar\n")
    w("| # | Kural |")
    w("|---|---|")
    for k, v in CLEANING_RULES.items():
        w(f"| {k} | {v} |")
    w("")

    w("## Etki\n")
    w(f"- Girdi: **{df_raw.shape[0]:,} x {df_raw.shape[1]}**")
    w(f"- Cikti: **{df.shape[0]:,} x {df.shape[1]}** (3 flag + 1 seq kolonu eklendi)")
    w(f"- **R3** dusurulen kolon: {log['R3_dropped']}")
    w(f"- **R1** NaN'a cevrilen sifir: **{log['R1_zeros_to_nan']:,}** hucre")
    w(f"- **R2** NaN'a cevrilen negatif: **{log['R2_negatives_to_nan']:,}** hucre")
    w(f"- **R8** NaN'a cevrilen imkansiz-kucuk deger: "
      f"**{log['R8_tiny_to_nan']:,}** hucre")
    w(f"- **R4** duplicate timestamp'li satir: {log['R4_dup_rows']} (silinmedi, isaretlendi)")
    w("  <br>*Not:* audit raporu 14 diyor cunku `duplicated()` her tekrarin ilk")
    w("  gorunumunu saymaz. Burada `keep=False` ile cakismanin **her iki tarafi**")
    w("  isaretleniyor; ayni olayin iki farkli sayimi.")
    w(f"- **R5** durus blogu satiri: {log['R5_downtime_rows']} (silinmedi, isaretlendi)")
    total_cells = len(df) * len(log["actual_cols"])
    touched = (log["R1_zeros_to_nan"] + log["R2_negatives_to_nan"]
               + log["R8_tiny_to_nan"])
    w(f"\nOutput olcum hucrelerinin **%{100 * touched / total_cells:.1f}**'i NaN'a cevrildi "
      f"({touched:,} / {total_cells:,}). Hicbir satir silinmedi.\n")

    w("### Neden hicbir satir silinmedi?\n")
    w("Sifirlar tek bir durus blogunda toplanmis olsa satir bazli filtreleme")
    w("dogru olurdu. Ama audit gosterdi ki sifirlar yuzlerce kisa kesinti halinde")
    w("dagilmis (Stage1.M14 -> 673 ayri kesinti) ve her output'ta FARKLI")
    w("satirlarda. Satir silmek, bir output'un dropout'u yuzunden diger 25")
    w("output'un gecerli olcumunu de atmak demekti. Bunun yerine hucre bazli")
    w("NaN kullanildi; her output kendi gecerli verisiyle analiz edilir.\n")

    w("## Output KPI ozeti\n")
    # Figurler figures.py tarafindan uretilir; linkleri burada yaziliyor ki
    # rapor yeniden uretildiginde gomme kaybolmasin.
    w("![bias vs variability](figures/01_bias_vs_variability.png)\n")
    w("![kontrol grafikleri](figures/02_control_charts.png)\n")
    w("`bias` = ortalama isaretli sapma (merkezleme hatasi).  ")
    w("`dev_std` = sapmanin standart sapmasi (kararlilik).  ")
    w("`bias_share_pct` = toplam hatanin (RMSE^2) yuzde kaci bias'tan geliyor.\n")
    w("Bu ayrim K6 geregi: **bias bir ayar problemi, variability bir kontrol")
    w("problemidir.** Ikisi farkli aksiyon gerektirir.\n")
    cols = ["output", "setpoint", "valid_pct", "sp_over_std", "bias", "bias_pct",
            "dev_std", "mae", "rmse", "bias_share_pct", "error_type", "in_scope"]
    w("| " + " | ".join(cols) + " |")
    w("|" + "|".join("---" for _ in cols) + "|")
    for _, r in summary.iterrows():
        w("| " + " | ".join(
            "" if pd.isna(r[c]) else str(r[c]) for c in cols) + " |")
    w("")

    ins = summary[summary.in_scope == "evet"]
    bias_dom = ins[ins.error_type == "bias"].sort_values("bias_share_pct", ascending=False)
    var_dom = ins[ins.error_type == "variability"].sort_values("dev_std", ascending=False)
    unclear = ins[ins.error_type == "belirsiz"]
    lo, hi = BIAS_BAND

    w("## Kapsam\n")
    w(f"{schema.N_OUTPUTS} output'un **{len(ins)}**'i analize giriyor. Kapsam disi kalanlar, "
      "hangi gerekceyle cikarildiklariyla birlikte:\n")
    w("| output | gerekce |")
    w("|---|---|")
    for _, r in summary[summary.in_scope != "evet"].iterrows():
        w(f"| `{r.output}` | {r.scope_reason} |")
    w("")
    w("> **R7 neden gerekti:** `Stage2.M6`'nin setpoint'i 0.01, sapmasinin standart")
    w("> sapmasi 0.197. Hedef, olcum gurultusunun yirmide biri kadar -- yani gercek")
    w("> bir hedef degil, girilmemis/kullanilmayan bir alan. Ona bolununce bias")
    w("> **%5295** cikiyordu ve output yanlislikla 'bias-baskin' siniflaniyordu.")
    w("> Esik veriden dogruluyor: M6'nin abs(sp)/std orani 0.05, bir sonraki output")
    w("> 3.79 -- arada buyuk bosluk var, kesim keyfi degil.\n")

    w("## Bulgular\n")
    w(f"> **Bias-baskin ({len(bias_dom)} adet)** - hatanin >%{hi:.0f}'i merkezleme")
    w("> kaymasindan. Bir **ayar/kalibrasyon** problemi; proses kararli ama yanlis")
    w("> noktada calisiyor:")
    for _, r in bias_dom.head(6).iterrows():
        pct = f" ({r.bias_pct:+.1f}%)" if pd.notna(r.bias_pct) else ""
        w(f">   - `{r.output}`: bias {r.bias:+.3f}{pct}, hatanin %{r.bias_share_pct}'i bias")
    w(">")
    w(f"> **Variability-baskin ({len(var_dom)} adet)** - hatanin <%{lo:.0f}'i bias.")
    w("> Bir **proses kontrol** problemi; optimizasyonun asil hedefi:")
    for _, r in var_dom.head(6).iterrows():
        w(f">   - `{r.output}`: dev_std {r.dev_std:.3f}, "
          f"hatanin sadece %{r.bias_share_pct}'i bias")
    if len(unclear):
        w(">")
        w(f"> **Belirsiz ({len(unclear)} adet)** - `bias_share_pct` %{lo:.0f}-%{hi:.0f}")
        w("> bandinda. Bias ve variability bilesenleri neredeyse esit; tek bir esige")
        w("> dayanarak kategoriye zorlanmadi:")
        for _, r in unclear.iterrows():
            w(f">   - `{r.output}`: bias {r.bias:.4f} ~ dev_std {r.dev_std:.4f} "
              f"(bias payi %{r.bias_share_pct})")
    w("")
    w("> **Neden onemli:** Bias-baskin bir output'u optimizasyonla kovalamak")
    w("> yanlistir - cozumu setpoint'i duzeltmektir, proses parametresi oynatmak")
    w("> degil. Optimizasyon variability-baskin output'lara odaklanir. Belirsiz")
    w("> olanlar Faz 2'de control chart'la incelenip karara baglanir.\n")

    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main():
    df_raw = load_raw()
    df, log = clean(df_raw)
    kpi, summary = build_kpis(df)

    PROC.mkdir(parents=True, exist_ok=True)
    out = pd.concat([df, kpi], axis=1)
    out.to_csv(PROC / "clean_v1.csv", index=False)
    summary.to_csv(ROOT / "reports" / "output_kpi_summary.csv", index=False)
    write_report(df_raw, df, log, summary)

    ins = summary[summary.in_scope == "evet"]
    print(f"yazildi: data/processed/clean_v1.csv  ({out.shape[0]:,} x {out.shape[1]})")  # noqa: E501
    print(f"yazildi: {REPORT}")
    print("yazildi: reports/output_kpi_summary.csv\n")
    print(f"R1 sifir->NaN     : {log['R1_zeros_to_nan']:,} hucre")
    print(f"R2 negatif->NaN   : {log['R2_negatives_to_nan']:,} hucre")
    print(f"R8 imkansiz-kucuk : {log['R8_tiny_to_nan']:,} hucre")
    print(f"R3 dusurulen kolon: {log['R3_dropped']}")
    print(f"R4 dup timestamp  : {log['R4_dup_rows']} satir (isaretlendi)")
    print(f"R5 durus blogu    : {log['R5_downtime_rows']} satir (isaretlendi)")
    print(f"\nkapsam ici output : {len(ins)}/{schema.N_OUTPUTS}")
    for reason, n in summary[summary.in_scope != "evet"].scope_reason.value_counts().items():
        print(f"  kapsam disi ({n}): {reason}")
    print()
    for et in ("bias", "variability", "belirsiz"):
        sub = ins[ins.error_type == et]
        print(f"{et:12}: {len(sub):2}  {', '.join(sub.output)}")


if __name__ == "__main__":
    main()
