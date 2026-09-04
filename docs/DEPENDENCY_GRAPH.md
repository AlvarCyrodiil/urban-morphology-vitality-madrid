# Dependency graph

Reconstructed programmatically over the 63 `.ipynb` and `.py` files of the original project by
extracting reads and writes with regexes (`read_csv`, `read_file`, `to_csv`, `to_file`, `open()`)
and resolving path variables and `BASE + r'\…'` concatenations.

## Minimal chain

```
  OSM (OSMnx)          Cadastre INSPIRE
  walk / all           577,875 footprints
        |                     |
        +----------+----------+
                   v
        01  morphology_network_cadastre
                   v
        madrid_morfologia_h3_v10.gpkg          2,991 hex, 39 cols
           |                    |                       |
    02 ----+           03 ------+                       |
           v                    v                       |
  metricas_geometricas_v2   bloques_huellas             |
  (Block D-a)               (32,186 blocks, D-b)        |
           |                    |                       |
           +---------+----------+-----------------------+
                     v
        04  feature_assembly_ablation   <-- labels_hex_manual (733)
                     v
        master_hex_v4.gpkg                     2,887 hex, 42 metrics
                     v
        05  final_classification
                     v
        madrid_clasificacion_final_v5.gpkg     F1 0.847
                     |
   PART II           |
                     |
  register 2015-25   |     premises census, terraces,
  census 2021        |     parks, markets
        v            |            v
   07 register_...   |     08 vitality_indicators
        v            |            v
  turnover_padron    |     vitalidad_ocio_hex.csv
        |            |            |
  drive graph        |            |
        v            |            |
   06 centralidad_h3 |            |
        |            |            |
        +------+-----+------------+
               v
      LOST STEP (rebuilt in reconstruct.py)
      madrid_vitalidad_h3_master_v5.csv
               v
      09  chapter7_results
               v
      OLS +9.8% · matched +6.0% (144 pairs)
      commercial +4.4% · demographic +8.1% · unsupervised index -3.4%
```

## Producer of each intermediate

| File | Produced by | Consumed by |
|---|---|---|
| `madrid_morfologia_h3_v10.gpkg` | `morfologia_madrid_modelo_catastro_alturas_v2.ipynb` → **01** | 02, 03, 04, 06, 07, 08, 09 |
| `madrid_morfologia_h3_metricas_geometricas_v2.gpkg` | `morfologia_madrid_metricas_geometricas_v2.ipynb` → **02** | 04 |
| `bloques_huellas.gpkg` | `16_bloques_desde_huellas.py` → **03** | 04, figures |
| `master_hex_v4.gpkg` | `intento_clasificacion_final_v4.ipynb` → **04** | 05 |
| `madrid_clasificacion_final_v5.gpkg` | `intento_clasificacion_final_v5.ipynb` → **05** | 08, 09 |
| `centralidad_h3.csv` | `compute_centrality_h3.py` → **06** | via master v2/v4/v5 |
| `turnover_padron_2015_2025.csv` | `Vitalidad/00_exploracion_datos.ipynb` → **07** | via the lost step |
| `vitalidad_ocio_hex.csv` | `Vitalidad/04_…_mezcla_usos.ipynb` → **08** | 09 |
| `wikidata_historical_age_h3.csv` | `wikidata_historical_age.ipynb` | Figure 3.6 only |
| **`madrid_vitalidad_h3_master_v5.csv`** | **nobody** | 08, 09 |

## Orphans

Read but never written. Expected (external raw inputs): the cadastre and heights shapefiles, the
census sections, the premises census, terraces, markets, the municipal register, the VUT register,
the Airbnb listings, `query.geojson`, `labels_hex_manual (5).csv`.

Problematic: **`madrid_vitalidad_h3_master_v5.csv`** — see `REPRODUCIBILITY.md` §1.

## Superseded branches, excluded

Determined by the graph: they write files no notebook in the final chain reads.

| Branch | Why excluded |
|---|---|
| `morfologia_madrid_indice_teorico_v{1,2,3,4,5}`, `v4(RES8)` | Terminal outputs nobody reads; `v4` feeds only the deep-learning branch |
| `clasificacion_morfologica_reconstruida{,_EN,_EN.BACKUP}` | Same; the 26 MB `_EN` produces `indice_teorico_v4.gpkg` |
| `morfologia_madrid_v6{, - copia}`, `Versiones antiguas/*` (5 files), `morfologia/01_etl_morfologia` | Write `v6`, `v8`, `v11` — unread |
| `morfologia_madrid_tres_clases_v1` | Terminal output |
| `morfologia_madrid_modelo con catastro` | Superseded by `alturas_v2`; contains the `officialAr` bug and a cadastre path that does not exist |
| `morfologia_madrid_metricas_geometricas` (v1) | Superseded by `_v2` |
| `intento_clasificacion_final{,_v2,_v3}` | Terminal outputs; v3 is read only by a figure script. **v4 is kept** — it produces `master_hex_v4.gpkg` and the ablation table |
| `Vitalidad/0{1,2,3}_*` | Superseded by the v4→v5 chain; 02 uses the old classification and gets ATT ≈ 0 |
| `Vitalidad/04_analisis_vitalidad_v4` | Superseded by `04_…_mezcla_usos`, which is later and a superset |
| `Clasificacion extra/*` (10 files, `madrid.gpkg` 288 MB, `ResNet34-4class6.h5` 85 MB) | Chen & Biljecki (2021) appears in the thesis as a citation only; no experiment is reproduced |
| `clasificacion_morfologica/0{0..12}_*.py` | Exploration that led to the 42 variables; the definitive computation lives inside step 04. **13–16 kept** (16 produces `bloques_huellas.gpkg`; 13–15 produce figures) |
| `Catastro/outputs_altura_calle/*` | Not among the 42 variables |

## Scanner limitations

Paths built inside loops or f-strings are detected as templates (`padron_enero_{year}.csv`), and a
variable reassigned several times can resolve to the wrong value. Every critical file's result was
confirmed by reading the code by hand.
