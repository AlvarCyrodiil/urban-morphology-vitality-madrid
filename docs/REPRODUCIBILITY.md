# Reproducibility audit

Built by walking the `file → notebook → file` dependency graph backwards from the final outputs
across the 63 `.ipynb` and `.py` files of the original project, extracting reads and writes by
regex and resolving path variables.

Five points had no surviving code. Four are rebuilt and verified by `reconstruct.py` (27 checks,
all passing); the fifth is partly closed.

| # | Missing | Status |
|---|---|---|
| 1 | `asoc_km2`, `cv_pob` (vitality dimensions 4 and 5) | rebuilt — r = 0.999 and r = 1.000 |
| 2 | Spatial block validation (0.826 / 0.822) | rebuilt — 0.829 and 0.821 |
| 3 | Common support region (Figure 7.1) | rebuilt — exact |
| 4 | §8.4 correlations and estimates, balance table | rebuilt — 15/15 exact |
| 5 | External drive graph for centrality | partial — regenerated at r = 0.945 |

## 1. The two lost vitality columns

`madrid_vitalidad_h3_master_v5.csv` is read by three notebooks and written by none. It carries 15
columns absent from the previous `v4`, two of which enter the vitality index. Timestamps bracket
the lost notebook:

```
31 May 2026 16:56  madrid_vitalidad_h3_master_v4.csv
31 May 2026 18:01  entidades_asociaciones.csv, entidades_colectivos.csv
31 May 2026 18:06  callejero_direcciones.csv
31 May 2026 18:08  madrid_vitalidad_h3_master_v5.csv
```

**`cv_pob`** — plain mean of the section-level population coefficient of variation over the census
sections whose **centroid** falls inside each hexagon, taking `cv_pob` from
`turnover_padron_2015_2025.csv` (produced by step 07 from the 2015–2025 municipal register).

> r = 1.00000, **100 %** of the 1,206 hexagons identical. Population-weighted mean (r = 0.998),
> median (0.987) and maximum (0.920) were ruled out; only the plain mean reproduces the file.

**`asoc_km2`** — the association register carries postal addresses but no coordinates, so records
are geocoded against the municipal street gazetteer (`street_gazetteer.csv`, UTM ETRS89) on
normalised street name plus number, falling back to the street centroid; then counted per hexagon
and divided by its area.

> 92.3 % matched on street+number, 94.9 % with the fallback; 3,031 of 3,200 associations land in a
> hexagon. r = 0.9987, Spearman 0.997, **99.3 %** of hexagons identical. The residual 0.7 % are
> records whose exact number does not match and which the original code resolved slightly
> differently.

**The test that matters.** Substituting dimensions 4 and 5 with the rebuilt columns and rerunning
the results chapter:

| Result | Rebuilt | Published |
|---|---|---|
| Total (RF) — OLS | +9.7 % | +9.8 % |
| Total (RF) — matched, 144 pairs | +6.0 % | +6.0 % |
| Commercial — OLS / matched | +6.1 % / +4.4 % | +6.1 % / +4.4 % |
| Demographic — OLS / matched | +14.3 % / +8.0 % | +14.3 % / +8.1 % |
| Unsupervised index — matched, 188 pairs | −3.5 % | −3.5 % |

Pair counts match exactly. Part II is reproducible from raw data.

## 2. Spatial block validation

The thesis reports F1-macro falling from 0.847 to 0.826 holding out neighbourhoods and to 0.822
on 1 km blocks. The project contains no `GroupKFold` or spatial grouping of any kind — only the
`StratifiedKFold(5)` that yields 0.847.

| Design | Grouping | F1-macro | Published |
|---|---|---|---|
| `StratifiedGroupKFold(10)` | neighbourhood (79 groups) | 0.829 ± 0.061 | 0.826 |
| `GroupKFold(10)` | 1 km cell (162 groups) | 0.821 ± 0.055 | 0.822 |

The exact configuration was not documented and these two were found by trying several, so this is
a plausible reconstruction rather than a bit-for-bit replay. What is robust is the substantive
claim: across sixteen configurations (neighbourhood and 0.5/1/2 km blocks; `GroupKFold` and
`StratifiedGroupKFold`; k = 5 and 10) all fall between 0.799 and 0.846 — a drop of zero to five
points. The classifier's accuracy is not an artefact of spatial autocorrelation under any of them.

## 3. Common support (Figure 7.1)

The last cell of step 09 uses `pt`, `pc`, `lo`, `hi`, which no cell defines: a clean top-to-bottom
run raises `NameError`. The stored output reads
`Common support: [0.026, 0.528] | outside: 2 spontaneous, 20 planned`.

Recovered: not the stored `ps` column (which comes from the earlier classification and gives
`[0.043, 0.923]`), but a propensity score re-estimated on the Random Forest sample with
`sklearn.linear_model.LogisticRegression` **at its defaults** (L2, C = 1.0) over the four
**standardised** controls, with the support taken as the overlap of the two ranges:

```python
lo, hi = max(pt.min(), pc.min()), min(pt.max(), pc.max())
```

> Exact match: [0.026, 0.528], 2 spontaneous and 20 planned off support.

Regularisation matters here: unpenalised fits (`statsmodels.Logit`, or `penalty=None`) give
[0.026, 0.531]. The 2/20 count is the same under every variant, so the reading of the figure does
not depend on it.

## 4. Tourism (§8.4) and the balance table

**Table 7.1, "SMD before"** — imbalance before matching on the RF analytic sample (216 spontaneous,
819 planned): `log_renta` 0.30, `log_densidad` 0.38, `dist_centro_km` 0.55, `log_bc_mean` 0.33.
All four exact.

**Tourism correlations with `log_airbnb`** — over all 2,991 hexagons, not the analytic sample (which
gives markedly lower values): index +0.71, commercial +0.74, demographic +0.45, turnover +0.03,
age −0.15. All five exact.

**With tourism in the controls** — the six published figures are the **matched** estimates,
not OLS. The manuscript now states this in the caption of the components table.

| Series | Matched | Published | OLS equivalent |
|---|---|---|---|
| Commercial block | +1.4 % | +1.4 % | +2.4 % |
| Leisure (`dim8`) | +2.0 % | +2.0 % | +4.7 % |
| Demographic block | +6.7 % | +6.7 % | +10.2 % |
| Land-use mix (`dim1`) | +5.1 % | +5.1 % | +4.7 % |
| Amenities (`dim2`) | −3.2 % | −3.2 % | −2.5 % |
| Total | +3.8 % | +3.8 % | +5.8 % |

## 5. The external drive graph

Step 06 reads `…\redes-madrid\processed\madrid_drive.graphml`, which sits outside the project and
no longer exists. It produces `log_bc_mean`, one of the four controls. The output CSV ships, so
the chain runs, but the graph cannot be recovered exactly: betweenness is approximated from a
`k = 500` node sample and depends on the OSM snapshot, which changes over time.

Downloading Madrid's drive network today (31,560 nodes, 61,980 edges) and repeating the
computation gives `log_bc_mean` at **Pearson r = 0.945** against the stored file — so the stored
file is a legitimate betweenness of Madrid's street network, just not recoverable byte for byte.

Substituting the regenerated control and rerunning the results chapter (the unsupervised row of
this table was computed before the duplicate correction above and is indicative):

| Result | Regenerated | Published |
|---|---|---|
| Total (RF) — OLS | +9.7 % | +9.8 % |
| Total (RF) — matched | +7.0 % (p < 0.001) | +6.0 % |
| Commercial — matched | +3.7 % (p = 0.073) | +4.4 % (p = 0.036) |
| Demographic — matched | +11.2 % (p < 0.001) | +8.1 % |
| Unsupervised index — matched | −1.9 % (p = 0.159) | −3.5 % (p = 0.020) |

### This is estimator fragility, not an error

To separate "the graph changed" from "the matched estimator is unstable", the **original**
`log_bc_mean` was perturbed with Gaussian noise of the same magnitude as the observed discrepancy
(σ = 0.33), 25 draws:

| Result | OLS with noise | Matched with noise | Published |
|---|---|---|---|
| Total (RF) | +9.8 % ± 0.05 | +7.4 % ± 0.86, range [+5.9, +8.9] | +6.0 % |
| Commercial | +6.1 % ± 0.06 | +4.3 % ± 1.05, range [+2.3, +6.5] | +4.4 % |
| Demographic | +14.3 % ± 0.04 | +11.3 % ± 1.42, range [+9.0, +14.8] | +8.1 % |
| Unsupervised index | −1.8 % ± 0.03 | −2.3 % ± 0.71, range [−3.6, −1.1] | −3.5 % |

1. **OLS is robust** (±0.05 points): +9.8 %, +6.1 %, +14.3 % and −1.8 % do not depend on the exact
   centrality values.
2. **1:1 matching without replacement is intrinsically unstable** (±0.7 to ±1.4 points). It is a
   greedy algorithm that discards controls in distance order, so a small perturbation in one
   covariate reorders the pairs. Every value obtained with the regenerated centrality falls inside
   these ranges, so none of them is evidence of an error.
3. **The sign of the reversal always holds.** Across all 25 draws the unsupervised-index effect
   stays negative (range [−3.7 %, −1.2 %]), though it loses significance in some. The thesis's
   central claim does not depend on this control; its magnitude and significance do.

Recommendation: reporting the matched estimate as preferred is defensible, but it should be stated
that it is a high-variance estimator and that the robust figure is the OLS one. Matching with
replacement, or with k > 1 neighbours, would reduce this sensitivity considerably.

To regenerate: download with `ox.graph_from_place('Madrid, Spain', network_type='drive')`, save as
`.graphml`, point `GRAPHML` at it, and run step 06 (~10–15 min).

## Corrections to prior assumptions

**Which notebook produced `madrid_morfologia_h3_v10.gpkg`.** Two write it; the file in use came
from `morfologia_madrid_modelo_catastro_alturas_v2.ipynb`:

- the `morfologia_continua` signature in the file (mean 0.490, sd 0.238) matches that notebook's
  stored output exactly, and not the other's (0.505 / 0.219);
- it fixes a real bug: INSPIRE's `officialAr` is the **text label** `'grossFloorArea'`, not a
  number; built area lives in the `value` column. The older notebook coerced it with `to_numeric`,
  got `NaN`, and fell back to a `footprint × floors` proxy. This affects `cat_far` and
  `cat_floors_mean`, two of the most important RF predictors;
- Table 3.1 of the thesis documents the **VALUE** field, which is what this notebook uses;
- the older notebook's cadastre path does not exist on disk.

The `.gpkg` timestamp (29 Apr) precedes the notebook's (4 May), which is inconsistent with the
above; most likely the notebook was saved later without rerunning the export. The numerical
signature and the `value` fix outweigh the timestamp.

**`network_type` is not uniform.** Step 01 (Block A metrics) uses `'walk'`; step 02 (Block D) uses
`'all'`. Both are in the final chain. The `'all'` calls in twelve other files belong to abandoned
branches.

**Three duplicate column pairs, not two**, in `madrid_clasificacion_final_v5.gpkg`:
`R4_all` ≡ `grid_crystallinity_all` and `R4_major` ≡ `grid_crystallinity_major` (both predictors),
plus `area_km2` ≡ `cell_km2` (neither is a predictor). So 42 variables, 40 distinct.

The Random Forest is indifferent to this, but the **unsupervised index was not**: it is an
unweighted mean of signed z-scores, so the two duplicated columns entered it twice and `R4_all`
and `R4_major` carried double weight — the equal weighting was not even uniform. They are now
excluded from `SIGN` in step 05, which leaves 27 signed variables and moves the index figures to
AUC **0.772**, F1-macro 0.632, agreement **80 %**, and the causal estimates to **−1.8 %** by OLS
(no longer significant) and **−3.5 %** matched over 188 pairs. 44 of 1,654 urban cells change
label; the old and new indices correlate at r = 0.992.

## Anchor verification

| Anchor | Expected | Found |
|---|---|---|
| Rows | 2,887 | 2,887 |
| Labels | 733 (524 planned / 209 spontaneous) | 524 + 209 |
| `tipologia_rf` | 237 / 133 / 1,284 | matches |
| Predictors | 42 (40 distinct) | 42 |
| F1-macro CV | 0.847 | 0.847 ± 0.021 |
| OLS | +9.8 % | +9.8 % |
| Matched | +6.0 %, 144 pairs | +6.0 %, 144 pairs |
| Commercial / demographic | +4.4 % / +8.1 % | +4.4 % / +8.1 % |
| Unsupervised index | −3.5 % | −3.5 % |
