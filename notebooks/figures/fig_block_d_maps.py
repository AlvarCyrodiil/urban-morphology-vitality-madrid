# -*- coding: utf-8 -*-
# ── MAPS: Block D — grid-regularity indicators ───────────────────────────────
#
# One map per metric (shown and saved individually). Persisted Block-D metrics
# only (parts a, b and the _all/_major comparison of part d). Source:
# madrid_clasificacion_final_v3.gpkg (geometry + metrics, Pozuelo already removed).
#
# Colour convention: RED ≈ spontaneous in every map (metrics whose HIGH value
# marks planned fabric —R4, BAS, edge_len_cv, block_area_cv— use a reversed scale).
#
# NOTE: the §3.4.4(c) "second family" —grid_score, bear_entropy_malla, ortho_abs,
# ortho_adapt, m3_p75, ratio_build_road— is not stored in any file (computed
# on the fly); its maps come from scripts 04/05/06 in this folder.
# ─────────────────────────────────────────────────────────────────────────────
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, geopandas as gpd, matplotlib.pyplot as plt
from pathlib import Path

BASE    = Path(r'C:\Users\Alvar\OneDrive\Desktop\estudios\economía\Artículos\MQUEA')
GPKG    = BASE / 'madrid_clasificacion_final_v3.gpkg'
LABELS  = BASE / 'labels_hex_manual.csv'
OUTDIR  = Path('imagenes'); OUTDIR.mkdir(exist_ok=True)
MIN_BLD = 5   # §3.3 filter: a hexagon is urban if cat_n_buildings >= 5 (raise to 30 for a cleaner map)

print('Loading…')
g = gpd.read_file(GPKG).to_crs('EPSG:25830')
lab = pd.read_csv(LABELS); lab['hex_id'] = lab['hex_id'].astype(str)
g['label'] = g['hex_id'].astype(str).map(
    dict(zip(lab['hex_id'], pd.to_numeric(lab['tipologia_train'], errors='coerce'))))

# (column, cmap, title, subtitle)   cmap 'RdYlBu' => red=low ; 'RdYlBu_r' => red=high
PANELS = [
    ('R4_all',             'RdYlBu',   'R4 — 4th orientation harmonic',        'high = grid (planned)'),
    ('BAS_all',            'RdYlBu',   'BAS — Bearing Alignment Score',        'high = aligned to the grid (planned)'),
    ('ADI_mean_all',       'RdYlBu_r', 'ADI — junction irregularity',          'high = irregular junctions (spontaneous)'),
    ('block_area_cv',      'RdYlBu',   'block_area_cv — block-size spread',     'high = mixed sizes (planned: Ensanche+PAU)'),
    ('block_compact_mean', 'RdYlBu_r', 'block_compact_mean — block compactness','high = compact blocks (spontaneous)'),
    ('edge_len_cv_all',    'RdYlBu',   'edge_len_cv — segment-length spread',   'high = mixed lengths (planned)'),
    ('R4_major',           'RdYlBu',   'R4_major — major network only',         'weak discriminator (|d| ~ 0.14)'),
    ('BAS_major',          'RdYlBu',   'BAS_major — major network only',        'weak discriminator'),
]

# Cohen's d (manual labels)
esp, plan = g['label'] == 0, g['label'] == 1
dvals = {}
for col, *_ in PANELS:
    c = pd.to_numeric(g[col], errors='coerce'); s = c[esp | plan].std()
    dvals[col] = (c[esp].mean() - c[plan].mean()) / s if s > 0 else np.nan
print("\nCohen's d (spontaneous − planned):")
for col in dvals:
    print(f'  {col:22s} d = {dvals[col]:+.2f}')

# §3.3 filter: non-urban (sparsely built) hexagons are greyed out
urban = pd.to_numeric(g['cat_n_buildings'], errors='coerce').fillna(0) >= MIN_BLD
print(f'\nUrban hexagons (>= {MIN_BLD} buildings): {int(urban.sum())} of {len(g)}  (rest greyed out)')
gm = g.copy()
gm.loc[~urban, [p[0] for p in PANELS]] = np.nan

# ── one figure per metric ──────────────────────────────────────────────────────
for col, cmap, title, sub in PANELS:
    fig, ax = plt.subplots(figsize=(11, 11))
    gm.plot(column=col, cmap=cmap, linewidth=0.05, edgecolor='white',
            legend=True, legend_kwds={'label': col, 'orientation': 'horizontal',
                                      'shrink': 0.55, 'pad': 0.02},
            missing_kwds={'color': 'lightgrey', 'label': f'non-urban (< {MIN_BLD} buildings)'},
            ax=ax)
    ax.set_title(f'{title}\n{sub}  ·  Cohen’s d = {dvals[col]:+.2f}  ·  red ≈ spontaneous',
                 fontsize=12, pad=10)
    ax.set_axis_off()
    plt.tight_layout()
    out = OUTDIR / f'blockD_{col}.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'Saved: {out}')
    plt.show()
