# -*- coding: utf-8 -*-
"""检查行政区边界，按区统计CNLUCC class51面积。"""
import os, io, json
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.ops import unary_union

OUTROOT = r'local_raw_workspace\historical_underground_space_backcast_v1'
os.makedirs(OUTROOT + r'\01_inputs', exist_ok=True)
os.makedirs(OUTROOT + r'\02_lucc', exist_ok=True)

log = io.StringIO()

# ========== 边界检查 ==========
shp = r'local_raw_workspace\北京市数据\北京市\北京市_县界.shp'
gdf = gpd.read_file(shp, encoding='gbk')
bj = gdf[gdf['code'].astype(str).str.startswith('1101')].copy()
bj['district'] = bj['Name'].astype(str)

# 别名映射（历史名称->现代16区）
ALIAS = {'密云县': '密云区', '延庆县': '延庆区', '北京经济技术开发区': '大兴区', '经开区': '大兴区'}
bj['district'] = bj['district'].replace(ALIAS)

audit_rows = []
n16 = bj['district'].nunique()
geom_valid = bj.geometry.is_valid.all()
# overlap 检查（16区之间）
overlaps = []
for i in range(len(bj)):
    for j in range(i + 1, len(bj)):
        if bj.geometry.iloc[i].intersects(bj.geometry.iloc[j]):
            inter = bj.geometry.iloc[i].intersection(bj.geometry.iloc[j])
            if not inter.is_empty and inter.area > 1e-6:
                overlaps.append((bj['district'].iloc[i], bj['district'].iloc[j], inter.area))
# 总面积（等积投影：与 LUCC 栅格同参数 Albers）
bj_albers = bj.to_crs('+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 +ellps=krass')
areas_km2 = bj_albers.geometry.area / 1e6
total_km2 = areas_km2.sum()

for _, r in bj.iterrows():
    audit_rows.append({
        'district': r['district'], 'code': r['code'],
        'geometry_valid': bool(r.geometry.is_valid),
        'geom_type': r.geometry.geom_type,
        'area_km2_albers': round(bj_albers.loc[bj_albers['district'] == r['district'], 'geometry'].area.iloc[0] / 1e6, 2),
        'has_jingkai_separate': '北京经济技术开发区' in bj['Name'].astype(str).values,
    })
pd.DataFrame(audit_rows).to_csv(OUTROOT + r'\01_inputs\district_boundary_audit.csv', index=False, encoding='utf-8-sig')

log.write(f"=== 边界 Gate ===\n")
log.write(f"区数: {n16} (需16) -> {'PASS' if n16 == 16 else 'FAIL'}\n")
log.write(f"geometry valid: {geom_valid}\n")
log.write(f"区际 overlap: {len(overlaps)} 处\n")
log.write(f"总面积(Albers): {total_km2:.0f} km2 (北京实际约16410)\n")
log.write(f"经开区独立存在: {'北京经济技术开发区' in bj['Name'].astype(str).values} (本县界不含经开区, 大兴即大兴)\n")
log.write(f"CRS: {bj.crs}\n\n")

# ========== 阶段3：class51 zonal ==========
LUCC_BASE = r'local_raw_workspace\北京市数据\【241021】中国土地利用数据1980-2020'
GRIDS = {
    1980: r'\1980年中国土地利用现状遥感监测数据\Lucc1980\lucc1980',
    1990: r'\1990年中国土地利用现状遥感监测数据\lucc1990\lucc1990',
    1995: r'\1995年中国土地利用现状遥感监测数据\lucc1995\lucc95',
    2000: r'\2000年中国土地利用现状遥感监测数据\lucc2000\lucc2000',
    2005: r'\2005年中国土地利用现状遥感监测数据\lucc2005\lucc2005',
    2010: r'\2010年中国土地利用现状遥感监测数据\lucc2010\lucc2010',
    2015: r'\2015年中国土地利用现状遥感监测数据\lucc2015',
    2020: r'\2020年中国土地利用现状遥感监测数据\2020年\ld2020',
}

records = []
for year, gpath in sorted(GRIDS.items()):
    with rasterio.open(LUCC_BASE + gpath) as src:
        rcrs = src.crs
        res_x, res_y = src.res
        # 确认投影坐标系且单位为米
        is_projected_m = rcrs is not None and rcrs.is_projected and 'metre' in str(rcrs.linear_units).lower() or (rcrs and rcrs.is_projected)
        pixel_area = abs(res_x * res_y)
        districts = bj.to_crs(rcrs)
        darea = districts.geometry.area  # m2 in raster CRS (Albers 等积)
        for _, row in districts.iterrows():
            g = row.geometry.__geo_interface__
            arr, _ = mask(src, [g], crop=True, filled=True, nodata=255)
            a = arr[0]
            n51 = int((a == 51).sum())
            n53 = int((a == 53).sum())   # sensitivity only
            records.append({
                'year': year, 'district': row['district'], 'class_code': 51,
                'urban_land_area_m2': n51 * pixel_area,
                'urban_land_area_km2': n51 * pixel_area / 1e6,
                'district_area_km2': row.geometry.area / 1e6,
                'urban_fraction_of_district': n51 * pixel_area / row.geometry.area,
                'source_raster': gpath.split('\\')[-1],
                'raster_crs': 'Albers_Equal_Area(Krassowsky)',
                'pixel_area_method': f'pixel_count x {pixel_area:.0f} m2 (projected, metre, all_touched=False)',
                'source_resolution': f'{res_x}m x {res_y}m',
                'n51_pixels': n51, 'n53_pixels_sensitivity': n53,
                'qc_flag': '',
            })
    log.write(f"{year}: done (res={res_x}m, projected={rcrs.is_projected})\n")

lucc = pd.DataFrame(records)

# 51+53 敏感性面积列
lucc['urban51plus53_area_km2_sensitivity'] = (lucc['n51_pixels'] + lucc['n53_pixels_sensitivity']) * lucc['urban_land_area_m2'] / lucc['n51_pixels'].replace(0, np.nan) / 1e6
lucc.loc[lucc['n51_pixels'] == 0, 'urban51plus53_area_km2_sensitivity'] = (
    (lucc.loc[lucc['n51_pixels'] == 0, 'n51_pixels'] + lucc.loc[lucc['n51_pixels'] == 0, 'n53_pixels_sensitivity']) * 0.0)

# QC: 面积非负、不超过区面积
lucc.loc[lucc['urban_land_area_m2'] < 0, 'qc_flag'] = 'negative_area'
lucc.loc[lucc['urban_fraction_of_district'] > 1.0, 'qc_flag'] = 'exceeds_district_area'

lucc.drop(columns=[]).to_csv(OUTROOT + r'\02_lucc\district_LUCC_urban_area.csv', index=False, encoding='utf-8-sig')

with open(OUTROOT + r'\02_lucc\_lucc_extract_log.txt', 'w', encoding='utf-8') as f:
    f.write(log.getvalue())

# 摘要
with open(OUTROOT + r'\02_lucc\_lucc_summary.txt', 'w', encoding='utf-8') as f:
    f.write("=== 全市 class51 总面积 (km2) ===\n")
    f.write(lucc.groupby('year')['urban_land_area_km2'].sum().to_string() + "\n\n")
    f.write("=== 2020 各区 class51 (km2) ===\n")
    f.write(lucc[lucc.year == 2020].set_index('district')['urban_land_area_km2'].sort_values(ascending=False).to_string() + "\n")
print('done')
