# Urban form and neighbourhood vitality in Madrid

Code and data for the master's thesis *Urban Form and Neighbourhood Vitality in Madrid*
(QuEA 2025–26). The thesis text is not included here while it is unpublished; it will be added
after the defence.

**Part I** classifies Madrid's urban fabric as *spontaneous* or *planned* on an H3 resolution-9
grid, using two independent instruments: an unsupervised theoretical index and a supervised
Random Forest trained on 733 hand-labelled hexagons. **Part II** builds a six-dimension vitality
index and estimates the effect of morphology on vitality by OLS and Mahalanobis matching. No
variable used to classify morphology enters the vitality index or its controls.

## Results

| | Value | Source |
|---|---|---|
| Random Forest F1-macro (5-fold CV, 42 variables) | **0.847 ± 0.021** | `05` |
| Held out by neighbourhood / by 1 km block | 0.826 / **0.822** | `reconstruct.py` |
| AUC of the unsupervised index | 0.772 | `05` |
| Agreement between the two instruments | 80 % | `05` |
| Effect on vitality — OLS with controls | **+9.8 %** (p < 0.0001) | `09` |
| Effect on vitality — matched | **+6.0 %** (p = 0.0005, 144 pairs) | `09` |
| Commercial block — matched | +4.4 % (p = 0.036) | `09` |
| Demographic block — matched | +8.1 % (p = 0.003) | `09` |
| Same test, unsupervised index — matched | −3.5 % (p = 0.020, 188 pairs) | `09` |

The last row is a robustness check, not a co-equal result. The unsupervised index recovers only
72 of the 209 anchored spontaneous cells and reaches AUC 0.772 against the classifier's
cross-validated AUC of 0.948, so its treated class is a small and non-random subset of the fabric
it is meant to identify, and measurement error of that size leaves its causal estimate close to
uninterpretable. Its OLS counterpart, −1.8 %, is not significant. The thesis reports the negative
estimate as a bound on what the evidence carries, not as an alternative answer.

## Quick check

```bash
pip install -r requirements.txt
```

```bash
python verify.py
```

Recomputes the published figures from `data/` in ~30 s. No downloads, no path editing.

```bash
python reconstruct.py
```

Rebuilds the four steps whose original code was lost and checks them against the published
figures — 27 checks, ~3 min. See [Lost steps](#lost-steps).

## Execution order

Absolute paths are hard-coded in every notebook; see [`docs/PATHS.md`](docs/PATHS.md) for the one
line to edit in each. Heavy inputs are not in the repository; see
[`data/raw/SOURCES.md`](data/raw/SOURCES.md). Thanks to `data/processed/`, steps 04, 05 and 09 —
which produce every figure above — run without downloading anything.

### Part I — classification

| # | File | Reads | Writes |
|---|---|---|---|
| 01 | `01_morphology_network_cadastre.ipynb` | OSM via OSMnx (`network_type='walk'`), cadastre | `madrid_morfologia_h3_v10.gpkg` |
| 02 | `02_geometric_metrics_block_d.ipynb` | step 01, OSM (`network_type='all'`) | `madrid_morfologia_h3_metricas_geometricas_v2.gpkg` |
| 03 | `03_blocks_from_footprints.py` | step 01, cadastre | `bloques_huellas.gpkg` |
| 04 | `04_feature_assembly_ablation.ipynb` | steps 01–03 + labels | `master_hex_v4.gpkg`, ablation table |
| 05 | `05_final_classification.ipynb` | step 04 + labels | **`madrid_clasificacion_final_v5.gpkg`** |

Steps 01 and 02 use **different** OSM networks — `walk` for the Block A street metrics, `all` for
the Block D grid-regularity metrics. That is what the code producing the files in use does.

Step 04 caches: if `master_hex_v4.gpkg` exists with all 42 columns it skips the cadastral
reassembly. The file ships, so step 04 is fast unless deleted.

### Part II — vitality and causal effect

| # | File | Reads | Writes |
|---|---|---|---|
| 06 | `06_network_centrality.py` | Madrid drive graph, step 01 | `centralidad_h3.csv` |
| 07 | `07_register_census_turnover.ipynb` | municipal register 2015–2025, census 2021 | `turnover_padron_2015_2025.csv` |
| — | *lost step, rebuilt in* `reconstruct.py` | step 07 + associations + gazetteer | `madrid_vitalidad_h3_master_v5.csv` |
| 08 | `08_vitality_indicators.ipynb` | premises census, master v5 | `vitalidad_ocio_hex.csv` |
| 09 | `09_chapter7_results.ipynb` | the five files below | *prints and plots only* |

Step 09 produces the whole of the results chapter — chapter 8 of the final manuscript; the file
name records the numbering of an earlier draft — and reads exactly:

```
madrid_morfologia_h3_v10.gpkg
madrid_clasificacion_final_v5.gpkg
madrid_vitalidad_h3_master_v5.csv
vitalidad_ocio_hex.csv
censo2021_seccen_madrid.gpkg
```

`notebooks/figures/` produces thesis figures only and feeds no numerical result.

## Expected output

Step 05 (console output is in Spanish, as in the original):

```
Hexágonos: 2887 · urbanos: 1654 · etiquetados: 733
AUC del índice (sin umbral): 0.772
RF CV F1-macro: 0.847 ± 0.021  (42 variables)
Tipología RF (urbano): {'Espontáneo': 237, 'Transición': 133, 'Planificado': 1284}
Acuerdo índice vs RF: 80%
```

Ablation table from step 04:

| Variable set | n | CV F1-macro |
|---|---|---|
| A (street network) | 11 | 0.560 ± 0.044 |
| A+B (+ era) | 18 | 0.775 ± 0.038 |
| A+B+C (+ built form) | 26 | 0.848 ± 0.012 |
| A+B+C+Da (+ grid geometry) | 38 | 0.841 ± 0.015 |
| all | 42 | 0.847 ± 0.021 |

Step 09 with `tipologia_rf`: OLS +9.8 %, matched +6.0 % over 144 pairs; commercial +4.4 %,
demographic +8.1 %. With `tipologia_idx`: matched −3.5 % over 188 pairs. Post-matching balance
below 0.10 on all four covariates.

## Vitality index

Every component is converted to its percentile rank on [0,1], averaged within dimension, and the
index is the unweighted mean of six dimensions.

| Block | Dimension | Variables |
|---|---|---|
| Commercial | `dim1` land-use mix | `div_actividad` |
| Commercial | `dim2` amenities | `terrazas_ext_km2`, `n_parques_500m` |
| Commercial | `dim8` leisure | `nocturno_km2`, `restauracion_km2` |
| Demographic | `dim4` associations | `asoc_km2` |
| Demographic | `dim5` turnover | `cv_pob` |
| Demographic | `dim6` youth | `pct_menores16`, `pct_16a64` |

Controls: `log_renta`, `log_densidad`, `dist_centro_km`, `log_bc_mean`. Tourism (`log_airbnb`)
enters only in §8.4 and §8.5 of the manuscript.

## Lost steps

Tracing the dependency graph backwards found five points where the original code was not kept.
Four are rebuilt and verified by `reconstruct.py`; details in
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

| # | What was missing | Fidelity |
|---|---|---|
| 1 | `asoc_km2` and `cv_pob` (dimensions 4 and 5) — they existed only inside `madrid_vitalidad_h3_master_v5.csv`, which no notebook writes | `cv_pob` **r = 1.000** (100 % identical); `asoc_km2` **r = 0.999** (99.3 %). The results chapter recomputed with them gives the same figures and the same 144 and 188 pairs |
| 2 | Spatial block validation — no `GroupKFold` anywhere in the project | **0.829** and **0.821** vs 0.826 and 0.822 |
| 3 | Common support region of Figure 7.1 — the cell uses `pt/pc/lo/hi`, which nothing defines | **[0.026, 0.528]**, 2 and 20 off support. Exact |
| 4 | Tourism correlations, tourism-controlled estimates, "SMD before" column | **15 of 15 exact** |
| 5 | External drive graph for step 06 | Regenerated, **r = 0.945**. `centralidad_h3.csv` ships, so the chain runs |

Two caveats worth carrying into the defence.

**The exact spatial-CV configuration was not recorded.** The values above were found by trying
several. Across sixteen configurations (neighbourhood and 0.5/1/2 km blocks; grouped and
stratified; k = 5 and 10) all land between 0.799 and 0.846 — a drop of zero to five points from
0.847 — so the thesis's claim holds under any of them.

**OLS is robust, matching is not.** Perturbing `log_bc_mean` with noise the size of the
centrality discrepancy (σ = 0.33, 25 draws) moves the OLS estimates by ±0.05 points and the
matched ones by ±0.9 to ±1.4:

| | OLS with noise | Matched with noise | Published |
|---|---|---|---|
| Total (RF) | +9.8 % ± 0.05 | +7.4 % ± 0.86, range [+5.9, +8.9] | +6.0 % |
| Demographic | +14.3 % ± 0.04 | +11.3 % ± 1.42, range [+9.0, +14.8] | +8.1 % |
| Unsupervised index | −1.8 % ± 0.03 | −2.3 % ± 0.71, range [−3.6, −1.1] | −3.5 % |

1:1 matching without replacement is greedy, so a small perturbation in one covariate reorders the
pairs. The sign of the reversal holds in all 25 draws, but the robust figure is the OLS one.
Matching with replacement, or k > 1 neighbours, would cut this sensitivity.

Also worth stating in the text: the six tourism-controlled figures of §8.4 (+1.4 %, +2.0 %,
+6.7 %, +5.1 %, −3.2 %, +3.8 %) are the **matched** estimates, not OLS; the OLS equivalents are
+2.4 %, +10.2 % and +5.8 %.

## Data

`data/processed/` holds the intermediates that make the repository runnable without reprocessing
the cadastre. `data/raw/` holds only light, redistributable inputs. Not included, with download
instructions in [`data/raw/SOURCES.md`](data/raw/SOURCES.md):

| File | Size | Reason |
|---|---|---|
| `catastro_comunidad_de_madrid.shp` | ~1.2 GB | 577,875 footprints |
| `ALTURAS_EDIFICIOS.shp` | ~263 MB | 490,740 polygons |
| Premises census, municipal register | ~1 GB | Open-data downloads |
| `airbnb_madrid_listings.csv` | 4.3 MB | Licence, see below |
| Cadastre INSPIRE `.gml` | ~2.7 GB | Not used by the final chain |

**Inside Airbnb.** The download page states CC BY 4.0, but the site's data policies ask that the
data not be republished. Given that contradiction the snapshot is **not redistributed**. It is
Madrid, **31 May 2026** (25,094 listings), from <https://insideairbnb.com/get-the-data/>. The
hexagon-level aggregates derived from it (`airbnb_ent_km2`) do ship inside master v5.

## Licence

MIT for the code ([`LICENSE`](LICENSE)); CC BY 4.0 for the derived data in `data/processed/`;
source data keeps its provider's licence (Cadastre, Madrid open data, INE, OpenStreetMap ODbL,
Wikidata CC0). The thesis PDF is the author's and is not MIT-licensed.

## Citation

> Fernández-Uribarri Poveda, Á. (2026). *Urban form and neighbourhood vitality in Madrid:
> separating form from place*. Master's thesis, QuEA.
