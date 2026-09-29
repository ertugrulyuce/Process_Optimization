# Data Dictionary

Otomatik uretildi: `python src/data_processing/data_dictionary.py`  
Kaynak: `data/raw/continuous_factory_process.csv` (14,088 x 116)

Elle duzenlenmez. Veri degisirse script yeniden calistirilir.

## Rol tanimlari

| Rol | Adet | Aciklama |
|---|---|---|
| `time` | 1 | Zaman damgasi (1 Hz). |
| `ambient` | 2 | Cevre kosulu. Kontrol edilemez. Efektif ornekleme ~350 sn (K4) -> 4 saatte ~40 bagimsiz gozlem. |
| `raw_material` | 12 | Gelen hammadde ozelligi. Kontrol edilemez. 2-5 ayrik seviye, cok seyrek degisim (K4) -> lot etiketi gibi ele alinir. |
| `controlled` | 25 | Operatorun ayarlayabildigi parametre (VARSAYIM A1). Optimizasyonun karar degiskeni. |
| `measured` | 16 | Proses tepkisi. Ayarlanmaz, olculur. Teshis degiskeni; optimizasyonda karar degiskeni DEGIL. |
| `output_actual` | 30 | Urun boyutsal olcumu. Optimize edilen cikti. Tam 0 = sensor dropout (R1), negatif = imkansiz (R2). |
| `output_setpoint` | 30 | Hedef deger. SABIT (K3) -> model girdisi degil, yalnizca deviation'in referans noktasi. |

## Prosesteki asamalar

| Stage | Kolon | Aciklama |
|---|---|---|
| `ambient` | 2 | Hat disi cevre |
| `stage1` | 36 | Stage 1 - Machine 1/2/3 (paralel) |
| `stage2` | 14 | Stage 2 - Machine 4/5 (seri) |
| `combiner` | 3 | Stage 1 birlestirme adimi |
| `stage1_out` | 30 | Stage 1 cikti olcumu (combiner sonrasi) |
| `stage2_out` | 30 | Stage 2 cikti olcumu (nihai) |
| `-` | 1 | - |

## Kolonlar

### `controlled` (25 kolon)

*Operatorun ayarlayabildigi parametre (VARSAYIM A1). Optimizasyonun karar degiskeni.*

| column | stage | machine | min | max | mean | std | n_unique | n_changes | zero_pct | note |
|---|---|---|---|---|---|---|---|---|---|---|
| Machine1.Zone1Temperature.C.Actual | stage1 | M1 | 71.9 | 72.5 | 72.013 | 0.0632 | 12 | 83.0 | 0.0 |  |
| Machine1.Zone2Temperature.C.Actual | stage1 | M1 | 71.3 | 72.7 | 72.013 | 0.4063 | 60 | 1847.0 | 0.0 |  |
| Machine1.MotorRPM.C.Actual | stage1 | M1 | 10.39 | 12.24 | 11.072 | 0.6352 | 111 | 9384.0 | 0.0 |  |
| Machine1.ExitZoneTemperature.C.Actual | stage1 | M1 | 69.7 | 80.0 | 75.966 | 2.059 | 130 | 676.0 | 0.0 |  |
| Machine2.Zone1Temperature.C.Actual | stage1 | M2 | 68.67 | 69.66 | 68.997 | 0.057 | 108 | 11236.0 | 0.0 |  |
| Machine2.Zone2Temperature.C.Actual | stage1 | M2 | 67.78 | 69.941 | 69.101 | 0.1091 | 174 | 11223.0 | 0.0 |  |
| Machine2.MotorRPM.C.Actual | stage1 | M2 | 13.82 | 13.97 | 13.897 | 0.0292 | 65 | 12562.0 | 0.0 |  |
| Machine2.ExitZoneTemperature.C.Actual | stage1 | M2 | 59.599 | 60.5 | 60.001 | 0.1621 | 52 | 3055.0 | 0.0 |  |
| Machine3.Zone1Temperature.C.Actual | stage1 | M3 | 77.278 | 78.7 | 78.008 | 0.0768 | 20 | 153.0 | 0.0 |  |
| Machine3.Zone2Temperature.C.Actual | stage1 | M3 | 77.7 | 78.6 | 78.005 | 0.1148 | 58 | 1383.0 | 0.0 |  |
| Machine3.MotorRPM.C.Actual | stage1 | M3 | 11.96 | 14.0 | 13.27 | 0.4346 | 248 | 13448.0 | 0.0 |  |
| Machine3.ExitZoneTemperature.C.Actual | stage1 | M3 | 64.8 | 65.2 | 65.008 | 0.0624 | 19 | 220.0 | 0.0 |  |
| FirstStage.CombinerOperation.Temperature3.C.Actual | combiner | - | 79.6 | 80.322 | 80.004 | 0.1183 | 38 | 865.0 | 0.0 |  |
| Machine4.Temperature1.C.Actual | stage2 | M4 | 298.0 | 393.0 | 360.124 | 2.2878 | 81 | 1190.0 | 0.0 |  |
| Machine4.Temperature2.C.Actual | stage2 | M4 | 284.0 | 396.0 | 360.135 | 2.9572 | 84 | 1384.0 | 0.0 |  |
| Machine4.Pressure.C.Actual | stage2 | M4 | 14.0 | 25.0 | 17.226 | 0.9411 | 56 | 7151.0 | 0.0 |  |
| Machine4.Temperature3.C.Actual | stage2 | M4 | 268.0 | 327.0 | 322.612 | 3.7133 | 70 | 819.0 | 0.0 |  |
| Machine4.Temperature4.C.Actual | stage2 | M4 | 14.0 | 25.0 | 17.226 | 0.9411 | 56 | 7151.0 | 0.0 | DUSURULDU (R3) - Machine4.Pressure ile birebir ozdes |
| Machine4.Temperature5.C.Actual | stage2 | M4 | 260.0 | 326.0 | 309.782 | 2.8599 | 69 | 626.0 | 0.0 |  |
| Machine5.Temperature1.C.Actual | stage2 | M5 | 309.4 | 310.3 | 309.998 | 0.0392 | 21 | 516.0 | 0.0 |  |
| Machine5.Temperature2.C.Actual | stage2 | M5 | 289.7 | 290.3 | 289.998 | 0.0519 | 27 | 542.0 | 0.0 |  |
| Machine5.Temperature3.C.Actual | stage2 | M5 | 263.8 | 270.0 | 269.679 | 1.0309 | 69 | 103.0 | 0.0 |  |
| Machine5.Temperature4.C.Actual | stage2 | M5 | 237.6 | 245.0 | 242.66 | 1.591 | 85 | 367.0 | 0.0 |  |
| Machine5.Temperature5.C.Actual | stage2 | M5 | 242.9 | 245.7 | 244.995 | 0.1056 | 35 | 289.0 | 0.0 |  |
| Machine5.Temperature6.C.Actual | stage2 | M5 | 62.8 | 66.1 | 63.421 | 0.4022 | 49 | 284.0 | 0.0 |  |

### `measured` (16 kolon)

*Proses tepkisi. Ayarlanmaz, olculur. Teshis degiskeni; optimizasyonda karar degiskeni DEGIL.*

| column | stage | machine | min | max | mean | std | n_unique | n_changes | zero_pct | note |
|---|---|---|---|---|---|---|---|---|---|---|
| Machine1.RawMaterialFeederParameter.U.Actual | stage1 | M1 | 231.3 | 1331.82 | 1242.764 | 95.8459 | 6057 | 14075.0 | 0.0 |  |
| Machine1.MotorAmperage.U.Actual | stage1 | M1 | 44.4 | 88.53 | 70.333 | 5.5252 | 311 | 13009.0 | 0.0 |  |
| Machine1.MaterialPressure.U.Actual | stage1 | M1 | 359.47 | 487.25 | 409.007 | 20.4784 | 3655 | 14048.0 | 0.0 |  |
| Machine1.MaterialTemperature.U.Actual | stage1 | M1 | 76.3 | 83.9 | 81.47 | 0.9306 | 99 | 421.0 | 0.0 |  |
| Machine2.RawMaterialFeederParameter.U.Actual | stage1 | M2 | 0.0 | 266.48 | 202.585 | 15.1109 | 5127 | 14073.0 | 0.0 |  |
| Machine2.MotorAmperage.U.Actual | stage1 | M2 | 71.56 | 74.38 | 73.399 | 0.3961 | 92 | 12807.0 | 0.0 |  |
| Machine2.MaterialPressure.U.Actual | stage1 | M2 | 218.87 | 250.58 | 226.122 | 3.1064 | 764 | 14016.0 | 0.0 |  |
| Machine2.MaterialTemperature.U.Actual | stage1 | M2 | 68.8 | 77.4 | 76.812 | 0.855 | 137 | 10223.0 | 0.0 |  |
| Machine3.RawMaterialFeederParameter.U.Actual | stage1 | M3 | 0.0 | 259.07 | 202.38 | 15.6536 | 5145 | 14069.0 | 0.1 |  |
| Machine3.MotorAmperage.U.Actual | stage1 | M3 | 321.25 | 374.32 | 345.112 | 9.0777 | 3395 | 14067.0 | 0.0 |  |
| Machine3.MaterialPressure.U.Actual | stage1 | M3 | 235.06 | 263.71 | 246.75 | 6.1221 | 1682 | 13536.0 | 0.0 |  |
| Machine3.MaterialTemperature.U.Actual | stage1 | M3 | 65.3 | 75.5 | 74.14 | 2.0583 | 109 | 233.0 | 0.0 |  |
| FirstStage.CombinerOperation.Temperature1.U.Actual | combiner | - | 45.3 | 118.9 | 108.918 | 5.6699 | 211 | 4074.0 | 0.0 |  |
| FirstStage.CombinerOperation.Temperature2.U.Actual | combiner | - | 53.3 | 115.2 | 84.898 | 18.5793 | 359 | 12532.0 | 0.0 |  |
| Machine4.ExitTemperature.U.Actual | stage2 | M4 | 35.0 | 216.0 | 187.14 | 23.6531 | 122 | 6040.0 | 0.0 |  |
| Machine5.ExitTemperature.U.Actual | stage2 | M5 | 45.4 | 159.2 | 153.98 | 10.308 | 310 | 12728.0 | 0.0 |  |

### `ambient` (2 kolon)

*Cevre kosulu. Kontrol edilemez. Efektif ornekleme ~350 sn (K4) -> 4 saatte ~40 bagimsiz gozlem.*

| column | stage | machine | min | max | mean | std | n_unique | n_changes | zero_pct | note |
|---|---|---|---|---|---|---|---|---|---|---|
| AmbientConditions.AmbientHumidity.U.Actual | ambient | - | 13.84 | 17.24 | 15.331 | 1.189 | 27 | 38.0 | 0.0 |  |
| AmbientConditions.AmbientTemperature.U.Actual | ambient | - | 23.02 | 24.43 | 23.844 | 0.3735 | 26 | 40.0 | 0.0 |  |

### `raw_material` (12 kolon)

*Gelen hammadde ozelligi. Kontrol edilemez. 2-5 ayrik seviye, cok seyrek degisim (K4) -> lot etiketi gibi ele alinir.*

| column | stage | machine | min | max | mean | std | n_unique | n_changes | zero_pct | note |
|---|---|---|---|---|---|---|---|---|---|---|
| Machine1.RawMaterial.Property1 | stage1 | M1 | 11.54 | 12.9 | 11.851 | 0.5103 | 4 | 4.0 | 0.0 |  |
| Machine1.RawMaterial.Property2 | stage1 | M1 | 200.0 | 236.0 | 205.676 | 11.6063 | 4 | 4.0 | 0.0 |  |
| Machine1.RawMaterial.Property3 | stage1 | M1 | 601.11 | 1048.06 | 951.68 | 126.662 | 5 | 5.0 | 0.0 |  |
| Machine1.RawMaterial.Property4 | stage1 | M1 | 247.0 | 257.0 | 248.869 | 3.2978 | 4 | 4.0 | 0.0 |  |
| Machine2.RawMaterial.Property1 | stage1 | M2 | 12.59 | 12.85 | 12.793 | 0.1073 | 2 | 1.0 | 0.0 |  |
| Machine2.RawMaterial.Property2 | stage1 | M2 | 236.0 | 241.0 | 239.911 | 2.0635 | 2 | 1.0 | 0.0 |  |
| Machine2.RawMaterial.Property3 | stage1 | M2 | 556.7 | 601.11 | 566.368 | 18.328 | 2 | 1.0 | 0.0 |  |
| Machine2.RawMaterial.Property4 | stage1 | M2 | 256.0 | 257.0 | 256.218 | 0.4127 | 2 | 1.0 | 0.0 |  |
| Machine3.RawMaterial.Property1 | stage1 | M3 | 8.83 | 9.86 | 9.09 | 0.3966 | 3 | 2.0 | 0.0 |  |
| Machine3.RawMaterial.Property2 | stage1 | M3 | 186.0 | 221.0 | 205.647 | 16.3198 | 3 | 2.0 | 0.0 |  |
| Machine3.RawMaterial.Property3 | stage1 | M3 | 408.97 | 433.18 | 425.014 | 9.5599 | 3 | 2.0 | 0.0 |  |
| Machine3.RawMaterial.Property4 | stage1 | M3 | 200.0 | 205.0 | 203.039 | 2.1776 | 3 | 2.0 | 0.0 |  |

### `output_actual` (30 kolon)

*Urun boyutsal olcumu. Optimize edilen cikti. Tam 0 = sensor dropout (R1), negatif = imkansiz (R2).*

| column | stage | machine | min | max | mean | std | n_unique | n_changes | zero_pct | note |
|---|---|---|---|---|---|---|---|---|---|---|
| Stage1.Output.Measurement0.U.Actual | stage1_out | - | 0.0 | 20.88 | 12.961 | 0.2058 | 143 | 5426.0 | 0.5 |  |
| Stage1.Output.Measurement1.U.Actual | stage1_out | - | -3.133 | 19.14 | 13.851 | 1.2893 | 359 | 3502.0 | 41.9 |  |
| Stage1.Output.Measurement2.U.Actual | stage1_out | - | -4.928 | 23.53 | 11.426 | 0.5721 | 316 | 6059.0 | 0.6 |  |
| Stage1.Output.Measurement3.U.Actual | stage1_out | - | 0.0 | 26.24 | 21.532 | 0.2322 | 124 | 5595.0 | 1.0 |  |
| Stage1.Output.Measurement4.U.Actual | stage1_out | - | -7.689 | 34.76 | 33.288 | 1.2151 | 466 | 6086.0 | 1.2 |  |
| Stage1.Output.Measurement5.U.Actual | stage1_out | - | -0.58 | 4.96 | 2.544 | 0.7087 | 92 | 661.0 | 95.1 |  |
| Stage1.Output.Measurement6.U.Actual | stage1_out | - | -0.746 | 7.03 | 2.008 | 0.7677 | 327 | 4735.0 | 33.4 |  |
| Stage1.Output.Measurement7.U.Actual | stage1_out | - | -0.76 | 5.19 | 2.91 | 0.1404 | 52 | 1999.0 | 62.2 |  |
| Stage1.Output.Measurement8.U.Actual | stage1_out | - | -0.0 | 22.46 | 20.907 | 0.3727 | 115 | 5177.0 | 5.5 |  |
| Stage1.Output.Measurement9.U.Actual | stage1_out | - | -0.004 | 20.45 | 18.936 | 0.4361 | 226 | 5827.0 | 5.1 |  |
| Stage1.Output.Measurement10.U.Actual | stage1_out | - | -0.001 | 13.07 | 7.831 | 0.1858 | 146 | 5907.0 | 1.9 |  |
| Stage1.Output.Measurement11.U.Actual | stage1_out | - | -0.0 | 7.47 | 5.8 | 0.3732 | 110 | 1478.0 | 74.3 |  |
| Stage1.Output.Measurement12.U.Actual | stage1_out | - | -0.0 | 3.95 | 1.555 | 0.1493 | 122 | 4821.0 | 22.6 |  |
| Stage1.Output.Measurement13.U.Actual | stage1_out | - | -1.225 | 6.91 | 2.953 | 0.8345 | 243 | 5658.0 | 2.4 |  |
| Stage1.Output.Measurement14.U.Actual | stage1_out | - | -6.549 | 22.302 | 15.418 | 0.9252 | 295 | 4572.0 | 35.5 |  |
| Stage2.Output.Measurement0.U.Actual | stage2_out | - | -0.0 | 19.064 | 12.808 | 0.3193 | 246 | 10822.0 | 8.7 |  |
| Stage2.Output.Measurement1.U.Actual | stage2_out | - | -0.0 | 12.86 | 6.577 | 0.798 | 523 | 11176.0 | 4.8 |  |
| Stage2.Output.Measurement2.U.Actual | stage2_out | - | -0.0 | 16.54 | 10.71 | 0.8142 | 490 | 10905.0 | 4.3 |  |
| Stage2.Output.Measurement3.U.Actual | stage2_out | - | -0.0 | 25.22 | 20.423 | 0.645 | 388 | 10506.0 | 5.5 |  |
| Stage2.Output.Measurement4.U.Actual | stage2_out | - | -0.0 | 34.29 | 30.928 | 4.6471 | 367 | 1290.0 | 90.5 |  |
| Stage2.Output.Measurement5.U.Actual | stage2_out | - | -0.0 | 8.11 | 2.781 | 0.227 | 215 | 10932.0 | 1.3 |  |
| Stage2.Output.Measurement6.U.Actual | stage2_out | - | -0.0 | 3.31 | 0.539 | 0.1965 | 205 | 11247.0 | 1.3 |  |
| Stage2.Output.Measurement7.U.Actual | stage2_out | - | -0.0 | 7.45 | 2.986 | 0.2366 | 235 | 10186.0 | 2.5 |  |
| Stage2.Output.Measurement8.U.Actual | stage2_out | - | -0.0 | 24.756 | 19.716 | 0.5186 | 274 | 10999.0 | 6.9 |  |
| Stage2.Output.Measurement9.U.Actual | stage2_out | - | -0.004 | 18.36 | 16.589 | 0.6713 | 173 | 7964.0 | 29.8 |  |
| Stage2.Output.Measurement10.U.Actual | stage2_out | - | -0.0 | 8.59 | 7.892 | 0.1707 | 155 | 10710.0 | 4.5 |  |
| Stage2.Output.Measurement11.U.Actual | stage2_out | - | -0.0 | 6.32 | 5.669 | 0.1741 | 161 | 10568.0 | 4.5 |  |
| Stage2.Output.Measurement12.U.Actual | stage2_out | - | -0.0 | 5.2 | 2.009 | 0.3189 | 172 | 10601.0 | 1.8 |  |
| Stage2.Output.Measurement13.U.Actual | stage2_out | - | -0.0 | 8.0 | 3.584 | 0.2335 | 244 | 10902.0 | 1.4 |  |
| Stage2.Output.Measurement14.U.Actual | stage2_out | - | -3.437 | 14.26 | 8.036 | 0.6771 | 396 | 10988.0 | 6.5 |  |

### `output_setpoint` (30 kolon)

*Hedef deger. SABIT (K3) -> model girdisi degil, yalnizca deviation'in referans noktasi.*

| column | stage | machine | min | max | mean | std | n_unique | n_changes | zero_pct | note |
|---|---|---|---|---|---|---|---|---|---|---|
| Stage1.Output.Measurement0.U.Setpoint | stage1_out | - | 0.0 | 13.75 | 13.695 | 0.8652 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement1.U.Setpoint | stage1_out | - | 0.0 | 22.74 | 22.65 | 1.4309 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement2.U.Setpoint | stage1_out | - | 0.0 | 13.02 | 12.968 | 0.8193 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement3.U.Setpoint | stage1_out | - | 0.0 | 21.88 | 21.793 | 1.3768 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement4.U.Setpoint | stage1_out | - | 0.0 | 32.55 | 32.421 | 2.0482 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement5.U.Setpoint | stage1_out | - | 0.0 | 2.74 | 2.729 | 0.1724 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement6.U.Setpoint | stage1_out | - | 0.0 | 4.25 | 4.233 | 0.2674 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement7.U.Setpoint | stage1_out | - | 0.0 | 2.97 | 2.958 | 0.1869 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement8.U.Setpoint | stage1_out | - | 0.0 | 21.3 | 21.215 | 1.3403 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement9.U.Setpoint | stage1_out | - | 0.0 | 19.52 | 19.442 | 1.2283 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement10.U.Setpoint | stage1_out | - | 0.0 | 8.65 | 8.616 | 0.5443 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement11.U.Setpoint | stage1_out | - | 0.0 | 6.16 | 6.136 | 0.3876 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement12.U.Setpoint | stage1_out | - | 0.0 | 2.02 | 2.012 | 0.1271 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement13.U.Setpoint | stage1_out | - | 0.0 | 3.16 | 3.147 | 0.1988 | 2 | 4.0 | 0.4 |  |
| Stage1.Output.Measurement14.U.Setpoint | stage1_out | - | 0.0 | 17.72 | 17.65 | 1.115 | 2 | 4.0 | 0.4 |  |
| Stage2.Output.Measurement0.U.Setpoint | stage2_out | - | 12.05 | 12.05 | 12.05 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement1.U.Setpoint | stage2_out | - | 11.71 | 11.71 | 11.71 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement2.U.Setpoint | stage2_out | - | 11.0 | 11.0 | 11.0 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement3.U.Setpoint | stage2_out | - | 20.73 | 20.73 | 20.73 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement4.U.Setpoint | stage2_out | - | 31.36 | 31.36 | 31.36 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement5.U.Setpoint | stage2_out | - | 2.71 | 2.71 | 2.71 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement6.U.Setpoint | stage2_out | - | 0.01 | 0.01 | 0.01 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement7.U.Setpoint | stage2_out | - | 2.75 | 2.75 | 2.75 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement8.U.Setpoint | stage2_out | - | 19.39 | 19.39 | 19.39 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement9.U.Setpoint | stage2_out | - | 16.47 | 16.47 | 16.47 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement10.U.Setpoint | stage2_out | - | 7.93 | 7.93 | 7.93 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement11.U.Setpoint | stage2_out | - | 5.65 | 5.65 | 5.65 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement12.U.Setpoint | stage2_out | - | 1.85 | 1.85 | 1.85 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement13.U.Setpoint | stage2_out | - | 2.89 | 2.89 | 2.89 | 0.0 | 1 | 0.0 | 0.0 |  |
| Stage2.Output.Measurement14.U.Setpoint | stage2_out | - | 11.71 | 11.71 | 11.71 | 0.0 | 1 | 0.0 | 0.0 |  |

## Turetilmis kolonlar (`data/processed/clean_v1.csv`)

| Kolon | Aciklama |
|---|---|
| `seq` | Satir sirasi. Duplicate timestamp jitter'i nedeniyle asil zaman eksenidir. |
| `flag_dup_timestamp` | Timestamp'i baska bir satirla cakisiyor (R4). |
| `flag_downtime` | Stage1 setpoint'lerinin tamami 0 - durus blogu (R5). |
| `<Stage>.M<i>.dev` | `Actual - Setpoint`. Isaretli sapma. |
| `<Stage>.M<i>.abs_dev` | Mutlak sapma. |
| `<Stage>.M<i>.rel_dev_pct` | Setpoint'e gore yuzde sapma. |

> Setpoint'in 0 oldugu satirlarda (durus) hedef tanimsizdir; deviation NaN birakilir, sifira bolme yapilmaz.
