# -*- coding: utf-8 -*-
"""Plot Extended Data figures 1-6 and run pixel checks on all figures."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch
import pandas as pd, numpy as np, os, datetime as dt
from PIL import Image

BASE = r"local_raw_workspace"
V2 = os.path.join(BASE, "groundwater_underground_encounter_v2")
FRZ = os.path.join(BASE, "Nature_results_freeze_v1")
SRC = os.path.join(FRZ, "03_figure_source_tables")
ED = os.path.join(FRZ, "05_extended_data")
os.makedirs(ED, exist_ok=True)

MM = 1 / 25.4
plt.rcParams.update({
    "font.family": "Arial", "font.size": 6, "axes.linewidth": 0.7,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.labelsize": 5.5, "ytick.labelsize": 5.5,
    "axes.labelsize": 6.5, "pdf.fonttype": 42, "svg.fonttype": "none", "legend.fontsize": 5.2,
})
C_GW = "#1f4e79"; C_ACC = "#c8402a"
CM_ENC = LinearSegmentedColormap.from_list("enc", ["#faf7f2", "#f2b88c", "#e07b4f", "#c8402a", "#8c2318"])
CM_ENC.set_bad("#bdbdbd")
EN = {"东城区": "Dongcheng", "西城区": "Xicheng", "朝阳区": "Chaoyang", "丰台区": "Fengtai", "石景山区": "Shijingshan",
      "海淀区": "Haidian", "门头沟区": "Mentougou", "房山区": "Fangshan", "通州区": "Tongzhou", "顺义区": "Shunyi",
      "昌平区": "Changping", "大兴区": "Daxing", "怀柔区": "Huairou", "平谷区": "Pinggu", "密云区": "Miyun", "延庆区": "Yanqing"}

def save_all(fig, name):
    for ext in ("svg", "pdf", "png"):
        fig.savefig(os.path.join(ED, f"{name}.{ext}"), dpi=300 if ext == "png" else None,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)

def despine(ax):
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

def ym_to_num(s):
    return dt.date(int(s[:4]), int(s[5:7]), 15).toordinal()

# ============ ED1 selected years slopegraph ============
fig, ax = plt.subplots(figsize=(120 * MM, 90 * MM))
sl = pd.read_csv(os.path.join(SRC, "ED1_selected_years.csv"))
tjb = pd.read_csv(os.path.join(SRC, "Fig2b_trajectory_summary.csv"))
cls = dict(zip(tjb["district"], tjb["trajectory_class"]))
colmap = {"contact_reemerged": C_ACC, "persistent_contact": C_GW, "contact_lost_during_depletion": "#e07b4f",
          "intermittent_or_uncertain": "#999999", "persistent_no_contact": "#bbbbbb"}
years = [2000, 2005, 2010, 2015, 2020]
for _, r in sl.iterrows():
    c = colmap.get(cls.get(r["district"], ""), "#bbbbbb")
    ax.plot(years, [r[str(y)] for y in years], "-o", color=c, lw=0.8, ms=2.2)
    ax.text(2020.15, r["2020"], EN.get(r["district"], r["district"]), fontsize=4.6, va="center", color=c)
    if abs(r["2000"]) > 1e-9:
        ax.text(1999.85, r["2000"], EN.get(r["district"], r["district"]), fontsize=4.6, va="center", ha="right", color=c)
ax.set_xlim(1998.5, 2022.5); ax.set_ylim(-0.03, 0.55)
ax.set_xticks(years)
ax.set_ylabel("Encounter fraction C (central)")
ax.set_xlabel("Year")
despine(ax)
save_all(fig, "ExtendedData_Fig1_selected_historical_years")

# ============ ED2 MAIN vs RAW ============
fig, (axA, axB) = plt.subplots(1, 2, figsize=(180 * MM, 72 * MM), width_ratios=[1, 1.25])
hs = pd.read_csv(os.path.join(SRC, "ED2_main_raw.csv"))
axA.scatter(hs["E_index_RAW"], hs["E_index_MAIN"], s=3, c="#8c8c8c", alpha=0.5, lw=0)
lim = max(hs["E_index_MAIN"].max(), hs["E_index_RAW"].max()) * 1.05
axA.plot([0, lim], [0, lim], color=C_ACC, lw=0.8)
fsd = hs[hs["district"] == "房山区"]
axA.scatter(fsd["E_index_RAW"], fsd["E_index_MAIN"], s=4, c=C_GW, alpha=0.7, lw=0)
axA.text(0.05, 0.9, "1:1 line", transform=axA.transAxes, color=C_ACC, fontsize=5.2)
axA.text(0.35, 0.06, "Fangshan (max |ΔE| = 0.419, 2015 deep)", transform=axA.transAxes, fontsize=5.0, color=C_GW)
axA.set_xlabel("E_index, RAW snapshot backcast")
axA.set_ylabel("E_index, MAIN stock-constrained")
axA.set_xlim(0, lim); axA.set_ylim(0, lim)
despine(axA)
axA.text(-0.16, 1.05, "a", transform=axA.transAxes, fontsize=8, fontweight="bold")

fsc = fsd[fsd["depth_scenario"] == "deep"].sort_values("year")
axB.plot(fsc["year"], fsc["E_index_MAIN"], color=C_GW, lw=1.0, label="MAIN")
axB.plot(fsc["year"], fsc["E_index_RAW"], color=C_GW, lw=1.0, ls=(0, (3, 1.6)), label="RAW")
axB.fill_between(fsc["year"], fsc["E_index_RAW"], fsc["E_index_MAIN"], color=C_GW, alpha=0.12, lw=0)
axB.legend(frameon=False, loc="upper left")
axB.set_xlabel("Year"); axB.set_ylabel("E_index, Fangshan deep")
axB.set_xlim(2000, 2020)
despine(axB)
axB.text(-0.13, 1.05, "b", transform=axB.transAxes, fontsize=8, fontweight="bold")
fig.subplots_adjust(left=0.075, right=0.98, top=0.96, bottom=0.14, wspace=0.25)
save_all(fig, "ExtendedData_Fig2_MAIN_vs_RAW_sensitivity")

# ============ ED3 small multiples 16 districts ============
fig = plt.figure(figsize=(180 * MM, 150 * MM))
gs = fig.add_gridspec(4, 4, left=0.055, right=0.985, top=0.955, bottom=0.06, hspace=0.62, wspace=0.38)
sm = pd.read_csv(os.path.join(SRC, "ED3_small_multiples.csv"))
sm["x"] = sm["year_month"].map(ym_to_num)
prof = pd.read_csv(os.path.join(SRC, "ED6_depth_area_profiles.csv"))
order16 = sm[sm["year_month"] == "2025-12"].sort_values("encounter_fraction", ascending=False)["district"].tolist()
for i, d in enumerate(order16):
    ax = fig.add_subplot(gs[i // 4, i % 4])
    g = sm[sm["district"] == d].sort_values("x")
    ltp = prof[(prof["district"] == d) & (prof["layer_fraction"] > 1e-9)]
    ax.fill_between(g["x"], g["groundwater_depth_m"], g["groundwater_depth_m"].max() * 1.15,
                    where=g["encounter_fraction"] > 1e-9, color=C_ACC, alpha=0.16, lw=0, interpolate=True)
    ax.plot(g["x"], g["groundwater_depth_m"], color=C_GW, lw=0.8)
    for _, r in ltp.iterrows():
        ax.axhline(r["representative_depth_m"], color="#cccccc", lw=0.4, zorder=1)
    ax.set_ylim(g["groundwater_depth_m"].max() * 1.15, g["groundwater_depth_m"].min() * 0.5)
    ax.set_xlim(g["x"].min() - 10, g["x"].max() + 10)
    ax.set_xticks([ym_to_num(f"{y}-01") for y in [2020, 2022, 2024]])
    ax.set_xticklabels(["2020", "2022", "2024"], fontsize=4.6)
    ax.tick_params(axis="y", labelsize=4.6)
    ax.set_title(EN.get(d, d), fontsize=5.4, fontweight="bold", loc="left", pad=1.5)
    despine(ax)
fig.supylabel("Groundwater depth (m, b.g.l.; inverted)", fontsize=6, x=0.012)
save_all(fig, "ExtendedData_Fig3_all_threshold_small_multiples")

# ============ ED4 robustness with 2026 YTD ============
fig, (axA, axB) = plt.subplots(1, 2, figsize=(180 * MM, 66 * MM), width_ratios=[1.6, 1])
f5a = pd.read_csv(os.path.join(SRC, "Fig5a_robustness.csv"))
vals = [float(f5a[f5a["class"] == c]["fraction"].iloc[0]) for c in ["robust_no_contact", "depth_sensitive_contact", "robust_contact"]]
labs = ["Robust no contact", "Depth-sensitive", "Robust contact"]
cols = ["#d9d9d9", "#f2b88c", "#c8402a"]
left = 0
for v, lb, cc in zip(vals, labs, cols):
    axA.barh([0], [v], left=left, color=cc, height=0.42, edgecolor="white", lw=0.6)
    txtc = "white" if cc == "#c8402a" else "#333333"
    axA.text(left + v / 2, 0, f"{lb}\n{v*100:.1f}%", ha="center", va="center", fontsize=5.0, color=txtc)
    left += v
axA.set_xlim(0, 1); axA.set_ylim(-0.5, 0.6); axA.set_yticks([])
axA.set_xticks([0, 0.5, 1.0]); axA.set_xticklabels(["0", "50", "100%"], fontsize=5.2)
axA.set_xlabel("Main window Sep 2019 – Dec 2025 (n = 1,193)", fontsize=5.5)
axA.spines["left"].set_visible(False); despine(axA)
axA.text(-0.10, 1.08, "a", transform=axA.transAxes, fontsize=8, fontweight="bold")

ytd = pd.read_csv(os.path.join(SRC, "ED4_robustness_2026ytd.csv"))
tot = ytd["count_2026ytd"].sum()
vc = dict(zip(ytd["class"], ytd["count_2026ytd"]))
v2 = [vc.get("robust_no_contact", 0) / tot, vc.get("depth_sensitive_contact", 0) / tot, vc.get("robust_contact", 0) / tot]
left = 0
for v, lb, cc in zip(v2, labs, cols):
    axB.barh([0], [v], left=left, color=cc, height=0.42, edgecolor="white", lw=0.6)
    txtc = "white" if cc == "#c8402a" else "#333333"
    axB.text(left + v / 2, 0, f"{v*100:.1f}%", ha="center", va="center", fontsize=5.0, color=txtc)
    left += v
axB.set_xlim(0, 1); axB.set_ylim(-0.5, 0.6); axB.set_yticks([])
axB.set_xticks([0, 0.5, 1.0]); axB.set_xticklabels(["0", "50", "100%"], fontsize=5.2)
axB.set_xlabel("2026 YTD (n = 144; excluded from main text)", fontsize=5.5)
axB.spines["left"].set_visible(False); despine(axB)
axB.text(-0.10, 1.08, "b", transform=axB.transAxes, fontsize=8, fontweight="bold")
fig.subplots_adjust(left=0.05, right=0.985, top=0.90, bottom=0.16, wspace=0.22)
save_all(fig, "ExtendedData_Fig4_robustness_with_2026YTD")

# ============ ED5 groundwater QC ============
fig, (axA, axB) = plt.subplots(1, 2, figsize=(180 * MM, 100 * MM), width_ratios=[1.1, 1])
rg = pd.read_csv(os.path.join(SRC, "ED5_gw_qc.csv"))
rg["x"] = rg["year_month"].map(ym_to_num)
order_q = [d for d in order16 if d in rg["district"].unique()]
cmap_qc = {"ok": "#dce6f1", "missing": "#bdbdbd", "support_change": "#f2b88c"}
for i, d in enumerate(order_q):
    g = rg[rg["district"] == d]
    axA.hlines(i, g["x"].min(), g["x"].max(), color="#eeeeee", lw=2.4)
    gg = g[~g["missing_flag"]]
    axA.hlines(i, gg["x"].min(), gg["x"].max(), color="#dce6f1", lw=2.4)
    gm = g[g["missing_flag"]]
    if len(gm):
        axA.hlines(i, gm["x"].min(), gm["x"].max(), color="#bdbdbd", lw=2.4)
    sc = g[g["network_support_change_flag"] == True] if "network_support_change_flag" in g.columns else pd.DataFrame()
    if len(sc):
        axA.plot(sc["x"].iloc[0], i, "|", ms=4, color="#e07b4f", mew=1.0)
axA.set_yticks(range(len(order_q))); axA.set_yticklabels([EN.get(d, d) for d in order_q], fontsize=5.0)
axA.set_ylim(len(order_q) - 0.5, -0.5)
axA.xaxis.set_major_locator(mdates.YearLocator())
axA.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
axA.set_xlabel("Month")
axA.spines["left"].set_visible(False); despine(axA)
axA.text(-0.22, 1.04, "a", transform=axA.transAxes, fontsize=8, fontweight="bold")

rgv = rg[~rg["missing_flag"]].copy()
for d in order_q:
    g = rgv[rgv["district"] == d].sort_values("x")
    axB.plot(g["x"], g["depth_mean_m"], color=C_GW, lw=0.55, alpha=0.8)
    axB.text(g["x"].iloc[-1] + 8, g["depth_mean_m"].iloc[-1], EN.get(d, d), fontsize=4.2, va="center", color="#555555")
axB.invert_yaxis()
axB.set_ylabel("Groundwater depth (m, mean; inverted)")
axB.xaxis.set_major_locator(mdates.YearLocator())
axB.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
axB.set_xlim(rgv["x"].min() - 10, rgv["x"].max() + 130)
despine(axB)
axB.text(-0.10, 1.04, "b", transform=axB.transAxes, fontsize=8, fontweight="bold")
fig.subplots_adjust(left=0.115, right=0.99, top=0.965, bottom=0.10, wspace=0.22)
save_all(fig, "ExtendedData_Fig5_groundwater_QC")

# ============ ED6 depth-area profiles ============
fig, ax = plt.subplots(figsize=(180 * MM, 78 * MM))
prof6 = pd.read_csv(os.path.join(SRC, "ED6_depth_area_profiles.csv"))
prof6 = prof6[prof6["layer_fraction"] > 1e-9]
order6 = prof6.groupby("district")["layer_fraction"].max().loc[[d for d in order16 if d in prof6["district"].unique()]].index
prof6["_o"] = prof6["district"].map({d: i for i, d in enumerate(order6)})
prof6 = prof6.sort_values("_o")
layer_cols = {"B1": "#1f4e79", "B2": "#4a78a8", "B3": "#f2b88c", "B4": "#c8402a", "B5+": "#7a3b2e"}
bottoms = {d: 0.0 for d in order6}
for lb in ["B1", "B2", "B3", "B4", "B5+"]:
    sub = prof6[prof6["layer_bucket"] == lb]
    xs, hs, bs = [], [], []
    for d in order6:
        r_ = sub[sub["district"] == d]
        if len(r_):
            xs.append(EN.get(d, d)); hs.append(float(r_["layer_fraction"].iloc[0])); bs.append(bottoms[d])
            bottoms[d] += float(r_["layer_fraction"].iloc[0])
        else:
            xs.append(EN.get(d, d)); hs.append(0); bs.append(bottoms[d])
    ax.bar(range(len(order6)), hs, bottom=bs, color=layer_cols[lb], width=0.62, edgecolor="white", lw=0.5, label=lb)
ax.set_xticks(range(len(order6)))
ax.set_xticklabels([EN.get(d, d) for d in order6], rotation=45, ha="right", fontsize=5.0)
ax.set_ylabel("Layer share p(d,l) of joint-acceptance\nunderground space (central scenario)")
ax.set_ylim(0, 1.02)
ax.legend(frameon=False, ncol=5, loc="upper right", fontsize=5.2, title="Layer", title_fontsize=5.2)
despine(ax)
save_all(fig, "ExtendedData_Fig6_depth_area_profiles")

# ============ automated pixel checks for all figures ============
qc = []
def check_png(path):
    img = np.asarray(Image.open(path).convert("RGB"))
    h, w, _ = img.shape
    # non-white content bounding box
    nonwhite = (img < 245).any(axis=2)
    ys, xs = np.where(nonwhite)
    frac_content = nonwhite.mean()
    # detect pure-black pixels (rendering failure indicator)
    black = (img < 10).all(axis=2).mean()
    return {"file": os.path.basename(path), "px_w": w, "px_h": h,
            "mm_w": round(w / 300 * 25.4, 1), "mm_h": round(h / 300 * 25.4, 1),
            "content_frac": round(float(frac_content), 3), "black_frac": round(float(black), 4),
            "margin_left_px": int(xs.min()), "margin_right_px": int(w - xs.max()),
            "margin_top_px": int(ys.min()), "margin_bottom_px": int(h - ys.max())}

for folder in [os.path.join(FRZ, "04_main_figures"), ED]:
    for f in sorted(os.listdir(folder)):
        if f.endswith(".png"):
            qc.append(check_png(os.path.join(folder, f)))
qcdf = pd.DataFrame(qc)
qcdf.to_csv(os.path.join(FRZ, "07_audit", "figure_source_audit.csv"), index=False, encoding="utf-8-sig")
with open(os.path.join(FRZ, "_stage1_inspection", "stage4_pixelqc.txt"), "w", encoding="utf-8") as f:
    f.write(qcdf.to_string())
print("STAGE4C DONE — 6 ED figures + pixel QC")
