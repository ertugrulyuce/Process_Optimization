"""
Faz 1 - Data Audit.

Ham CSV'yi hicbir sey degistirmeden inceler ve reports/01_data_quality_report.md
uretir. Bu script veri YAZMAZ; sadece teshis koyar. Temizlik kurallari audit
sonuclarina bakilarak clean.py icinde tanimlanir.

Calistirma:  python src/data_processing/audit.py
"""
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import schema  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "continuous_factory_process.csv"
OUT = ROOT / "reports" / "01_data_quality_report.md"

# Bir output olcumunun modellemeye alinabilmesi icin gereken en dusuk gecerli
# veri orani. Esik keyfi degil: %50'nin altinda kalan bir seride deviation
# KPI'si serinin kendisinden cok dropout desenini olcer.
MIN_VALID_RATIO = 0.50

# Zaman ekseninde "bosluk" sayilan adim (sn) ve "dusuk kardinalite" ust siniri.
# Rapor metni bu sabitlerden uretilir.
GAP_THRESHOLD_S = 60
LOW_CARD_LIMIT = 10


def load() -> pd.DataFrame:
    df = pd.read_csv(RAW)
    df["time_stamp"] = pd.to_datetime(df["time_stamp"])
    return df


def sec_time(df: pd.DataFrame) -> dict[str, Any]:
    t = df["time_stamp"]
    d = t.diff().dt.total_seconds()
    return dict(
        start=t.min(), end=t.max(), span=t.max() - t.min(), n=len(t),
        monotonic=bool(t.is_monotonic_increasing),
        dup_ts=int(t.duplicated().sum()),
        step_counts=d.value_counts().head(5).to_dict(),
        step_mode=float(d.mode().iloc[0]),
        gaps_gt_60s=int((d > GAP_THRESHOLD_S).sum()),
        span_hours=(t.max() - t.min()).total_seconds() / 3600,
    )


def sec_outputs(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for st in schema.STAGES:
        for i in range(schema.N_MEASUREMENTS):
            a = df[f"{st}.Output.Measurement{i}.U.Actual"]
            s = df[f"{st}.Output.Measurement{i}.U.Setpoint"]
            zero = a == 0
            nz = a[~zero]
            iz = zero.astype(int)
            runs = int((iz.diff() == 1).sum()) + int(iz.iloc[0])
            rows.append(dict(
                output=f"{st}.M{i}",
                setpoint=round(s.max(), 3),
                sp_unique=int(s.nunique()),
                zero_pct=round(100 * zero.mean(), 1),
                zero_runs=runs,
                neg_count=int((a < 0).sum()),
                valid_pct=round(100 * (~zero).mean(), 1),
                nz_mean=round(nz.mean(), 3) if len(nz) else np.nan,
                nz_std=round(nz.std(), 4) if len(nz) else np.nan,
            ))
    t = pd.DataFrame(rows)
    t["cv_pct"] = (t.nz_std / t.nz_mean * 100).round(1)
    t["bias_pct"] = ((t.nz_mean - t.setpoint) / t.setpoint * 100).round(1)
    t["modelable"] = np.where(t.valid_pct >= MIN_VALID_RATIO * 100, "evet", "HAYIR")
    return t


def sec_autocorr(df: pd.DataFrame, cols: Sequence[str],
                 lags: Sequence[int] = (1, 30, 60, 300, 600)) -> pd.DataFrame:
    rows = []
    for c in cols:
        x = df[c]
        r: dict[str, Any] = {"column": c}
        for lag in lags:
            r[f"lag{lag}"] = round(x.autocorr(lag), 3)
        rows.append(r)
    return pd.DataFrame(rows)


def sec_constants(df: pd.DataFrame) -> dict[str, Any]:
    num = df.drop(columns=["time_stamp"])
    nu = num.nunique()
    return dict(
        constant=list(nu[nu == 1].index),
        two_valued=list(nu[nu == 2].index),
        low_card={c: int(nu[c]) for c in nu[(nu > 2) & (nu < LOW_CARD_LIMIT)].index},
    )


def raw_levels(df: pd.DataFrame, machine: str) -> tuple[int, str]:
    """Makinenin hammadde kolon sayisi ve aldiklari farkli deger sayisi ("2", "4-5")."""
    cols = [c for c in df.columns
            if schema.classify(c) == schema.RAW_MAT and c.startswith(f"{machine}.")]
    nu = [int(df[c].nunique()) for c in cols]
    lv = str(min(nu)) if min(nu) == max(nu) else f"{min(nu)}-{max(nu)}"
    return len(cols), lv


def md_table(df: pd.DataFrame) -> str:
    """DataFrame -> markdown tablo. tabulate bagimliligindan kacinmak icin elle."""
    cols = list(df.columns)
    head = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    body = [
        "| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |"
        for row in df.itertuples(index=False, name=None)
    ]
    return "\n".join([head, sep] + body)


def main() -> None:
    df = load()
    sch = pd.DataFrame(schema.build(df.columns))
    time = sec_time(df)
    outs = sec_outputs(df)
    consts = sec_constants(df)
    dv = schema.decision_variables(df.columns)
    ac = sec_autocorr(
        df,
        dv[:6]
        + schema.noise_variables(df.columns)[:2]
        + ["Stage1.Output.Measurement0.U.Actual",
           "Stage2.Output.Measurement0.U.Actual"],
    )

    lines: list[str] = []
    w = lines.append
    w("# Faz 1 - Data Quality Report\n")
    w("Kaynak: `data/raw/continuous_factory_process.csv`  ")
    w("Uretildi: `python src/data_processing/audit.py`\n")

    w("## 1. Sema\n")
    w(f"- Boyut: **{df.shape[0]:,} satir x {df.shape[1]} kolon**")
    w(f"- Eksik deger (NaN): **{int(df.isna().sum().sum())}**")
    w(f"- Tam duplicate satir: **{int(df.duplicated().sum())}**")
    w(f"- Veri tipleri: {df.dtypes.value_counts().to_dict()}\n")
    w("Degisken rolleri (bkz. `src/data_processing/schema.py`, VARSAYIM A1):\n")
    w(md_table(sch.groupby("role").size().reset_index(name="adet")))
    w("")

    w("## 2. Zaman ekseni\n")
    w(f"- Aralik: **{time['start']} -> {time['end']}**")
    w(f"- Toplam sure: **{time['span']}** (~{time['span_hours']:.1f} saat)")
    w(f"- Ornekleme: {1 / time['step_mode']:g} Hz. "
      f"Adim dagilimi (sn): {time['step_counts']}")
    w(f"- Monotonik artan: {time['monotonic']}")
    w(f"- **Duplicate timestamp: {time['dup_ts']}**")
    w(f"- {GAP_THRESHOLD_S} sn'den buyuk bosluk: {time['gaps_gt_60s']}\n")
    n_rows_tr = f"{df.shape[0]:,}".replace(",", ".")  # Turkce binlik ayraci
    w(f"> **BULGU Z1 - Veri tek bir ~{time['span_hours']:.0f} saatlik pencereden "
      f"geliyor.** {n_rows_tr} satir")
    w("> cok gorunuyor ama bagimsiz gozlem sayisi degil. Long-term process")
    w("> capability, vardiya/rejim karsilastirmasi ve gun-ici trend analizi bu")
    w("> veriyle YAPILAMAZ. Faz 2 short-term capability ile sinirlidir.\n")

    w("## 3. Sabit ve dusuk-kardinaliteli kolonlar\n")
    w(f"- Tek degerli (sifir varyans): **{len(consts['constant'])} kolon** - "
      "tamami Stage2 setpoint'leri")
    w(f"- Iki degerli: **{len(consts['two_valued'])} kolon**")
    w(f"- Kardinalitesi {LOW_CARD_LIMIT} altinda olan digerleri: {consts['low_card']}\n")
    n_s2_const = sum(1 for c in consts["constant"]
                     if schema.classify(c) == schema.OUT_SETPNT and c.startswith("Stage2."))
    n_m2, lv_m2 = raw_levels(df, "Machine2")
    _, lv_m3 = raw_levels(df, "Machine3")
    w("> **BULGU S1 - Setpoint'ler degisken degil, sabit hedeftir.** Stage2'nin")
    w(f"> {n_s2_const} setpoint'i tek deger; Stage1'inkiler sabit + durus blogunda 0.")
    w("> Sonuc: setpoint bir MODEL GIRDISI olarak kullanilamaz (sifir bilgi).")
    w("> Tek rolu, deviation KPI'sinin referans noktasi olmaktir.\n")
    w(f"> **BULGU S2 - Hammadde ozellikleri neredeyse sabit.** Machine2'nin {n_m2}")
    w(f"> Property'si {lv_m2}, Machine3'unkiler {lv_m3} farkli deger aliyor. Hammadde")
    w("> varyasyonu bu veri setinde zayif bir aciklayici degiskendir.\n")

    w("## 4. Output olcum kalitesi\n")
    w(md_table(outs))
    w("")
    bad = outs[outs.modelable == "HAYIR"]
    # Ornekler: en parcali kesintili output ve en yuksek sifir oranli output
    frag = outs.loc[outs.zero_runs.idxmax()]
    worst = outs.loc[outs.zero_pct.idxmax()]
    w("> **BULGU O1 - Sifirlar eksik veridir, olcum degil.** Sifirlar bitisik tek")
    w("> bir durus blogunda degil, yuzlerce kisa kesinti halinde dagilmis")
    w(f"> (ornegin {frag.output}: {frag.zero_runs} ayri kesinti). "
      f"Setpoint'i {worst.setpoint} olan bir")
    w(f"> boyutun %{worst.zero_pct:.0f} oraninda tam 0 olmasi fiziksel degil, "
      "sensor dropout'tur.")
    w("> Bu degerler NaN'a cevrilmeli, sifir olarak modele girmemelidir.\n")
    w(f"> **BULGU O2 - {len(bad)} output modellenemez** "
      f"(gecerli veri < %{MIN_VALID_RATIO * 100:.0f}): "
      f"{', '.join(bad.output)}. Kapsam disi birakilir.\n")
    w("> **BULGU O3 - Negatif olcumler var.** Boyutsal olcum negatif olamaz;")
    w("> impossible value olarak isaretlenmelidir.\n")
    w("> **BULGU O4 - Bazi output'lar setpoint'ten sistematik sapiyor** (bias):")
    order = outs.bias_pct.abs().sort_values(ascending=False).index
    for _, r in outs.reindex(order).head(5).iterrows():
        w(f">   - `{r.output}`: hedef {r.setpoint}, gerceklesen ort. {r.nz_mean} "
          f"(**{r.bias_pct:+.1f}%**)")
    w("> Bu bir merkezleme (centering) problemidir; variability'den ayri ele alinir.\n")

    w("## 5. Otokorelasyon\n")
    w(md_table(ac))
    w("")
    w("> **BULGU A1 - Ardisik gozlemler bagimsiz degil.** Karar degiskenlerinde")
    w("> lag-1 otokorelasyonu 0.99'a ulasiyor. **Rastgele train/test split")
    w("> kullanilirsa test seti train setinin neredeyse kopyasi olur ve R2")
    w("> sahte sekilde yuksek cikar.** Bloklu / zaman-sirali split zorunludur.\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    outs.to_csv(ROOT / "reports" / "output_quality_table.csv", index=False)
    sch.to_csv(ROOT / "reports" / "variable_schema.csv", index=False)
    print(f"yazildi: {OUT}")
    print("yazildi: reports/output_quality_table.csv")
    print("yazildi: reports/variable_schema.csv")
    print(f"\nmodellenemez output ({len(bad)}): {list(bad.output)}")


if __name__ == "__main__":
    main()
