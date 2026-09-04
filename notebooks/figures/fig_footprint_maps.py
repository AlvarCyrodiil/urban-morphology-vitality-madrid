# -*- coding: utf-8 -*-
# ── MAPAS: métricas de huella de edificio (compacidad, densidad de perímetro,
#    entropía de orientación) — Madrid H3 res.9 ───────────────────────────────
#
# Calcula desde el catastro las tres métricas de forma de la huella y dibuja los
# tres mapas en un único panel. Autónomo: no depende de otros scripts.
#
#   · cat_compactness_mean   = media de  C = 4πA / P²  por hexágono   (1=círculo)
#   · cat_perimeter_density  = Σ perímetro de huellas / área celda  [m/km²]
#   · cat_orientation_entropy= entropía de Shannon del rumbo del eje largo de
#                              cada huella (18 bins de 10°), normalizada a [0,1]
#
# Mínimo de 10 edificios por hexágono; en rojo los valores altos (≈ espontáneo).
# ─────────────────────────────────────────────────────────────────────────────
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, geopandas as gpd, matplotlib.pyplot as plt
from scipy.stats import entropy as shannon
from pathlib import Path

BASE     = Path(r'C:\Users\Alvar\OneDrive\Desktop\estudios\economía\Artículos\MQUEA')
GPKG_IN  = BASE / 'madrid_morfologia_h3_v10.gpkg'
CAT_SHP  = BASE / 'Catastro' / 'catastro_comunidad_de_madrid.shp'
LABELS   = BASE / 'labels_hex_manual.csv'
CRS      = 'EPSG:25830'
POZUELO  = ['Aravaca', 'El Plantío', 'Valdemarín']   # apéndice oeste desconectado
MIN_BLD  = 10
OUTDIR   = Path('imagenes'); OUTDIR.mkdir(exist_ok=True)

# ── malla ────────────────────────────────────────────────────────────────────
print('Cargando hexágonos…')
hexg = gpd.read_file(GPKG_IN).to_crs(CRS)
hexg = hexg[~hexg['barrio_nombre'].isin(POZUELO)].reset_index(drop=True)
hexg['cell_km2'] = hexg.geometry.area / 1e6

# ── catastro ───────────────────────────────────────────────────────────────────
print('Cargando catastro (puede tardar)…')
try:
    import pyogrio
    cat = pyogrio.read_dataframe(str(CAT_SHP), columns=['gml_id']).to_crs(CRS)
except Exception:
    cat = gpd.read_file(str(CAT_SHP))[['geometry']].to_crs(CRS)
cat = cat[cat.geometry.notna() & cat.geometry.is_valid].copy()
cat['area']  = cat.geometry.area
cat['perim'] = cat.geometry.length
cat = cat[(cat['area'] > 5) & (cat['perim'] > 0)].reset_index(drop=True)

# asignar cada edificio (por su centroide) a un hexágono — primero, para no
# calcular la orientación sobre los 577k de toda la Comunidad
print('Asignando edificios a hexágonos…')
pts = cat[['area', 'perim', 'geometry']].copy()
pts['bidx'] = cat.index
pts['geometry'] = cat.geometry.centroid
j = gpd.sjoin(pts, hexg[['hex_id', 'geometry']], predicate='within', how='inner')
j['geom'] = cat.geometry.values[j['bidx'].values]
print(f'  edificios dentro de la ciudad: {len(j):,}')

# ── métricas por edificio ──────────────────────────────────────────────────────
j['compact'] = 4 * np.pi * j['area'] / (j['perim'] ** 2)

def long_axis_bearing(geom):
    try:
        xs, ys = geom.minimum_rotated_rectangle.exterior.coords.xy
        edges = [(xs[i+1]-xs[i], ys[i+1]-ys[i]) for i in range(4)]
        dx, dy = max(edges, key=lambda e: e[0]**2 + e[1]**2)
        return np.degrees(np.arctan2(dy, dx)) % 180
    except Exception:
        return np.nan

print('Calculando orientación (min rotated rectangle)…')
j['bear'] = [long_axis_bearing(g) for g in j['geom'].values]

def orient_entropy(b):
    b = b.dropna()
    if len(b) < MIN_BLD:
        return np.nan
    h, _ = np.histogram(b, bins=np.linspace(0, 180, 19))
    p = h[h > 0] / h.sum()
    return shannon(p) / np.log(min(len(b), 18))

# ── agregación por hexágono ─────────────────────────────────────────────────────
g = j.groupby('hex_id')
agg = pd.DataFrame({
    'n':                       g.size(),
    'cat_compactness_mean':    g['compact'].mean(),
    'sum_perim':               g['perim'].sum(),
    'cat_orientation_entropy': g['bear'].apply(orient_entropy),
}).reset_index().merge(hexg[['hex_id', 'cell_km2']], on='hex_id', how='left')
agg['cat_perimeter_density'] = agg['sum_perim'] / agg['cell_km2']
low = agg['n'] < MIN_BLD
agg.loc[low, ['cat_compactness_mean', 'cat_perimeter_density']] = np.nan

VARS = ['cat_compactness_mean', 'cat_perimeter_density', 'cat_orientation_entropy']
agg[['hex_id'] + VARS].to_csv('metricas_huella_h3.csv', index=False)   # reutilizable
hexg = hexg.merge(agg[['hex_id'] + VARS], on='hex_id', how='left')

# ── Cohen d con las etiquetas manuales ─────────────────────────────────────────
lab = pd.read_csv(LABELS); lab['hex_id'] = lab['hex_id'].astype(str)
hexg['label'] = hexg['hex_id'].astype(str).map(
    dict(zip(lab['hex_id'], pd.to_numeric(lab['tipologia_train'], errors='coerce'))))
esp, plan = hexg['label'] == 0, hexg['label'] == 1
print('\nCohen d (espontáneo − planificado)  ·  cobertura:')
for v in VARS:
    c = pd.to_numeric(hexg[v], errors='coerce'); s = c[esp | plan].std()
    d = (c[esp].mean() - c[plan].mean()) / s if s > 0 else np.nan
    print(f'  {v:26s} d = {d:+.2f}   ({c.notna().mean()*100:.0f}% con dato)')

# ── mapas ──────────────────────────────────────────────────────────────────────
TIT = {
    'cat_compactness_mean':    ('Compacidad media de huellas  C = 4πA/P²',
                                'alto = formas compactas/regulares'),
    'cat_perimeter_density':   ('Densidad de perímetro  [m fachada / km²]',
                                'alto = grano fino, muchas parcelas pequeñas (espontáneo)'),
    'cat_orientation_entropy': ('Entropía de orientación de huellas  [0–1]',
                                'alto = orientaciones mezcladas (espontáneo) · bajo = Ensanche ortogonal'),
}
fig, axes = plt.subplots(1, 3, figsize=(24, 9))
for ax, v in zip(axes, VARS):
    hexg.plot(column=v, cmap='RdYlBu_r', linewidth=0.05, edgecolor='white',
              legend=True, legend_kwds={'orientation': 'horizontal', 'shrink': 0.6, 'pad': 0.02},
              missing_kwds={'color': 'lightgrey', 'label': f'Sin datos (<{MIN_BLD} edif.)'}, ax=ax)
    t, sub = TIT[v]
    ax.set_title(f'{t}\n{sub}', fontsize=11, pad=10)
    ax.set_axis_off()
fig.suptitle('Métricas de huella de edificio por hexágono H3 — Madrid (rojo = alto ≈ espontáneo)',
             fontsize=15, y=1.02)
plt.tight_layout()
out = OUTDIR / 'mapas_huella.png'
plt.savefig(out, dpi=150, bbox_inches='tight')
print(f'\nGuardado: {out}')
plt.show()
