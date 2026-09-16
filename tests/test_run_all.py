"""
run_all.py testleri.

Pipeline surucusunun iki tehlikeli yani var:
  1. Temizlik uretilen dosyalari siliyor. Yanlis tetiklenirse butun raporlar
     gider -- scriptin varlik sebebi zaten elle silme sirasinda `docs/`
     altindaki bir dosyanin kaybedilmesiydi.
  2. Adimlar birbirinin ciktisini okuyor. Sira bozulursa eski girdiyle yeni
     rapor uretilir ve bu hicbir hata vermez.

Ikisi de burada sabitlendi. Testler alt surec calistirmaz.
"""
from pathlib import Path
import types

import pytest

import run_all


@pytest.fixture
def calls(monkeypatch):
    """Alt surec calistirmadan main()'i surer; cagrilan adimlari kaydeder."""
    recorded = []

    def fake_run(cmd, **kwargs):
        recorded.append(Path(cmd[1]).stem)
        return types.SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(run_all.subprocess, "run", fake_run)
    return recorded


@pytest.fixture
def cleaned(monkeypatch):
    """clean_outputs() cagrildi mi -- gercek dosya silmeden."""
    recorded = []
    monkeypatch.setattr(run_all, "clean_outputs", lambda: recorded.append(True))
    return recorded


# --- adim secimi --------------------------------------------------------------

def test_no_selection_runs_the_whole_pipeline():
    assert run_all.select_steps() == run_all.STEPS
    assert run_all.select_steps("") == run_all.STEPS


def test_single_step_selection():
    assert [Path(s).stem for s, _ in run_all.select_steps("clean")] == ["clean"]


def test_selection_keeps_pipeline_order_not_the_order_typed():
    """Adimlar birbirinin ciktisini okuyor; ters sirada calistirmak sizinti degil, eski veri uretir."""
    picked = run_all.select_steps("capability,clean")

    assert [Path(s).stem for s, _ in picked] == ["clean", "capability"]


def test_repeated_step_runs_once():
    assert len(run_all.select_steps("clean,clean")) == 1


def test_unknown_step_is_rejected_with_the_valid_list():
    with pytest.raises(ValueError) as exc:
        run_all.select_steps("temizlik")

    assert "temizlik" in str(exc.value)
    assert "clean" in str(exc.value)   # gecerli adimlar mesajda


def test_step_names_match_the_scripts():
    assert run_all.step_names() == [Path(s).stem for s, _ in run_all.STEPS]
    assert len(set(run_all.step_names())) == len(run_all.STEPS)  # ad cakismasi yok


# --- temizlik -----------------------------------------------------------------

def test_clean_patterns_never_reach_handwritten_docs():
    """
    Scriptin varlik sebebi: `docs/` elle yazildi, silinmemeli. Temizlik
    desenleri yalnizca uretilen dizinleri kapsayabilir.
    """
    assert run_all.GENERATED
    for pattern in run_all.GENERATED:
        assert pattern.startswith(("reports/", "data/processed/")), pattern


def test_clean_outputs_removes_generated_files_only(tmp_path, monkeypatch):
    for d in ("reports/figures", "docs", "data/processed", "data/raw"):
        (tmp_path / d).mkdir(parents=True)
    generated = [tmp_path / "reports" / "01_rapor.md",
                 tmp_path / "reports" / "tablo.csv",
                 tmp_path / "reports" / "figures" / "01_grafik.png",
                 tmp_path / "data" / "processed" / "clean_v1.csv"]
    kept = [tmp_path / "docs" / "assumptions.md",
            tmp_path / "data" / "raw" / "ham.csv"]
    for p in generated + kept:
        p.write_text("x", encoding="utf-8")
    monkeypatch.setattr(run_all, "ROOT", tmp_path)

    run_all.clean_outputs()

    assert not any(p.exists() for p in generated)
    assert all(p.exists() for p in kept)


# --- komut satiri -------------------------------------------------------------

def test_list_prints_steps_without_running_anything(calls, cleaned, capsys):
    rc = run_all.main(["--list"])

    assert rc == 0
    assert calls == [] and cleaned == []
    assert "capability" in capsys.readouterr().out


def test_clean_flag_cleans_and_exits(calls, cleaned):
    rc = run_all.main(["--clean"])

    assert rc == 0
    assert cleaned == [True]
    assert calls == []      # hicbir adim calistirilmadi


def test_full_run_cleans_first(calls, cleaned):
    rc = run_all.main([])

    assert rc == 0
    assert cleaned == [True]
    assert calls == run_all.step_names()


def test_keep_skips_cleaning(calls, cleaned):
    run_all.main(["--keep"])

    assert cleaned == []
    assert calls == run_all.step_names()


def test_only_runs_one_step_and_never_cleans(calls, cleaned):
    """
    --only temizlik yapmamali: temizlik butun uretilen ciktilari siler,
    secilmeyen adimlarinkini de. Tek adimi yenilemek digerlerini silmek olmaz.
    """
    rc = run_all.main(["--only", "capability"])

    assert rc == 0
    assert cleaned == []
    assert calls == ["capability"]


def test_unknown_step_exits_without_touching_anything(calls, cleaned, capsys):
    rc = run_all.main(["--only", "yok_boyle_bir_adim"])

    assert rc == 2
    assert calls == [] and cleaned == []
    assert "bilinmeyen adim" in capsys.readouterr().out


def test_failing_step_is_reported(monkeypatch, cleaned, capsys):
    def failing_run(cmd, **kwargs):
        return types.SimpleNamespace(returncode=1, stderr="Traceback\nValueError: x")

    monkeypatch.setattr(run_all.subprocess, "run", failing_run)
    rc = run_all.main(["--only", "clean"])

    assert rc == 1
    out = capsys.readouterr().out
    assert "BASARISIZ" in out
    assert "ValueError: x" in out
