"""
Pano veri katmani -- streamlit'ten bagimsiz.

UI'dan ayri durmasinin sebebi test edilebilirlik: streamlit kurulu olmayan
bir ortamda (CI dahil) bu modul import edilip dogrulanabiliyor. app.py
yalnizca gorunum; butun okuma ve ozetleme burada.

Kaynak olarak YALNIZCA reports/ altindaki commit edilmis CSV'ler kullanilir.
Ham veri repoda yok (data/raw, data/processed gitignore'da); pano onlara
bagli olsaydi depoyu klonlayan hic kimsede calismazdi.

Pano hicbir sayiyi yeniden hesaplamaz. Otoriter kaynak reports/ altindaki
markdown raporlardir; burasi onlarin ozetini gosterir.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

# Panonun okudugu dosyalar; hepsi script ciktisi ve repoya islenmis.
SOURCES = {
    "kpi": "output_kpi_summary.csv",
    "capability": "capability_table.csv",
    "correlation": "correlation_table.csv",
    "modeling": "modeling_results.csv",
    "validation": "validation_folds.csv",
    "optimization": "optimization_points.csv",
}


class MissingReportError(FileNotFoundError):
    """
    Pano bir rapor ciktisini bulamadi.

    Bu panonun hatasi degil: reports/ temizlenmis ya da pipeline hic
    calistirilmamis demektir. Mesaj ne yapilmasi gerektigini soyler.
    """


def load(name):
    """Tek bir rapor CSV'si."""
    if name not in SOURCES:
        raise KeyError(f"bilinmeyen kaynak: {name}. Gecerli olanlar: "
                       f"{', '.join(sorted(SOURCES))}")
    path = REPORTS / SOURCES[name]
    if not path.exists():
        raise MissingReportError(
            f"{path.name} yok. Pano yalnizca uretilmis raporlari okur; once "
            "`make run` (ya da `python run_all.py`) calistirin.")
    return pd.read_csv(path)


def load_all():
    """Panonun ihtiyac duydugu butun tablolar."""
    return {name: load(name) for name in SOURCES}


def scope_summary(kpi):
    """Kapsam ve hata tipi dagilimi (Faz 1)."""
    ins = kpi[kpi.in_scope == "evet"]
    return {
        "toplam": len(kpi),
        "kapsam_ici": len(ins),
        "kapsam_disi": len(kpi) - len(ins),
        "bias": int((ins.error_type == "bias").sum()),
        "variability": int((ins.error_type == "variability").sum()),
        "belirsiz": int((ins.error_type == "belirsiz").sum()),
    }


def out_of_scope(kpi):
    """Kapsam disi output'lar ve gerekceleri."""
    return (kpi[kpi.in_scope != "evet"][["output", "valid_pct", "scope_reason"]]
            .reset_index(drop=True))


def cpk_column(capability, scenario="orta"):
    """
    Senaryo adindan Cpk kolonunu bulur (ornek: `Cpk orta (+/-%2)`).

    Kolon adi tolerans degerini icerdigi icin sabit yazilamaz: tolerans
    degisirse pano sessizce yanlis kolonu gostermek yerine hata vermeli.
    """
    matches = [c for c in capability.columns
               if c.startswith("Cpk") and scenario in c]
    if not matches:
        mevcut = [c for c in capability.columns if c.startswith("Cpk")]
        raise KeyError(f"'{scenario}' senaryosuna ait Cpk kolonu yok. "
                       f"Mevcut: {mevcut}")
    return matches[0]


def scenarios(capability):
    """Capability tablosundaki senaryo adlari (`dar`, `orta`, `genis`)."""
    return [c.split()[1] for c in capability.columns if c.startswith("Cpk ")]


def worst_capability(capability, scenario="orta", n=5):
    """En dusuk Cpk'li output'lar. Cp/Cpk'si hesaplanamayanlar listeye girmez."""
    col = cpk_column(capability, scenario)
    cols = ["output", "error_type", "sigma_st", col]
    return capability.dropna(subset=[col]).nsmallest(n, col)[cols]


def best_models(modeling, feature_set="controlled"):
    """
    Her output icin, verilen girdi setindeki en iyi model.

    Varsayilan `controlled`: optimizasyon sorusu (S1). Gecmis degerlerle
    (ctrl+lag) elde edilen basari izleme sorusudur (S2) ve S1'in yerine
    gecmez; bu yuzden set adi acikca isteniyor.
    """
    sub = modeling[modeling.feature_set == feature_set]
    if sub.empty:
        mevcut = sorted(modeling.feature_set.unique())
        raise ValueError(f"'{feature_set}' girdi setine ait satir yok. "
                         f"Mevcut: {mevcut}")
    return sub.loc[sub.groupby("output").skill_vs_pers.idxmax()].reset_index(drop=True)


def fold_consistency(validation, skip_first=True):
    """
    Walk-forward fold'larinda beceri tutarliligi.

    Fold 1 varsayilan olarak disarida: train seti digerlerinin cok altinda
    kaliyor (bkz. 08_validation_report.md), ayni kefeye konursa model haksiz
    yere kotu gorunur.
    """
    v = validation[validation.fold > 1] if skip_first else validation
    out = (v.groupby("output")
            .agg(fold=("fold", "count"),
                 pozitif=("skill_vs_pers", lambda s: int((s > 0).sum())),
                 medyan=("skill_vs_pers", "median"),
                 en_dusuk=("skill_vs_pers", "min"))
            .reset_index())
    out["her_foldda_pozitif"] = out.pozitif == out.fold
    return out


def headline(kpi, modeling, validation):
    """
    Panonun ustundeki dort sayi.

    Dordu de projenin durustce soyledigi seyi gosterir: kapsam dar, model
    zayif, tek bolmeye dayanan sonuclar fold'lar arasinda ayakta kalmiyor.
    """
    scope = scope_summary(kpi)
    best = best_models(modeling)
    folds = fold_consistency(validation)
    return {
        "Kapsam ici output": f"{scope['kapsam_ici']} / {scope['toplam']}",
        "Variability-baskin": str(scope["variability"]),
        "Persistence'i gecen": f"{int((best.skill_vs_pers > 0).sum())} / {len(best)}",
        "Her fold'da pozitif": f"{int(folds.her_foldda_pozitif.sum())} / {len(folds)}",
    }
