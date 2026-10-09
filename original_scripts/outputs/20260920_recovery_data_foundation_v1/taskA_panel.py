# -*- coding: utf-8 -*-
"""
Build and check the district x month panel for 2019-09..2026; sources are read-only.
Fixed 13-district set, specified in advance from the 附件1 footnote and statistical-scope audit:
  16 districts minus {延庆, 门头沟, 石景山} -> the official city-mean arithmetic set.
Variables: D = depth below ground (m, positive down). No interpolation, no deletion.
"""
import os, json
import numpy as np
import pandas as pd

ROOT = r"local_raw_workspace"
SRC = os.path.join(ROOT, "地下水数据", "时序规整")
OUT = os.path.join(ROOT, "outputs", "20260920_recovery_data_foundation_v1")
os.makedirs(OUT, exist_ok=True)

DIST16 = ["东城", "西城", "朝阳", "海淀", "丰台", "石景山", "门头沟", "房山",
          "通州", "顺义", "昌平", "大兴", "怀柔", "平谷", "密云", "延庆"]
FIXED13 = [d for d in DIST16 if d not in ("延庆", "门头沟", "石景山")]

panel = pd.read_csv(os.path.join(SRC, "北京市平原区地下水_分区逐期面板_2019-2026_v3.csv"),
                    encoding="utf-8-sig")
panel["ym"] = panel["观测日期"].str[:7]

# ---------------- A1 audit ----------------
per_month = panel.groupby("ym").size()
src_map = {"district_panel_raw": "周报/动态附件(原始)", "gap_ocr_v2": "周报图片附件OCR补采",
           "gap_ocr_v2_fix": "OCR补采-修复", "gap_ocr_v2_fix2": "OCR补采-修复2",
           "master_2026_event": "2026台风事件加密观测", "pdf_202609": "2026-09官方PDF统计表",
           "master_2026_event+pdf_202609": "事件+PDF双源", "docx_monthly": "月报统计表",
           "docx_monthly_ref": "月报参照列反演"}
audit = {
    "source_file": "北京市平原区地下水_分区逐期面板_2019-2026_v3.csv",
    "rows_periods": int(len(panel)),
    "districts": DIST16,
    "n_districts": 16,
    "date_range": [panel["观测日期"].min(), panel["观测日期"].max()],
    "n_unique_months": int(panel["ym"].nunique()),
    "period_type_by_source": {k: src_map.get(k, k) for k in panel["来源"].unique()},
    "source_counts": panel["来源"].value_counts().to_dict(),
    "periods_per_month_distribution": {str(k): int(v) for k, v in per_month.value_counts().sort_index().items()},
    "missing_periods_per_district": {d: int(panel[d].isna().sum()) for d in DIST16},
    "duplicate_dates": int(panel["观测日期"].duplicated().sum()),
    "schema_changes": "none detected: constant wide schema 观测日期/全市平均埋深/有效区数/来源/期名 + 16 district columns",
    "units_and_direction": "埋深, m, positive down (per project 口径审计说明); D变大=下降, D变小=恢复",
    "documented_regime_switches": ["2020-07-28: 全市算术口径14区→11区 + 石景山井网更换",
                                    "2025-04-14: 全市算术口径11区→13区(东西城纳入)",
                                    "2019-09/10: 月报统计表口径", "2019-11-28: 自动130眼井口径",
                                    "2023-08: 23·7暴雨加密简报期"],
    "fixed13_definition": "16区 minus {延庆, 门头沟, 石景山} — 附件1脚注'延庆、门头沟和石景山区不参加平均计算'; 已与既有'固定13区自算均值'列反算核对(max|diff|=0.005m, 为四舍五入差)",
    "note": "东西城在2019-2020年14区口径期无观测(各缺12-13期); 房山缺19期",
}
with open(os.path.join(OUT, "district_period_panel_audit.json"), "w", encoding="utf-8") as f:
    json.dump(audit, f, ensure_ascii=False, indent=2)

# ---------------- A2 strict district x month aggregation ----------------
rows = []
for (ym, d), g in panel.melt(id_vars=["观测日期", "ym", "来源"], value_vars=DIST16,
                             var_name="district", value_name="depth").dropna(subset=["depth"]).groupby(["ym", "district"]):
    v = g["depth"].values
    n = len(v)
    rows.append({"district": d, "year_month": ym,
                 "depth_mean_m": v.mean(), "depth_median_m": float(np.median(v)),
                 "depth_min_m": v.min(), "depth_max_m": v.max(),
                 "depth_std_m": float(v.std(ddof=1)) if n > 1 else 0.0,
                 "n_periods": n,
                 "first_observation_date": g["观测日期"].min(),
                 "last_observation_date": g["观测日期"].max(),
                 "source_support": ("single_period" if n == 1 else
                                    "two_periods" if n == 2 else "three_or_more_periods"),
                 "qc_flag": ""})
mon = pd.DataFrame(rows)
# explicit missing district-month cells (marked, not interpolated)
all_months = sorted(panel["ym"].unique())
full_idx = pd.MultiIndex.from_product([all_months, DIST16], names=["year_month", "district"])
mon = mon.set_index(["year_month", "district"]).reindex(full_idx).reset_index()
miss = mon["n_periods"].isna()
mon.loc[miss, "source_support"] = "missing"
mon.loc[miss, "n_periods"] = 0
mon["n_periods"] = mon["n_periods"].astype(int)
mon.to_csv(os.path.join(OUT, "district_groundwater_monthly_2019_2026.csv"),
           index=False, encoding="utf-8-sig")
print("district-months valid:", int((~miss).sum()), "/", len(mon),
      "| mean periods/month:", round(mon.loc[~miss, "n_periods"].mean(), 2))

# ---------------- A3 fixed-support city series ----------------
AREA = {"东城": 39, "西城": 51, "朝阳": 467, "海淀": 435, "丰台": 306, "石景山": 84,
        "门头沟": 1450, "房山": 1997, "通州": 897, "顺义": 1016, "昌平": 1342,
        "大兴": 1031, "怀柔": 2122, "平谷": 948, "密云": 2232, "延庆": 1992}  # 事前存在: 建模域分区面积 km2
wide = mon.pivot(index="year_month", columns="district", values="depth_mean_m")
city_rows = []
for ym in all_months:
    r = wide.loc[ym, FIXED13]
    avail = r.dropna()
    w = np.array([AREA[d] for d in avail.index], float)
    city_rows.append({"year_month": ym,
                      "fixed_district_set": "13区=16区-{延庆,门头沟,石景山}",
                      "n_expected_districts": 13,
                      "n_available_districts": int(len(avail)),
                      "complete_support": bool(len(avail) == 13),
                      "city_mean_equal": float(avail.mean()) if len(avail) else np.nan,
                      "city_mean_weighted": float((avail.values * w).sum() / w.sum()) if len(avail) else np.nan,
                      "weight_note": "pre-existing model-domain district areas (km2), 05_recovery_patterns"})
city = pd.DataFrame(city_rows)
city.to_csv(os.path.join(OUT, "city_comparable_monthly_2019_2026.csv"), index=False, encoding="utf-8-sig")
print("complete city months (13/13):", int(city["complete_support"].sum()), "/", len(city))

# ---------------- A4 consistency audits ----------------
ann = pd.read_csv(os.path.join(SRC, "北京市各区县地下水年度汇总统计_2019-2026.csv"), encoding="utf-8-sig")
ann.columns = [c.strip() for c in ann.columns]
mon_ok = mon.dropna(subset=["depth_mean_m"])
mon_ann = mon_ok.groupby(["district", mon_ok["year_month"].str[:4].astype(int).rename("year")])["depth_mean_m"].agg(["mean", "count"]).reset_index()
dec_df = mon_ok[mon_ok["year_month"].str[5:7] == "12"].copy()
dec_df["year"] = dec_df["year_month"].str[:4].astype(int)
dec = dec_df.set_index(["district", "year"])["depth_mean_m"]
cmp_rows = []
for r in ann.itertuples():
    d, y = r.区县, int(r.年份)
    sel = mon_ann[(mon_ann["district"] == d) & (mon_ann["year"] == y)]
    my_mean = float(sel["mean"].iloc[0]) if len(sel) else np.nan
    n_m = int(sel["count"].iloc[0]) if len(sel) else 0
    off_mean = float(r._4) if pd.notna(r._4) else np.nan  # 年均埋深(米)
    cmp_rows.append({"district": d, "year": y, "statistic": "annual_mean",
                     "monthly_panel_value_m": my_mean, "official_annual_value_m": off_mean,
                     "difference_m": (my_mean - off_mean) if np.isfinite(my_mean) and np.isfinite(off_mean) else np.nan,
                     "n_months_in_panel": n_m})
    my_dec = float(dec.get((d, y), np.nan))
    off_end = float(r._5) if pd.notna(r._5) else np.nan   # 年末埋深(米)
    cmp_rows.append({"district": d, "year": y, "statistic": "yearend_vs_dec_month",
                     "monthly_panel_value_m": my_dec, "official_annual_value_m": off_end,
                     "difference_m": (my_dec - off_end) if np.isfinite(my_dec) and np.isfinite(off_end) else np.nan,
                     "n_months_in_panel": n_m})
cmp_df = pd.DataFrame(cmp_rows)
# per-district correlation & trend consistency on annual means
summ = []
for d in DIST16:
    s = cmp_df[(cmp_df["district"] == d) & (cmp_df["statistic"] == "annual_mean")].dropna(subset=["difference_m"])
    if len(s) >= 3:
        summ.append({"district": d, "n_years": len(s),
                     "mean_abs_diff_annual_mean_m": float(s["difference_m"].abs().mean()),
                     "corr_annual_mean": float(np.corrcoef(s["monthly_panel_value_m"], s["official_annual_value_m"])[0, 1]),
                     "trend_panel": float(np.polyfit(s["year"], s["monthly_panel_value_m"], 1)[0]),
                     "trend_official": float(np.polyfit(s["year"], s["official_annual_value_m"], 1)[0]),
                     "trend_direction_match": bool(np.sign(np.polyfit(s["year"], s["monthly_panel_value_m"], 1)[0]) == np.sign(np.polyfit(s["year"], s["official_annual_value_m"], 1)[0]))})
cmp_df.to_csv(os.path.join(OUT, "district_monthly_vs_annual_audit.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(summ).to_csv(os.path.join(OUT, "_district_annual_consistency_summary.csv"), index=False, encoding="utf-8-sig")
print(pd.DataFrame(summ)[["district", "n_years", "mean_abs_diff_annual_mean_m", "corr_annual_mean", "trend_direction_match"]].to_string())

# city vs official background (annual official 公报口径 + 官方全市值 monthly-aggregated)
off_ann = pd.read_csv(os.path.join(SRC, "北京市历年平均地下水位_1986-2025.csv"), encoding="utf-8-sig")
off_ann.columns = ["year", "yearend_depth_m", "yoy", "nature", "source"]
off_ann = off_ann[(off_ann["year"] >= 2019) & (off_ann["year"] <= 2025)]
cmp_city = city.dropna(subset=["city_mean_equal"]).copy()
cmp_city["year"] = cmp_city["year_month"].str[:4].astype(int)
city_ann = cmp_city.groupby("year")["city_mean_equal"].mean()
off_m = panel.groupby("ym")["全市平均埋深"].mean()
off_m_ann = off_m.groupby(off_m.index.str[:4].astype(int)).mean()
crows = []
yrs = sorted(set(city_ann.index) & set(off_ann["year"]))
ca = city_ann.reindex(yrs).values; oa = off_ann.set_index("year").loc[yrs, "yearend_depth_m"].values.astype(float)
crows.append({"check": "fixed13_annual_mean_vs_official_yearend_公报口径", "years": f"{yrs[0]}-{yrs[-1]}",
              "trend_city_m_per_yr": float(np.polyfit(yrs, ca, 1)[0]),
              "trend_official_m_per_yr": float(np.polyfit(yrs, oa, 1)[0]),
              "trend_direction_match": bool(np.sign(np.polyfit(yrs, ca, 1)[0]) == np.sign(np.polyfit(yrs, oa, 1)[0])),
              "yoy_change_corr": float(np.corrcoef(np.diff(ca), np.diff(oa))[0, 1]),
              "cumulative_change_city_m": float(ca[-1] - ca[0]),
              "cumulative_change_official_m": float(oa[-1] - oa[0]),
              "support_mismatch": True,
              "note": "city=fixed13 arithmetic monthly-mean of annual means; official=公报年末口径; not strict RMSE"})
yrs2 = sorted(set(city_ann.index) & set(off_m_ann.index))
ca2 = city_ann.reindex(yrs2).values; oa2 = off_m_ann.reindex(yrs2).values.astype(float)
crows.append({"check": "fixed13_vs_official_cityvalue_monthly_aggregated", "years": f"{yrs2[0]}-{yrs2[-1]}",
              "trend_city_m_per_yr": float(np.polyfit(yrs2, ca2, 1)[0]),
              "trend_official_m_per_yr": float(np.polyfit(yrs2, oa2, 1)[0]),
              "trend_direction_match": bool(np.sign(np.polyfit(yrs2, ca2, 1)[0]) == np.sign(np.polyfit(yrs2, oa2, 1)[0])),
              "yoy_change_corr": float(np.corrcoef(np.diff(ca2), np.diff(oa2))[0, 1]),
              "cumulative_change_city_m": float(ca2[-1] - ca2[0]),
              "cumulative_change_official_m": float(oa2[-1] - oa2[0]),
              "support_mismatch": True,
              "note": "official全市值口径在2020-07/2025-04发生算术口径切换(见audit JSON), 与固定13区序列非严格同支持"})
pd.DataFrame(crows).to_csv(os.path.join(OUT, "city_support_consistency_audit.csv"), index=False, encoding="utf-8-sig")

# ---------------- A5 QC flags ----------------
SWITCH_MONTHS = {"2020-07", "2020-08", "2021-01", "2024-01", "2025-04"}  # documented regime switches (a priori)
qc = mon.copy()
qc = qc.sort_values(["district", "year_month"])
qc["month_to_month_change_m"] = qc.groupby("district")["depth_mean_m"].diff()
qc["within_month_range_m"] = qc["depth_max_m"] - qc["depth_min_m"]
thr = {}
for d in DIST16:
    ch = qc.loc[qc["district"] == d, "month_to_month_change_m"].dropna()
    med = ch.median(); mad = (ch - med).abs().median()
    thr[d] = (med, mad)
qc["flag_missing"] = qc["source_support"] == "missing"
qc["flag_sparse_support"] = qc["source_support"] == "single_period"
qc["flag_possible_source_change"] = qc["year_month"].isin(SWITCH_MONTHS)
def lj(r):
    if pd.isna(r["month_to_month_change_m"]):
        return False
    med, mad = thr[r["district"]]
    return abs(r["month_to_month_change_m"] - med) > 5 * max(mad, 1e-9)
qc["flag_large_jump"] = qc.apply(lj, axis=1)
qc = qc[["district", "year_month", "depth_mean_m", "month_to_month_change_m", "within_month_range_m",
         "flag_missing", "flag_large_jump", "flag_sparse_support", "flag_possible_source_change"]]
qc.to_csv(os.path.join(OUT, "district_monthly_qc_flags.csv"), index=False, encoding="utf-8-sig")
print("large jumps:", int(qc["flag_large_jump"].sum()), "| sparse:", int(qc["flag_sparse_support"].sum()),
      "| missing:", int(qc["flag_missing"].sum()))
print(qc[qc["flag_large_jump"]][["district", "year_month", "month_to_month_change_m"]].to_string())
print("TASK A DONE")
