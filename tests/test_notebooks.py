"""
Defterlerin repoya cikti tasimadigini dogrular.

Neden onemli: hucre ciktilari (grafiklerin base64'u, tablo HTML'leri) diff'i
okunamaz hale getirir ve repoyu sisirir. Daha kotusu, commit edilen bir
cikti kodun o anki haliyle uretildigini garanti etmez -- eski bir
calistirmanin goruntusu sessizce repoda kalir ve okuyan onu guncel sanir.

Temizlik `nbstripout` ile otomatik (bkz. .pre-commit-config.yaml). Bu test,
kancanin kurulmadigi ya da atlandigi durumu yakalar: CI kancaya bagli degil.
"""
import json

import pytest
from conftest import ROOT

NOTEBOOKS = sorted((ROOT / "notebooks").glob("*.ipynb"))


def test_there_is_at_least_one_notebook():
    """Defter yoksa asagidaki test sessizce bos gecer, koruma da yok demektir."""
    assert NOTEBOOKS


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_carries_no_output(path):
    nb = json.loads(path.read_text(encoding="utf-8"))

    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        assert not cell.get("outputs"), f"{path.name} hucre {i}: cikti commit edilmis"
        assert cell.get("execution_count") is None, \
            f"{path.name} hucre {i}: execution_count dolu"
