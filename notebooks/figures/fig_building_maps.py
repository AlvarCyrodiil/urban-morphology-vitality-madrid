# -*- coding: utf-8 -*-
# ── MAPAS sobre las HUELLAS de edificio (no hexágonos) ───────────────────────
#
# Pinta los polígonos de catastro coloreados por las métricas de forma que se
# calculan a nivel de edificio:
#   · compacidad   C = 4πA / P²            (alto = forma compacta)
#   · orientación  rumbo del eje largo      (color cíclico, 0°≈180°)
#   · perímetro    P de cada huella [m]     (materia prima de cat_perimeter_density)
#
# Dos filas: arriba toda la ciudad, abajo un zoom (centro histórico ↔ Ensanche)
# para ver los edificios uno a uno.
# ─────────────────────────────────────────────────────────────────────────────
import warnings; warnings.filterwarnings('ignore')
import numpy as np, geopandas as gpd, matplotlib.pyplot as plt
from pathlib import Path

BASE    = Path(r'C:\Users\Alvar\OneDrive\Desktop\estudios\economía\Artículos\MQUEA')
CAT_SHP = BASE / 'Catastro' / 'catastro_comunidad_de_madrid.shp'
GPKG    = BASE / 'madrid_morfologia_h3_v10.gpkg'
CRS     = 'EPSG:25830'
POZUELO = ['Aravaca', 'El Plantío', 'Valdemarín']
OUTDIR  = Path('imagenes'); OUTDIR.mkdir(exist_ok=True)
# ventana de zoom (centro de Madrid: casco histórico al O, Ensanche/Salamanca al E)
ZOOM = (438700, 4473000, 442900, 4476500)   # xmin, ymin, xmax, ymax

# ── ciudad (para recortar el catastro a Madrid) ────────────────────────────────
hexg = gpd.read_file(GPKG).to_crs(CRS)
hexg = hexg[~hexg['barrio_nombre'].isin(POZUELO)]
city = hexg.geometry.union_all() if hasattr(hexg.geometry, 'union_all') else hexg.geometry.unary_union

# ── huellas ─────────────────────────────────────────────────────────────────
print('Cargando catastro…')
try:
    import pyogrio
    cat = pyogrio.read_dataframe(str(CAT_SHP), columns=['gml_id']).to_crs(CRS)
except Exception:
    cat = gpd.read_file(str(CAT_SHP))[['geometry']].to_crs(CRS)
cat = cat[cat.geometry.notna() & cat.geometry.is_valid].copy()
cat['area']  = cat.geometry.area
cat['perim'] = cat.geometry.length
cat = cat[(cat['area'] > 5) & (cat['perim'] > 0)]
# solo Madrid: centroide dentro de la ciudad
cat = cat[cat.geometry.centroid.within(city)].reset_index(drop=True)
print(f'  huellas en la ciudad: {len(cat):,}')

cat['compact'] = 4 * np.pi * cat['area'] / (cat['perim'] ** 2)
def bearing(geom):
    try:
        xs, ys = geom.minimum_rotated_rectangle.exterior.coords.xy
        edges = [(xs[i+1]-xs[i], ys[i+1]-ys[i]) for i in range(4)]
        dx, dy = max(edges, key=lambda e: e[0]**2 + e[1]**2)
        return np.degrees(np.arctan2(dy, dx)) % 180
    except Exception:
        return np.nan
print('Calculando orientación…')
cat['orient'] = [bearing(g) for g in cat.geometry.values]

# ── figura: 2 filas (ciudad / zoom) × 3 columnas (métricas) ─────────────────────
PANELS = [
    ('compact', 'viridis',  (0.2, 0.8),  'Compacidad  C = 4πA/P²', 'alto = compacta'),
    ('orient',  'twilight', (0, 180),    'Orientación del eje largo', '0°≈180° (cíclico)'),
    ('perim',   'plasma',   (0, 200),    'Perímetro de la huella [m]', 'base de perimeter_density'),
]
catz = cat.cx[ZOOM[0]:ZOOM[2], ZOOM[1]:ZOOM[3]]
print(f'  huellas en el zoom: {len(catz):,}')

fig, axes = plt.subplots(2, 3, figsize=(24, 16))
for col, (var, cmap, (vmin, vmax), tit, sub) in enumerate(PANELS):
    # fila 0: ciudad
    ax = axes[0, col]
    cat.plot(column=var, cmap=cmap, vmin=vmin, vmax=vmax, linewidth=0, ax=ax,
             legend=True, legend_kwds={'orientation': 'horizontal', 'shrink': 0.5, 'pad': 0.01})
    ax.set_title(f'{tit}\n{sub} — ciudad', fontsize=11); ax.set_axis_off()
    # fila 1: zoom
    ax = axes[1, col]
    catz.plot(column=var, cmap=cmap, vmin=vmin, vmax=vmax, linewidth=0.1, edgecolor='white', ax=ax)
    ax.set_xlim(ZOOM[0], ZOOM[2]); ax.set_ylim(ZOOM[1], ZOOM[3])
    ax.set_title(f'{tit} — zoom centro/Ensanche', fontsize=11); ax.set_axis_off()
fig.suptitle('Métricas de forma sobre las huellas de edificio — Madrid', fontsize=16, y=1.01)
plt.tight_layout()
out = OUTDIR / 'mapas_huella_edificios.png'
plt.savefig(out, dpi=140, bbox_inches='tight')
print(f'Guardado: {out}')
plt.show()
