# Faz 5 - Endustriyel Yorum ve Veri Toplama Onerisi

Uretildi: `python src/analysis/recommendations.py`

Faz 4 bu veriden guclu bir optimizasyon onerisi cikmadigini gosterdi;
Faz 5 validation (V1) bunu daha da zayiflatti. Bu rapor o olumsuz sonucu
**uygulanabilir bir oneriye** cevirir.

## 1. Bulgularin guven derecesi

Her bulgu, hangi kanita dayandigi ve validation'dan nasil ciktigina gore
derecelendirildi. **Yuksek guvenli bulgular proses parametresi degil,
veri kalitesi ve olcum sistemiyle ilgili olanlar.**

| # | Bulgu | Guven | Neden |
|---|---|---|---|
| 1 | `Machine4.Temperature4` = `Machine4.Pressure` (ozdes kolon) | **yuksek** | 14.088 satirin tamaminda birebir; yorum gerektirmiyor |
| 2 | Output'larin %19'u sensor dropout (sifir/underflow) | **yuksek** | dogrudan sayim, model yok |
| 3 | 14 output bias-baskin, 9 variability-baskin | **yuksek** | dogrudan hesap; bias/variability ayrisimi kararli |
| 4 | Rastgele split R2 0.97 -> dogru split -6.89 | **yuksek** | tekrarlanabilir, yontemsel |
| 5 | Karar degiskenleri deviation'i aciklamiyor | **yuksek** | hem dogrusal hem dogrusal olmayan modellerde |
| 6 | Stage1 -> Stage2 gecikme ~270 sn | **orta** | 148 ciftte tepe; dagilim tek tepeli degil |
| 7 | `Machine4.Pressure` 14-17 daha iyi | **dusuk** | V2: zaman parcalarinin %57'sinde tutuyor |
| 8 | 5 output'ta model persistence'i geciyor | **cok dusuk** | V1: walk-forward'da hicbiri tum fold'larda pozitif degil |

> **Bu tablo projenin en durust ciktisi.** Bir bulguyu "guclu" diye
> sunmak kolay; hangi bulgunun ne kadar tasidigini soylemek zor.
> Uygulama kararlari 1-5 arasindaki bulgulara dayandirilmali;
> 7 ve 8 numarali bulgular **aksiyon dayanagi degildir.**

## 2. Onerilen aksiyonlar

Format: Bulgu -> Muhendislik yorumu -> Aksiyon -> Beklenen etki -> Risk

### A1 — Bias-baskin output'larda setpoint/kalibrasyon gozden gecirilsin

**Bulgu:** 25 kapsam ici output'un 14'unde hatanin %60'tan fazlasi
merkezleme kaymasindan geliyor. En uclar:

- `Stage1.M6`: hedef 4.25, gerceklesen sapma -2.239 (**%-52.7**)
- `Stage2.M1`: hedef 11.71, gerceklesen sapma -5.131 (**%-43.8**)
- `Stage1.M1`: hedef 22.74, gerceklesen sapma -8.870 (**%-39.0**)

**Muhendislik yorumu:** Proses bu output'larda *kararli* ama *yanlis
noktada* calisiyor. Dagilim dar; sorun yayilim degil merkez. Bu, proses
parametresi oynatarak duzeltilecek bir sey degil -- ya setpoint yanlis
girilmis, ya olcum sistemi kaymis (kalibrasyon), ya da hedef degeri
gercekci degil.

**Aksiyon:** Bu 14 output icin setpoint kaydi ve olcum cihazi
kalibrasyonu kontrol edilsin. Once `Stage1.M1` ve `Stage2.M1` -- ikisi de
hedefin ~%40 altinda ve hatalarinin %98'i bias.

**Beklenen etki:** Kalibrasyon kaymasiysa dogrudan ve buyuk; ayar
hatasiysa aninda. **Bu, projenin en yuksek getirili onerisidir** cunku
model gerektirmiyor ve etki buyuklugu dogrudan olculmus.

**Risk:** Dusuk. Ancak hedef degerlerin neden o sekilde belirlendigi
bilinmiyor; %40'lik sapma kasitli bir uretim tercihi de olabilir. Once
proses sahibine sorulmali.

### A2 — Sensor dropout'u giderilsin

**Bulgu:** Output olcum hucrelerinin **%18.6**'si gecersiz:
tam sifirlar, float-underflow degerleri ve negatifler (kural bazinda dokum:
`02_cleaning_report.md`).
`Stage1.M5` gecerli verisinin yalnizca %4.6'sina sahip.

**Muhendislik yorumu:** Sifirlar tek bir durus blogunda degil, yuzlerce
kisa kesinti halinde (`Stage1.M14` -> 673 ayri kesinti). Bu bir uretim
durusu deseni degil, **olcum sistemi guvenilirligi** sorunudur.
Underflow degerleri ise veri toplama zincirinde bir sayisal hataya
isaret ediyor -- gercek bir olcum `1e-306` olamaz.

**Aksiyon:** 4 output (`Stage1.M5/M7/M11`, `Stage2.M4`) analiz disi
kaldi. Bu sensorlerin bakimi/degisimi olmadan o olcumler hakkinda hicbir
sey soylenemez. Underflow icin veri toplama yazilimi incelensin.

**Beklenen etki:** Analiz kapsamini 25'ten 29 output'a cikarir.

**Risk:** Yok. Veri kalitesi duzeltmesi.

### A3 — Ozdes kolon cifti duzeltilsin

**Bulgu:** `Machine4.Temperature4` ile `Machine4.Pressure` 14.088 satirin
tamaminda birebir ayni. Deger araligi (14-25) diger Machine 4
sicakliklariyla (260-396) uyumsuz, basincla uyumlu.

**Muhendislik yorumu:** Bir etiketleme/kopyalama hatasi. Ya iki tag ayni
kaynagi okuyor ya da biri yanlis adlandirilmis.

**Aksiyon:** Historian tag esleme tablosu kontrol edilsin.

**Risk:** Yok — ama **duzeltilmezse** bu cift her modelde yapay
multicollinearity ve sisirilmis feature importance uretir.

### A4 — Sabit setpoint yerine periyodik yeniden kalibrasyon

**Bulgu (V3):** 5 output'un 3'unde, 4 saatlik pencere icindeki pencere
ortalamalari arasi kayma, serinin kendi standart sapmasindan **buyuk**
(`Stage2.M9`: 2.29 sigma).

**Muhendislik yorumu:** Proses merkezi gurultuden daha hizli kayiyor.
Bir donemde dogru olan ayar, saatler sonra merkezi kaymis olur.

**Aksiyon:** "Su degere ayarlayin" turu sabit oneriler yerine
**periyodik yeniden merkezleme** (ornegin vardiya basi) prosedurü.

**Risk:** Asiri duzeltme (over-control). Kayma olcum gurultusuyle
karistirilirsa proses daha da kararsizlasir. Yeniden merkezleme esigi
istatistiksel olarak tanimlanmali.

## 3. Optimizasyonun onunu ne acar?

Bu bolum projenin en pratik ciktisidir: **veri neden yetmedi ve ne kadar
gerekir?**

Aktif CPP'lerin otokorelasyonu ~2000 satir (≈33 dakika) boyunca sonmuyor (V0). Yani 14.088 satirlik
veri, bu parametreler acisindan yaklasik **7 bagimsiz
blok** demek. Optimizasyonun ogrenmesi gereken kontrast burada ve orada
bir avuc gozlem var.

### Gozlenen etki buyuklukleri

Her CPP icin, en iyi ve en kotu dilim arasindaki farkin serinin
standart sapmasina orani (Cohen'in d'si):

| parametre | medyan d | en buyuk d | yorum |
|---|---|---|---|
| `Machine1.ExitZoneTemperature` | 0.342 | 1.056 | buyuk |
| `Machine1.MotorRPM` | 0.332 | 1.041 | buyuk |
| `Machine3.MotorRPM` | 0.314 | 0.947 | buyuk |
| `Machine4.Temperature3` | 0.205 | 0.932 | buyuk |
| `Machine4.Pressure` | 0.074 | 0.439 | kucuk |

> Etkiler **kucuk**. Kucuk etkiyi saptamak icin cok sayida bagimsiz
> gozlem gerekir; elde ~7 tane var.

### Ne kadar veri gerekir?

Guc analizi (guc 0.80, alfa 0.05, iki seviye karsilastirmasi):

| senaryo | etki (d) | gereken bagimsiz gozlem | gozlemsel sure | DOE ile |
|---|---|---|---|---|
| gozlenen medyan etki | 0.3062 | 342 | **190 saat** | **28 saat** |
| gozlenen en buyuk etki | 1.056 | 29 | **16 saat** | **2 saat** |
| orta etki (d=0.5) hedeflenirse | 0.5 | 128 | **71 saat** | **11 saat** |

> **BULGU N1 - Gozlemsel veri bekleyerek bu is cozulmez.** Prosesi
> kendi haline birakip veri biriktirmek, otokorelasyon nedeniyle
> saatte yalnizca ~2 bagimsiz gozlem uretiyor.
>
> **DOE ayni bilgiyi mertebe kucuk surede verir.** Fark yontemden
> geliyor: parametre bilincli olarak degistirildiginde otokorelasyon
> kirilir ve her run bagimsiz bir gozlem olur. Ayrica DOE'de
> parametreler **gozlenen dar araligin disina** cikarilabilir --
> etki buyuklugu de artar.

### Onerilen deney tasarimi

**5 faktor, 2 seviye, yarim-kesir faktoriyel (2^5⁻¹ = 16 kosul)**

| faktor | mevcut aralik | onerilen dusuk | onerilen yuksek |
|---|---|---|---|
| `Machine1.MotorRPM` | 10.39 – 12.24 | 9.93 | 12.70 |
| `Machine1.ExitZoneTemperature` | 69.70 – 80.00 | 67.12 | 82.58 |
| `Machine3.MotorRPM` | 11.96 – 14.00 | 11.45 | 14.51 |
| `Machine4.Pressure` | 14.00 – 25.00 | 11.25 | 27.75 |
| `Machine4.Temperature3` | 268.00 – 327.00 | 253.25 | 341.75 |

> Onerilen seviyeler mevcut araligin **%25 disina** tasiyor. Bunun iki
> nedeni var: (1) etki buyuklugu aralikla birlikte buyur, (2) mevcut
> aralik zaten prosesin rahat oldugu bolge -- kontrast orada yok.
>
> **Bu seviyeler proses guvenligi ve urun kalitesi acisindan proses
> muhendisi tarafindan onaylanmadan uygulanmamalidir.** Buradaki
> oneri istatistikseldir, fiziksel fizibilite degerlendirmesi degildir.

Her kosu ~5 dakika (K13: transport delay ~270 sn + dengelenme payi),
16 kosul x 3 replikasyon = **48 kosu ≈ 4 saat**
net deney suresi.

## 4. Izleme onerileri

**Control chart secimi:** Klasik I-MR grafigi bu proses icin **uygun
degil** (K10) -- otokorelasyon nedeniyle medyan out-of-control orani
%41.8 cikiyor, kararli bir proseste ~%0.3 beklenir. Yanlis alarm
operatoru grafige guvenmemeye iter.

Yerine: **EWMA veya CUSUM**, ya da once bir zaman serisi modeli kurup
**artiklar uzerinde** kontrol grafigi.

**Erken uyari:** S2 sonucu (Faz 3) burada degerli -- deviation kisa
vadede gecmis degerlerinden tahmin edilebiliyor. Bu, optimizasyon icin
kullanilamaz ama **bir sonraki periyodu ongoren erken uyari** icin
kullanilabilir.

**Veri toplama:** Ambient kosullari ~350 sn'de bir guncelleniyor (K4);
4 saatte ~40 bagimsiz gozlem. Bu degiskenlerin etkisi arastirilacaksa
ornekleme sikligi artirilmali veya cok daha uzun sureli veri toplanmali.

## 5. Limitler

| Limit | Etkisi |
|---|---|
| Veri tek bir 3,9 saatlik pencereden | Long-term capability, vardiya ve mevsim etkisi analiz edilemez |
| Gozlemsel veri, deney degil | Hicbir bulgu nedensellik iddia edemez |
| Spec limitleri yok | Cp/Cpk mutlak yorumlanamaz, yalnizca siralama |
| `.C.`/`.U.` anlami dogrulanamadi (A1) | Karar degiskeni seti varsayima dayali; riski olculdu (K19), kapatilmadi |
| Karar degiskenleri dar aralikta | Optimizasyonun ogrenecegi kontrast yok |
| Transport delay tek tepeli degil | Stage1-Stage2 eslesmesi yaklasik |

> **Projenin sonucu bir optimizasyon tablosu degil, bir teshis.** Proses
> mevcut haliyle zaten calistigi bolgede duruyor; iyilestirme icin gereken
> sey daha iyi bir model degil, **daha iyi tasarlanmis bir deney.**
