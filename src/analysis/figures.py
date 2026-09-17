"""
Faz 2 - Gorseller.

reports/figures/ altina PNG uretir. Her figur bir bulguyu tasir; suslemek icin
grafik cizilmez.

Renk kullanimi: kategorik slotlar sabit sirayla atanir (blue -> orange -> aqua),
asla dondurulmez. Scatter'lar tum ciftleri ayni anda gosterdigi icin en fazla
3 kategori kullanilir -- ilk uc slot bu kosulda dogrulanmis olan settir.

Calistirma:  python src/analysis/figures.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "reports" / "figures"
PROC = ROOT / "data" / "processed" / "clean_v1.csv"

# --- dogrulanmis kategorik slotlar, sabit sirada ---
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"      # blue, orange, aqua
SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8983"
GRID = "#e3e2dd"

ROLE_COLOR = {"bias": C2, "variability": C1, "belirsiz": C3}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "text.color": INK, "xtick.color": INK2, "ytick.color": INK2,
    "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.grid": True, "axes.axisbelow": True,
    "font.size": 9, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 2, "figure.dpi": 130,
})


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / name
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print(f"  {p.relative_to(ROOT)}")
    return p


def fig_bias_vs_variability(kpi):
    """Faz 1'in ana bulgusu: hata iki farkli tipte."""
    ins = kpi[kpi.in_scope == "evet"]
    fig, ax = plt.subplots(figsize=(7, 5))
    for et in ("bias", "variability", "belirsiz"):
        sub = ins[ins.error_type == et]
        ax.scatter(sub.bias.abs(), sub.dev_std, s=70, alpha=0.9,
                   color=ROLE_COLOR[et], edgecolor=SURFACE, linewidth=1.5,
                   label=f"{et} ({len(sub)})", zorder=3)
    # Her iki eksen de log: y=x referans cizgisinin gecerli olmasi icin
    # olceklerin ayni olmasi sart. (Ilk surumde x log / y lineerdi ve cizgi
    # geometrik olarak yanlis yerdeydi.)
    lo = min(ins.bias.abs().min(), ins.dev_std.min()) * 0.6
    hi = max(ins.bias.abs().max(), ins.dev_std.max()) * 1.6
    ax.plot([lo, hi], [lo, hi], color=MUTED, linewidth=1, linestyle="--",
            zorder=1)
    # etiketi cizginin geometrik ortasina koy (log olcekte sqrt), boylece
    # baslikla cakismaz
    mid = (lo * hi) ** 0.5
    ax.annotate("bias = dev_std", xy=(mid, mid), color=MUTED, fontsize=8,
                ha="center", va="bottom", rotation=45,
                rotation_mode="anchor")
    # sadece uc noktalari etiketle; cakismayi onlemek icin yon degistir
    marked = pd.concat([ins.nlargest(3, "bias"), ins.nlargest(2, "dev_std")])
    marked = marked.drop_duplicates("output")
    for i, (_, r) in enumerate(marked.iterrows()):
        dx, dy = (7, 4) if i % 2 == 0 else (7, -11)
        ax.annotate(r.output, (abs(r.bias), r.dev_std), fontsize=8,
                    color=INK2, xytext=(dx, dy), textcoords="offset points")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("abs(bias)  -  merkezleme hatasi  (log)")
    ax.set_ylabel("dev_std  -  yayilim  (log)")
    ax.set_title("Hata iki farkli tipte: merkezleme mi, yayilim mi?")
    ax.legend(frameon=False, loc="upper left")
    fig.text(0.5, -0.02,
             "Cizginin sag/alt tarafi bias-baskin (ayar problemi); sol/ust tarafi "
             "variability-baskin (kontrol problemi).\nHer iki eksen log ve olcekler "
             "esit, boylece 45 derecelik cizgi gercekten bias = dev_std demek.",
             ha="center", fontsize=8, color=MUTED)
    return save(fig, "01_bias_vs_variability.png")


def fig_control_charts(df, kpi):
    """Iki ornek: bias-baskin ve variability-baskin bir output."""
    ins = kpi[kpi.in_scope == "evet"]
    a = ins[ins.error_type == "bias"].nlargest(1, "bias_share_pct").iloc[0]
    b = ins[ins.error_type == "variability"].nlargest(1, "dev_std").iloc[0]

    fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    for ax, row, color in zip(axes, (a, b), (C2, C1)):
        st, m = row.output.split(".")
        col = f"{st}.Output.Measurement{m[1:]}.U.Actual"
        y = df[col]
        ax.plot(df.seq, y, color=color, linewidth=0.9, zorder=3)
        mu = y.mean()
        ax.axhline(row.setpoint, color=INK, linewidth=1.5, zorder=4)
        ax.axhline(mu, color=MUTED, linewidth=1.2, linestyle="--", zorder=4)
        # Etiketler sola: sagda setpoint ile ortalama cizgileri birbirine cok
        # yakin oldugunda ust uste biniyordu.
        ax.annotate(f"setpoint {row.setpoint}", xy=(len(df) * 0.01, row.setpoint),
                    color=INK, fontsize=8, ha="left", va="bottom",
                    backgroundcolor=SURFACE)
        ax.annotate(f"ortalama {mu:.2f}", xy=(len(df) * 0.30, mu),
                    color=MUTED, fontsize=8, ha="left", va="top",
                    backgroundcolor=SURFACE)
        # Y sinirlari veriye gore: 0'dan baslatmak yayilimi gorunmez kiliyordu.
        lo = min(float(y.min()), row.setpoint)
        hi = max(float(y.max()), row.setpoint)
        pad = (hi - lo) * 0.12
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_title(f"{row.output} - {row.error_type}-baskin "
                     f"(bias payi %{row.bias_share_pct}, dev_std {row.dev_std})",
                     loc="left")
        ax.set_ylabel("olcum")
    axes[-1].set_xlabel("satir sirasi (1 Hz, ~3.9 saat)")
    fig.suptitle("Ayni proses, iki farkli problem", y=0.98, fontsize=12,
                 fontweight="bold")
    fig.text(0.5, -0.02, "Ustte: seri dar ama hedefin uzaginda -> setpoint ayari. "
             "Altta: seri hedefte ama genis -> proses kontrolu.",
             ha="center", fontsize=8, color=MUTED)
    fig.tight_layout()
    return save(fig, "02_control_charts.png")


def fig_neff_effect(corr):
    """Neden ham korelasyona guvenilmez."""
    fig, ax = plt.subplots(figsize=(7, 5))
    for lab, mask, color in (
            ("FDR sonrasi anlamli", corr.sig_fdr, C1),
            ("anlamsiz", ~corr.sig_fdr, C2)):
        sub = corr[mask]
        ax.scatter(sub.r.abs(), sub.n_eff, s=26, alpha=0.75, color=color,
                   edgecolor=SURFACE, linewidth=0.6,
                   label=f"{lab} ({len(sub)})", zorder=3)
    ax.axhline(30, color=MUTED, linewidth=1, linestyle="--", zorder=2)
    ax.annotate("n_eff = 30  (altinda hukum verilmez)", xy=(0.02, 33),
                color=MUTED, fontsize=8, backgroundcolor=SURFACE)
    ax.set_yscale("log")
    ax.set_xlabel("abs(r)  -  ham korelasyon buyuklugu")
    ax.set_ylabel("n_eff  -  efektif bagimsiz gozlem (log)")
    ax.set_title("Yuksek korelasyon, az kanit")
    ax.legend(frameon=False, loc="upper right")
    fig.text(0.5, -0.03,
             "Sag altta yogunlasan noktalar: guclu gorunen ama cok az bagimsiz "
             "gozleme dayanan iliskiler.\nHam n = 14.088 kullanilsaydi hepsi "
             "'anlamli' cikardi.",
             ha="center", fontsize=8, color=MUTED)
    return save(fig, "03_neff_effect.png")


def fig_transport_delay(link):
    """Stage1 -> Stage2 gecikme dagilimi."""
    rel = link[link.reliable]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bins = np.arange(0, 950, 50)
    ax.hist(rel.best_lag, bins=bins, color=C1, edgecolor=SURFACE, linewidth=1.2,
            zorder=3)
    mode = rel.best_lag.mode().iloc[0]
    ax.axvline(mode, color=C2, linewidth=2, zorder=4)
    ax.annotate(f"en sik tepe: {int(mode)} sn", xy=(mode, ax.get_ylim()[1] * 0.9),
                color=C2, fontsize=9, ha="left", xytext=(8, 0),
                textcoords="offset points", fontweight="bold")
    ax.set_xlabel("Stage1 -> Stage2 gecikmesi (saniye)")
    ax.set_ylabel("tepe yapan output cifti")
    ax.set_title("Transport delay: capraz korelasyon tepelerinin dagilimi")
    fig.text(0.5, -0.06,
             "Ilk tarama 0-300 sn idi ve tepeler sinira yapisikti; aralik 900 sn'ye "
             "acildiginda tepe yerinde kaldi.\nYani gecikme gercek, tarama "
             "artifakti degil.", ha="center", fontsize=8, color=MUTED)
    return save(fig, "04_transport_delay.png")


def fig_skill(res):
    """
    Faz 3'un ozeti: modeller hangi baseline'i geciyor?

    Iki panel ayni output'lari gosterir; solda optimizasyon sorusu (S1),
    sagda izleme sorusu (S2). Ayrim gorsel olarak okunabilsin diye.
    """
    # sharey KULLANILMAZ: her panel kendi siralamasina sahip; paylasilan y
    # ekseni sag panelin cubuklarini sol panelin etiketleriyle eslestirirdi.
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5.8))
    panels = [("controlled", "S1 — sadece karar degiskenleri\n(optimizasyon sorusu)"),
              ("ctrl+lag", "S2 — gecmis degerler dahil\n(izleme sorusu)")]

    for ax, (fs, title) in zip(axes, panels):
        sub = res[res.feature_set == fs]
        if sub.empty:
            continue
        best = sub.loc[sub.groupby("output").skill_vs_pers.idxmax()]
        best = best.sort_values("skill_vs_pers")
        y = np.arange(len(best))
        colors = [C1 if v > 0 else C2 for v in best.skill_vs_pers]
        ax.barh(y, best.skill_vs_pers.clip(lower=-1.2), color=colors,
                edgecolor=SURFACE, linewidth=1.2, height=.74, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels(best.output, fontsize=7.5)
        ax.set_ylim(-.8, len(best) - .2)
        ax.axvline(0, color=INK, linewidth=1.4, zorder=4)
        ax.set_xlim(-1.25, .6)
        ax.set_title(title, loc="left", fontsize=10)
        ax.set_xlabel("beceri skoru (persistence'a gore)")
        n_pos = int((best.skill_vs_pers > 0).sum())
        ax.annotate(f"{n_pos} / {len(best)} output\npersistence'i geciyor",
                    xy=(.97, .03), xycoords="axes fraction", ha="right",
                    va="bottom", fontsize=8.5, color=INK2,
                    backgroundcolor=SURFACE)
        ax.annotate("← baseline'dan kotu", xy=(.03, .97), xycoords="axes fraction",
                    ha="left", va="top", fontsize=8, color=MUTED,
                    backgroundcolor=SURFACE)
    fig.suptitle("Model, \"onceki degeri tekrarla\"yi gecebiliyor mu?",
                 fontsize=12, fontweight="bold", y=.98)
    fig.text(0.5, -0.03,
             "Sifirin solunda kalan her cubuk, modelin hicbir sey ogrenmemis bir "
             "baseline'dan daha kotu oldugu anlamina gelir.\nS1'de karar "
             "degiskenleri yetersiz; S2'deki basari gecmis degerlerden geliyor ve "
             "optimizasyona cevrilemez.",
             ha="center", fontsize=8, color=MUTED)
    fig.tight_layout()
    return save(fig, "05_skill_scores.png")


def main():
    df = pd.read_csv(PROC)
    kpi = pd.read_csv(ROOT / "reports" / "output_kpi_summary.csv")
    corr = pd.read_csv(ROOT / "reports" / "correlation_table.csv")
    link = pd.read_csv(ROOT / "reports" / "stage_link_table.csv")

    print("uretilen figurler:")
    fig_bias_vs_variability(kpi)
    fig_control_charts(df, kpi)
    fig_neff_effect(corr)
    fig_transport_delay(link)

    # Faz 3 ciktisi varsa onun figuru de uretilir
    res_path = ROOT / "reports" / "modeling_results.csv"
    if res_path.exists():
        fig_skill(pd.read_csv(res_path))


if __name__ == "__main__":
    main()
