# Faz 5 - Validation ve Dayaniklilik

Kaynak: `data/processed/clean_v1.csv`  
Uretildi: `python src/analysis/validation.py`

Faz 3 ve 4'un butun sonuclari **tek bir bolmeye** dayaniyordu (son %30).
O donem atipikse tum sonuclar yaniltici olur. Burada ayni sorular zaman
ekseni boyunca ilerleyen **5 ayri pencerede** tekrar soruluyor.

## V0 - Embargo hesabi beklenmedik bir sey gosterdi

Embargo, karar degiskenlerinin otokorelasyonunun 0.2 altina indigi
mesafeye gore secilir. Aktif CPP'ler icin bu deger **2000 satir**
cikti. Faz 3'te 24 `controlled` kolonun medyani 49 satirdi.

| parametre | sonumlenme lag'i | durum |
|---|---|---|
| `Machine1.MotorRPM` | 2000 | **SANSURLU** — tarama siniri |
| `Machine1.ExitZoneTemperature` | 2000 | **SANSURLU** — tarama siniri |
| `Machine3.MotorRPM` | 2000 | **SANSURLU** — tarama siniri |
| `Machine4.Pressure` | 1730 | olculdu |
| `Machine4.Temperature3` | 2000 | **SANSURLU** — tarama siniri |

> **BULGU V0 - 4 / 5 aktif CPP'nin otokorelasyonu
> tarama siniri icinde hic sonmuyor.** Donen sayi bir olcum degil,
> aramanin durdugu yer; gercek sonumlenme daha uzakta.
>
> Bunun anlami K5'in sanilandan agir olmasi: karar degiskenleri **33+
> dakika** boyunca otokorelasyonlu. 14.088 satirlik veri, bu parametreler
> acisindan yaklasik **7 bagimsiz blok**
> demek -- 14.088 degil.
>
> Faz 2'de olculen medyan `n_eff` = 442 bu tabloyla birlikte okunmali:
> o deger output serilerini de iceriyordu. **Optimizasyonun ogrenmesi
> gereken sey karar degiskenlerinin etkisi ve orada elde bir avuc
> bagimsiz gozlem var.** Faz 4'un zayif sonucu buradan geliyor.

## V1 - Model becerisi fold'lar arasinda tutarli mi?

**Once bir adalet duzeltmesi.** Walk-forward'da train seti ileriye
dogru buyuyor; ilk fold yalnizca **1,292 satirla** egitiliyor, tek split ise 6,865-9,569 satirla.
Fold 1'i digerleriyle ayni kefeye koymak modeli haksiz yere kotu
gosterir. Asagida ayri tutuldu.

| fold | train | test |
|---|---|---|
| 1 | 1,292 | 1,646 |
| 2 | 2,938 | 1,646 |
| 3 | 4,584 | 1,646 |
| 4 | 6,230 | 1,646 |
| 5 | 8,715 | 2,143 |

`tek_split` = Faz 3/4'te kullanilan tek bolmenin sonucu.  
`fold 1` ayri sutunda: yetersiz train, yorum disi.

| output | tek_split | fold 1 (yetersiz) | fold 2-5 medyani | en dusuk | en yuksek | pozitif |
|---|---|---|---|---|---|---|
| Stage2.M0 | +0.2253 | -10.2412 | +0.1167 | -0.1377 | +0.1665 | 3/4 |
| Stage2.M10 | +0.1004 | -6.8412 | -0.1936 | -0.7328 | -0.0846 | 0/4 |
| Stage2.M7 | +0.1650 | -3.7905 | +0.1803 | -0.0257 | +0.2250 | 3/4 |
| Stage2.M8 | +0.1108 | -0.6119 | +0.0632 | -0.1126 | +0.1644 | 2/4 |
| Stage2.M9 | +0.2553 | -2.3653 | -0.6681 | -0.8066 | +0.2595 | 1/3 |

> **BULGU V1 - Tek split sonuclari kirilgan.** Fold 1 disarida
> birakildiginda bile, 5 output'un yalnizca **0**'i
> her fold'da pozitif kaliyor.
>
> Su output'lar fold'larin yarisinda veya daha azinda pozitif --
> tek split sonucu bunlar icin **gecersiz sayilmali**:
>   - `Stage2.M10`: 0/4 fold, medyan -0.1936 (tek split +0.1004)
>   - `Stage2.M8`: 2/4 fold, medyan +0.0632 (tek split +0.1108)
>   - `Stage2.M9`: 1/3 fold, medyan -0.6681 (tek split +0.2553)
>
> **Bu, Faz 3 ve 4'un sonuclarini dogrudan etkiliyor.** "5 output'ta
> persistence gecildi" ifadesi tek bolmeye dayaniyordu; walk-forward
> bu ifadeyi desteklemiyor. Faz 4'un optimizasyon onerileri de ayni
> zemine dayandigi icin **guven derecesi dusurulmelidir.**

## V2 - Ampirik optimizasyon bulgusu zamanda tutuyor mu?

Faz 4'un tek tutarli bulgusu: `Machine4.Pressure` en dusuk
dilimi (14-17) butun output'larda en iyiydi. Bu bulgu tek bir donemin
artifakti mi, yoksa veri boyunca tutuyor mu?

| output | 1/4 | 2/4 | 3/4 | 4/4 | tutma orani |
|---|---|---|---|---|---|
| Stage2.M0 | nan | EVET | EVET | hayir | **2/3** |
| Stage2.M10 | EVET | EVET | EVET | hayir | **3/4** |
| Stage2.M7 | EVET | EVET | EVET | hayir | **3/4** |
| Stage2.M8 | nan | EVET | hayir | hayir | **1/3** |
| Stage2.M9 | EVET | hayir | hayir | nan | **1/3** |

> **BULGU V2 - Bulgu zaman parcalarinin ortalama %57'inde tutuyor.**
> Bulgu kismen tutuyor. Bazi donemlerde tersine donuyor, yani
> **kosula bagli**: parametrenin etkisi diger kosullara gore
> degisiyor olabilir. K18 zayiflar.

## V3 - Dagilim kaymasi ne kadar buyuk?

K16'da fark edilen kayma burada olculuyor: veri 8 ardisik pencereye
bolunup her birinde deviation ortalamasi hesaplandi. `kayma_sigma`,
pencereler arasi farkin serinin kendi standart sapmasina orani.

| output | en dusuk pencere | en yuksek pencere | kayma | kayma / sigma |
|---|---|---|---|---|
| Stage2.M9 | -0.1246 | 0.4383 | 0.5629 | **2.29** |
| Stage2.M0 | 0.4583 | 0.9003 | 0.4419 | **1.75** |
| Stage2.M10 | -0.1096 | 0.0166 | 0.1262 | **1.02** |
| Stage2.M8 | 0.1278 | 0.4809 | 0.353 | **0.91** |
| Stage2.M7 | 0.1208 | 0.2951 | 0.1743 | **0.75** |

> **BULGU V3 - 3 / 5 output'ta pencereler arasi kayma,
> serinin kendi standart sapmasindan buyuk.** Yani prosesin ortalamasi,
> 4 saatlik pencere icinde bile gurultuden daha fazla oynuyor.
>
> Pratik sonucu: **sabit bir setpoint onerisi kisa omurludur.** Bir
> donemde dogru olan ayar, saatler sonra merkezi kaymis olabilir.
> Endustriyel oneri bu yuzden "su degere ayarlayin" degil,
> **"duzenli yeniden kalibrasyon"** yonunde olmalidir.
