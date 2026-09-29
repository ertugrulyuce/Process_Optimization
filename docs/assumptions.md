# Varsayımlar Log'u

Bu dosya, veriden **türetilmeyen** ama analizde kullanılan her kabulü kayıt altına alır.
Proje prensibi: *"Varsayımlar gerçek veriden ayrı tutulacak."*

Her varsayım, yanlış çıkması hâlinde neyi geçersiz kılacağıyla birlikte yazılır.

> **Konum notu:** Bu dosya `docs/` altında, çünkü **elle yazılıyor** — hiçbir script
> onu üretmiyor. `reports/` altındaki her şey script çıktısıdır ve yeniden
> üretilebilir; bu dosya değil. (Bir kez `reports/` altındayken pipeline temizliğinde
> silindi; ayrımın nedeni bu.)

---

## A1 — `.C.` = Controlled, `.U.` = Uncontrolled

**Kabul:** Kolon adındaki `.C.` eki değişkenin operatör tarafından ayarlanabilir
(setpoint verilebilir) olduğunu, `.U.` eki ise yalnızca ölçüldüğünü gösterir.

**Durum:** ⚠️ **AÇIK — doğrulanamadı.** İki yol da denendi:

- *Dokümantasyon:* Kaggle dataset sayfası, `awesome-industrial-datasets` kaydı ve
  dataseti kullanan yayınlar tarandı. Hiçbiri `.C.`/`.U.` ekini açıklamıyor.
  Veri Liveline Technologies'in 2019'da Detroit yakınındaki bir hattından; kolon
  adlandırması firmanın iç konvansiyonu ve yayınlanmamış görünüyor.
- *Ampirik:* Davranışsal test denendi (`src/data_processing/verify_a1.py`) —
  **sonuçsuz.** `.C.Actual` bir setpoint değil, kontrollü değişkenin gerçekleşen
  ölçümü olduğu için "sabit kalma" beklentisi baştan hatalıydı; ayrıca kullanılan
  `hold_ratio` metriği kontrol edilebilirliği değil sensör güncelleme frekansını
  ölçüyordu.

**Kalan dayanak:** Domain bilgisi. Bir ekstrüderde bölge sıcaklıkları ve vida devri
ayarlanır; motor amperajı ve malzeme basıncı bunların sonucudur. Sınıflandırma 116
kolonun tamamını `unknown` bırakmadan, fiziksel olarak tutarlı biçimde ayırıyor.

**Yanlışsa ne olur:** Faz 4'ün karar değişkeni seti komple değişir. Optimizasyon,
gerçekte ayarlanamayan bir parametre için "optimum değer" önerebilir — sonuç
uygulanamaz olur. **Bu, projedeki en yüksek etkili tek varsayımdır.**

**Nasıl ele alınacak:** Doğrulanamadığı için *yok sayılmayacak, sınırı ölçülecek.*
Faz 4'te karar değişkeni seti daraltılıp genişletilerek duyarlılık analizi yapılacak.
Sonuç bu varsayıma duyarlıysa, bu bulgunun kendisi raporlanacak.

---

## A2 — Output ölçümlerindeki tam sıfırlar eksik veridir

**Kabul:** `Stage*.Output.Measurement*.U.Actual` kolonlarındaki `0.0` değerleri
gerçek ölçüm değil, sensör dropout / ölçüm alınmaması durumudur; NaN'a çevrilir.

**Dayanak:** Setpoint'i 2.74 olan bir boyutun %95 oranında tam olarak 0 olması
fiziksel değil. Sıfırlar tek bir duruş bloğunda toplanmamış, yüzlerce kısa kesinti
hâlinde dağılmış (`Stage1.M14` → 673 ayrı kesinti).

**Yanlışsa ne olur:** Sıfırlar gerçek üretim durumuysa, onları atmak proses
davranışının bir kısmını gizler. Ancak sıfır olarak modele sokmak deviation KPI'sını
kesinlikle bozar — bu yüzden atmak daha az riskli.

---

## A3 — Modellenebilirlik eşiği %50

**Kabul:** Geçerli (sıfır olmayan) veri oranı %50'nin altındaki output'lar kapsam
dışı bırakılır. Elenenler: `Stage1.M5`, `Stage1.M7`, `Stage1.M11`, `Stage2.M4`.

**Dayanak:** Bu oranın altında, hesaplanan deviation KPI'sı serinin kendisinden çok
dropout desenini ölçer.

**Yanlışsa ne olur:** Eşik keyfîdir; %30 veya %70 seçilebilirdi. Elenen output'lar
rapordan silinmez, "kapsam dışı" olarak gerekçesiyle listelenir.

---

## A4 — Spesifikasyon limitleri veride yoktur, varsayılacaktır

**Kabul:** Veri setinde LSL/USL yok; yalnızca setpoint var. Cp/Cpk hesaplanırken spec
limitleri varsayımsal olarak tanımlandı — setpoint ± %1 / %2 / %5, üç senaryo.

**Yanlışsa ne olur:** Cp/Cpk değerleri mutlak anlamda yorumlanamaz. Bu yüzden
capability sonuçları **output'lar arası karşılaştırma** için kullanılıyor, "proses
yeterli/yetersiz" gibi mutlak bir hükme dayanak yapılmıyor. Üç senaryo, sonucun
tolerans seçimine ne kadar duyarlı olduğunu gösteriyor.

---

## A5 — Stage 1 → Stage 2 arasındaki gecikme

**Kabul (başlangıçta):** Malzemenin Stage 1 çıkışından Stage 2 çıkışına ulaşması
zaman alır, ama bu transport delay veri setinde belirtilmemiş. Aynı satırdaki
Stage 1 ve Stage 2 ölçümleri aynı malzemeye ait olmayabilir.

**Durum: KISMEN ÇÖZÜLDÜ** (`reports/05_stage_link_report.md`). Gecikme sabit
varsayılmadı, arandı: 148 güvenilir output çiftinde çapraz korelasyon tepesi
**~270 sn**'de. Çiftlerin yalnızca %7'si lag = 0'da tepe yapıyor.

**Sınır artifaktı kontrolü:** İlk tarama 0–300 sn aralığında yapıldı ve tepeler
265 sn'de, yani üst sınıra yapışık çıktı. Aralık 900 sn'ye genişletildiğinde tepe
270 sn'de kaldı — yani gecikme gerçek, tarama artifaktı değil.

**Kalan belirsizlik:** Dağılım tek tepeli değil (250–300'de 40 çift, 500–550'de 15).
Bu, tek bir malzeme akışı yerine birden fazla yol/karışım olabileceğini
düşündürüyor. Faz 3'te tek bir sabit sayıya kilitlenilmeyecek.

---

## A6 — Veri tek bir ~4 saatlik pencereden geliyor

**Bu bir varsayım değil, ölçülmüş bir kısıttır** — ama sonuçların yorumunu
sınırladığı için burada kayıtlı: `2019-03-06 10:52` → `14:47`.

**Sonucu:** Long-term capability, vardiya etkisi, gün/hafta trendi, mevsimsellik
bu veriyle analiz edilemez. Bulunacak "optimum koşullar" yalnızca bu pencerede
gözlenen çalışma aralığı için geçerlidir ve dışına ekstrapole edilemez.

---

## A7 — Değişkenlerin efektif örnekleme frekansı farklı

**Bu da ölçülmüş bir kısıttır** (`reports/a1_verification.md`).

Bütün kolonlar 1 Hz *kaydedilmiş* ama 1 Hz *ölçülmemiş*:

| Değişken | 4 saatte değişim | Efektif periyot |
|---|---|---|
| `Machine2.RawMaterial.Property1-4` | **1** | — |
| `Machine3.RawMaterial.Property1-4` | 2 | ~2 saat |
| `Machine1.RawMaterial.Property1-4` | 4–5 | ~1 saat |
| `AmbientConditions.AmbientHumidity` | 38 | ~371 sn |
| `AmbientConditions.AmbientTemperature` | 40 | ~352 sn |
| `Machine1.Zone1Temperature` | 83 | ~170 sn |

**Sonucu:** "Gürültü değişkeni" sayılan 14 kolonun **12'si pratikte sabittir.**
Hammadde varyasyonunun etkisi bu veriyle araştırılamaz.

---

## A8 — Setpoint'in anlamlı sayılabilmesi için |setpoint| ≥ dev_std

**Kabul:** Bir output'un setpoint'i, sapmasının standart sapmasından küçükse o
setpoint gerçek bir hedef değildir; oransal KPI'ları tanımsız sayılır ve output
kapsam dışı bırakılır.

**Dayanak:** `Stage2.M6`'nın setpoint'i 0.01, `dev_std`'si 0.197 — hedef, ölçüm
gürültüsünün yirmide biri. Buna bölünce bias %5295 çıkıyordu ve output yanlışlıkla
"bias-baskın" sınıflanıyordu.

**Eşik neden 1.0:** Veriden doğruluyor. `Stage2.M6`'nın oranı **0.05**, sıradaki
output **3.79**. Arada büyük boşluk var; 1.0 ile 3.0 arası herhangi bir eşik aynı
tek output'u eler.

**Yanlışsa ne olur:** `Stage2.M6` gerçekten hedefi 0.01 olan bir ölçümse (ör. ideali
sıfır olan bir kusur sayımı), elemek yerine *mutlak* deviation ile ele almak
gerekirdi. Oransal KPI yine de geçersiz olurdu.

---

## A9 — Bias/variability sınıflandırmasında %40–60 belirsiz bandı

**Kabul:** `bias_share_pct > %60` → bias-baskın, `< %40` → variability-baskın,
arası **belirsiz** olarak işaretlenir ve kategoriye zorlanmaz.

**Dayanak:** Tek bir %50 eşiğiyle `Stage2.M7` **%51.0** ile kıl payı bias tarafına
düşüyordu. Bias'ı 0.2370, `dev_std`'si 0.2325 — bileşenler pratikte eşit. Bunu
"bias-baskın" diye raporlamak, veride olmayan bir kesinlik iddia etmek olurdu.

**Sonucu:** Belirsiz bandındaki output'lar (`Stage2.M7`, `Stage2.M8`) Faz 3'te model
üzerinden karara bağlanacak.

---

## A10 — Fiziksel olarak imkansız küçük değerler (R8)

**Kabul:** Bir ölçüm, setpoint'inin %1'inden küçükse (ama tam sıfır değilse)
fiziksel sayılmaz; NaN'a çevrilir.

**Dayanak:** Veride tam sıfır olmayan ama setpoint'in %1'inden küçük değerler var;
büyüklükleri `1e-306`'dan `0.04`'e kadar uzanıyor. 26 output'ta toplam 185 hücre;
bunların 103'ü negatif olduğu için R2'de sayılıyor, R8'e kalan **82 hücre**
(24 output). 185 hücrenin 178'i bir sıfıra en fazla 3 satır uzaklıkta, yani
dropout bloklarının içinde ya da kenarında: ölçüm değil, dropout kalıntısı.
A2'nin `== 0` testi bunları kaçırıyordu; `Stage1.M1`'in minimumu `4.4e-151` çıkıyordu.

**Eşik neden %1:** Veriden türetilmiş bir kesim değil. İlk gerekçe "artifaktlar
`1e-3`'ten küçük, gerçek ölçümler %50–150'de, %1 geniş bir boşluğa düşüyor" idi;
veride tutmadı. Eşiğin hemen altında (%0,37–0,63) ve hemen üstünde (%1,08) aynı
türden değerler var ve `Stage2.M12` ile `Stage1.M13`'te setpoint'in %1–30'u
arasında ~1.500 ölçüm kesintisiz uzanıyor.

Eşiğin savunması, sonucu belirlememesi. `02_cleaning_report.md`'deki duyarlılık
taraması eşiği `1e-4`'ten %10'a kadar kaydırıyor: `1e-4` ile %5 arasında hiçbir
output'un kapsamı ya da sınıfı değişmiyor. İlk değişiklik %10'da.

**Etkisi:** `Stage2.M8` variability-baskından "belirsiz" bandına taşındı.

**Açık soru — `Stage2.M12`'nin ilk 1.000 satırı:** Taramada %10'da sınıfı değişen
tek output M12 (variability → bias). Nedeni R8'in hedeflediği artifaktlar değil:
M12'nin setpoint'in %30'unun altındaki 372 ölçümünün 371'i ilk 1.000 satırda ve
M12'nin yüksek `dev_std`'sini bu dönem taşıyor. Bu dönemin bir devreye alma geçişi
mi yoksa gerçek proses mi olduğu ayrı bir karar; R8 eşiğiyle çözülmemeli.

---

## A11 — I-MR kontrol grafiği bu veri için geçerli değil

**Bu bir varsayım değil, test edilip reddedilmiş bir yöntemdir** — kayıtta duruyor
çünkü standart SPC akışının neden uygulanmadığını açıklıyor.

I-MR grafiği ardışık gözlemlerin bağımsız olduğunu varsayar. Bu veride lag-1
otokorelasyon 0.93–0.99. Sonuç: `MR_bar` küçük çıkıyor → `sigma_st` düşük tahmin
ediliyor → kontrol limitleri gereğinden dar → medyan out-of-control oranı **%41.8**
(kararlı bir proseste ~%0.3 beklenir).

**Sonucu:** Kararlılık hükmü askıya alındı. Doğru araç, Faz 3'te model kurulduktan
sonra artıklar üzerinde kontrol grafiği (residual chart) veya EWMA/CUSUM olacak.
