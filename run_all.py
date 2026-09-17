"""
Tum pipeline'i sirayla calistirir.

Neden var: pipeline'i elle `rm -f reports/*.md` ile temizlerken elle yazilan
`assumptions.md` de silindi (hicbir script onu uretmiyordu). Bu script yalnizca
URETILEN ciktilari temizler ve sirayi tek yerde tutar.

Kural: `reports/` altindaki her sey script ciktisidir, silinebilir.
       Elle yazilan dokumanlar `docs/` altindadir, asla silinmez.

Calistirma:
    python run_all.py                    # temizle + hepsini calistir
    python run_all.py --keep             # temizlemeden calistir
    python run_all.py --only clean       # tek adim (temizlik yapilmaz)
    python run_all.py --only clean,capability
    python run_all.py --list             # adimlari listele
    python run_all.py --clean            # yalnizca uretilen ciktilari sil
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Sira onemli: her adim oncekinin ciktisini kullanir.
STEPS = [
    ("src/data_processing/audit.py", "veri kalitesi teshisi"),
    ("src/data_processing/verify_a1.py", "A1 varsayimi + ornekleme frekansi"),
    ("src/data_processing/clean.py", "temizlik + deviation KPI'lari"),
    ("src/data_processing/data_dictionary.py", "degisken sozlugu"),
    ("src/analysis/capability.py", "control chart + Cp/Cpk"),
    ("src/analysis/correlation.py", "otokorelasyon + FDR duzeltmeli korelasyon"),
    ("src/analysis/stage_link.py", "transport delay aramasi"),
    ("src/modeling/train.py", "tahmin modelleri + CPP"),
    ("src/optimization/optimize.py", "dar kapsamli optimizasyon"),
    ("src/analysis/validation.py", "walk-forward validation + drift"),
    ("src/analysis/recommendations.py", "endustriyel oneri + DOE"),
    ("src/analysis/figures.py", "gorseller"),
]

# Yalnizca bunlar uretilen ciktidir; temizlikte silinir.
GENERATED = ["reports/*.md", "reports/*.csv", "reports/figures/*.png",
             "data/processed/*.csv"]


def step_names():
    return [Path(script).stem for script, _ in STEPS]


def select_steps(only=None):
    """
    `--only` ile secilen adimlar; bos birakilirsa pipeline'in tamami.

    Donen liste her zaman PIPELINE sirasindadir, kullanicinin yazdigi sirada
    degil: adimlar birbirinin ciktisini okuyor, ters sirada calistirmak eski
    girdiyle yeni rapor uretirdi. Bilinmeyen ad ValueError.
    """
    if not only:
        return list(STEPS)

    wanted = [n.strip() for n in only.split(",") if n.strip()]
    unknown = [n for n in wanted if n not in step_names()]
    if unknown:
        raise ValueError(f"bilinmeyen adim: {', '.join(unknown)}\n"
                         f"gecerli adimlar: {', '.join(step_names())}")
    return [(script, desc) for script, desc in STEPS
            if Path(script).stem in wanted]


def clean_outputs():
    n = 0
    for pattern in GENERATED:
        for p in ROOT.glob(pattern):
            p.unlink()
            n += 1
    print(f"temizlendi: {n} uretilen dosya")
    print("korundu   : docs/ (elle yazilan dokumanlar), data/raw, data/_quarantine\n")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="run_all.py",
        description="Pipeline'i sirayla calistirir; yalnizca uretilen ciktilari temizler.")
    p.add_argument("--keep", action="store_true",
                   help="uretilen ciktilari silmeden calistir")
    p.add_argument("--only", metavar="ADIM",
                   help="yalnizca bu adim(lar)i calistir, virgulle ayir (bkz. --list)")
    p.add_argument("--list", action="store_true", dest="list_steps",
                   help="adimlari listele ve cik")
    p.add_argument("--clean", action="store_true", dest="clean_only",
                   help="yalnizca uretilen ciktilari sil ve cik")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.list_steps:
        for script, desc in STEPS:
            print(f"  {Path(script).stem:<16} {desc}")
        return 0

    if args.clean_only:
        clean_outputs()
        return 0

    try:
        steps = select_steps(args.only)
    except ValueError as exc:
        print(f"HATA: {exc}")
        return 2

    # --only ile temizlik YAPILMAZ: temizlik butun uretilen ciktilari siler,
    # secilmeyen adimlarinkini de. Tek bir adimi yeniden calistirmak, geri
    # kalan raporlari silmek anlamina gelmemeli.
    if args.only:
        print(f"yalnizca {len(steps)} adim calistiriliyor; temizlik atlandi\n")
    elif not args.keep:
        clean_outputs()

    failed = []
    t0 = time.time()
    for script, desc in steps:
        name = Path(script).stem
        print(f"  {name:<16} {desc:<42}", end="", flush=True)
        t = time.time()
        r = subprocess.run([sys.executable, str(ROOT / script)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            print(f"OK  ({time.time() - t:.1f}s)")
        else:
            print("HATA")
            failed.append((name, r.stderr.strip().splitlines()[-1:]))

    print(f"\ntoplam {time.time() - t0:.1f}s")
    if failed:
        print("\nBASARISIZ:")
        for name, err in failed:
            print(f"  {name}: {' '.join(err)}")
        return 1
    print("pipeline tamam.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
