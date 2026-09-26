"""
requirements.lock ile requirements.txt'in uyumu.

Lock, commit edilmis raporlari ureten surumleri sabitler. requirements.txt
guncellenip lock unutulursa iki dosya sessizce ayrisir: yeni kurulum bir
surumu, rapor yeniden uretimi baska bir surumu kullanir. Bu testler o
ayrismayi CI'da yakalar. Lock'un gercekten kurulabildigi ayri bir CI adiminda
(pip --dry-run) dogrulaniyor.
"""
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def _requirements(path):
    reqs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            reqs.append(Requirement(line))
    return reqs


def _pins(path):
    """{kanonik ad: surum}; `==` disinda bir belirtec varsa hata."""
    pins = {}
    for req in _requirements(path):
        specs = list(req.specifier)
        assert len(specs) == 1 and specs[0].operator == "==", (
            f"lock'ta tam surum olmali: {req}")
        pins[canonicalize_name(req.name)] = specs[0].version
    return pins


LOCK = _pins(ROOT / "requirements.lock")
DIRECT = _requirements(ROOT / "requirements.txt")


@pytest.mark.parametrize("req", DIRECT, ids=lambda r: r.name)
def test_direct_requirement_is_pinned_within_range(req):
    name = canonicalize_name(req.name)
    assert name in LOCK, f"{req.name} requirements.txt'te var, lock'ta yok"
    assert req.specifier.contains(LOCK[name]), (
        f"lock {req.name}=={LOCK[name]} ama requirements.txt {req.specifier} istiyor")


def test_lock_has_no_duplicates():
    names = [canonicalize_name(r.name) for r in _requirements(ROOT / "requirements.lock")]
    assert len(names) == len(set(names))
