# Continuous Manufacturing Process Optimization

[![CI](https://github.com/ertugrulyuce/Process_Optimization/actions/workflows/ci.yml/badge.svg)](https://github.com/ertugrulyuce/Process_Optimization/actions/workflows/ci.yml)
[![Lisans: MIT](https://img.shields.io/badge/lisans-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Gerçek bir sürekli akış üretim prosesinden alınan veriyle uçtan uca proses
optimizasyon çalışması. Detroit yakınlarındaki bir hattan 14.088 gözlem,
116 değişken, 1 Hz örnekleme, 3 saat 55 dakika.

**Veri:** [Multistage Continuous-Flow Manufacturing Process](https://www.kaggle.com/datasets/supergus/multistage-continuousflow-manufacturing-process)
— Liveline Technologies. Veri 6 Mart 2019'da kaydedildi, Ocak 2020'de
Kaggle'da yayımlandı. Ham veri bu repoda **yer almaz** (bkz. Lisans).

---

## Sonuç

Bu çalışmanın çıktısı bir optimizasyon tablosu değil, **bir teşhis.**

Veriden *"şu parametreleri şu değerlere çekin, sapma şu kadar azalır"* türü bir
öneri çıkmadı — ve bunun sebebi yöntem değil, verinin yapısı. Karar
değişkenlerinin otokorelasyonu 33+ dakika sönmüyor; 14.088 satır bu parametreler
açısından **~7 bağımsız blok** demek. Optimizasyonun öğreneceği kontrast yok.

**En yüksek getirili bulgu modelden çıkmadı:** 25 kapsam içi çıktının 14'ünde
hatanın %60'tan fazlası merkezleme kaymasından geliyor. `Stage1.M1` hedefin %39
altında ve hatasının %98'i bias — bir ayar/kalibrasyon problemi, model
gerektirmiyor.

İkinci çıktı, optimizasyonun önünü açacak somut bir deney tasarımı: 5 faktör,
2 seviye, yarım-kesir faktöriyel — 16 koşul × 3 replikasyon ≈ ~4 saat net koşu
süresi. Güç karşılaştırması ayrı bir sayı: gözlenen etki büyüklüğünde (d = 0,31)
%80 güce ulaşmak gözlemsel veriyle ~190 saat, tasarlanmış deneyle ~28 saat
sürer (bkz. teknik rapor §7 A6).

📖 **[Analiz Raporu](https://claude.ai/code/artifact/96278aab-51d0-4a3b-acb2-7a592394e36b)** — çalışmanın tamamı, figürlerle
📊 **[Proses Optimizasyon Panosu](https://claude.ai/code/artifact/8a183a29-74ce-4d2d-abbf-157c08a5d22d)** — filtrelenebilir interaktif özet
📄 **[Teknik Rapor](docs/technical_report.md)** — repo içi, tam metodoloji

---

## Hızlı başlangıç

Python 3.11 veya üzeri gerekir.

```bash
git clone https://github.com/ertugrulyuce/Process_Optimization.git
cd Process_Optimization
pip install -r requirements.lock   # raporları üreten tam sürümler
make test                          # ham veri gerekmez
```

Raporlar repoda olduğu için okumak ve panoyu açmak için bu kadarı yeterli.
Pipeline'ı gerçek veriyle yeniden çalıştırmak için ham CSV'yi
[Kaggle'dan](https://www.kaggle.com/datasets/supergus/multistage-continuousflow-manufacturing-process)
indirip `data/raw/continuous_factory_process.csv` olarak kaydedin:

```bash
make run             # 12 adım, ~6 dakika
make check-reports   # "tamam: 24 rapor manifestle ayni" → raporlar birebir yeniden üretildi
```

> ⚠️ **Ham CSV'yi Excel'de açmayın.** Türkçe/Avrupa locale ayarlarında Excel
> ondalıklı sayıları tarihe çevirir (`11.54` → `Kas.54`) ve bu **geri alınamaz**
> (`13.5` ve `13.05` ikisi de `13.May` olur). Bu projede bir kez yaşandı —
> 556.563 hücre (%34,4) bozulmuştu. Bozuk kopya `data/_quarantine/` altında
> gerekçesiyle duruyor.

`requirements.lock` tam sürümleri sabitler; `requirements.txt` yalnızca alt
sınır verir ve daha yeni sürümleri kurar. Bu da çalışır; yalnızca
`make check-reports` bir fark gösterirse sebebi kod değil sürüm farkı olabilir.

## Komutlar

`make` kurulu değilse (Windows'ta genelde yoktur) sağdaki komut aynı işi yapar.

| make | doğrudan | ne yapar |
|---|---|---|
| `make test` | `python tools/check_imports.py` + `python -m pytest` | import zinciri + testler; ham veri gerekmez |
| `make lint` | `python -m ruff check .` | kural seti ve gerekçeleri `ruff.toml` içinde |
| `make run` | `python run_all.py` | üretilen çıktıları sil + 12 adımı çalıştır |
| | `python run_all.py --only clean` | tek adım, temizlik yapılmaz (`--list` adımları gösterir) |
| `make check-reports` | `python tools/report_manifest.py` | raporlar `reports/MANIFEST.sha256` ile aynı mı |
| `make clean` | `python run_all.py --clean` | yalnızca üretilen çıktıları sil; `docs/` korunur |
| `make dashboard` | `python -m streamlit run dashboard/app.py` | KPI panosu; önce `pip install -r dashboard/requirements.txt` |

Tüm raporlar script çıktısıdır, elle düzenlenmez. Kod değişikliği bir raporu
değiştiriyorsa bu bilinçli olmalı: `python tools/report_manifest.py --update`
ve rapor aynı commit'e girer, yoksa CI kırmızıya döner. Pano hiçbir sayıyı
yeniden hesaplamaz, commit edilmiş CSV'leri okur; ham veri olmadan da çalışır.

Adımların hangi dosyayı okuyup yazdığı ve doğrulama katmanları:
[`docs/architecture.md`](docs/architecture.md).

**Geliştirme:** `pip install -r requirements-dev.txt` ve isteğe bağlı olarak
`pre-commit install` (commit öncesi ruff + defter çıktısı temizliği; aynı
kontroller CI'da da çalışır). Değişiklikler: [`CHANGELOG.md`](CHANGELOG.md).

## Yapı

```text
data/raw/          Kaggle orijinali (repoya girmez)
data/processed/    clean_v1.csv — temizlenmiş veri + KPI'lar (repoya girmez)
data/_quarantine/  Excel'in bozduğu kopya + gerekçe
src/
  data_processing/ schema, audit, verify_a1, clean, data_dictionary
  analysis/        capability, correlation, stage_link, validation,
                   recommendations, figures
  modeling/        splits, train
  optimization/    optimize
reports/           9 üretilen rapor + tablolar + figürler, MANIFEST.sha256
docs/              architecture, technical_report, assumptions, plan_v0_original
notebooks/         01_kesif — keşif defteri (hücre çıktıları commit edilmez)
dashboard/         Streamlit KPI panosu — reports/ CSV'lerini okur
tests/             pytest — ham veriye dokunmayan testler
tools/             check_imports, report_manifest — CI kontrolleri
run_all.py         pipeline sürücüsü
```

## Metodolojik duruş

Projenin ayırt edici tarafı, sonuçları değil **neyin sonuç sayılmadığını**
belirleme biçimi:

- **Rastgele train/test split kullanılmadı.** Aynı model, aynı veri: rastgele
  split R² = 0,97, doğru bloklu split R² = −6,89. Aradaki fark modelin değil,
  değerlendirme yönteminin sonucu.
- **Her model bir naive baseline'a karşı ölçüldü.** "Önceki değeri tekrarla"
  tahmini hiçbir şey öğrenmeden R² = 0,85 alıyor; bu eşiği geçemeyen model
  prosese dair bilgi taşımıyor.
- **İki düzeltme birlikte uygulandı.** Otokorelasyon (Bartlett'in tam formülü)
  ve çoklu karşılaştırma (Benjamini-Hochberg FDR). 600 çiftte ham testte 434
  "anlamlı" ilişki, düzeltme sonrası 81.
- **Tüm sonuçlar walk-forward ile sınandı** — ve bazıları ayakta kalmadı.
  "5 çıktıda persistence geçildi" sonucu tek bölmeye dayanıyordu; 5 pencerede
  hiçbir çıktı tüm fold'larda pozitif kalmadı.
- **Her varsayım, yanlış çıkarsa neyi geçersiz kılacağıyla kayıtlı**
  ([`docs/assumptions.md`](docs/assumptions.md), A1–A11).

## Kısıtlar

Proje boyunca ölçülen ve kapsamı belirleyen 24 kısıt. En kritik olanlar:

| # | Kısıt |
|---|---|
| K1 | Veri tek bir 3,9 saatlik pencereden — long-term capability analiz edilemez |
| K2 | Çıktı ölçümlerinin %18,6'sı geçersiz; 30 çıktının 5'i kapsam dışı |
| K5 | Otokorelasyon lag-1'de 0,99 — rastgele split geçersiz |
| K6 | Hata iki tipte: 14 bias-, 9 variability-baskın, 2 belirsiz |
| K7 | Gerçek karar uzayı 24 değil 5 değişken |
| K8 | `Machine4.Temperature4` ile `Machine4.Pressure` birebir özdeş — veri hatası |
| K9 | `.C.`/`.U.` ekinin anlamı doğrulanamadı — riski ölçüldü, kapatılmadı |
| K10 | I-MR control chart bu veri için geçersiz — OOC oranı %38,5 |
| K14 | Rastgele split R² 0,97 → doğru split −6,89 |
| K21 | CPP otokorelasyonu 2000 gecikmede sönmüyor → ~7 bağımsız blok |
| K22 | Tek split sonuçları walk-forward'da ayakta kalmıyor |
| K24 | Proses merkezi gürültüden hızlı kayıyor (2,29σ'ya kadar) |

Tam liste ve gerekçeler:
[`continuous_manufacturing_process_optimization_plan.md`](continuous_manufacturing_process_optimization_plan.md)

## İlke

Veri neyi söyleyemiyorsa, o iddia edilmiyor. Bir kısıtı fark edip sınırını
ölçmek, o kısıtı görmezden gelip güçlü bir sonuç iddia etmekten daha değerlidir.

Sonuçlar gözlemsel veriye dayanır; hiçbiri nedensellik iddia etmez.

---

## Lisans

**Kod ve raporlar** (bu repodaki her şey): MIT — tam metin [LICENSE](LICENSE).

**Veri:** Bu repo ham veriyi içermez ve dağıtmaz. Kaggle'daki lisans kaydı
`Data files © Original Authors` — açık bir lisans verilmemiş, telif orijinal
yazarlarda (Liveline Technologies) kalmıştır. Veriyi kullanmak isteyenlerin
[kaynağından](https://www.kaggle.com/datasets/supergus/multistage-continuousflow-manufacturing-process)
kendilerinin indirmesi gerekir; `.gitignore` `data/` altındaki tüm CSV'leri
repo dışında tutar.

Bu bağımsız bir portföy çalışmasıdır; Liveline Technologies ile herhangi bir
bağlantısı yoktur ve şirket tarafından desteklenmemiştir.
