"""
schema.py testleri.

Bu modul projenin en kritik on kosulunu belirliyor: hangi degiskene operator
mudahale edebilir, hangisine edemez. Yanlis siniflanan tek bir kolon,
optimizasyonun kontrol edilemeyen bir degiskeni "ayarlanabilir" sanmasina ve
tum onerinin gecersizlesmesine yol acar. Bu yuzden siniflandirma kurallari
testle sabitlendi.
"""
import csv

import pytest
import schema
from conftest import ROOT


# Gercek veri setinden alinmis kolon adlari; uydurma ornek kullanilmadi.
@pytest.mark.parametrize("column,expected", [
    ("time_stamp",                              "time"),
    ("AmbientConditions.AmbientHumidity.U.Actual", schema.AMBIENT),
    ("Machine3.RawMaterial.Property1",          schema.RAW_MAT),
    ("Machine1.Zone2Temperature.C.Actual",      schema.CONTROLLED),
    ("Machine3.MaterialPressure.U.Actual",      schema.MEASURED),
    ("Stage1.Output.Measurement6.U.Actual",     schema.OUT_ACTUAL),
    ("Stage1.Output.Measurement1.U.Setpoint",   schema.OUT_SETPNT),
])
def test_classify_roles(column, expected):
    assert schema.classify(column) == expected


def test_output_setpoint_not_read_as_measured():
    """
    Kural sirasi regresyon testi.

    `Stage1.Output.Measurement1.U.Setpoint` hem `.Output.Measurement` hem de
    `.U.` kalibina uyuyor. classify() icinde Output kontrolu `.U.Actual`
    kontrolunden once gelmezse bu kolon 'measured' sayilir ve cikti
    hedefleri teshis degiskeni muamelesi gorur. Siralama bozulursa burasi
    kirilir.
    """
    assert schema.classify("Stage1.Output.Measurement1.U.Setpoint") == schema.OUT_SETPNT
    assert schema.classify("Stage2.Output.Measurement1.U.Actual") == schema.OUT_ACTUAL


def test_ambient_beats_raw_material_prefix():
    """AmbientConditions kontrolu RawMaterial kontrolunden once gelmeli."""
    assert schema.classify("AmbientConditions.AmbientTemperature.U.Actual") == schema.AMBIENT


@pytest.mark.parametrize("column,expected", [
    ("Machine1.Zone1Temperature.C.Actual",      "stage1"),
    ("Machine3.MaterialPressure.U.Actual",      "stage1"),
    ("Machine4.Temperature1.C.Actual",          "stage2"),
    ("Machine5.Temperature3.C.Actual",          "stage2"),
    ("FirstStage.CombinerOperation.Temperature1.U.Actual", "combiner"),
    ("Stage1.Output.Measurement0.U.Actual",     "stage1_out"),
    ("Stage2.Output.Measurement0.U.Actual",     "stage2_out"),
    ("AmbientConditions.AmbientHumidity.U.Actual", "ambient"),
    ("time_stamp",                              "-"),
])
def test_stage_of(column, expected):
    assert schema.stage_of(column) == expected


def test_machine_of():
    assert schema.machine_of("Machine4.Temperature1.C.Actual") == "M4"
    assert schema.machine_of("Stage1.Output.Measurement0.U.Actual") == "-"
    assert schema.machine_of("time_stamp") == "-"


def test_decision_and_noise_are_disjoint():
    """
    Bir kolon hem karar degiskeni hem gurultu olamaz. Ortusme olursa
    optimizasyon kontrol edemedigi bir degiskeni ayarlamaya calisir.
    """
    cols = [r["column"] for r in _committed_schema()]
    decisions = set(schema.decision_variables(cols))
    noise = set(schema.noise_variables(cols))

    assert decisions, "karar degiskeni bulunamadi"
    assert noise, "gurultu degiskeni bulunamadi"
    assert not (decisions & noise)


def test_build_covers_every_column_once():
    cols = ["time_stamp", "Machine1.Zone1Temperature.C.Actual",
            "Stage1.Output.Measurement0.U.Actual"]
    rows = schema.build(cols)

    assert [r["column"] for r in rows] == cols
    assert all(set(r) == {"column", "role", "stage", "machine"} for r in rows)


def test_no_unknown_columns_in_real_dataset():
    """
    Gercek veri setindeki her kolon bir role oturmali. 'unknown' cikan kolon,
    siniflandirma kurallarinin veriyi tam kapsamadigi anlamina gelir.
    """
    unknown = [r["column"] for r in _committed_schema()
               if schema.classify(r["column"]) == "unknown"]
    assert unknown == []


def test_matches_committed_schema_table():
    """
    reports/variable_schema.csv repoya islenmis bir cikti. Kod degisip bu
    tablo yeniden uretilmezse rapor ile kod birbirinden ayrilir. Bu test o
    ayrilmayi yakalar.
    """
    for row in _committed_schema():
        col = row["column"]
        assert schema.classify(col) == row["role"], col
        assert schema.stage_of(col) == row["stage"], col
        assert schema.machine_of(col) == row["machine"], col


def _committed_schema():
    path = ROOT / "reports" / "variable_schema.csv"
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
