"""Select one visible chart estimate per year and spatial unit; retain every source reading."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,math,hashlib,shutil,zipfile
D=Path('/mnt/data');O=D/'district_digitization_v1'
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,rr,fields=None):
 assert rr or fields
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rr[0]));w.writeheader();w.writerows(rr)
def num(x):
 try:return float(x)
 except (ValueError,TypeError):return None
raw=read(O/'district_year_end_all_sources_raw.csv')
annual={int(r['年份']):num(r['平原区年末地下水平均埋深(米)']) for r in read(D/'北京市历年平均地下水位_1986-2025.csv')}
annual[1980]=7.24
# City markers are audit controls only, never used to rescale district bars.
controls=[]; control_lookup={}
for r in raw:
 if r['district_raw']!='全市': continue
 y=int(r['year']);v=num(r['depth_raw_m']);a=annual.get(y);err=num(r['digitization_error_scale_m'])
 diff=(v-a) if v is not None and a is not None else None
 bad=diff is not None and abs(diff)>max(.5,err or 0)
 q=dict(source_bulletin_year=r['source_bulletin_year'],year=y,source_file=r['source_file'],source_pdf_page=r['source_pdf_page'],source_figure=r['source_figure'],city_figure_depth_m=v,city_text_or_annual_table_depth_m=a,figure_minus_text_m=round(diff,3) if diff is not None else '',screening_threshold_m=max(.5,err or 0),flag_figure_text_disagreement=bad,used_to_rescale_district_values=False)
 controls.append(q);control_lookup[(int(r['source_bulletin_year']),y)]=q
write(O/'district_chart_city_control_audit.csv',controls)
G=defaultdict(list)
for r in raw:
 if r['district_raw']!='全市': G[(int(r['year']),r['district_raw'])].append(r)
pairs=[];stats={}
for key,rr in G.items():
 valid=[r for r in rr if num(r['depth_raw_m']) is not None];diffmax=0;conf=False
 for i,a in enumerate(valid):
  for b in valid[i+1:]:
   va=num(a['depth_raw_m']);vb=num(b['depth_raw_m']);diff=abs(va-vb)
   tol=max(.5,num(a['digitization_error_scale_m'])+num(b['digitization_error_scale_m']))
   flag=diff>tol
   diffmax=max(diffmax,diff);conf|=flag
   pairs.append(dict(year=key[0],district_raw=key[1],source_record_a=a['source_record_id'],source_record_b=b['source_record_id'],source_file_a=a['source_file'],source_file_b=b['source_file'],depth_a_m=va,depth_b_m=vb,absolute_difference_m=round(diff,3),screening_tolerance_m=round(tol,3),flag_between_report_disagreement=flag,interpretation='agreement_is_not_independent_observational_validation'))
 stats[key]={'n_source_figures':len(valid),'source_reading_range_m':round(diffmax,3) if len(valid)>1 else '', 'conflict':conf}
write(O/'district_year_end_cross_report_audit.csv',pairs)
unitid={'通州':'tongzhou','大兴':'daxing','房山':'fangshan','门头沟':'mentougou','昌平':'changping','顺义':'shunyi','延庆':'yanqing','怀柔':'huairou','密云':'miyun','平谷':'pinggu','城近郊':'inner_urban_aggregate_legacy','城六区':'six_urban_districts_aggregate'}
main=[]
for (y,label),rr in sorted(G.items()):
 if y!=1980 and not 2000<=y<=2025:continue
 # 1980 legacy reference uses one declared source, not an average of copies.
 # Modern six-urban-district reference remains in the all-source table, not merged with the legacy aggregate.
 if y==1980 and label=='城六区':continue
 valid=[r for r in rr if num(r['depth_raw_m']) is not None]
 if not valid:continue
 if y==1980:
  src=next((r for r in valid if int(r['source_bulletin_year'])==2020),None)
  if src is None: src=min(valid,key=lambda r:int(r['source_bulletin_year']))
  selection='declared_1980_reference_from_2020_vector_chart'
 else:
  valid.sort(key=lambda r:(int(r['source_bulletin_year'])!=y,abs(int(r['source_bulletin_year'])-y)))
  src=valid[0]; selection='current_year_bulletin_preferred' if int(src['source_bulletin_year'])==y else 'next_available_bulletin_previous_year_series'
 flag=[];st=stats[(y,label)];control=control_lookup[(int(src['source_bulletin_year']),y)]
 if st['conflict']:flag.append('cross_report_value_disagreement')
 if control['flag_figure_text_disagreement']:flag.append('source_chart_city_control_disagreement')
 if 'draft' in src['source_qc']:flag.append('bulletin_marked_draft')
 if src['digitization_method'].startswith('photograph'):flag.append('low_resolution_photographed_chart')
 if y==2001 and label=='密云':flag.append('primary_figure_occluded_used_alternate_source')
 if label in ['城近郊','城六区']:flag.append('aggregate_not_single_district')
 if label=='城六区':flag.append('not_merged_with_legacy_inner_urban_aggregate')
 m=dict(year=y,date=f'{y}-12-31',district=label+'区' if label not in ['城近郊','城六区'] else label,district_raw=label,spatial_unit_id=unitid[label],spatial_level='district_plain_part' if label not in ['城近郊','城六区'] else 'multi_district_aggregate',depth_m=round(num(src['depth_raw_m']),1),selected_unrounded_digitization_m=num(src['depth_raw_m']),variable='groundwater_depth_below_ground',unit='m',positive_direction='down',temporal_statistic='year_end',record_type='official_figure_digitized',is_1980_reference=(y==1980),source_file=src['source_file'],source_bulletin_year=int(src['source_bulletin_year']),source_pdf_page=int(src['source_pdf_page']),source_figure=src['source_figure'],source_series_role=src['source_series_role'],source_record_id=src['source_record_id'],selection_rule=selection,digitization_method=src['digitization_method'],digitization_error_scale_m=num(src['digitization_error_scale_m']),n_source_figures=st['n_source_figures'],source_reading_range_m=st['source_reading_range_m'],city_control_difference_m=control['figure_minus_text_m'],year_to_year_change_m='',qc_flag=';'.join(flag),interpolation_anchor_status='',cross_year_spatial_support_verified=False)
 main.append(m)
# Flag adjacent-year changes for review; this is not a deletion rule or a claim of hydrological error.
prev={}
for r in main:
 u=r['spatial_unit_id'];a=prev.get(u)
 if a is not None and r['year']==a['year']+1:
  change=r['depth_m']-a['depth_m'];r['year_to_year_change_m']=round(change,1)
  if abs(change)>5:r['qc_flag']+=';large_year_to_year_change_gt5m'
 prev[u]=r
for r in main:
 flags=set(filter(None,r['qc_flag'].split(';')))
 severe=flags & {'cross_report_value_disagreement','source_chart_city_control_disagreement','bulletin_marked_draft','low_resolution_photographed_chart','primary_figure_occluded_used_alternate_source','large_year_to_year_change_gt5m'}
 r['qc_flag']=';'.join(sorted(flags)) if flags else 'no_screening_flag'
 r['interpolation_anchor_status']='review_before_use' if severe else 'candidate_anchor_not_interpolation_validated'
 if r['is_1980_reference']:r['interpolation_anchor_status']='historical_reference_not_time_gap_fill'
main.sort(key=lambda r:(r['year'],r['spatial_unit_id']))
name='beijing_district_groundwater_year_end_1980_2000_2025_digitized.csv'
write(O/name,main);shutil.copy2(O/name,D/name)
# Convenient matrix: missing columns remain empty when the aggregate label changes.
labels=['通州','大兴','房山','门头沟','昌平','顺义','延庆','怀柔','密云','平谷','城近郊','城六区']
wide=[]
for y in sorted(set(r['year'] for r in main)):
 row={'year':y}; row.update({label:next((r['depth_m'] for r in main if r['year']==y and r['district_raw']==label),'') for label in labels});wide.append(row)
write(O/'district_year_end_matrix_m.csv',wide)
# Input provenance and record checks.
sourcefiles=sorted(set(r['source_file'] for r in raw))
manifest=[dict(source_file=f,sha256=hashlib.sha256((D/f).read_bytes()).hexdigest(),size_bytes=(D/f).stat().st_size) for f in sourcefiles]
write(O/'source_file_hashes.csv',manifest)
ys={y:sum(r['year']==y for r in main) for y in sorted(set(r['year'] for r in main))}
assert all(ys[y]==(12 if y==2023 else 11) for y in range(2000,2026)),ys
assert ys[1980]==11
assert len({(r['year'],r['spatial_unit_id']) for r in main})==len(main)==298
assert all(0<=r['depth_m']<100 for r in main)
assert len(raw)==828
summary={'main_records':len(main),'records_2000_2025':sum(2000<=r['year']<=2025 for r in main),'reference_records_1980':ys[1980],'source_bulletins_digitized':len(sourcefiles),'all_source_records_including_city_controls':len(raw),'district_source_records':sum(r['district_raw']!='全市' for r in raw),'city_control_records':len(controls),'unresolved_source_endpoints':sum(num(r['depth_raw_m']) is None for r in raw),'selected_record_qc_counts':dict(Counter(r['interpolation_anchor_status'] for r in main)),'selected_cross_report_disagreement':sum('cross_report_value_disagreement' in r['qc_flag'] for r in main),'year_counts':ys,'interpolation_performed':False,'rescaled_to_city_anchor':False}
(O/'validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
conf=[p for p in pairs if p['year']>=2000 and p['flag_between_report_disagreement']]
conf.sort(key=lambda p:p['absolute_difference_m'],reverse=True)
print(json.dumps(summary,ensure_ascii=False,indent=2));print('Largest conflicts:',conf[:8])
