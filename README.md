# Beijing groundwater rebound and underground-space contact

Data and code for *Groundwater rebound and renewed contact with existing underground space in Beijing*.

Version v1.0.0, based on supplementary archive `NHR-R1-20261009`. Prepared 9 October 2026. Correspondence: Ming Wang, wangming@bnu.edu.cn.

The primary recovery window ends in December 2025. January to September 2026 is a separate descriptive extension; September contains observations only through 7 September.

## Quick start

```bash
git clone https://github.com/JosephBk0123/beijing-groundwater-underground-contact.git
cd beijing-groundwater-underground-contact
python -m pip install -r requirements.txt
python reproduce_core.py
python reproduce_revision.py
python plot_revision.py
```

Python 3.10 or later is required; the scripts were tested with Python 3.12.14. The core check uses only the standard library. NumPy and pandas are needed for the supplementary analyses, and Matplotlib for Figs. S11 to S13. The tested package versions are pinned in `requirements.txt`; `python -m pip install numpy pandas matplotlib` installs the same libraries without version pins.

The scripts resolve inputs relative to their own location and need no network access or third-party raw files. Leave assertions enabled: Python's `-O` option disables the checks.

## Reuse and citation

Code: [MIT](LICENSE). Authors' processed-data contributions and documentation: [CC BY 4.0](LICENSE-DATA). See [third-party source attribution and exclusions](THIRD_PARTY_NOTICES.md). Use [CITATION.cff](CITATION.cff) and the version tag when citing this release. No article DOI is assigned by this repository.

## Core verification

The core script recomputes the following from the supplied tables and writes `verification_result.json`:

- Monthly arithmetic means and observation counts from the 277-date v3 observation panel: 1,337 valid district-month cells, including the 2026 extension.
- Encounter fractions for 4,011 district-month-scenario records and encounter fractions and temporal indices for 630 historical district-year-scenario records.
- Complete-calendar contact runs and the December 2025 classes: nine newly persistent, three pre-existing, one transient-only and three without observed contact.
- Twenty-four first district-layer crossings: seven first runs confirmed for at least six months, twelve transient and five with insufficient follow-up. Missing months interrupt continuity; the script tests this rule.
- Depth classification for the 1,193 valid recovery-window district-months: 459 robust no-contact, 325 depth-sensitive and 409 robust-contact observations.
- Retention of 65 review-before-use flags among the 210 historical district-year records.

These checks cover the tabular calculations. Administrative-record processing, raster extraction, activation-reference selection, inferential p values and other figure exports are documented in the original scripts below and are outside this check.

## Files and units

| Directory or file | Contents and use |
|---|---|
| `inputs/groundwater_period_panel_v3.csv` | Observation-date panel, one district column per district, groundwater depth in metres below ground; smaller values mean a shallower water table. |
| `inputs/groundwater_monthly.csv` | Observation-average depth, count, range and support fields for each district-month. Empty depth cells are missing observations, not zero depth. |
| `inputs/groundwater_historical_direct10.csv` | Selected 2000–2020 district-year observations for ten districts, including source and quality fields. |
| `inputs/district_depth_profile_v2.csv` | Aggregated B1–B4 and B5+ area shares, sample sizes and represented underground area in m². The unresolved-district group is retained for auditing and excluded from sixteen-district analysis. |
| `inputs/acceptance_layer_decomposition_audit_v2.json` | Area field, units, floor decomposition, district assignment, duplicate removal and area-conservation audit. |
| `inputs/CNLUCC_district_class51.csv` | Class-51 urban-land counts and areas for eight epochs, raster resolution, projection and extraction method. |
| `inputs/depth_time_cube_MAIN.csv` and `depth_time_cube_RAW.csv` | Annual stock support, layer fractions and scenario depths. MAIN uses cumulative-maximum mapped urban area; RAW retains snapshot fluctuations. K is dimensionless, normalized to 2020. |
| `results/` | Historical and monthly encounter tables, class summaries, sensitivity tables, reported statistics and Table S1. C is a fraction from zero to one; manuscript encounter increases use percentage points. R_LEA is in percentage points per year. |
| `figure_tables/` | Frozen figure source tables, including intermediate tables and activation inputs. Original filenames are retained; use the mapping below for current NHR figure numbers. |
| `original_scripts/` | Original processing, digitization and plotting scripts; personal project-root paths are replaced with a local-workspace placeholder. |
| `provenance/` | Original report links, selected chart pages, calibration, source flags, cross-report comparisons, source-file hashes and the manuscript reference catalogue. |
| `validation/` | Release checks: `core.json` records the core calculations, `revision.json` the supplementary regressions, and `figures.json` the comparison with manuscript Figs. S11 to S13. |
| `file_manifest.csv` | SHA-256 and size of each distributed file except this manifest itself. |

The historical metadata includes selected observations and comparisons with other reports. The historical join uses the file ending in `_digitized.csv`; its 210-record analysis subset is `inputs/groundwater_historical_direct10.csv`. Similarly named files from other processing branches may contain different selections.

## Data sources and scope

1. Beijing Water Authority, [Beijing Water Resources Bulletins](https://swj.beijing.gov.cn/zwgk/szygb/). The digitization master and extract manifest record the original filenames, chart pages and selected series. Quality-flag categories can overlap.
2. Beijing Water Authority, [Beijing Plain Groundwater Dynamics](https://swj.beijing.gov.cn/zwgk/sjfb/dxsxx/). The supplied report-link index and v3 panel identify source support. Arithmetic within-month averaging gives each available report equal weight; reporting frequency is not uniform.
3. Beijing Water Authority, [Beijing Water Statistical Yearbook](https://swj.beijing.gov.cn/zwgk/swtjnj/). The 2025 volume, published in 2026, Table 1, pp. 1–2, supplied recent citywide checks.
4. Beijing Municipal Commission of Housing and Urban-Rural Development, Joint Acceptance Opinion Notification Attachments (data-cleaned dataset), [Beijing Public Data Open Platform](https://data.beijing.gov.cn/). The [2025 catalogue](https://data.beijing.gov.cn/docs/2025.pdf), item 384, identifies the provider and fields. The archived 10,000-record extract has acceptance identifiers dated 2023 to 2026. Its original download date is unavailable; a raw-file hash identifies the snapshot. The sixteen-district sample contains 3,215 asset records and 11,746,267 m²; 49 other layered asset records have unresolved districts. Acceptance dates do not establish construction dates.
5. X. Xu, [China's Multi-period Land Use Remote Sensing Monitoring Dataset (CNLUCC)](https://www.resdc.cn/DOI/DOI.aspx?DOIID=201), 2026 registration, DOI [10.12078/2026071401](https://doi.org/10.12078/2026071401). The analysis uses eight local 1 km inputs: 1980, 1990, 1995, 2000, 2005, 2010, 2015 and 2020. These are a subset of the epochs listed in the catalogue. The 1980 label denotes the late-1970s/1980 product epoch. The main proxy uses class 51 (urban land), excluding classes 52 and 53. Raster-cell centres determine district inclusion. The citation's 2026 registration date does not indicate when the archived inputs were downloaded or updated.

Source portals were consulted on 30 September 2026; original acquisition dates remain unspecified. The repository contains processed research tables. Raw CNLUCC grids, complete bulletin PDFs, individual project records and district-boundary coordinates must be obtained from their providers under the terms described in the third-party notices.

## Original processing chain

The scripts in `original_scripts/` document the original processing chain. They were not all rerun for this release and require external source files and path configuration. Original computer-root paths have been replaced with `local_raw_workspace`; scientific values are unchanged. Dependencies include NumPy, pandas, SciPy, GeoPandas, rasterio, Shapely and Matplotlib, plus the image/PDF tools listed in the digitization scripts. A complete version-locked environment for this chain was not archived.

| Stage | Original script |
|---|---|
| Chart extraction and digitization | `groundwater_digitization/extract_charts.py`, `digitize.py`, `build_outputs.py` |
| Period-to-month aggregation | `outputs/20260920_recovery_data_foundation_v1/taskA_panel.py` |
| CNLUCC district extraction | `historical_underground_space_backcast_v1/07_scripts/02_extract_lucc_by_district.py` |
| Historical stock backcast | `historical_underground_space_backcast_v11/07_scripts/v11_main.py` |
| Encounter calculations | `groundwater_underground_encounter_v2/09_scripts/v20_core.py` |
| Revised event and robustness tables | `Nature_results_freeze_v1/_scripts/stage2_revision.py` |
| Figure tables and original main/extended figures | `Nature_results_freeze_v1/_scripts/stage4a_sourcetables.py`, `stage4b_mainfigs_v2.py`, `stage4c_extdata.py` |
| Activation metrics, revised Fig. 4 and later supplements | `Nature_results_freeze_v1/_scripts/_fig5_compute.py`, `fig4_spatial_and_s7_s9.py` |

Paths in this table are relative to `original_scripts/`.

## Current figure mapping

| NHR figure | Source table filename or prefix in `figure_tables/` |
|---|---|
| Fig. 1 | `Fig1*` |
| Fig. 2 | `Fig2*` |
| Fig. 3 | `Fig3*` |
| Fig. 4 | `fig4_spatial_legacy_activation_source.csv` |
| Fig. S1 | `ED5_gw_qc.csv` |
| Fig. S2 | `ED6_depth_area_profiles.csv`; district totals in `results/Table_S1_district_sample.csv` |
| Fig. S3 | `ED2_main_raw.csv` |
| Fig. S4 | `ED1_selected_years.csv` |
| Fig. S5 | `ED3_small_multiples.csv` |
| Fig. S6 | `figS7_layer_timing_persistence_source.csv` |
| Fig. S7 | `figS8_robustness_summary_source.csv` |
| Figs. S8–S9 | `fig4_spatial_legacy_activation_source.csv`, `Fig5_metrics_by_district.csv` and `fig5_inputs/`; calculations in `fig4_spatial_and_s7_s9.py` |
| Fig. S10 | `ED4_robustness_2026ytd.csv`, `ED4_robustness_per_district.csv` |

Older figure identifiers in the scripts and some `Fig4*` and `Fig5*` tables refer to earlier layouts. The table above maps the archived filenames to the current manuscript figures.


## Supplementary analyses and figures

The revision script executes `reproduce_depth.py` and compares all computed CSV
outputs with the archived revision results. It checks the 192 district/duration
classes, recomputes the five-record assignment effect from aggregate layer areas,
and checks the citywide support weighting and the 81%/91% milestones. Results go
under `recomputed/`; `revision_verification.json` records the checks and library
versions. The plot script exports the current S11 to S13 filenames.

- `revision/depth/`: 27 configurations (three originals plus 24 case variants),
  140-grid results, monthly/annual fractions, transitions and duration classes.
- `revision/duration/`: original three-scenario duration results and the aggregate
  Daxing/Tongzhou assignment comparison.
- Figs. S11, S12 and S13 correspond to engineering cases, the depth grid and
  persistence duration, respectively. Files in `Figures/` supplied separately
  contain the final publication figures. Main Figs. 1–3 use the revised labels
  and legends, with their plotting code in `original_scripts/redraw_review_figures.py`.

E4 denotes 国家知识产权局专利局专利审查协作北京中心专利大厦（北京市丰台区汽车博物馆南路2号）.
Supplementary Note S3 documents the engineering heights and datum assumptions.

E1 and E4 appear in the same [2017 batch-five acceptance notice](https://zjw.beijing.gov.cn/bjjs/kjcxytg/jzyxjsyysfgc/ysgs/743807857/index.shtml), published on 5 January 2018. E4 is the first entry, “专利技术研发中心研发用房建设项目”; E1 is the second, “科研楼等3项（北京城建集团有限责任公司学院南路62号科研楼项目）”. Their B1/B2/B3 storey heights are 4.00/5.10/5.10 m and 5.75/4.00/4.00 m, respectively. The source names and entry numbers are recorded in `revision/depth/工程来源与转换假设.json`.

Historical audit JSON files retain the original runs' relative paths and hashes
for provenance; the scripts do not use them as runtime dependencies. The current
file manifest and verification JSON files describe this release.

## Interpretation limits

The analysis screens contact at district scale. Digitized chart readings retain
unresolved source-quality flags, and passing the calculation checks does not
validate their physical accuracy. The engineering cases provide geometry
references; they have not been matched to individual acceptance records or
independently checked for groundwater contact. No new independent well-level or
engineering-impact validation was performed.

Baseline profiles use the original administrative assignments. The five-record
comparison tests assignment sensitivity and does not establish project locations.
Standardized building/use classification was not completed. The six-month rule
describes contact duration; it has not been calibrated as a leakage or uplift threshold.
