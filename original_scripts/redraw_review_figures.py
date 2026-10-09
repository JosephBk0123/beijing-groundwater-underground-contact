"""Redraw the review figures with revised labels and legends."""
from pathlib import Path
import hashlib, json, re, shutil, sys, os
from itertools import combinations

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FINAL_R25 = '--r25-final' in sys.argv
MIN_FONT = 8.0 if FINAL_R25 else 7.0
OUT = HERE.parent/('修改v1/R2.5_图件修订' if FINAL_R25 else '修改v1/图件修订v1')
SRC = OUT/'source_tables'
SRC.mkdir(parents=True, exist_ok=True)
sys.path.insert(0,str(HERE/'plot_dependencies'))
os.environ['MPLCONFIGDIR'] = str(HERE/'matplotlib_config')
import matplotlib
matplotlib.use('Agg')
from matplotlib.text import Text
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
import pandas as pd
import numpy as np

frozen = ROOT/'Nature_results_freeze_v1/03_figure_source_tables'
protected_paths = list(frozen.glob('*.csv')) + list((HERE.parent/'Figures').glob('Figure_[123].*'))
protected_paths += [HERE.parent/'01_NHR_Manuscript_reorganized_humanized.docx', HERE.parent/'01_NHR_Manuscript_reviewer_revision_working.docx']
protected = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected_paths}
for p in frozen.glob('*.csv'):
    shutil.copy2(p,SRC/p.name)

code = (ROOT/'Nature_results_freeze_v1/_scripts/stage4b_mainfigs_v2.py').read_text(encoding='utf-8')
code = code.split('# ================= Fig 4 (synthesis: persistence, robustness, mismatch)')[0]
code = code.replace('SRC = os.path.join(FRZ, "03_figure_source_tables")', f'SRC = {str(SRC)!r}')
code = code.replace('FIG = os.path.join(FRZ, "04_main_figures")', f'FIG = {str(OUT)!r}')
code = re.sub(r'def save_all\(fig, name\):.*?(?=\ndef panel_label)',
              'def save_all(fig, name):\n    review_save(fig, name)\n',code,flags=re.S)
code = code.replace('alpha=0.20, zorder=1','alpha=0.55, zorder=1')
code = code.replace('color=dc[d], lw=1.5, alpha=0.55',
                    'color=dc[d], ls=["-", "--", "-.", ":"][DIST16_CN.index(d)%4], lw=1.2, alpha=0.55')
code = code.replace('figsize=(180 * MM, 150 * MM)', 'figsize=(180 * MM, 205 * MM)',1)
code = code.replace('bottom=0.055, hspace=0.34, wspace=0.24','bottom=0.19, hspace=0.36, wspace=0.24',1)
code = code.replace('figsize=(180 * MM, 150 * MM)', 'figsize=(180 * MM, 180 * MM)')
code = code.replace('figsize=(180 * MM, 165 * MM)', 'figsize=(180 * MM, 195 * MM)')
records = []

def review_save(fig,name):
    global ns
    # Revised HD/CY/SJ/FT positions; DC/XC unchanged and leader lines disabled.
    offsets = {'DC':(5.5,0),'XC':(-3.5,0),'SJ':(-4,0),'HD':(1,1),'FT':(-2,0),'CY':(5,4)}
    districts = {'DC':'东城区','XC':'西城区','SJ':'石景山区','HD':'海淀区','FT':'丰台区','CY':'朝阳区'}
    for ax in fig.axes:
        if ax.patches and not ax.get_xticks().size:
            for label in list(ax.texts):
                if label.get_text() in offsets:
                    text=label.get_text()
                    ring=ns['rings'][(ns['rings'].district==districts[text]) & (ns['rings'].ring==0)]
                    ring=ring[ring.part==ring.groupby('part').size().idxmax()]
                    xy=(ring.x.mean(),ring.y.mean());label.remove()
                    ax.annotate(text,xy=xy,xytext=offsets[text],textcoords='offset points',
                                ha='center',va='center',fontsize=8.5 if FINAL_R25 else 7.5,zorder=8,
                                path_effects=[pe.withStroke(linewidth=1.3,foreground='white')])
        elif ax.get_xticks().size:
            for label in ax.texts:
                if label.get_text() in ['HD','HR','FS','TZ','DX','MY']:
                    label.set_position((.03,1.025));label.set_va('bottom')
    for text in fig.findobj(Text):
        if text.get_text():
            text.set_fontsize(max(MIN_FONT,text.get_fontsize()))
            if text.get_text() in ['a','b','c','d']:text.set_fontsize(10)
    if name.startswith('Fig1'):
        codes=['DC','XC','CY','HD','FT','SJ','MT','FS','TZ','SY','CP','DX','HR','PG','MY','YQ']
        handles=[Line2D([],[],color=ns['dc'][d],ls=['-','--','-.',':'][i%4],lw=1.5,
                       label=(codes[i]+' '+ns['EN'][d]) if FINAL_R25 else ns['EN'][d])
                 for i,d in enumerate(ns['DIST16_CN'])]
        fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.008),ncol=4,
                   frameon=False,fontsize=MIN_FONT,handlelength=2.4,columnspacing=1.0,labelspacing=.6,
                   title='District background curves in a and b',title_fontsize=7.5)
        fig.text(.06,.165 if FINAL_R25 else .150,('c periods: peripheral ten districts 2000–2025; CY/HD/FT/SJ 2019–2025;' if FINAL_R25
                          else 'c: peripheral districts 2000–2025; four core districts 2019–2025;'),fontsize=7)
        fig.text(.06,.150 if FINAL_R25 else .135,('DC/XC 2020–2025. Ranges use each district’s available series.' if FINAL_R25
                          else 'Dongcheng / Xicheng 2020–2025. Coverage differs across districts.'),fontsize=7)
        fig.text(.06,.135 if FINAL_R25 else .119,'Heavy blue curves: citywide series. Thin coloured curves: district series.',fontsize=7)
        for ax in fig.axes:
            if ax.get_ylabel().startswith('$D_'):ax.set_ylabel('Groundwater depth range (m)' if FINAL_R25 else 'Groundwater range (m)',fontsize=7.5)
            if 'S_{' in ax.get_ylabel():ax.set_ylabel('2020 class-51 support / district area\n(dimensionless; cumulative maximum)' if FINAL_R25 else '2020 land-use proxy / district area\n(dimensionless)',fontsize=7.5)
    if name.startswith('Fig3'):
        fig.text(.5,.415,'Map and heatmap share the encounter-fraction scale (0–1).',
                 fontsize=7,ha='center')
    fig.canvas.draw()
    nonempty=[t for t in fig.findobj(Text) if t.get_text()]
    for text in nonempty:
        text.set_fontsize(max(MIN_FONT,text.get_fontsize()))
    assert min(t.get_fontsize() for t in nonempty)>=MIN_FONT
    # Check the six label positions and disabled leader lines across all map panels.
    fig.canvas.draw()
    for ax in fig.axes:
        if ax.patches and not ax.get_xticks().size:
            core={t.get_text():t for t in ax.texts if t.get_text() in offsets}
            assert all(t.arrow_patch is None for t in core.values())
            boxes={k:Text.get_window_extent(t,fig.canvas.get_renderer()) for k,t in core.items()}
            for a,b in combinations(boxes,2):
                assert not boxes[a].overlaps(boxes[b]), (name,a,b)
    number={'Fig1_legacy_context':1,'Fig2_historical_reemergence':2,'Fig3_threshold_activation':3}[name]
    for ext in ['svg','pdf','png']:
        filename=f'Figure_{number}_R2_5.{ext}' if FINAL_R25 else f'Figure_{number}_review_v1.{ext}'
        fig.savefig(OUT/filename,dpi=600 if ext=='png' else None,
                    bbox_inches='tight',facecolor='white')
    records.append({'figure':number,'min_font_pt':min(t.get_fontsize() for t in nonempty),
                    'width_mm':round(fig.get_figwidth()*25.4,1),'height_mm':round(fig.get_figheight()*25.4,1),
                    'text_count':len(nonempty)})
    ns['plt'].close(fig)

ns={'__name__':'__main__','review_save':review_save}
exec(compile(code,'frozen_figure_code_redirected','exec'),ns)
assert len(records)==3
# Check scientific values against the frozen tables after reusing the plotting code.
for filename,cols in [('Fig1b_stock_proxy.csv',['stock_sum_km2']),
                      ('Fig1c_gw_delta_map.csv',['gw_level_delta_m']),
                      ('Fig1d_stock_ratio_map.csv',['stock_area_km2_2020','surface_area_km2']),
                      ('Fig2b_historical_heatmap.csv',None),('Fig3a_recovery_heatmap.csv',None)]:
    left=pd.read_csv(frozen/filename);right=pd.read_csv(SRC/filename)
    pd.testing.assert_frame_equal(left[cols] if cols else left,right[cols] if cols else right)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in protected.items())
(HERE/('R2_5_figure_audit_20261008.json' if FINAL_R25 else 'figure_readability_audit_20261008.json')).write_text(json.dumps({
    'output_dir':str(OUT),'figures':records,'original_files_unchanged':True,
    'scientific_table_comparison':'passed','protected_sha256':protected,
    'scope':'Typography and annotations using current frozen data; economic-zone reassignment pending',
    'central_label_offsets_points':{'DC':[5.5,0],'XC':[-3.5,0],'SJ':[-4,0],'HD':[1,1],'FT':[-2,0],'CY':[5,4]},
    'label_reference':str(OUT/'Figure_1_R2_5_modify2.png'),
    'label_overlap_check':'passed: all six core labels in every map panel; no label-to-centre leaders',
},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(records))
