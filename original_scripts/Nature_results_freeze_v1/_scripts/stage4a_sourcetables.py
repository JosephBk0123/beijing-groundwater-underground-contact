# -*- coding: utf-8 -*-
"""Build figure source tables from the revised results."""
import pandas as pd, numpy as np, os, json

BASE = r"local_raw_workspace"
V2 = os.path.join(BASE, "groundwater_underground_encounter_v2")
V11 = os.path.join(BASE, "historical_underground_space_backcast_v11")
FRZ = os.path.join(BASE, "Nature_results_freeze_v1")
SRC = os.path.join(FRZ, "03_figure_source_tables")
os.makedirs(SRC, exist_ok=True)

GD = os.path.join(BASE, "2026.09.04 自然基金委评审材料准备", "Multi-scale data assimilation reveals dynamic antecedent conditions for compound rainfall–groundwater hazards", "data", "地下水部分")

EN = {
    "东城区": "Dongcheng", "西城区": "Xicheng", "朝阳区": "Chaoyang", "丰台区": "Fengtai",
    "石景山区": "Shijingshan", "海淀区": "Haidian", "门头沟区": "Mentougou", "房山区": "Fangshan",
    "通州区": "Tongzhou", "顺义区": "Shunyi", "昌平区": "Changping", "大兴区": "Daxing",
    "怀柔区": "Huairou", "平谷区": "Pinggu", "密云区": "Miyun", "延庆区": "Yanqing",
}

# ============ Fig1a groundwater ============
c1 = pd.read_csv(os.path.join(GD, "beijing_plain_groundwater_1980_1999_current.csv"))
c2 = pd.read_csv(os.path.join(GD, "beijing_plain_groundwater_2000_2025_yearly_qc.csv"))
# prefer official year-end anchor; fallback december
c2y = c2[["year", "official_year_end_anchor_m", "december_depth_m", "monthly_mean_m", "spatial_support_regime", "qc_flag"]].copy()
c2y["depth_m"] = c2y["official_year_end_anchor_m"].fillna(c2y["december_depth_m"]).fillna(c2y["monthly_mean_m"])
c1y = c1[(c1["record_type"].str.contains("year", case=False, na=False)) | (c1["month"] == 12)].copy()
c1y = c1y.sort_values("date").groupby("year", as_index=False).last()
f1a = pd.concat([
    c1y[["year", "depth_m"]].assign(source="1980-1999 digitized bulletin"),
    c2y[["year", "depth_m"]].assign(source="2000-2025 monthly integrated"),
], ignore_index=True).sort_values("year")
f1a = f1a[(f1a["year"] >= 1986) & (f1a["year"] <= 2025)].reset_index(drop=True)
f1a["spatial_support_change_2021"] = f1a["year"] >= 2021
f1a.to_csv(os.path.join(SRC, "Fig1a_groundwater.csv"), index=False, encoding="utf-8-sig")

# ============ Fig1b stock proxy ============
sp = pd.read_csv(os.path.join(V11, "08_next_stage", "district_LUCC_stock_proxy_nodes.csv"))
agg = sp.groupby("year", as_index=False).agg(stock_sum_km2=("stock_area_km2", "sum"), raw_sum_km2=("raw_area_km2", "sum"), n_stock_constrained=("stock_constraint_applied", "sum"))
agg.to_csv(os.path.join(SRC, "Fig1b_stock_proxy.csv"), index=False, encoding="utf-8-sig")

# ============ Fig2a historical heatmap ============
h = pd.read_csv(os.path.join(V2, "03_historical", "historical_encounter_direct10_2000_2020.csv"))
tj = pd.read_csv(os.path.join(V2, "03_historical", "historical_contact_trajectory_summary.csv"))
hc = h[h["depth_scenario"] == "central"].pivot(index="district", columns="year", values="encounter_fraction")
# order by trajectory class
class_order = ["contact_reemerged", "persistent_contact", "contact_lost_during_depletion", "intermittent_or_uncertain", "persistent_no_contact"]
tj["co"] = tj["trajectory_class"].map({c: i for i, c in enumerate(class_order)})
order = tj.sort_values(["co", "enc_frac_2020"], ascending=[True, False])["district"].tolist()
hc = hc.loc[order]
hc.to_csv(os.path.join(SRC, "Fig2a_historical_heatmap.csv"), encoding="utf-8-sig")

# ============ Fig2b trajectory summary ============
tjb = tj[["district", "trajectory_class", "deepest_year", "deepest_depth_m", "enc_frac_2000", "enc_frac_at_deepest", "enc_frac_2020"]].copy()
tjb.to_csv(os.path.join(SRC, "Fig2b_trajectory_summary.csv"), index=False, encoding="utf-8-sig")

# ============ Fig2c flagship trajectories (Fangshan + Daxing) ============
hl = pd.read_csv(os.path.join(V2, "03_historical", "historical_layer_contact_long_2000_2020.csv"))
rows = []
for d in ["房山区", "大兴区"]:
    hh = h[(h["district"] == d) & (h["depth_scenario"] == "central")].sort_values("year")
    for _, r in hh.iterrows():
        rows.append({"district": EN[d], "district_cn": d, "year": r["year"], "groundwater_depth_m": r["groundwater_depth_m"], "encounter_fraction": r["encounter_fraction"], "series": "historical central"})
# representative thresholds per district (central scenario)
th = hl[(hl["depth_scenario"] == "central") & (hl["year"] == 2000)][["district", "layer_bucket", "representative_depth_m"]].drop_duplicates()
th = th[th["district"].isin(["房山区", "大兴区"])]
th["district_en"] = th["district"].map(EN)
th.to_csv(os.path.join(SRC, "Fig2c_thresholds.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(rows).to_csv(os.path.join(SRC, "Fig2c_flagship_trajectories.csv"), index=False, encoding="utf-8-sig")

# ============ Fig3a recovery heatmap ============
re_ = pd.read_csv(os.path.join(V2, "04_recovery", "recovery_encounter_monthly_16district.csv"))
re_["year_month"] = re_["year_month"].astype(str)
rec_c = re_[(re_["depth_scenario"] == "central") & (re_["year_month"] <= "2025-12")]
heat = rec_c.pivot(index="district", columns="year_month", values="encounter_fraction")
# order: 2025 C descending; missing all -> bottom by name
rs2 = pd.read_csv(os.path.join(FRZ, "01_revised_tables", "recovery_district_summary_v2.csv"))
c25 = rs2.set_index("district")["2025_encounter_fraction_central"]
order3 = c25.sort_values(ascending=False).index.tolist()
heat = heat.loc[[d for d in order3 if d in heat.index]]
heat.to_csv(os.path.join(SRC, "Fig3a_recovery_heatmap.csv"), encoding="utf-8-sig")

# ============ Fig3b-d exemplar threshold panels ============
rl = pd.read_csv(os.path.join(V2, "04_recovery", "recovery_layer_contact_long.csv"))
rl["year_month"] = rl["year_month"].astype(str)
for tag, d in [("Fig3b_fangshan", "房山区"), ("Fig3c_huairou", "怀柔区"), ("Fig3d_miyun", "密云区")]:
    gg = re_[(re_["district"] == d) & (re_["depth_scenario"] == "central")].sort_values("year_month")[["year_month", "groundwater_depth_m", "encounter_fraction"]]
    lt = rl[(rl["district"] == d) & (rl["depth_scenario"] == "central")][["layer_bucket", "representative_depth_m"]].drop_duplicates().sort_values("representative_depth_m")
    gg.assign(district=EN[d], district_cn=d).to_csv(os.path.join(SRC, f"{tag}_threshold.csv"), index=False, encoding="utf-8-sig")
    lt.assign(district=EN[d], district_cn=d).to_csv(os.path.join(SRC, f"{tag}_layer_thresholds.csv"), index=False, encoding="utf-8-sig")

# ============ Fig4a crossing timeline ============
rc = pd.read_csv(os.path.join(V2, "04_recovery", "recovery_threshold_crossings.csv"))
rc_c = rc[(rc["depth_scenario"] == "central") & (rc["layer_fraction"] > 1e-9)].copy()
fc = rc_c[rc_c["first_crossing_since_2019"].notna()].copy()
fc["first_crossing_date"] = fc["first_crossing_date"].astype(str)
fc["district_en"] = fc["district"].map(EN)
fc = fc.sort_values(["first_crossing_date", "district"])
fc.to_csv(os.path.join(SRC, "Fig4a_crossing_timeline.csv"), index=False, encoding="utf-8-sig")

# ============ Fig4c persistence ============
pc = rc_c[rc_c["n_contact_entries"] > 0].copy()
pc["district_en"] = pc["district"].map(EN)
pc["district_layer"] = pc["district_en"] + " " + pc["layer_bucket"]
pc = pc.sort_values("longest_contact_run_months")
pc.to_csv(os.path.join(SRC, "Fig4c_persistence.csv"), index=False, encoding="utf-8-sig")

# ============ Fig5a robustness ============
dr_main = pd.read_csv(os.path.join(FRZ, "01_revised_tables", "depth_scenario_robustness_2019_2025.csv"))
cnt = dr_main["robustness_class"].value_counts()
f5a = pd.DataFrame({"class": ["robust_no_contact", "robust_contact", "depth_sensitive_contact"],
                    "count": [int(cnt.get("robust_no_contact", 0)), int(cnt.get("robust_contact", 0)), int(cnt.get("depth_sensitive_contact", 0))]})
f5a["fraction"] = f5a["count"] / 1193
f5a.to_csv(os.path.join(SRC, "Fig5a_robustness.csv"), index=False, encoding="utf-8-sig")

# per-district robustness for ExtData4
per_d = dr_main.groupby(["district", "robustness_class"]).size().unstack(fill_value=0).reset_index()
per_d.to_csv(os.path.join(SRC, "ED4_robustness_per_district.csv"), index=False, encoding="utf-8-sig")
dr_ytd = pd.read_csv(os.path.join(FRZ, "01_revised_tables", "depth_scenario_robustness_2026YTD.csv"))
cnt_y = dr_ytd["robustness_class"].value_counts()
pd.DataFrame({"class": list(cnt_y.index), "count_2026ytd": list(cnt_y.values)}).to_csv(os.path.join(SRC, "ED4_robustness_2026ytd.csv"), index=False, encoding="utf-8-sig")

# ============ Fig5b rank mismatch ============
rk = pd.read_csv(os.path.join(FRZ, "01_revised_tables", "recovery_vs_encounter_rate_rank_2025_16district.csv"))
rk["district_en"] = rk["district"].map(EN)
rk.to_csv(os.path.join(SRC, "Fig5b_rank_mismatch.csv"), index=False, encoding="utf-8-sig")

# ============ Fig5c scenario range 2025 ============
last = re_[(re_["depth_scenario"].isin(["shallow", "central", "deep"])) & (re_["year_month"] == "2025-12")]
piv = last.pivot(index="district", columns="depth_scenario", values="encounter_fraction").reset_index()
piv["district_en"] = piv["district"].map(EN)
piv = piv.sort_values("central", ascending=False)
piv.to_csv(os.path.join(SRC, "Fig5c_scenario_range.csv"), index=False, encoding="utf-8-sig")

# ============ ExtData 1 selected years slopegraph ============
sel_years = [2000, 2005, 2010, 2015, 2020]
sl = hc[sel_years].reset_index()
sl.to_csv(os.path.join(SRC, "ED1_selected_years.csv"), index=False, encoding="utf-8-sig")

# ============ ExtData 2 MAIN vs RAW ============
hs = pd.read_csv(os.path.join(V2, "05_sensitivity", "historical_MAIN_vs_RAW_sensitivity.csv"))
hs["district_en"] = hs["district"].map(EN)
hs.to_csv(os.path.join(SRC, "ED2_main_raw.csv"), index=False, encoding="utf-8-sig")

# ============ ExtData 3 small multiples (16 district central) ============
sm = rec_c[["year_month", "district", "groundwater_depth_m", "encounter_fraction"]].copy()
sm["district_en"] = sm["district"].map(EN)
sm.to_csv(os.path.join(SRC, "ED3_small_multiples.csv"), index=False, encoding="utf-8-sig")

# ============ ExtData 5 groundwater QC ============
rg = pd.read_csv(os.path.join(V2, "04_recovery", "recovery_groundwater_monthly_16district.csv"))
rg["year_month"] = rg["year_month"].astype(str)
rg["district_en"] = rg["district"].map(EN)
rg["missing_flag"] = False
mm = pd.read_csv(os.path.join(V2, "08_audit", "missing_month_audit.csv"), dtype={"year_month": str})
mmset = set(zip(mm["district"], mm["year_month"]))
rg["missing_flag"] = [ (d, ym) in mmset for d, ym in zip(rg["district"], rg["year_month"]) ]
rg.to_csv(os.path.join(SRC, "ED5_gw_qc.csv"), index=False, encoding="utf-8-sig")

# ============ ExtData 6 depth-area profiles p_{d,l} ============
# layer structure from recovery layer long first month
first_month = rec_c["year_month"].min()
base_rows = rl[(rl["depth_scenario"] == "central")]
prof = base_rows.groupby(["district", "layer_no", "layer_bucket", "representative_depth_m"], as_index=False)["layer_fraction"].first()
prof["district_en"] = prof["district"].map(EN)
prof = prof.sort_values(["district", "layer_no"])
prof.to_csv(os.path.join(SRC, "ED6_depth_area_profiles.csv"), index=False, encoding="utf-8-sig")

# manifest
files = sorted(os.listdir(SRC))
with open(os.path.join(SRC, "_manifest.txt"), "w", encoding="utf-8") as f:
    for fn in files:
        if fn.startswith("_"): continue
        dfx = pd.read_csv(os.path.join(SRC, fn))
        f.write(f"{fn}: rows={len(dfx)} cols={list(dfx.columns)[:8]}\n")
print("STAGE4A DONE:", len(files), "source tables")
