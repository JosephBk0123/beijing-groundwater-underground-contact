"""Recompute the supplementary analyses and compare them with archived results."""
from pathlib import Path
import json,platform,runpy,sys
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
assert __debug__, 'Run without -O: scientific checks require assertions.'
runpy.run_path(str(HERE/'reproduce_depth.py'),run_name='__main__')
# Keep the generated engineering-source metadata consistent with the release copy.
source_name='工程来源与转换假设.json'
assert json.loads((HERE/'recomputed/depth'/source_name).read_text(encoding='utf-8')) == json.loads((HERE/'revision/depth'/source_name).read_text(encoding='utf-8'))
csv_checks={}
for expected in sorted((HERE/'revision/depth').glob('*.csv')):
    actual=HERE/'recomputed/depth'/expected.name
    assert actual.exists(),expected.name
    a=pd.read_csv(actual);b=pd.read_csv(expected)
    pd.testing.assert_frame_equal(a,b,check_dtype=False,rtol=1e-10,atol=1e-9)
    csv_checks[expected.name]=len(a)

duration=pd.read_csv(HERE/'revision/duration/duration_by_district_192.csv')
events=pd.read_csv(HERE/'recomputed/depth/逐区接触时间与持续分类.csv')
for row in duration.itertuples():
    matched=events[(events.config_id==row.scenario)&(events.duration_months==row.duration_months)&(events.district==row.district)]
    assert len(matched)==1 and matched.iloc[0].category==row.category,(row.scenario,row.district,row.duration_months)

profiles=pd.read_csv(HERE/'revision/duration/affected_layer_profiles.csv')
water=pd.read_csv(HERE/'inputs/groundwater_monthly.csv')
water=water[(water.year_month<='2025-12')&water.depth_mean_m.notna()].copy()
water['district']=water.district.apply(lambda s:s if s.endswith('区') else s+'区')
scenarios={'shallow':[3.5,7,10.5,14,17.5],'central':[5,9,13,17,21],'deep':[5.5,11,16.5,22,27.5]}
max_change=0.0
assert abs(profiles.old_area_m2.sum()-profiles.new_area_m2.sum())<1e-7
for district,g in profiles.groupby('district'):
    g=g.set_index('layer_bucket').reindex(['B1','B2','B3','B4','B5+'])
    old=g.old_area_m2/g.old_area_m2.sum();new=g.new_area_m2/g.new_area_m2.sum()
    np.testing.assert_allclose(old,g.old_fraction,atol=1e-12)
    np.testing.assert_allclose(new,g.new_fraction,atol=1e-12)
    delta=g.new_area_m2-g.old_area_m2
    np.testing.assert_allclose(delta.iloc[1:],0,atol=1e-9)
    assert abs(abs(delta.iloc[0])-1566)<1e-9
    depths=water[water.district==district].depth_mean_m.to_numpy()
    for z in scenarios.values():
        state=depths[:,None]<=np.array(z)
        c0=state@old.to_numpy();c1=state@new.to_numpy()
        assert np.array_equal(c0>1e-9,c1>1e-9)
        max_change=max(max_change,float(np.max(np.abs(c1-c0))*100))
assert abs(max_change-0.045990387375866026)<1e-9

lucc=pd.read_csv(HERE/'inputs/CNLUCC_district_class51.csv')
areas=lucc.pivot(index='year',columns='district',values='urban_land_area_km2').sort_index().cummax()
total=areas.sum(axis=1)
assert total.loc[2020]==1587 and total.loc[2015]==1443
t=2004+4.5/12
may2004=float(np.interp(t,total.index,total)/total.loc[2020])
year2015=float(total.loc[2015]/total.loc[2020])
assert abs(may2004-.805765595463138)<1e-12
assert abs(year2015-.9092627599243857)<1e-12
for year in areas.index:
    weights=areas.loc[2020]/total.loc[2020]
    k=areas.loc[year]/areas.loc[2020]
    assert abs(float((weights*k).sum())-total.loc[year]/total.loc[2020])<1e-12
result={'status':'passed','python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'csv_regressions':csv_checks,'duration_classes_checked':len(duration),'assignment_max_change_pp':max_change,'city_proxy_May2004':may2004,'city_proxy_2015':year2015,'scope':'Tabular reproduction and frozen-output regression; not independent physical validation or a raw GIS rebuild.'}
(HERE/'revision_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
