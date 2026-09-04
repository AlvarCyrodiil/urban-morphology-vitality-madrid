import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

print('=== Centralidad de red → Hexágonos H3 ===')

GRAPHML  = Path(r'C:\Users\Alvar\OneDrive\Desktop\redes-madrid\processed\madrid_drive.graphml')
GPKG_H3  = Path(r'C:\Users\Alvar\OneDrive\Desktop\estudios\economía\Artículos\MQUEA\madrid_morfologia_h3_v10.gpkg')
OUT_CSV  = Path(r'C:\Users\Alvar\OneDrive\Desktop\estudios\economía\Artículos\MQUEA\Vitalidad\centralidad_h3.csv')
CRS = 'EPSG:25830'

# 1. Cargar grafo
print('Cargando grafo...', end=' ', flush=True)
G = ox.load_graphml(str(GRAPHML))
print(f'OK — {G.number_of_nodes():,} nodos, {G.number_of_edges():,} aristas')

# 2. Betweenness centrality aproximado (k=500, normalizado)
print('Calculando betweenness (k=500)... puede tardar 10-15 min')
import random; random.seed(42); np.random.seed(42)
bc = nx.betweenness_centrality(G, k=500, normalized=True, weight='length', seed=42)
print(f'Betweenness calculado — {len(bc):,} nodos')

# 3. Nodos → GeoDataFrame en EPSG:25830
nodes_gdf = ox.graph_to_gdfs(G, edges=False)[['geometry']].copy()
nodes_gdf['betweenness'] = nodes_gdf.index.map(bc).fillna(0)
nodes_gdf = nodes_gdf.to_crs(CRS)
print(f'Nodos GDF: {len(nodes_gdf):,}')

# 4. Cargar hexágonos H3
gdf_h3 = gpd.read_file(str(GPKG_H3)).to_crs(CRS)[['hex_id', 'geometry']]
print(f'Hexágonos: {len(gdf_h3):,}')

# 5. Spatial join nodos → hexágonos
print('Spatial join nodos → H3...', end=' ', flush=True)
join = gpd.sjoin(nodes_gdf[['betweenness','geometry']], gdf_h3, how='inner', predicate='within')
print(f'OK — {len(join):,} nodos asignados')

# 6. Agregar por hexágono: media, max y suma de betweenness
cent_agg = (
    join.groupby('hex_id')['betweenness']
    .agg(
        bc_mean='mean',
        bc_max='max',
        bc_sum='sum',
        bc_n='count'
    )
    .reset_index()
)

# Log para comprimir la distribución muy sesgada
cent_agg['log_bc_mean'] = np.log1p(cent_agg['bc_mean'] * 1e6)  # escalar antes de log
cent_agg['log_bc_max']  = np.log1p(cent_agg['bc_max']  * 1e6)

print(f'\nHexágonos con centralidad: {len(cent_agg):,}')
print(cent_agg[['bc_mean','bc_max','log_bc_mean']].describe().round(4))

# 7. Guardar
cent_agg.to_csv(OUT_CSV, index=False)
print(f'\nGuardado: {OUT_CSV}')
