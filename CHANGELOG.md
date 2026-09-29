# Değişiklik Günlüğü

Bu projedeki önemli değişiklikler. Biçim
[Keep a Changelog](https://keepachangelog.com/tr-TR/1.1.0/) örnek alınarak
yazıldı. Sürüm etiketi yok, bölümler tarihe göre. Ayrıntı ve gerekçe ilgili
commit mesajındadır (kısa SHA parantez içinde).

**Rapor etkisi** satırı, değişikliğin `reports/` altındaki bir sayıyı ya da
metni değiştirip değiştirmediğini söyler. Belirtilmeyen her değişiklikte
raporlar birebir aynı kaldı (`tools/report_manifest.py`).

---

## 2026-09-29

### Düzeltilen
- R8'in %1 eşiği için yazılan gerekçe ("artifaktlarla gerçek ölçümler arasında
  geniş boşluk") veride tutmuyordu: eşiğin iki yanında aynı türden değerler
  var. Eşik değişmedi; gerekçe, sonucun eşiğe bağlı olmadığını gösteren
  hesaplanmış bir duyarlılık taramasıyla değiştirildi (`clean.py`, A10).
  **Rapor etkisi:** `02_cleaning_report.md`'ye tarama tablosu eklendi.
  Mevcut sayıların hiçbiri değişmedi, temizlenmiş veri aynı (`bb575c0`).
- Değişken sözlüğü her kolonun değişim sayısını 1 fazla gösteriyordu (ilk
  satırın NaN farkı değişim sayılıyordu) (`4cc6be1`). **Rapor etkisi:**
  `data_dictionary.csv/.md`'de yalnızca `n_changes`, her satırda 1 eksik.
- Rapor kodunda elle yazılmış ~85 sayı hesaplanan değere bağlandı
  (`4b8898b`). Bu sırada üç yanlış sayı çıktı: "lag-1 otokorelasyon
  0.93–0.99" hiçbir değişken kümesinde tutmuyor (output'larda medyan 0.89,
  karar değişkenlerinde 0.99); R7 bloğunda `Stage2.M6` için 0.197 ve %5295,
  doğrusu 0.196 ve %5296. **Rapor etkisi:** `02`'de R7 bloğu, `03` ve
  `04`'te lag-1 cümlesi; diğer raporlar birebir aynı.

## 2026-09-27

### Eklenen
- `docs/architecture.md`: pipeline akış şeması, adım başına okunan/yazılan
  dosyalar, modül import bağımlılıkları, doğrulama katmanları (`5977d8b`).
- `requirements.lock`: commit edilmiş raporları üreten tam sürümler (19
  paket). scipy 1.17.1'de, çünkü 1.18 Python 3.11'i bıraktı; bu lock'la
  sıfırdan tam pipeline çalıştırıldı, raporlar aynı. `requirements.txt` ile
  uyumu test ediliyor, kurulabilirliği CI'da her Python sürümünde
  doğrulanıyor (`14d515d`).
- `CHANGELOG.md`: bu dosya (`ccbabb6`).
- `tests/test_stage_link.py`: `stage_link.py` için ilk testler.

### Değişen
- `src/data_processing` altındaki beş modüle type hint eklendi. mypy
  (`--strict` dahil) temiz; mypy iki yanlış ipucunu yakaladı, düzeltildi
  (`b64570c`).
- README sadeleştirildi: hızlı başlangıç bölümü, `make` ve doğrudan
  komutlar tek tabloda (`473a977`).

### Düzeltilen
- `make dashboard` hedefi hiç tanımlanmamıştı; README ve `make help` onu
  gösteriyordu. CI artık hedefin varlığını `make -n` ile doğruluyor
  (`99eeed3`).
- Temizlik raporu 103 hücreyi hem R2'de hem R8'de sayıyordu (`e668ede`).
  **Rapor etkisi:** `02_cleaning_report.md`'de R8 185 → 82 hücre, toplam
  %18,7 → %18,6. Temizlenmiş veri aynı.
- Rapor kodunda elle yazılmış 10 sayı eski bir çalıştırmadan kalmıştı; artık
  ilgili adımın çıktısından hesaplanıyor (`20e5475`). **Rapor etkisi:** 6
  markdown rapor (örn. `09`'da medyan OOC %38,5 → %41,8, `04`'te medyan
  n_eff 465 → 442). CSV değişmedi.
- Gecikme dağılımı tablosu tam tarama sınırında (900 sn) tepe yapan 2 çifti
  düşürüyordu (`cade939`). **Rapor etkisi:** `05_stage_link_report.md`'de
  tablo toplamı 146 → 148.
- README, teknik rapor, varsayımlar ve plan dosyasındaki eski sayılar
  raporlarla eşitlendi. Çoğu R8 kuralından önceki bir çalıştırmadan
  kalmıştı (`e85b462`).

### Kaldırılan
- `statsmodels` bağımlılığı. İlk sürümden beri `requirements.txt`'te
  duruyordu ama hiçbir modül import etmiyordu (`ad1d25d`).

## 2026-09-21

### Eklenen
- `reports/MANIFEST.sha256` ve `tools/report_manifest.py`: commit edilmiş 24
  raporun (md + csv) hash'i. Kod değişikliğinin raporu sessizce kaydırmasını
  yakalar. PNG'ler kapsam dışı (`74d002d`).
- CI'da manifest tutarlılık adımı, `make check-reports` (`800f74a`).

### Düzeltilen
- `train.py`: permutation importance sıralaması aynı veriyle iki çalışmada
  farklı çıkıyordu (`n_jobs=-1` bit gürültüsü + beraberlik). Artık 5 haneye
  yuvarlanmış değere, beraberlikte ada göre sıralanıyor (`778e20e`).
  **Rapor etkisi:** `feature_importance.csv`'de 3 yer değişimi (5 hanede eşit
  çiftler); top-8 kümeleri, değerler ve markdown raporlar aynı.

## 2026-09-20

### Eklenen
- `dashboard/`: Streamlit KPI panosu. Yalnızca commit edilmiş
  `reports/*.csv`'yi okur, ham veri gerektirmez (`289ec11`, `23fdfba`).

## 2026-09-19

### Eklenen
- `notebooks/01_kesif.ipynb`: keşif defteri (`2db4456`).
- Defter çıktılarının repoya girmemesi: nbstripout pre-commit kancası ve
  `tests/test_notebooks.py` (`ee4d702`).

## 2026-09-18

### Düzeltilen
- `optimize.py`: çözüm bulunamadığında (hedef output ya da aktif CPP yoksa)
  ilgisiz yerlerde çökmek yerine nedenini yazan `NoSolutionError` veriyor
  (`16a19bc`).

## 2026-09-17

### Eklenen
- ruff + pre-commit yapılandırması, CI lint adımı. Kural seti E, F, W, I;
  elenen kurallar `ruff.toml` içinde gerekçeli (`c23751e`, `d249e06`,
  `0d26de8`).

## 2026-09-16

### Eklenen
- `run_all.py --only`, `--list`, `--clean` bayrakları (`b6ce7a4`).
- `Makefile`: `make test / run / clean`; CI'da doğrulanıyor (`b87fff8`).

## 2026-09-13 – 2026-09-15

### Eklenen
- Birim testleri: `clean.py` (19), `capability.py` (16), `splits.py` (70),
  `correlation.py` (25) (`e0fee0f`, `10be872`, `0553494`, `e22fa23`).

### Değişen
- `clean.py` içindeki gömülü eşikler adlandırılmış sabitlere taşındı
  (`eadbd40`).

### Düzeltilen
- `capability.py`: `sigma_st = 0` ve yetersiz veri için açık davranış.
  Az output'lu veride C2–C4 bulgularına "Cpk = nan" satırı giriyordu
  (`eb1b48a`).
- Temizlik raporu eklenen kolonları "3 flag + 1 seq" diye yazıyordu; doğrusu
  2 flag + 1 seq (`cc35066`). **Rapor etkisi:** `02_cleaning_report.md`'de
  tek satır; tablo boyutu zaten doğruydu.

## 2026-09-11 – 2026-09-12

### Eklenen
- `LICENSE` (MIT). README MIT diyordu, dosya yoktu (`6e401ec`).
- pytest altyapısı ve `schema.py` için 23 test (`719c328`).
- GitHub Actions CI: testler + import kontrolü, Python 3.11/3.12/3.13
  (`d9e599b`).
- README rozetleri (`def7528`).

## 2026-09-09

### Düzeltilen
- DOE güç karşılaştırması: "~190 saat gözlemsel = ~4 saat deney" yanlıştı.
  4 saat önerilen tasarımın net koşu süresi; güç eşdeğeri ~28 saat
  (`3fe550c`).

## 2026-09-02

### Eklenen
- Uçtan uca analiz: 12 adımlı pipeline, 9 rapor, teknik rapor ve
  varsayımlar logu (`ab7a86d`).
