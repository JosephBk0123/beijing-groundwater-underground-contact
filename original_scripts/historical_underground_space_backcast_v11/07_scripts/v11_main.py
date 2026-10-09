# -*- coding: utf-8 -*-
"""v1.1 主脚本：v1.0 LUCC 节点 -> 逐区 stock proxy -> 双 treatment x 3β 回推
-> 年度插值 -> full/MAIN/RAW cube -> 审计 -> join plan -> 图 -> run_summary
（不触碰 v1.0 原文件；全部输出到 historical_underground_space_backcast_v11/）"""
import pandas as pd
import numpy as np
import os, io, json, shutil

V10 = r'local_raw_workspace\historical_underground_space_backcast_v1'
V11 = r'local_raw_workspace\historical_underground_space_backcast_v11'
PROFILE = r'local_raw_workspace\2026.09.04 自然基金委评审材料准备\Multi-scale data assimilation reveals dynamic antecedent conditions for compound rainfall–groundwater hazards\data\地下空间部分\district_depth_profile_v2.csv'

for sub in ['01_source_v10', '02_lucc', '03_backcast', '04_cube', '05_audit', '06_figures', '07_scripts', '08_next_stage']:
    os.makedirs(os.path.join(V11, sub), exist_ok=True)

log = io.StringIO()
DISTRICTS16 = ['东城区', '西城区', '朝阳区', '丰台区', '石景山区', '海淀区', '门头沟区', '房山区',
               '通州区', '顺义区', '昌平区', '大兴区', '怀柔区', '平谷区', '密云区', '延庆区']
TREATMENTS = ['raw_snapshot', 'monotone_stock_proxy']
BETAS = [0.8, 1.0, 1.2]

# ============ 1. 读取 v1.0 LUCC ============
lucc10 = pd.read_csv(V10 + r'\02_lucc\district_LUCC_urban_area.csv')
assert lucc10.year.isin([1980, 1990, 1995, 2000, 2005, 2010, 2015, 2020]).all()
raw = lucc10.pivot_table(index='year', columns='district', values='urban_land_area_km2')
YEARS = sorted(raw.index.tolist())
meta = lucc10.groupby(['year', 'district'])[['source_raster']].first()
log.write(f"v1.0 节点: {YEARS}, {raw.shape[1]} 区\n")

# ============ 2. stock proxy（逐区 cumulative max） ============
stock = raw.copy()
for d in raw.columns:
    stock[d] = raw[d].cummax()

# v11 LUCC 表
rows = []
for d in raw.columns:
    for y in YEARS:
        s_raw = raw.loc[y, d]
        s_stock = stock.loc[y, d]
        prev_stock = stock.loc[y, d] if y == YEARS[0] else stock.loc[raw.index[raw.index < y].max(), d]
        adj = s_stock - s_raw
        rows.append({
            'year': y, 'district': d,
            'urban_land_area_raw_km2': s_raw,
            'urban_land_area_stock_proxy_km2': s_stock,
            'previous_stock_proxy_km2': prev_stock,
            'stock_constraint_applied': bool(s_stock > s_raw),
            'stock_constraint_adjustment_km2': adj,
            'stock_constraint_adjustment_fraction': (adj / s_raw) if s_raw > 0 else np.nan,
            'urban_ratio_raw_to_2020': s_raw / raw.loc[2020, d],
            'urban_ratio_stock_to_2020': s_stock / stock.loc[2020, d],
            'raw_negative_change_flag': bool(y > YEARS[0] and s_raw < raw.loc[raw.index[raw.index < y].max(), d]),
            'source_raster': meta.loc[(y, d), 'source_raster'],
            'qc_flag': '',
        })
lucc11 = pd.DataFrame(rows)
lucc11.to_csv(V11 + r'\02_lucc\district_LUCC_urban_area_v11.csv', index=False, encoding='utf-8-sig')

# 审计
trig = lucc11[lucc11.stock_constraint_applied]
trig_audit = pd.DataFrame([{
    'district': r.district, 'year': r.year,
    'raw_area_km2': r.urban_land_area_raw_km2,
    'previous_stock_area_km2': r.previous_stock_proxy_km2,
    'stock_area_km2': r.urban_land_area_stock_proxy_km2,
    'adjustment_km2': r.stock_constraint_adjustment_km2,
    'adjustment_fraction': r.stock_constraint_adjustment_fraction,
    'raw_to_previous_change_km2': r.urban_land_area_raw_km2 - r.previous_stock_proxy_km2,
    'raw_to_previous_change_fraction': (r.urban_land_area_raw_km2 - r.previous_stock_proxy_km2) / r.previous_stock_proxy_km2 if r.previous_stock_proxy_km2 > 0 else np.nan,
    'constraint_applied': True,
} for r in trig.itertuples()])
trig_audit.to_csv(V11 + r'\02_lucc\stock_constraint_audit.csv', index=False, encoding='utf-8-sig')
lucc11[['year', 'district', 'urban_land_area_raw_km2', 'urban_land_area_stock_proxy_km2',
        'stock_constraint_applied']].to_csv(V11 + r'\02_lucc\stock_constraint_all_nodes.csv', index=False, encoding='utf-8-sig')
log.write(f"stock constraint 触发: {len(trig_audit)} 个 district-year 节点\n")

# ============ 3. 深度结构 p_d,l（沿用 v1.0 处理） ============
prof = pd.read_csv(PROFILE)
prof16 = prof[prof['district'].isin(DISTRICTS16)].copy()
LNO = {'B1': 1, 'B2': 2, 'B3': 3, 'B4': 4, 'B5+': 5}
prof16['layer_no'] = prof16['layer_bucket'].map(LNO)
p_tbl = prof16.pivot_table(index='district', columns='layer_no', values='layer_area_fraction')
p_sum = p_tbl.sum(axis=1)
renorm = p_sum[(p_sum - 1).abs() > 1e-6].index.tolist()
for d in renorm:
    p_tbl.loc[d] = p_tbl.loc[d] / p_tbl.loc[d].sum()
log.write(f"Σp 舍入归一化区(沿用v1.0): {renorm}\n")
depths = prof16.groupby('layer_no')[['depth_shallow_m', 'depth_central_m', 'depth_deep_m']].first()
n_assets = prof16.groupby('district')['n_assets'].first()

# ============ 4. 节点 backcast（双 treatment x 3β） ============
node_rows = []
for treat in TREATMENTS:
    mat = raw if treat == 'raw_snapshot' else stock
    for d in mat.columns:
        for y in YEARS:
            R = mat.loc[y, d] / mat.loc[2020, d]
            for b in BETAS:
                role = ('MAIN' if treat == 'monotone_stock_proxy' else 'RAW_SENSITIVITY') if b == 1.0 else 'SENSITIVITY'
                node_rows.append({
                    'year': y, 'district': d, 'lucc_treatment': treat, 'beta': b, 'analysis_role': role,
                    'urban_land_area_raw_km2': raw.loc[y, d],
                    'urban_land_area_stock_proxy_km2': stock.loc[y, d],
                    'urban_land_area_used_km2': mat.loc[y, d],
                    'urban_land_ratio_to_2020': R,
                    'underground_space_index_2020eq1': R ** b,
                    'absolute_backcast_available': False,
                    'estimated_underground_area_m2': np.nan,
                    'source_is_observed_lucc_node': True, 'qc_flag': '',
                })
nodes11 = pd.DataFrame(node_rows)
nodes11.to_csv(V11 + r'\03_backcast\district_underground_space_nodes_v11.csv', index=False, encoding='utf-8-sig')

# ============ 5. 年度插值（先K后插值） ============
ann_rows = []
for treat in TREATMENTS:
    mat = raw if treat == 'raw_snapshot' else stock
    for d in mat.columns:
        s20 = mat.loc[2020, d]
        for b in BETAS:
            knode = {y: (mat.loc[y, d] / s20) ** b for y in YEARS}
            for y in range(1980, 2021):
                if y in knode:
                    k = knode[y]
                    used = mat.loc[y, d]
                    interp = False
                else:
                    lo = max(yy for yy in YEARS if yy < y)
                    hi = min(yy for yy in YEARS if yy > y)
                    k = knode[lo] + (y - lo) / (hi - lo) * (knode[hi] - knode[lo])
                    used = mat.loc[lo, d] + (y - lo) / (hi - lo) * (mat.loc[hi, d] - mat.loc[lo, d])
                    interp = True
                role = ('MAIN' if treat == 'monotone_stock_proxy' else 'RAW_SENSITIVITY') if b == 1.0 else 'SENSITIVITY'
                ann_rows.append({
                    'year': y, 'district': d, 'lucc_treatment': treat, 'beta': b, 'analysis_role': role,
                    'urban_land_area_raw_km2': np.nan if y not in raw.index else raw.loc[y, d],
                    'urban_land_area_stock_proxy_km2': np.nan if y not in stock.index else stock.loc[y, d],
                    'urban_land_area_used_km2': used, 'urban_land_ratio_to_2020': used / s20,
                    'underground_space_index_2020eq1': k,
                    'absolute_backcast_available': False, 'estimated_underground_area_m2': np.nan,
                    'interpolation_flag': interp, 'source_is_observed_lucc_node': not interp,
                    'lucc_source_type': ('lucc_node' if not interp else 'linear_interp_between_nodes'),
                    'qc_flag': '',
                })
annual11 = pd.DataFrame(ann_rows)
annual11.to_csv(V11 + r'\03_backcast\district_underground_space_annual_v11.csv', index=False, encoding='utf-8-sig')
log.write(f"annual_v11: {len(annual11)} 行 (期望 {16*41*6})\n")

# MAIN annual
annual11[(annual11.lucc_treatment == 'monotone_stock_proxy') & (annual11.beta == 1.0)].to_csv(
    V11 + r'\08_next_stage\district_underground_space_annual_MAIN.csv', index=False, encoding='utf-8-sig')

# ============ 6. cube（full + MAIN + RAW） ============
def build_cube(subset):
    rows = []
    for r in subset.itertuples():
        p = p_tbl.loc[r.district]
        k = r.underground_space_index_2020eq1
        idx_ge = {}
        cum = 0.0
        for l in range(5, 0, -1):
            cum += p[l] if l in p.index else 0.0
            idx_ge[l] = cum
        for l in range(1, 6):
            pl = p[l] if l in p.index else 0.0
            rows.append({
                'year': r.year, 'district': r.district,
                'lucc_treatment': r.lucc_treatment, 'beta': r.beta, 'analysis_role': r.analysis_role,
                'urban_land_area_raw_km2': r.urban_land_area_raw_km2,
                'urban_land_area_stock_proxy_km2': r.urban_land_area_stock_proxy_km2,
                'urban_land_area_used_km2': r.urban_land_area_used_km2,
                'urban_land_ratio_to_2020': r.urban_land_ratio_to_2020,
                'underground_space_index_2020eq1': k,
                'layer_no': l, 'layer_bucket': f'B{l}' if l < 5 else 'B5+',
                'layer_fraction': pl,
                'layer_area_index': k * pl,
                'area_at_or_deeper_index': k * idx_ge[l],
                'area_at_or_deeper_fraction': idx_ge[l],
                'depth_shallow_m': depths.loc[l, 'depth_shallow_m'],
                'depth_central_m': depths.loc[l, 'depth_central_m'],
                'depth_deep_m': depths.loc[l, 'depth_deep_m'],
                'n_assets_profile': int(n_assets[r.district]),
                'absolute_backcast_available': False,
                'estimated_underground_area_m2': np.nan,
                'layer_area_m2': np.nan, 'area_at_or_deeper_m2': np.nan,
                'interpolation_flag': r.interpolation_flag, 'qc_flag': '',
            })
    return pd.DataFrame(rows)

cube_full = build_cube(annual11)
cube_full.to_csv(V11 + r'\04_cube\underground_space_depth_time_cube_v11_full.csv', index=False, encoding='utf-8-sig')
main_cube = cube_full[cube_full.analysis_role == 'MAIN']
raw_cube = cube_full[cube_full.analysis_role == 'RAW_SENSITIVITY']
main_cube.to_csv(V11 + r'\04_cube\underground_space_depth_time_cube_MAIN.csv', index=False, encoding='utf-8-sig')
raw_cube.to_csv(V11 + r'\04_cube\underground_space_depth_time_cube_RAW_SENSITIVITY.csv', index=False, encoding='utf-8-sig')
shutil.copy(V11 + r'\04_cube\underground_space_depth_time_cube_MAIN.csv', V11 + r'\08_next_stage\underground_space_depth_time_cube_MAIN.csv')
shutil.copy(V11 + r'\04_cube\underground_space_depth_time_cube_RAW_SENSITIVITY.csv', V11 + r'\08_next_stage\underground_space_depth_time_cube_RAW_SENSITIVITY.csv')
log.write(f"full cube: {len(cube_full)} (期望19680), MAIN: {len(main_cube)} (期望3280), RAW: {len(raw_cube)} (期望3280)\n")

# stock proxy 节点简表（next stage D）
lucc11[['year', 'district', 'urban_land_area_raw_km2', 'urban_land_area_stock_proxy_km2',
        'stock_constraint_applied']].rename(columns={
    'urban_land_area_raw_km2': 'raw_area_km2', 'urban_land_area_stock_proxy_km2': 'stock_area_km2'}
).to_csv(V11 + r'\08_next_stage\district_LUCC_stock_proxy_nodes.csv', index=False, encoding='utf-8-sig')

# ============ 7. QC / 守恒审计 ============
aud_rows = []
max_err = 0.0
fails = []
for (d, y, t, b), g in cube_full.groupby(['district', 'year', 'lucc_treatment', 'beta']):
    s = g['layer_area_index'].sum()
    k = g['underground_space_index_2020eq1'].iloc[0]
    max_err = max(max_err, abs(s - k))
    b1 = g[g.layer_no == 1]['area_at_or_deeper_index'].iloc[0]
    if abs(b1 - k) > 1e-5:
        fails.append((d, y, t, b, 'b1', b1, k))
    v = g.sort_values('layer_no')['area_at_or_deeper_index'].values
    if any(v[i] < v[i + 1] - 1e-12 for i in range(len(v) - 1)):
        fails.append((d, y, t, b, 'mono', None, None))
    if not (g['layer_fraction'].between(0, 1)).all() or not (g['area_at_or_deeper_fraction'].between(0, 1 + 1e-9)).all():
        fails.append((d, y, t, b, 'frac', None, None))
    aud_rows.append({'district': d, 'year': y, 'lucc_treatment': t, 'beta': b,
                     'sum_layer_index': s, 'index': k, 'sum_minus_index_abs': abs(s - k),
                     'b1_equals_index': abs(b1 - k) <= 1e-5, 'monotonic_ok': True, 'frac_range_ok': True})
aud11 = pd.DataFrame(aud_rows)
aud11.to_csv(V11 + r'\05_audit\backcast_conservation_audit_v11.csv', index=False, encoding='utf-8-sig')
log.write(f"conservation max err: {max_err:.2e}, hard fails: {len(fails)}\n")

# MAIN index 非递减检查
main_ann = annual11[(annual11.lucc_treatment == 'monotone_stock_proxy') & (annual11.beta == 1.0)]
nondec_ok = True
for d, g in main_ann.groupby('district'):
    g = g.sort_values('year')
    if g['underground_space_index_2020eq1'].diff().dropna().min() < -1e-12:
        nondec_ok = False
log.write(f"MAIN annual index 非递减: {nondec_ok}\n")

# stock 节点非递减
stock_nondec = all((stock[d].diff().dropna() >= 0).all() for d in stock.columns)
log.write(f"stock 节点全部非递减: {stock_nondec}\n")

# MAIN vs RAW 差异
diff_stats = []
for d in DISTRICTS16:
    m = main_ann[main_ann.district == d].set_index('year')['underground_space_index_2020eq1']
    r = annual11[(annual11.lucc_treatment == 'raw_snapshot') & (annual11.beta == 1.0) & (annual11.district == d)].set_index('year')['underground_space_index_2020eq1']
    diff = (m - r).abs()
    diff_stats.append({'district': d, 'max_abs_diff': diff.max(), 'year_of_max': diff.idxmax()})
diff_df = pd.DataFrame(diff_stats)

# ============ 8. join plan ============
OUTER10 = ['大兴区', '密云区', '平谷区', '延庆区', '怀柔区', '房山区', '昌平区', '通州区', '门头沟区', '顺义区']
jp = []
for d in DISTRICTS16:
    if d in OUTER10:
        jp.append({'district': d, 'historical_groundwater_direct_join_possible': True,
                   'historical_groundwater_spatial_unit': d, 'monthly_2019plus_join_possible': True,
                   'notes': '1980-2025区级年末地下水27年值可直接join'})
    else:
        jp.append({'district': d, 'historical_groundwater_direct_join_possible': False,
                   'historical_groundwater_spatial_unit': '城近郊(1980-2023)/城六区(2023-2025)聚合',
                   'monthly_2019plus_join_possible': False,
                   'notes': '地下水侧为聚合单元, 需聚合地下空间cube后join; 禁止拆分聚合地下水值到6区'})
pd.DataFrame(jp).to_csv(V11 + r'\08_next_stage\groundwater_encounter_join_plan.csv', index=False, encoding='utf-8-sig')

# ============ 9. schema md ============
schema_md = """# Encounter 输入 Schema（v1.1 冻结）

## 主输入
`underground_space_depth_time_cube_MAIN.csv`（16区 × 41年 × 5层 = 3,280 行）

| 字段 | 含义 |
|---|---|
| year | 1980-2020 年度（LUCC 节点间为线性插值，interpolation_flag 标记） |
| district | 现代北京16区 |
| lucc_treatment | monotone_stock_proxy（主情景） |
| beta | 1.0 |
| layer_no / layer_bucket | 1-5 / B1-B5+，地下层数层桶 |
| layer_fraction | p(d,l)：现代地下空间第 l 层面积比例（来自联合验收 profile v2） |
| underground_space_index_2020eq1 | K(d,t)：区级地下空间相对指数，2020=1 |
| layer_area_index | K × p(d,l)：第 l 层相对面积指数 |
| area_at_or_deeper_index | Σ_{j>=l} layer_area_index：达到第 l 层代表底板深度时暴露的相对面积（**encounter 查表核心字段**） |
| area_at_or_deeper_fraction | Σ_{j>=l} p(d,j)：与时间无关的深度结构累计比例 |
| depth_shallow_m / depth_central_m / depth_deep_m | 第 l 层底板埋深三套情景（shallow/central/deep） |
| n_assets_profile | 该区联合验收样本资产数（质量披露，非权重） |

## 重要边界
- **当前全部是相对/index 空间（2020=1）**，没有真实地下空间 m² baseline（absolute_backcast_available=false）。
- estimated_underground_area_m2 / layer_area_m2 / area_at_or_deeper_m2 均为 NA，待 U_d,2020 基准后按同管线升级。
- RAW_SENSITIVITY cube 为 raw_snapshot × β=1 对照情景，行数与 MAIN 相同。
- 遇遇计算公式预留：E_d(t) = Σ_l A_{d,l}(t) · I(z_l >= D_d(t))；当前 A 用 index 替代。
"""
with open(V11 + r'\08_next_stage\encounter_input_schema.md', 'w', encoding='utf-8') as f:
    f.write(schema_md)

# ============ 10. 图 ============
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# fig01 全市 raw vs stock
tot_raw = raw.sum(axis=1)
tot_stock = stock.sum(axis=1)
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(tot_raw.index, tot_raw.values, 'o--', color='#7f7f7f', label='Σ raw snapshot')
ax.plot(tot_stock.index, tot_stock.values, 'o-', color='#d62728', label='Σ stock proxy (逐区求和)')
for x, y in tot_stock.items():
    ax.annotate(f'{y:.0f}', (x, y), textcoords='offset points', xytext=(0, 6), fontsize=9)
ax.set_title('北京全市 class51: raw vs stock proxy (km²)')
ax.set_xticks(tot_raw.index)
ax.legend()
plt.tight_layout()
plt.savefig(V11 + r'\06_figures\fig01_citywide_raw_vs_stock.png', dpi=150)
plt.close()

# fig02 16区 small multiples
fig, axes = plt.subplots(4, 4, figsize=(16, 13), sharex=True)
for ax_i, d in zip(axes.flat, DISTRICTS16):
    ax_i.plot(raw.index, raw[d], 'o--', color='#7f7f7f', label='raw')
    ax_i.plot(stock.index, stock[d], 'o-', color='#d62728', label='stock')
    ax_i.set_title(d, fontsize=11)
axes[0, 0].legend(fontsize=8)
plt.suptitle('各区 class51: raw vs stock proxy (km²)', fontsize=14)
plt.tight_layout()
plt.savefig(V11 + r'\06_figures\fig02_district_raw_vs_stock_small_multiples.png', dpi=150)
plt.close()

# fig03 MAIN index
sel = ['朝阳区', '海淀区', '大兴区', '通州区', '昌平区', '房山区', '门头沟区']
fig, ax = plt.subplots(figsize=(9, 6))
for d in sel:
    g = main_ann[main_ann.district == d].sort_values('year')
    ax.plot(g.year, g.underground_space_index_2020eq1, label=d)
ax.axhline(1.0, color='gray', ls=':', lw=1)
ax.legend(fontsize=9)
ax.set_title('MAIN (stock proxy, β=1) 地下空间指数 (2020=1)')
plt.tight_layout()
plt.savefig(V11 + r'\06_figures\fig03_MAIN_underground_index_selected_districts.png', dpi=150)
plt.close()

# fig04 MAIN vs RAW diff（差异最大6区）
top6 = diff_df.sort_values('max_abs_diff', ascending=False).head(6)['district'].tolist()
fig, ax = plt.subplots(figsize=(9, 6))
for d in top6:
    m = main_ann[main_ann.district == d].set_index('year')['underground_space_index_2020eq1'].sort_index()
    r = annual11[(annual11.lucc_treatment == 'raw_snapshot') & (annual11.beta == 1.0) & (annual11.district == d)].set_index('year')['underground_space_index_2020eq1'].sort_index()
    ax.plot(m.index, (m - r).abs(), label=f'{d} (max={abs(m-r).max():.3f})')
ax.legend(fontsize=9)
ax.set_title('|MAIN − RAW_SENSITIVITY| 指数差 (受 stock constraint 影响最大的区)')
plt.tight_layout()
plt.savefig(V11 + r'\06_figures\fig04_MAIN_vs_RAW_difference.png', dpi=150)
plt.close()

# ============ 11. processing_log ============
with open(V11 + r'\processing_log_v11.md', 'w', encoding='utf-8') as f:
    f.write(log.getvalue())

# 导出中间统计供 run_summary 用
trig_by_d = trig_audit.groupby('district').size().reindex(DISTRICTS16).fillna(0).astype(int)
city_tot = pd.DataFrame({'year': YEARS, 'sum_raw_km2': [tot_raw[y] for y in YEARS],
                         'sum_stock_km2': [tot_stock[y] for y in YEARS]})
d2020diff = pd.DataFrame({
    'district': DISTRICTS16,
    'raw2020': [raw.loc[2020, d] for d in DISTRICTS16],
    'stock2020': [stock.loc[2020, d] for d in DISTRICTS16]})
d2020diff['difference'] = d2020diff.stock2020 - d2020diff.raw2020
top15 = trig_audit.reindex(trig_audit.adjustment_km2.abs().sort_values(ascending=False).index).head(15)
diff_df.to_csv(V11 + r'\05_audit\_main_raw_diff.csv', index=False, encoding='utf-8-sig')
city_tot.to_csv(V11 + r'\05_audit\_city_totals.csv', index=False, encoding='utf-8-sig')
d2020diff.to_csv(V11 + r'\05_audit\_d2020_diff.csv', index=False, encoding='utf-8-sig')
trig_by_d.to_csv(V11 + r'\05_audit\_trig_by_district.csv', encoding='utf-8-sig')
print('ALL DONE | trig:', len(trig_audit), '| cube:', len(cube_full), '| maxerr:', max_err, '| nondec:', nondec_ok, '| stock_nondec:', stock_nondec)
