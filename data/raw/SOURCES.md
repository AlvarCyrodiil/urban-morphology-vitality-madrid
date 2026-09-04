# Data sources

## Included

| File | Origin | Licence | Used for |
|---|---|---|---|
| `labels_hex_manual_v5.csv` | Author's manual labelling of prototype neighbourhoods | CC BY 4.0 | Ground truth: 733 hexagons (524 planned / 209 spontaneous). Trains the RF in steps 04 and 05 |
| `censo2021_seccen_madrid.gpkg` | INE, 2021 Population and Housing Census, census sections | Free reuse with attribution | Age structure (`pct_menores16`, `pct_16a64`) → dimension 6 |
| `entidades_asociaciones.csv` | Madrid City Council, register of citizen entities | Open data | `asoc_km2` (dimension 4) |
| `entidades_colectivos.csv` | Same | Open data | Same |
| `street_gazetteer.csv` | Madrid City Council street gazetteer, trimmed to street / number / ETRS89 coordinates | Open data | Geocoding the associations in `reconstruct.py` |
| `mercadillos.csv` | Madrid City Council | Open data | `n_mercadillos_1km` |
| `200967-4-mercados.csv` | Madrid City Council, municipal markets | Open data | `n_mercados_500m`, `dist_mercado_km` |
| `wikidata_query.geojson` | Wikidata SPARQL (churches, convents, palaces, gates, fountains, bridges) | CC0 | Figure 3.6, historical anchors (~6,900 elements) |

## Not included

### Cadastre

`catastro_comunidad_de_madrid.shp` — 577,875 building footprints, ~1.2 GB with the `.dbf`.
Attributes used: `value` (gross built m² — **not** `officialAr`, which is the text label
`'grossFloorArea'`), `beginning`, `currentUse`, geometry.

- <https://www.catastro.hacienda.gob.es/webinspire/index.html>
- <https://www.catastro.hacienda.gob.es/INSPIRE/buildings/ES.SDGC.BU.atom.xml> (province 28)

Place at `<BASE>/Catastro/catastro_comunidad_de_madrid.shp`. Used by steps 01 and 03.

### Building heights

`ALTURAS_EDIFICIOS.shp` — 490,740 polygons with `ALTURA` in metres, ~263 MB.
<https://datos.madrid.es> → "alturas de edificios". Explored in §3.4.3 only; **not among the 42
model variables**.

### Premises census

`200085-*-censo-locales.csv`, `209548-*-censo-locales-historico.csv`, ~660 MB. Source of
`div_actividad`, `nocturno_km2`, `restauracion_km2`, `terrazas_ext_km2`.
<https://datos.madrid.es> → "Censo de locales y sus actividades". Used by steps 07 and 08.

### Municipal register 2015–2025

`padron_enero_<year>.csv`, `209163-*`, ~370 MB. Source of `cv_pob` (dimension 5) and density.
<https://datos.madrid.es> → "Padrón municipal. Estadística histórica". Used by step 07.

### Terraces, parks, tourist flats

Pavement terraces (`31097.csv`), parks and gardens, and the VUT register
(`VIVIENDAS_USO_TURISTICO.xlsx`) — all at <https://datos.madrid.es>.

### Inside Airbnb

**Not redistributed.** Madrid snapshot of **31 May 2026**, 25,094 listings, restricted to entire
home/apartment and expressed as listings per km², in logs.
<https://insideairbnb.com/get-the-data/>

The download page states Creative Commons Attribution 4.0, but the site's data policies
(<https://insideairbnb.com/data-policies/>) explicitly ask users not to republish the data. Given
that contradiction the CSV is left out. Hexagon-level aggregates derived from it
(`airbnb_ent_km2`, `log_airbnb`) do ship inside `data/processed/madrid_vitalidad_h3_master_v5.csv`.

Two limits stated in §6.2 of the thesis: no activity filter, so a listing counts whether or not it
was let; and Inside Airbnb displaces published coordinates by up to ~150 m, which at a 175 m cell
edge assigns some listings to a neighbouring hexagon. Both blur the tourism gradient rather than
create it.

### OpenStreetMap

Downloaded at runtime by OSMnx, ODbL. `network_type` differs between steps: **`walk`** in step 01
(Block A metrics), **`all`** in step 02 (Block D grid metrics). Also `ox.features_from_place` for
neighbourhoods (`admin_level=10`) and buildings. Enable `ox.settings.use_cache = True`.

### Drive network for centrality

Step 06 expects a `madrid_drive.graphml` that lived outside the project and is not kept (see
`docs/REPRODUCIBILITY.md` §5). Its output ships. To regenerate:
`ox.graph_from_place('Madrid, Spain', network_type='drive')`.

### INE household income atlas

Mean income per person by census section (`log_renta`, a chapter 7 control).
<https://www.ine.es/experimental/atlas/experimental_atlas.htm>
