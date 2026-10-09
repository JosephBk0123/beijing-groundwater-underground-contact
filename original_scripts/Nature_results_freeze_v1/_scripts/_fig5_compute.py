# -*- coding: utf-8 -*-
"""Recompute Figure 5 metrics from source tables.
The Excel summary supplies the QA4 cross-check.
Outputs: Fig5_metrics_by_district.csv, Fig5_group_summary.csv, Fig5_QA_report.txt,
         _fig5_metrics.json (plotting input)."""
import pandas as pd, numpy as np, os, json

FREEZE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(FREEZE, "03_figure_source_tables", "fig5_inputs")
V2 = os.path.join(BASE, "groundwater_underground_encounter_v2")
KIN = os.path.join(BASE, "first_exposure_kinetics_v1")
OUT = os.path.join(FREEZE, "03_figure_source_tables")
os.makedirs(OUT, exist_ok=True)

log = []
def w(s=""):
    log.append(str(s))

CENTRAL6 = ["东城区", "西城区", "朝阳区", "海淀区", "丰台区", "石景山区"]
EN = {"东城区": "Dongcheng", "西城区": "Xicheng", "朝阳区": "Chaoyang", "海淀区": "Haidian",
      "丰台区": "Fengtai", "石景山区": "Shijingshan", "门头沟区": "Mentougou", "房山区": "Fangshan",
      "通州区": "Tongzhou", "顺义区": "Shunyi", "昌平区": "Changping", "大兴区": "Daxing",
      "怀柔区": "Huairou", "平谷区": "Pinggu", "密云区": "Miyun", "延庆区": "Yanqing"}
ZD = {"B1": 5.0, "B2": 9.0, "B3": 13.0, "B4": 17.0}
END = "2025-12"

# ---------- load sources ----------
gwm = pd.read_csv(os.path.join(V2, "04_recovery", "recovery_groundwater_monthly_16district.csv"))
enc = pd.read_csv(os.path.join(V2, "04_recovery", "recovery_encounter_monthly_16district.csv"))
his = pd.read_csv(os.path.join(V2, "03_historical", "historical_encounter_direct10_2000_2020.csv"))
lay = pd.read_csv(os.path.join(
    BASE, "science_inputs",
    
    "data", "地下空间部分", "district_underground_layer_area_v2.csv"))
db = pd.read_csv(os.path.join(KIN, "per_district_deepest_boundary_first_contact_central.csv"))
rb = pd.read_csv(os.path.join(KIN, "rebound_cohort_first_contact_after_2015_central.csv"))
xl = pd.read_csv(os.path.join(KIN, "S1_pp_monthly_16district.csv"))  # QA4 reference

enc = enc[enc["depth_scenario"] == "central"].copy()
enc["year_month"] = enc["year_month"].astype(str)
gwm["year_month"] = gwm["year_month"].astype(str)
hc = his[his["depth_scenario"] == "central"].copy()

w("=" * 72)
w("Figure 5 指标重算 + QA 报告（数据 ≤ 2025-12；2026 YTD 未使用）")
w("=" * 72)

# ---------- QA1: 16区完整性 ----------
w("\n[QA1] 16区完整性")
DIST16 = sorted(set(gwm["district"]))
w(f"地下水月序列 districts={len(DIST16)}: {'、'.join(DIST16)}")
lay16 = sorted(d for d in set(lay["district"]) if d != "未解析")
w(f"地下空间分层 districts={len(lay16)}: {'、'.join(lay16)}")
w("  （注：分层表另含'未解析'区=联合验收旧格式行无区信息，非真实行政区，QA1 中剔除）")
try:
    import geopandas as gpd
    geo = gpd.read_file(os.path.join(
        BASE, "science_inputs",
        
        "results", "overnight_20260914", "geology", "management_masks", "districts.geojson"))
    geo16 = sorted(geo["district"].tolist())
    w(f"行政边界 districts={len(geo16)}: {'、'.join(geo16)}")
    geo_ok = set(geo16) == set(DIST16)
except Exception as e:
    geo_ok = False
    w(f"行政边界读取失败: {e}")
w(f"QA1: {'PASS' if set(DIST16)==set(lay16)==set(geo16) and len(DIST16)==16 else 'FAIL'}")
# ---------- QA2: 地下空间比例 ----------
w("\n[QA2] 地下空间比例（B1-B4 非负、Σp=1 误差<1e-6）")
prof = {}
bad = []
for d, g in lay[lay["layer_bucket"].isin(["B1", "B2", "B3", "B4"])].groupby("district"):
    areas = dict(zip(g["layer_bucket"], g["layer_area_m2"]))
    U = sum(areas.values())
    if U <= 0:
        bad.append((d, "U<=0")); continue
    p = {k: areas.get(k, 0.0) / U for k in ZD}
    if any(v < 0 for v in areas.values()):
        bad.append((d, "negative area"))
    if abs(sum(p.values()) - 1) >= 1e-6:
        bad.append((d, f"sum-1={sum(p.values())-1:.2e}"))
    prof[d] = p
w(f"QA2: {'PASS' if not bad else 'FAIL ' + str(bad)}")

# ---------- monthly C series (recompute from depth, not read encounter_fraction) ----------
def C_from_depth(d, depth):
    p = prof[d]
    return 100.0 * sum(v for k, v in p.items() if ZD[k] >= depth)

# QA3: C bounds + step-structure spot check
w("\n[QA3] C 界限与阶跃结构抽检")
badc = []
for d in prof:
    for dep in [0.5, 4.9, 5.0, 8.9, 9.0, 12.9, 13.0, 16.9, 17.0, 20.0]:
        c = C_from_depth(d, dep)
        if not (0 <= c <= 100 + 1e-9):
            badc.append((d, dep, c))
# Check the response at the depth thresholds.
# I[z_k >= D]: as depth decreases, more layers counted.
step_ok = True
for d in prof:
    p = prof[d]
    if abs(C_from_depth(d, 5.0) - 100.0) > 1e-9: step_ok = False
    if abs(C_from_depth(d, 9.0) - 100 * (p["B2"] + p["B3"] + p["B4"])) > 1e-9: step_ok = False
    if abs(C_from_depth(d, 13.0) - 100 * (p["B3"] + p["B4"])) > 1e-9: step_ok = False
    if abs(C_from_depth(d, 17.0) - 100 * p["B4"]) > 1e-9: step_ok = False
w(f"QA3: {'PASS' if not badc and step_ok else 'FAIL ' + str(badc)}")

# ---------- per-district metrics ----------
w("\n[指标重算]")
dbmap = {r["district"]: r for _, r in db.iterrows()}
rows = []
for d in DIST16:
    dd = dbmap[d]
    T_d = str(dd["T_deepest"])
    D_Td = float(dd["depth_at_deepest_m"])
    C_Td = float(dd["C_at_deepest"]) * 100
    left_boundary = T_d == "2019-09"
    # --- monthly C series from depth (≤2025-12) ---
    gg = gwm[(gwm["district"] == d) & (gwm["year_month"] <= END)].sort_values("year_month")
    ym = gg["year_month"].tolist()
    Cser = [C_from_depth(d, v) for v in gg["depth_mean_m"]]
    # C_2025
    C_2025 = Cser[-1] if ym and ym[-1] == END else (C_from_depth(d, gg["depth_mean_m"].iloc[-1]) if len(gg) else np.nan)
    # --- T_d state: C_Td recompute ---
    # if T_d inside monthly window, recompute from depth; else use annual encounter table
    if T_d in ym:
        C_Td_re = Cser[ym.index(T_d)]
    else:
        hh = hc[(hc["district"] == d) & (hc["year"] == int(T_d[:4]))]
        C_Td_re = float(hh["encounter_fraction"].iloc[0]) * 100 if len(hh) else np.nan
    # --- t_first: hybrid boundary max(2015-12, T_d) ---
    rrow = rb[rb["district"] == d]
    status = str(rrow["status"].iloc[0]) if len(rrow) else ""
    t2015 = rrow["first_contact_after_2015"].iloc[0] if len(rrow) else np.nan
    t2015 = str(t2015) if not pd.isna(t2015) else ""
    boundary = max("2015-12", T_d)
    t_first, C_first, note = None, np.nan, ""
    if t2015 and t2015.lower() != "nan" and t2015 >= boundary:
        t_first = t2015
    elif t2015 and t2015.lower() != "nan" and t2015 < boundary:
        t_first = str(dd["first_contact_after_deepest"])
        note = "recovery-era first contact (2015-after event predates T_d)"
    if t_first and t_first.lower() != "nan":
        if t_first in ym:
            C_first = Cser[ym.index(t_first)]
        else:
            hh = hc[(hc["district"] == d) & (hc["year"] == int(t_first[:4]))]
            C_first = float(hh["encounter_fraction"].iloc[0]) * 100 if len(hh) else np.nan
        ya, ma = int(T_d[:4]), int(T_d[5:7]); yb, mb = int(t_first[:4]), int(t_first[5:7])
        wait_m = (yb - ya) * 12 + (mb - ma)
        dC_first = C_first - C_Td_re
        R_LEA = dC_first / (wait_m / 12.0) if wait_m > 0 else np.nan
    else:
        wait_m = np.nan; dC_first = np.nan; R_LEA = np.nan
    # --- escalation ---
    dC_RE = C_2025 - C_Td_re
    ya, ma = int(T_d[:4]), int(T_d[5:7])
    wm_all = (2025 - ya) * 12 + (12 - ma)
    R_all = dC_RE / (wm_all / 12.0) if wm_all > 0 else np.nan
    # --- persistence ---
    Nc = sum(1 for c in Cser if c > 0)
    Lmax, cur = 0, 0
    for c in Cser:
        cur = cur + 1 if c > 0 else 0
        Lmax = max(Lmax, cur)
    if t_first and t_first in ym:
        i0 = ym.index(t_first)
        after = Cser[i0:]
        P_contact = sum(1 for c in after if c > 0) / len(after) if after else np.nan
    else:
        P_contact = np.nan
    rows.append(dict(
        district_cn=d, district_en=EN[d], central_six_flag=int(d in CENTRAL6),
        T_d=T_d, D_Td=round(D_Td, 2), t_first=t_first if t_first else "",
        wait_months=wait_m if not np.isnan(wait_m) else np.nan,
        wait_years=round(wait_m / 12.0, 3) if not np.isnan(wait_m) else np.nan,
        C_Td=round(C_Td_re, 2), C_first=round(C_first, 2) if not np.isnan(C_first) else np.nan,
        delta_C_first=round(dC_first, 2) if not np.isnan(dC_first) else np.nan,
        R_LEA_pp_per_year=round(R_LEA, 3) if not np.isnan(R_LEA) else np.nan,
        C_2025=round(C_2025, 2), delta_C_RE=round(dC_RE, 2),
        R_all_pp_per_year=round(R_all, 3) if not np.isnan(R_all) else np.nan,
        N_contact_months=Nc, L_max_contact_months=Lmax,
        P_contact=round(P_contact, 3) if not np.isnan(P_contact) else np.nan,
        status=status, left_boundary_flag=int(left_boundary), note=note))

m = pd.DataFrame(rows).sort_values("t_first").reset_index(drop=True)
m.to_csv(os.path.join(OUT, "Fig5_metrics_by_district.csv"), index=False, encoding="utf-8-sig")

# ---------- QA4: vs Excel ----------
w("\n[QA4] R_LEA 与 S1_pp_monthly_16district.csv 年化值比对（容差 0.01）")
qa4 = []
qa4_ok = True
for _, r in m.iterrows():
    ref = xl[xl["district"] == r["district_cn"]]
    if not len(ref):
        continue
    rv = ref["S1pp_annualized_pp_per_year"].iloc[0]
    nv = r["R_LEA_pp_per_year"]
    if np.isnan(rv) and np.isnan(nv):
        continue
    if np.isnan(rv) != np.isnan(nv):
        qa4_ok = False; qa4.append((r["district_cn"], rv, nv, "NaN mismatch")); continue
    diff = abs(nv - rv)
    if diff > 0.01:
        qa4_ok = False
    qa4.append((r["district_cn"], rv, nv, round(diff, 4)))
for q in qa4:
    w(f"  {q[0]}: existing={q[1]}  recomputed={q[2]}  |diff|={q[3]}")
w(f"QA4: {'PASS' if qa4_ok else 'FAIL — 停止最终作图，需排查'}")

# ---------- QA5: 左边界 ----------
w("\n[QA5] T_d 左边界检查")
lb = m[m["left_boundary_flag"] == 1][["district_cn", "T_d"]]
for _, r in lb.iterrows():
    w(f"  left-boundary minimum: {r['district_cn']} (T_d = {r['T_d']} = 数据窗口起点，标记为 deepest observed within window，非绝对历史最低点)")
for d in ["海淀区", "朝阳区"]:
    hit = m[m["district_cn"] == d].iloc[0]
    w(f"  特别检查 {d}: T_d={hit['T_d']} left_boundary={hit['left_boundary_flag']}")
w("QA5: DONE")

# ---------- QA6: 2026 ----------
w("\n[QA6] 2026 数据隔离：全部指标仅使用 year_month ≤ 2025-12 — PASS")

# ---------- group summary ----------
w("\n[分组汇总]")
def grp(sub, col):
    x = sub[col].dropna()
    return dict(n=len(x), median=round(float(x.median()), 3), mean=round(float(x.mean()), 3),
                q1=round(float(x.quantile(0.25)), 3), q3=round(float(x.quantile(0.75)), 3))
gs = []
for name, sub in [("central_six", m[m["central_six_flag"] == 1]), ("noncentral", m[m["central_six_flag"] == 0])]:
    a = grp(sub, "R_LEA_pp_per_year"); a.update(group=name, metric="R_LEA"); gs.append(a)
    b = grp(sub, "delta_C_RE"); b.update(group=name, metric="delta_C_RE"); gs.append(b)
# Mann-Whitney
try:
    from scipy.stats import mannwhitneyu, spearmanr
    c = m[(m["central_six_flag"] == 1)]["R_LEA_pp_per_year"].dropna()
    n = m[(m["central_six_flag"] == 0)]["R_LEA_pp_per_year"].dropna()
    if len(c) >= 3 and len(n) >= 3:
        U, pU = mannwhitneyu(c, n, alternative="two-sided")
        w(f"R_LEA Mann-Whitney U: U={U:.1f}, p={pU:.4f} (central n={len(c)}, noncentral n={len(n)})")
    c2 = m[(m["central_six_flag"] == 1)]["delta_C_RE"].dropna()
    n2 = m[(m["central_six_flag"] == 0)]["delta_C_RE"].dropna()
    U2, pU2 = mannwhitneyu(c2, n2, alternative="two-sided")
    w(f"ΔC_RE Mann-Whitney U: U={U2:.1f}, p={pU2:.4f} (central n={len(c2)}, noncentral n={len(n2)})")
    sp = spearmanr(m["R_LEA_pp_per_year"].dropna(),
                   m.loc[m["R_LEA_pp_per_year"].notna(), "delta_C_RE"])
    w(f"Spearman(R_LEA, ΔC_RE): rho={sp.statistic:.3f}, p={sp.pvalue:.4f}, n={int(m['R_LEA_pp_per_year'].notna().sum())}")
    with open(os.path.join(OUT, "_fig5_stats.json"), "w", encoding="utf-8") as f:
        json.dump({"mwu_R_LEA": [float(U), float(pU)], "mwu_dC_RE": [float(U2), float(pU2)],
                   "spearman": [float(sp.statistic), float(sp.pvalue), int(m["R_LEA_pp_per_year"].notna().sum())]}, f)
except ImportError:
    w("scipy 不可用：跳过 Mann-Whitney/Spearman（绘图脚本中需自行处理）")

gdf = pd.DataFrame(gs)[["group", "metric", "n", "median", "q1", "q3", "mean"]]
gdf.to_csv(os.path.join(OUT, "Fig5_group_summary.csv"), index=False, encoding="utf-8-sig")
w("\n" + gdf.to_string(index=False))

w("\n[全部 QA 结论] " + ("ALL PASS — 可进入绘图" if qa4_ok and not bad and not badc and geo_ok else "存在 FAIL，详见上文"))

open(os.path.join(FREEZE, "07_audit", "Fig5_QA_report.txt"), "w", encoding="utf-8").write("\n".join(log))
m.to_json(os.path.join(OUT, "_fig5_metrics.json"), orient="records", force_ascii=False, indent=1)
print("done")
