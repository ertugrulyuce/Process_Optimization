"""
reports/ icin hash manifest: rapor ciktilari yeniden uretilebilir mi?

reports/ repoya giriyor ve README'deki her sayi oradan geliyor. Kod degisince
rapor sessizce kayabilir -- refactor "davranis degistirmez" sanilir, CSV'de
ucuncu ondalik oynar, kimse fark etmez. Manifest, commit edilmis her raporun
hash'ini tutar; pipeline yeniden calistirildiktan sonra kontrol edilir.

    python tools/report_manifest.py            # kontrol (varsayilan)
    python tools/report_manifest.py --update   # manifesti yeniden yaz

Tipik kullanim:
    python run_all.py --only train
    python tools/report_manifest.py            # fark yoksa rapor kaymamis

Fark CIKMASI GEREKIYORSA (bilincli bir degisiklik), --update ile manifest
yenilenir ve raporla ayni commit'e girer. Boylece rapor degisikligi
diff'te acikca gorunur, sessiz kalmaz.

CI'da ham veri yok, pipeline calistirilamaz. Orada kontrol daha dar bir soruyu
cevaplar: commit edilen raporlar manifestle tutarli mi? Elle duzenlenmis bir
rapor ya da manifesti guncellenmeden commit edilen bir cikti orada yakalanir.

Kapsam: reports/*.md ve reports/*.csv. Figurler (PNG) disarida: baytlari
matplotlib/freetype surumune bagli, ayni veriyle farkli makinede farkli
hash uretirler -- bu yeniden uretilebilirlik degil, ortam farki olurdu.

Satir sonlari hash'ten once LF'ye cevrilir. core.autocrlf=true olan Windows
kopyasinda dosyalar CRLF, CI'da LF; ham bayt hash'i her dosyayi "degismis"
gosterirdi.
"""
import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
MANIFEST_NAME = "MANIFEST.sha256"
PATTERNS = ("*.md", "*.csv")


def file_hash(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def compute(reports=REPORTS):
    """{dosya adi: sha256}. Ad sirasina gore, manifestin kendisi haric."""
    files = sorted({p for pat in PATTERNS for p in reports.glob(pat)},
                   key=lambda p: p.name)
    return {p.name: file_hash(p) for p in files if p.name != MANIFEST_NAME}


def write(hashes, path):
    # sha256sum bicimi: `sha256sum -c` ile de dogrulanabilir (LF kopyada)
    text = "".join(f"{h}  {name}\n" for name, h in hashes.items())
    path.write_bytes(text.encode("ascii"))


def read(path):
    hashes = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if line.strip():
            h, name = line.split("  ", 1)
            hashes[name] = h
    return hashes


def compare(expected, actual):
    """(degisen, eksik, fazla) -- her biri sirali dosya adi listesi."""
    changed = sorted(n for n in expected.keys() & actual.keys()
                     if expected[n] != actual[n])
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    return changed, missing, extra


def main(argv=None, reports=REPORTS):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--update", action="store_true",
                    help="manifesti mevcut raporlardan yeniden yaz")
    args = ap.parse_args(argv)

    manifest = reports / MANIFEST_NAME
    actual = compute(reports)

    if args.update:
        write(actual, manifest)
        print(f"yazildi: {manifest.relative_to(reports.parent)} ({len(actual)} dosya)")
        return 0

    if not manifest.exists():
        print(f"HATA: {MANIFEST_NAME} yok -- once --update ile olusturun.")
        return 1

    changed, missing, extra = compare(read(manifest), actual)
    for label, names in (("degisti", changed), ("eksik  ", missing), ("fazla  ", extra)):
        for n in names:
            print(f"{label} {n}")

    if changed or missing or extra:
        print("\nRaporlar manifestle uyusmuyor. Fark bilincliyse:"
              " python tools/report_manifest.py --update")
        return 1

    print(f"tamam: {len(actual)} rapor manifestle ayni")
    return 0


if __name__ == "__main__":
    sys.exit(main())
