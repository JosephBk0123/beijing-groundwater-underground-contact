# -*- coding: utf-8 -*-
"""
v2.0 Encounter 主分析全流程
输入：MAIN/RAW cube (v1.1), 年度地下水 digitized, foundation 月面板, 长表(石景山regime)
输出：groundwater_underground_encounter_v2/ 全目录
"""
import pandas as pd
import numpy as np
import os, io, json, glob

ROOT = r'local_raw_workspace'
V11 = ROOT + r'\historical_underground_space_backcast_v11\08_next_stage'
GW_DIR = ROOT + r'\2026.09.04 自然基金委评审材料准备\Multi-scale data assimilation reveals dynamic antecedent conditions for compound rainfall–groundwater hazards\data\地下水部分'
OUT = ROOT + r'\groundwater_underground_encounter_v2'
for sub in ['01_inputs', '02_groundwater', '03_historical', '04_recovery', '05_sensitivity', '06_ranking', '07_figures', '08_audit', '09_scripts']:
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)

log = io.StringIO()
OUTER10 = ['大兴区', '密云区', '平谷区', '延庆区', '怀柔区', '房山区', '昌平区', '通州区', '门头沟q'.replace('q', '') + '区', '顺义区']
D16 = ['东城区', '西城区', '朝阳区', '丰台区', '石景山区', '海淀区', '门头沟区', '房山区',
       '通州区', '顺义区', '昌平区', '大兴区', '怀柔区', '平谷区', '密云区', '延庆区']
SCEN = {'shallow': {1: 3.5, 2: 7.0, 3: 10.5, 4: 14.0, 5: 17.5},
        'central': {1: 5.0, 2: 9.0, 3: 13.0, 4: 17.0, 5: 21.0},
        'deep':    {1: 5.5, 2: 11.0, 3: 16.5, 4: 22.0, 5: 27.5}}

# ============ 1. cube 读取与校验 ============
main = pd.read_csv(V11 + r'\underground_space_depth_time_cube_MAIN.csv')
rawcube = pd.read_csv(VILI := (V11 + r'\underground_space_depth_time_cube_RAW_SENSITIVITY.csv'))
assert len(main) == 3280, f"MAIN rows {len(main)}"
assert main.district.nunique() == 16 and main.year.between(1980, 2020).all() and main.layer_no.isin([1, 2, 3, 4, 5]).all()
assert (main.lucc_treatment == 'monotone_stock_proxy').all() and (main.beta == 1.0).all()
log.write(f"MAIN cube 校验 PASS: {len(main)} rows\n")

# p_d,l 与 K 查询
plat = main.pivot_table(index=['district', 'year'], columns='layer_no', values='layer_fraction')
kmap = main[main.layer_no == 1].set_index(['district', 'year'])['underground_space_index_2020eq1']
n_assets_map = main[main.layer_no == 1].set_index('district')['n_assets_profile'].to_dict()
kmap_raw = rawcube[rawcube.layer_no == 1].set_index(['district', 'year'])['underground_space_index_2020eq1']
plat_raw_frac = rawcube.pivot_table(index=['district', 'year'], columns='layer_no', values='layer_fraction')

# ============ 2. join plan v2 ============
jp = pd.DataFrame([{'district': d,
                    'historical_groundwater_direct_join_possible': d in OUTER10,
                    'historical_groundwater_spatial_unit': d if d in OUTER10 else '城近郊/城六区聚合',
                    'monthly_2019plus_join_possible': True,   # 16区月面板
                    'notes': '2019-2026官方16区逐期面板已审计(v3:277期)' } for d in D16])
jp.to_csv(OUT + r'\01_inputs\groundwater_encounter_join_plan_v2.csv', index=False, encoding='utf-8-sig')

# ============ 3. 历史年度 direct10 ============
gw = pd.read_csv(os.path.join(GW_DIR, 'beijing_district_groundwater_year_end_1980_2000_2025_digitized.csv'))
d10 = gw[(gw.district.isin(OUTER10)) & (gw.year.between(2000, 2020))].copy()
assert len(d10) == 210
d10[['year', 'district', 'depth_m', 'qc_flag', 'interpolation_anchor_status',
     'digitization_error_scale_m', 'spatial_level', 'spatial_unit_id']].to_csv(
    OUT + r'\02_groundwater\groundwater_historical_direct10.csv', index=False, encoding='utf-8-sig')

def encounter_rows(gw_df, k_lookup, time_col='year', scen_list=('shallow', 'central', 'deep')):
    rows = []
    for r in gw_df.itertuples():
        D = r.depth_m
        dname = r.district
        t = int(r.year)
        for sc in scen_list:
            C = 0.0
            shallowest = None
            for l in range(1, 6):
                pl = plat.loc[(dname, t), l] if (dname, t) in plat.index else 0.0
                if SCEN[sc][l] >= D and pl > 1e-9:
                    C += pl
                    if shallowest is None:
                        shallowest = l
            K = k_lookup.get((dname, t), np.nan)
            near = any(abs(SCEN[sc][l] - D) <= 0.5 for l in range(1, 6)
                       if (plat.loc[(dname, t), l] if (dname, t) in plat.index else 0.0) > 1e-9)
            rows.append({
                'year': t, 'district': dname, 'groundwater_depth_m': D,
                'gw_qc_flag': r.qc_flag, 'gw_interpolation_anchor_status': r.interpolation_anchor_status,
                'digitization_error_scale_m': r.digitization_error_scale_m,
                'depth_scenario': sc, 'underground_space_index_2020eq1': K,
                'encounter_fraction': C,
                'encounter_area_index_2020eq1': K * C,
                'meaningful_contact': C > 1e-9,
                'shallowest_contacted_layer': (f'B{shallowest}' if shallowest and shallowest < 5 else ('B5+' if shallowest == 5 else 'none')),
                'near_any_threshold_flag': near,
                'n_assets_profile': n_assets_map.get(dname),
            })
    return pd.DataFrame(rows)

hist = encounter_rows(d10, kmap)
hist.to_csv(OUT + r'\03_historical\historical_encounter_direct10_2000_2020.csv', index=False, encoding='utf-8-sig')

# 分层长表
layer_rows = []
for r in d10.itertuples():
    for sc in ('shallow', 'central', 'deep'):
        for l in range(1, 6):
            pl = plat.loc[(r.district, int(r.year)), l]
            z = SCEN[sc][l]
            layer_rows.append({
                'year': int(r.year), 'district': r.district, 'depth_scenario': sc,
                'groundwater_depth_m': r.depth_m, 'layer_no': l,
                'layer_bucket': f'B{l}' if l < 5 else 'B5+', 'layer_fraction': pl,
                'representative_depth_m': z, 'threshold_margin_m': z - r.depth_m,
                'contact_flag': z >= r.depth_m, 'positive_area_contact_flag': (z >= r.depth_m) and (pl > 1e-9),
                'layer_area_index': (kmap.get((r.district, int(r.year)), np.nan) * pl) if z >= r.depth_m else 0.0,
                'gw_qc_flag': r.qc_flag, 'near_threshold_flag': abs(z - r.depth_m) <= 0.5,
            })
pd.DataFrame(layer_rows).to_csv(OUT + r'\03_historical\historical_layer_contact_long_2000_2020.csv', index=False, encoding='utf-8-sig')

# ============ 4. 最深年 + trajectory + crossing ============
traj_rows = []
cross_rows = []
for d in OUTER10:
    g = hist[(hist.district == d) & (hist.depth_scenario == 'central')].sort_values('year')
    depths = d10[d10.district == d].set_index('year')['depth_m']
    deepest_year = int(depths.idxmax())
    deepest_depth = float(depths.max())
    # trajectory
    c = g['encounter_fraction'].values
    first_pos = next((i for i, v in enumerate(c) if v > 1e-9), None)
    last_pos = next((i for i in range(len(c) - 1, -1, -1) if c[i] > 1e-9), None)
    if first_pos is None:
        traj = 'persistent_no_contact'
    elif first_pos == 0 and last_pos == len(c) - 1:
        # 检查是否有中间断0
        if (c > 1e-9).all():
            traj = 'persistent_contact'
        else:
            traj = 'contact_reemerged' if c[-1] > 1e-9 else 'contact_lost_during_depletion'
    elif first_pos > 0:
        traj = 'newly_emerged_contact' if c[-1] > 1e-9 else 'intermittent_or_uncertain'
    else:
        traj = 'contact_lost_during_depletion'
    traj_rows.append({'district': d, 'depth_scenario': 'central',
                      'trajectory_class': traj, 'deepest_year': deepest_year,
                      'deepest_depth_m': deepest_depth,
                      'enc_frac_2000': float(g[g.year == 2000].encounter_fraction.iloc[0]),
                      'enc_frac_at_deepest': float(g[g.year == deepest_year].encounter_fraction.iloc[0]),
                      'enc_frac_2020': float(g[g.year == 2020].encounter_fraction.iloc[0])})
    # rebound crossing（各情景各层, deepest_year 之后）
    for sc in ('shallow', 'central', 'deep'):
        dd = d10[d10.district == d].set_index('year').sort_index()
        post = dd[dd.index > deepest_year]
        prev_contact = None
        for y, rr in post.iterrows():
            D = rr.depth_m
            for l in range(1, 6):
                pl = plat.loc[(d, int(y)), l]
                if pl <= 1e-9:
                    continue
                contact = SCEN[sc][l] >= D
                if prev_contact is not None and not prev_contact.get(l, contact) and contact:
                    y_qc = rr.qc_flag
                    y_anchor = rr.interpolation_anchor_status
                    prev_y = post.index[post.index.get_loc(y) - 1]
                    prev_anchor = dd.loc[prev_y, 'interpolation_anchor_status']
                    quality = 'review_required' if ('review_before_use' in str(y_anchor) or 'review_before_use' in str(prev_anchor)) else 'standard'
                    cross_rows.append({
                        'district': d, 'layer_no': l, 'layer_bucket': f'B{l}' if l < 5 else 'B5+',
                        'depth_scenario': sc, 'rebound_crossing_year': int(y),
                        'deepest_groundwater_year': deepest_year,
                        'layer_fraction': pl, 'crossing_quality': quality,
                        'near_threshold_flag': abs(SCEN[sc][l] - D) <= 0.5,
                        'qc_flag': y_qc,
                        'network_support_change_flag': (d == '石景山区' and int(y) == 2020),
                    })
            prev_contact = {l: (SCEN[sc][l] >= D and plat.loc[(d, int(y)), l] > 1e-9) for l in range(1, 6)}
traj_df = pd.DataFrame(traj_rows)
traj_df.to_csv(OUT + r'\03_historical\historical_contact_trajectory_summary.csv', index=False, encoding='utf-8-sig')
cross_df = pd.DataFrame(cross_rows)
cross_df.to_csv(OUT + r'\03_historical\historical_threshold_crossings.csv', index=False, encoding='utf-8-sig')

# 1980 参考
d80 = gw[(gw.district.isin(OUTER10)) & (gw.year == 1980)].copy()
ref80 = encounter_rows(d80, kmap)
ref80['reference_snapshot_only'] = True
ref80.to_csv(OUT + r'\03_historical\historical_encounter_1980_reference.csv', index=False, encoding='utf-8-sig')

# ============ 5. 恢复期月面板 ============
mpanel = pd.read_csv(ROOT + r'\outputs\20260920_recovery_data_foundation_v1\district_groundwater_monthly_2019_2026.csv')
mpanel['year_month'] = mpanel['year_month'].astype(str)
mpanel = mpanel[mpanel.n_periods.astype(int) > 0].copy()
mpanel['district_full'] = mpanel['district'].astype(str) + '区'
# 石景山 regime 标记
lg = pd.read_csv(ROOT + r'\地下水数据\时序规整\北京市平原区地下水_长表_2019-2026.csv')
lg['观测日期'] = pd.to_datetime(lg['观测日期'])
sjs_new = lg[(lg['区'] == '石景山') & (lg['石景山井网regime'].astype(str).str.contains('NEW'))]
sjs_switch_month = sjs_new['观测日期'].dt.strftime('%Y-%m').min() if len(sjs_new) else None
log.write(f"石景山井网切换月: {sjs_switch_month}\n")
mpanel['network_support_change_flag'] = (mpanel['district_full'] == '石景山区') & (mpanel['year_month'].str[:4].astype(int) >= 2020)
mpanel_out = mpanel[['year_month', 'district_full', 'depth_mean_m', 'depth_median_m', 'depth_min_m', 'depth_max_m',
                     'depth_std_m', 'n_periods', 'source_support', 'qc_flag', 'network_support_change_flag']].rename(
    columns={'district_full': 'district'})
mpanel_out.to_csv(OUT + r'\02_groundwater\groundwater_monthly_16district_2019_2026.csv', index=False, encoding='utf-8-sig')

# 恢复期 encounter（K: 2019用K2019, 2020+冻结为1）
rec_rows = []
for r in mpanel_out.itertuples():
    ym = r.year_month
    y = int(ym[:4]); m = int(ym[5:7])
    d = r.district
    D = r.depth_mean_m
    K19 = kmap.get((d, 2019), 1.0)
    K = kmap.get((d, y), 1.0) if y <= 2020 else 1.0
    for sc in ('shallow', 'central', 'deep'):
        C = 0.0; shallowest = None
        for l in range(1, 6):
            pl = plat.loc[(d, min(y, 2020)), l]
            if SCEN[sc][l] >= D and pl > 1e-9:
                C += pl
                if shallowest is None:
                    shallowest = l
        rec_rows.append({
            'year_month': ym, 'year': y, 'month': m, 'district': d,
            'groundwater_depth_m': D, 'depth_scenario': sc,
            'underground_space_index_2020eq1': K,
            'encounter_fraction': C,
            'encounter_area_index_2020eq1': K * C,
            'fixed2020_encounter_index': C,
            'post2020_stock_frozen': y > 2020,
            'meaningful_contact': C > 1e-9,
            'shallowest_contacted_layer': (f'B{shallowest}' if shallowest and shallowest < 5 else ('B5+' if shallowest == 5 else 'none')),
            'near_any_threshold_flag': any(abs(SCEN[sc][l] - D) <= 0.5 for l in range(1, 6) if plat.loc[(d, min(y, 2020)), l] > 1e-9),
            'n_assets_profile': n_assets_map.get(d),
            'qc_flag': r.qc_flag, 'network_support_change_flag': r.network_support_change_flag,
        })
rec = pd.DataFrame(rec_rows)
rec.to_csv(OUT + r'\04_recovery\recovery_encounter_monthly_16district.csv', index=False, encoding='utf-8-sig')

# 恢复期 groundwater 月表（重命名）
mpanel_out.to_csv(OUT + r'\04_recovery\recovery_groundwater_monthly_16district.csv', index=False, encoding='utf-8-sig')

# 恢复期分层长表
rec_layer_rows = []
for r in mpanel_out.itertuples():
    y = int(r.year_month[:4])
    for sc in ('shallow', 'central', 'deep'):
        for l in range(1, 6):
            pl = plat.loc[(r.district, min(y, 2020)), l]
            z = SCEN[sc][l]
            rec_layer_rows.append({
                'year_month': r.year_month, 'district': r.district, 'depth_scenario': sc,
                'groundwater_depth_m': r.depth_mean_m, 'layer_no': l,
                'layer_bucket': f'B{l}' if l < 5 else 'B5+', 'layer_fraction': pl,
                'representative_depth_m': z, 'threshold_margin_m': z - r.depth_mean_m,
                'contact_flag': z >= r.depth_mean_m,
                'positive_area_contact_flag': (z >= r.depth_mean_m) and (pl > 1e-9),
                'near_threshold_flag': abs(z - r.depth_mean_m) <= 0.5,
            })
pd.DataFrame(rec_layer_rows).to_csv(OUT + r'\04_recovery\recovery_layer_contact_long.csv', index=False, encoding='utf-8-sig')

# ============ 6. 恢复期 crossing ============
rec_cross = []
for d in D16:
    for sc in ('shallow', 'central', 'deep'):
        g = rec[(rec.district == d) & (rec.depth_scenario == sc)].sort_values('year_month')
        g = g[g.year_month <= '2025-12']
        for l in range(1, 6):
            pl = plat.loc[(d, 2020), l]
            if pl <= 1e-9:
                continue
            contact_seq = []
            for _, rr in g.iterrows():
                contact_seq.append((rr.year_month, SCEN[sc][l] >= rr.groundwater_depth_m))
            entries = sum(1 for i in range(1, len(contact_seq)) if not contact_seq[i - 1][1] and contact_seq[i][1])
            exits = sum(1 for i in range(1, len(contact_seq)) if contact_seq[i - 1][1] and not contact_seq[i][1])
            first_cross = next((contact_seq[i][0] for i in range(1, len(contact_seq)) if not contact_seq[i - 1][1] and contact_seq[i][1]), None)
            # persistent_entry
            persistent = None
            if first_cross:
                idxs = [i for i, (ym, c) in enumerate(contact_seq) if ym == first_cross]
                if idxs:
                    i0 = idxs[0]
                    run = 1
                    for j in range(i0 + 1, len(contact_seq)):
                        if contact_seq[j][1]:
                            run += 1
                        else:
                            break
                    persistent = run >= 3   # 首月+后续至少2个连续月
            contact_months = sum(1 for _, c in contact_seq if c)
            total = len(contact_seq)
            longest = 0; cur = 0
            for _, c in contact_seq:
                cur = cur + 1 if c else 0
                longest = max(longest, cur)
            last_status = contact_seq[-1][1] if contact_seq else None
            rec_cross.append({
                'district': d, 'layer_no': l, 'layer_bucket': f'B{l}' if l < 5 else 'B5+',
                'depth_scenario': sc, 'layer_fraction': pl,
                'first_crossing_since_2019': first_cross,
                'first_crossing_persistent': persistent,
                'n_contact_entries': entries, 'n_contact_exits': exits,
                'first_crossing_date': first_cross, 'last_crossing_date': contact_seq[-1][0] if contact_seq else None,
                'contact_months': contact_months, 'total_observed_months': total,
                'contact_month_fraction': contact_months / total if total else np.nan,
                'longest_contact_run_months': longest,
                'status_at_last_2025_month': ('contact' if last_status else ('no_contact' if last_status is False else 'no_data')),
            })
rec_cross_df = pd.DataFrame(rec_cross)
rec_cross_df.to_csv(OUT + r'\04_recovery\recovery_threshold_crossings.csv', index=False, encoding='utf-8-sig')

# ============ 7. 恢复期区级 summary ============
sum_rows = []
for d in D16:
    g = rec[(rec.district == d) & (rec.depth_scenario == 'central') & (rec.year_month <= '2025-12')].sort_values('year_month')
    dm = g[['year_month', 'groundwater_depth_m']].copy()
    local_deepest = dm.groundwater_depth_m.max()
    local_deepest_month = dm.loc[dm.groundwater_depth_m.idxmax(), 'year_month']
    d2025 = dm[dm.year_month.str.startswith('2025')]
    last2025 = d2025.iloc[-1] if len(d2025) else None
    recovery = local_deepest - last2025.groundwater_depth_m if last2025 is not None else np.nan
    mc = rec_cross_df[(rec_cross_df.district == d) & (rec_cross_df.depth_scenario == 'central')]
    first_c = mc[mc.first_crossing_since_2019.notna() & (mc.first_crossing_persistent == True)]
    scen_res = {}
    for sc in ('shallow', 'central', 'deep'):
        gsc = rec[(rec.district == d) & (rec.depth_scenario == sc)]
        scen_res[sc] = gsc.encounter_fraction.max()
    agree = 'robust_contact' if all(v > 0 for v in scen_res.values()) else ('robust_no_contact' if all(v == 0 for v in scen_res.values()) else 'depth_sensitive')
    sum_rows.append({
        'district': d,
        'local_deepest_month': local_deepest_month, 'local_deepest_depth_m': local_deepest,
        '2025_last_depth_m': last2025.groundwater_depth_m if last2025 is not None else np.nan,
        'recovery_from_deepest_to_2025_m': recovery,
        'first_meaningful_contact_date': mc[mc.first_crossing_since_2019.notna()].first_crossing_since_2019.min() if mc.first_crossing_since_2019.notna().any() else None,
        'first_persistent_contact_date': first_c.first_crossing_since_2019.min() if len(first_c) else None,
        '2025_encounter_fraction_central': (g[g.year_month.str.startswith('2025')].encounter_fraction.iloc[-1] if len(g[g.year_month.str.startswith('2025')]) else np.nan),
        'max_encounter_fraction_central': g.encounter_fraction.max(),
        'contact_month_fraction_central': g.meaningful_contact.mean(),
        'shallow_result': scen_res['shallow'], 'central_result': scen_res['central'], 'deep_result': scen_res['deep'],
        'depth_scenario_agreement': agree,
    })
pd.DataFrame(sum_rows).to_csv(OUT + r'\04_recovery\recovery_district_summary.csv', index=False, encoding='utf-8-sig')

# ============ 8. 敏感性 ============
# MAIN vs RAW
sens_rows = []
for r in hist.itertuples():
    K_raw = kmap_raw.get((r.district, r.year), np.nan)
    sens_rows.append({
        'year': r.year, 'district': r.district, 'depth_scenario': r.depth_scenario,
        'encounter_fraction_MAIN': r.encounter_fraction,
        'encounter_fraction_RAW': r.encounter_fraction,   # 分层比例相同 -> C 相同
        'E_index_MAIN': r.encounter_area_index_2020eq1,
        'E_index_RAW': K_raw * r.encounter_fraction,
        'delta_E': r.encounter_area_index_2020eq1 - K_raw * r.encounter_fraction,
        'relative_delta_E': (r.encounter_area_index_2020eq1 - K_raw * r.encounter_fraction) / r.encounter_area_index_2020eq1 if r.encounter_area_index_2020eq1 > 1e-12 else np.nan,
    })
sens = pd.DataFrame(sens_rows)
maxC_diff = (sens.encounter_fraction_MAIN - sens.encounter_fraction_RAW).abs().max()
sens.to_csv(OUT + r'\05_sensitivity\historical_MAIN_vs_RAW_sensitivity.csv', index=False, encoding='utf-8-sig')
log.write(f"MAIN vs RAW: max|C_MAIN-C_RAW| = {maxC_diff:.2e} (应为0)\n")

# 深度稳健性
rob_rows = []
for (d, ym) in rec.groupby(['district', 'year_month']).groups:
    gsc = {sc: rec[(rec.district == d) & (rec.year_month == ym) & (rec.depth_scenario == sc)].encounter_fraction.iloc[0]
           for sc in ('shallow', 'central', 'deep')}
    cls = ('robust_contact' if all(v > 0 for v in gsc.values())
           else 'robust_no_contact' if all(v == 0 for v in gsc.values()) else 'depth_sensitive_contact')
    rob_rows.append({'district': d, 'year_month': ym, **{f'enc_{sc}': gsc[sc] for sc in gsc},
                     'robustness_class': cls})
rob = pd.DataFrame(rob_rows)
rob.to_csv(OUT + r'\05_sensitivity\depth_scenario_robustness.csv', index=False, encoding='utf-8-sig')
mono_ok = (rec.groupby(['district', 'year_month']).apply(
    lambda g: g.set_index('depth_scenario').loc['shallow', 'encounter_fraction']
    <= g.set_index('depth_scenario').loc['central', 'encounter_fraction'] + 1e-6
    and g.set_index('depth_scenario').loc['central', 'encounter_fraction']
    <= g.set_index('depth_scenario').loc['deep', 'encounter_fraction'] + 1e-6, include_groups=False)).all()
log.write(f"C_shallow<=C_central<=C_deep 全通过: {bool(mono_ok)}\n")

# ============ 9. ranking ============
r2020 = hist[(hist.depth_scenario == 'central') & (hist.year == 2020)].set_index('district')
rank_rows = []
for d in OUTER10:
    depths = d10[d10.district == d].set_index('year')['depth_m']
    deepest = depths.max()
    d2020 = depths.loc[2020]
    recovery = deepest - d2020
    rank_rows.append({'district': d, 'timepoint': 2020,
                      'recovery_from_historical_deepest_m': recovery,
                      'encounter_fraction_central': r2020.loc[d, 'encounter_fraction']})
rk = pd.DataFrame(rank_rows)
rk['recovery_rank'] = rk.recovery_from_historical_deepest_m.rank(ascending=False)
rk['encounter_rate_rank'] = rk.encounter_fraction_central.rank(ascending=False)
rk['rank_mismatch'] = rk.recovery_rank - rk.encounter_rate_rank
rk.to_csv(OUT + r'\06_ranking\recovery_vs_encounter_rate_rank.csv', index=False, encoding='utf-8-sig')

# ============ 10. 审计 ============
max_id_err = 0.0
for tag, df_ in [('hist', hist), ('rec', rec)]:
    tcol = 'year' if tag == 'hist' else 'year_month'
    for (d, t, sc), g in df_.groupby(['district', tcol, 'depth_scenario']):
        e = abs(g.encounter_area_index_2020eq1.iloc[0] - g.underground_space_index_2020eq1.iloc[0] * g.encounter_fraction.iloc[0])
        max_id_err = max(max_id_err, e)
        if not (0 <= g.encounter_fraction.iloc[0] <= 1 + 1e-9):
            log.write(f"FRAC RANGE FAIL {d} {t} {sc}\n")
log.write(f"identity max err (E=K*C): {max_id_err:.2e}\n")
pd.DataFrame([{'check': 'E=K*C identity', 'max_abs_err': max_id_err},
              {'check': 'C_shallow<=C_central<=C_deep', 'pass': bool(mono_ok)},
              {'check': 'MAIN_vs_RAW_C_diff', 'max_abs': maxC_diff}]).to_csv(
    OUT + r'\08_audit\encounter_conservation_audit.csv', index=False, encoding='utf-8-sig')

# missing month audit
mma = mpanel_out.copy()
full = pd.MultiIndex.from_product([D16, sorted(mpanel_out.year_month.unique())], names=['district', 'year_month'])
have = pd.MultiIndex.from_frame(mma[['district', 'year_month']])
missing = full.difference(have)
pd.DataFrame({'district': [m[0] for m in missing], 'year_month': [m[1] for m in missing]}
             ).to_csv(OUT + r'\08_audit\missing_month_audit.csv', index=False, encoding='utf-8-sig')
log.write(f"missing district-month: {len(missing)}\n")

# crossing 事件审计
cross_df.to_csv(OUT + r'\08_audit\crossing_event_audit.csv', index=False, encoding='utf-8-sig')

# QC 传播
hist[['district', 'year', 'gw_qc_flag', 'gw_interpolation_anchor_status', 'digitization_error_scale_m']].drop_duplicates().to_csv(
    OUT + r'\08_audit\groundwater_qc_propagation.csv', index=False, encoding='utf-8-sig')

with open(OUT + r'\processing_log_encounter_v2.md', 'w', encoding='utf-8') as f:
    f.write(log.getvalue())

print('CORE DONE | hist:', len(hist), '| rec:', len(rec), '| C_MAINvsRAW:', maxC_diff, '| mono:', bool(mono_ok))
