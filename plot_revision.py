"""Plot supplementary depth and duration sensitivity results."""
from pathlib import Path
import hashlib
import json
import os
import sys

HERE = Path(__file__).resolve().parent
PACKAGE = HERE
OUT = PACKAGE / 'recomputed/figures'
OUT.mkdir(parents=True,exist_ok=True)
SOURCE = OUT / 'source_tables'
SOURCE.mkdir(exist_ok=True)
os.environ['MPLCONFIGDIR'] = str(HERE / 'matplotlib_config')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
from matplotlib.text import Text
import numpy as np
import pandas as pd

DEPTH = PACKAGE / 'revision/depth'
DURATION = PACKAGE / 'revision/duration'
paths = {
    'config': DEPTH / '全部27组深度配置.csv',
    'summary': DEPTH / '配置影响汇总.csv',
    'district': DEPTH / '逐区接触时间与持续分类.csv',
    'grid': DEPTH / '扩展140组参数网格.csv',
    'duration': DURATION / 'duration_by_district_192.csv',
    'duration_counts': DURATION / 'duration_summary_12.csv',
}
protected = list(paths.values())
hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
data = {k: pd.read_csv(p).fillna('') for k, p in paths.items()}
config = data['config'].set_index('config_id')
summary = data['summary'].set_index('config_id')
district = data['district']
grid = data['grid']
duration = data['duration']
counts = data['duration_counts']

EN = {
    '东城区': 'Dongcheng', '西城区': 'Xicheng', '朝阳区': 'Chaoyang',
    '海淀区': 'Haidian', '丰台区': 'Fengtai', '石景山区': 'Shijingshan',
    '门头沟区': 'Mentougou', '房山区': 'Fangshan', '通州区': 'Tongzhou',
    '顺义区': 'Shunyi', '昌平区': 'Changping', '大兴区': 'Daxing',
    '怀柔区': 'Huairou', '平谷区': 'Pinggu', '密云区': 'Miyun', '延庆区': 'Yanqing',
}
DISTRICTS = list(EN)
STATES = ['new_persistent_activation', 'pre_existing_contact',
          'transient_only_contact', 'no_observed_contact', 'other_observed_contact']
LABELS = ['New persistent', 'Pre-existing', 'Transient only', 'No observed contact', 'Other observed contact']
COLORS = ['#238B80', '#8876AC', '#E6B458', '#E8EDF1', '#7895AE']
STATE_MAP = dict(zip(STATES, range(5)))
CMAP = ListedColormap(COLORS)
NORM = BoundaryNorm(np.arange(-.5, 5, 1), 5)
MM = 1 / 25.4
plt.rcParams.update({
    'font.family': 'Arial', 'font.size': 8.5,
    'axes.labelsize': 8.5, 'axes.titlesize': 9.5, 'xtick.labelsize': 8,
    'ytick.labelsize': 8.3, 'legend.fontsize': 8.3,
    'axes.linewidth': .6, 'pdf.fonttype': 42, 'ps.fonttype': 42,
    'svg.fonttype': 'none', 'savefig.facecolor': 'white',
})
records = []


def title(ax, text):
    ax.set_title(text, loc='left', fontweight='bold', pad=11)


def category_legend(fig, y):
    fig.legend([Patch(facecolor=c, edgecolor='#ccd1d5', linewidth=.4) for c in COLORS], LABELS,
               loc='lower center', bbox_to_anchor=(.54, y), ncol=3, frameon=False,
               handlelength=1.3, columnspacing=1.1, labelspacing=.7)


def category_matrix(ax, values, columns, names=True):
    ax.imshow(values, cmap=CMAP, norm=NORM, aspect='auto', interpolation='nearest')
    ax.set_xticks(range(len(columns)), columns)
    ax.set_yticks(range(len(DISTRICTS)), [EN[d] for d in DISTRICTS] if names else [])
    ax.set_xticks(np.arange(-.5, len(columns), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(DISTRICTS), 1), minor=True)
    ax.grid(which='minor', color='white', linewidth=.55)
    ax.tick_params(which='both', length=0, pad=4)
    for spine in ax.spines.values():
        spine.set_color('#bac4cd')


def save(fig, stem):
    fig.canvas.draw()
    texts = [t for t in fig.findobj(Text) if t.get_text() and t.get_visible()]
    assert min(t.get_fontsize() for t in texts) >= 8
    # Check labels stay inside the fixed-size canvas before exporting.
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    for t in texts:
        box = t.get_window_extent(renderer)
        if box.width > 0 and box.height > 0:
            assert box.x0 >= -1 and box.y0 >= -1 and box.x1 <= bounds.x1 + 1 and box.y1 <= bounds.y1 + 1, (stem, t.get_text(), tuple(box.bounds))
    for ext in ['pdf', 'svg', 'png']:
        fig.savefig(OUT / f'{stem}.{ext}', dpi=600 if ext == 'png' else None)
    fig.savefig(OUT / f'{stem}_preview.png', dpi=180)
    records.append({'file_stem': stem, 'width_mm': fig.get_figwidth() * 25.4,
                    'height_mm': fig.get_figheight() * 25.4, 'min_font_pt': min(t.get_fontsize() for t in texts)})
    plt.close(fig)


# Check plotted classifications and summaries against the source tables.
assert len(config) == 27 and len(grid) == 140 and len(duration) == 192
assert not grid.duplicated(['first_depth_m', 'increment_m']).any()
q6 = district[district.duration_months == 6]
assert not q6.duplicated(['config_id', 'district']).any()
assert set(q6.category).issubset(STATES)
for cid, rows in q6.groupby('config_id'):
    assert len(rows) == 16
    assert int((rows.category == STATES[0]).sum()) == summary.loc[cid, 'new_persistent_count']
for _, row in counts.iterrows():
    selected = duration[(duration.scenario == row.scenario) & (duration.duration_months == row.duration_months)]
    assert len(selected) == 16
    assert int((selected.category == STATES[0]).sum()) == row.new_persistent_count
assert list(summary.loc[summary.index.str.startswith('E'), 'new_persistent_count'].agg(['min', 'max'])) == [7, 9]
assert list(grid.new_persistent_count.agg(['min', 'max'])) == [7, 10]
assert grid.max_abs_paired_first_new_shift_months.max() == 55

# Figure 1: 24 conditional engineering configurations, identity of districts, and effect sizes.
ordered = ['central']
for case in ['E1', 'E2', 'E3', 'E4']:
    for tail in ['extend', 'central_tail']:
        ordered.extend(f'{case}_{offset}_{tail}' for offset in ['m03', 'zero', 'p03'])
class_frame = q6.pivot(index='district', columns='config_id', values='category').reindex(index=DISTRICTS, columns=ordered)
assert class_frame.notna().all().all()
common = list(class_frame.index[(class_frame.iloc[:, 1:] == STATES[0]).all(axis=1)])
assert set(common) == {'东城区', '西城区', '丰台区', '海淀区', '昌平区', '怀柔区'}
fig = plt.figure(figsize=(180 * MM, 220 * MM))
fig.text(.16, .974, 'Engineering-informed depth sensitivity', fontsize=11, fontweight='bold')
ax = fig.add_axes([.16, .46, .82, .405])
labels = ['C'] + ['−.3', '0', '+.3'] * 8
category_matrix(ax, class_frame.replace(STATE_MAP).to_numpy(dtype=int), labels)
ax.tick_params(axis='x', labelrotation=90)
for tick, d in zip(ax.get_yticklabels(), DISTRICTS):
    tick.set_fontweight('bold' if d in common else 'normal')
ax.text(-.18, 1.17, 'a', transform=ax.transAxes, fontsize=10, fontweight='bold')
for i, case in enumerate(['E1', 'E2', 'E3', 'E4']):
    center = 3.5 + i * 6
    ax.text(center, 1.135, case, transform=ax.get_xaxis_transform(), ha='center', fontsize=9, fontweight='bold')
    ax.text(center - 1.5, 1.045, 'Extend', transform=ax.get_xaxis_transform(), ha='center', fontsize=8)
    ax.text(center + 1.5, 1.045, 'Retain', transform=ax.get_xaxis_transform(), ha='center', fontsize=8)
    ax.axvline(.5 + i * 6, color='#52616e', lw=.8)
    ax.axvline(3.5 + i * 6, color='#52616e', lw=.5, ls=':')
ax.set_xlabel('C: central baseline. Other columns: datum offset δ (m).', labelpad=6)
category_legend(fig, .365)
fig.text(.16, .355, 'Bold district names: new persistent contact in all 24 case configurations.', fontsize=8)
tail_styles = [('extend', '#236A97', -.12, 'Extend last increment'),
               ('central_tail', '#B56232', .12, 'Retain central for absent floors')]
for pos, metric, label, lim, letter in [
    ([.16, .135, .34, .16], 'mean_absolute_encounter_change_pp', 'Mean |ΔC| (percentage points)', (-.1, 4.4), 'b'),
    ([.64, .135, .34, .16], 'max_abs_paired_first_new_shift_months', 'Maximum paired |Δt| (months)', (-.5, 24), 'c'),
]:
    ax = fig.add_axes(pos)
    for j, case in enumerate(['E1', 'E2', 'E3', 'E4']):
        for tail, color, offset, _ in tail_styles:
            ids = [f'{case}_{x}_{tail}' for x in ['m03', 'zero', 'p03']]
            vals = summary.loc[ids, metric].to_numpy(dtype=float)
            ax.plot([vals.min(), vals.max()], [j + offset] * 2, color=color, lw=1.3)
            ax.scatter(vals, np.repeat(j + offset, 3), s=19, color=color, edgecolor='white', linewidth=.3, zorder=3)
    ax.set_yticks(range(4), ['E1', 'E2', 'E3', 'E4'])
    ax.set_ylim(3.5, -.5)
    ax.set_xlim(*lim)
    if letter == 'c': ax.set_xticks([0, 6, 12, 18, 24])
    ax.set_xlabel(label)
    title(ax, f'{letter}  ' + ('Encounter-fraction change' if letter == 'b' else 'First-crossing time change'))
    ax.grid(axis='x', color='#E5E9ED', lw=.6)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
fig.legend([Line2D([], [], color=c, marker='o', markersize=4) for _, c, _, _ in tail_styles],
           [s[3] for s in tail_styles], loc='lower center', bbox_to_anchor=(.55, .066), ncol=2, frameon=False)
fig.text(.04, .044, 'Dots: three datum offsets. Segments show their ranges, not confidence intervals.', fontsize=8)
fig.text(.04, .021, 'Largest single district-month |ΔC|: 81.73 percentage points (Yanqing).', fontsize=8)
save(fig, 'Figure_S11')

# Figure 2: complete a-by-h grid. Every cell is one computed configuration.
fig = plt.figure(figsize=(180 * MM, 190 * MM))
fig.text(.115, .973, 'Sensitivity across 140 depth configurations', fontsize=11, fontweight='bold')
metrics = [
    ('new_persistent_count', 'a  New persistent districts', 'YlGnBu', 7, 10, [7, 8, 9, 10], 'Districts'),
    ('mean_absolute_encounter_change_pp', 'b  Mean encounter-fraction\n    difference from central', 'YlOrRd', 0, 7, [0, 2, 4, 6], 'pp'),
    ('max_abs_paired_first_new_shift_months', 'c  Maximum paired\n    first-crossing time shift', 'magma_r', 0, 55, [0, 15, 30, 45, 55], 'Months'),
    ('six_month_class_changed_n', 'd  Districts changing\n    persistence class', 'PuBuGn', 0, 8, [0, 2, 4, 6, 8], 'Districts'),
]
for i, (metric, heading, cmap, vmin, vmax, ticks, unit) in enumerate(metrics):
    left = .115 if i % 2 == 0 else .62
    bottom = .58 if i < 2 else .16
    ax = fig.add_axes([left, bottom, .285, .28])
    tab = grid.pivot(index='first_depth_m', columns='increment_m', values=metric).sort_index().sort_index(axis=1)
    assert tab.shape == (14, 10) and not tab.isna().any().any()
    xs = np.r_[tab.columns.to_numpy() - .125, tab.columns.max() + .125]
    ys = np.r_[tab.index.to_numpy() - .125, tab.index.max() + .125]
    if i in [0, 3]:
        cm = plt.get_cmap(cmap, vmax - vmin + 1)
        norm = BoundaryNorm(np.arange(vmin - .5, vmax + 1.5), vmax - vmin + 1)
        mesh = ax.pcolormesh(xs, ys, tab.to_numpy(), cmap=cm, norm=norm, edgecolors='white', linewidth=.25)
    else:
        mesh = ax.pcolormesh(xs, ys, tab.to_numpy(), cmap=cmap, vmin=vmin, vmax=vmax, edgecolors='white', linewidth=.25)
    ax.add_patch(Rectangle((3.875, 4.875), .25, .25, fill=False, edgecolor='black', linewidth=1.4, zorder=4))
    ax.set_xticks([3.25, 4, 4.75, 5.5], ['3.25', '4.00', '4.75', '5.50'])
    ax.set_yticks([3, 4, 5, 6])
    ax.set_xlabel('Layer increment h (m)')
    ax.set_ylabel('B1 nominal depth a (m)')
    title(ax, heading)
    cbax = fig.add_axes([left + .302, bottom, .017, .28])
    cb = fig.colorbar(mesh, cax=cbax, ticks=ticks)
    cb.ax.set_title(unit, fontsize=8, pad=6)
    cb.ax.tick_params(labelsize=8, width=.5, length=2)
    if i == 0:
        for a in tab.index:
            for h in tab.columns:
                value = int(tab.loc[a, h])
                ax.text(h, a, str(value), ha='center', va='center', fontsize=8, color='white' if value >= 9 else '#183C51')
fig.text(.115, .087, 'Depth at level l: a + (l − 1)h. Six-month criterion; endpoint: December 2025.', fontsize=8)
fig.text(.115, .06, 'Outlined cell: central (a = 5 m, h = 4 m). All differences are relative to central.', fontsize=8)
fig.text(.115, .033, 'Timing shifts use paired observed crossings; absent crossings are not assigned a zero shift.', fontsize=8)
save(fig, 'Figure_S12')

# Figure 3: duration choice, including identities and all five classification states.
fig = plt.figure(figsize=(180 * MM, 190 * MM))
fig.text(.16, .974, 'Sensitivity to the persistence-duration criterion', fontsize=11, fontweight='bold')
ax = fig.add_axes([.16, .735, .79, .16])
scenario_styles = [('shallow', '#2775A5', 'v', '--'), ('central', '#252525', 'o', '-'), ('deep', '#B56A37', 's', '-.')]
for scenario, color, marker, ls in scenario_styles:
    rows = counts[counts.scenario == scenario].sort_values('duration_months')
    ax.plot(rows.duration_months, rows.new_persistent_count, color=color, ls=ls, marker=marker,
            markersize=6 if scenario == 'deep' else 4.2, markerfacecolor='none' if scenario == 'deep' else color,
            markeredgewidth=1.1, lw=1.3, label=scenario.capitalize())
for q in [3, 6, 9, 12]:
    for value in sorted(set(counts.loc[counts.duration_months == q, 'new_persistent_count'])):
        ax.annotate(str(value), (q, value), xytext=(0, 7), textcoords='offset points', ha='center', fontsize=8)
ax.set_xlim(2.7, 12.4)
ax.set_ylim(6, 12)
ax.set_xticks([3, 6, 9, 12])
ax.set_yticks([6, 8, 10, 12])
ax.set_xlabel('Required continuous contact (months)')
ax.set_ylabel('New persistent districts')
ax.grid(axis='y', color='#E2E8ED', lw=.6)
ax.spines[['top', 'right']].set_visible(False)
title(ax, 'a  Number of districts')
ax.legend(loc='upper right', ncol=3, frameon=False, bbox_to_anchor=(1, 1.29))
fig.text(.16, .653, 'Central: 3 and 6 months give the same nine districts; 9 and 12 months give eight and seven.', fontsize=8)
for i, (scenario, _, _, _) in enumerate(scenario_styles):
    ax = fig.add_axes([.16 + i * .28, .155, .23, .405])
    tab = duration[duration.scenario == scenario].pivot(index='district', columns='duration_months', values='category').reindex(DISTRICTS)
    assert list(tab.columns) == [3, 6, 9, 12]
    values = tab.replace(STATE_MAP).to_numpy(dtype=int)
    category_matrix(ax, values, ['3', '6', '9', '12'], names=i == 0)
    ax.set_xlabel('Months')
    title(ax, f'{chr(98 + i)}  {scenario.capitalize()}')
    if scenario == 'central':
        assert tab.loc['石景山区', 6] == STATES[0] and tab.loc['石景山区', 9] == STATES[4]
        assert tab.loc['门头沟区', 9] == STATES[0] and tab.loc['门头沟区', 12] == STATES[4]
category_legend(fig, .055)
fig.text(.04, .018, 'Classification at December 2025; initial contact has priority and missing months interrupt runs.', fontsize=8)
save(fig, 'Figure_S13')

# Export the exact tables and a stable project-identity key used by these figures.
display_names = {'E1': '学院南路62号科研楼', 'E2': '凯恒中心', 'E3': '金方大厦',
                 'E4': '国家知识产权局专利局专利审查协作北京中心专利大厦（北京市丰台区汽车博物馆南路2号）'}
for key, frame in data.items():
    table = frame.copy()
    if key == 'config':
        table['project_display_name'] = table.case_id.map(display_names).fillna('')
    table.to_csv(SOURCE / f'{key}.csv', index=False, encoding='utf-8-sig')
class_frame.to_csv(SOURCE / 'engineering_classification_matrix.csv', encoding='utf-8-sig')

captions = '''敏感性分析图件说明（2026年10月9日）

文件用途与阅读顺序
图1回答工程案例配置是否改变具体地区、接触比例及转换时间；图2展示完整的140组参数网格；图3比较持续时间判据。PDF和SVG为矢量文件，PNG为600 dpi，preview.png用于快速查看。图件宽度均为180 mm，最小字号8 pt；插入论文时建议按双栏宽度使用。图号为工作编号，合并稿件时再确定正式补充图编号。

工程代码及名称
E1：学院南路62号科研楼。
E2：凯恒中心。
E3：金方大厦。
E4：国家知识产权局专利局专利审查协作北京中心专利大厦（北京市丰台区汽车博物馆南路2号）。住建委原始公示名称为“专利技术研发中心研发用房建设项目”。代码E4沿用原计算标识。

图1 中文说明
a为16区在central基准及24组工程条件配置下的持续接触分类。24组来自4个案例、3种地面参照偏移δ（−0.30、0、+0.30 m）及2种资料未覆盖层的处理：Extend按最后一个已知层高延续；Retain保留原central阈值。δ为名义首层起算面高于室外地面的有符号高差；这些扰动不是测量置信区间。表内加粗区名表示全部24组工程配置均保持新持续接触分类。b为相对central的接触比例平均绝对差，按1,193个有效区—月等权计算，单位为百分点；不是按面积加权的全市差值。c为双方均识别出无接触到接触转换时，逐区配对月份差的最大绝对值。每条线连接同一案例、同一补齐方式下3个δ值的范围，不是置信区间。无可配对转换的记录不填零。a采用截至2025年12月的终点分类及6个月判据。B5+面积权重为零。
结果：新持续接触区数为7—9；东城、西城、丰台、海淀、昌平、怀柔在全部24组中保持该类。b的均差范围为0.88—4.00个百分点，c最大为22个月。最大单个区—月差值为延庆的81.73个百分点，来自B1阈值跨越时大面积层级一次性计入，不能用平均差值代表所有地区。来源不提供的楼层外推不能称为工程实测。

Fig. S11. Sensitivity to engineering-informed depth configurations.
(a) District contact classes under the central baseline (C) and 24 configurations formed from four documented projects, three datum offsets and two rules for floors absent from the project records. Extend continues the last documented storey increment; Retain keeps the central threshold at undocumented levels. The signed offset δ is the elevation of the assumed first-floor datum relative to outdoor ground. Bold district names identify newly persistent contact in all 24 configurations. (b) Mean absolute differences in encounter fraction relative to central, with equal weight for 1,193 valid district-months. (c) Maximum absolute district-level difference in the first observed non-contact-to-contact transition month, restricted to paired observed transitions. Re-entry after contact at the beginning of a record can qualify as an observed transition. Points show the three offsets; segments indicate their range, not confidence intervals. Missing transition pairs are not assigned zero differences. Classes use a six-month terminal-run criterion at December 2025, with pre-existing contact taking priority. The largest individual district-month encounter-fraction difference is 81.73 percentage points in Yanqing. Configurations with undocumented levels extended are conditional scenarios, not site measurements.

图2 中文说明
每格是一组实际计算，a为地下首层（B1）名义深度3.00—6.25 m，h为后续层间增量3.25—5.50 m，步长均为0.25 m；第l层深度为a+(l−1)h，共140组。黑色框线标出central（a=5、h=4）。面板a为新持续接触区数（7—10），b为相对central的接触比例平均绝对差（0—6.8233个百分点），c为可配对首次转换时间的最大绝对偏移（0—55个月），d为相对central改变持续接触类别的区数（0—8）。三个差异指标相对central，不应与原浅、深情景之间27.2%的二元状态差异混淆。相同总区数可能对应不同区名单或类别。该网格是设计的参数扫描，不代表经验分布或概率。

Fig. S12. Sensitivity across 140 depth configurations.
The nominal B1 depth a ranges from 3.00 to 6.25 m and the subsequent increment h from 3.25 to 5.50 m, both in 0.25-m steps. Level l has depth a+(l−1)h. Each cell is a computed configuration; the outlined cell marks central (a=5 m, h=4 m). Panels show (a) the number of newly persistent districts, (b) the mean absolute encounter-fraction difference over 1,193 valid district-months, (c) the maximum absolute shift in paired first observed transition months, and (d) the number of districts changing persistence class. All differences use central as the reference. Classes use the six-month criterion at December 2025. Panel (c) excludes unpaired transitions; changes in whether a transition is observed are retained in the source table. The grid is a parameter scan, not an empirical probability distribution. Equal district counts do not imply equal membership, encounter fractions or timing.

图3 中文说明
a比较浅、中、深三组原始深度配置在3、6、9、12个月连续接触要求下的新持续接触区数；b—d分别列出三组深度配置的16区完整类别。central的3个月与6个月名单完全相同；9个月时石景山不再满足终点新持续接触要求，12个月时门头沟也不再满足。深层配置从3个月的11区变为6个月的9区，说明central的3／6个月一致不能推广到所有深度配置。连续段被缺测打断；已有接触优先单列。Other observed contact包括终点仍接触但连续长度不足所设月数、或历史上出现持续段而终点未持续的情形。六个月是描述性半年窗口，没有据此校准为渗漏、抗浮或运行中断的临界时长。

Fig. S13. Sensitivity to the persistence-duration criterion.
(a) Number of newly persistent districts under 3-, 6-, 9- and 12-month terminal-run criteria. (b–d) District classes for the shallow, central and deep depth configurations. All classes refer to December 2025. Missing observations interrupt runs, and contact at the start of the available record is classified as pre-existing. Other observed contact includes terminal contact shorter than the selected criterion and earlier sustained episodes without persistence at the endpoint. Under central, the three- and six-month criteria identify the same nine districts; Shijingshan leaves the newly persistent class at nine months and Mentougou at twelve months. These classifications describe geometric contact, not observed engineering damage.

复核与重现
source_tables保存绘图使用的数值与分类。绘图脚本为outputs/NHR_revision_v2_20260930/_work/plot_sensitivity_figures.py，使用现有本地Python及绘图依赖。脚本包含逐区分类计数与汇总表一致性检查，并核对原始分析文件及正文的SHA-256不变。文件audit.json记录输入哈希、尺寸、字号与检查结果。
'''
(OUT / '图件说明与中英文图注.txt').write_text(captions, encoding='utf-8-sig')
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in hashes.items())
audit = {'date': '2026-10-09', 'figures': records, 'input_sha256': hashes,
         'source_checks': 'passed: 27 six-month class counts; 12 duration counts; full grid and classification dimensions; stable six districts',
         'scientific_inputs_and_manuscripts_unchanged': True,
         'figure1_configuration_count': 24, 'figure2_configuration_count': 140,
         'common_persistent_districts_case24': common,
         'case_max_paired_shift_months': 22, 'grid_max_paired_shift_months': 55,
         'reproduction_script': str(Path(__file__).resolve()), 'visual_qa': 'pending'}
(OUT / 'audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(records, ensure_ascii=False))
