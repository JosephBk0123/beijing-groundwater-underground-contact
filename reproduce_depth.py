"""Recompute engineering-informed depth sensitivity from the frozen inputs."""
from pathlib import Path
from collections import Counter
import ast, hashlib, json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
OUT=HERE/'recomputed/depth'
OUT.mkdir(parents=True,exist_ok=True)
END=pd.Period('2025-12',freq='M')
SCENARIOS={'shallow':[3.5,7,10.5,14,17.5],'central':[5,9,13,17,21],'deep':[5.5,11,16.5,22,27.5]}
source_script=HERE/'original_scripts/Nature_results_freeze_v1/_scripts/fig4_spatial_and_s7_s9.py'
functions=[n for n in ast.parse(source_script.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='contact_runs']
assert len(functions)==1
namespace={}
exec(compile(ast.Module(body=functions,type_ignores=[]),str(source_script),'exec'),namespace)
runs=namespace['contact_runs']
inputs=[HERE/'inputs/depth_time_cube_MAIN.csv',HERE/'inputs/groundwater_monthly.csv',HERE/'inputs/groundwater_historical_direct10.csv',HERE/'results/recovery_encounter_monthly.csv',HERE/'results/historical_encounter.csv',source_script]
protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
cube=pd.read_csv(inputs[0])
prof=cube[cube.year==2020].pivot(index='district',columns='layer_no',values='layer_fraction').sort_index()
assert prof.shape==(16,5) and (prof[5]==0).all()
water=pd.read_csv(inputs[1])
water=water[(water.year_month<='2025-12')&water.depth_mean_m.notna()].copy()
water['district']=water.district.apply(lambda s:s if s.endswith('区') else s+'区')
water['month']=pd.PeriodIndex(water.year_month,freq='M')
water=water.sort_values(['district','month']).reset_index(drop=True)
assert len(water)==1193 and set(water.district)==set(prof.index)
hist=pd.read_csv(inputs[2])
hist=hist.sort_values(['district','year']).reset_index(drop=True)
assert len(hist)==210
K=cube[cube.layer_no==1].set_index(['district','year']).underground_space_index_2020eq1
panels={d:g.set_index('month').depth_mean_m.reindex(pd.period_range(g.month.min(),END,freq='M')) for d,g in water.groupby('district')}

def encounter(table,depths,depth_col):
    weights=prof.reindex(table.district).to_numpy()
    return ((table[depth_col].to_numpy()[:,None]<=np.asarray(depths))*weights).sum(axis=1)

def state_events(state,q):
    episodes=runs(state)
    longest=max((n for _,_,n in episodes),default=0)
    terminal=next((n for _,b,n in episodes if b==END),0)
    if state.iloc[0]==1: category='pre_existing_contact'
    elif not episodes: category='no_observed_contact'
    elif terminal>=q: category='new_persistent_activation'
    elif state.iloc[-1]==0 and longest<q: category='transient_only_contact'
    else: category='other_observed_contact'
    new=[r for r in episodes if r[0]!=state.index[0] and state.get(r[0]-1,np.nan)==0]
    first=new[0] if new else None
    persistent=next((r for r in new if r[2]>=q),None)
    return dict(category=category,first_observed_contact=str(episodes[0][0]) if episodes else '',first_new_contact=str(first[0]) if first else '',first_persistent_onset=str(persistent[0]) if persistent else '',first_persistence_confirmed=str(persistent[0]+q-1) if persistent else '',terminal_run_months=terminal,longest_run_months=longest),episodes,new

def district_events(depths,q=6):
    rows=[]
    for d,full in panels.items():
        z=max(z for z,w in zip(depths,prof.loc[d]) if w>1e-9)
        state=(full<=z).astype(float).where(full.notna())
        event,_,_=state_events(state,q)
        rows.append(dict(district=d,observed_months=int(full.notna().sum()),missing_months=int(full.isna().sum()),**event))
    return pd.DataFrame(rows).set_index('district')

base_C=encounter(water,SCENARIOS['central'],'depth_mean_m')
base_hist=encounter(hist,SCENARIOS['central'],'depth_m')
base_events=district_events(SCENARIOS['central'])
assert Counter(base_events.category)=={'new_persistent_activation':9,'pre_existing_contact':3,'no_observed_contact':3,'transient_only_contact':1}
archived=pd.read_csv(inputs[3])
archived=archived[(archived.depth_scenario=='central')&(archived.year_month<='2025-12')].set_index(['district','year_month'])
np.testing.assert_allclose(base_C,archived.encounter_fraction.reindex(pd.MultiIndex.from_frame(water[['district','year_month']])),atol=1e-10,rtol=0)
old_hist=pd.read_csv(inputs[4])
old_hist=old_hist[old_hist.depth_scenario=='central'].set_index(['district','year'])
np.testing.assert_allclose(base_hist,old_hist.encounter_fraction.reindex(pd.MultiIndex.from_frame(hist[['district','year']])),atol=1e-10,rtol=0)
original_binary_change=(encounter(water,SCENARIOS['shallow'],'depth_mean_m')>1e-9)!=(encounter(water,SCENARIOS['deep'],'depth_mean_m')>1e-9)
assert int(original_binary_change.sum())==325
assert [r[2] for r in runs(pd.Series([0,1,1,np.nan,1,1,0],index=pd.period_range('2020-01',periods=7,freq='M')))]==[2,2]

cases=[
    dict(case_id='E1',source_project_name='科研楼等3项（北京城建集团有限责任公司学院南路62号科研楼项目）',source_entry_number=2,case_name='学院南路62号科研楼',heights=[5.75,4,4],reported_floor_elevations=None,indoor_outdoor_difference_m=.3,zero_absolute_elevation_m=52.140,base_delta_m=.3,source_url='https://zjw.beijing.gov.cn/bjjs/kjcxytg/jzyxjsyysfgc/ysgs/743807857/index.shtml',source_status='official project overview; first-floor datum and indoor-above-outdoor direction are explicit model assumptions'),
    dict(case_id='E2',case_name='凯恒中心',heights=[5.7,3.3,3.3],reported_floor_elevations=None,indoor_outdoor_difference_m=None,zero_absolute_elevation_m=None,base_delta_m=0,source_url='https://zjw.beijing.gov.cn/bjjs/kjcxytg/jzyxjsyysfgc/ysgs/743807698/index.shtml',source_status='official storey heights; outdoor datum not supplied; zero-offset conversion is conditional'),
    dict(case_id='E3',case_name='金方大厦',heights=[3.35,4.2],reported_floor_elevations=[-3.35,-7.55],indoor_outdoor_difference_m=None,zero_absolute_elevation_m=None,base_delta_m=0,source_url='https://static.cninfo.com.cn/finalpage/2013-01-08/61992737.PDF',source_status='appraisal PDF page 20; reported floor elevations verified, outdoor datum and floor surface unresolved'),
    dict(case_id='E4',source_project_name='专利技术研发中心研发用房建设项目',source_entry_number=1,case_name='国家知识产权局专利局专利审查协作北京中心专利大厦（北京市丰台区汽车博物馆南路2号）',heights=[4,5.1,5.1],reported_floor_elevations=None,indoor_outdoor_difference_m=.3,zero_absolute_elevation_m=47.200,base_delta_m=.3,source_url='https://zjw.beijing.gov.cn/bjjs/kjcxytg/jzyxjsyysfgc/ysgs/743807857/index.shtml',source_status='official project overview; first-floor datum and indoor-above-outdoor direction are explicit model assumptions'),
]
(OUT/'工程来源与转换假设.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf-8')
configs=[dict(config_id=k,case_id='',case_name=k,delta_m=np.nan,tail_rule='original',primary=True,depths=z,supported_floors=4) for k,z in SCENARIOS.items()]
geometry=[]
supported_rows=[]
for case in cases:
    # z_l = -relative floor elevation - delta; delta = first-floor datum above outdoor ground.
    relative=np.asarray(case['reported_floor_elevations']) if case['reported_floor_elevations'] is not None else -np.cumsum(case['heights'])
    if case['case_id']=='E3': np.testing.assert_allclose(-np.diff(relative),[4.2])
    n=len(relative)
    for delta in [-.3,0,.3]:
        tag='m03' if delta<0 else ('p03' if delta>0 else 'zero')
        known=-relative-delta
        assert (known>0).all() and (np.diff(known)>0).all()
        for i,z in enumerate(known):
            geometry.append(dict(case_id=case['case_id'],case_name=case['case_name'],delta_m=delta,layer_bucket=f'B{i+1}',reported_storey_height_m=case['heights'][i],relative_floor_elevation_m=relative[i],floor_elevation_basis='reported' if case['reported_floor_elevations'] is not None else 'calculated from storey heights with first-floor datum assumed',nominal_depth_below_ground_m=z,central_depth_m=SCENARIOS['central'][i],difference_from_central_m=z-SCENARIOS['central'][i],primary_delta=delta==case['base_delta_m']))
        # Compare only documented levels, holding the full-stock denominator fixed.
        z_supported=np.r_[known,[-np.inf]*(5-n)]
        central_supported=np.r_[SCENARIOS['central'][:n],[-np.inf]*(5-n)]
        c1=encounter(water,z_supported,'depth_mean_m');c0=encounter(water,central_supported,'depth_mean_m')
        supported_rows.append(dict(case_id=case['case_id'],delta_m=delta,supported_floors=n,mean_absolute_change_pp=100*float(np.abs(c1-c0).mean()),max_absolute_change_pp=100*float(np.abs(c1-c0).max()),binary_contact_changed_months=int(((c1>1e-9)!=(c0>1e-9)).sum()),normalization='original total district layer area; unsourced layers excluded from both comparators, no renormalization'))
        for tail in ['continue_last_increment','retain_central_unsourced']:
            depths=list(known)
            depths += [known[-1]+case['heights'][-1]*(i-n+1) if tail=='continue_last_increment' else SCENARIOS['central'][i] for i in range(n,5)]
            assert min(np.diff(depths))>0
            configs.append(dict(config_id=f"{case['case_id']}_{tag}_{'extend' if tail=='continue_last_increment' else 'central_tail'}",case_id=case['case_id'],case_name=case['case_name'],delta_m=delta,tail_rule=tail,primary=delta==case['base_delta_m'],depths=depths,supported_floors=n))
assert len(configs)==27
pd.DataFrame(geometry).to_csv(OUT/'工程几何与原阈值对照.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(supported_rows).to_csv(OUT/'仅资料覆盖层级的对照.csv',index=False,encoding='utf-8-sig')
pd.DataFrame([{k:v for k,v in c.items() if k!='depths'}|{f'B{i+1}_m':z for i,z in enumerate(c['depths'])} for c in configs]).to_csv(OUT/'全部27组深度配置.csv',index=False,encoding='utf-8-sig')

def summarize(config_id,depths):
    C=encounter(water,depths,'depth_mean_m')
    ev=district_events(depths)
    changed=ev.category!=base_events.category
    first_changed=ev.first_new_contact!=base_events.first_new_contact
    paired=(ev.first_new_contact!='')&(base_events.first_new_contact!='')
    shifts=[pd.Period(a,freq='M').ordinal-pd.Period(b,freq='M').ordinal for a,b in zip(ev.loc[paired,'first_new_contact'],base_events.loc[paired,'first_new_contact'])]
    max_idx=int(np.abs(C-base_C).argmax())
    h=encounter(hist,depths,'depth_m')
    return dict(config_id=config_id,new_persistent_count=int((ev.category=='new_persistent_activation').sum()),new_persistent_districts='；'.join(ev.index[ev.category=='new_persistent_activation']),six_month_class_changed_districts='；'.join(ev.index[changed]),six_month_class_changed_n=int(changed.sum()),first_new_contact_changed_n=int(first_changed.sum()),first_new_contact_changed_districts='；'.join(ev.index[first_changed]),max_abs_paired_first_new_shift_months=max(map(abs,shifts),default=0),binary_contact_changed_months=int(((C>1e-9)!=(base_C>1e-9)).sum()),mean_absolute_encounter_change_pp=100*float(np.abs(C-base_C).mean()),max_absolute_encounter_change_pp=100*float(np.abs(C-base_C).max()),max_change_district=water.iloc[max_idx].district,max_change_month=water.iloc[max_idx].year_month,historical_mean_absolute_change_pp=100*float(np.abs(h-base_hist).mean()),historical_max_absolute_change_pp=100*float(np.abs(h-base_hist).max()))

summary=[];monthly=[];historical=[];district_rows=[];layer_rows=[]
for config in configs:
    cid=config['config_id'];depths=config['depths']
    summary.append(summarize(cid,depths))
    C=encounter(water,depths,'depth_mean_m')
    frame=water[['district','year_month','depth_mean_m']].copy()
    frame['config_id']=cid;frame['encounter_fraction']=C;frame['change_from_central_pp']=100*(C-base_C)
    monthly.append(frame)
    frame=hist[['district','year','depth_m','qc_flag']].copy()
    frame['config_id']=cid;frame['encounter_fraction']=encounter(hist,depths,'depth_m')
    frame['change_from_central_pp']=100*(frame.encounter_fraction-base_hist)
    frame['stock_proxy_K']=[K.loc[d,y] for d,y in zip(hist.district,hist.year)]
    frame['relative_temporal_index']=frame.encounter_fraction*frame.stock_proxy_K
    historical.append(frame)
    for q in [3,6,9,12]:
        ev=district_events(depths,q).reset_index()
        ev['config_id']=cid;ev['duration_months']=q
        district_rows.append(ev)
    for d,full in panels.items():
        for i,z in enumerate(depths):
            if prof.loc[d,i+1]<=1e-9:continue
            state=(full<=z).astype(float).where(full.notna())
            event,episodes,new=state_events(state,6)
            first=new[0] if new else None
            status=('confirmed_6_month' if first[2]>=6 else ('transient_first_run' if state.get(first[1]+1,np.nan)==0 else 'insufficient_followup')) if first else 'no_observed_new_crossing'
            layer_rows.append(dict(config_id=cid,district=d,layer_bucket=f'B{i+1}',nominal_depth_m=z,first_new_crossing=event['first_new_contact'],first_run_end=str(first[1]) if first else '',first_run_months=first[2] if first else np.nan,first_run_status=status,first_persistent_onset=event['first_persistent_onset'],max_contact_run_months=event['longest_run_months'],terminal_contact_run_months=event['terminal_run_months'],pre_existing_contact=state.iloc[0]==1))
summary=pd.DataFrame(summary)
pd.concat(monthly,ignore_index=True).to_csv(OUT/'月度接触比例全部配置.csv',index=False,encoding='utf-8-sig')
annual=pd.concat(historical,ignore_index=True)
annual.to_csv(OUT/'年度接触比例与时间指数全部配置.csv',index=False,encoding='utf-8-sig')
annual_dates=[]
for (cid,d),g in annual.groupby(['config_id','district'],sort=False):
    touched=g[g.encounter_fraction>1e-9]
    annual_dates.append(dict(config_id=cid,district=d,first_observed_contact_year=int(touched.year.min()) if len(touched) else np.nan,contact_at_first_observed_year=bool(g.iloc[0].encounter_fraction>1e-9),annual_observation_note='sampled year-end states; no continuous within-year persistence inferred'))
pd.DataFrame(annual_dates).to_csv(OUT/'年度首次观测接触对照.csv',index=False,encoding='utf-8-sig')
districts=pd.concat(district_rows,ignore_index=True)
assert len(districts)==1728
districts.to_csv(OUT/'逐区接触时间与持续分类.csv',index=False,encoding='utf-8-sig')
layers=pd.DataFrame(layer_rows)
layers.to_csv(OUT/'逐层首次接触与连续段.csv',index=False,encoding='utf-8-sig')
summary.to_csv(OUT/'配置影响汇总.csv',index=False,encoding='utf-8-sig')
# Check all 24 original district-layer events.
old_events=pd.read_csv(HERE/'figure_tables/figS7_layer_timing_persistence_source.csv').set_index(['district','layer_bucket'])
new_events=layers[(layers.config_id=='central')&(layers.first_new_crossing!='')].set_index(['district','layer_bucket'])
assert set(new_events.index)==set(old_events.index) and len(new_events)==24
for column in ['first_new_crossing','first_run_end','first_run_months','first_run_status']:
    assert list(new_events[column].reindex(old_events.index))==list(old_events[column]),column

grid=[]
for a in np.arange(3.0,6.251,.25):
    for h in np.arange(3.25,5.501,.25):
        grid.append(dict(first_depth_m=float(a),increment_m=float(h),**summarize(f'grid_{a:.2f}_{h:.2f}',[a+i*h for i in range(5)])))
assert len(grid)==140
grid=pd.DataFrame(grid)
assert float(grid[(grid.first_depth_m==5)&(grid.increment_m==4)].iloc[0].max_absolute_encounter_change_pp)==0
grid.to_csv(OUT/'扩展140组参数网格.csv',index=False,encoding='utf-8-sig')
assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in protected.items())
primary=summary[summary.config_id.isin([c['config_id'] for c in configs if c['case_id'] and c['primary']])]
audit=dict(scope='Completed engineering-informed parameter sensitivity; conditional nominal ground conversion, not measured site-contact validation',cutoff='2025-12',valid_months=1193,historical_district_years=210,configuration_count=27,case_count=4,datum_offsets_m=[-.3,0,.3],datum_offset_definition='delta = first-floor reference elevation minus outdoor ground elevation; z = -relative floor elevation - delta',unknown_datum_offsets='analyst-selected perturbations; not measured or confidence bounds',tail_rules=['continue_last_increment','retain_central_unsourced'],original_depth_binary_change_count=325,original_depth_binary_change_fraction=325/1193,original_events_reproduced=24,duration_classification_rows=1728,grid_count=140,grid_first_depth_range_m=[3,6.25],grid_increment_range_m=[3.25,5.5],grid_persistent_count_range=[int(grid.new_persistent_count.min()),int(grid.new_persistent_count.max())],case_persistent_count_range=[int(summary.iloc[3:].new_persistent_count.min()),int(summary.iloc[3:].new_persistent_count.max())],primary_case_results=primary.to_dict('records'),all_config_summaries=summary.to_dict('records'),protected_sha256=protected,checks='passed: archived monthly/annual fractions, 325-month depth sensitivity, 24 layer-event identities, calendar missingness and source/manuscript hashes')
case_sets=[set(s.split('；')) for s in summary.iloc[3:].new_persistent_districts]
audit.update(case_all24_common_persistent_districts=sorted(set.intersection(*case_sets)),
    case_mean_absolute_change_pp_range=[float(summary.iloc[3:].mean_absolute_encounter_change_pp.min()),float(summary.iloc[3:].mean_absolute_encounter_change_pp.max())],
    case_max_paired_first_new_shift_months=int(summary.iloc[3:].max_abs_paired_first_new_shift_months.max()),
    descriptive_case_mean_nominal_B1_m=float(np.mean([-(-np.cumsum(c['heights']))[0]-c['base_delta_m'] for c in cases])),
    descriptive_case_mean_last_increment_m=float(np.mean([c['heights'][-1] for c in cases])),
    scientific_output_rows={'monthly':1193*27,'annual':210*27,'annual_dates':len(annual_dates),'district_duration':len(districts),'layer_events':len(layers)},
    reproduction_script=str(Path(__file__).resolve()))
(OUT/'工程深度补充分析核查.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(primary[['config_id','new_persistent_count','six_month_class_changed_n','first_new_contact_changed_n','mean_absolute_encounter_change_pp','max_absolute_encounter_change_pp']].to_string(index=False))
print('Expanded grid persistent-count range:',audit['grid_persistent_count_range'])
print('All-case persistent-count range:',audit['case_persistent_count_range'])
print(audit['checks'])
