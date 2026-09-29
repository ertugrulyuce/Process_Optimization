# Continuous Manufacturing Process Optimization — Plan v1

> **v1 notu.** Bu plan, Sprint 1 data audit sonrasında revize edildi. v0 (audit
> öncesi hâli) `docs/plan_v0_original.md` içinde duruyor. Değişiklikler:
> 13 sprint → 6 faz; verinin gerçek kısıtları kapsamı daralttı; kontrol
> edilebilir / edilemez değişken ayrımı eklendi.

---

## Proje Amacı

Gerçek bir multistage continuous-flow manufacturing prosesinden alınan veriyi
kullanarak uçtan uca bir **Process Optimization** çalışması yürütmek.

**Ana problem:** Kontrol edilebilir proses parametrelerinin ürün boyutsal
çıktılarının hedeflerinden sapmasına etkisini belirlemek ve deviation'ı
azaltabilecek çalışma koşullarını ortaya çıkarmak.

### Temel prensipler
- Sonuçlar önceden belirlenmeyecek.
- Veri istenen sonucu verecek şekilde manipüle edilmeyecek.
- Varsayımlar gerçek veriden ayrı tutulacak → `docs/assumptions.md`
- Korelasyon doğrudan nedensellik olarak yorumlanmayacak.
- ML amaç değil, mühendislik problemini çözmek için araç olacak.
- Her önemli kararın teknik gerekçesi dokümante edilecek.
- **Veri neyi söyleyemiyorsa, o iddia edilmeyecek.**

---

## Veri ve Proses

**Dataset:** Multistage Continuous-Flow Manufacturing Process (Liveline
Technologies, Detroit, 2019)
**Kaynak:** https://www.kaggle.com/datasets/supergus/multistage-continuousflow-manufacturing-process

**14.088 gözlem × 116 değişken.** 1 Hz örnekleme, `2019-03-06 10:52 → 14:47`.

```text
                    ┌── Machine 1 ──┐
                    │               │
Raw Material ───────┼── Machine 2 ──┼──→ Combiner → Stage 1 Output (15 ölçüm)
                    │               │
                    └── Machine 3 ──┘
                                           ↓
                                      Machine 4 → Machine 5
                                           ↓
                                    Stage 2 Output (15 ölçüm)
```

### Değişken rolleri

`src/data_processing/schema.py` her kolonu role ayırır (116/116, `unknown` yok):

| Rol | Adet | Optimizasyondaki yeri |
|---|---|---|
| `controlled` | 25 | **Karar değişkenleri** — oynayabildiğimiz tek şey |
| `measured` | 16 | Proses tepkisi — teşhis değişkeni, girdi değil |
| `ambient` + `raw_material` | 14 | Gürültü — kontrol edilemez |
| `output_actual` | 30 | Optimize edilen çıktı |
| `output_setpoint` | 30 | Sabit hedef (model girdisi **değil**) |

---

# Verinin Kısıtları — Kapsamı Belirleyen Bulgular

Bunlar Sprint 1'de ölçüldü. Planın hangi maddelerinin geçersiz olduğunu
belirledikleri için en başta duruyorlar. Ayrıntı: `reports/01_data_quality_report.md`

### K1 — Veri tek bir ~4 saatlik pencereden
14.088 satır bol görünür ama tek vardiyanın yarısı.
**Kapsam dışı:** long-term capability, vardiya/rejim karşılaştırması, gün-hafta
trendi, mevsimsellik. Sprint 4 short-term capability ile sınırlı.

### K2 — Output'lardaki sıfırlar sensör dropout
Setpoint'i 2.74 olan bir boyut %95 oranında tam 0. Sıfırlar tek duruş bloğunda
değil, yüzlerce kısa kesinti hâlinde (Stage1.M14 → 673 kesinti).
**Kapsam dışı (R6):** `Stage1.M5`, `Stage1.M7`, `Stage1.M11`, `Stage2.M4` —
geçerli veri < %50. Silinmez, gerekçesiyle "kapsam dışı" listelenir.

**Kapsam dışı (R7):** `Stage2.M6` — setpoint'i 0.01, sapmasının standart sapması
0.196. Hedef, ölçüm gürültüsünün yirmide biri; gerçek bir hedef değil. Oransal
KPI'ları tanımsız (bkz. A8).

**Modellenebilir: 30 output'tan 25'i.**

### K3 — Setpoint'ler sabit
Stage2'nin 15 setpoint'i tek değer, Stage1'inkiler sabit + duruş bloğunda 0.
Setpoint bir model girdisi olarak **sıfır bilgi taşır**. Tek rolü deviation'ın
referans noktası olmak.

### K4 — Gürültü değişkenlerinin 12'si pratikte sabit
`Machine2.RawMaterial.Property1-4` tüm veri boyunca **1 kez** değişiyor.
Ambient sıcaklık ~352 sn'de bir güncelleniyor → 4 saatte ~40 bağımsız gözlem.
**Kapsam dışı:** "hammadde varyasyonunun etkisi" ve "ambient koşulların etkisi"
bu veriyle araştırılamaz. Analiz kontrol edilebilir parametrelere odaklanır.

### K5 — Otokorelasyon lag-1'de 0.99
**Rastgele train/test split yasak.** Test seti train'in kopyası olur, R² sahte
çıkar. Bloklu / zaman-sıralı split zorunlu. Bu, projenin tek en kolay hata yapma
noktasıdır.

### K6 — Merkezleme (bias) problemi variability'den ayrı
Bazı output'lar hedeften sistematik sapıyor: `Stage1.M6` −53%, `Stage2.M1` −44%,
`Stage1.M1` −39%. Bias ve variability ayrı ele alınır; karıştırılırsa
optimizasyon yanlış şeyi kovalar.

### K7 — Gerçek optimizasyon uzayı 24 değil, 5 değişken
Karar değişkenlerinin 4 saatlik pencerede *ne kadar oynatıldığı* ölçüldü. 25
kolonun **13'ünün varyasyon katsayısı %0.5'in altında** — proses onları
neredeyse hiç değiştirmemiş. Machine5'in sıcaklıkları pratikte sabit
(CV %0.01–0.66, hepsi %1'in altında): bir değişken hiç değişmediyse etkisi öğrenilemez, dolayısıyla
onun için "optimum" da bulunamaz.

**Anlamlı varyasyon gösteren 5 değişken — projenin gerçek karar uzayı:**

| Değişken | Aralık | CV |
|---|---|---|
| `Machine1.MotorRPM` | 10.39 – 12.24 | %5.74 |
| `Machine4.Temperature4` / `Pressure` | 14 – 25 | %5.46 |
| `Machine3.MotorRPM` | 11.96 – 14.00 | %3.28 |
| `Machine1.ExitZoneTemperature` | 69.7 – 80.0 | %2.71 |
| `Machine4.Temperature3` | 268 – 327 | %1.15 |

**Sonucu:** Optimizasyon bu değişkenler üzerinde kurulur. Diğerleri modelde
kalır ama "optimize edilebilir" diye sunulmaz — sabit çalışma koşulu olarak
raporlanır. Bu, kapsamı daraltmaz; **odaklar.**

### K8 — İki kolon çifti birebir özdeş
- `Machine4.Temperature4.C.Actual` **==** `Machine4.Pressure.C.Actual`
  (14.088 satırın tamamında). Bir sıcaklık ile bir basınç aynı olamaz — bu bir
  veri/adlandırma hatasıdır. Biri düşürülür, hangisi olduğu raporlanır.
- `Stage2.Output.Measurement1.U.Setpoint` **==** `Stage2.Output.Measurement14.U.Setpoint`
  (ikisi de sabit 11.71 — K3 gereği zaten model girdisi değil).

Bu çiftler modelde bırakılırsa yapay multicollinearity ve şişirilmiş feature
importance üretir.

### K9 — A1 varsayımı açık
`.C.`/`.U.` ekinin anlamı doğrulanamadı (dokümantasyon yok, ampirik test
sonuçsuz). Domain bilgisine dayanıyor. **Sprint 4'te duyarlılık analizi ile
sınırı ölçülecek.** Ayrıntı: `docs/assumptions.md` A1.

---

# Faz Planı

v0'daki 13 sprint 6 faza indirildi. Gerekçe: Sprint 0/1/2 aynı işin parçaları
(veri temeli); 3/4 birlikte proses karakterizasyonu; 5/6 birlikte (root cause
zaten model üstünden çıkacak); 8/9 birlikte (senaryo ve validation aynı
holdout'u kullanır).

---

## Faz 1 — Veri Temeli ✅ *(tamamlandı)*
*v0: Sprint 0 + 1 + 2*

**Amaç:** Ham veriyi güvenilir hâle getirmek ve prosesle eşlemek.

- [x] Data audit → `reports/01_data_quality_report.md`
- [x] Değişken şeması ve rol sınıflandırması → `src/data_processing/schema.py`
- [x] Varsayım log'u → `docs/assumptions.md`
- [x] A1 doğrulama denemesi → `reports/a1_verification.md`
- [x] **`clean.py`** — R1–R8 kuralları, `data/processed/clean_v1.csv`
- [x] Deviation KPI'ları (signed / absolute / relative) — bias ve variability ayrı
- [x] Cleaning report → `reports/02_cleaning_report.md`
- [x] Data dictionary → `reports/data_dictionary.md`

**Çıktı:** Clean Dataset v1 ✅, KPI Dataset ✅, Data Dictionary ✅

### Faz 1 sonucu — optimizasyonun gerçek hedefi

25 kapsam içi output, hata yapısına göre ayrıldı
(`bias_share_pct` = toplam hatanın yüzde kaçı merkezleme kaymasından):

| Tip | Adet | Ne demek | Çözümü |
|---|---|---|---|
| **Bias-baskın** (>%60) | 14 | Proses kararlı ama yanlış noktada | Setpoint / kalibrasyon ayarı |
| **Variability-baskın** (<%40) | 9 | Hedef doğru ama dağılım geniş | Proses kontrolü — **optimizasyonun hedefi** |
| **Belirsiz** (%40–60) | 2 | Bileşenler eşit — `Stage2.M7`, `Stage2.M8` | Faz 2'de control chart ile karara bağlanır |

En uç bias örnekleri: `Stage1.M1` (−39%, hatanın %98'i bias), `Stage2.M1`
(−44%, %98), `Stage2.M14` (−31%, %97).

En yüksek variability: `Stage1.M4` (dev_std 1.112), `Stage1.M13` (0.833),
`Stage2.M2` (0.793).

**Bunun anlamı:** Bias-baskın bir output'u proses parametresi oynatarak
düzeltmeye çalışmak yanlıştır — çözümü setpoint'i düzeltmektir. Faz 4
optimizasyonu **9 variability-baskın output'a** odaklanacak.

---

## Faz 2 — Proses Karakterizasyonu ✅ *(tamamlandı)*
*v0: Sprint 3 + 4*

**Amaç:** Prosesin davranışını, değişkenliğini ve stabilitesini anlamak.

- [x] I-MR control chart istatistikleri, short-term/long-term sigma
      → `reports/03_capability_report.md`
- [x] Cp/Cpk — üç varsayımsal tolerans senaryosuyla (A4)
- [x] Otokorelasyon + çoklu karşılaştırma düzeltmeli korelasyon
      → `reports/04_correlation_report.md`
- [x] Stage 1 → Stage 2 transport delay araması (A5)
      → `reports/05_stage_link_report.md`
- [x] Görseller → `reports/figures/`

### Faz 2 sonuçları

**K10 — Control chart bu veri için geçersiz araç.** Medyan out-of-control oranı
**%41.8**; kararlı bir proseste ~%0.3 olmalı. Sebep proses değil yöntem: I-MR
bağımsız gözlem varsayar, bu veride output'ların lag-1 otokorelasyonu medyan 0.89
(0.37–0.99). `MR_bar`
küçük çıkıyor → kontrol limitleri gerçekte olması gerekenden dar. **Kararlılık
hükmü askıya alındı**; doğru araç, Faz 3'te model kurulduktan sonra artıklar
üzerinde kontrol grafiği (residual chart) olacak.

**K11 — Anlamlı ilişkilerin çoğu istatistiksel yanılsamaymış.** 600 çift
test edildi:

| ölçüt | anlamlı | oran |
|---|---|---|
| Ham `n = 14.088` ile | 437 | %72.8 |
| Otokorelasyon düzeltmesi (`n_eff`) ile | 148 | %24.7 |
| + Çoklu karşılaştırma (FDR) ile | **81** | **%14** |

Medyan `n_eff` = **442**, 14.088 değil. Düzeltme yapılmasaydı **356 sahte
ilişki** raporlanacaktı.

**K12 — Basit ve güçlü bir sürükleyici yok.** Variability-baskın output'lar için
aktif karar değişkenleriyle `|r| > 0.3` olan FDR-sonrası anlamlı ilişki sayısı:
**3**. En yüksek ham korelasyonlar (`Stage1.M4 ← Machine1.MotorRPM`, r = 0.67)
`n_eff ≈ 14` üzerine kurulu, yani anlamsız. Bu, projeyi bitiren bir sonuç değil
— doğrusal korelasyonun yakalayamadığı etkiler (gecikme, etkileşim,
doğrusalsızlık) Faz 3'te test edilecek. Ama **beklenti şimdiden kalibre
edilmeli.**

**K13 — Transport delay ~270 sn.** Çiftlerin yalnızca %7'si lag = 0'da tepe
yapıyor. İlk tarama 0–300 sn'de yapıldı ve tepeler üst sınıra yapışıktı; aralık
900 sn'ye açıldığında tepe yerinde kaldı — yani sınır artifaktı değil. Dağılım
tek tepeli değil (250–300'de 40 çift, 500–550'de 15), bu da tek bir malzeme
akışı yerine birden fazla yol olabileceğini düşündürüyor. **A5 kısmen çözüldü.**

**Çıktı:** Capability Report ✅, Correlation Report ✅, Stage Link Report ✅,
Figures ✅

---

## Faz 3 — Root Cause + Predictive Modeling ✅ *(tamamlandı)*
*v0: Sprint 5 + 6*

**Amaç:** Output deviation'ının hangi kontrol edilebilir parametrelerle ilişkili
olduğunu belirlemek ve ne kadarının açıklanabildiğini ölçmek.

- [ ] **Bloklu / zaman-sıralı split** (K5 — kırmızı çizgi)
- [ ] Baseline: Linear Regression
- [ ] Non-linear: Random Forest, Gradient Boosting
- [ ] MAE / RMSE / R² — baseline'a göre raporlanır, mutlak değil
- [ ] Feature importance + permutation importance
- [ ] Multicollinearity, lag ilişkileri
- [ ] Model sonuçlarını proses bilgisiyle karşılaştır
- [ ] **Critical Process Parameters (CPP)** listesi

**Kırmızı çizgi:** Model açıklama gücü düşük çıkarsa zorlanmayacak. "Bu proses
mevcut parametrelerle tahmin edilemiyor" da geçerli bir bulgudur ve öyle
raporlanır.

**Çıktı:** CPP Listesi ✅, Model Comparison ✅, Feature Importance ✅
→ `reports/06_modeling_report.md`

### Faz 3 sonuçları

**K14 — Rastgele split %97'lik sahte başarı üretiyor.** Aynı model, aynı veri,
sadece bölme yöntemi değişiyor:

| Bölme yöntemi | R² |
|---|---|
| Rastgele split (**yanlış**) | **0.97** |
| Bloklu split + embargo (doğru) | **−6.89** |
| *baseline:* persistence | 0.85 |

Embargo 49 satır — keyfi değil, karar değişkenlerinin otokorelasyonunun 0.2
altına indiği mesafenin medyanı. Bu, aynı veri setiyle yapılan çalışmalarda
yüksek R² bildiren sonuçların bir kısmını açıklar.

**K15 — İki soru ayrışıyor: açıklama ≠ tahmin.**

| Soru | Girdi | Sonuç |
|---|---|---|
| **S1** Karar değişkenleri açıklıyor mu? | sadece `controlled` | 13/25 ortalamayı, **5/25** persistence'ı geçiyor |
| **S2** Deviation tahmin edilebilir mi? | + geçmiş değerler | **17/25** persistence'ı geçiyor |

S2'nin başarısı S1'in yerine geçmez: "deviation'ın bir sonraki değeri öncekine
benziyor" bilgisi hangi parametrenin değiştirileceğini söylemez. **Faz 4 yalnızca
S1'e dayanabilir.**

**K16 — Dağılım kayması var.** Neredeyse tüm output'larda R² negatif ama
`skill_vs_mean` pozitif. Çelişki değil: R² test bloğunun *kendi* ortalamasını
referans alır (gerçekte bilinmez), skill ise train ortalamasını (gerçekçi).
Aradaki fark, deviation dağılımının 4 saatlik pencere içinde bile kaydığını
gösteriyor. Faz 5'te yeniden kalibrasyon ihtiyacı olarak raporlanacak.

### Critical Process Parameters

Permutation importance'ın üst sıraları **pasif** değişkenlerle doluydu
(`Machine5.Temperature6`, CV %0.63). Bir değişken neredeyse sabitken modelin ona
önem atfetmesi genellikle **zaman vekilliğidir** — değişken yavaşça sürükleniyor
ve model onun üzerinden zaman trendini yakalıyor. Nedensel değil.

CPP adayları bu yüzden yalnızca aktif değişkenler arasından seçildi:

| Parametre | CV % | Kaç output'ta | Faz 2'de de anlamlı mı |
|---|---|---|---|
| `Machine4.Temperature3` | 1.15 | 9 | ✅ evet |
| `Machine1.ExitZoneTemperature` | 2.71 | 7 | — |
| `Machine3.MotorRPM` | 3.28 | 4 | — |
| `Machine1.MotorRPM` | 5.74 | 3 | — |
| `Machine4.Pressure` | 5.46 | 2 | ✅ evet |

İki bağımsız yöntem (Faz 2 korelasyon, Faz 3 permutation importance)
`Machine4.Temperature3` ve `Machine4.Pressure` üzerinde birleşiyor — bu
yakınsama güven artırıyor.

---

## Faz 4 — Optimization + Duyarlılık ✅ *(tamamlandı)*
*v0: Sprint 7 + 8*

**Amaç:** CPP'ler için daha iyi çalışma koşulları belirlemek ve sonucun neye
bağlı olduğunu ölçmek.

- [ ] Objective function (bias ve variability ayrı terimler — K6)
- [ ] Karar değişkenleri: yalnızca `controlled` (24 kolon)
- [ ] Constraint set: gözlenen çalışma aralıkları (K1 — dışına ekstrapolasyon yok)
- [ ] Optimum operating point / range
- [ ] **A1 duyarlılık analizi** (K9): karar değişkeni seti daraltılıp
      genişletilerek sonucun varsayıma bağlılığı ölçülür
- [ ] Senaryolar: Current / Conservative / Aggressive
- [ ] Before-After KPI karşılaştırması

**Çıktı:** Optimization Model ✅, Scenario Analysis ✅, A1 Sensitivity ✅
→ `reports/07_optimization_report.md`

### Faz 4 sonuçları

Kapsam bilinçli olarak dar: 5 output (S1'de persistence geçilenler) × 5 aktif CPP.
Arama uzayı yalnızca gözlenen min–max aralığı (K1 — ekstrapolasyon yok).

**K17 — Optimizasyon iki bağımsız yolla kuruldu ve yollar büyük ölçüde
ayrışıyor.** Model R²'si negatif olduğu için model-tabanlı arama tek başına
dayanak sayılmadı; aynı soru gözlenen veriden de soruldu. 25 karşılaştırmanın
yalnızca **7'sinde (%28)** iki yol aynı bölgeyi işaret ediyor. Uzlaşmayan
yerlerde ampirik bulgu esas alındı.

**K18 — Tek tutarlı bulgu: `Machine4.Pressure` 14–17.** 5 output'un 5'i de bu
aralığı en iyi buluyor. Ama bu bir keşif değil, **mevcut ayarın doğrulanması**:
o dilim gözlemlerin %65'ini içeriyor ve etki büyüklükleri küçük (%2–26). İşaret
testi `0.5⁵ = %3.1` verir, ancak output'lar bağımsız olmadığı için gerçek
olasılık daha yüksek. Yön tutarlılığı bir işarettir, kanıt değil.

**K19 — A1 riski düştü.** `measured` değişkenleri eklemek 5/5 output'ta modeli
*kötüleştiriyor*. A1 yanlış olsaydı (yani `.U.` kolonlar da ayarlanabilir olsaydı)
onları eklemek tahmin gücünü artırmalıydı. Bu A1'i kanıtlamaz ama karar
değişkenlerini `.C.` ile sınırlamayı veriye dayalı olarak savunulabilir kılar.

**K20 — 5 CPP'ye daralmak bazı output'lara zarar veriyor.** `Stage2.M10` dar
sette −0.358, geniş sette +0.100. Bu output için optimizasyon önerisi geçersiz
sayıldı.

### Faz 4'ün dürüst özeti

Bu veriden *"şu parametreleri şu değerlere çekin, sapma şu kadar azalır"* türü
bir öneri **çıkmıyor.** Çıkan şey daha mütevazı ama gerçek: proses zaten iyi
çalıştığı bölgede duruyor, etkiler küçük ve gözlemsel, nedensellik iddia
edilemez.

Asıl kısıt veri: 4 saatlik pencerede karar değişkenleri yeterince oynatılmamış
(K7), dolayısıyla optimizasyonun öğreneceği kontrast yok. **Optimizasyonun
önünü açacak şey daha iyi model değil, daha iyi veri.**

---

## Faz 5 — Validation + Endüstriyel Yorum ✅ *(tamamlandı)*
*v0: Sprint 9 + 10*

**Amaç:** Sonuçların dayanıklılığını test etmek ve uygulanabilir öneriye çevirmek.

- [ ] Holdout validation (zaman-sıralı)
- [ ] Robustness / extreme scenario testleri
- [ ] Model ve varsayım limitleri
- [ ] Bulgu → Mühendislik yorumu → Önerilen aksiyon → Beklenen etki →
      Uygulama riski
- [ ] Monitoring ve veri toplama önerileri (özellikle: K1, K4'ü aşmak için
      hangi veri toplanmalı)

**Çıktı:** Validation Report ✅, Industrial Improvement Proposal ✅
→ `reports/08_validation_report.md`, `reports/09_recommendations.md`

### Faz 5 sonuçları

**K21 — Karar değişkenlerinin otokorelasyonu 2000 lag'de bile sönmüyor.**
5 aktif CPP'nin 4'ünde sönümlenme mesafesi tarama sınırına dayandı — yani
ölçülen değil, aramanın durduğu yer. Pratik sonuç: 14.088 satırlık veri bu
parametreler açısından **~7 bağımsız blok** demek. Optimizasyonun öğrenmesi
gereken kontrast tam da burada ve orada bir avuç gözlem var.

**K22 — Tek split sonuçları walk-forward'da ayakta kalmıyor.** Faz 3'ün
"5 output'ta persistence geçildi" sonucu tek bölmeye dayanıyordu. Fold 1
(yetersiz train) dışarıda bırakılsa bile **hiçbir output tüm fold'larda pozitif
kalmıyor**: `Stage2.M10` 0/4, `Stage2.M9` 1/3. Faz 3 ve 4'ün güven derecesi
düşürüldü.

**K23 — Faz 4'ün tek bulgusu koşula bağlı.** `Machine4.Pressure` 14–17 bulgusu
zaman parçalarının **%57'sinde** tutuyor. Kısmen geçerli, ama kararlı değil.

**K24 — Proses merkezi gürültüden hızlı kayıyor.** 5 output'un 3'ünde pencereler
arası kayma, serinin kendi standart sapmasından büyük (`Stage2.M9`: 2.29σ).
Sabit setpoint önerisi kısa ömürlüdür.

### Faz 5'in asıl çıktısı: ne kadar veri gerekir?

Güç analizi (güç 0.80, α 0.05):

| Senaryo | Etki (d) | Gözlemsel süre | DOE ile |
|---|---|---|---|
| Gözlenen medyan etki | 0.31 | **190 saat** | **28 saat** |
| Orta etki (d = 0.5) | 0.50 | 71 saat | 11 saat |

Elimizdeki veri **3,9 saat**. Gözlemsel veri biriktirerek bu iş çözülmez —
otokorelasyon nedeniyle saatte yalnızca ~2 bağımsız gözlem üretiliyor.

**Önerilen tasarım:** 5 faktör, 2 seviye, yarım-kesir faktöriyel (16 koşul),
3 replikasyon → ~4 saat net deney süresi. Seviyeler mevcut aralığın %25 dışına
taşıyor; bu istatistiksel bir öneridir ve proses mühendisi onayı olmadan
uygulanmamalıdır.

---

## Faz 6 — Dokümantasyon + Dashboard ✅ *(tamamlandı)*
*v0: Sprint 11 + 12*

- [x] README — sonuç, metodolojik duruş, kısıtlar
- [x] Technical report → `docs/technical_report.md`
- [x] Limitations — K1–K24 + A1–A11
- [x] Reproducibility — `run_all.py`, 12 adım, ~6 dakika
- [x] Dashboard — interaktif pano (filtrelenebilir, sıralanabilir)

**Çıktı:** Technical Report ✅, Dashboard ✅, README ✅

### Dashboard

[Proses Optimizasyon Panosu](https://claude.ai/code/artifact/8a183a29-74ce-4d2d-abbf-157c08a5d22d)

Bölümler: özet şerit → çıktı performansı (filtre + sıralama + dağılım grafiği)
→ karar değişkenleri → düzeltme hunisi (437 → 148 → 81) → DOE hesabı →
bulguların güven derecesi.

Plan v0 "Power BI veya Tableau" diyordu; bunun yerine tek dosyalık, veri gömülü
bir HTML pano üretildi — kurulum gerektirmiyor, paylaşılabilir ve
`run_all.py` çıktılarından besleniyor.

---

# Repository

```text
Process_Optimization/
├── data/
│   ├── raw/                  # Kaggle orijinali — ASLA Excel'de açılmaz
│   ├── processed/
│   └── _quarantine/          # Excel'in bozduğu kopya + gerekçe
├── src/
│   ├── data_processing/      # schema.py, audit.py, verify_a1.py, clean.py
│   ├── analysis/
│   ├── modeling/
│   └── optimization/
├── tests/                    # pytest — conftest.py yolu src/ altına kurar
├── reports/                  # üretilen raporlar + figürler (script çıktısı)
├── notebooks/
├── dashboard/
├── docs/                     # assumptions.md, technical_report.md,
│                             # plan_v0_original.md (elle yazılır, silinmez)
├── run_all.py                # tüm pipeline'ı sırayla çalıştırır
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── LICENSE
└── README.md
```

---

# Başarı Kriterleri

- [ ] Ham verinin güvenilir temizlenmesi ve kısıtlarının açıkça ölçülmesi
- [ ] Ölçülebilir KPI framework (bias ve variability ayrı)
- [ ] Problemli output'ların gerekçeli tespiti
- [ ] Critical Process Parameters
- [ ] Predictive model — baseline'a göre dürüst raporlanmış
- [ ] Optimization model + duyarlılık analizi
- [ ] Validation
- [ ] Quantitative before/after karşılaştırma
- [ ] Industrial recommendations
- [ ] Dashboard + technical documentation

**Improvement yüzdesi önceden belirlenmeyecek.** Sonuç analizden çıkacak.

---

# Çalışma Prensibi

**Data → Insight → Model → Decision**

ML veya optimization sonucu beklendiği gibi çıkmazsa proje zorlanmayacak; sonuç
olduğu gibi raporlanacak. Bir kısıtı fark edip sınırını ölçmek, o kısıtı görmezden
gelip güçlü bir sonuç iddia etmekten daha değerlidir.

---

# Mevcut Durum

**Faz 1–6 tamamlandı.** 
Tek komut: `python run_all.py`.

**Altı fazın tamamı bitti.** 12 reproducible script, 9 üretilen rapor, 5 figür,
teknik rapor, interaktif pano. Tek komut: `python run_all.py` (~6 dakika).

**Projenin sonucu bir optimizasyon tablosu değil, bir teşhis.** Proses mevcut
haliyle zaten çalıştığı bölgede duruyor; iyileştirme için gereken şey daha iyi
bir model değil, daha iyi tasarlanmış bir deney. En yüksek getirili öneri de
modelden çıkmadı: 14 bias-baskın output'ta setpoint/kalibrasyon kontrolü.

Planın başında konan prensip — *"ML veya optimization sonucu beklendiği gibi
çıkmazsa proje zorlanmayacak"* — üç kez sınandı ve üçünde de sonuç olduğu gibi
raporlandı: Faz 3'te modelin açıklama gücü, Faz 4'te optimizasyon önerisinin
zayıflığı, Faz 5'te kendi önceki sonuçlarımızın walk-forward'da çökmesi.
