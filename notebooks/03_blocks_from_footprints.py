# -*- coding: utf-8 -*-
# %% [markdown]
# # Bloques (manzanas) desde las huellas de edificio — forma, regularidad y patio
#
# Agrupamos las huellas que (casi) se tocan (cierre morfológico) → cada figura = una
# **manzana edificada**. Métricas:
#
# **Regularidad del contorno** (lo que el ojo distingue entre casco y Ensanche):
# - `edgeR4` — R4 (4º armónico) de los **rumbos de los lados** del bloque. Rectángulo = 2
#   direcciones perpendiculares → ≈1; contorno irregular → muchas direcciones → bajo.
#   (El mejor discriminador: casco ≈0.73 vs Ensanche ≈0.93.)
# - `rectangularity` — área / área del rectángulo rotado mínimo. 1 = rectángulo perfecto.
# - (`compact` = 4πA/P² y `convexity` se guardan como descriptores secundarios; la compacidad
#   mezcla irregularidad con elongación, por eso discrimina peor.)
#
# **Patio interior** (huecos de la manzana):
# - `courtyard_ratio` = patios / envolvente ; `courtyard_to_built` = patios / construido.
# - `court_convexity` / `court_angularity` — regularidad del patio (Ensanche: patio grande y
#   regular; casco: patios pequeños e irregulares; PAU de chalets: sin patio).
#
# Los bloques + métricas se cachean en `bloques_huellas.gpkg` (borra el fichero para recalcular).

# %%
import warnings; warnings.filterwarnings('ignore')
import numpy as np, geopandas as gpd, matplotlib.pyplot as plt
from shapely import unary_union
from shapely.geometry import Polygon, box
from pathlib import Path

BASE    = Path(r'C:\Users\Alvar\OneDrive\Desktop\estudios\economía\Artículos\MQUEA')
CAT_SHP = BASE / 'Catastro' / 'catastro_comunidad_de_madrid.shp'
GPKG    = BASE / 'madrid_morfologia_h3_v10.gpkg'
CRS     = 'EPSG:25830'
POZUELO = ['Aravaca', 'El Plantío', 'Valdemarín']
OUTDIR  = Path('imagenes'); OUTDIR.mkdir(exist_ok=True)
CACHE   = Path('bloques_huellas.gpkg')

CLOSE, SIMP, MIN_BLK, COURT_MIN = 2.0, 3.0, 50, 30   # m / m / m² / m²
ZOOM = (438700, 4473000, 442900, 4476500)            # centro histórico (O) ↔ Ensanche (E)

# %% [markdown]
# ## Helpers de forma

# %%
def edge_r4(poly):
    """R4 de los rumbos de los lados (ponderado por longitud). Rectángulo→≈1, irregular→bajo."""
    xy = np.asarray(poly.exterior.coords); s = np.diff(xy, axis=0)
    L = np.hypot(s[:, 0], s[:, 1])
    if L.sum() == 0: return np.nan
    th = np.arctan2(s[:, 1], s[:, 0]); w = L / L.sum()
    return float(abs(np.sum(w * np.exp(1j * 4 * th))))

def rectangularity(poly):
    mrr = poly.minimum_rotated_rectangle
    return poly.area / mrr.area if mrr.area > 0 else np.nan

def angularity(poly):
    xy = np.asarray(poly.exterior.coords)[:-1]
    if len(xy) < 3: return np.nan
    e = np.roll(xy, -1, axis=0) - xy; a = np.arctan2(e[:, 1], e[:, 0])
    t = (np.diff(a, append=a[0]) + np.pi) % (2*np.pi) - np.pi
    return float(np.degrees(np.abs(t).sum()))

# %% [markdown]
# ## 1. Construir bloques + métricas (o cargar de caché)

# %%
if CACHE.exists():
    bdf = gpd.read_file(CACHE)
    print(f'Cargado de caché: {len(bdf):,} bloques')
else:
    print('Cargando catastro…')
    try:
        import pyogrio
        cat = pyogrio.read_dataframe(str(CAT_SHP), columns=['gml_id']).to_crs(CRS)
    except Exception:
        cat = gpd.read_file(str(CAT_SHP))[['geometry']].to_crs(CRS)
    cat = cat[cat.geometry.notna() & cat.geometry.is_valid]
    hexg = gpd.read_file(GPKG).to_crs(CRS); hexg = hexg[~hexg['barrio_nombre'].isin(POZUELO)]
    city = hexg.geometry.union_all() if hasattr(hexg.geometry, 'union_all') else hexg.geometry.unary_union
    cat = cat[cat.geometry.centroid.within(city)].copy()
    print(f'  huellas en la ciudad: {len(cat):,}')

    print(f'Fusionando huellas (CLOSE={CLOSE} m)…')
    merged = unary_union(cat.geometry.buffer(CLOSE)).buffer(-CLOSE)
    parts = list(merged.geoms) if merged.geom_type == 'MultiPolygon' else [merged]
    recs = []
    for g in parts:
        if g.is_empty or g.area < MIN_BLK: continue
        env = Polygon(g.exterior); env_s = env.simplify(SIMP, preserve_topology=True)
        if not env_s.is_valid or env_s.area < MIN_BLK: continue
        courts = [Polygon(r) for r in g.interiors]; courts = [c for c in courts if c.area >= COURT_MIN]
        if courts:
            w = np.array([c.area for c in courts])
            cc = np.average([c.area / c.convex_hull.area for c in courts], weights=w)
            ca = np.average([angularity(c.simplify(SIMP)) for c in courts], weights=w)
            carea = float(w.sum())
        else:
            cc = ca = np.nan; carea = 0.0
        recs.append(dict(geometry=env_s, built_area=g.area, env_area=env.area,
                         court_area=carea, court_n=len(courts), court_convexity=cc, court_angularity=ca))
    bdf = gpd.GeoDataFrame(recs, crs=CRS)
    # métricas de contorno
    bdf['edgeR4']         = bdf.geometry.apply(edge_r4)
    bdf['rectangularity'] = bdf.geometry.apply(rectangularity)
    bdf['compact']        = 4*np.pi*bdf.geometry.area / (bdf.geometry.length**2)
    bdf['convexity']      = bdf.geometry.area / bdf.geometry.convex_hull.area
    # métricas de patio
    bdf['courtyard_ratio']    = bdf['court_area'] / bdf['env_area']
    bdf['courtyard_to_built'] = bdf['court_area'] / bdf['built_area']
    bdf.to_file(CACHE)
    print(f'  bloques: {len(bdf):,}  → cacheado en {CACHE}')

print(bdf[['edgeR4','rectangularity','compact','courtyard_ratio','court_convexity']].describe().round(3).to_string())

# %% [markdown]
# ## 2. Comprobación: centro histórico vs Ensanche

# %%
for name, w in {'Centro histórico': (439400, 4473300, 440200, 4474100),
                'Ensanche (Salamanca)': (441100, 4474600, 441900, 4475400)}.items():
    s = bdf[bdf.intersects(box(*w))]
    print(f'  {name:22s}: edgeR4={s.edgeR4.median():.2f}  rect={s.rectangularity.median():.2f}  '
          f'courtyard_ratio={s.courtyard_ratio.median():.2f}  court_convexity={s.court_convexity.median():.2f}')

# %% [markdown]
# ## 3. Mapas (ciudad + zoom)

# %%
def panel_map(panels, fname, suptitle):
    bz = bdf[bdf.intersects(box(*ZOOM))]
    fig, axes = plt.subplots(2, len(panels), figsize=(10*len(panels), 18))
    for col, (var, cmap, (vmin, vmax), tit, sub) in enumerate(panels):
        ax = axes[0, col]
        bdf.plot(column=var, cmap=cmap, vmin=vmin, vmax=vmax, linewidth=0, ax=ax,
                 legend=True, legend_kwds={'orientation':'horizontal','shrink':0.5,'pad':0.01},
                 missing_kwds={'color':'lightgrey'})
        ax.set_title(f'{tit}\n{sub} — ciudad', fontsize=12); ax.set_axis_off()
        ax = axes[1, col]
        bz.plot(column=var, cmap=cmap, vmin=vmin, vmax=vmax, linewidth=0.2, edgecolor='white', ax=ax,
                missing_kwds={'color':'lightgrey'})
        ax.set_xlim(ZOOM[0], ZOOM[2]); ax.set_ylim(ZOOM[1], ZOOM[3])
        ax.set_title(f'{tit} — zoom centro/Ensanche', fontsize=12); ax.set_axis_off()
    fig.suptitle(suptitle, fontsize=16, y=1.0); plt.tight_layout()
    out = OUTDIR / fname; plt.savefig(out, dpi=140, bbox_inches='tight'); print(f'Guardado: {out}'); plt.show()

# Mapa A — regularidad del contorno
panel_map(
    [('edgeR4', 'RdYlBu', (0.3, 1.0), 'edgeR4 — ortogonalidad del contorno', 'bajo = irregular (espontáneo) · alto = rectángulo'),
     ('rectangularity', 'RdYlBu', (0.4, 1.0), 'Rectangularidad — área/bbox', 'bajo = irregular (espontáneo) · 1 = rectángulo')],
    'bloques_huellas_irregularidad.png', 'Regularidad del contorno de manzana — Madrid (rojo ≈ espontáneo)')

# %%
# Mapa B — patio interior
panel_map(
    [('courtyard_ratio', 'cividis', (0, 0.6), 'Proporción de patio — hueco/envolvente', 'alto = patio de manzana grande (Ensanche)'),
     ('court_convexity', 'viridis', (0.4, 1.0), 'Regularidad del patio — convexidad', 'bajo = patio irregular · gris = sin patio')],
    'bloques_huellas_patio.png', 'Patio interior de manzana — Madrid')

# %% [markdown]
# ## 4. Homogeneidad local — ¿se parece cada manzana a sus vecinas?
# Para cada bloque, K=6 vecinos más cercanos (por centroide):
# - `area_local_cv` = CV de las áreas del vecindario → BAJO = áreas parecidas (planificado).
# - `angle_align` = alineación circular de la orientación de rejilla (fase de R4, ponderada por
#   edgeR4) → ALTO = vecinas con la misma orientación (planificado).

# %%
from scipy.spatial import cKDTree
if 'angle_align' not in bdf.columns:
    def _edge_z(poly):
        xy = np.asarray(poly.exterior.coords); s = np.diff(xy, axis=0); L = np.hypot(s[:, 0], s[:, 1])
        if L.sum() == 0: return 0j
        th = np.arctan2(s[:, 1], s[:, 0]); w = L / L.sum(); return np.sum(w * np.exp(1j * 4 * th))
    K = 6
    _z = np.array([_edge_z(g) for g in bdf.geometry]); _mag = np.abs(_z)
    _unit = np.where(_mag > 0, _z / np.maximum(_mag, 1e-9), 0)
    _A = bdf.geometry.area.values
    _cen = np.c_[bdf.geometry.centroid.x, bdf.geometry.centroid.y]
    _, _idx = cKDTree(_cen).query(_cen, k=K + 1)            # self + K vecinos
    acv = np.full(len(bdf), np.nan); al = np.full(len(bdf), np.nan)
    for i in range(len(bdf)):
        nb = _idx[i]; a = _A[nb]
        acv[i] = a.std() / a.mean() if a.mean() > 0 else np.nan
        w = _mag[nb]
        al[i] = abs(np.sum(_unit[nb] * w) / w.sum()) if w.sum() > 0 else np.nan
    bdf['area_local_cv'] = acv; bdf['angle_align'] = al
    bdf.to_file(CACHE)                                       # re-cachear con las nuevas columnas
for name, w in {'Centro histórico': (439400, 4473300, 440200, 4474100),
                'Ensanche (Salamanca)': (441100, 4474600, 441900, 4475400)}.items():
    s = bdf[bdf.intersects(box(*w))]
    print(f'  {name:22s}: area_local_cv={s.area_local_cv.median():.2f}  angle_align={s.angle_align.median():.2f}')

# %%
# Mapa C — homogeneidad local (parecido con las manzanas vecinas)
panel_map(
    [('area_local_cv', 'RdYlBu_r', (0.2, 1.0), 'Heterogeneidad de área local (CV, K=6)', 'alto = áreas dispares (espontáneo)'),
     ('angle_align', 'RdYlBu', (0.5, 1.0), 'Alineación de orientación local (R4)', 'bajo = orientaciones dispares (espontáneo)')],
    'bloques_huellas_vecindad.png', 'Homogeneidad local de las manzanas — Madrid (rojo ≈ espontáneo)')
