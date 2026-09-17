"""
Faz 5 - Endustriyel Yorum ve Veri Toplama Onerisi.

Faz 4 gosterdi ki bu veriden guclu bir optimizasyon onerisi cikmiyor; Faz 5
validation bunu daha da zayiflatti. Bu scriptin isi, o olumsuz sonucu
**uygulanabilir bir oneriye** cevirmek.

Iki soru cevaplaniyor:

  1. Mevcut veriden ne onerilebilir? (dusuk guvenli, sinirli)
  2. Optimizasyonun onunu ne acar? -- ve **ne kadar veri gerekir?**

Ikincisi hesaplanabilir bir sorudur ve bu scriptin asil katkisi odur:
gozlenen etki buyuklugu + bagimsiz gozlem maliyeti -> gereken deney buyuklugu.

Calistirma:  python src/analysis/recommendations.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "modeling"))
sys.path.insert(0, str(ROOT / "src" / "data_processing"))
import schema  # noqa: E402
import splits  # noqa: E402

PROC = ROOT / "data" / "processed" / "clean_v1.csv"
OUT = ROOT / "reports" / "09_recommendations.md"

CV_ACTIVE = 1.0
# Iki grup karsilastirmasi, guc 0.80, alfa 0.05 (iki yonlu):
#   n_per_group ~= 16 / d^2      (Cohen'in pratik yaklasimi)
POWER_CONST = 16
SAMPLING_HZ = 1.0


def observed_effects(df, cpps, targets):
    """Her CPP x output icin gozlenen standardize etki buyuklugu (Cohen d)."""
    rows = []
    for c in cpps:
        try:
            q = pd.qcut(df[c], 4, duplicates="drop")
        except ValueError:
            continue
        for t in targets:
            dev = df[f"{t}.dev"]
            g = dev.abs().groupby(q, observed=True).agg(["mean", "count"])
            g = g[g["count"] >= 150]
            if len(g) < 2:
                continue
            lo, hi = float(g["mean"].min()), float(g["mean"].max())
            sd = float(dev.std())
            if not sd:
                continue
            rows.append(dict(
                parametre=c.replace(".C.Actual", "")
                           .replace("FirstStage.CombinerOperation", "Combiner"),
                output=t,
                fark=round(hi - lo, 5),
                seri_std=round(sd, 5),
                cohen_d=round((hi - lo) / sd, 4)))
    return pd.DataFrame(rows)


def required_experiment(d, block_len, n_levels=2):
    """
    Verilen etki buyuklugu icin gereken bagimsiz gozlem ve sure.

    Iki senaryo:
      - GOZLEMSEL: bagimsiz gozlem = bir otokorelasyon blogu (block_len satir).
        Proses kendi haline birakilir, veri birikmesi beklenir.
      - DENEYSEL (DOE): her kosul bilincli olarak ayarlanir. Ayar degisimi
        otokorelasyonu kirar, dolayisiyla her run bir bagimsiz gozlemdir.
        Run suresi = prosesin yeni ayarda dengelenme suresi (transport delay
        mertebesinde alindi).
    """
    if not d or np.isnan(d) or d <= 0:
        return None
    n_per_group = POWER_CONST / (d ** 2)
    total_obs = n_per_group * n_levels

    obs_rows = total_obs * block_len
    obs_hours = obs_rows / SAMPLING_HZ / 3600

    # DOE: her run bagimsiz; run suresi ~ dengelenme + olcum
    run_seconds = 300          # K13: transport delay ~270 sn + pay
    doe_hours = total_obs * run_seconds / 3600
    return dict(cohen_d=round(d, 4),
                n_per_group=int(np.ceil(n_per_group)),
                toplam_gozlem=int(np.ceil(total_obs)),
                gozlemsel_saat=round(obs_hours, 1),
                doe_saat=round(doe_hours, 1))


def main():
    df = pd.read_csv(PROC)
    kpi = pd.read_csv(ROOT / "reports" / "output_kpi_summary.csv")
    res = pd.read_csv(ROOT / "reports" / "modeling_results.csv")
    fold = pd.read_csv(ROOT / "reports" / "validation_folds.csv")

    dvs = [c for c in schema.decision_variables(df.columns) if c in df.columns]
    cpps = [c for c in dvs if 100 * df[c].std() / df[c].mean() >= CV_ACTIVE]
    block_len = splits.suggest_embargo(df, cpps)

    s1 = res[res.feature_set == "controlled"]
    best = s1.loc[s1.groupby("output").skill_vs_pers.idxmax()]
    targets = list(best[best.skill_vs_pers > 0].output)

    eff = observed_effects(df, cpps, targets)
    write_report(df, kpi, eff, fold, cpps, block_len, targets)
    eff.to_csv(ROOT / "reports" / "effect_sizes.csv", index=False)
    print(f"yazildi: {OUT}")
    print(f"aktif CPP: {len(cpps)} | blok uzunlugu: {block_len} satir")
    if not eff.empty:
        print(f"medyan Cohen d: {eff.cohen_d.median():.4f}  "
              f"(en buyuk {eff.cohen_d.max():.4f})")


def write_report(df, kpi, eff, fold, cpps, block_len, targets):
    L = []
    w = L.append
    ins = kpi[kpi.in_scope == "evet"]

    w("# Faz 5 - Endustriyel Yorum ve Veri Toplama Onerisi\n")
    w("Uretildi: `python src/analysis/recommendations.py`\n")
    w("Faz 4 bu veriden guclu bir optimizasyon onerisi cikmadigini gosterdi;")
    w("Faz 5 validation (V1) bunu daha da zayiflatti. Bu rapor o olumsuz sonucu")
    w("**uygulanabilir bir oneriye** cevirir.\n")

    # ---- 1. Guven derecelendirmesi ----
    w("## 1. Bulgularin guven derecesi\n")
    w("Her bulgu, hangi kanita dayandigi ve validation'dan nasil ciktigina gore")
    w("derecelendirildi. **Yuksek guvenli bulgular proses parametresi degil,")
    w("veri kalitesi ve olcum sistemiyle ilgili olanlar.**\n")
    w("| # | Bulgu | Guven | Neden |")
    w("|---|---|---|---|")
    w("| 1 | `Machine4.Temperature4` = `Machine4.Pressure` (ozdes kolon) | "
      "**yuksek** | 14.088 satirin tamaminda birebir; yorum gerektirmiyor |")
    w("| 2 | Output'larin %19'u sensor dropout (sifir/underflow) | "
      "**yuksek** | dogrudan sayim, model yok |")
    w("| 3 | 14 output bias-baskin, 9 variability-baskin | "
      "**yuksek** | dogrudan hesap; bias/variability ayrisimi kararli |")
    w("| 4 | Rastgele split R2 0.97 -> dogru split -6.89 | "
      "**yuksek** | tekrarlanabilir, yontemsel |")
    w("| 5 | Karar degiskenleri deviation'i aciklamiyor | "
      "**yuksek** | hem dogrusal hem dogrusal olmayan modellerde |")
    w("| 6 | Stage1 -> Stage2 gecikme ~270 sn | "
      "**orta** | 150 ciftte tepe; dagilim tek tepeli degil |")
    w("| 7 | `Machine4.Pressure` 14-17 daha iyi | "
      "**dusuk** | V2: zaman parcalarinin %57'sinde tutuyor |")
    w("| 8 | 5 output'ta model persistence'i geciyor | "
      "**cok dusuk** | V1: walk-forward'da hicbiri tum fold'larda pozitif degil |")
    w("")
    w("> **Bu tablo projenin en durust ciktisi.** Bir bulguyu \"guclu\" diye")
    w("> sunmak kolay; hangi bulgunun ne kadar tasidigini soylemek zor.")
    w("> Uygulama kararlari 1-5 arasindaki bulgulara dayandirilmali;")
    w("> 7 ve 8 numarali bulgular **aksiyon dayanagi degildir.**\n")

    # ---- 2. Aksiyon tablosu ----
    w("## 2. Onerilen aksiyonlar\n")
    w("Format: Bulgu -> Muhendislik yorumu -> Aksiyon -> Beklenen etki -> Risk\n")

    bias_top = ins[ins.error_type == "bias"].reindex(
        ins[ins.error_type == "bias"].bias_pct.abs().sort_values(
            ascending=False).index).head(3)

    w("### A1 — Bias-baskin output'larda setpoint/kalibrasyon gozden gecirilsin\n")
    w("**Bulgu:** 25 kapsam ici output'un 14'unde hatanin %60'tan fazlasi")
    w("merkezleme kaymasindan geliyor. En uclar:\n")
    for _, r in bias_top.iterrows():
        w(f"- `{r.output}`: hedef {r.setpoint}, gerceklesen sapma "
          f"{r.bias:+.3f} (**%{r.bias_pct:+.1f}**)")
    w("")
    w("**Muhendislik yorumu:** Proses bu output'larda *kararli* ama *yanlis")
    w("noktada* calisiyor. Dagilim dar; sorun yayilim degil merkez. Bu, proses")
    w("parametresi oynatarak duzeltilecek bir sey degil -- ya setpoint yanlis")
    w("girilmis, ya olcum sistemi kaymis (kalibrasyon), ya da hedef degeri")
    w("gercekci degil.\n")
    w("**Aksiyon:** Bu 14 output icin setpoint kaydi ve olcum cihazi")
    w("kalibrasyonu kontrol edilsin. Once `Stage1.M1` ve `Stage2.M1` -- ikisi de")
    w("hedefin ~%40 altinda ve hatalarinin %98'i bias.\n")
    w("**Beklenen etki:** Kalibrasyon kaymasiysa dogrudan ve buyuk; ayar")
    w("hatasiysa aninda. **Bu, projenin en yuksek getirili onerisidir** cunku")
    w("model gerektirmiyor ve etki buyuklugu dogrudan olculmus.\n")
    w("**Risk:** Dusuk. Ancak hedef degerlerin neden o sekilde belirlendigi")
    w("bilinmiyor; %40'lik sapma kasitli bir uretim tercihi de olabilir. Once")
    w("proses sahibine sorulmali.\n")

    w("### A2 — Sensor dropout'u giderilsin\n")
    w("**Bulgu:** Output olcum hucrelerinin **%18.6**'si gecersiz: 78.539 tam")
    w("sifir + 185 float-underflow degeri (`1e-100` mertebesinde) + 126 negatif.")
    w("`Stage1.M5` gecerli verisinin yalnizca %4.6'sina sahip.\n")
    w("**Muhendislik yorumu:** Sifirlar tek bir durus blogunda degil, yuzlerce")
    w("kisa kesinti halinde (`Stage1.M14` -> 673 ayri kesinti). Bu bir uretim")
    w("durusu deseni degil, **olcum sistemi guvenilirligi** sorunudur.")
    w("Underflow degerleri ise veri toplama zincirinde bir sayisal hataya")
    w("isaret ediyor -- gercek bir olcum `1e-306` olamaz.\n")
    w("**Aksiyon:** 4 output (`Stage1.M5/M7/M11`, `Stage2.M4`) analiz disi")
    w("kaldi. Bu sensorlerin bakimi/degisimi olmadan o olcumler hakkinda hicbir")
    w("sey soylenemez. Underflow icin veri toplama yazilimi incelensin.\n")
    w("**Beklenen etki:** Analiz kapsamini 25'ten 29 output'a cikarir.\n")
    w("**Risk:** Yok. Veri kalitesi duzeltmesi.\n")

    w("### A3 — Ozdes kolon cifti duzeltilsin\n")
    w("**Bulgu:** `Machine4.Temperature4` ile `Machine4.Pressure` 14.088 satirin")
    w("tamaminda birebir ayni. Deger araligi (14-25) diger Machine 4")
    w("sicakliklariyla (260-396) uyumsuz, basincla uyumlu.\n")
    w("**Muhendislik yorumu:** Bir etiketleme/kopyalama hatasi. Ya iki tag ayni")
    w("kaynagi okuyor ya da biri yanlis adlandirilmis.\n")
    w("**Aksiyon:** Historian tag esleme tablosu kontrol edilsin.\n")
    w("**Risk:** Yok — ama **duzeltilmezse** bu cift her modelde yapay")
    w("multicollinearity ve sisirilmis feature importance uretir.\n")

    w("### A4 — Sabit setpoint yerine periyodik yeniden kalibrasyon\n")
    w("**Bulgu (V3):** 5 output'un 3'unde, 4 saatlik pencere icindeki pencere")
    w("ortalamalari arasi kayma, serinin kendi standart sapmasindan **buyuk**")
    w("(`Stage2.M9`: 2.29 sigma).\n")
    w("**Muhendislik yorumu:** Proses merkezi gurultuden daha hizli kayiyor.")
    w("Bir donemde dogru olan ayar, saatler sonra merkezi kaymis olur.\n")
    w("**Aksiyon:** \"Su degere ayarlayin\" turu sabit oneriler yerine")
    w("**periyodik yeniden merkezleme** (ornegin vardiya basi) prosedurü.\n")
    w("**Risk:** Asiri duzeltme (over-control). Kayma olcum gurultusuyle")
    w("karistirilirsa proses daha da kararsizlasir. Yeniden merkezleme esigi")
    w("istatistiksel olarak tanimlanmali.\n")

    # ---- 3. Neden optimize edilemedi + DOE ----
    w("## 3. Optimizasyonun onunu ne acar?\n")
    w("Bu bolum projenin en pratik ciktisidir: **veri neden yetmedi ve ne kadar")
    w("gerekir?**\n")
    w(f"Aktif CPP'lerin otokorelasyonu ~{block_len} satir (≈"
      f"{block_len/60:.0f} dakika) boyunca sonmuyor (V0). Yani 14.088 satirlik")
    w(f"veri, bu parametreler acisindan yaklasik **{len(df)//block_len} bagimsiz")
    w("blok** demek. Optimizasyonun ogrenmesi gereken kontrast burada ve orada")
    w("bir avuc gozlem var.\n")

    if not eff.empty:
        w("### Gozlenen etki buyuklukleri\n")
        w("Her CPP icin, en iyi ve en kotu dilim arasindaki farkin serinin")
        w("standart sapmasina orani (Cohen'in d'si):\n")
        agg = (eff.groupby("parametre")
                  .agg(medyan_d=("cohen_d", "median"),
                       en_buyuk_d=("cohen_d", "max"))
                  .sort_values("en_buyuk_d", ascending=False))
        w("| parametre | medyan d | en buyuk d | yorum |")
        w("|---|---|---|---|")
        for p, r in agg.iterrows():
            lab = ("cok kucuk" if r.en_buyuk_d < 0.2 else
                   "kucuk" if r.en_buyuk_d < 0.5 else
                   "orta" if r.en_buyuk_d < 0.8 else "buyuk")
            w(f"| `{p}` | {r.medyan_d:.3f} | {r.en_buyuk_d:.3f} | {lab} |")
        w("")
        w("> Etkiler **kucuk**. Kucuk etkiyi saptamak icin cok sayida bagimsiz")
        w("> gozlem gerekir; elde ~"
          f"{len(df)//block_len} tane var.\n")

        w("### Ne kadar veri gerekir?\n")
        w("Guc analizi (guc 0.80, alfa 0.05, iki seviye karsilastirmasi):\n")
        w("| senaryo | etki (d) | gereken bagimsiz gozlem | gozlemsel sure | "
          "DOE ile |")
        w("|---|---|---|---|---|")
        for label, d in (("gozlenen medyan etki", float(eff.cohen_d.median())),
                         ("gozlenen en buyuk etki", float(eff.cohen_d.max())),
                         ("orta etki (d=0.5) hedeflenirse", 0.5)):
            req = required_experiment(d, block_len)
            if req:
                w(f"| {label} | {req['cohen_d']} | {req['toplam_gozlem']:,} | "
                  f"**{req['gozlemsel_saat']:,.0f} saat** | "
                  f"**{req['doe_saat']:,.0f} saat** |")
        w("")
        w("> **BULGU N1 - Gozlemsel veri bekleyerek bu is cozulmez.** Prosesi")
        w("> kendi haline birakip veri biriktirmek, otokorelasyon nedeniyle")
        w("> saatte yalnizca ~2 bagimsiz gozlem uretiyor.")
        w(">")
        w("> **DOE ayni bilgiyi mertebe kucuk surede verir.** Fark yontemden")
        w("> geliyor: parametre bilincli olarak degistirildiginde otokorelasyon")
        w("> kirilir ve her run bagimsiz bir gozlem olur. Ayrica DOE'de")
        w("> parametreler **gozlenen dar araligin disina** cikarilabilir --")
        w("> etki buyuklugu de artar.\n")

    w("### Onerilen deney tasarimi\n")
    w(f"**{len(cpps)} faktor, 2 seviye, yarim-kesir faktoriyel "
      f"(2^{len(cpps)}⁻¹ = {2**(len(cpps)-1)} kosul)**\n")
    w("| faktor | mevcut aralik | onerilen dusuk | onerilen yuksek |")
    w("|---|---|---|---|")
    for c in cpps:
        lo, hi = float(df[c].min()), float(df[c].max())
        span = hi - lo
        w(f"| `{c.replace('.C.Actual','')}` | {lo:.2f} – {hi:.2f} | "
          f"{lo - 0.25*span:.2f} | {hi + 0.25*span:.2f} |")
    w("")
    w("> Onerilen seviyeler mevcut araligin **%25 disina** tasiyor. Bunun iki")
    w("> nedeni var: (1) etki buyuklugu aralikla birlikte buyur, (2) mevcut")
    w("> aralik zaten prosesin rahat oldugu bolge -- kontrast orada yok.")
    w(">")
    w("> **Bu seviyeler proses guvenligi ve urun kalitesi acisindan proses")
    w("> muhendisi tarafindan onaylanmadan uygulanmamalidir.** Buradaki")
    w("> oneri istatistikseldir, fiziksel fizibilite degerlendirmesi degildir.\n")
    w("Her kosu ~5 dakika (K13: transport delay ~270 sn + dengelenme payi),")
    w(f"{2**(len(cpps)-1)} kosul x 3 replikasyon = "
      f"**{2**(len(cpps)-1)*3} kosu ≈ {2**(len(cpps)-1)*3*5/60:.0f} saat**")
    w("net deney suresi.\n")

    # ---- 4. Izleme ----
    w("## 4. Izleme onerileri\n")
    w("**Control chart secimi:** Klasik I-MR grafigi bu proses icin **uygun")
    w("degil** (K10) -- otokorelasyon nedeniyle medyan out-of-control orani")
    w("%38.5 cikiyor, kararli bir proseste ~%0.3 beklenir. Yanlis alarm")
    w("operatoru grafige guvenmemeye iter.\n")
    w("Yerine: **EWMA veya CUSUM**, ya da once bir zaman serisi modeli kurup")
    w("**artiklar uzerinde** kontrol grafigi.\n")
    w("**Erken uyari:** S2 sonucu (Faz 3) burada degerli -- deviation kisa")
    w("vadede gecmis degerlerinden tahmin edilebiliyor. Bu, optimizasyon icin")
    w("kullanilamaz ama **bir sonraki periyodu ongoren erken uyari** icin")
    w("kullanilabilir.\n")
    w("**Veri toplama:** Ambient kosullari ~350 sn'de bir guncelleniyor (K4);")
    w("4 saatte ~40 bagimsiz gozlem. Bu degiskenlerin etkisi arastirilacaksa")
    w("ornekleme sikligi artirilmali veya cok daha uzun sureli veri toplanmali.\n")

    # ---- 5. Limitler ----
    w("## 5. Limitler\n")
    w("| Limit | Etkisi |")
    w("|---|---|")
    w("| Veri tek bir 3,9 saatlik pencereden | Long-term capability, vardiya "
      "ve mevsim etkisi analiz edilemez |")
    w("| Gozlemsel veri, deney degil | Hicbir bulgu nedensellik iddia edemez |")
    w("| Spec limitleri yok | Cp/Cpk mutlak yorumlanamaz, yalnizca siralama |")
    w("| `.C.`/`.U.` anlami dogrulanamadi (A1) | Karar degiskeni seti varsayima "
      "dayali; riski olculdu (K19), kapatilmadi |")
    w("| Karar degiskenleri dar aralikta | Optimizasyonun ogrenecegi kontrast yok |")
    w("| Transport delay tek tepeli degil | Stage1-Stage2 eslesmesi yaklasik |")
    w("")
    w("> **Projenin sonucu bir optimizasyon tablosu degil, bir teshis.** Proses")
    w("> mevcut haliyle zaten calistigi bolgede duruyor; iyilestirme icin gereken")
    w("> sey daha iyi bir model degil, **daha iyi tasarlanmis bir deney.**\n")

    OUT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
