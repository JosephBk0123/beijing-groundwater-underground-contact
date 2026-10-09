"""Digitize visible district year-end charts. No annual anchoring or temporal interpolation."""
import csv,json,math
from pathlib import Path
import numpy as np,cv2,fitz
from PIL import Image,ImageDraw,ImageFont
D=Path('/mnt/data');O=D/'district_digitization_v1';W=O/'work';Q=O/'qa'
NORMAL='通州 大兴 房山 门头沟 昌平 顺义 延庆 怀柔 密云 平谷 城近郊 全市'.split()
ORD01='全市 平谷 密云 怀柔 延庆 顺义 昌平 门头沟 房山 大兴 通州 城近郊'.split()
ORD02='全市 城近郊 平谷 密云 怀柔 延庆 顺义 昌平 门头沟 房山 大兴 通州'.split()
ORD23='城近郊 门头沟 房山 通州 顺义 昌平 大兴 怀柔 平谷 密云 延庆 全市'.split()
ORD24=['城六区']+ORD23[1:]
ORD25='城六区 门头沟 房山 通州 顺义 延庆 昌平 大兴 怀柔 平谷 密云 全市'.split()
Y=[250,250,0];M=[250,0,250];B=[0,0,250];P=[150,150,250];V=[140,130,250];PINK=[250,150,205];BLUE=[0,105,250];PUR=[197,105,250];TEAL=[0,155,208]
# Axis scales read from the visible tick marks, never from city year-end anchor values.
CFG={
2001:dict(y0=58,scale=(619.5-58.5)/26,ymax=632,pal=[M,Y,B],order=ORD01,years=[2000,2001,1980],xmin=202,xmax=1115),
2002:dict(y0=217,scale=(800-217)/30,ymax=804,pal=[M,Y,B],order=ORD02,years=[2002,2001,1980],xmin=305,xmax=1218),
2008:dict(y0=363,scale=(1082.5-349)/40,ymax=1105,pal=[Y,PINK,B],xmin=430,xmax=1785),
2009:dict(y0=383,scale=(1118-382.5)/40,ymax=1140,pal=[Y,P,M],xmin=360,xmax=1845),
2010:dict(y0=403,scale=(1120-382.5)/45,ymax=1140,pal=[Y,P,M],xmin=410,xmax=1892),
2012:dict(y0=396,scale=3*(674.171-496.85)/45,ymax=940,pal=[Y,P,M],xmin=375,xmax=1340),
2013:dict(y0=105,scale=(337-103.6)/45,ymax=346,pal=[Y,M,P],xmin=92,xmax=510),
2014:dict(y0=410,scale=(1260-399.5)/45,ymax=1290,pal=[Y,M,[122,122,250]],xmin=314,xmax=1810),
2015:dict(y0=188,scale=(527-186)/45,ymax=542,pal=[Y,M,[150,140,250]],xmin=142,xmax=755),
2016:dict(y0=366,scale=(831.5-364)/45,ymax=843,pal=[Y,M,V],xmin=238,xmax=1322),
2017:dict(y0=242,scale=(776.5-239.5)/45,ymax=790,pal=[Y,M,V],xmin=215,xmax=1656),
2018:dict(y0=270,scale=(994.5-268.5)/45,ymax=1000,pal=[Y,M,V],xmin=180,xmax=1645),
2019:dict(y0=78,scale=4,ymax=260,pal=[Y,M,V],xmin=60,xmax=530),
2021:dict(y0=144,scale=(595-144)/40,ymax=600,pal=[Y,BLUE,PUR],xmin=128,xmax=1028),
2022:dict(y0=88,scale=(265-88)/30,ymax=269,pal=[Y,BLUE,PUR],xmin=68,xmax=570),
2023:dict(y0=135,scale=(415-135)/30,ymax=419,pal=[Y,BLUE,PUR],xmin=107,xmax=887,order=ORD23),
2024:dict(y0=153,scale=(637-153)/25,ymax=642,pal=[[250,168,216],TEAL,Y],xmin=98,xmax=928,order=ORD24,years=[2024,2023,1980]),
2025:dict(y0=97,scale=(401-95)/18,ymax=402,pal=[TEAL,[232,145,188],Y],xmin=69,xmax=660,order=ORD25,years=[2025,2024,1980]),
}
PHOTOS={
2003:dict(corners=[[159,557],[556,554],[558,770],[161,772]],maxdepth=30, pal=[[137,192,216],[212,173,192],[167,173,77]],order=ORD02,years=[2003,2002,1980],first=[72,95,117],last=[1097,1120,1142]),
2004:dict(corners=[[198,603],[628,603],[629,809],[197,811]],maxdepth=30,pal=[[147,171,159],[154,151,186],[203,158,145]],years=[2004,2003,1980],first=[20,45,69],last=[1126,1150,1174]),
2006:dict(corners=[[154,655],[558,650],[562,826],[149,830]],maxdepth=30,pal=[[188,177,65],[133,146,187],[135,83,90]],years=[2006,2005,1980],first=[20,49,78],last=[1120,1149,1178]),
2007:dict(corners=[[104,635],[604,639],[608,872],[100,853]],maxdepth=35,pal=[[58,121,161],[179,112,149],[218,193,55]],years=[2007,2006,1980],first=[32,54,76],last=[1114,1136,1158]),
}
PAGES={2001:7,2002:15,2003:17,2004:16,2006:15,2007:13,2008:12,2009:12,2010:12,2012:14,2013:13,2014:13,2015:13,2016:12,2017:13,2018:13,2019:13,2020:13,2021:13,2022:13,2023:13,2024:13,2025:13}
AXIS_ZERO={2001:58.5,2002:217.0,2008:349.0,2009:382.5,2010:382.5,2012:395.55,2013:103.6,2014:399.5,2015:186.0,2016:364.0,2017:239.5,2018:268.5,2019:77.0,2021:144.0,2022:88.0,2023:135.0,2024:153.0,2025:97.0}
for _y,_c in CFG.items(): _c['axis_zero_y']=AXIS_ZERO[_y]
for _y,_c in PHOTOS.items(): _c['axis_zero_y']=0.0
rows=[];issues=[];calibs={}
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
def runs(v,gap=1):
 ix=np.flatnonzero(v)
 return [] if len(ix)==0 else [p for p in np.split(ix,np.where(np.diff(ix)>gap)[0]+1) if len(p)]
def palette_masks(a,pal,threshold):
 dist=np.linalg.norm(a.astype(float)[:,:,None,:]-np.array(pal)[None,None,:,:],axis=3)
 choose=dist.argmin(2);return [(choose==k)&(dist[:,:,k]<threshold) for k in range(3)]
def addrec(yr,c,k,j,x,ystart,yend,depth,method,err,flag=''):
 target=c.get('years',[1980,yr-1,yr])[k];label=c.get('order',NORMAL)[j]
 fig= '未编号行政区埋深比较图' if yr<=2003 else ('图7' if yr<=2013 else ('图2-9' if yr==2025 else '图2-8'))
 rows.append(dict(source_record_id=f'GB{yr}_{target}_{j:02d}',year=target,date=f'{target}-12-31',district_raw=label,depth_raw_m=round(depth,3) if depth is not None else '',source_bulletin_year=yr,source_file=f'gb{yr}.pdf',source_pdf_page=PAGES[yr],source_figure=fig,source_series_role='reference_1980' if target==1980 else ('current_year' if target==yr else 'previous_year'),digitization_method=method,measurement_x=round(x,3),measurement_y_top=round(ystart,3) if ystart is not None else '',measurement_y_bottom=round(yend,3) if yend is not None else '',axis_coordinate_units='pdf_point' if method=='pdf_vector_rectangle' else ('rectified_pixel' if method.startswith('photograph') else 'image_pixel'),axis_units_per_m=round(c['scale'],6),axis_zero_y=c.get('axis_zero_y',130.96),digitization_error_scale_m=round(err,2),source_qc=flag))
for yr,c in CFG.items():
 a=np.array(Image.open(W/f'{yr}_native.png').convert('RGB'));masks=palette_masks(a,c['pal'],65 if yr==2008 else 85)
 annotated=Image.fromarray(a);draw=ImageDraw.Draw(annotated);starts=[]
 for k,mask in enumerate(masks):
  band=mask[max(0,c['y0']-3):c['y0']+18,c['xmin']:c['xmax']]
  counts=band.sum(0)
  rs=runs(counts>=max(2,band.shape[0]*.30),gap=2)
  rs=[r for r in rs if len(r)>=max(2,(c['xmax']-c['xmin'])/250)]
  centres=[float(np.median(r)+c['xmin']) for r in rs]
  if len(centres)!=12:
   issues.append(f'{yr} series{k} detected {len(centres)} bars: {centres}')
   continue
  for j,(x,run) in enumerate(zip(centres,rs)):
   width=len(run);xs=range(int(x)-max(0,width//8),int(x)+max(0,width//8)+1)
   ya=max(0,c['y0']-40);yb=min(a.shape[0],c['ymax'])
   cv=(mask[ya:yb,list(xs)].sum(1)>=max(1,len(xs)*.6)).astype(np.uint8)
   cv=cv2.morphologyEx(cv[:,None],cv2.MORPH_CLOSE,np.ones((3,1),np.uint8))[:,0]
   groups=runs(cv>0,gap=1);groups=[g for g in groups if len(g)>2 and g[0]<70]
   flag=''
   if not groups:
    issues.append(f'{yr} {k} {j} no vertical bar');continue
   g=max(groups,key=len);top=float(g[0]+ya);bottom=float(g[-1]+ya+1)
   depth=(bottom-c['axis_zero_y'])/c['scale']
   err=max(.10,2.5/c['scale'])
   if yr in [2001,2002,2008,2009,2010,2012,2013,2014,2015]:
    err=max(.30,err);flag='three_dimensional_chart_endpoint_approximation'
   if yr==2002:flag+=';bulletin_marked_draft'
   if yr==2001 and k==1 and j==2:
    depth=None;flag+=';bar_endpoint_occluded_by_legend'
   if depth is not None:
    draw.ellipse((x-3,bottom-3,x+3,bottom+3),fill='white',outline='black')
    draw.text((x-10,bottom+5),f'{depth:.1f}',fill='black',font=font)
   addrec(yr,c,k,j,x,top,bottom,depth,'raster_color_segment',err,flag)
   starts.append(top)
 draw.text((10,a.shape[0]-22),f'Axis scale {c["scale"]:.4f} px/m; NO city anchoring',fill='black',font=font)
 annotated.save(Q/f'{yr}_digitization_overlay.png')
 calibs[str(yr)]=c
# Photographed charts: perspective rectification of plot rectangle then colour-traced endpoints.
for yr,c in PHOTOS.items():
 a=np.array(Image.open(W/f'{yr}_native.png').convert('RGB'));H=cv2.getPerspectiveTransform(np.float32(c['corners']),np.float32([[0,0],[1200,0],[1200,660],[0,660]]))
 rect=cv2.warpPerspective(a,H,(1201,661),flags=cv2.INTER_LINEAR);c['scale']=660/c['maxdepth']
 
 bg=np.median(rect[-45:,:,:].reshape(-1,3),axis=0)
 dist=np.linalg.norm(rect.astype(float)[:,:,None,:]-np.array(c['pal']+[bg.tolist()])[None,None,:,:],axis=3)
 assigned=dist.argmin(2)
 masks=[(assigned==k)&(dist[:,:,k]<60) for k in range(3)]
 ann=Image.fromarray(rect);draw=ImageDraw.Draw(ann)
 for k,mask in enumerate(masks):
  for j,x in enumerate(np.linspace(c['first'][k],c['last'][k],12)):
   # follow the main coloured face in a narrow horizontal search; vertical smoothing removes scan speckle
   
   xx0=int(round(x));xa=max(0,xx0-22);xb=min(1201,xx0+23)
   counts=mask[5:45,xa:xb].sum(0)
   cand=runs(counts>=max(5,counts.max()*.80),gap=2)
   if cand:
    cand=max(cand,key=len);x=float(np.median(cand)+xa)
   xx=int(round(x));v=mask[:,max(0,xx-2):min(1201,xx+3)].mean(1)
   v=cv2.morphologyEx((v>.35).astype('uint8')[:,None],cv2.MORPH_CLOSE,np.ones((9,1),np.uint8))[:,0]
   groups=runs(v>0,1);groups=[g for g in groups if len(g)>8 and g[0]<35]
   if groups:
    g=max(groups,key=len);top=float(g[0]);end=float(g[-1]+1);depth=end/c['scale'];flag='photographed_chart_perspective_corrected;low_resolution'
   else:
    top=0;end=None;depth=None;flag='photographed_chart_endpoint_unresolved';issues.append(f'{yr} photo {k}/{j} unresolved')
   if end is not None:
    draw.ellipse((x-3,end-3,x+3,end+3),fill='white',outline='black');draw.text((x-12,end+8),f'{depth:.1f}',fill='black',font=font)
   addrec(yr,c,k,j,x,top,end,depth,'photograph_rectified_color_trace',.6,flag)
 ann.save(Q/f'{yr}_rectified_overlay.png');Image.fromarray(rect).save(W/f'{yr}_rectified.png');c['homography']=H.tolist();calibs[str(yr)]=c
# 2020 vector rectangle heights: no raster quantisation and no annual-value scaling.
yr=2020;p=fitz.open(D/'gb2020.pdf')[12]; c={'scale':(267.11-130.96)/45,'years':[1980,2019,2020]}
for dr in p.get_drawings():
 if len(dr['items'])==12 and dr['type']=='f':
  f=dr['fill'];k=0 if f[0]>.9 and f[1]>.9 else (1 if f[0]>.9 else 2)
  for j,(_,r,_) in enumerate(dr['items']):
   depth=r.height/c['scale'];addrec(2020,c,k,j,(r.x0+r.x1)/2,r.y0,r.y1,depth,'pdf_vector_rectangle',.05,'vector_geometry_not_original_tabular_value')
calibs['2020']={'scale_pdf_points_per_m':c['scale'],'zero_pdf_y':130.96,'maximum45_pdf_y':267.11,'method':'pdf_vector_rectangle'}
rows.sort(key=lambda r:(r['source_bulletin_year'],r['year'],r['district_raw']))
with (O/'district_year_end_all_sources_raw.csv').open('w',encoding='utf-8-sig',newline='') as f:
 wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
(O/'digitization_calibration.json').write_text(json.dumps(calibs,ensure_ascii=False,indent=2),encoding='utf8')
(O/'work'/'detection_issues.txt').write_text('\n'.join(issues),encoding='utf8')
print('Raw records:',len(rows),'expected',len(PAGES)*36,'missing',sum(r['depth_raw_m']=='' for r in rows))
print('\n'.join(issues))
for yr in PAGES:
 print(yr,[(r['year'],r['depth_raw_m']) for r in rows if r['source_bulletin_year']==yr and r['district_raw']=='全市'])
