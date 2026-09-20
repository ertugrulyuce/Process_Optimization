"""
KPI panosu.

Calistirma:
    pip install -r dashboard/requirements.txt
    streamlit run dashboard/app.py

Pano hicbir sayiyi yeniden hesaplamaz: reports/ altindaki commit edilmis
script ciktilarini okur. Otoriter kaynak markdown raporlardir; burasi
onlarin ozeti. Butun okuma/ozetleme data.py icinde ve testli.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from dashboard import data  # noqa: E402

FIGURES = ROOT / "reports" / "figures"

st.set_page_config(page_title="Process Optimization -- KPI ozeti", layout="wide")
st.title("Surekli Uretim Proses Optimizasyonu -- KPI ozeti")
st.caption(
    "Bu pano hicbir sayiyi yeniden hesaplamaz; `reports/` altindaki script "
    "ciktilarini okur. Otoriter kaynak markdown raporlardir."
)

try:
    tables = data.load_all()
except data.MissingReportError as exc:
    st.error(str(exc))
    st.stop()

kpi = tables["kpi"]
capability = tables["capability"]
modeling = tables["modeling"]
validation = tables["validation"]
optimization = tables["optimization"]

with st.sidebar:
    st.header("Kaynak")
    st.write("Pano su dosyalari okuyor:")
    for name, filename in sorted(data.SOURCES.items()):
        st.write(f"- `reports/{filename}`")
    st.info("Tablolar `make run` ile yeniden uretilir. Pano onlari degistirmez.")

for column, (label, value) in zip(st.columns(4),
                                  data.headline(kpi, modeling, validation).items()):
    column.metric(label, value)

kapsam, yeterlilik, model, optimizasyon = st.tabs(
    ["Kapsam ve KPI", "Capability", "Model ve validation", "Optimizasyon"])

with kapsam:
    scope = data.scope_summary(kpi)
    st.subheader("Kapsam")
    st.write(
        f"{scope['toplam']} output'un **{scope['kapsam_ici']}**'i analize giriyor. "
        f"Hata tipi dagilimi: {scope['bias']} bias-baskin, "
        f"{scope['variability']} variability-baskin, {scope['belirsiz']} belirsiz."
    )
    st.markdown(
        "Bias bir **ayar/kalibrasyon** problemi, variability bir **proses kontrol** "
        "problemi. Optimizasyonun hedefi ikinci gruptur: bias-baskin bir output'u "
        "parametre oynatarak kovalamak yanlistir, cozumu setpoint'i duzeltmektir."
    )
    st.dataframe(data.out_of_scope(kpi), width="stretch", hide_index=True)

    figure = FIGURES / "01_bias_vs_variability.png"
    if figure.exists():
        st.image(str(figure), caption="Bias ve variability ayrimi (Faz 1)")

with yeterlilik:
    st.subheader("Short-term capability")
    st.warning(
        "Veride spesifikasyon limiti YOK (A4). Cp/Cpk degerleri setpoint "
        "etrafinda varsayimsal toleranslarla hesaplandi; amac mutlak bir "
        "yeterlilik hukmu degil, output'lari ayni olcute gore siralamak."
    )
    secenekler = data.scenarios(capability)
    senaryo = st.selectbox("Tolerans senaryosu", secenekler,
                           index=secenekler.index("orta") if "orta" in secenekler else 0)
    st.dataframe(data.worst_capability(capability, senaryo, n=10),
                 width="stretch", hide_index=True)
    st.caption(
        "sigma_st = MR_bar / d2 (short-term). Otokorelasyon bu tahmini kucultur, "
        "yani kontrol limitleri gercekte olmasi gerekenden dar cikar -- ayrinti "
        "`reports/03_capability_report.md` icinde."
    )

with model:
    st.subheader("Model becerisi")
    setler = sorted(modeling.feature_set.unique())
    secilen = st.radio("Girdi seti", setler,
                       index=setler.index("controlled") if "controlled" in setler else 0,
                       horizontal=True)
    best = data.best_models(modeling, secilen)
    st.write(
        f"**{int((best.skill_vs_pers > 0).sum())} / {len(best)}** output'ta model "
        "persistence baseline'ini geciyor."
    )
    st.dataframe(best[["output", "error_type", "model", "r2",
                       "skill_vs_mean", "skill_vs_pers"]],
                 width="stretch", hide_index=True)
    st.markdown(
        "`controlled` optimizasyon sorusudur (S1): karar degiskenleri sapmayi "
        "acikliyor mu? `ctrl+lag` izleme sorusudur (S2) ve S1'in yerine gecmez -- "
        "sapmanin bir sonraki degerinin oncekine benzemesi, hangi parametrenin "
        "degistirilecegini soylemez."
    )

    st.subheader("Walk-forward tutarlilik")
    st.dataframe(data.fold_consistency(validation), width="stretch", hide_index=True)
    st.caption(
        "Fold 1 disarida: train seti digerlerinin cok altinda kaliyor. Tek "
        "bolmeye dayanan sonuclarin kirilganligi icin `reports/08_validation_report.md`."
    )

with optimizasyon:
    st.subheader("Model-tabanli optimum noktalar")
    st.warning(
        "Model R2'si negatif; bu tablo TEK BASINA dayanak degildir. Ayni soru "
        "modele guvenmeden ampirik olarak da soruldu ve iki yolun uzlasip "
        "uzlasmadigi `reports/07_optimization_report.md` icinde raporlandi."
    )
    st.dataframe(optimization, width="stretch", hide_index=True)
    st.markdown(
        "Arama uzayi her parametrede **gozlenen min-max araligiyla** sinirli "
        "(K1): ekstrapolasyon yok. Onerilen noktalar gozlemsel veriden gelir, "
        "nedensellik iddiasi tasimaz."
    )
