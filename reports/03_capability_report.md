# Faz 2 - Proses Kararliligi ve Short-Term Capability

Kaynak: `data/processed/clean_v1.csv`  
Uretildi: `python src/analysis/capability.py`

Kapsam: 25 output (Faz 1'de kapsam ici sayilanlar).

## Onemli uyari - kontrol grafiklerinin gecerliligi

I-MR kontrol grafigi **ardisik gozlemlerin bagimsiz oldugunu varsayar.**
Bu 25 output'ta lag-1 otokorelasyonu medyan **0.89** (aralik 0.37-0.99; K5). Otokorelasyonlu bir seride:

- Ardisik farklar kucuk oldugu icin `MR_bar` kucuk cikar,
- dolayisiyla `sigma_st` oldugundan kucuk tahmin edilir,
- kontrol limitleri gercekte olmasi gerekenden **dar** olur,
- ve seri, gercekte kararli olsa bile surekli limit disina tasar.

> **BULGU C1 - Out-of-control oranlari yontem artifaktidir.** Medyan
> out-of-control orani **%41.8**. Gercek bir prosesde bu oran
> %0.3 civarinda olmali. Bu fark prosesin kontrolsuz oldugunu degil,
> **I-MR grafiginin bu veri icin uygun arac olmadigini** gosterir.
> Asagidaki `ooc` sutunlari bu nedenle proses hukmu olarak kullanilmaz.

> *Dogru yaklasim:* otokorelasyonlu proses icin EWMA / CUSUM grafigi veya
> once bir zaman serisi modeli kurup **artiklar** uzerinde kontrol grafigi
> (residual chart). Bu, Faz 3'te model kurulduktan sonra yapilabilir hale
> gelecek; simdilik kararlilik hukmu askiya alinir.

## Short-term vs long-term yayilim

`lt_st_ratio` = sigma_lt / sigma_st. 1'e yakinsa seri kararli; buyukse
seride kayma/surukleme var demektir. **Ancak** otokorelasyon `sigma_st`'yi
kucuk gosterdigi icin bu oran yukari saplidir; siralama icin kullanilabilir,
mutlak deger olarak degil.

| output | hata tipi | sigma_st | sigma_lt | lt/st |
|---|---|---|---|---|
| `Stage1.M1` | bias | 0.035 | 1.1808 | **33.7756** |
| `Stage1.M4` | variability | 0.0401 | 1.1119 | **27.7123** |
| `Stage1.M13` | variability | 0.036 | 0.8328 | **23.1238** |
| `Stage1.M0` | bias | 0.0121 | 0.2058 | **17.0145** |
| `Stage1.M2` | bias | 0.0391 | 0.5552 | **14.1825** |
| `Stage1.M8` | bias | 0.0147 | 0.201 | **13.7029** |
| `Stage1.M3` | bias | 0.0218 | 0.2322 | **10.6416** |
| `Stage1.M6` | bias | 0.0809 | 0.7636 | **9.4435** |

> **BULGU C2 - Kayma en belirgin Stage1.M1'de** (lt/st = 33.7756). Sirali liste, Faz 3'te hangi
> output'larin zaman bagimli davranis gosterdigini onceliklendirmek icin
> kullanilacak.

## Capability (Cp / Cpk)

**Veride spesifikasyon limiti YOK** (A4). Asagidaki degerler setpoint
etrafinda simetrik varsayimsal toleranslarla hesaplandi. Amac *mutlak*
bir "proses yeterli/yetersiz" hukmu vermek degil -- output'lari **ayni
olcute gore siralamak.** Uc senaryo, sonucun tolerans secimine ne kadar
duyarli oldugunu gosteriyor.

| output | error_type | setpoint | sigma_st | Cpk dar (+/-%1) | Cpk orta (+/-%2) | Cpk genis (+/-%5) |
|---|---|---|---|---|---|---|
| Stage1.M1 | bias | 22.74 | 0.035 | -82.4 | -80.23 | -73.73 |
| Stage1.M0 | bias | 13.75 | 0.0121 | -17.95 | -14.16 | -2.79 |
| Stage2.M1 | bias | 11.71 | 0.1239 | -13.49 | -13.17 | -12.23 |
| Stage1.M2 | bias | 13.02 | 0.0391 | -12.45 | -11.34 | -8.02 |
| Stage1.M10 | bias | 8.65 | 0.0214 | -11.41 | -10.07 | -6.02 |
| Stage2.M14 | bias | 11.71 | 0.1268 | -9.34 | -9.03 | -8.11 |
| Stage1.M6 | bias | 4.25 | 0.0809 | -9.05 | -8.88 | -8.35 |
| Stage1.M14 | bias | 17.72 | 0.0748 | -9.36 | -8.57 | -6.21 |
| Stage1.M12 | bias | 2.02 | 0.0182 | -8.14 | -7.77 | -6.66 |
| Stage2.M13 | bias | 2.89 | 0.05 | -4.44 | -4.25 | -3.67 |
| Stage2.M0 | bias | 12.05 | 0.0913 | -2.34 | -1.9 | -0.58 |
| Stage1.M9 | bias | 19.52 | 0.0425 | -3.0 | -1.47 | 3.12 |
| Stage1.M13 | variability | 3.16 | 0.036 | -1.62 | -1.33 | -0.45 |
| Stage2.M12 | variability | 1.85 | 0.0359 | -1.32 | -1.15 | -0.64 |
| Stage2.M7 | belirsiz | 2.75 | 0.0542 | -1.29 | -1.12 | -0.61 |
| Stage1.M4 | variability | 32.55 | 0.0401 | -3.47 | -0.77 | 7.34 |
| Stage2.M2 | variability | 11.0 | 0.1193 | -0.49 | -0.19 | 0.73 |
| Stage2.M5 | variability | 2.71 | 0.0526 | -0.28 | -0.11 | 0.41 |
| Stage2.M8 | belirsiz | 19.39 | 0.2529 | -0.18 | 0.07 | 0.84 |
| Stage2.M3 | variability | 20.73 | 0.067 | -0.47 | 0.57 | 3.66 |
| Stage2.M11 | variability | 5.65 | 0.037 | 0.32 | 0.83 | 2.36 |
| Stage1.M8 | bias | 21.3 | 0.0147 | -3.98 | 0.86 | 15.38 |
| Stage2.M10 | variability | 7.93 | 0.0465 | 0.31 | 0.88 | 2.58 |
| Stage1.M3 | bias | 21.88 | 0.0218 | -1.97 | 1.37 | 11.4 |
| Stage2.M9 | variability | 16.47 | 0.0424 | 0.17 | 1.47 | 5.35 |

> **BULGU C3 - En dusuk capability'ye sahip output'lar** (orta senaryo,
> +/-%2 tolerans):
>   - `Stage1.M1` (bias): Cpk = **-80.23**
>   - `Stage1.M0` (bias): Cpk = **-14.16**
>   - `Stage2.M1` (bias): Cpk = **-13.17**
>   - `Stage1.M2` (bias): Cpk = **-11.34**
>   - `Stage1.M10` (bias): Cpk = **-10.07**
>
> Cpk'nin negatif olmasi, proses ortalamasinin varsayilan tolerans
> bandinin **disinda** kalmasi demektir -- yani bias o kadar buyuk ki
> urun sistematik olarak spec disinda uretiliyor olurdu. Bu, Faz 1'deki
> bias bulgusunun capability diliyle tekrari.

> **BULGU C4 - Optimizasyon hedefi output'larin capability'si.**
> Variability-baskin olanlar arasinda en dusuk Cpk:
>   - `Stage1.M13`: Cpk = -1.33, sigma_st = 0.036
>   - `Stage2.M12`: Cpk = -1.15, sigma_st = 0.0359
>   - `Stage1.M4`: Cpk = -0.77, sigma_st = 0.0401
>   - `Stage2.M2`: Cpk = -0.19, sigma_st = 0.1193
>   - `Stage2.M5`: Cpk = -0.11, sigma_st = 0.0526
> Bunlar Faz 3/4'un birincil hedefi: bias'i degil **yayilimi** kucultmek.

## Tam tablo

| output | error_type | n | mean | setpoint | sigma_st | sigma_lt | lt_st_ratio | ooc | ooc_pct | Cp dar (+/-%1) | Cpk dar (+/-%1) | Cp orta (+/-%2) | Cpk orta (+/-%2) | Cp genis (+/-%5) | Cpk genis (+/-%5) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Stage1.M0 | bias | 14018 | 12.9613 | 13.75 | 0.0121 | 0.2058 | 17.0145 | 11335 | 80.8603 | 3.79 | -17.95 | 7.58 | -14.16 | 18.95 | -2.79 |
| Stage1.M1 | bias | 8177 | 13.8705 | 22.74 | 0.035 | 1.1808 | 33.7756 | 3765 | 46.0438 | 2.17 | -82.4 | 4.34 | -80.23 | 10.84 | -73.73 |
| Stage1.M2 | bias | 14002 | 11.4273 | 13.02 | 0.0391 | 0.5552 | 14.1825 | 10073 | 71.9397 | 1.11 | -12.45 | 2.22 | -11.34 | 5.54 | -8.02 |
| Stage1.M3 | bias | 13953 | 21.5323 | 21.88 | 0.0218 | 0.2322 | 10.6416 | 4567 | 32.7313 | 3.34 | -1.97 | 6.68 | 1.37 | 16.71 | 11.4 |
| Stage1.M4 | variability | 13912 | 33.2935 | 32.55 | 0.0401 | 1.1119 | 27.7123 | 11431 | 82.1665 | 2.7 | -3.47 | 5.41 | -0.77 | 13.52 | 7.34 |
| Stage1.M6 | bias | 9372 | 2.0115 | 4.25 | 0.0809 | 0.7636 | 9.4435 | 6357 | 67.8297 | 0.18 | -9.05 | 0.35 | -8.88 | 0.88 | -8.35 |
| Stage1.M8 | bias | 13308 | 20.9118 | 21.3 | 0.0147 | 0.201 | 13.7029 | 5372 | 40.3667 | 4.84 | -3.98 | 9.68 | 0.86 | 24.2 | 15.38 |
| Stage1.M9 | bias | 13362 | 18.9421 | 19.52 | 0.0425 | 0.2879 | 6.7758 | 5590 | 41.8351 | 1.53 | -3.0 | 3.06 | -1.47 | 7.66 | 3.12 |
| Stage1.M10 | bias | 13819 | 7.8314 | 8.65 | 0.0214 | 0.1734 | 8.1113 | 9073 | 65.656 | 1.35 | -11.41 | 2.7 | -10.07 | 6.74 | -6.02 |
| Stage1.M12 | bias | 10892 | 1.5558 | 2.02 | 0.0182 | 0.1433 | 7.8798 | 6325 | 58.0701 | 0.37 | -8.14 | 0.74 | -7.77 | 1.85 | -6.66 |
| Stage1.M13 | variability | 13743 | 2.9536 | 3.16 | 0.036 | 0.8328 | 23.1238 | 9638 | 70.1302 | 0.29 | -1.62 | 0.58 | -1.33 | 1.46 | -0.45 |
| Stage1.M14 | bias | 9071 | 15.4413 | 17.72 | 0.0748 | 0.663 | 8.8632 | 8460 | 93.2642 | 0.79 | -9.36 | 1.58 | -8.57 | 3.95 | -6.21 |
| Stage2.M0 | bias | 12861 | 12.8108 | 12.05 | 0.0913 | 0.2523 | 2.7635 | 1157 | 8.9962 | 0.44 | -2.34 | 0.88 | -1.9 | 2.2 | -0.58 |
| Stage2.M1 | bias | 13408 | 6.5791 | 11.71 | 0.1239 | 0.79 | 6.3751 | 3703 | 27.6178 | 0.32 | -13.49 | 0.63 | -13.17 | 1.58 | -12.23 |
| Stage2.M2 | variability | 13480 | 10.7129 | 11.0 | 0.1193 | 0.7931 | 6.6499 | 3189 | 23.6573 | 0.31 | -0.49 | 0.61 | -0.19 | 1.54 | 0.73 |
| Stage2.M3 | variability | 13312 | 20.4291 | 20.73 | 0.067 | 0.5392 | 8.0444 | 9233 | 69.3585 | 1.03 | -0.47 | 2.06 | 0.57 | 5.15 | 3.66 |
| Stage2.M5 | variability | 13896 | 2.7811 | 2.71 | 0.0526 | 0.2233 | 4.246 | 4640 | 33.3909 | 0.17 | -0.28 | 0.34 | -0.11 | 0.86 | 0.41 |
| Stage2.M7 | belirsiz | 13739 | 2.987 | 2.75 | 0.0542 | 0.2325 | 4.2919 | 716 | 5.2114 | 0.17 | -1.29 | 0.34 | -1.12 | 0.85 | -0.61 |
| Stage2.M8 | belirsiz | 13111 | 19.7218 | 19.39 | 0.2529 | 0.3878 | 1.5333 | 291 | 2.2195 | 0.26 | -0.18 | 0.51 | 0.07 | 1.28 | 0.84 |
| Stage2.M9 | variability | 9876 | 16.6129 | 16.47 | 0.0424 | 0.2462 | 5.8074 | 2182 | 22.094 | 1.29 | 0.17 | 2.59 | 1.47 | 6.47 | 5.35 |
| Stage2.M10 | variability | 13450 | 7.8934 | 7.93 | 0.0465 | 0.1235 | 2.6569 | 978 | 7.2714 | 0.57 | 0.31 | 1.14 | 0.88 | 2.84 | 2.58 |
| Stage2.M11 | variability | 13457 | 5.6705 | 5.65 | 0.037 | 0.1522 | 4.1092 | 6410 | 47.6332 | 0.51 | 0.32 | 1.02 | 0.83 | 2.54 | 2.36 |
| Stage2.M12 | variability | 13819 | 2.011 | 1.85 | 0.0359 | 0.313 | 8.7158 | 1877 | 13.5827 | 0.17 | -1.32 | 0.34 | -1.15 | 0.86 | -0.64 |
| Stage2.M13 | bias | 13892 | 3.5851 | 2.89 | 0.05 | 0.2275 | 4.5454 | 6447 | 46.408 | 0.19 | -4.44 | 0.39 | -4.25 | 0.96 | -3.67 |
| Stage2.M14 | bias | 13171 | 8.0391 | 11.71 | 0.1268 | 0.655 | 5.1649 | 2835 | 21.5246 | 0.31 | -9.34 | 0.62 | -9.03 | 1.54 | -8.11 |
