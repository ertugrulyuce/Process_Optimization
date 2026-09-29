"""
Faz 1 - Data Dictionary uretici.

Ham veri + sema + audit istatistiklerini birlestirip reports/data_dictionary.md
uretir. Elle yazilmaz: veri degisirse yeniden calistirilir, boylece sozluk
veriyle senkron kalir.

Calistirma:  python src/data_processing/data_dictionary.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import schema  # noqa: E402
from clean import DROP_DUPLICATE_COLS  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "continuous_factory_process.csv"
OUT = ROOT / "reports" / "data_dictionary.md"

# {alan}'lar main() icinde veriden doldurulur (bkz. role_facts)
ROLE_DESC = {
    "time": "Zaman damgasi ({hz:g} Hz).",
    schema.AMBIENT: "Cevre kosulu. Kontrol edilemez. Efektif ornekleme ~{amb_period:.0f} sn "
                    "(K4) -> {hours:.0f} saatte ~{amb_obs} bagimsiz gozlem.",
    schema.RAW_MAT: "Gelen hammadde ozelligi. Kontrol edilemez. {lv_min}-{lv_max} ayrik "
                    "seviye, cok seyrek degisim (K4) -> lot etiketi gibi ele alinir.",
    schema.CONTROLLED: "Operatorun ayarlayabildigi parametre (VARSAYIM A1). "
                       "Optimizasyonun karar degiskeni.",
    schema.MEASURED: "Proses tepkisi. Ayarlanmaz, olculur. Teshis degiskeni; "
                     "optimizasyonda karar degiskeni DEGIL.",
    schema.OUT_ACTUAL: "Urun boyutsal olcumu. Optimize edilen cikti. "
                       "Tam 0 = sensor dropout (R1), negatif = imkansiz (R2).",
    schema.OUT_SETPNT: "Hedef deger. SABIT (K3) -> model girdisi degil, "
                       "yalnizca deviation'in referans noktasi.",
}

STAGE_DESC = {
    "ambient": "Hat disi cevre",
    "stage1": "Stage 1 - Machine 1/2/3 (paralel)",
    "stage2": "Stage 2 - Machine 4/5 (seri)",
    "combiner": "Stage 1 birlestirme adimi",
    "stage1_out": "Stage 1 cikti olcumu (combiner sonrasi)",
    "stage2_out": "Stage 2 cikti olcumu (nihai)",
    "-": "-",
}


def role_facts(df: pd.DataFrame, t: pd.DataFrame) -> dict[str, float | int]:
    """ROLE_DESC metnindeki sayilar: kayit frekansi, pencere, ambient/hammadde."""
    ts = df["time_stamp"]
    # verify_a1 ile ayni sayim: ilk satirin NaN farki degisim sayilmaz
    amb_obs = max(int((df[c].diff().dropna() != 0).sum())
                  for c in t.column[t.role == schema.AMBIENT])
    lv = t.n_unique[t.role == schema.RAW_MAT]
    return dict(
        hz=1 / ts.diff().dt.total_seconds().mode().iloc[0],
        hours=(ts.max() - ts.min()).total_seconds() / 3600,
        amb_obs=amb_obs,
        # "~" degeri onlar basamagina yuvarlanir (352 -> 350)
        amb_period=round(len(df) / amb_obs, -1),
        lv_min=int(lv.min()),
        lv_max=int(lv.max()),
    )


def main() -> None:
    df = pd.read_csv(RAW)
    df["time_stamp"] = pd.to_datetime(df["time_stamp"])

    rows = []
    for c in df.columns:
        role = schema.classify(c)
        s = df[c]
        rec = dict(
            column=c,
            role=role,
            stage=schema.stage_of(c),
            machine=schema.machine_of(c),
            dtype=str(s.dtype),
            n_unique=int(s.nunique()),
        )
        if role != "time":
            valid = s[(s != 0)] if role == schema.OUT_ACTUAL else s
            rec.update(
                min=round(float(s.min()), 3),
                max=round(float(s.max()), 3),
                mean=round(float(valid.mean()), 3) if len(valid) else np.nan,
                std=round(float(valid.std()), 4) if len(valid) else np.nan,
                zero_pct=round(100 * float((s == 0).mean()), 1),
                # ilk satirin diff'i NaN; dropna olmadan NaN != 0 degisim sayilir
                n_changes=int((s.diff().dropna() != 0).sum()),
            )
        rec["note"] = ""
        if c in DROP_DUPLICATE_COLS:
            rec["note"] = "DUSURULDU (R3) - Machine4.Pressure ile birebir ozdes"
        rows.append(rec)

    t = pd.DataFrame(rows)
    facts = role_facts(df, t)
    role_desc = {k: v.format(**facts) for k, v in ROLE_DESC.items()}

    lines: list[str] = []
    w = lines.append
    w("# Data Dictionary\n")
    w("Otomatik uretildi: `python src/data_processing/data_dictionary.py`  ")
    w(f"Kaynak: `data/raw/continuous_factory_process.csv` "
      f"({df.shape[0]:,} x {df.shape[1]})\n")
    w("Elle duzenlenmez. Veri degisirse script yeniden calistirilir.\n")

    w("## Rol tanimlari\n")
    w("| Rol | Adet | Aciklama |")
    w("|---|---|---|")
    for role, desc in role_desc.items():
        w(f"| `{role}` | {int((t.role == role).sum())} | {desc} |")
    w("")

    w("## Prosesteki asamalar\n")
    w("| Stage | Kolon | Aciklama |")
    w("|---|---|---|")
    for st, desc in STAGE_DESC.items():
        n = int((t.stage == st).sum())
        if n:
            w(f"| `{st}` | {n} | {desc} |")
    w("")

    w("## Kolonlar\n")
    for role in [schema.CONTROLLED, schema.MEASURED, schema.AMBIENT,
                 schema.RAW_MAT, schema.OUT_ACTUAL, schema.OUT_SETPNT]:
        sub = t[t.role == role]
        if sub.empty:
            continue
        w(f"### `{role}` ({len(sub)} kolon)\n")
        w(f"*{role_desc[role]}*\n")
        cols = ["column", "stage", "machine", "min", "max", "mean", "std",
                "n_unique", "n_changes", "zero_pct", "note"]
        w("| " + " | ".join(cols) + " |")
        w("|" + "|".join("---" for _ in cols) + "|")
        for _, r in sub.iterrows():
            w("| " + " | ".join(
                "" if pd.isna(r[c]) else str(r[c]) for c in cols) + " |")
        w("")

    w("## Turetilmis kolonlar (`data/processed/clean_v1.csv`)\n")
    w("| Kolon | Aciklama |")
    w("|---|---|")
    w("| `seq` | Satir sirasi. Duplicate timestamp jitter'i nedeniyle asil "
      "zaman eksenidir. |")
    w("| `flag_dup_timestamp` | Timestamp'i baska bir satirla cakisiyor (R4). |")
    w("| `flag_downtime` | Stage1 setpoint'lerinin tamami 0 - durus blogu (R5). |")
    w("| `<Stage>.M<i>.dev` | `Actual - Setpoint`. Isaretli sapma. |")
    w("| `<Stage>.M<i>.abs_dev` | Mutlak sapma. |")
    w("| `<Stage>.M<i>.rel_dev_pct` | Setpoint'e gore yuzde sapma. |")
    w("")
    w("> Setpoint'in 0 oldugu satirlarda (durus) hedef tanimsizdir; deviation "
      "NaN birakilir, sifira bolme yapilmaz.\n")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    t.to_csv(ROOT / "reports" / "data_dictionary.csv", index=False)
    print(f"yazildi: {OUT}")
    print("yazildi: reports/data_dictionary.csv")
    print(f"\n{len(t)} kolon belgelendi:")
    print(t.role.value_counts().to_string())


if __name__ == "__main__":
    main()
