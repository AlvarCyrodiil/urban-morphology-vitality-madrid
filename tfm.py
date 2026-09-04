"""Shared helpers for verify.py and reconstruct.py."""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.spatial import cKDTree
from scipy.stats import rankdata, t as tdist
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer

BASE = Path(__file__).resolve().parent
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
CRS = "EPSG:25830"
CTRL = ["log_renta", "log_densidad", "dist_centro_km", "log_bc_mean"]

NET = ["bearing_entropy", "mean_circuity", "p90_circuity", "degree_std", "edge_len_std",
       "dead_end_ratio", "intersection_dens", "internal_connect", "edge_len_mean",
       "road_density_km", "mean_degree"]
ERA = ["cat_pct_pre1860", "cat_pct_1860_1940", "cat_pct_1940_1960", "cat_pct_1960_1985",
       "cat_pct_post1985", "cat_year_median", "cat_year_iqr"]
CVOL = ["cat_floors_mean", "cat_floors_cv", "cat_far", "cat_footprint_ratio", "cat_pct_residential"]
CFOOT = ["cat_compactness_mean", "cat_perimeter_density", "cat_orientation_entropy"]
DA = ["R4_all", "BAS_all", "ADI_mean_all", "ADI_median_all", "R4_major", "BAS_major",
      "block_area_cv", "block_compact_mean", "grid_crystallinity_all", "edge_len_cv_all",
      "n_blocks", "grid_crystallinity_major"]
DB = ["edgeR4", "rectangularity", "area_local_cv", "angle_align"]
FEATURES = NET + ERA + CVOL + CFOOT + DA + DB          # 42 predictors, 40 distinct

_state = {"ok": True}


def check(name, got, want, tol, fmt="{:+8.3f}"):
    """Print a pass/fail line and track the global result."""
    ok = abs(got - want) <= tol
    _state["ok"] &= ok
    print(f"  [{'OK ' if ok else 'X  '}] {name:<46s} {fmt.format(got)}   (published {fmt.format(want).strip()})")
    return ok


def all_passed():
    return _state["ok"]


def rf():
    return RandomForestClassifier(n_estimators=400, max_features="sqrt", min_samples_leaf=3,
                                  class_weight=None, random_state=42, n_jobs=-1)


def labelled_features(gdf):
    """Design matrix and target for the 733 labelled hexagons."""
    lab = pd.read_csv(RAW / "labels_hex_manual_v5.csv")
    lab["hex_id"] = lab["hex_id"].astype(str)
    gdf["label"] = gdf["hex_id"].astype(str).map(
        dict(zip(lab["hex_id"], pd.to_numeric(lab["tipologia_train"], errors="coerce"))))
    d = gdf[gdf.label.isin([0, 1])].copy()
    feats = [f for f in FEATURES if f in gdf.columns]
    X = SimpleImputer(strategy="median").fit_transform(d[feats])
    return d, X, d["label"].astype(int).values, feats


def percentile_rank(x):
    x = pd.to_numeric(x, errors="coerce")
    ok = x.notna()
    r = pd.Series(np.nan, index=x.index)
    if ok.sum():
        r[ok] = rankdata(x[ok], method="average") / ok.sum()
    return r


def _mean_rank(*cols):
    return pd.concat(cols, axis=1).mean(axis=1)


def age_by_hexagon(gdf, sections):
    """Population-weighted <16 and 16-64 shares per hexagon."""
    pts = sections.copy()
    pts["geometry"] = sections.geometry.centroid
    j = gpd.sjoin(pts[["pct_menores16", "pct_16a64", "pob_total", "geometry"]],
                  gdf[["hex_id", "geometry"]], how="inner", predicate="within")

    def w(g, c):
        v, wt = g[c].to_numpy(float), g["pob_total"].to_numpy(float)
        m = np.isfinite(v) & np.isfinite(wt) & (wt > 0)
        return float(np.average(v[m], weights=wt[m])) if m.any() else np.nan

    return pd.DataFrame([(h, w(g, "pct_menores16"), w(g, "pct_16a64")) for h, g in j.groupby("hex_id")],
                        columns=["hex_id", "pct_menores16", "pct_16a64"])


def load_vitality(asoc_col="asoc_km2", cv_col="cv_pob", extra=None):
    """Master table with the six vitality dimensions and the two typologies.

    asoc_col / cv_col select which columns feed dimensions 4 and 5, so the same
    code serves both the published values and the reconstructed ones (passed in `extra`).
    """
    gdf = gpd.read_file(PROC / "madrid_morfologia_h3_v10.gpkg").to_crs(CRS)
    gdf["hex_id"] = gdf["hex_id"].astype(str)
    m = pd.read_csv(PROC / "madrid_vitalidad_h3_master_v5.csv")
    m["hex_id"] = m["hex_id"].astype(str)
    ocio = pd.read_csv(PROC / "vitalidad_ocio_hex.csv")
    ocio["hex_id"] = ocio["hex_id"].astype(str)
    m = m.merge(ocio, on="hex_id", how="left")
    if extra is not None:
        m = m.merge(extra, on="hex_id", how="left")

    sections = gpd.read_file(RAW / "censo2021_seccen_madrid.gpkg").to_crs(CRS)
    m = m.merge(age_by_hexagon(gdf, sections), on="hex_id", how="left")

    pr = percentile_rank
    m["dim1"] = pr(m["div_actividad"])
    m["dim2"] = _mean_rank(pr(m["terrazas_ext_km2"]), pr(m["n_parques_500m"]))
    m["dim4"] = pr(m[asoc_col])
    m["dim5"] = pr(m[cv_col])
    m["dim6"] = _mean_rank(pr(m["pct_menores16"]), pr(m["pct_16a64"]))
    m["dim8"] = _mean_rank(pr(m["nocturno_km2"]), pr(m["restauracion_km2"]))
    m["vitality"] = m[["dim1", "dim2", "dim4", "dim5", "dim6", "dim8"]].mean(axis=1)
    m["vit_commercial"] = m[["dim1", "dim2", "dim8"]].mean(axis=1)
    m["vit_demographic"] = m[["dim4", "dim5", "dim6"]].mean(axis=1)

    clf = gpd.read_file(PROC / "madrid_clasificacion_final_v5.gpkg")[
        ["hex_id", "tipologia_idx", "tipologia_rf"]]
    clf["hex_id"] = clf["hex_id"].astype(str)
    return gdf, sections, m.merge(clf, on="hex_id", how="left")


def effect(m, outcome, treatment, ctrl=CTRL):
    """OLS and 1:1 Mahalanobis-matched ATT, both as % of the control mean.

    Returns (ols_pct, ols_p, att_pct, att_p, n_pairs, sample).
    """
    d = m[m[treatment].isin(["Espontáneo", "Planificado"])].dropna(subset=[outcome] + ctrl).copy()
    d["esp"] = (d[treatment] == "Espontáneo").astype(int)
    ref = d.loc[d.esp == 0, outcome].mean()

    fit = sm.OLS(d[outcome].astype(float),
                 sm.add_constant(d[["esp"] + ctrl].astype(float))).fit(cov_type="HC1")

    z = (d[ctrl] - d[ctrl].mean()) / d[ctrl].std()
    treated, control = d.index[d.esp == 1], d.index[d.esp == 0]
    L = np.linalg.cholesky(np.linalg.inv(np.cov(z.values.T)))
    dist, nn = cKDTree(z.loc[control].values @ L).query(z.loc[treated].values @ L, k=1)
    used, pairs = set(), []
    for i in np.argsort(dist):                       # greedy, nearest pair first
        c = nn[i]
        if c not in used:
            pairs.append((treated[i], control[c]))
            used.add(c)
    gaps = d.loc[[a for a, _ in pairs], outcome].values - d.loc[[b for _, b in pairs], outcome].values
    att = gaps.mean()
    p_att = 2 * (1 - tdist.cdf(abs(att / (gaps.std(ddof=1) / np.sqrt(len(gaps)))), len(gaps) - 1))
    return (fit.params["esp"] / ref * 100, fit.pvalues["esp"], att / ref * 100, p_att, len(pairs), d)
