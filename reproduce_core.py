"""Run from any folder with Python >=3.10; only the standard library is needed.
Verifies the archived tabular analysis, not raw GIS extraction or figure export.
"""
from pathlib import Path
from collections import Counter,defaultdict
from itertools import combinations
import csv,json,math,statistics,sys

BASE=Path(__file__).resolve().parent
def read(name):
    with (BASE/name).open(encoding='utf-8-sig',newline='') as file:
        return list(csv.DictReader(file))
def ordinal(ym):
    y,m=map(int,ym.split('-')); return 12*y+m-1
def runs(states):
    out=[]; start=None
    for i,state in enumerate(states+[None]):
        if state is True and start is None: start=i
        if state is not True and start is not None:
            out.append((start,i-1,i-start));start=None
    return out
assert runs([False,True,True,None,True,True,False])==[(1,2,2),(4,5,2)]

period=read('inputs/groundwater_period_panel_v3.csv')
monthly=read('inputs/groundwater_monthly.csv')
groups=defaultdict(list)
districts=sorted({r['district'] for r in monthly})
for row in period:
    for d in districts:
        if row[d]: groups[(d,row['观测日期'][:7])].append(float(row[d]))
monthly_valid=0
for r in monthly:
    values=groups[(r['district'],r['year_month'])]
    assert int(r['n_periods'])==len(values)
    if values:
        assert math.isclose(statistics.mean(values),float(r['depth_mean_m']),abs_tol=1e-10)
        monthly_valid+=1
    else: assert not r['depth_mean_m']

cube=read('inputs/depth_time_cube_MAIN.csv')
profiles=defaultdict(list); kmap={}
for r in cube:
    if r['year']=='2020': profiles[r['district']].append(r)
    if r['layer_no']=='1': kmap[(r['district'],r['year'])]=float(r['underground_space_index_2020eq1'])
for profile in profiles.values():
    assert abs(sum(float(r['layer_fraction']) for r in profile)-1)<1.1e-6
def encounter(d,depth,sc):
    return sum(float(r['layer_fraction']) for r in profiles[d] if float(r['depth_'+sc+'_m'])>=depth)

recovery=read('results/recovery_encounter_monthly.csv')
for r in recovery:
    c=encounter(r['district'],float(r['groundwater_depth_m']),r['depth_scenario'])
    assert math.isclose(c,float(r['encounter_fraction']),abs_tol=1e-10)
hist=read('results/historical_encounter.csv')
for r in hist:
    c=encounter(r['district'],float(r['groundwater_depth_m']),r['depth_scenario'])
    assert math.isclose(c,float(r['encounter_fraction']),abs_tol=1e-10)
    assert math.isclose(c*kmap[(r['district'],r['year'])],float(r['encounter_area_index_2020eq1']),abs_tol=1e-10)

central=[r for r in recovery if r['depth_scenario']=='central' and r['year_month']<='2025-12']
assert len(central)==1193
expected={r['district']:r for r in read('figure_tables/fig4_spatial_legacy_activation_source.csv')}
events={(r['district'],r['layer_bucket']):r for r in read('figure_tables/figS7_layer_timing_persistence_source.csv')}
classes=Counter(); statuses=Counter(); end=ordinal('2025-12'); event_count=0
for d in profiles:
    records={ordinal(r['year_month']):r for r in central if r['district']==d}
    start=min(records); months=list(range(start,end+1))
    contact=[float(records[m]['encounter_fraction'])>1e-9 if m in records else None for m in months]
    episodes=runs(contact); terminal=next((n for a,b,n in episodes if b==len(months)-1),0)
    longest=max((n for a,b,n in episodes),default=0)
    if contact[0]: category='pre_existing_contact'
    elif not episodes: category='no_contact_through_2025'
    elif terminal>=6: category='new_persistent_activation'
    elif contact[-1] is False and longest<6: category='transient_only_contact'
    else: raise AssertionError('Unclassified district: '+d)
    assert category==expected[d]['activation_class']
    assert longest==int(expected[d]['max_contact_run_months'])
    assert terminal==int(expected[d]['terminal_contact_run_months'])
    classes[category]+=1
    for layer in profiles[d]:
        if float(layer['layer_fraction'])<=1e-9: continue
        z=float(layer['depth_central_m'])
        states=[float(records[m]['groundwater_depth_m'])<=z if m in records else None for m in months]
        episodes=runs(states)
        new=[r for r in episodes if r[0]>0 and states[r[0]-1] is False]
        if not new:
            assert (d,layer['layer_bucket']) not in events
            continue
        a,b,n=new[0]; e=events[(d,layer['layer_bucket'])]
        assert start+a==ordinal(e['first_new_crossing'])
        status='confirmed_6_month' if n>=6 else ('transient_first_run' if b+1<len(states) and states[b+1] is False else 'insufficient_followup')
        assert status==e['first_run_status'] and n==int(e['first_run_months'])
        assert max(r[2] for r in episodes)==int(e['max_contact_run_months'])
        statuses[status]+=1;event_count+=1
robust=Counter()
for r in central:
    cs=[encounter(r['district'],float(r['groundwater_depth_m']),s)>1e-9 for s in ['shallow','central','deep']]
    robust['robust_contact' if all(cs) else 'robust_no_contact' if not any(cs) else 'depth_sensitive_contact']+=1
assert robust=={'robust_contact':409,'robust_no_contact':459,'depth_sensitive_contact':325}
assert statuses=={'confirmed_6_month':7,'transient_first_run':12,'insufficient_followup':5}
assert classes=={'new_persistent_activation':9,'pre_existing_contact':3,'transient_only_contact':1,'no_contact_through_2025':3}
historical=read('inputs/groundwater_historical_direct10.csv')
assert len(historical)==210 and sum(r['interpolation_anchor_status']=='review_before_use' for r in historical)==65
result={'python':sys.version.split()[0],'monthly_aggregation_valid_cells':monthly_valid,'monthly_encounter_scenario_rows_checked':len(recovery),'historical_encounter_rows_checked':len(hist),'recovery_window_valid_months':1193,'district_classes':classes,'first_layer_events':event_count,'first_run_statuses':statuses,'depth_sensitivity':robust,'historical_quality_flags_retained':65,'checks':'passed'}
print(json.dumps(result,ensure_ascii=False,indent=2))
(BASE/'verification_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
