# VARSAYIM A1 - Dogrulama Denemesi

**Hipotez:** `.C.` = Controlled (ayarlanabilir), `.U.` = Uncontrolled (olculur).

## 1. Dokumantasyon aramasi: SONUCSUZ

Kaggle dataset sayfasi, `awesome-industrial-datasets` kaydi ve dataseti
kullanan makaleler tarandi. Hicbiri `.C.` / `.U.` ekinin anlamini
aciklamiyor. Veri seti Liveline Technologies tarafindan 2019'da Detroit
yakinlarindaki gercek bir uretim hattindan alinmis; kolon adlandirmasi
muhtemelen firmanin ic konvansiyonu ve yayinlanmamis.

## 2. Davranissal test: SONUCSUZ

`hold_ratio` = P(ardisik fark == 0) metrigi denendi. Beklenti: kontrol
edilen degisken setpoint'te bekler, hold_ratio yuksek olur.

| grup | n | hold_ratio ort. | min | max |
|---|---|---|---|---|
| .C. | 25 | 0.754 | 0.045 | 0.994 |
| .U. (output haric) | 18 | 0.329 | 0.001 | 0.997 |

**Gruplar ayrismadi.** Test iki nedenle gecersiz:

1. `.C.Actual` bir setpoint degil, kontrol edilen degiskenin *gerceklesen*
   olcumudur. Setpoint sabitken bile actual dalgalanir; yuksek hold_ratio
   beklemek bastan hataliydi.
2. `hold_ratio` kontrol edilebilirligi degil, **sensor guncelleme frekansini**
   olcuyor. `AmbientTemperature.U.Actual` hold_ratio=0.997 -- kontrol
   edildigi icin degil, ~352 saniyede bir guncellendigi icin.

> **Sonuc: A1 ne dogrulandi ne curutuldu.** Dayanagi domain bilgisi olarak
> kalir: bir ekstruderde bolge sicakliklari ve vida devri ayarlanir
> (`Zone1Temperature.C`, `MotorRPM.C`); motor amperaji ve malzeme basinci
> bunlarin sonucudur (`MotorAmperage.U`, `MaterialPressure.U`). Sprint 7'de
> karar degiskeni seti daraltilip genisletilerek **duyarlilik analizi**
> yapilacak; sonuc bu varsayima bagliysa acikca belirtilecek.

## 3. Testten cikan gercek bulgu: ornekleme frekansi

Butun kolonlar 1 Hz *kaydedilmis* ama 1 Hz *olculmemis*. Efektif
guncelleme periyotlari cok farkli:

**15 kolonun 4 saatlik pencerede 100'den az degisimi var:**

| column | role | degisim sayisi | guncelleme periyodu (sn) | ayrik seviye |
|---|---|---|---|---|
| Machine2.RawMaterial.Property1 | raw_material | 1 | 14088.0 | 2 |
| Machine2.RawMaterial.Property4 | raw_material | 1 | 14088.0 | 2 |
| Machine2.RawMaterial.Property3 | raw_material | 1 | 14088.0 | 2 |
| Machine2.RawMaterial.Property2 | raw_material | 1 | 14088.0 | 2 |
| Machine3.RawMaterial.Property1 | raw_material | 2 | 7044.0 | 3 |
| Machine3.RawMaterial.Property4 | raw_material | 2 | 7044.0 | 3 |
| Machine3.RawMaterial.Property3 | raw_material | 2 | 7044.0 | 3 |
| Machine3.RawMaterial.Property2 | raw_material | 2 | 7044.0 | 3 |
| Machine1.RawMaterial.Property1 | raw_material | 4 | 3522.0 | 4 |
| Machine1.RawMaterial.Property4 | raw_material | 4 | 3522.0 | 4 |
| Machine1.RawMaterial.Property2 | raw_material | 4 | 3522.0 | 4 |
| Machine1.RawMaterial.Property3 | raw_material | 5 | 2817.6 | 5 |
| AmbientConditions.AmbientHumidity.U.Actual | ambient | 38 | 370.7 | 27 |
| AmbientConditions.AmbientTemperature.U.Actual | ambient | 40 | 352.2 | 26 |
| Machine1.Zone1Temperature.C.Actual | controlled | 83 | 169.7 | 12 |

> **BULGU F1 - Ambient kosullari pratikte sabittir.** `AmbientTemperature`
> ~352 sn'de, `AmbientHumidity` ~371 sn'de bir guncelleniyor. 4 saatlik
> pencerede bu, ~38-40 bagimsiz gozlem demek. Bu iki degiskeni output
> deviation'inin aciklayicisi olarak kullanmak istatistiksel olarak zayiftir;
> bulunacak herhangi bir iliski 40 noktaya dayanir, 14.088'e degil.

> **BULGU F2 - Hammadde ozellikleri lot bazli, surekli degil.** 2-5 ayrik
> seviye ve cok seyrek degisim. Bunlar surekli degisken gibi degil,
> kategorik lot etiketi gibi ele alinmalidir.

## 4. Tam tablo

| column | suffix | role | hold_ratio | degisim | periyot (sn) | seviye | std |
|---|---|---|---|---|---|---|---|
| Machine2.RawMaterial.Property2 | - | raw_material | 0.9999 | 1 | 14088.0 | 2 | 2.0635 |
| Machine2.RawMaterial.Property1 | - | raw_material | 0.9999 | 1 | 14088.0 | 2 | 0.1073 |
| Machine2.RawMaterial.Property4 | - | raw_material | 0.9999 | 1 | 14088.0 | 2 | 0.4127 |
| Machine2.RawMaterial.Property3 | - | raw_material | 0.9999 | 1 | 14088.0 | 2 | 18.328 |
| Machine3.RawMaterial.Property2 | - | raw_material | 0.9999 | 2 | 7044.0 | 3 | 16.3198 |
| Machine3.RawMaterial.Property1 | - | raw_material | 0.9999 | 2 | 7044.0 | 3 | 0.3966 |
| Machine3.RawMaterial.Property4 | - | raw_material | 0.9999 | 2 | 7044.0 | 3 | 2.1776 |
| Machine3.RawMaterial.Property3 | - | raw_material | 0.9999 | 2 | 7044.0 | 3 | 9.5599 |
| Machine1.RawMaterial.Property4 | - | raw_material | 0.9997 | 4 | 3522.0 | 4 | 3.2978 |
| Machine1.RawMaterial.Property1 | - | raw_material | 0.9997 | 4 | 3522.0 | 4 | 0.5103 |
| Machine1.RawMaterial.Property2 | - | raw_material | 0.9997 | 4 | 3522.0 | 4 | 11.6063 |
| Machine1.RawMaterial.Property3 | - | raw_material | 0.9996 | 5 | 2817.6 | 5 | 126.662 |
| AmbientConditions.AmbientHumidity.U.Actual | .U. | ambient | 0.9973 | 38 | 370.7 | 27 | 1.189 |
| AmbientConditions.AmbientTemperature.U.Actual | .U. | ambient | 0.9972 | 40 | 352.2 | 26 | 0.3735 |
| Machine1.Zone1Temperature.C.Actual | .C. | controlled | 0.9941 | 83 | 169.7 | 12 | 0.0632 |
| Machine5.Temperature3.C.Actual | .C. | controlled | 0.9927 | 103 | 136.8 | 69 | 1.0309 |
| Machine3.Zone1Temperature.C.Actual | .C. | controlled | 0.9891 | 153 | 92.1 | 20 | 0.0768 |
| Machine3.ExitZoneTemperature.C.Actual | .C. | controlled | 0.9844 | 220 | 64.0 | 19 | 0.0624 |
| Machine3.MaterialTemperature.U.Actual | .U. | measured | 0.9835 | 233 | 60.5 | 109 | 2.0583 |
| Machine5.Temperature6.C.Actual | .C. | controlled | 0.9798 | 284 | 49.6 | 49 | 0.4022 |
| Machine5.Temperature5.C.Actual | .C. | controlled | 0.9795 | 289 | 48.7 | 35 | 0.1056 |
| Machine5.Temperature4.C.Actual | .C. | controlled | 0.9739 | 367 | 38.4 | 85 | 1.591 |
| Machine1.MaterialTemperature.U.Actual | .U. | measured | 0.9701 | 421 | 33.5 | 99 | 0.9306 |
| Machine5.Temperature1.C.Actual | .C. | controlled | 0.9634 | 516 | 27.3 | 21 | 0.0392 |
| Machine5.Temperature2.C.Actual | .C. | controlled | 0.9615 | 542 | 26.0 | 27 | 0.0519 |
| Machine4.Temperature5.C.Actual | .C. | controlled | 0.9556 | 626 | 22.5 | 69 | 2.8599 |
| Stage1.Output.Measurement5.U.Actual | .U. | output_actual | 0.9531 | 661 | 21.3 | 92 | 0.5702 |
| Machine1.ExitZoneTemperature.C.Actual | .C. | controlled | 0.952 | 676 | 20.8 | 130 | 2.059 |
| Machine4.Temperature3.C.Actual | .C. | controlled | 0.9419 | 819 | 17.2 | 70 | 3.7133 |
| FirstStage.CombinerOperation.Temperature3.C.Actual | .C. | controlled | 0.9386 | 865 | 16.3 | 38 | 0.1183 |
| Machine4.Temperature1.C.Actual | .C. | controlled | 0.9155 | 1190 | 11.8 | 81 | 2.2878 |
| Stage2.Output.Measurement4.U.Actual | .U. | output_actual | 0.9084 | 1290 | 10.9 | 367 | 9.1677 |
| Machine3.Zone2Temperature.C.Actual | .C. | controlled | 0.9018 | 1383 | 10.2 | 58 | 0.1148 |
| Machine4.Temperature2.C.Actual | .C. | controlled | 0.9018 | 1384 | 10.2 | 84 | 2.9572 |
| Stage1.Output.Measurement11.U.Actual | .U. | output_actual | 0.8951 | 1478 | 9.5 | 110 | 2.5427 |
| Machine1.Zone2Temperature.C.Actual | .C. | controlled | 0.8689 | 1847 | 7.6 | 60 | 0.4063 |
| Stage1.Output.Measurement7.U.Actual | .U. | output_actual | 0.8581 | 1999 | 7.0 | 52 | 1.414 |
| Machine2.ExitZoneTemperature.C.Actual | .C. | controlled | 0.7831 | 3055 | 4.6 | 52 | 0.1621 |
| Stage1.Output.Measurement1.U.Actual | .U. | output_actual | 0.7514 | 3502 | 4.0 | 359 | 6.9043 |
| FirstStage.CombinerOperation.Temperature1.U.Actual | .U. | measured | 0.7108 | 4074 | 3.5 | 211 | 5.6699 |
| Stage1.Output.Measurement14.U.Actual | .U. | output_actual | 0.6754 | 4572 | 3.1 | 295 | 7.4165 |
| Stage1.Output.Measurement6.U.Actual | .U. | output_actual | 0.6639 | 4735 | 3.0 | 327 | 1.1357 |
| Stage1.Output.Measurement12.U.Actual | .U. | output_actual | 0.6578 | 4821 | 2.9 | 122 | 0.6637 |
| Stage1.Output.Measurement8.U.Actual | .U. | output_actual | 0.6325 | 5177 | 2.7 | 115 | 4.7866 |
| Stage1.Output.Measurement0.U.Actual | .U. | output_actual | 0.6148 | 5426 | 2.6 | 143 | 0.9342 |
| Stage1.Output.Measurement3.U.Actual | .U. | output_actual | 0.6028 | 5595 | 2.5 | 124 | 2.1105 |
| Stage1.Output.Measurement13.U.Actual | .U. | output_actual | 0.5984 | 5658 | 2.5 | 243 | 0.941 |
| Stage1.Output.Measurement9.U.Actual | .U. | output_actual | 0.5864 | 5827 | 2.4 | 226 | 4.1973 |
| Stage1.Output.Measurement10.U.Actual | .U. | output_actual | 0.5807 | 5907 | 2.4 | 146 | 1.0855 |
| Machine4.ExitTemperature.U.Actual | .U. | measured | 0.5712 | 6040 | 2.3 | 122 | 23.6531 |
| Stage1.Output.Measurement2.U.Actual | .U. | output_actual | 0.5699 | 6059 | 2.3 | 316 | 1.0528 |
| Stage1.Output.Measurement4.U.Actual | .U. | output_actual | 0.568 | 6086 | 2.3 | 466 | 3.8698 |
| Machine4.Pressure.C.Actual | .C. | controlled | 0.4924 | 7151 | 2.0 | 56 | 0.9411 |
| Machine4.Temperature4.C.Actual | .C. | controlled | 0.4924 | 7151 | 2.0 | 56 | 0.9411 |
| Stage2.Output.Measurement9.U.Actual | .U. | output_actual | 0.4347 | 7964 | 1.8 | 173 | 7.6086 |
| Machine1.MotorRPM.C.Actual | .C. | controlled | 0.3339 | 9384 | 1.5 | 111 | 0.6352 |
| Stage2.Output.Measurement7.U.Actual | .U. | output_actual | 0.2769 | 10186 | 1.4 | 235 | 0.5179 |
| Machine2.MaterialTemperature.U.Actual | .U. | measured | 0.2743 | 10223 | 1.4 | 137 | 0.855 |
| Stage2.Output.Measurement3.U.Actual | .U. | output_actual | 0.2542 | 10506 | 1.3 | 388 | 4.6903 |
| Stage2.Output.Measurement11.U.Actual | .U. | output_actual | 0.2498 | 10568 | 1.3 | 161 | 1.1823 |
| Stage2.Output.Measurement12.U.Actual | .U. | output_actual | 0.2475 | 10601 | 1.3 | 172 | 0.4145 |
| Stage2.Output.Measurement10.U.Actual | .U. | output_actual | 0.2397 | 10710 | 1.3 | 155 | 1.6458 |
| Stage2.Output.Measurement0.U.Actual | .U. | output_actual | 0.2318 | 10822 | 1.3 | 246 | 3.6205 |
| Stage2.Output.Measurement13.U.Actual | .U. | output_actual | 0.2261 | 10902 | 1.3 | 244 | 0.4768 |
| Stage2.Output.Measurement2.U.Actual | .U. | output_actual | 0.2259 | 10905 | 1.3 | 490 | 2.3112 |
| Stage2.Output.Measurement5.U.Actual | .U. | output_actual | 0.224 | 10932 | 1.3 | 215 | 0.3914 |
| Stage2.Output.Measurement14.U.Actual | .U. | output_actual | 0.22 | 10988 | 1.3 | 396 | 2.0829 |
| Stage2.Output.Measurement8.U.Actual | .U. | output_actual | 0.2192 | 10999 | 1.3 | 274 | 5.0244 |
| Stage2.Output.Measurement1.U.Actual | .U. | output_actual | 0.2066 | 11176 | 1.3 | 523 | 1.607 |
| Machine2.Zone2Temperature.C.Actual | .C. | controlled | 0.2033 | 11223 | 1.3 | 174 | 0.1091 |
| Machine2.Zone1Temperature.C.Actual | .C. | controlled | 0.2024 | 11236 | 1.3 | 108 | 0.057 |
| Stage2.Output.Measurement6.U.Actual | .U. | output_actual | 0.2016 | 11247 | 1.3 | 205 | 0.2048 |
| FirstStage.CombinerOperation.Temperature2.U.Actual | .U. | measured | 0.1104 | 12532 | 1.1 | 359 | 18.5793 |
| Machine2.MotorRPM.C.Actual | .C. | controlled | 0.1083 | 12562 | 1.1 | 65 | 0.0292 |
| Machine5.ExitTemperature.U.Actual | .U. | measured | 0.0965 | 12728 | 1.1 | 310 | 10.308 |
| Machine2.MotorAmperage.U.Actual | .U. | measured | 0.0909 | 12807 | 1.1 | 92 | 0.3961 |
| Machine1.MotorAmperage.U.Actual | .U. | measured | 0.0765 | 13009 | 1.1 | 311 | 5.5252 |
| Machine3.MotorRPM.C.Actual | .C. | controlled | 0.0454 | 13448 | 1.0 | 248 | 0.4346 |
| Machine3.MaterialPressure.U.Actual | .U. | measured | 0.0391 | 13536 | 1.0 | 1682 | 6.1221 |
| Machine2.MaterialPressure.U.Actual | .U. | measured | 0.005 | 14016 | 1.0 | 764 | 3.1064 |
| Machine1.MaterialPressure.U.Actual | .U. | measured | 0.0028 | 14048 | 1.0 | 3655 | 20.4784 |
| Machine3.MotorAmperage.U.Actual | .U. | measured | 0.0014 | 14067 | 1.0 | 3395 | 9.0777 |
| Machine3.RawMaterialFeederParameter.U.Actual | .U. | measured | 0.0013 | 14069 | 1.0 | 5145 | 15.6536 |
| Machine2.RawMaterialFeederParameter.U.Actual | .U. | measured | 0.001 | 14073 | 1.0 | 5127 | 15.1109 |
| Machine1.RawMaterialFeederParameter.U.Actual | .U. | measured | 0.0009 | 14075 | 1.0 | 6057 | 95.8459 |
