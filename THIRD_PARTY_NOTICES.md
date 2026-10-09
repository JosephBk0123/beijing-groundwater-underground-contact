# Data sources and licence scope

The authors' Python code is licensed under the MIT License in `LICENSE`.
The authors' rights in processed research tables, derived results and original documentation are licensed under CC BY 4.0 in `LICENSE-DATA`.
These licences do not grant rights in third-party source products or override their providers' terms. Publicly available facts are not made subject to new exclusive rights by this repository.

## Source attribution

- Beijing Water Authority: [Water Resources Bulletins](https://swj.beijing.gov.cn/zwgk/szygb/), [Beijing Plain Groundwater Dynamics](https://swj.beijing.gov.cn/zwgk/sjfb/dxsxx/) and [Water Statistical Yearbooks](https://swj.beijing.gov.cn/zwgk/swtjnj/). The tables transcribe or aggregate reported observations; source links, pages and quality flags are retained in `provenance/`.
- Beijing Municipal Commission of Housing and Urban-Rural Development: joint-acceptance records from the [Beijing Public Data Open Platform](https://data.beijing.gov.cn/). Only aggregate research tables are distributed, not individual project records.
- X. Xu, [China's Multi-period Land Use Remote Sensing Monitoring Dataset (CNLUCC)](https://www.resdc.cn/DOI/DOI.aspx?DOIID=201), DOI [10.12078/2026071401](https://doi.org/10.12078/2026071401). Only district-level class-51 counts, areas and derived proxies are included. The original raster grids are not redistributed or relicensed.
- Engineering geometry references are identified in `revision/depth/工程来源与转换假设.json`; original notices and reports remain with their providers.

The public repository excludes complete source PDFs, raster grids, individual acceptance records and district-boundary coordinates. The boundary file `_beijing_district_rings.csv` was omitted because its redistribution licence was not established. The three commands in the quick start run without it; rebuilding the archived maps requires separately obtained boundaries and configuration of the historical plotting scripts.
