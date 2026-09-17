"""
Her modulun import edilebildigini dogrular.

src/ bir paket degil: moduller birbirini `import schema` seklinde, duz dizin
mantigiyla cagiriyor (gerekcesi tests/conftest.py icinde). Bunun bedeli, bir
dosya tasindiginda veya yeniden adlandirildiginda import zincirinin yalnizca
ilgili script calistirildiginda kirilmasi -- testler bunu yakalamaz. Bu script
tum modulleri import ederek kirilmayi CI'da yakalar.

Moduller isi `if __name__ == "__main__"` altinda yaptigi icin import etmek
veri dosyasi gerektirmez; CI'da ham veri yok.
"""
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBDIRS = ("data_processing", "analysis", "modeling", "optimization")

for sub in SUBDIRS:
    sys.path.insert(0, str(ROOT / "src" / sub))
sys.path.insert(0, str(ROOT))


def main() -> int:
    modules = sorted(p.stem for sub in SUBDIRS for p in (ROOT / "src" / sub).glob("*.py"))
    modules.append("run_all")

    failed = []
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 -- hangi hata olursa olsun raporlanmali
            failed.append((name, exc))
            print(f"HATA  {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"tamam {name}")

    if failed:
        print(f"\n{len(failed)} modul import edilemedi.")
        return 1

    print(f"\n{len(modules)} modul import edildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
