"""Plot the R_LEA map and S7-S9 diagnostics. Run with --check-only for QA.

R_LEA is retained verbatim. Six-month runs are checked on calendar months
through 2025-12; missing months break a confirmed continuous run.
"""
from pathlib import Path
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patheffects as pe
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon, Rectangle
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kendalltau

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "03_figure_source_tables"
MAIN = ROOT / "04_main_figures"
SUPP = ROOT / "05_extended_data"
AUDIT = ROOT / "07_audit"
END = pd.Period("2025-12", freq="M")
AB = {"东城区": "DC", "西城区": "XC", "朝阳区": "CY", "海淀区": "HD", "丰台区": "FT",
      "石景山区": "SJ", "门头沟区": "MT", "房山区": "FS", "通州区": "TZ", "大兴区": "DX",
      "顺义区": "SY", "昌平区": "CP", "平谷区": "PG", "怀柔区": "HR", "密云区": "MY", "延庆区": "YQ"}
BLUE, RED, GREY = "#1f4e79", "#c8402a", "#777777"
CMAP = LinearSegmentedColormap.from_list("enc", ["#faf7f2", "#f2b88c", "#e07b4f", "#c8402a", "#8c2318"])
MARKERS = {"B1": "o", "B2": "s", "B3": "^", "B4": "D"}
plt.rcParams.update({"font.family": "Arial", "font.size": 6, "axes.labelsize": 6.5,
                     "xtick.labelsize": 5.5, "ytick.labelsize": 5.5, "axes.linewidth": .7,
                     "xtick.major.width": .6, "ytick.major.width": .6,
                     "pdf.fonttype": 42, "svg.fonttype": "none"})


def contact_runs(series):
    """Return (start, end, observed consecutive months) for monthly contact=1."""
    result, start = [], None
    for month, value in series.items():
        if value == 1 and start is None:
            start = month
        if value != 1 and start is not None:
            result.append((start, month - 1, month.ordinal - start.ordinal))
            start = None
    if start is not None:
        result.append((start, series.index[-1], series.index[-1].ordinal - start.ordinal + 1))
    return result


def build_sources():
    metrics = pd.read_csv(SRC / "Fig5_metrics_by_district.csv").set_index("district_cn")
    monthly = pd.read_csv(SRC / "fig5_inputs/groundwater_underground_encounter_v2/04_recovery/recovery_encounter_monthly_16district.csv")
    monthly = monthly[(monthly.depth_scenario == "central") & (monthly.year_month <= str(END))].copy()
    monthly["period"] = pd.PeriodIndex(monthly.year_month, freq="M")
    profiles = pd.read_csv(SRC / "ED6_depth_area_profiles.csv")
    scenarios = pd.read_csv(SRC / "Fig5c_scenario_range.csv").set_index("district")
    ranks = pd.read_csv(SRC / "Fig5b_rank_mismatch.csv").set_index("district")
    old_crossings = pd.read_csv(SRC / "Fig4a_crossing_timeline.csv")
    district_rows, layer_rows = [], []
    for district, m in metrics.iterrows():
        observed = monthly[monthly.district == district].set_index("period").sort_index()
        full = observed.reindex(pd.period_range(observed.index[0], END, freq="M"))
        contact = (full.encounter_fraction > 1e-9).astype(float).where(full.encounter_fraction.notna())
        runs = contact_runs(contact)
        start_contact, end_contact = bool(contact.iloc[0]), bool(contact.iloc[-1])
        longest = max((r[2] for r in runs), default=0)
        terminal = next((r[2] for r in runs if r[1] == END), 0)
        if start_contact:
            category = "pre_existing_contact"
        elif not runs:
            category = "no_contact_through_2025"
        elif terminal >= 6:
            category = "new_persistent_activation"
        elif not end_contact and longest < 6:
            category = "transient_only_contact"
        else:
            raise ValueError(f"Needs explicit class beyond the agreed four: {district}")
        first_persistent = next((str(a) for a, b, n in runs if n >= 6 and a != full.index[0]), "")
        local_rows = []
        for _, layer in profiles[(profiles.district == district) & (profiles.layer_fraction > 1e-9)].iterrows():
            state = (full.groundwater_depth_m <= layer.representative_depth_m).astype(float).where(full.groundwater_depth_m.notna())
            layer_runs = contact_runs(state)
            new_runs = [r for r in layer_runs if r[0] != full.index[0] and state.get(r[0] - 1, np.nan) == 0]
            old = old_crossings[(old_crossings.district == district) & (old_crossings.layer_bucket == layer.layer_bucket)]
            if old.empty:
                continue
            start = pd.Period(old.iloc[0].first_crossing_date, freq="M")
            first = next(r for r in layer_runs if r[0] == start)
            if first[2] >= 6:
                status = "confirmed_6_month"
            elif state.get(first[1] + 1, np.nan) == 0:
                status = "transient_first_run"
            else:
                status = "insufficient_followup"
            row = dict(district=district, district_code=AB[district], layer_bucket=layer.layer_bucket,
                       representative_depth_m=layer.representative_depth_m,
                       first_new_crossing=str(start), first_run_end=str(first[1]), first_run_months=first[2],
                       first_run_status=status,
                       first_persistent_crossing=next((str(a) for a, b, n in new_runs if n >= 6), ""),
                       max_contact_run_months=max(r[2] for r in layer_runs),
                       legacy_max_contact_run_months=int(old.iloc[0].longest_contact_run_months),
                       final_contact_state="contact" if state.iloc[-1] == 1 else "no_contact",
                       legacy_first_crossing_persistent=bool(old.iloc[0].first_crossing_persistent))
            local_rows.append(row)
            layer_rows.append(row)
        rank, sc = ranks.loc[district], scenarios.loc[district]
        persistent_dates = [r["first_persistent_crossing"] for r in local_rows if r["first_persistent_crossing"]]
        first_dates = [r["first_new_crossing"] for r in local_rows]
        district_rows.append(dict(
            district=district, district_code=AB[district], district_en=m.district_en,
            central_six_flag=int(m.central_six_flag), series_start_month=str(full.index[0]),
            T_d=m.T_d, D_Td=m.D_Td, C_Td=m.C_Td,
            C_start=float(full.encounter_fraction.iloc[0] * 100), C_2025=m.C_2025,
            delta_C_RE=m.delta_C_RE, first_activation=m.t_first,
            first_new_crossing=min(first_dates, default=""),
            first_persistent_crossing=min(persistent_dates, default=""),
            first_persistent_district_contact=first_persistent,
            waiting_months=m.wait_months, delta_C_first_pp=m.delta_C_first,
            R_LEA=m.R_LEA_pp_per_year, max_contact_run_months=longest,
            terminal_contact_run_months=terminal,
            start_contact_state="contact" if start_contact else "no_contact",
            final_contact_state="contact" if end_contact else "no_contact",
            activation_class=category, C2025_shallow=100 * sc.shallow,
            C2025_central=100 * sc.central, C2025_deep=100 * sc.deep,
            rebound_m=rank.recovery_from_local_deepest_to_2025_m,
            rebound_rank=rank.recovery_rank_16, encounter_rank=rank.encounter_rate_rank_16,
            valid_months=len(observed), missing_months=int(full.encounter_fraction.isna().sum()),
            T_d_at_observation_boundary=int(m.left_boundary_flag), frozen_metric_status=m.status,
        ))
    districts, layers = pd.DataFrame(district_rows), pd.DataFrame(layer_rows)
    # Alternative reference used for the sensitivity comparison.
    districts["waiting_months_from_series_start"] = [
        (pd.Period(t, freq="M").ordinal - pd.Period(s, freq="M").ordinal) if pd.notna(t) else np.nan
        for t, s in zip(districts.first_activation, districts.series_start_month)]
    districts["R_LEA_series_start_sensitivity"] = 12 * districts.delta_C_first_pp / districts.waiting_months_from_series_start
    robust = pd.read_csv(ROOT / "01_revised_tables/depth_scenario_robustness_2019_2025.csv")
    robustness = robust.groupby("robustness_class").size().rename("count").reset_index()
    robustness["fraction"] = robustness["count"] / len(robust)
    n10 = districts.dropna(subset=["R_LEA"])
    r16 = spearmanr(districts.rebound_m, districts.C2025_central)
    t16 = kendalltau(districts.rebound_m, districts.C2025_central)
    r10 = spearmanr(n10.R_LEA, n10.delta_C_RE)
    stats = dict(rank16_rho=float(r16.statistic), rank16_tau_b=float(t16.statistic), rank16_n=len(districts),
                 R_LEA_escalation_rho=float(r10.statistic), R_LEA_escalation_p=float(r10.pvalue), R_LEA_escalation_n=len(n10))
    stats["reference_sensitivity_rank_rho_n10"] = float(spearmanr(n10.R_LEA, n10.R_LEA_series_start_sensitivity).statistic)
    return districts, layers, robustness, stats


def check_sources(d, layers, robust, stats):
    # Missing calendar months interrupt contact runs.
    sample = pd.Series([0, 1, 1, np.nan, 1, 1, 0], index=pd.period_range("2020-01", periods=7, freq="M"))
    assert [r[2] for r in contact_runs(sample)] == [2, 2]
    assert len(d) == 16 and d.district.nunique() == 16 and d.valid_months.sum() == 1193
    assert len(layers) == 24 and not layers.duplicated(["district", "layer_bucket"]).any()
    assert layers.first_run_status.value_counts().to_dict() == {
        "confirmed_6_month": 7, "transient_first_run": 12, "insufficient_followup": 5}
    assert d.activation_class.value_counts().to_dict() == {
        "new_persistent_activation": 9, "pre_existing_contact": 3,
        "no_contact_through_2025": 3, "transient_only_contact": 1}
    original = pd.read_csv(SRC / "Fig5_metrics_by_district.csv").set_index("district_cn")
    assert np.allclose(d.set_index("district").R_LEA.sort_index(), original.R_LEA_pp_per_year.sort_index(), equal_nan=True)
    assert np.max(abs(d.C_2025 - d.C2025_central)) <= .006
    assert (d.C2025_shallow <= d.C2025_central + 1e-9).all()
    assert (d.C2025_central <= d.C2025_deep + 1e-9).all()
    assert dict(zip(robust.robustness_class, robust["count"])) == {
        "robust_no_contact": 459, "robust_contact": 409, "depth_sensitive_contact": 325}
    assert abs(stats["rank16_rho"] + .5871) < .0001
    assert abs(stats["rank16_tau_b"] + .4380) < .0001
    assert abs(stats["R_LEA_escalation_rho"] - .13939393939393938) < 1e-10
    assert stats["R_LEA_escalation_n"] == 10
    assert (layers.loc[layers.first_run_status == "confirmed_6_month", "first_run_months"] >= 6).all()


def save(fig, folder, name):
    folder.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(folder / f"{name}.{ext}", dpi=400, facecolor="white")
    plt.close(fig)


def clean(ax, letter=None):
    ax.spines[["top", "right"]].set_visible(False)
    if letter:
        ax.text(-.16, 1.035, letter, transform=ax.transAxes, fontsize=8, weight="bold", va="bottom")


def spatial(d):
    rings = pd.read_csv(SRC / "_beijing_district_rings.csv")
    assert set(rings.district) == set(d.district)
    data = d.set_index("district")
    fig = plt.figure(figsize=(180 / 25.4, 170 / 25.4))
    ax = fig.add_axes([.075, .19, .85, .79])
    norm = Normalize(0, d.loc[d.activation_class == "new_persistent_activation", "R_LEA"].max())
    halo = [pe.withStroke(linewidth=1.4, foreground="white")]
    nudge = {"西城区": (-.017, .005), "东城区": (.085, -.050), "朝阳区": (.035, .010),
             "海淀区": (-.010, .018), "石景山区": (-.018, -.006), "丰台区": (-.010, -.028)}
    for district, group in rings.groupby("district"):
        row = data.loc[district]
        kind = row.activation_class
        face = CMAP(norm(row.R_LEA)) if kind == "new_persistent_activation" else ("#e5e5e5" if kind == "pre_existing_contact" else "white")
        hatch = "." if kind == "pre_existing_contact" else ("///" if kind == "no_contact_through_2025" else None)
        for (_, ring), coords in group.groupby(["part", "ring"]):
            if ring == 0:
                ax.add_patch(Polygon(coords[["x", "y"]].to_numpy(), closed=True,
                                     facecolor=face, edgecolor="#888888", lw=.55, hatch=hatch))
        outer = group[group.ring == 0]
        biggest = outer.groupby("part").size().idxmax()
        center = outer[outer.part == biggest][["x", "y"]].mean()
        dx, dy = nudge.get(district, (0, .015))
        if district == "东城区":
            ax.annotate(row.district_code, center, xytext=(center.x + dx, center.y + dy),
                        fontsize=6, ha="left", va="center", path_effects=halo,
                        arrowprops=dict(arrowstyle="-", lw=.45, color=GREY), zorder=6)
        else:
            ax.text(center.x + dx, center.y + dy, row.district_code,
                    fontsize=6 if district in nudge else 7, ha="center", va="center", path_effects=halo, zorder=5)
        if kind == "transient_only_contact":
            ax.plot(center.x + .10, center.y - .08, "x", color="#333333", ms=8, mew=1.5)
    xmin, xmax, ymin, ymax = rings.x.min(), rings.x.max(), rings.y.min(), rings.y.max()
    width, height = xmax - xmin, ymax - ymin
    ax.set_xlim(xmin - .03 * width, xmax + .03 * width)
    ax.set_ylim(ymin - .03 * height, ymax + .03 * height)
    ax.set_aspect(1 / np.cos(np.deg2rad(40)))
    ax.axis("off")
    nx, ny = xmin + .07 * width, ymax - .19 * height
    ax.annotate("", (nx, ny + .12 * height), (nx, ny),
                arrowprops=dict(arrowstyle="-|>", color="#333333", lw=1.1, mutation_scale=12))
    ax.text(nx, ny + .14 * height, "N", ha="center", fontsize=7)
    scale = 20 / (111.32 * np.cos(np.deg2rad(40)))
    sx, sy = xmax - .29 * width, ymin + .06 * height
    ax.plot([sx, sx + scale], [sy, sy], color="#333333", lw=1.4)
    for x in (sx, sx + scale):
        ax.plot([x, x], [sy - .007 * height, sy + .007 * height], color="#333333", lw=.9)
    ax.text(sx + scale / 2, sy + .018 * height, "20 km", ha="center", fontsize=6)
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=CMAP), cax=fig.add_axes([.25, .142, .50, .020]), orientation="horizontal")
    cb.set_label(r"Legacy exposure activation intensity, $R_{\mathrm{LEA}}$ (pp yr$^{-1}$)", fontsize=7)
    cb.ax.tick_params(labelsize=6, width=.6, length=2)
    cb.outline.set_linewidth(.6)
    fig.legend(handles=[
        Patch(facecolor="#e5e5e5", edgecolor="#888888", hatch=".", label="Pre-existing contact\nat series start (n = 3)"),
        Line2D([], [], marker="x", color="#333333", ls="none", mew=1.2, label="Transient-only contact\n(n = 1)"),
        Patch(facecolor="white", edgecolor="#888888", hatch="///", label="No contact through\nDec 2025 (n = 3)"),
    ], loc="lower center", bbox_to_anchor=(.5, .012), ncol=3, frameon=False,
        fontsize=6, handlelength=2.3, handleheight=1.8, columnspacing=2.2)
    save(fig, MAIN, "Fig4_spatial_legacy_activation")


def first_run_style(status):
    return (RED, RED) if status == "confirmed_6_month" else (("white", RED) if status == "transient_first_run" else ("#bdbdbd", "#777777"))


def timing(d, layers):
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(180 / 25.4, 128 / 25.4),
                                 gridspec_kw={"width_ratios": [1.08, 1.0, 1.12]})
    fig.subplots_adjust(left=.055, right=.99, top=.94, bottom=.23, wspace=.54)
    order = layers.sort_values("first_new_crossing", ascending=False).district.unique().tolist()
    for _, r in layers.iterrows():
        face, edge = first_run_style(r.first_run_status)
        a.plot(pd.Period(r.first_new_crossing, freq="M").to_timestamp(), order.index(r.district),
               marker=MARKERS[r.layer_bucket], mfc=face, mec=edge, ms=3.7, mew=.8, ls="none")
    a.set_yticks(range(len(order)), [AB[x] for x in order])
    a.invert_yaxis()
    a.set_xlim(pd.Timestamp("2019-09-01"), pd.Timestamp("2026-01-01"))
    a.xaxis.set_major_locator(mdates.YearLocator(2)); a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    a.set_xlabel("First new threshold crossing")
    clean(a, "a")
    sub = d.dropna(subset=["R_LEA"])
    xmax, ymax = sub.waiting_months.max() * 1.10, sub.delta_C_first_pp.max() * 1.16
    for rate in (.5, 1, 2, 3):
        x = min(xmax, ymax * 12 / rate)
        b.plot([0, x], [0, rate * x / 12], "--", color="#bbbbbb", lw=.5, zorder=1)
        b.text(x - 1, rate * x / 12 + .10, f"{rate:g}", ha="right", fontsize=5, color=GREY)
    offsets = {"XC": (3, .28), "MY": (-3, .35), "FT": (3, .24), "HR": (3, -.45),
               "DC": (3, .20), "SJ": (3, .20), "MT": (3, -.5), "HD": (-3, .32), "DX": (-3, .3), "CP": (-3, .35)}
    for _, r in sub.iterrows():
        marker = "o" if r.central_six_flag else "^"
        b.plot(r.waiting_months, r.delta_C_first_pp, marker, color=BLUE,
               mfc=BLUE if r.central_six_flag else "#9ecae1", ms=4.1, mew=.6, zorder=3)
        if r.activation_class == "transient_only_contact":
            b.plot(r.waiting_months, r.delta_C_first_pp, "x", color="#333333", ms=6, mew=1.1)
        dx, dy = offsets[r.district_code]
        b.text(r.waiting_months + dx, r.delta_C_first_pp + dy, r.district_code, fontsize=5.3,
               ha="left" if dx > 0 else "right", va="center")
    b.set(xlim=(0, xmax), ylim=(0, ymax), xlabel="Waiting time to first\nactivation (months)", ylabel=r"First exposure jump, $\Delta C_{\mathrm{first}}$ (pp)")
    b.set_xticks([0, 40, 80, 120])
    clean(b, "b")
    persistence = layers.sort_values(["max_contact_run_months", "district_code", "layer_bucket"], ascending=[False, True, True])
    for i, (_, r) in enumerate(persistence.iterrows()):
        face, edge = first_run_style(r.first_run_status)
        c.plot(r.max_contact_run_months, i, MARKERS[r.layer_bucket], mfc=face, mec=edge, ms=3.3, mew=.7)
    c.set_yticks(range(len(persistence)), persistence.district_code + " " + persistence.layer_bucket, fontsize=4.9)
    c.set_ylim(len(persistence) - .4, -.8); c.set_xlim(-2, 75)
    c.set_xlabel("Longest continuous\ncontact run (months)")
    c.axvline(6, color=BLUE, lw=1.2, ls=(0, (2, 2)))
    c.text(8, 1, "6 month", color=BLUE, weight="bold", fontsize=5.2, va="top")
    clean(c, "c")
    status_handles = [Line2D([], [], marker="o", ls="none", ms=4, mfc=face, mec=edge, label=label)
                      for face, edge, label in [(RED, RED, "First run ≥6 months"), ("white", RED, "First run <6 months; exited"), ("#bdbdbd", GREY, "First run <6 months; censored")]]
    fig.legend(handles=status_handles, loc="lower center", bbox_to_anchor=(.50, .085), ncol=3, frameon=False, fontsize=5.2, columnspacing=1.1)
    fig.legend(handles=[Line2D([], [], marker=m, color=GREY, ls="none", ms=3.5, label=layer) for layer, m in MARKERS.items()],
               loc="lower left", bbox_to_anchor=(.04, .025), ncol=4, frameon=False, fontsize=5.2)
    fig.legend(handles=[Line2D([], [], marker="o", color=BLUE, ls="none", label="Central six"),
                        Line2D([], [], marker="^", mfc="#9ecae1", mec=BLUE, ls="none", label="Other districts")],
               loc="lower right", bbox_to_anchor=(.99, .025), ncol=2, frameon=False, fontsize=5.2)
    save(fig, SUPP, "Supplementary_FigS7_timing_and_persistence")


def sensitivity(d, robust):
    fig = plt.figure(figsize=(180 / 25.4, 112 / 25.4))
    ax = fig.add_axes([.095, .29, .88, .67])
    rows = d.sort_values("C2025_central", ascending=False)
    for i, (_, r) in enumerate(rows.iterrows()):
        ax.plot([r.C2025_shallow / 100, r.C2025_deep / 100], [i, i], color="#cccccc", lw=2.3, zorder=1)
        ax.plot(r.C2025_shallow / 100, i, "v", color=BLUE, ms=3.6, mfc="white", mew=.7)
        ax.plot(r.C2025_deep / 100, i, "^", color=GREY, ms=3.6, mfc="white", mew=.7)
        ax.plot(r.C2025_central / 100, i, "o", color=RED, ms=3.8, zorder=3)
    ax.set_yticks(range(len(rows)), rows.district_code)
    ax.set_ylim(len(rows) - .4, -.6); ax.set_xlim(-.03, 1.04)
    ax.set_xlabel("Encounter fraction C, Dec 2025")
    ax.legend(handles=[Line2D([], [], marker="v", ls="none", mec=BLUE, mfc="white", label="shallow"),
                       Line2D([], [], marker="o", ls="none", color=RED, label="central"),
                       Line2D([], [], marker="^", ls="none", mec=GREY, mfc="white", label="deep")],
              loc="lower right", frameon=False, ncol=3, fontsize=6)
    clean(ax)
    left, width, gap = .12, .80, .017
    for key, label, col in [("robust_no_contact", "robust no-contact", "#d9d9d9"),
                            ("depth_sensitive_contact", "depth-sensitive", "#f2b88c"),
                            ("robust_contact", "robust contact", RED)]:
        row = robust.set_index("robustness_class").loc[key]
        w = row.fraction * width
        fig.add_artist(Rectangle((left, .08), w, .04, transform=fig.transFigure, fc=col, ec="white", lw=.4))
        fig.text(left + w / 2, .10, f"{row.fraction:.1%}", ha="center", va="center", fontsize=6, color="white" if col == RED else "#333333")
        fig.text(left + w / 2, .14, f"{label}\n{int(row['count']):,} / 1,193", ha="center", va="bottom", fontsize=6, color="#555555")
        left += w + gap
    fig.text(.5, .025, "Sep 2019–Dec 2025 · 1,193 valid district-months", ha="center", fontsize=6)
    save(fig, SUPP, "Supplementary_FigS8_structural_depth_sensitivity")


def alternatives(d, stats):
    fig, (a, b) = plt.subplots(1, 2, figsize=(180 / 25.4, 112 / 25.4))
    fig.subplots_adjust(left=.07, right=.98, top=.85, bottom=.18, wspace=.36)
    for _, r in d.iterrows():
        delta = abs(r.encounter_rank - r.rebound_rank)
        color = RED if delta >= 8 else ("#dd8452" if delta >= 4 else "#c9c9c9")
        a.plot([0, 1], [r.rebound_rank, r.encounter_rank], color=color, lw=1.25 if delta >= 8 else .8)
        a.plot(0, r.rebound_rank, "o", ms=3, mfc=BLUE, mec="white", mew=.4)
        a.plot(1, r.encounter_rank, "o", ms=3, mfc=RED, mec="white", mew=.4)
    label_y = {"YQ": .9, "FS": 2.1, "TZ": 3, "HR": 4.2, "SJ": 10.8, "MT": 12, "PG": 14.6}
    for code, y in label_y.items():
        r = d.set_index("district_code").loc[code]
        a.annotate(code, (1, r.encounter_rank), (1.10, y), fontsize=5.6, va="center",
                   arrowprops=dict(arrowstyle="-", color="#aaaaaa", lw=.45))
    a.set_xlim(-.24, 1.53); a.set_ylim(16.6, .4)
    a.set_xticks([0, 1], ["Groundwater-rebound\nrank", "Dec-2025 encounter\nrank"])
    a.set_ylabel("Rank (1 = highest)")
    a.text(.5, 1.05, f"Spearman ρ = {stats['rank16_rho']:.2f}; Kendall τ-b = {stats['rank16_tau_b']:.2f}\nn = 16; average ranks for ties",
           transform=a.transAxes, ha="center", fontsize=5.7, va="bottom")
    clean(a, "a")
    sub = d.dropna(subset=["R_LEA"])
    for _, r in sub.iterrows():
        b.scatter(r.R_LEA, r.delta_C_RE, s=6 + 2.2 * r.C_2025,
                  marker="o" if r.central_six_flag else "^", c=BLUE if r.central_six_flag else "#9ecae1",
                  edgecolors=BLUE, linewidths=.6, zorder=4)
        if r.activation_class == "transient_only_contact":
            b.plot(r.R_LEA, r.delta_C_RE, "x", color="#333333", ms=6, mew=1.1)
    offsets = {"XC": (.06, 1.1), "MY": (.06, .9), "FT": (-.10, -2.2), "HR": (.06, .2),
               "DC": (.07, 1.1), "SJ": (.06, 1), "MT": (.07, .9), "HD": (.07, .9), "DX": (.06, .9), "CP": (.06, .8)}
    for _, r in sub.iterrows():
        dx, dy = offsets[r.district_code]
        b.text(r.R_LEA + dx, r.delta_C_RE + dy, r.district_code, fontsize=5.5,
               path_effects=[pe.withStroke(linewidth=1.3, foreground="white")], zorder=6)
    b.axvline(sub.R_LEA.median(), color="#bbbbbb", lw=.55, ls="--")
    b.axhline(sub.delta_C_RE.median(), color="#bbbbbb", lw=.55, ls="--")
    b.set(xlim=(-.10, sub.R_LEA.max() * 1.16), ylim=(-1, sub.delta_C_RE.max() * 1.18),
          xlabel="First-activation intensity,\n" + r"$R_{\mathrm{LEA}}$ (pp yr$^{-1}$)",
          ylabel=r"Exposure escalation, $\Delta C_{\mathrm{RE}}$ (pp)")
    b.text(.5, 1.05, f"Spearman ρ = {stats['R_LEA_escalation_rho']:.2f}; p = {stats['R_LEA_escalation_p']:.3f}; n = 10",
           transform=b.transAxes, ha="center", fontsize=5.7, va="bottom")
    for size in (10, 30, 50):
        b.scatter([], [], s=6 + 2.2 * size, facecolors="none", edgecolors="#555555", lw=.6, label=f"{size} pp")
    b.legend(title=r"$C_{2025}$", title_fontsize=5.5, fontsize=5.3, frameon=False, loc="upper right", labelspacing=.9)
    clean(b, "b")
    fig.legend(handles=[Line2D([], [], marker="o", color=BLUE, ls="none", label="Central six"),
                        Line2D([], [], marker="^", mfc="#9ecae1", mec=BLUE, ls="none", label="Other districts"),
                        Line2D([], [], marker="x", color="#333333", ls="none", label="Transient-only contact")],
               loc="lower center", bbox_to_anchor=(.66, .02), ncol=3, fontsize=5.2, frameon=False)
    save(fig, SUPP, "Supplementary_FigS9_alternative_screening_metrics")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    d, layers, robust, stats = build_sources()
    check_sources(d, layers, robust, stats)
    print(json.dumps({"district_classes": d.activation_class.value_counts().to_dict(),
                      "first_run_classes": layers.first_run_status.value_counts().to_dict(), "statistics": stats}, ensure_ascii=True))
    if args.check_only:
        print("PASS: source identities, retained R_LEA, calendar continuity, classes and correlations")
        return
    for table, name in [(d, "fig4_spatial_legacy_activation_source.csv"),
                        (layers, "figS7_layer_timing_persistence_source.csv"),
                        (robust, "figS8_robustness_summary_source.csv")]:
        table.to_csv(SRC / name, index=False, encoding="utf-8-sig")
    (AUDIT / "fig4_spatial_s7_s9_statistics.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    spatial(d)
    timing(d, layers)
    sensitivity(d, robust)
    alternatives(d, stats)
    print("Saved Fig4 and Supplementary S7-S9 in PNG, PDF and SVG.")


if __name__ == "__main__":
    main()
