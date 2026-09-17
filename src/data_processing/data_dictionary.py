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

ROLE_DESC = {
    "time": "Zaman damgasi (1 Hz).",
    schema.AMBIENT: "Cevre kosulu. Kontrol edilemez. Efektif ornekleme ~350 sn "
                    "(K4) -> 4 saatte ~40 bagimsiz gozlem.",
    schema.RAW_MAT: "Gelen hammadde ozelligi. Kontrol edilemez. 2-5 ayrik seviye, "
                    "cok seyrek degisim (K4) -> lot etiketi gibi ele alinir.",
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


def main():
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
                n_changes=int((s.diff() != 0).sum()),
            )
        rec["note"] = ""
        if c in DROP_DUPLICATE_COLS:
            rec["note"] = "DUSURULDU (R3) - Machine4.Pressure ile birebir ozdes"
        rows.append(rec)

    t = pd.DataFrame(rows)

    lines = []
    w = lines.append
    w("# Data Dictionary\n")
    w("Otomatik uretildi: `python src/data_processing/data_dictionary.py`  ")
    w(f"Kaynak: `data/raw/continuous_factory_process.csv` "
      f"({df.shape[0]:,} x {df.shape[1]})\n")
    w("Elle duzenlenmez. Veri degisirse script yeniden calistirilir.\n")

    w("## Rol tanimlari\n")
    w("| Rol | Adet | Aciklama |")
    w("|---|---|---|")
    for role, desc in ROLE_DESC.items():
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
        w(f"*{ROLE_DESC[role]}*\n")
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
