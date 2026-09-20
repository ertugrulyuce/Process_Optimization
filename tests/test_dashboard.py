"""
dashboard/data.py testleri.

Pano, projenin sonuclarini tek ekranda ozetliyor. Yanlis bir ozet dogru
raporlarin uzerini orter: cogu okuyucu markdown'i acmadan panoya bakar.
Bu yuzden okuma ve ozetleme katmani -- streamlit'ten bagimsiz tutulmasinin
sebebi de bu -- testleniyor.

Testler commit edilmis reports/ CSV'lerini okur; ham veri gerekmez.
"""
import pandas as pd
import pytest

from dashboard import data


def _capability_frame():
    return pd.DataFrame({
        "output": ["A", "B", "C", "D"],
        "error_type": ["bias", "variability", "variability", "bias"],
        "sigma_st": [0.1, 0.2, 0.0, 0.3],
        "Cpk orta (+/-%2)": [1.5, -0.4, float("nan"), 0.2],
    })


def _modeling_frame():
    return pd.DataFrame({
        "output": ["A", "A", "B", "B"],
        "feature_set": ["controlled", "controlled", "controlled", "ctrl+lag"],
        "model": ["rf", "hgb", "rf", "hgb"],
        "skill_vs_pers": [0.1, 0.4, -0.2, 0.9],
    })


def _validation_frame():
    return pd.DataFrame({
        "output": ["A"] * 4 + ["B"] * 4,
        "fold": [1, 2, 3, 4] * 2,
        # A: fold 1 disinda da pozitif. B: yalnizca fold 1 guclu.
        "skill_vs_pers": [0.9, 0.1, 0.2, 0.3, 0.8, -0.1, 0.2, -0.3],
    })


# --- kaynaklar ----------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(data.SOURCES))
def test_every_source_loads(name):
    assert not data.load(name).empty


def test_load_all_returns_every_source():
    assert set(data.load_all()) == set(data.SOURCES)


def test_unknown_source_lists_the_valid_ones():
    with pytest.raises(KeyError, match="bilinmeyen kaynak"):
        data.load("olmayan")


def test_missing_report_says_what_to_run(tmp_path, monkeypatch):
    """
    Eksik dosya panonun hatasi degil: pipeline calistirilmamis demektir.
    Mesaj ne yapilacagini soylemeli, yoksa kullanici panoyu bozuk sanir.
    """
    monkeypatch.setattr(data, "REPORTS", tmp_path)

    with pytest.raises(data.MissingReportError, match="make run"):
        data.load("kpi")


# --- kapsam -------------------------------------------------------------------

def test_scope_summary_adds_up():
    kpi = data.load("kpi")
    scope = data.scope_summary(kpi)

    assert scope["kapsam_ici"] + scope["kapsam_disi"] == scope["toplam"] == len(kpi)
    assert scope["bias"] + scope["variability"] + scope["belirsiz"] == scope["kapsam_ici"]


def test_out_of_scope_rows_carry_their_reason():
    disarida = data.out_of_scope(data.load("kpi"))

    assert not disarida.empty
    assert disarida.scope_reason.str.contains("kapsam disi").all()


# --- capability ---------------------------------------------------------------

def test_cpk_column_is_found_by_scenario_name():
    assert data.cpk_column(data.load("capability"), "orta").startswith("Cpk orta")


def test_unknown_scenario_lists_available_columns():
    with pytest.raises(KeyError, match="Cpk"):
        data.cpk_column(_capability_frame(), "yok")


def test_scenarios_come_from_the_table():
    assert data.scenarios(data.load("capability")) == ["dar", "orta", "genis"]


def test_worst_capability_is_sorted_and_drops_undefined():
    """Cp/Cpk'si hesaplanamayan output (sigma_st = 0) siralamaya girmez."""
    worst = data.worst_capability(_capability_frame(), "orta", n=2)

    assert worst.output.tolist() == ["B", "D"]
    assert "C" not in worst.output.tolist()


# --- model --------------------------------------------------------------------

def test_best_models_picks_one_row_per_output():
    best = data.best_models(_modeling_frame())

    assert best.output.tolist() == ["A", "B"]
    assert best.model.tolist() == ["hgb", "rf"]          # A icin daha iyi skor
    assert best.skill_vs_pers.tolist() == [0.4, -0.2]    # ctrl+lag satiri sayilmadi


def test_unknown_feature_set_lists_available_ones():
    with pytest.raises(ValueError, match="controlled"):
        data.best_models(_modeling_frame(), feature_set="yok")


# --- validation ---------------------------------------------------------------

def test_fold_consistency_skips_the_first_fold_by_default():
    """Fold 1'in train seti cok kucuk; ayni kefeye konursa model haksiz gorunur."""
    out = data.fold_consistency(_validation_frame()).set_index("output")

    assert out.loc["A", "fold"] == 3 and out.loc["A", "pozitif"] == 3
    assert out.loc["B", "fold"] == 3 and out.loc["B", "pozitif"] == 1


def test_first_fold_can_be_included():
    out = data.fold_consistency(_validation_frame(), skip_first=False).set_index("output")

    assert out.loc["A", "fold"] == 4
    assert out.loc["B", "pozitif"] == 2   # fold 1 sayilinca B iki pozitif


def test_fold_consistency_flags_outputs_positive_in_every_fold():
    out = data.fold_consistency(_validation_frame()).set_index("output")

    assert bool(out.loc["A", "her_foldda_pozitif"]) is True
    assert bool(out.loc["B", "her_foldda_pozitif"]) is False


# --- ust satir ----------------------------------------------------------------

def test_headline_matches_the_committed_tables():
    kpi = data.load("kpi")
    modeling = data.load("modeling")
    validation = data.load("validation")

    head = data.headline(kpi, modeling, validation)
    ins = kpi[kpi.in_scope == "evet"]

    assert head["Kapsam ici output"] == f"{len(ins)} / {len(kpi)}"
    assert head["Variability-baskin"] == str((ins.error_type == "variability").sum())
    assert " / " in head["Persistence'i gecen"]
    assert " / " in head["Her fold'da pozitif"]
