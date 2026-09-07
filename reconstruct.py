"""Rebuild the four steps whose original code was lost, and check them against the
published figures. ~3 min, no downloads.

    python reconstruct.py   # exit 0 if everything matches

1. asoc_km2 and cv_pob - the two vitality dimensions that existed only inside
   madrid_vitalidad_h3_master_v5.csv, which no notebook writes.
2. Spatial block validation (0.826 by neighbourhood, 0.822 by 1 km block).
3. Common support region of the common-support figure.
4. Tourism correlations, tourism-controlled estimates, covariate-balance table.
"""
import re
import sys
import unicodedata

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold

from tfm import (CRS, CTRL, PROC, RAW, all_passed, check, effect,
                 labelled_features, load_vitality, rf)


def normalise(s):
    """Uppercase, strip accents and punctuation - for street-name matching."""
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", s)).strip()


# ---------------------------------------------------------------- 1. lost columns
print("\n" + "=" * 70)
print(" 1. THE TWO LOST VITALITY COLUMNS (dimensions 4 and 5)")
print("=" * 70 + "\n")

hexes = gpd.read_file(PROC / "madrid_morfologia_h3_v10.gpkg").to_crs(CRS)
hexes["hex_id"] = hexes["hex_id"].astype(str)
hexes["km2"] = hexes.geometry.area / 1e6

# asoc_km2: the register has postal addresses only, so geocode against the street gazetteer
assoc = pd.read_csv(RAW / "entidades_asociaciones.csv", sep=";", encoding="latin-1", dtype=str)
assoc.columns = [c.lstrip("﻿") for c in assoc.columns]
gaz = pd.read_csv(RAW / "street_gazetteer.csv")
assoc["via"] = assoc["Calle"].map(normalise)
assoc["num"] = pd.to_numeric(assoc["Numero"].str.extract(r"(\d+)")[0], errors="coerce")

located = assoc.merge(gaz, on=["via", "num"], how="left")
exact = located["x"].notna().mean()
street_centroid = gaz.groupby("via", as_index=False)[["x", "y"]].mean().add_suffix("_v")
located = located.merge(street_centroid.rename(columns={"via_v": "via"}), on="via", how="left")
located["x"] = located["x"].fillna(located["x_v"])
located["y"] = located["y"].fillna(located["y_v"])
print(f"  {len(assoc)} associations: {exact:.1%} matched on street+number, "
      f"{located['x'].notna().mean():.1%} with street-centroid fallback")

pts = located.dropna(subset=["x", "y"])
pts = gpd.GeoDataFrame(pts, geometry=gpd.points_from_xy(pts.x, pts.y), crs=CRS)
counts = gpd.sjoin(pts, hexes[["hex_id", "geometry"]], predicate="within",
                   how="inner").groupby("hex_id").size().rename("n")
assoc_hex = hexes[["hex_id", "km2"]].merge(counts, on="hex_id", how="left").fillna({"n": 0})
assoc_hex["asoc_rebuilt"] = assoc_hex["n"] / assoc_hex["km2"]

# cv_pob: plain mean over the census sections whose centroid falls in the hexagon
sections = gpd.read_file(RAW / "censo2021_seccen_madrid.gpkg").to_crs(CRS)
sections["CUSEC"] = pd.to_numeric(sections["CUSEC"], errors="coerce")
turnover = pd.read_csv(PROC / "turnover_padron_2015_2025.csv")
sec = sections.merge(turnover[["CUSEC", "cv_pob"]], on="CUSEC", how="left")
sec_pts = sec.copy()
sec_pts["geometry"] = sec.geometry.centroid
cv_hex = (gpd.sjoin(sec_pts[["cv_pob", "geometry"]], hexes[["hex_id", "geometry"]],
                    how="inner", predicate="within")
          .groupby("hex_id")["cv_pob"].mean().rename("cv_rebuilt").reset_index())

published = pd.read_csv(PROC / "madrid_vitalidad_h3_master_v5.csv")
published["hex_id"] = published["hex_id"].astype(str)
side_by_side = (published[["hex_id", "asoc_km2", "cv_pob"]]
                .merge(assoc_hex[["hex_id", "asoc_rebuilt"]], on="hex_id")
                .merge(cv_hex, on="hex_id", how="left"))

a = side_by_side.dropna(subset=["asoc_km2", "asoc_rebuilt"])
check("asoc_km2 vs stored (Pearson r)", float(np.corrcoef(a.asoc_km2, a.asoc_rebuilt)[0, 1]),
      1.0, 0.01, "{:8.4f}")
print(f"        identical hexagons: {np.isclose(a.asoc_km2, a.asoc_rebuilt).mean():.1%}   "
      f"Spearman {spearmanr(a.asoc_km2, a.asoc_rebuilt).statistic:.4f}")
c = side_by_side.dropna(subset=["cv_pob", "cv_rebuilt"])
check("cv_pob vs stored (Pearson r)", float(np.corrcoef(c.cv_pob, c.cv_rebuilt)[0, 1]),
      1.0, 0.001, "{:8.5f}")
print(f"        identical hexagons: {np.isclose(c.cv_pob, c.cv_rebuilt).mean():.1%}   n={len(c)}")

# ------------------------------------------------------- 2. results chapter rebuilt
print("\n" + "=" * 70)
print(" 2. RESULTS CHAPTER USING THE REBUILT COLUMNS")
print("=" * 70 + "\n")

rebuilt = assoc_hex[["hex_id", "asoc_rebuilt"]].merge(cv_hex, on="hex_id", how="outer")
_, _, m = load_vitality(asoc_col="asoc_rebuilt", cv_col="cv_rebuilt", extra=rebuilt)

for outcome, treatment, name, want_ols, want_att in [
        ("vitality", "tipologia_rf", "total (RF)", 9.8, 6.0),
        ("vit_commercial", "tipologia_rf", "commercial", 6.1, 4.4),
        ("vit_demographic", "tipologia_rf", "demographic", 14.3, 8.1),
        ("vitality", "tipologia_idx", "total (unsupervised)", -1.8, -3.5)]:
    ols, _, att, _, n, sample = effect(m, outcome, treatment)
    check(f"{name} - OLS", ols, want_ols, 0.6, "{:+7.1f}%")
    check(f"{name} - matched ({n} pairs)", att, want_att, 0.6, "{:+7.1f}%")

# ---------------------------------------------------------------- 3. spatial validation
print("\n" + "=" * 70)
print(" 3. SPATIAL BLOCK VALIDATION")
print("=" * 70 + "\n")

master = gpd.read_file(PROC / "master_hex_v4.gpkg").to_crs(CRS)
d, X, y, _ = labelled_features(master)
centroids = d.geometry.centroid


def grouped_f1(groups, splitter):
    scores = [f1_score(y[te], rf().fit(X[tr], y[tr]).predict(X[te]), average="macro")
              for tr, te in splitter.split(X, y, groups=groups)]
    return float(np.mean(scores)), float(np.std(scores))


km_block = (np.floor(centroids.x / 1000).astype(int).astype(str) + "_" +
            np.floor(centroids.y / 1000).astype(int).astype(str)).values
mean_b, sd_b = grouped_f1(d["barrio_nombre"].fillna("NA").values,
                          StratifiedGroupKFold(10, shuffle=True, random_state=42))
check("holding out neighbourhoods (StratifiedGroupKFold 10)", mean_b, 0.826, 0.008, "{:8.3f}")
mean_k, sd_k = grouped_f1(km_block, GroupKFold(10))
check("1 km spatial blocks (GroupKFold 10)", mean_k, 0.822, 0.008, "{:8.3f}")
print(f"        spread: neighbourhoods +-{sd_b:.3f}, blocks +-{sd_k:.3f}")

# ---------------------------------------------------------------- 4. support and tourism
print("\n" + "=" * 70)
print(" 4. COMMON SUPPORT AND TOURISM")
print("=" * 70 + "\n")

*_, sample = effect(m, "vitality", "tipologia_rf")
z = (sample[CTRL].astype(float) - sample[CTRL].astype(float).mean()) / sample[CTRL].astype(float).std()
ps = LogisticRegression(max_iter=20000).fit(z.values, sample["esp"].values).predict_proba(z.values)[:, 1]
treated, control = ps[sample.esp.values == 1], ps[sample.esp.values == 0]
lo, hi = max(treated.min(), control.min()), min(treated.max(), control.max())
check("common support - lower bound", lo, 0.026, 0.0015, "{:8.3f}")
check("common support - upper bound", hi, 0.528, 0.0015, "{:8.3f}")
print(f"        off support: {int(((treated < lo) | (treated > hi)).sum())} spontaneous / "
      f"{int(((control < lo) | (control > hi)).sum())} planned   (published 2 / 20)\n")

for v, want in zip(CTRL, [0.30, 0.38, 0.55, 0.33]):
    t, c_ = sample.loc[sample.esp == 1, v], sample.loc[sample.esp == 0, v]
    smd = abs(t.mean() - c_.mean()) / np.sqrt((t.std() ** 2 + c_.std() ** 2) / 2)
    check(f"balance SMD before - {v}", smd, want, 0.015, "{:8.2f}")

print()
for col, want in [("vitality", 0.71), ("vit_commercial", 0.74), ("vit_demographic", 0.45),
                  ("dim5", 0.03), ("dim6", -0.15)]:
    check(f"r({col}, log_airbnb)", float(m[[col, "log_airbnb"]].corr().iloc[0, 1]),
          want, 0.012, "{:+8.2f}")

print()
for col, name, want in [("vit_commercial", "commercial", 1.4), ("dim8", "leisure (dim8)", 2.0),
                        ("vit_demographic", "demographic", 6.7), ("dim1", "land-use mix (dim1)", 5.1),
                        ("dim2", "amenities (dim2)", -3.2), ("vitality", "total", 3.8)]:
    _, _, att, *_ = effect(m, col, "tipologia_rf", CTRL + ["log_airbnb"])
    check(f"tourism-controlled, matched - {name}", att, want, 0.45, "{:+7.1f}%")

print("\n" + "=" * 70)
print("  ALL LOST STEPS REBUILT" if all_passed() else "  MISMATCH - see above")
print("=" * 70 + "\n")
sys.exit(0 if all_passed() else 1)
