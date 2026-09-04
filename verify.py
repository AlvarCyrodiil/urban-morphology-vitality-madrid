"""Recompute the published figures from data/. ~30 s, no downloads.

    python verify.py        # exit 0 if everything matches
"""
import sys

import geopandas as gpd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold, cross_val_score

from tfm import (CFOOT, CVOL, CRS, ERA, NET, PROC, all_passed, check,
                 effect, labelled_features, load_vitality, rf)

print("\n=== PART I - morphological classification ===\n")

gdf = gpd.read_file(PROC / "master_hex_v4.gpkg").to_crs(CRS)
d, X, y, feats = labelled_features(gdf)
print(f"  hexagons={len(gdf)}  labelled={len(d)}  "
      f"({int((y == 1).sum())} planned / {int((y == 0).sum())} spontaneous)\n")

cv = StratifiedKFold(5, shuffle=True, random_state=42)
check(f"Random Forest F1-macro ({len(feats)} variables)",
      cross_val_score(rf(), X, y, cv=cv, scoring="f1_macro").mean(), 0.847, 0.010)

print()
impute = SimpleImputer(strategy="median")
for name, block, want in [("block A (street network)", NET, 0.560),
                          ("blocks A+B (+era)", NET + ERA, 0.775),
                          ("blocks A+B+C (+built form)", NET + ERA + CVOL + CFOOT, 0.848)]:
    Xb = impute.fit_transform(d[[f for f in block if f in gdf.columns]])
    check(f"  ablation {name}", cross_val_score(rf(), Xb, y, cv=cv, scoring="f1_macro").mean(),
          want, 0.015)

clf = gpd.read_file(PROC / "madrid_clasificacion_final_v5.gpkg")["tipologia_rf"].value_counts()
print(f"\n  published tipologia_rf: {clf.get('Espontáneo', 0)} spontaneous / "
      f"{clf.get('Transición', 0)} transitional / {clf.get('Planificado', 0)} planned"
      "   (expected 237 / 133 / 1284)")

print("\n\n=== PART II - effect on vitality (chapter 7) ===\n")

_, _, m = load_vitality()
for outcome, treatment, name, want_ols, want_att, want_n in [
        ("vitality", "tipologia_rf", "total (RF)", 9.8, 6.0, 144),
        ("vit_commercial", "tipologia_rf", "commercial block", 6.1, 4.4, 144),
        ("vit_demographic", "tipologia_rf", "demographic block", 14.3, 8.1, 144),
        ("vitality", "tipologia_idx", "total (unsupervised index)", -2.4, -3.4, 185)]:
    ols, _, att, _, n, _ = effect(m, outcome, treatment)
    check(f"{name} - OLS", ols, want_ols, 0.6, "{:+7.1f}%")
    check(f"{name} - matched ({n} pairs, expected {want_n})", att, want_att, 0.6, "{:+7.1f}%")

print("\n" + "=" * 62)
print("  ALL FIGURES REPRODUCE" if all_passed() else "  MISMATCH - see above")
print("=" * 62 + "\n")
sys.exit(0 if all_passed() else 1)
