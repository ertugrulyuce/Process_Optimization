"""
Pano arayuzunun hatasiz calistigini dogrular.

Streamlit kurulu degilse ATLANIR: pipeline ve CI streamlit gerektirmiyor
(bkz. dashboard/requirements.txt), yani bu test yereldeki gelistirici icin.
CI ciktisinda "skipped" olarak gorunur.

Arayuzden bagimsiz olan okuma/ozetleme katmaninin testleri
tests/test_dashboard.py icinde ve onlar her ortamda kosar.
"""
import pytest

pytest.importorskip("streamlit", reason="pano bagimliligi: dashboard/requirements.txt")

from conftest import ROOT  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(ROOT / "dashboard" / "app.py")


def test_app_runs_without_exceptions():
    at = AppTest.from_file(APP, default_timeout=120).run()

    assert not at.exception
    assert at.title[0].value.startswith("Surekli Uretim")
    assert len(at.metric) == 4   # ust satirdaki dort sayi
    assert len(at.tabs) == 4


def test_app_reports_missing_files_instead_of_crashing(tmp_path, monkeypatch):
    """
    reports/ yoksa pano cokmemeli; ne yapilmasi gerektigini yazmali.
    Bos bir pano, "sonuc yok" gibi degil "proje calismiyor" gibi okunur.
    """
    from dashboard import data
    monkeypatch.setattr(data, "REPORTS", tmp_path)

    at = AppTest.from_file(APP, default_timeout=120).run()

    assert not at.exception
    assert any("make run" in e.value for e in at.error)
