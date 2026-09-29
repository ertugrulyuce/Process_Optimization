"""
VARSAYIM A1'in ampirik testi + ornekleme frekansi analizi.

Hipotez: kolon adindaki '.C.' = Controlled, '.U.' = Uncontrolled.

Kaggle dokumantasyonu bu konuda sessiz (arastirildi, bkz. reports/a1_verification.md).
Dokumantasyon yerine davranissal bir test denendi.

DENENEN TEST ve NEDEN ISE YARAMADI
----------------------------------
Ilk fikir: kontrol edilen degisken setpoint'te bekler, hold_ratio = P(diff==0)
yuksek olur. Bu test SONUCSUZ kaldi, iki nedenle:

  1. `.C.Actual` bir setpoint degil, kontrol edilen degiskenin GERCEKLESEN
     olcumudur. Setpoint sabit olsa bile actual dalgalanir. Yuksek hold_ratio
     beklemek hataliydi.
  2. hold_ratio aslinda SENSOR GUNCELLEME FREKANSINI olcuyor. AmbientTemperature
     ~350 saniyede bir guncellendigi icin hold_ratio=0.997 cikiyor; kontrol
     edildigi icin degil.

Test A1'i ne dogruluyor ne curutuyor. Sonuc boyle raporlanir, zorlanmaz.

BUNUN YERINE CIKAN GERCEK BULGU
-------------------------------
Kolonlar cok farkli efektif ornekleme frekanslarina sahip. 1 Hz kaydedilmis
olmalari hepsinin 1 Hz olculdugu anlamina gelmiyor. Bu, model girdisi
secerken dogrudan onemlidir.

Calistirma:  python src/data_processing/verify_a1.py
"""
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import schema  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "continuous_factory_process.csv"
OUT = ROOT / "reports" / "a1_verification.md"

# Bu esigin altinda efektif gozlemi olan kolon, 4 saatlik pencerede
# istatistiksel olarak neredeyse sabittir.
LOW_INFO_THRESHOLD = 100


def profile(s: pd.Series) -> dict[str, float | int]:
    d = s.diff().dropna()
    n_changes = int((d != 0).sum())
    return dict(
        hold_ratio=round(float((d == 0).mean()), 4),
        n_changes=n_changes,
        update_period_s=round(len(s) / n_changes, 1) if n_changes else np.inf,
        n_levels=int(s.nunique()),
        std=round(float(s.std()), 4),
    )


def main() -> None:
    raw = pd.read_csv(RAW)
    # Pencere uzunlugu ve kayit frekansi rapor metninde kullanilir
    ts = pd.to_datetime(raw["time_stamp"])
    span_h = (ts.max() - ts.min()).total_seconds() / 3600
    rec_hz = 1 / ts.diff().dt.total_seconds().mode().iloc[0]
    df = raw.drop(columns=["time_stamp"])
    rows = []
    for c in df.columns:
        role = schema.classify(c)
        if role in ("time", schema.OUT_SETPNT):
            continue
        # profile() yalnizca sayilari dondurur; buraya metin alanlari ekleniyor
        p: dict[str, Any] = profile(df[c])
        p.update(column=c, role=role,
                 suffix=".C." if ".C.Actual" in c else
                        (".U." if ".U.Actual" in c else "-"))
        rows.append(p)

    t = pd.DataFrame(rows)[["column", "suffix", "role", "hold_ratio",
                            "n_changes", "update_period_s", "n_levels", "std"]]
    c_grp = t[t.suffix == ".C."]
    u_grp = t[(t.suffix == ".U.") & (t.role != schema.OUT_ACTUAL)]

    lines: list[str] = []
    w = lines.append
    w("# VARSAYIM A1 - Dogrulama Denemesi\n")
    w("**Hipotez:** `.C.` = Controlled (ayarlanabilir), `.U.` = Uncontrolled (olculur).\n")

    w("## 1. Dokumantasyon aramasi: SONUCSUZ\n")
    w("Kaggle dataset sayfasi, `awesome-industrial-datasets` kaydi ve dataseti")
    w("kullanan makaleler tarandi. Hicbiri `.C.` / `.U.` ekinin anlamini")
    w("aciklamiyor. Veri seti Liveline Technologies tarafindan 2019'da Detroit")
    w("yakinlarindaki gercek bir uretim hattindan alinmis; kolon adlandirmasi")
    w("muhtemelen firmanin ic konvansiyonu ve yayinlanmamis.\n")

    w("## 2. Davranissal test: SONUCSUZ\n")
    w("`hold_ratio` = P(ardisik fark == 0) metrigi denendi. Beklenti: kontrol")
    w("edilen degisken setpoint'te bekler, hold_ratio yuksek olur.\n")
    w("| grup | n | hold_ratio ort. | min | max |")
    w("|---|---|---|---|---|")
    for name, g in ((".C.", c_grp), (".U. (output haric)", u_grp)):
        w(f"| {name} | {len(g)} | {g.hold_ratio.mean():.3f} | "
          f"{g.hold_ratio.min():.3f} | {g.hold_ratio.max():.3f} |")
    w("")
    w("**Gruplar ayrismadi.** Test iki nedenle gecersiz:\n")
    w("1. `.C.Actual` bir setpoint degil, kontrol edilen degiskenin *gerceklesen*")
    w("   olcumudur. Setpoint sabitken bile actual dalgalanir; yuksek hold_ratio")
    w("   beklemek bastan hataliydi.")
    amb = t[t.column == "AmbientConditions.AmbientTemperature.U.Actual"].iloc[0]
    w("2. `hold_ratio` kontrol edilebilirligi degil, **sensor guncelleme frekansini**")
    w(f"   olcuyor. `AmbientTemperature.U.Actual` hold_ratio={amb.hold_ratio:.3f} -- kontrol")
    w(f"   edildigi icin degil, ~{amb.update_period_s:.0f} saniyede bir guncellendigi icin.\n")
    w("> **Sonuc: A1 ne dogrulandi ne curutuldu.** Dayanagi domain bilgisi olarak")
    w("> kalir: bir ekstruderde bolge sicakliklari ve vida devri ayarlanir")
    w("> (`Zone1Temperature.C`, `MotorRPM.C`); motor amperaji ve malzeme basinci")
    w("> bunlarin sonucudur (`MotorAmperage.U`, `MaterialPressure.U`). Sprint 7'de")
    w("> karar degiskeni seti daraltilip genisletilerek **duyarlilik analizi**")
    w("> yapilacak; sonuc bu varsayima bagliysa acikca belirtilecek.\n")

    w("## 3. Testten cikan gercek bulgu: ornekleme frekansi\n")
    w(f"Butun kolonlar {rec_hz:g} Hz *kaydedilmis* ama {rec_hz:g} Hz *olculmemis*. Efektif")
    w("guncelleme periyotlari cok farkli:\n")
    low = t[t.n_changes < LOW_INFO_THRESHOLD].sort_values("n_changes")
    w(f"**{len(low)} kolonun {span_h:.0f} saatlik pencerede "
      f"{LOW_INFO_THRESHOLD}'den az degisimi var:**\n")
    w("| column | role | degisim sayisi | guncelleme periyodu (sn) | ayrik seviye |")
    w("|---|---|---|---|---|")
    for _, r in low.iterrows():
        w(f"| {r.column} | {r.role} | {r.n_changes} | {r.update_period_s} | {r.n_levels} |")
    w("")
    hum = t[t.column == "AmbientConditions.AmbientHumidity.U.Actual"].iloc[0]
    amb_n = t[t.role == schema.AMBIENT].n_changes
    lv = t[t.role == schema.RAW_MAT].n_levels
    n_rows_tr = f"{len(df):,}".replace(",", ".")  # Turkce binlik ayraci
    w("> **BULGU F1 - Ambient kosullari pratikte sabittir.** `AmbientTemperature`")
    w(f"> ~{amb.update_period_s:.0f} sn'de, `AmbientHumidity` ~{hum.update_period_s:.0f} "
      f"sn'de bir guncelleniyor. {span_h:.0f} saatlik")
    w(f"> pencerede bu, ~{amb_n.min()}-{amb_n.max()} bagimsiz gozlem demek. Bu iki "
      "degiskeni output")
    w("> deviation'inin aciklayicisi olarak kullanmak istatistiksel olarak zayiftir;")
    w(f"> bulunacak herhangi bir iliski {amb_n.max()} noktaya dayanir, "
      f"{n_rows_tr}'e degil.\n")
    w(f"> **BULGU F2 - Hammadde ozellikleri lot bazli, surekli degil.** "
      f"{lv.min()}-{lv.max()} ayrik")
    w("> seviye ve cok seyrek degisim. Bunlar surekli degisken gibi degil,")
    w("> kategorik lot etiketi gibi ele alinmalidir.\n")

    w("## 4. Tam tablo\n")
    w("| column | suffix | role | hold_ratio | degisim | periyot (sn) | seviye | std |")
    w("|---|---|---|---|---|---|---|---|")
    for _, r in t.sort_values("n_changes").iterrows():
        w(f"| {r.column} | {r.suffix} | {r.role} | {r.hold_ratio} | {r.n_changes} | "
          f"{r.update_period_s} | {r.n_levels} | {r['std']} |")
    w("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    t.to_csv(ROOT / "reports" / "a1_verification.csv", index=False)

    print(f"yazildi: {OUT}\n")
    print("A1 davranissal test: SONUCSUZ (metrik kontrol degil, ornekleme frekansi olcuyor)")
    print(f"\nDusuk bilgi iceren kolonlar (<{LOW_INFO_THRESHOLD} degisim): {len(low)}")
    print(low[["column", "n_changes", "update_period_s", "n_levels"]].to_string(index=False))


if __name__ == "__main__":
    main()
