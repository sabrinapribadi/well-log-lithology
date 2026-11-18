"""Basin-independent mineral-physics features and the M0 physics reference (ADR-013 §5).

Endpoints (KGS Geological Log Analysis; Asquith & Krygowski 2004): grain density quartz 2.65, calcite 2.71, dolomite 2.87,
anhydrite 2.98, halite 2.04 g/cc; fluid 1.0 g/cc and 189 µs/ft; neutron in limestone porosity units.
Every threshold here was fixed in ADR-013 before any P3b model was evaluated.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.scoring import NAMES

RHO_FLUID, DT_FLUID, U_FLUID = 1.0, 189.0, 0.398


def _col(d: pd.DataFrame, c: str) -> pd.Series:
    return d[c].astype("float64") if c in d else pd.Series(np.nan, index=d.index)


def crossplot_porosity(rhob: pd.Series, nphi: pd.Series) -> pd.Series:
    """Neutron-density crossplot porosity (limestone units), clipped to 0–0.45."""
    dphi = (2.71 - rhob) / 1.71
    return ((nphi + dphi) / 2).clip(0.0, 0.45)


def gr_index(d: pd.DataFrame) -> pd.Series:
    """GR scaled between each well's 5th and 95th percentiles, clipped to 0–1."""
    g = _col(d, "GR").groupby(d["WELL"])
    lo, hi = g.transform(lambda s: s.quantile(0.05)), g.transform(lambda s: s.quantile(0.95))
    return ((_col(d, "GR") - lo) / (hi - lo).where(hi > lo)).clip(0, 1)


def physics_features(d: pd.DataFrame) -> pd.DataFrame:
    """RHOmaa, neutron-density separation, apparent matrix transit time, Umaa (only where PEF exists), GR index."""
    rhob, nphi, dtc, pef = _col(d, "RHOB"), _col(d, "NPHI"), _col(d, "DTC"), _col(d, "PEF")
    phi = crossplot_porosity(rhob, nphi)
    out = pd.DataFrame(index=d.index)
    out["rhomaa"] = (rhob - phi * RHO_FLUID) / (1 - phi)
    out["nd_sep"] = nphi - (2.71 - rhob) / 1.71
    out["dtmaa"] = (dtc - phi * DT_FLUID) / (1 - phi)
    rho_e = (rhob + 0.1883) / 1.0704                       # apparent electron density from bulk density
    out["umaa"] = (pef * rho_e - phi * U_FLUID) / (1 - phi)
    out["gr_index"] = gr_index(d)
    return out.astype("float32")


def m0_classify(d: pd.DataFrame) -> np.ndarray:
    """M0: rule-based mineral classifier, no training. Returns class indices (NAMES); -1 where logs are missing."""
    rhob, nphi = _col(d, "RHOB").to_numpy(), _col(d, "NPHI").to_numpy()
    f = physics_features(d)
    rm, gi = f["rhomaa"].to_numpy(), f["gr_index"].to_numpy()
    out = np.full(len(d), -1, dtype=int)
    ok = np.isfinite(rhob) & np.isfinite(nphi) & np.isfinite(gi)
    k = {n: NAMES.index(n) for n in ("Coal", "Halite", "Anhydrite", "Shale", "Sandstone", "Limestone", "Dolomite")}
    rules = [  # first match wins, in the pre-registered order
        (rhob < 1.90, "Coal"),
        ((rhob < 2.20) & (nphi < 0.05), "Halite"),
        ((rhob > 2.92) & (nphi < 0.05), "Anhydrite"),
        (gi > 0.5, "Shale"),
        (rm < 2.68, "Sandstone"),
        (rm < 2.79, "Limestone"),
        (rm >= 2.79, "Dolomite"),
    ]
    todo = ok.copy()
    for mask, name in rules:
        hit = todo & np.nan_to_num(mask, nan=False).astype(bool)
        out[hit] = k[name]
        todo &= ~hit
    return out
