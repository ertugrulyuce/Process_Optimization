"""
pytest yol ayari.

src/ bir paket degil (modullerin birbirini `import schema` seklinde cagirmasi
icin duz dizin olarak tasarlandi). Testlerin ayni import'lari kullanabilmesi
icin alt dizinleri sys.path'e ekliyoruz -- boylece test kodu, script'lerin
calisma zamaninda gordugu yolun aynisini goruyor.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for sub in ("data_processing", "analysis", "modeling", "optimization"):
    sys.path.insert(0, str(ROOT / "src" / sub))

# run_all.py repo kokunde duruyor; testler onu da import ediyor.
sys.path.insert(0, str(ROOT))
