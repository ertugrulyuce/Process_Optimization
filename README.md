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

## Kurulum

Python 3.11 veya uzeri gerekir (numpy 2.x ve pandas 2.2 bagimliligi).

```bash
pip install -r requirements.txt
```

Geliştirme için ek olarak:

```bash
pip install -r requirements-dev.txt
pre-commit install   # commit öncesi ruff — isteğe bağlı, aynı kurallar CI'da da çalışır
```

Ham CSV'yi Kaggle'dan indirip `data/raw/continuous_factory_process.csv` olarak
kaydedin.

> ⚠️ **Ham CSV'yi Excel'de açmayın.** Türkçe/Avrupa locale ayarlarında Excel
> ondalıklı sayıları tarihe çevirir (`11.54` → `Kas.54`) ve bu **geri alınamaz**
> (`13.5` ve `13.05` ikisi de `13.May` olur). Bu projede bir kez yaşandı —
> 556.563 hücre (%34,4) bozulmuştu. Bozuk kopya `data/_quarantine/` altında
> gerekçesiyle duruyor.

## Çalıştırma

```bash
make lint    # ruff — kural seti ve gerekçeleri ruff.toml içinde
make test    # import kontrolü + pytest (ham veri gerekmez)
make run     # tüm pipeline — 12 adım, ~6 dakika
make clean   # yalnızca üretilen çıktıları sil
```

`make` kurulu değilse aynı komutlar doğrudan çalıştırılabilir:

```bash
python run_all.py                # temizle + 12 adım
python run_all.py --keep         # temizlemeden çalıştır
python run_all.py --only clean   # tek adım — temizlik yapılmaz
python run_all.py --list         # adımları listele
```

Adımlar sırayla: veri denetimi → A1 varsayım testi → temizlik + KPI → değişken
sözlüğü → capability → korelasyon → transport delay → modelleme → optimizasyon
→ validation → öneriler → görseller.

Tüm raporlar script çıktısıdır, elle düzenlenmez. `reports/` silinebilir ve
yeniden üretilir; elle yazılan dokümanlar `docs/` altındadır.

## Yapı

```text
data/raw/          Kaggle orijinali (repoya girmez)
data/processed/    clean_v1.csv — temizlenmiş veri + KPI'lar
data/_quarantine/  Excel'in bozduğu kopya + gerekçe
src/
  data_processing/ schema, audit, verify_a1, clean, data_dictionary
  analysis/        capability, correlation, stage_link, validation,
                   recommendations, figures
  modeling/        splits, train
  optimization/    optimize
reports/           9 üretilen rapor + figürler (script çıktısı)
docs/              technical_report, assumptions, plan_v0_original
tests/             pytest — veriye dokunmayan birim testleri
tools/             check_imports — CI'nin import zincirini doğrulaması
run_all.py         pipeline sürücüsü — `--only` ile tek adım
Makefile           make test / run / clean kısayolları
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
