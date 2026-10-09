# -*- coding: utf-8 -*-
"""Redraw Fig1-Fig5 from the existing source tables, correcting layout defects:
- Fig3/Fig4 serial-year axis (3989-3995) -> real datetime axis
- Fig3 b-d missing threshold lines (district_cn vs en join bug)
- label overlaps (Fig2b dumbbell, Fig4b case labels, Fig4c dense rows, Fig5a/b)
- annotation arrow style (Fig1a, Fig2c)
2026-09-21: Fig2/Fig3 redesigned as map + 4 exemplar insets +
full-width heatmap; maps reuse the Fig1 draw_map style (two-letter codes, north
arrow, 20 km scale bar). Fig2/Fig3 source tables are (re)written here.
Current outputs: Fig1-Fig3; the retired Fig4 is written only to its archive.
Use fig4_spatial_and_s7_s9.py for the current Fig4 and S7-S9."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D
import pandas as pd, numpy as np, os, datetime as dt

BASE = r"local_raw_workspace"
FRZ = os.path.join(BASE, "Nature_results_freeze_v1")
SRC = os.path.join(FRZ, "03_figure_source_tables")
FIG = os.path.join(FRZ, "04_main_figures")
os.makedirs(FIG, exist_ok=True)

MM = 1 / 25.4
plt.rcParams.update({
    "font.family": "Arial", "font.size": 6, "axes.linewidth": 0.7,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 2.2, "ytick.major.size": 2.2,
    "xtick.labelsize": 5.5, "ytick.labelsize": 5.5,
    "axes.labelsize": 6.5, "axes.titlesize": 6.5,
    "legend.fontsize": 5.2, "pdf.fonttype": 42, "svg.fonttype": "none",
})
C_GW = "#1f4e79"
C_ACC = "#c8402a"
C_REF1, C_REF2 = "#c07a28", "#6a51a3"   # milestone segments: first >20 m month / deepest 2015
CM_ENC = LinearSegmentedColormap.from_list("enc", ["#faf7f2", "#f2b88c", "#e07b4f", "#c8402a", "#8c2318"])
CM_ENC.set_bad("#bdbdbd")

EN = {"东城区": "Dongcheng", "西城区": "Xicheng", "朝阳区": "Chaoyang", "丰台区": "Fengtai", "石景山区": "Shijingshan",
      "海淀区": "Haidian", "门头沟区": "Mentougou", "房山区": "Fangshan", "通州区": "Tongzhou", "顺义区": "Shunyi",
      "昌平区": "Changping", "大兴区": "Daxing", "怀柔区": "Huairou", "平谷区": "Pinggu", "密云区": "Miyun", "延庆区": "Yanqing"}

def save_all(fig, name):
    os.makedirs(os.path.dirname(os.path.join(FIG, name)), exist_ok=True)
    for ext in ("svg", "pdf", "png"):
        fig.savefig(os.path.join(FIG, f"{name}.{ext}"), dpi=300 if ext == "png" else None,
                    bbox_inches=None if ext == "svg" else "tight", facecolor="white")
    plt.close(fig)

def panel_label(ax, letter, x=-0.14, y=1.04):
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=8, fontweight="bold", va="bottom", ha="left")

def despine(ax):
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

def ym_to_date(s):
    return dt.date(int(s[:4]), int(s[5:7]), 15)

# ================= Fig 1 =================
fig = plt.figure(figsize=(180 * MM, 150 * MM))
gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.12], width_ratios=[1.15, 1.0],
                      left=0.065, right=0.975, top=0.965, bottom=0.055, hspace=0.34, wspace=0.24)

ax = fig.add_subplot(gs[0, 0])
f1a = pd.read_csv(os.path.join(SRC, "Fig1a_groundwater.csv"))
f1av = f1a.dropna(subset=["depth_m"])
# --- faint 16-district background: direct10 yearly (<=2018) + monthly->annual (>=2019) ---
GW2 = os.path.join(BASE, "groundwater_underground_encounter_v2", "02_groundwater")
hist = pd.read_csv(os.path.join(GW2, "groundwater_historical_direct10.csv"))
hist = hist[hist["year"] <= 2018][["year", "district", "depth_m"]]
mon = pd.read_csv(os.path.join(GW2, "groundwater_monthly_16district_2019_2026.csv"))
mon["year"] = mon["year_month"].str[:4].astype(int)
ann = mon[mon["year"] <= 2025].groupby(["year", "district"], as_index=False)["depth_mean_m"].mean()
ann = ann.rename(columns={"depth_mean_m": "depth_m"})
dist_gw = pd.concat([hist, ann], ignore_index=True)
dist_gw.to_csv(os.path.join(SRC, "Fig1a_district_groundwater.csv"), index=False, encoding="utf-8-sig")
tab20 = plt.get_cmap("tab20")
DIST16_CN = ["东城区", "西城区", "朝阳区", "海淀区", "丰台区", "石景山区", "门头沟区", "房山区",
             "通州区", "顺义区", "昌平区", "大兴区", "怀柔区", "平谷区", "密云区", "延庆区"]
dc = {d: tab20(i / 16) for i, d in enumerate(DIST16_CN)}
for d in DIST16_CN:
    g = dist_gw[dist_gw["district"] == d].sort_values("year")
    if len(g):
        ax.plot(g["year"], g["depth_m"], color=dc[d], lw=1.5, alpha=0.20, zorder=1)
ax.plot(f1av["year"], f1av["depth_m"], color=C_GW, lw=1.8, zorder=3)
y0, y1 = ax.get_ylim()
ax.fill_between(f1av["year"], f1av["depth_m"], y1, color=C_GW, alpha=0.06, lw=0)
imax = f1av["depth_m"].idxmax()
ax.plot([f1av.loc[imax, "year"]], [f1av.loc[imax, "depth_m"]], "o", ms=3, mfc="white", mec=C_GW, mew=0.9, zorder=4)
ax.text(f1av.loc[imax, "year"], f1av.loc[imax, "depth_m"] - 3.0,
        f"deepest {int(f1av.loc[imax,'year'])}, {f1av.loc[imax,'depth_m']:.1f} m",
        fontsize=5.0, color="#333333", ha="center", va="bottom", zorder=5)
ax.invert_yaxis()
# --- milestone segments (shared with panel b): dashed rules connecting both
#     axes to the milestone point — first >20 m month (monthly city
#     series, strict year-month) and the deepest year-end (2015) ---
GD = os.path.join(BASE, "2026.09.04 自然基金委评审材料准备",
                  "Multi-scale data assimilation reveals dynamic antecedent conditions for compound rainfall–groundwater hazards",
                  "data", "地下水部分")
gwmon = pd.read_csv(os.path.join(GD, "beijing_plain_groundwater_2000_2025_monthly_integrated.csv"))
first20 = gwmon[gwmon["depth_m"] > 20].iloc[0]          # 2004-05, 20.11 m
x_first = first20["year"] + (first20["month"] - 0.5) / 12
d_first = float(first20["depth_m"])
lab_first = f"first >20 m ({int(first20['year'])}-{int(first20['month']):02d})"
yr_deep = int(f1av.loc[imax, "year"])
d_deep = float(f1av.loc[imax, "depth_m"])
X0 = 1997.5
ax.plot([X0, x_first], [d_first, d_first], color=C_REF1, lw=0.9, ls=(0, (4, 2)), zorder=2)
ax.plot([x_first], [d_first], "o", ms=2.6, mfc=C_REF1, mec="white", mew=0.6, zorder=5)
ax.text(x_first + 0.6, d_first, f"{lab_first}\n{d_first:.1f} m", fontsize=4.6,
        color=C_REF1, ha="left", va="bottom", linespacing=1.25, zorder=5)
ax.plot([X0, yr_deep], [d_deep, d_deep], color=C_REF2, lw=0.9, ls=(0, (4, 2)), zorder=2)
ax.set_ylim(ax.get_ylim())
ax.vlines([x_first, yr_deep], [d_first, d_deep], ax.get_ylim()[0],
          colors=[C_REF1, C_REF2], lw=0.9, linestyles=(0, (4, 2)), zorder=2)
# x-axis starts at first real observation (isolated 1998 bulletin point shown as dot);
# key years aligned with panel b (2000/2005/2010/2015/2020)
ax.set_xlim(1997.5, 2025)
ax.set_xticks([2000, 2005, 2010, 2015, 2020, 2025])
ax.set_ylabel("Groundwater depth (m)")
ax.set_xlabel("Year")
despine(ax)
panel_label(ax, "a", x=-0.13)

ax = fig.add_subplot(gs[0, 1])
f1b = pd.read_csv(os.path.join(SRC, "Fig1b_stock_proxy.csv"))
# relative stock proxy (2020 = 1): persistent-accumulation narrative, not absolute km2
f1b["stock_rel_2020eq1"] = f1b["stock_sum_km2"] / f1b.loc[f1b["year"] == 2020, "stock_sum_km2"].iloc[0]
f1b.to_csv(os.path.join(SRC, "Fig1b_stock_proxy.csv"), index=False, encoding="utf-8-sig")
ax.plot(f1b["year"], f1b["stock_rel_2020eq1"], "o", ms=3.0, mfc="white", mec=C_GW, mew=0.9, zorder=4)
ax.axhline(1.0, color="#bbbbbb", lw=0.5, ls=(0, (2, 2)), zorder=1)
# --- faint 16-district relative stock background ---
nodes = pd.read_csv(os.path.join(BASE, "historical_underground_space_backcast_v11", "08_next_stage",
                                 "district_LUCC_stock_proxy_nodes.csv"))
base2020 = nodes[nodes["year"] == 2020].set_index("district")["stock_area_km2"]
nodes["stock_rel_2020eq1"] = nodes.apply(lambda r: r["stock_area_km2"] / base2020.get(r["district"], np.nan), axis=1)
nodes[["year", "district", "stock_area_km2", "stock_rel_2020eq1"]].to_csv(
    os.path.join(SRC, "Fig1b_district_stock_proxy.csv"), index=False, encoding="utf-8-sig")
for d in DIST16_CN:
    g = nodes[nodes["district"] == d].sort_values("year")
    if len(g):
        ax.plot(g["year"], g["stock_rel_2020eq1"], color=dc[d], lw=1.5, alpha=0.20, zorder=1)
ax.plot(f1b["year"], f1b["stock_rel_2020eq1"], color=C_GW, lw=1.2, zorder=3)
# --- reference segments: same two milestones as panel a (variables reused
#     from panel a); segments run from the x-axis up to the stock curve and
#     end in a dot on the curve ---
stock_at = lambda y: float(np.interp(y, f1b["year"], f1b["stock_rel_2020eq1"]))
pd.DataFrame([
    {"milestone": "first depth >20 m (monthly)", "date": first20["date"],
     "x_year": round(x_first, 3), "depth_m": first20["depth_m"],
     "stock_rel_2020eq1": round(stock_at(x_first), 4)},
    {"milestone": "deepest year-end (panel a anchor)", "date": f"{yr_deep}-12",
     "x_year": yr_deep, "depth_m": float(f1av['depth_m'].max()),
     "stock_rel_2020eq1": round(stock_at(yr_deep), 4)},
]).to_csv(os.path.join(SRC, "Fig1b_milestone_segments.csv"), index=False, encoding="utf-8-sig")
ax.set_ylim(ax.get_ylim())
ybot = ax.get_ylim()[0]
for xx, col, lab, ha, dxs, dys, va in [
        (x_first, C_REF1, f"{lab_first}\nstock {stock_at(x_first)*100:.0f}%", "right", -0.5, 0.035, "bottom"),
        (yr_deep, C_REF2, f"deepest {yr_deep}\nstock {stock_at(yr_deep)*100:.0f}%", "left", 0.6, -0.045, "top")]:
    yy = stock_at(xx)
    ax.plot([xx, xx], [ybot, yy], color=col, lw=0.9, ls=(0, (4, 2)), zorder=2)
    ax.plot([xx], [yy], "o", ms=2.6, mfc=col, mec="white", mew=0.6, zorder=5)
    ax.text(xx + dxs, yy + dys, lab, fontsize=4.6, color=col, ha=ha, va=va,
            linespacing=1.25, zorder=5)
ax.set_xlim(1979, 2021)
ax.set_xticks([1980, 1990, 2000, 2005, 2010, 2015, 2020])
ax.set_xticklabels(["1980", "1990", "2000", "2005", "2010", "2015", "2020"], fontsize=5.0)
ax.set_ylabel("Relative underground-space\nstock (2020 = 1)")
ax.set_xlabel("Year")
despine(ax)
panel_label(ax, "b", x=-0.13)

# --- c: map of per-district groundwater level delta (deepest -> shallowest) ---
# --- d: map of per-district underground-space stock proxy area (2020) ---
from matplotlib.patches import Polygon as MplPolygon
rings = pd.read_csv(os.path.join(SRC, "_beijing_district_rings.csv"))

def draw_map(ax, values, cmap, cblabel, letter, norm=None, hmax=1.0):
    vals = pd.Series(values)
    import matplotlib.colors as mcolors
    if norm is None:
        vmin, vmax = vals.min(), vals.max()
        norm = mcolors.Normalize(vmin, vmax)
    for d, g in rings.groupby("district"):
        if d not in values:
            continue
        col = cmap(norm(values[d]))
        for (part, ring), gg in g.groupby(["part", "ring"]):
            if ring != 0:   # skip holes
                continue
            ax.add_patch(MplPolygon(gg[["x", "y"]].values, closed=True, fc=col, ec="white", lw=0.5, zorder=2))
    # left-align the map with the panel above: fit the axes box to the map's
    # geographic aspect and anchor that box to the left edge of the grid cell
    A = 1.30
    sub = rings[rings["district"].isin(vals.index)]
    xmin, xmax = sub["x"].min(), sub["x"].max()
    ymin, ymax = sub["y"].min(), sub["y"].max()
    xpad = 0.020 * (xmax - xmin); ypad = 0.035 * (ymax - ymin)
    x0, x1 = xmin - xpad, xmax + xpad
    y0, y1 = ymin - ypad, ymax + ypad
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    # Manual aspect: size the axes box so 1 deg lat is A times 1 deg lon on screen,
    # with the box hugging the left/bottom of the grid cell (aligns with panels a/b).
    pos = ax.get_position(); figw, figh = fig.get_size_inches()
    r_vis = ((y1 - y0) * A) / (x1 - x0)
    cell_w_in, cell_h_in = pos.width * figw, pos.height * figh * hmax
    map_w_in = cell_h_in / r_vis
    if map_w_in <= cell_w_in:
        map_h_in = cell_h_in
    else:
        map_w_in = cell_w_in; map_h_in = cell_w_in * r_vis
    map_w_frac, map_h_frac = map_w_in / figw, map_h_in / figh
    yoff = (pos.height * figh - map_h_in) / 2 / figh   # centre vertically in the cell
    ax.set_position([pos.x0, pos.y0 + yoff, map_w_frac, map_h_frac])
    ax.set_xticks([]); ax.set_yticks([])
    ax.spines[:].set_visible(False)
    # labels: two-letter district abbreviations inside the map
    import matplotlib.patheffects as pe
    halo = [pe.withStroke(linewidth=1.1, foreground="white")]
    AB = {"东城区": "DC", "西城区": "XC", "朝阳区": "CY", "海淀区": "HD", "丰台区": "FT",
          "石景山区": "SJ", "门头沟区": "MT", "房山区": "FS", "通州区": "TZ", "大兴区": "DX",
          "顺义区": "SY", "昌平区": "CP", "平谷区": "PG", "怀柔区": "HR", "密云区": "MY", "延庆区": "YQ"}
    nudge = {"西城区": (-0.014, 0.002), "东城区": (0.016, 0.006), "朝阳区": (0.030, 0.005),
             "海淀区": (-0.010, 0.020), "石景山区": (-0.010, 0.000), "丰台区": (-0.005, -0.010)}
    for d in DIST16_CN:
        g = rings[(rings["district"] == d) & (rings["ring"] == 0)]
        if not len(g) or d not in values:
            continue
        big = g.groupby("part").size().idxmax()
        gg = g[g["part"] == big]
        cx, cy = gg["x"].mean(), gg["y"].mean()
        dx, dy = nudge.get(d, (0.0, 0.0))
        ax.text(cx + dx, cy + dy, AB[d], fontsize=4.4 if d in nudge else 4.8,
                ha="center", va="center", color="#1a1a1a", path_effects=halo, zorder=4)
    # north arrow + scale bar (white underlay keeps the bar readable on fills)
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim(); w = x1 - x0; h = y1 - y0
    nx, ny = x0 + 0.07 * w, y1 - 0.13 * h
    ax.annotate("", xy=(nx, ny + 0.07 * h), xytext=(nx, ny), zorder=5,
                arrowprops=dict(arrowstyle="-|>", lw=0.9, color="#333333", mutation_scale=8))
    ax.text(nx, ny + 0.082 * h, "N", fontsize=5.2, ha="center", va="bottom",
            color="#333333", path_effects=halo, zorder=5)
    deg20 = 20.0 / (111.32 * np.cos(np.deg2rad(40.0)))   # 20 km in degrees longitude
    sx, sy = x1 - 0.36 * w, y0 + 0.07 * h
    for xx, yy in [([sx, sx + deg20], [sy, sy]),
                   ([sx, sx], [sy - 0.006 * h, sy + 0.006 * h]),
                   ([sx + deg20, sx + deg20], [sy - 0.006 * h, sy + 0.006 * h])]:
        ax.plot(xx, yy, color="white", lw=2.8, solid_capstyle="butt", zorder=4)
        ax.plot(xx, yy, color="#333333", lw=1.2 if xx[0] != xx[1] else 0.8,
                solid_capstyle="butt", zorder=5)
    ax.text(sx + deg20 / 2, sy + 0.012 * h, "20 km", fontsize=4.6, ha="center", va="bottom",
            color="#333333", path_effects=halo, zorder=6)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cax = fig.add_axes([pos.x0 + map_w_frac + 0.008, pos.y0 + yoff, 0.010, map_h_frac])
    cb = fig.colorbar(sm, cax=cax)
    cb.ax.tick_params(labelsize=4.6); cb.outline.set_linewidth(0.5)
    cb.set_label(cblabel, fontsize=5.2)
    panel_label(ax, letter, x=-0.02, y=1.02)

def draw_map_cat(ax, facecolor_fn, edge_fn, letter, label_ds=None):
    """Categorical twin of draw_map: identical geometry (extent, manual aspect,
    two-letter labels, north arrow, 20 km scale bar) but colours come from
    facecolor_fn(d) and edges from edge_fn(d)->(ec, lw); no colorbar.
    Polygons are drawn for every district where facecolor_fn(d) is not None."""
    drawn = []
    for d, g in rings.groupby("district"):
        fc = facecolor_fn(d)
        if fc is None:
            continue
        drawn.append(d)
        ec, lw = edge_fn(d)
        for (part, ring), gg in g.groupby(["part", "ring"]):
            if ring != 0:   # skip holes
                continue
            ax.add_patch(MplPolygon(gg[["x", "y"]].values, closed=True, fc=fc, ec=ec, lw=lw, zorder=2))
    A = 1.30
    sub = rings[rings["district"].isin(drawn)]
    xmin, xmax = sub["x"].min(), sub["x"].max()
    ymin, ymax = sub["y"].min(), sub["y"].max()
    xpad = 0.020 * (xmax - xmin); ypad = 0.035 * (ymax - ymin)
    x0, x1 = xmin - xpad, xmax + xpad
    y0, y1 = ymin - ypad, ymax + ypad
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    pos = ax.get_position(); figw, figh = fig.get_size_inches()
    r_vis = ((y1 - y0) * A) / (x1 - x0)
    cell_w_in, cell_h_in = pos.width * figw, pos.height * figh
    map_w_in = cell_h_in / r_vis
    if map_w_in <= cell_w_in:
        map_h_in = cell_h_in
    else:
        map_w_in = cell_w_in; map_h_in = cell_w_in * r_vis
    ax.set_position([pos.x0, pos.y0, map_w_in / figw, map_h_in / figh])
    ax.set_xticks([]); ax.set_yticks([])
    ax.spines[:].set_visible(False)
    import matplotlib.patheffects as pe
    halo = [pe.withStroke(linewidth=1.1, foreground="white")]
    AB = {"东城区": "DC", "西城区": "XC", "朝阳区": "CY", "海淀区": "HD", "丰台区": "FT",
          "石景山区": "SJ", "门头沟区": "MT", "房山区": "FS", "通州区": "TZ", "大兴区": "DX",
          "顺义区": "SY", "昌平区": "CP", "平谷区": "PG", "怀柔区": "HR", "密云区": "MY", "延庆区": "YQ"}
    nudge = {"西城区": (-0.014, 0.002), "东城区": (0.016, 0.006), "朝阳区": (0.030, 0.005),
             "海淀区": (-0.010, 0.020), "石景山区": (-0.010, 0.000), "丰台区": (-0.005, -0.010),
             "怀柔区": (0.032, 0.010)}   # HR: free the western edge for the Fig2a leader anchor
    for d in (label_ds if label_ds is not None else DIST16_CN):
        g = rings[(rings["district"] == d) & (rings["ring"] == 0)]
        if not len(g) or d not in drawn:
            continue
        big = g.groupby("part").size().idxmax()
        gg = g[g["part"] == big]
        cx, cy = gg["x"].mean(), gg["y"].mean()
        dx, dy = nudge.get(d, (0.0, 0.0))
        ax.text(cx + dx, cy + dy, AB[d], fontsize=4.4 if d in nudge else 4.8,
                ha="center", va="center", color="#1a1a1a", path_effects=halo, zorder=4)
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim(); w = x1 - x0; h = y1 - y0
    nx, ny = x0 + 0.07 * w, y1 - 0.13 * h
    ax.annotate("", xy=(nx, ny + 0.07 * h), xytext=(nx, ny), zorder=5,
                arrowprops=dict(arrowstyle="-|>", lw=0.9, color="#333333", mutation_scale=8))
    ax.text(nx, ny + 0.082 * h, "N", fontsize=5.2, ha="center", va="bottom",
            color="#333333", path_effects=halo, zorder=5)
    deg20 = 20.0 / (111.32 * np.cos(np.deg2rad(40.0)))
    sx, sy = x1 - 0.36 * w, y0 + 0.07 * h
    for xx, yy in [([sx, sx + deg20], [sy, sy]),
                   ([sx, sx], [sy - 0.006 * h, sy + 0.006 * h]),
                   ([sx + deg20, sx + deg20], [sy - 0.006 * h, sy + 0.006 * h])]:
        ax.plot(xx, yy, color="white", lw=2.8, solid_capstyle="butt", zorder=4)
        ax.plot(xx, yy, color="#333333", lw=1.2 if xx[0] != xx[1] else 0.8,
                solid_capstyle="butt", zorder=5)
    ax.text(sx + deg20 / 2, sy + 0.012 * h, "20 km", fontsize=4.6, ha="center", va="bottom",
            color="#333333", path_effects=halo, zorder=6)
    panel_label(ax, letter, x=-0.02, y=1.02)

# c data: delta = deepest - shallowest annual groundwater depth per district (m)
dgw = pd.read_csv(os.path.join(SRC, "Fig1a_district_groundwater.csv"))
delta = dgw.groupby("district")["depth_m"].agg(lambda s: s.max() - s.min())
delta_df = delta.reset_index()
delta_df.columns = ["district", "gw_level_delta_m"]
delta_df["district_en"] = delta_df["district"].map(EN)
delta_df.to_csv(os.path.join(SRC, "Fig1c_gw_delta_map.csv"), index=False, encoding="utf-8-sig")
CM_BLU = LinearSegmentedColormap.from_list("gw", ["#eef4f9", "#b8d0e4", "#6d97c4", "#1f4e79"])
axc = fig.add_subplot(gs[1, 0])
draw_map(axc, delta.to_dict(), CM_BLU, r"$D_{\mathrm{deepest}}-D_{\mathrm{shallowest}}$ (m)", "c")

# d data: underground-space stock proxy / surface area ratio (2020)
stk = pd.read_csv(os.path.join(SRC, "Fig1b_district_stock_proxy.csv"))
s20 = stk[stk["year"] == 2020].set_index("district")["stock_area_km2"]

def district_area_km2(g):
    lat0 = np.deg2rad(g["y"].mean())
    kx, ky = 111.32 * np.cos(lat0), 111.32
    tot = 0.0
    for (part, ring), gg in g.groupby(["part", "ring"]):
        x = gg["x"].values * kx; y = gg["y"].values * ky
        a = 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
        tot += a if ring == 0 else -abs(a)
    return abs(tot)

areas = rings.groupby("district").apply(district_area_km2)
ratio = (s20 / areas).dropna()
r_df = pd.DataFrame({
    "district": ratio.index,
    "surface_area_km2": areas.loc[ratio.index].values,
    "stock_area_km2_2020": s20.loc[ratio.index].values,
    "stock_to_surface_ratio": ratio.values,
})
r_df["district_en"] = r_df["district"].map(EN)
r_df.to_csv(os.path.join(SRC, "Fig1d_stock_ratio_map.csv"), index=False, encoding="utf-8-sig")
CM_ORG = LinearSegmentedColormap.from_list("st", ["#faf3ec", "#f0c49c", "#dd8452", "#b04a26"])
axd = fig.add_subplot(gs[1, 1])
draw_map(axd, ratio.to_dict(), CM_ORG, r"$S_{\mathrm{under}}/S_{\mathrm{surface}}$, 2020", "d")
save_all(fig, "Fig1_legacy_context")

# ================= Fig 2 =================
# 2026-09-21: a = trajectory-type map, b = four exemplar
# district trajectories, c = full-width 2000-2020 heatmap
import matplotlib.patheffects as pe
from matplotlib.patches import Patch, Rectangle
HALO = [pe.withStroke(linewidth=1.1, foreground="white")]

# --- source tables for the redesign ---
tjb = pd.read_csv(os.path.join(SRC, "Fig2b_trajectory_summary.csv"))
CLASS_ORDER = ["contact_reemerged", "persistent_contact", "contact_lost_during_depletion",
               "intermittent_or_uncertain", "persistent_no_contact"]
CLASS_SHORT = {"contact_reemerged": "re-emerged", "persistent_contact": "persistent contact",
               "contact_lost_during_depletion": "contact lost", "intermittent_or_uncertain": "intermittent",
               "persistent_no_contact": "no contact"}
CLASS_COLOR = {"contact_reemerged": "#c8402a", "persistent_contact": "#f2b88c",
               "contact_lost_during_depletion": "#7a9cc6", "intermittent_or_uncertain": "#bdbdbd",
               "persistent_no_contact": "#efefef"}
cls_map = dict(zip(tjb["district"], tjb["trajectory_class"]))
f2a = pd.DataFrame({"district": DIST16_CN})
f2a["district_en"] = f2a["district"].map(EN)
f2a["in_historical_direct10"] = f2a["district"].isin(tjb["district"])
f2a["trajectory_class"] = f2a["district"].map(cls_map)
f2a.to_csv(os.path.join(SRC, "Fig2a_trajectory_map.csv"), index=False, encoding="utf-8-sig")

EX2 = ["怀柔区", "房山区", "通州区", "大兴区"]   # corner insets: HR, FS, TZ, DX
AB2 = {"怀柔区": "HR", "房山区": "FS", "通州区": "TZ", "大兴区": "DX"}
h2 = pd.read_csv(os.path.join(BASE, "groundwater_underground_encounter_v2", "03_historical",
                              "historical_encounter_direct10_2000_2020.csv"))
rows = []
for d in EX2:
    g = h2[(h2["district"] == d) & (h2["depth_scenario"] == "central")].sort_values("year")
    for _, r in g.iterrows():
        rows.append({"district": EN[d], "district_cn": d, "year": int(r["year"]),
                     "groundwater_depth_m": r["groundwater_depth_m"],
                     "encounter_fraction": r["encounter_fraction"], "series": "historical central"})
tr2 = pd.DataFrame(rows)
tr2.to_csv(os.path.join(SRC, "Fig2a_exemplar_trajectories.csv"), index=False, encoding="utf-8-sig")
prof = pd.read_csv(os.path.join(SRC, "ED6_depth_area_profiles.csv"))
th2 = prof[prof["district"].isin(EX2)][["district", "district_en", "layer_bucket", "representative_depth_m", "layer_fraction"]]
th2.to_csv(os.path.join(SRC, "Fig2a_layer_thresholds.csv"), index=False, encoding="utf-8-sig")
hm = pd.read_csv(os.path.join(SRC, "Fig2a_historical_heatmap.csv"), index_col=0)
hm.to_csv(os.path.join(SRC, "Fig2b_historical_heatmap.csv"), encoding="utf-8-sig")

# --- well-level distribution band: assign monitoring wells to districts, then
#     per district-year quantiles (band = interquartile range across wells) ---
from matplotlib.path import Path as MplPath
wells = pd.read_excel(os.path.join(BASE, "地下水数据", "Groundwater depth in wells.xlsx"))
_paths = {}
for dd, g in rings.groupby("district"):
    for (part, ring), gg in g.groupby(["part", "ring"]):
        if ring != 0:
            continue
        _paths.setdefault(dd, []).append(MplPath(gg[["x", "y"]].values))
def _district_of(lon, lat):
    for dd, ps in _paths.items():
        if any(p.contains_point((lon, lat)) for p in ps):
            return dd
    return None
wells["district"] = [_district_of(lo, la) for lo, la in zip(wells["longitude(°)"], wells["latitude(°)"])]
wyears = [c for c in wells.columns if isinstance(c, int) and 2000 <= c <= 2020]
wrows = []
for d in EX2:
    sub = wells[wells["district"] == d]
    for y in wyears:
        v = sub[y].dropna()
        if len(v) >= 2:
            wrows.append({"district": d, "district_en": EN[d], "code": AB2[d], "year": y,
                          "n_wells": int(len(v)), "depth_min_m": float(v.min()),
                          "depth_p25_m": float(np.percentile(v, 25)),
                          "depth_p75_m": float(np.percentile(v, 75)),
                          "depth_max_m": float(v.max())})
wr = pd.DataFrame(wrows)
wr.to_csv(os.path.join(SRC, "Fig2a_well_range.csv"), index=False, encoding="utf-8-sig")

fig = plt.figure(figsize=(180 * MM, 155 * MM))
gs = fig.add_gridspec(2, 1, height_ratios=[1.35, 0.72],
                      left=0.075, right=0.985, top=0.965, bottom=0.075, hspace=0.30)

# --- a: combined panel — trajectory-class map with four corner exemplar
#        insets linked by straight leaders (HR upper left, FS lower left,
#        TZ upper right, DX lower right) ---
axm = fig.add_axes([0.315, 0.475, 0.37, 0.475])
draw_map_cat(axm,
             facecolor_fn=lambda d: CLASS_COLOR.get(cls_map.get(d, ""), "#ffffff"),
             edge_fn=lambda d: ("white", 0.5) if d in cls_map else ("#c9c9c9", 0.5),
             letter="a")
axm.set_facecolor("none")   # let leader lines pass through the map axes box
handles = [Patch(fc=CLASS_COLOR[c], ec="white", lw=0.5,
                 label=f"{CLASS_SHORT[c]} (n={(tjb['trajectory_class'] == c).sum()})") for c in CLASS_ORDER]
handles.append(Patch(fc="white", ec="#c9c9c9", lw=0.5, label="core districts (not in set)"))
axm.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, -0.10), frameon=False,
           fontsize=4.2, ncol=2, handletextpad=0.4, columnspacing=0.7, labelspacing=0.55,
           handlelength=1.2, handleheight=0.9, borderaxespad=0)

def exemplar_inset(ax, d):
    g = tr2[tr2["district_cn"] == d].sort_values("year")
    lt = th2[(th2["district"] == d) & (th2["layer_fraction"] > 1e-9)].sort_values("representative_depth_m")
    ax.plot(g["year"], g["groundwater_depth_m"], color=C_GW, lw=1.0, zorder=3)
    ytop = g["groundwater_depth_m"].min() * 0.55
    ybot = max(g["groundwater_depth_m"].max(),
               lt["representative_depth_m"].max() if len(lt) else 0) * 1.10
    end_depth = g["groundwater_depth_m"].iloc[-1]
    for _, r in lt.iterrows():
        if not (ytop < r["representative_depth_m"] < ybot):
            continue
        ax.axhline(r["representative_depth_m"], color="#aaaaaa", lw=0.5, zorder=1)
        # layer tag on the left when the curve ends near the threshold
        if abs(end_depth - r["representative_depth_m"]) < 1.2:
            lx, ha = 2000.4, "left"
        else:
            lx, ha = 2019.6, "right"
        ax.text(lx, r["representative_depth_m"], f"{r['layer_bucket']} {r['representative_depth_m']:.0f} m",
                fontsize=4.0, va="bottom", ha=ha, color="#777777", path_effects=HALO)
    ax.set_ylim(ybot, ytop)
    ax.set_xlim(2000, 2020)
    ax.set_xticks([2000, 2010, 2020])
    ax.locator_params(axis="y", nbins=4)
    ax.text(0.05, 0.86, AB2[d], transform=ax.transAxes, fontsize=6.5, fontweight="bold")
    despine(ax)
    ax.tick_params(labelsize=4.6)
    return ax

boxes = {"怀柔区": [0.055, 0.700, 0.185, 0.245],   # HR upper left
         "房山区": [0.055, 0.470, 0.185, 0.200],   # FS lower left
         "通州区": [0.760, 0.700, 0.185, 0.245],   # TZ upper right
         "大兴区": [0.760, 0.470, 0.185, 0.200]}   # DX lower right
inset_axes = {}
for d, bb in boxes.items():
    inset_axes[d] = exemplar_inset(fig.add_axes(bb), d)
for d in ("怀柔区", "通州区"):
    inset_axes[d].set_xticklabels([])
for d in ("怀柔区", "房山区"):
    inset_axes[d].set_ylabel("Depth (m)", fontsize=5.5)

# Fangshan annotations: deepest 2005, first central B2 rebound crossing 2012
axf = inset_axes["房山区"]
fs = tr2[tr2["district_cn"] == "房山区"].sort_values("year")
d05 = fs.loc[fs["groundwater_depth_m"].idxmax()]
axf.plot(d05["year"], d05["groundwater_depth_m"], "o", ms=2.4, mfc="white", mec=C_GW, mew=0.8, zorder=4)
axf.annotate("deepest 2005", xy=(d05["year"], d05["groundwater_depth_m"]), xytext=(2007.8, 21.0),
             fontsize=4.2, color="#444444", va="center", ha="left",
             arrowprops=dict(arrowstyle="-", lw=0.5, color="#999999", shrinkB=2))
y12 = fs[fs["year"] == 2012]["groundwater_depth_m"].iloc[0]
axf.annotate("first B2\ncrossing 2012", xy=(2012, y12), xytext=(2013.2, 6.4),
             fontsize=4.2, color=C_ACC, ha="left", va="center", linespacing=1.2,
             arrowprops=dict(arrowstyle="-", lw=0.5, color=C_ACC, shrinkB=2,
                             connectionstyle="arc3,rad=-0.18"))

# straight leaders: inset inner edge -> district boundary vertex nearest to the
# inset (anchor dot sits on the polygon edge, clear of the district name label)
for d in EX2:
    g = rings[(rings["district"] == d) & (rings["ring"] == 0)]
    big = g.groupby("part").size().idxmax()
    gg = g[g["part"] == big]
    bb = boxes[d]
    if d in ("怀柔区", "房山区"):
        ix, iy = bb[0] + bb[2], bb[1] + bb[3] * 0.5
    else:
        ix, iy = bb[0], bb[1] + bb[3] * 0.5
    ax_, ay_ = axm.transData.inverted().transform(fig.transFigure.transform((ix, iy)))
    pts = gg[["x", "y"]].values
    mx, my = gg["x"].mean(), gg["y"].mean()
    # anchor = point on the ray from the district centroid toward the inset,
    # 72% of the way to the polygon edge: always inside the district, on the
    # inset-facing side, and clear of the centroid name label
    dx_, dy_ = ax_ - mx, ay_ - my
    t_hit = np.inf
    p1 = pts
    p2 = np.roll(pts, -1, axis=0)
    ex, ey = p2[:, 0] - p1[:, 0], p2[:, 1] - p1[:, 1]
    den = dx_ * ey - dy_ * ex
    ok = np.abs(den) > 1e-14
    t = ((p1[:, 0] - mx) * ey - (p1[:, 1] - my) * ex) / np.where(ok, den, 1.0)
    s = ((p1[:, 0] - mx) * dy_ - (p1[:, 1] - my) * dx_) / np.where(ok, den, 1.0)
    cand = t[(ok) & (t > 1e-9) & (s >= 0) & (s <= 1)]
    if len(cand):
        t_hit = cand.min()
    if not np.isfinite(t_hit):
        k = np.argmin((pts[:, 0] - ax_) ** 2 + (pts[:, 1] - ay_) ** 2)
        cx, cy = pts[k] + 0.3 * (np.array([mx, my]) - pts[k])
    else:
        # HR: its name label sits between centroid and western edge, so hop
        # almost to the edge (inside) to clear the label
        frac = {"怀柔区": 0.88}.get(d, 0.72)
        cx, cy = mx + frac * t_hit * dx_, my + frac * t_hit * dy_
    fx, fy = fig.transFigure.inverted().transform(axm.transData.transform((cx, cy)))
    fig.lines.append(Line2D([ix, fx], [iy, fy], transform=fig.transFigure,
                            color="#999999", lw=0.6, zorder=1))
    axm.plot([cx], [cy], "o", ms=2.2, mfc="white", mec="#555555", mew=0.7, zorder=6)

# --- b: full-width historical heatmap, rows keyed to the map colours ---
ax = fig.add_subplot(gs[1])
M = hm.values.astype(float)
im = ax.imshow(M, aspect="auto", cmap=CM_ENC, vmin=0, vmax=1, interpolation="nearest")
ax.set_xticks(range(0, 21, 5)); ax.set_xticklabels([2000, 2005, 2010, 2015, 2020])
labels = [AB2.get(d, {"门头沟区": "MT", "密云区": "MY", "平谷区": "PG",
                      "顺义区": "SY", "昌平区": "CP", "延庆区": "YQ"}.get(d, EN.get(d, d)))
          for d in hm.index]
row_cls = [cls_map[d] for d in hm.index]
sep = [i for i in range(1, len(row_cls)) if row_cls[i] != row_cls[i - 1]]
for s in sep:
    ax.axhline(s - 0.5, color="white", lw=1.6)
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=5.5)
ax.text(20, list(hm.index).index("房山区"), "0.49", fontsize=4.8, ha="right", va="center", color="white", fontweight="bold")
ax.text(0, list(hm.index).index("房山区"), "0.10", fontsize=4.8, ha="left", va="center", color="#555555")
cb = fig.colorbar(im, ax=ax, fraction=0.022, pad=0.012)
cb.ax.tick_params(labelsize=5.0); cb.outline.set_linewidth(0.5)
cb.set_label("Encounter fraction C", fontsize=5.5)
ax.set_xlabel("Year")
ax.spines[:].set_visible(False)
panel_label(ax, "b", x=-0.062)
save_all(fig, "Fig2_historical_reemergence")

# ================= Fig 3 =================
# 2026-09-21: a = Dec-2025 endpoint map (16 districts),
# b = four exemplar monthly threshold panels, c = full-width monthly heatmap
import matplotlib.colors as mcolors

# --- source tables for the redesign ---
rk3 = pd.read_csv(os.path.join(SRC, "Fig5b_rank_mismatch.csv"))
f3a = rk3[["district", "district_en", "encounter_fraction_central_2025"]].copy()
f3a.to_csv(os.path.join(SRC, "Fig3a_endpoint_map.csv"), index=False, encoding="utf-8-sig")
re3 = pd.read_csv(os.path.join(BASE, "groundwater_underground_encounter_v2", "04_recovery",
                               "recovery_encounter_monthly_16district.csv"))
re3["year_month"] = re3["year_month"].astype(str)
rl3 = pd.read_csv(os.path.join(BASE, "groundwater_underground_encounter_v2", "04_recovery",
                               "recovery_layer_contact_long.csv"))
d = "海淀区"
gg = re3[(re3["district"] == d) & (re3["depth_scenario"] == "central")].sort_values("year_month")[["year_month", "groundwater_depth_m", "encounter_fraction"]]
lt = rl3[(rl3["district"] == d) & (rl3["depth_scenario"] == "central")][["layer_bucket", "representative_depth_m"]].drop_duplicates().sort_values("representative_depth_m")
gg.assign(district=EN[d], district_cn=d).to_csv(os.path.join(SRC, "Fig3e_haidian_threshold.csv"), index=False, encoding="utf-8-sig")
lt.assign(district=EN[d], district_cn=d).to_csv(os.path.join(SRC, "Fig3e_haidian_layer_thresholds.csv"), index=False, encoding="utf-8-sig")
hm3 = pd.read_csv(os.path.join(SRC, "Fig3a_recovery_heatmap.csv"), index_col=0)
hm3.to_csv(os.path.join(SRC, "Fig3c_recovery_heatmap.csv"), encoding="utf-8-sig")

fig = plt.figure(figsize=(180 * MM, 165 * MM))
gs = fig.add_gridspec(2, 1, height_ratios=[1.35, 0.72],
                      left=0.075, right=0.985, top=0.965, bottom=0.075, hspace=0.30)

# --- a: combined panel — Dec-2025 endpoint map in the middle, four monthly
#        exemplars at the corners (HD upper left, FS lower left, HR upper
#        right, MY lower right), each linked to its district by a straight leader ---
axm = fig.add_axes([0.315, 0.475, 0.37, 0.475])
val3 = dict(zip(f3a["district"], f3a["encounter_fraction_central_2025"]))
draw_map(axm, val3, CM_ENC, "Encounter fraction C,\nDec 2025", "a",
         norm=mcolors.Normalize(0, 1), hmax=0.85)
fig.axes[-1].remove()       # drop the map colourbar: panel b shares the same 0-1 scale
axm.set_facecolor("none")   # let leader lines pass through the map axes box

AB3 = {"海淀区": "HD", "房山区": "FS", "怀柔区": "HR", "密云区": "MY"}
TAG3 = {"海淀区": "Fig3e_haidian", "房山区": "Fig3b_fangshan",
        "怀柔区": "Fig3c_huairou", "密云区": "Fig3d_miyun"}

def monthly_inset(ax, d):
    gg = pd.read_csv(os.path.join(SRC, f"{TAG3[d]}_threshold.csv"))
    gg = gg[gg["year_month"] <= "2025-12"].copy()
    gg["x"] = gg["year_month"].map(ym_to_date)
    lt = pd.read_csv(os.path.join(SRC, f"{TAG3[d]}_layer_thresholds.csv"))
    fr = prof[prof["district"] == d][["layer_bucket", "layer_fraction"]]
    lt = lt.merge(fr, on="layer_bucket", how="left")
    lt = lt[lt["layer_fraction"] > 1e-9].sort_values("representative_depth_m")
    ytop = gg["groundwater_depth_m"].min() * 0.55
    ybot = max(gg["groundwater_depth_m"].max(),
               lt["representative_depth_m"].max() if len(lt) else 0) * 1.14
    hit = gg.loc[gg["encounter_fraction"] > 1e-9, "x"]
    if len(hit) and hit.iloc[0] > gg["x"].iloc[0]:
        ax.axvline(hit.iloc[0], color=C_ACC, lw=0.9, zorder=2)   # first new contact month
    ax.plot(gg["x"], gg["groundwater_depth_m"], color=C_GW, lw=0.95, zorder=3)
    xr, xl = dt.date(2025, 12, 15), dt.date(2019, 9, 20)
    end_depth = gg["groundwater_depth_m"].iloc[-1]
    for _, r in lt.iterrows():
        if not (ytop < r["representative_depth_m"] < ybot):
            continue
        ax.axhline(r["representative_depth_m"], color="#aaaaaa", lw=0.5, zorder=1)
        lx, ha = (xl, "left") if abs(end_depth - r["representative_depth_m"]) < 1.2 else (xr, "right")
        ax.text(lx, r["representative_depth_m"], f"{r['layer_bucket']} {r['representative_depth_m']:.0f} m",
                fontsize=3.8, va="bottom", ha=ha, color="#777777", path_effects=HALO)
    ax.set_ylim(ybot, ytop)
    ax.set_xlim(dt.date(2019, 8, 1), dt.date(2026, 1, 15))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.locator_params(axis="y", nbins=4)
    ax.text(0.05, 0.86, AB3[d], transform=ax.transAxes, fontsize=6.5, fontweight="bold")
    despine(ax)
    ax.tick_params(labelsize=4.6)
    return ax

boxes3 = {"海淀区": [0.055, 0.700, 0.185, 0.245],   # HD upper left
          "房山区": [0.055, 0.470, 0.185, 0.200],   # FS lower left
          "怀柔区": [0.760, 0.700, 0.185, 0.245],   # HR upper right
          "密云区": [0.760, 0.470, 0.185, 0.200]}   # MY lower right
inset3 = {d: monthly_inset(fig.add_axes(bb), d) for d, bb in boxes3.items()}
for d in ("海淀区", "怀柔区"):
    inset3[d].set_xticklabels([])
for d in ("海淀区", "房山区"):
    inset3[d].set_ylabel("Depth (m)", fontsize=5.5)

# straight leaders: inset inner edge -> district boundary vertex nearest to the
# inset (anchor pulled inward so the line stops clear of the two-letter label)
for d in boxes3:
    g = rings[(rings["district"] == d) & (rings["ring"] == 0)]
    big = g.groupby("part").size().idxmax()
    gg = g[g["part"] == big]
    bb = boxes3[d]
    if d in ("海淀区", "房山区"):
        ix, iy = bb[0] + bb[2], bb[1] + bb[3] * 0.5
    else:
        ix, iy = bb[0], bb[1] + bb[3] * 0.5
    ax_, ay_ = axm.transData.inverted().transform(fig.transFigure.transform((ix, iy)))
    pts = gg[["x", "y"]].values
    k = np.argmin((pts[:, 0] - ax_) ** 2 + (pts[:, 1] - ay_) ** 2)
    mx, my = gg["x"].mean(), gg["y"].mean()
    cx, cy = pts[k] + 0.18 * (np.array([mx, my]) - pts[k])
    fx, fy = fig.transFigure.inverted().transform(axm.transData.transform((cx, cy)))
    fig.lines.append(Line2D([ix, fx], [iy, fy], transform=fig.transFigure,
                            color="#999999", lw=0.6, zorder=1))
    axm.plot([cx], [cy], "o", ms=2.2, mfc="white", mec="#555555", mew=0.7, zorder=6)

# --- b: full-width monthly recovery heatmap (two-letter row labels) ---
ax = fig.add_subplot(gs[1])
M3 = hm3.values.astype(float)
M3m = np.ma.masked_invalid(M3)
im = ax.imshow(M3m, aspect="auto", cmap=CM_ENC, vmin=0, vmax=1, interpolation="nearest")
xt = [f"{y}-01" for y in range(2020, 2026)]
pos = [list(hm3.columns).index(c) if c in hm3.columns else -0.5 for c in xt]
ax.set_xticks(pos); ax.set_xticklabels([c[:4] for c in xt], fontsize=5.2)
AB16 = {"东城区": "DC", "西城区": "XC", "朝阳区": "CY", "海淀区": "HD", "丰台区": "FT",
        "石景山区": "SJ", "门头沟区": "MT", "房山区": "FS", "通州区": "TZ", "大兴区": "DX",
        "顺义区": "SY", "昌平区": "CP", "平谷区": "PG", "怀柔区": "HR", "密云区": "MY", "延庆区": "YQ"}
ax.set_yticks(range(len(hm3.index)))
ax.set_yticklabels([AB16.get(d, d) for d in hm3.index], fontsize=5.2)
ax.set_xlabel("Year")
ax.spines[:].set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.022, pad=0.012)
cb.ax.tick_params(labelsize=5.0); cb.outline.set_linewidth(0.5)
cb.set_label("Encounter fraction C", fontsize=5.5)
ax.text(1.0, -0.34, "grey = missing district-months", transform=ax.transAxes,
        fontsize=4.4, color="#888888", ha="right", va="top")
panel_label(ax, "b", x=-0.062)
save_all(fig, "Fig3_threshold_activation")

# ================= Fig 4 (synthesis: persistence, robustness, mismatch) =================
fig = plt.figure(figsize=(180 * MM, 150 * MM))
gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.0], width_ratios=[1.28, 1.0],
                      left=0.115, right=0.970, top=0.955, bottom=0.105, hspace=0.50, wspace=0.27)

# --- a: first new threshold crossings, 2019-2025 ---
axa = fig.add_subplot(gs[0, 0])
fc = pd.read_csv(os.path.join(SRC, "Fig4a_crossing_timeline.csv"))
fc["x"] = fc["first_crossing_date"].map(ym_to_date)
ds_order = fc.sort_values("x", ascending=False)["district"].unique().tolist()
ypos = {d: i for i, d in enumerate(ds_order)}
markers = {"B1": "o", "B2": "s", "B3": "^", "B4": "D"}
for _, r in fc.iterrows():
    pers = bool(r["first_crossing_persistent"]) if pd.notna(r["first_crossing_persistent"]) else False
    axa.plot(r["x"], ypos[r["district"]], markers.get(r["layer_bucket"], "o"),
             ms=3.5, mfc=(C_ACC if pers else "white"), mec=C_ACC, mew=0.8, zorder=3)
axa.set_yticks(range(len(ds_order)))
axa.set_yticklabels([AB16[d] for d in ds_order], fontsize=4.8)
axa.set_ylim(len(ds_order) - 0.5, -0.7)
axa.set_xlim(dt.date(2019, 9, 1), dt.date(2025, 12, 31))
axa.xaxis.set_major_locator(mdates.YearLocator())
axa.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
axa.set_xlabel("First new threshold crossing since Sep 2019")
despine(axa)
hl_eg = [
    Line2D([], [], marker="o", ls="none", mfc=C_ACC, mec=C_ACC, ms=3.4, label="persistent"),
    Line2D([], [], marker="o", ls="none", mfc="white", mec=C_ACC, ms=3.4, label="transient"),
    Line2D([], [], marker="o", ls="none", mfc="#cccccc", mec="#888888", ms=3.1, label="B1"),
    Line2D([], [], marker="s", ls="none", mfc="#cccccc", mec="#888888", ms=3.1, label="B2"),
    Line2D([], [], marker="^", ls="none", mfc="#cccccc", mec="#888888", ms=3.1, label="B3"),
    Line2D([], [], marker="D", ls="none", mfc="#cccccc", mec="#888888", ms=3.1, label="B4"),
]
axa.legend(handles=hl_eg, loc="upper center", bbox_to_anchor=(0.5, -0.16), frameon=False,
           fontsize=4.4, ncol=6, handletextpad=0.25, columnspacing=0.65)
panel_label(axa, "a", x=-0.135)

# --- b: persistence of contact ---
axb = fig.add_subplot(gs[0, 1])
pc = pd.read_csv(os.path.join(SRC, "Fig4c_persistence.csv"))
pc = pc.sort_values(["longest_contact_run_months", "district_layer"], ascending=[False, True]).reset_index(drop=True)
for i, (_, r) in enumerate(pc.iterrows()):
    pers = bool(r["first_crossing_persistent"]) if pd.notna(r["first_crossing_persistent"]) else False
    axb.plot(r["longest_contact_run_months"], i, markers.get(r["layer_bucket"], "o"),
             ms=2.9, mfc=(C_ACC if pers else "white"), mec=C_ACC, mew=0.7, clip_on=False, zorder=3)
axb.set_yticks(range(len(pc)))
axb.set_yticklabels(pc["district"].map(AB16) + " " + pc["layer_bucket"], fontsize=4.0)
axb.set_ylim(len(pc) - 0.4, -0.8)
axb.set_xlim(-2, max(pc["longest_contact_run_months"]) * 1.12 + 4)
axb.set_xlabel("Longest contact run (months)")
axb.axvline(6, color=C_GW, lw=1.2, ls=(0, (2, 2)))
axb.text(7.0, 1.0, "6 month", fontsize=4.2, color=C_GW, fontweight="bold", va="top", ha="left")
despine(axb)
panel_label(axb, "b", x=-0.265)

# --- c: structural-depth robustness + class-share inset ---
axc = fig.add_subplot(gs[1, 0])
sc = pd.read_csv(os.path.join(SRC, "Fig5c_scenario_range.csv"))
yy = np.arange(len(sc))[::-1]
for i, (_, r) in enumerate(sc.iterrows()):
    axc.plot([r["shallow"], r["deep"]], [yy[i], yy[i]], color="#d9d9d9", lw=2.2,
             solid_capstyle="butt", zorder=1)
    axc.plot(r["central"], yy[i], "o", ms=3.1, mfc=C_ACC, mec="none", zorder=3)
axc.set_yticks(yy); axc.set_yticklabels(sc["district"].map(AB16), fontsize=4.7)
axc.set_xlabel("Encounter fraction C, Dec 2025")
axc.set_xlim(-0.04, 1.06); axc.set_xticks([0, 0.5, 1.0])
axc.legend(handles=[Line2D([], [], color="#d9d9d9", lw=2.2, label="shallow–deep range"),
                    Line2D([], [], marker="o", ls="none", mfc=C_ACC, mec="none", ms=3.1, label="central")],
           loc="upper left", frameon=False, fontsize=4.4, handlelength=1.4)
despine(axc)
# in-panel summary of the former Fig.5a three-state shares
f5a = pd.read_csv(os.path.join(SRC, "Fig5a_robustness.csv"))
share_classes = ["robust_no_contact", "depth_sensitive_contact", "robust_contact"]
share_cols = ["#d9d9d9", "#f2b88c", "#c8402a"]
shares = [float(f5a[f5a["class"] == c]["fraction"].iloc[0]) for c in share_classes]
x0s, y0s, ws, hs = 0.37, 0.055, 0.55, 0.045
left = x0s
for v, cc, label in zip(shares, share_cols, ["robust no-contact", "depth-sensitive", "robust contact"]):
    axc.add_patch(Rectangle((left, y0s), v * ws, hs, transform=axc.transAxes,
                            fc=cc, ec="white", lw=0.4, clip_on=False))
    axc.text(left + v * ws / 2, y0s + hs / 2, f"{v*100:.1f}%", transform=axc.transAxes,
             fontsize=3.8, ha="center", va="center", color="white" if cc == "#c8402a" else "#333333")
    axc.text(left + v * ws / 2, y0s + hs + 0.026, label,
             transform=axc.transAxes, fontsize=4.0, color="#666666", ha="center", va="bottom")
    left += v * ws + 0.025
panel_label(axc, "c", x=-0.145)

# --- d: hydrology-exposure rank mismatch (dumbbell / slope) ---
axd = fig.add_subplot(gs[1, 1])
rk = pd.read_csv(os.path.join(SRC, "Fig5b_rank_mismatch.csv"))
for _, r in rk.iterrows():
    y0r, y1r = float(r["recovery_rank_16"]), float(r["encounter_rate_rank_16"])
    ad = abs(y1r - y0r)
    col = C_ACC if ad >= 8 else ("#dd8452" if ad >= 4 else "#c9c9c9")
    lw = 1.5 if ad >= 8 else (1.0 if ad >= 4 else 0.7)
    axd.plot([0, 1], [y0r, y1r], color=col, lw=lw, alpha=0.95 if ad >= 4 else 0.75, zorder=2)
    axd.plot(0, y0r, "o", ms=3.0, mfc=C_GW, mec="white", mew=0.4, zorder=3)
    axd.plot(1, y1r, "o", ms=3.0, mfc=C_ACC, mec="white", mew=0.4, zorder=3)
# label the diagnostic mismatch cases on the exposure-rank side, with small leaders
lab_y = {"Yanqing": 0.9, "Fangshan": 2.1, "Tongzhou": 3.0, "Huairou": 4.2,
         "Shijingshan": 10.8, "Mentougou": 12.0, "Pinggu": 14.6}
for name, yy_lab in lab_y.items():
    rr = rk[rk["district_en"] == name]
    if not len(rr):
        continue
    y1r = float(rr["encounter_rate_rank_16"].iloc[0])
    axd.annotate(AB16[rr["district"].iloc[0]], xy=(1, y1r), xytext=(1.10, yy_lab), fontsize=4.3,
                 ha="left", va="center", color="#444444",
                 arrowprops=dict(arrowstyle="-", lw=0.4, color="#bbbbbb", shrinkA=0, shrinkB=2))
axd.set_xlim(-0.62, 1.78)
axd.set_ylim(16.6, 0.4)
axd.set_xticks([0, 1])
axd.set_xticklabels(["groundwater-rebound\nrank", "Dec-2025 encounter-rate\nrank"], fontsize=4.8)
axd.set_ylabel("Rank (1 = highest)")
despine(axd)
panel_label(axd, "d", x=-0.185)

save_all(fig, "_archive_before_spatial_restructure_20260922/Fig4_persistence_robustness_mismatch")
print("STAGE4B V2 DONE — Fig1-Fig3 plus archived legacy Fig4")
