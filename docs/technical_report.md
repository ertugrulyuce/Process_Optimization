# Teknik Rapor
## Multistage Continuous-Flow Manufacturing Process — Proses Optimizasyon Çalışması

**Veri:** Liveline Technologies, Detroit yakınlarında bir üretim hattı, 6 Mart 2019
**Kapsam:** 14.088 gözlem × 116 değişken, 1 Hz örnekleme, 3 saat 55 dakika
**Kaynak:** [Kaggle — Multistage Continuous-Flow Manufacturing Process](https://www.kaggle.com/datasets/supergus/multistage-continuousflow-manufacturing-process)

---

## 1. Yönetici özeti

Bu çalışma, gerçek bir sürekli akış üretim prosesinden alınan veriyle uçtan uca
bir proses optimizasyonu yürütmeyi hedefledi: kontrol edilebilir parametrelerin
ürün boyutsal çıktılarının hedeflerinden sapmasına etkisini belirlemek ve
sapmayı azaltacak çalışma koşullarını ortaya çıkarmak.

**Sonuç, klasik anlamda bir optimizasyon tablosu değil, bir teşhistir.**

Veriden *"şu parametreleri şu değerlere çekin, sapma şu kadar azalır"* türü bir
öneri çıkmadı. Bunun sebebi yöntem yetersizliği değil — hem doğrusal korelasyon
hem doğrusal olmayan modeller (Random Forest, Gradient Boosting) aynı sonucu
verdi. Sebep, verinin yapısında:

- Proses 3,9 saatlik pencerede karar değişkenlerini yeterince oynatmamış.
- Bu parametrelerin otokorelasyonu 33+ dakika boyunca sönmüyor; 14.088 satır
  bu açıdan yaklaşık **7 bağımsız blok** demek.
- Optimizasyonun öğrenmesi gereken kontrast yok.

**En yüksek getirili bulgu modelden çıkmadı.** 25 kapsam içi çıktının 14'ünde
hatanın %60'tan fazlası merkezleme kaymasından geliyor — bir ayar/kalibrasyon
problemi. `Stage1.M1` hedefin %39 altında ve hatasının %98'i bias. Bu, model
gerektirmeyen, etkisi doğrudan ölçülmüş bir iyileştirme fırsatı.

Çalışmanın ikinci çıktısı, optimizasyonun önünü açacak somut bir deney
tasarımıdır: 5 faktör, 2 seviye, yarım-kesir faktöriyel (16 koşul × 3
replikasyon), ~4 saat net koşu süresi. Bu, güç karşılaştırmasından ayrı bir
sayıdır: gözlenen etki büyüklüğünde (d = 0,31) %80 güce ulaşmak gözlemsel
veriyle ~190 saat, tasarlanmış deneyle ~28 saat sürer (§7 A6).

---

## 2. Problem tanımı ve kapsam

### Proses

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

116 kolonun tamamı prosesteki rolüne göre sınıflandırıldı
(`src/data_processing/schema.py`), hiçbiri `unknown` kalmadı:

| Rol | Adet | Optimizasyondaki yeri |
|---|---|---|
| `controlled` | 24 | Karar değişkenleri |
| `measured` | 16 | Proses tepkisi — teşhis değişkeni, girdi değil |
| `ambient` + `raw_material` | 14 | Gürültü, kontrol edilemez |
| `output_actual` | 30 | Optimize edilen çıktı |
| `output_setpoint` | 30 | Sabit hedef, model girdisi değil |

Bu ayrım `.C.` / `.U.` kolon eki hipotezine dayanıyor (varsayım A1). Hipotez
dokümantasyondan doğrulanamadı; riski Faz 4'te ölçüldü (bkz. §5, K19).

### Kapsam dışı bırakılanlar

30 çıktının 5'i analiz dışında:

| Çıktı | Gerekçe |
|---|---|
| `Stage1.M5`, `Stage1.M7`, `Stage1.M11`, `Stage2.M4` | Geçerli veri < %50 |
| `Stage2.M6` | Setpoint (0,01) ölçüm gürültüsünün altında — oransal KPI tanımsız |

---

## 3. Veri kalitesi

### Ham veri bir kez bozuldu

Projenin ilk bulgusu veriyle ilgiliydi: elde bulunan CSV, Excel'de Türkçe
locale ile açılıp kaydedilmişti ve ondalıklı sayılar tarihe dönüşmüştü
(`11.54` → `Kas.54`). **556.563 hücre (%34,4) bozuktu**, 115 sayısal kolonun
94'ü etkilenmişti.

Geri çevirme denenmedi çünkü kayıplıdır: `13.5` ve `13.05` ikisi de `13.May`
olarak yazılmış, geri dönüştürüldüğünde ayırt edilemez. Ham dosya Kaggle'dan
yeniden indirildi; bozuk kopya `data/_quarantine/` altında gerekçesiyle
saklanıyor.

### Temizlik kuralları

Sekiz numaralı kural uygulandı; her biri bir denetim bulgusuna dayanıyor:

| # | Kural | Etki |
|---|---|---|
| R1 | Çıktı ölçümlerindeki tam sıfır → NaN | 78.539 hücre |
| R2 | Negatif ölçümler → NaN | 126 hücre |
| R3 | Birebir özdeş kolon düşürüldü | 1 kolon |
| R4 | Duplicate timestamp işaretlendi | 27 satır |
| R5 | Duruş bloğu işaretlendi | 56 satır |
| R6 | Geçerli veri < %50 olan çıktılar kapsam dışı | 4 çıktı |
| R7 | Setpoint < sapma std'si olanlar kapsam dışı | 1 çıktı |
| R8 | Setpoint'in %1'inden küçük değerler → NaN | 82 hücre |

Çıktı ölçüm hücrelerinin **%18,6'sı** geçersizdi. **Hiçbir satır silinmedi** —
sıfırlar her çıktıda farklı satırlarda olduğu için satır silmek, bir sensörün
dropout'u yüzünden diğer 24 çıktının geçerli ölçümünü de atmak olurdu.

**R8 nasıl bulundu:** Bir control chart'ta y ekseninin beklenmedik davranışını
kovalarken `Stage1.M1`'in minimumunun `4.4e-151` olduğu görüldü. R1'in `== 0`
testi bu float-underflow değerlerini kaçırıyordu; 26 çıktıda 185 hücre vardı.
Bunların 103'ü negatif olduğu için R2'de sayılıyor, tabloda R8'e 82 kalıyor.

---

## 4. Metodoloji

### Kırmızı çizgi: zaman-sıralı bölme

Karar değişkenlerinde lag-1 otokorelasyon 0,93–0,99. Rastgele train/test split
kullanılırsa test satırının komşuları train'de kalır ve model tahmin değil
**hatırlama** yapar.

Aynı model, aynı veri (`Stage1.M4.dev`), yalnızca bölme yöntemi değişiyor:

| Bölme yöntemi | R² |
|---|---|
| Rastgele split | **0,97** |
| Bloklu split, embargo yok | −6,28 |
| Bloklu split + embargo (49) | **−6,89** |
| *baseline:* persistence | 0,85 |

Embargo, karar değişkenlerinin otokorelasyonunun 0,2 altına indiği mesafenin
medyanı olarak seçildi — keyfi değil, veriden.

### Baseline'a göre raporlama

Ham R² bu veride yanıltıcı. "Önceki değeri tekrarla" (persistence) tahmini
hiçbir şey öğrenmeden R² = 0,85 alıyor. Bu yüzden her model iki baseline ile
karşılaştırıldı ve **beceri skoru** raporlandı:

```
skill = 1 − RMSE_model / RMSE_baseline     (0 = baseline kadar, < 0 = daha kötü)
```

### İki ayrı soru

| Soru | Girdi | Ne için |
|---|---|---|
| **S1** Karar değişkenleri sapmayı *açıklıyor* mu? | sadece `controlled` | Optimizasyonun dayanağı |
| **S2** Sapma *tahmin edilebilir* mi? | + geçmiş değerler | Erken uyarı / izleme |

Bu ayrım şart: geçmiş değerlerle yüksek R² elde edip "prosesi anladık" sanmak bu
veri setindeki en kolay tuzak. S2'nin başarısı S1'in yerine geçmez.

### İstatistiksel düzeltmeler

Korelasyon analizinde iki düzeltme birlikte uygulandı:

1. **Otokorelasyon** — Bartlett'in tam formülü:
   `n_eff = n / (1 + 2·Σₖ (1−k/n)·ρₓ(k)·ρᵧ(k))`
   Yalnızca lag-1 kullanan basit sürüm AR(1) varsayar ve bu veride
   otokorelasyonu ciddi biçimde eksik düzeltiyordu (medyan `n_eff` 1.744 yerine
   465).
2. **Çoklu karşılaştırma** — Benjamini-Hochberg FDR. 600 çift test edildiği için
   şans eseri ~30 tanesi "anlamlı" çıkardı.

---

## 5. Bulgular

Bulgular güven derecesine göre sıralandı. **Yüksek güvenli bulguların hiçbiri
proses parametresiyle ilgili değil** — veri kalitesi ve ölçüm sistemiyle ilgili.

### Yüksek güven

**B1 — İki kolon birebir özdeş.** `Machine4.Temperature4` ile
`Machine4.Pressure` 14.088 satırın tamamında aynı. Aralık kanıtı hangisinin
hatalı olduğunu söylüyor: Temperature4 `14–25`, diğer dört Machine 4 sıcaklığı
`260–396`, Pressure `14–25`. Yanlış adlandırılmış basınç kopyası.

**B2 — Ölçüm sisteminin %18,6'sı geçersiz veri üretiyor.** Sıfırlar tek bir
duruş bloğunda değil, yüzlerce kısa kesinti hâlinde (`Stage1.M14` → 673 ayrı
kesinti). Bu bir üretim duruşu deseni değil, ölçüm güvenilirliği sorunudur.

**B3 — Hata iki farklı tipte.** 25 kapsam içi çıktının 14'ü bias-baskın
(>%60 bias payı), 9'u variability-baskın (<%40), 2'si belirsiz bantta.

**B4 — Rastgele split %97'lik sahte başarı üretiyor.** (§4)

**B5 — Karar değişkenleri sapmayı açıklamıyor.** Doğrusal korelasyonda
`|r| > 0,3` olan, düzeltme sonrası anlamlı ilişki sayısı 3. Doğrusal olmayan
modellerde de hiçbir çıktıda R² pozitif değil.

600 çiftin düzeltme sonrası durumu:

| Ölçüt | Anlamlı | Oran |
|---|---|---|
| Ham `n = 14.088` | 434 | %72 |
| + Otokorelasyon (`n_eff`) | 159 | %27 |
| + Çoklu karşılaştırma (FDR) | **81** | **%14** |

### Orta güven

**B6 — Stage 1 → Stage 2 transport delay ~270 sn.** 150 güvenilir çiftin
yalnızca %5'i lag = 0'da tepe yapıyor. İlk tarama 0–300 sn'ydi ve tepeler üst
sınıra yapışıktı; aralık 900 sn'ye açıldığında tepe yerinde kaldı — sınır
artifaktı değil. Ancak dağılım tek tepeli değil (250–300'de 40 çift, 500–550'de
15), bu da birden fazla malzeme yolu olabileceğini düşündürüyor.

### Düşük güven

**B7 — `Machine4.Pressure` 14–17 aralığı daha iyi.** 5 çıktının 5'i de bu
dilimi en iyi buluyor. Ancak: dilim gözlemlerin %65'ini içeriyor (yani proses
zaten orada çalışıyor), etki büyüklükleri %1,7–25,8 arası küçük, ve zaman
parçalarının yalnızca **%57'sinde** tutuyor.

### Çok düşük güven

**B8 — 5 çıktıda model persistence'ı geçiyor.** Bu sonuç tek bir bölmeye
dayanıyordu. Walk-forward validation'da (5 pencere) **hiçbir çıktı tüm
fold'larda pozitif kalmıyor**: `Stage2.M10` 0/4, `Stage2.M9` 1/3.

---

## 6. Neden optimize edilemedi

**Karar değişkenlerinin otokorelasyonu sönmüyor.** 5 aktif parametrenin 4'ünde
sönümlenme mesafesi 2000 gecikmeye (tarama sınırı) dayandı — yani ölçülen değil,
aramanın durduğu yer. Pratik sonuç: veri bu parametreler açısından ~7 bağımsız
blok.

**Karar uzayı dar.** 24 karar değişkeninin 13'ünün varyasyon katsayısı %0,5'in
altında. Machine 5'in sıcaklıkları pratikte sabit (CV %0,01). Gerçek karar uzayı
5 parametre.

**Proses merkezi gürültüden hızlı kayıyor.** 5 çıktının 3'ünde pencereler arası
kayma, serinin kendi standart sapmasından büyük (`Stage2.M9`: 2,29σ). Sabit bir
setpoint önerisi kısa ömürlüdür.

---

## 7. Öneriler

### A1 — Bias-baskın çıktılarda setpoint/kalibrasyon kontrolü

**En yüksek getirili öneri, modelden çıkmadı.**

| Çıktı | Hedef | Sapma | Bias payı |
|---|---|---|---|
| `Stage1.M1` | 22,74 | −8,87 (%−39,0) | %98,1 |
| `Stage2.M1` | 11,71 | −5,13 (%−43,8) | %97,7 |
| `Stage2.M14` | 11,71 | −3,67 (%−31,4) | %96,9 |

Proses bu çıktılarda kararlı ama yanlış noktada. Dağılım dar; sorun yayılım
değil merkez. Proses parametresi oynatarak düzeltilecek bir şey değil.

**Risk:** Hedef değerlerin neden o şekilde belirlendiği bilinmiyor; %40'lık
sapma kasıtlı bir üretim tercihi de olabilir. Önce proses sahibine sorulmalı.

### A2 — Sensör dropout'u giderilsin

4 çıktı (`Stage1.M5/M7/M11`, `Stage2.M4`) yetersiz veri nedeniyle analiz dışı
kaldı. Bu sensörlerin bakımı olmadan o ölçümler hakkında hiçbir şey
söylenemez. Ayrıca `1e-306` mertebesindeki underflow değerleri veri toplama
zincirinde bir sayısal hataya işaret ediyor.

### A3 — Özdeş kolon çifti düzeltilsin

Historian tag eşleme tablosu kontrol edilsin. Düzeltilmezse bu çift her modelde
yapay multicollinearity ve şişirilmiş feature importance üretir.

### A4 — Sabit setpoint yerine periyodik yeniden merkezleme

Proses merkezi gürültüden hızlı kaydığı için "şu değere ayarlayın" türü sabit
öneriler kısa ömürlü. **Risk:** aşırı düzeltme (over-control) — yeniden
merkezleme eşiği istatistiksel olarak tanımlanmalı.

### A5 — Kontrol grafiği seçimi değişsin

Klasik I-MR grafiği bu proses için uygun değil: otokorelasyon nedeniyle medyan
out-of-control oranı **%38,5** çıkıyor (kararlı bir proseste ~%0,3 beklenir).
Yanlış alarm operatörü grafiğe güvenmemeye iter. Yerine EWMA/CUSUM, ya da bir
zaman serisi modeli kurup artıklar üzerinde kontrol grafiği.

### A6 — Tasarlanmış deney (DOE)

Güç analizi (güç 0,80, α 0,05):

| Senaryo | Etki (d) | Gözlemsel | DOE ile |
|---|---|---|---|
| Gözlenen medyan etki | 0,31 | **190 saat** | **28 saat** |
| Orta etki hedeflenirse | 0,50 | 71 saat | 11 saat |

Elimizdeki veri 3,9 saat. Gözlemsel veri biriktirerek bu iş çözülmez —
otokorelasyon nedeniyle saatte ~2 bağımsız gözlem üretiliyor. Parametre bilinçli
değiştirildiğinde otokorelasyon kırılır ve her koşu bağımsız bir gözlem olur.

**Önerilen tasarım:** 5 faktör, 2 seviye, yarım-kesir faktöriyel (16 koşul),
3 replikasyon, koşu başına ~5 dakika ≈ **4 saat net deney**.

Seviyeler mevcut aralığın %25 dışına taşıyor (etki büyüklüğü aralıkla birlikte
büyür, ve mevcut aralıkta kontrast yok). **Bu istatistiksel bir öneridir;
proses güvenliği ve ürün kalitesi açısından proses mühendisi onayı olmadan
uygulanmamalıdır.**

---

## 8. Limitler

| Limit | Etkisi |
|---|---|
| Veri tek bir 3,9 saatlik pencereden | Long-term capability, vardiya ve mevsim etkisi analiz edilemez |
| Gözlemsel veri, deney değil | Hiçbir bulgu nedensellik iddia edemez |
| Spesifikasyon limitleri yok | Cp/Cpk mutlak yorumlanamaz, yalnızca çıktılar arası sıralama |
| `.C.`/`.U.` anlamı doğrulanamadı (A1) | Karar değişkeni seti varsayıma dayalı; riski ölçüldü, kapatılmadı |
| Karar değişkenleri dar aralıkta | Optimizasyonun öğreneceği kontrast yok |
| Transport delay tek tepeli değil | Stage 1 – Stage 2 eşleşmesi yaklaşık |
| Ambient ~350 sn'de bir güncelleniyor | Çevre koşullarının etkisi araştırılamaz (~40 bağımsız gözlem) |

### A1 riski nasıl ölçüldü

`measured` değişkenleri eklemek **5/5 çıktıda modeli kötüleştiriyor**. A1 yanlış
olsaydı — yani `.U.` kolonlar da ayarlanabilir olsaydı — onları eklemek tahmin
gücünü artırmalıydı. Bu A1'i kanıtlamaz, ama karar değişkenlerini `.C.` ile
sınırlamayı veriye dayalı olarak savunulabilir kılar.

---

## 9. Tekrar üretilebilirlik

```bash
pip install -r requirements.txt
# Ham CSV'yi Kaggle'dan indirip data/raw/ altına koyun
python run_all.py        # 12 adım, ~6 dakika
```

Tüm raporlar ve figürler script çıktısıdır; hiçbiri elle düzenlenmez.
`reports/` silinebilir ve yeniden üretilir. Elle yazılan dokümanlar `docs/`
altındadır ve pipeline temizliğinden etkilenmez.

> **Ham CSV Excel'de açılmamalıdır.** Türkçe/Avrupa locale'de Excel ondalıklı
> sayıları tarihe çevirir ve bu geri alınamaz.

---

## 10. Gelecek çalışma

1. **DOE uygulanması** (§7 A6) — optimizasyonun önünü açacak tek şey.
2. **Residual chart** — Faz 3'te model kurulduktan sonra artıklar üzerinde
   kontrol grafiği, otokorelasyon sorununu aşar.
3. **Stage 1 → Stage 2 gecikmesinin fiziksel doğrulanması** — dağılımın tek
   tepeli olmaması birden fazla malzeme yolu olabileceğini düşündürüyor.
4. **Uzun süreli veri** — long-term capability ve vardiya etkisi için.
5. **A1'in kesin doğrulanması** — veri sahibinden kolon adlandırma konvansiyonu.

---

## Ek: Kısıt kayıtları

Proje boyunca ölçülen ve kapsamı belirleyen kısıtlar K1–K24 olarak numaralandı;
tam liste `continuous_manufacturing_process_optimization_plan.md` içinde.
Varsayımlar A1–A11 olarak `docs/assumptions.md` içinde, her biri yanlış çıkması
hâlinde neyi geçersiz kılacağıyla birlikte kayıtlı.
