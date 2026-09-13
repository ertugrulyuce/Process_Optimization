"""
Degisken semasi: her kolonu prosesteki rolune gore siniflandirir.

Bu modul, optimizasyonun en kritik on kosulunu saglar:
hangi degiskenlere operator mudahale edebilir, hangilerine edemez.
Bu ayrim yapilmadan "optimum calisma kosulu" onerilemez.

VARSAYIM A1: Kolon adindaki '.C.' = Controlled (setpoint verilebilir),
             '.U.' = Uncontrolled (olculur, dogrudan ayarlanamaz).
             Kaggle dokumantasyonundan dogrulanmali. Bkz. docs/assumptions.md
"""
import re

TIME = "time_stamp"

# --- rol tanimlari ---
AMBIENT     = "ambient"       # cevre kosulu -> kontrol edilemez (gurultu)
RAW_MAT     = "raw_material"  # gelen hammadde ozelligi -> kontrol edilemez (gurultu)
CONTROLLED  = "controlled"    # karar degiskeni -> optimizasyonda serbest
MEASURED    = "measured"      # proses tepkisi -> ne girdi ne cikti; teshis degiskeni
OUT_ACTUAL  = "output_actual"
OUT_SETPNT  = "output_setpoint"

# --- veri seti yapisi ---
# Her asama 15 boyutsal olcum uretir: `{stage}.Output.Measurement{i}.U.Actual`
# ve ayni adla `.Setpoint`. Audit, temizlik ve raporlar bu sayilara dayaniyor.
STAGES          = ("Stage1", "Stage2")
N_MEASUREMENTS  = 15
N_OUTPUTS       = len(STAGES) * N_MEASUREMENTS


def classify(col: str) -> str:
    if col == TIME:
        return "time"
    if col.startswith("AmbientConditions"):
        return AMBIENT
    if ".RawMaterial.Property" in col:
        return RAW_MAT
    if ".Output.Measurement" in col:
        return OUT_SETPNT if col.endswith(".Setpoint") else OUT_ACTUAL
    if ".C.Actual" in col:
        return CONTROLLED
    if ".U.Actual" in col:
        return MEASURED
    return "unknown"


def stage_of(col: str) -> str:
    """Degiskenin hangi proses asamasina ait oldugu."""
    if col == TIME:
        return "-"
    if col.startswith("AmbientConditions"):
        return "ambient"
    m = re.match(r"Machine([1-5])\.", col)
    if m:
        return "stage1" if m.group(1) in "123" else "stage2"
    if col.startswith("FirstStage.CombinerOperation"):
        return "combiner"
    if col.startswith("Stage1.Output"):
        return "stage1_out"
    if col.startswith("Stage2.Output"):
        return "stage2_out"
    return "unknown"


def machine_of(col: str) -> str:
    m = re.match(r"Machine([1-5])\.", col)
    return f"M{m.group(1)}" if m else "-"


def build(columns):
    """Kolon listesinden sema tablosu (list[dict]) uretir."""
    return [
        dict(column=c, role=classify(c), stage=stage_of(c), machine=machine_of(c))
        for c in columns
    ]


def decision_variables(columns):
    """Optimizasyonun uzerinde oynayabilecegi kolonlar."""
    return [c for c in columns if classify(c) == CONTROLLED]


def noise_variables(columns):
    """Kontrol edilemeyen ama output'u etkileyen kolonlar."""
    return [c for c in columns if classify(c) in (AMBIENT, RAW_MAT)]
