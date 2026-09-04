# Hard-coded paths

Every notebook fixes its working directory in a constant near the top, with the path of the
original machine. Replace

```
C:\Users\Alvar\OneDrive\Desktop\estudios\economía\Artículos\MQUEA
```

with wherever the repository was cloned.

| File | Constant |
|---|---|
| `01_morphology_network_cadastre.ipynb` | `CATASTRO_PATH` |
| `02_geometric_metrics_block_d.ipynb` | `GPKG_IN`, `OUT` |
| `03_blocks_from_footprints.py` | `BASE` |
| `04_feature_assembly_ablation.ipynb` | `BASE` |
| `05_final_classification.ipynb` | `BASE` |
| `06_network_centrality.py` | `GRAPHML`, `GPKG_H3`, `OUT_CSV` |
| `07_register_census_turnover.ipynb` | `BASE` |
| `08_vitality_indicators.ipynb` | `BASE`, `base` — **7 occurrences**, mixed `str`/`Path`, some pointing at `MQUEA` and some at `MQUEA\Vitalidad` |
| `09_chapter7_results.ipynb` | `BASE` |
| `figures/*.py`, `figures/fig_block_metrics.ipynb` | `BASE` |

`verify.py` and `reconstruct.py` need none of this: they resolve paths relative to themselves.

## Directory layout

The notebooks expect the original layout, not this repository's. Fastest way to run them
unmodified is to recreate it:

```bash
mkdir -p run/Vitalidad run/clasificacion_morfologica
cp data/processed/madrid_morfologia_h3_v10.gpkg data/processed/madrid_morfologia_h3_metricas_geometricas_v2.gpkg run/
cp data/processed/madrid_clasificacion_final_v5.gpkg data/processed/wikidata_historical_age_h3.csv run/
cp data/raw/labels_hex_manual_v5.csv "run/labels_hex_manual (5).csv"
cp data/raw/wikidata_query.geojson run/query.geojson
cp data/processed/bloques_huellas.gpkg data/processed/master_hex_v4.gpkg run/clasificacion_morfologica/
cp data/processed/centralidad_h3.csv data/processed/turnover_padron_2015_2025.csv run/Vitalidad/
cp data/processed/madrid_vitalidad_h3_master_v4.csv data/processed/madrid_vitalidad_h3_master_v5.csv run/Vitalidad/
cp data/processed/vitalidad_ocio_hex.csv data/raw/censo2021_seccen_madrid.gpkg run/Vitalidad/
```

then point `BASE` at `run/`.

Note the label file: steps 04 and 05 look for `labels_hex_manual (5).csv`, with the space and
parentheses. It is renamed to `labels_hex_manual_v5.csv` here, so either restore the old name or
edit the `LABELS` constant.

## Encoding

The original paths contain `economía` and `Artículos`. On cp1252 consoles this can raise
`UnicodeDecodeError` that looks like a corrupt data file but is not. Cloning to a path without
accents avoids it entirely.
