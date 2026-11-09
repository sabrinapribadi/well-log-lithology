"""REST API over the lithology tools (ADR-007).

    uvicorn src.serving.api:app --port 8000
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile

from src.serving.contracts import Lithology, Note, NotFound, Quality, UnitAgreement
from src.serving.tools import Tools

app = FastAPI(title="Well-Log Lithology API", version="1",
              description="North Sea lithology from a blind-tested model, Kansas log quality, and the Kansas transfer test result.")
MAX_UPLOAD = 20 * 1024 * 1024


@lru_cache(maxsize=1)
def tools() -> Tools:
    return Tools()


def _or_404(r):
    if isinstance(r, NotFound):
        raise HTTPException(status_code=404, detail=r.message)
    return r


@app.get("/health")
def health() -> dict:
    t = tools()
    return {"ok": True, "force_wells": len(t.store.force), "kansas_wells": len(t.store.kansas), "kansas_lithology_validated": False}


@app.get("/wells/{well:path}/lithology", response_model=Lithology)
def lithology(well: str):
    return _or_404(tools().predict_lithology(well))


@app.get("/kansas/{kgs_id}/quality", response_model=Quality)
def quality(kgs_id: str):
    return _or_404(tools().well_quality(kgs_id))


@app.get("/units/{unit}", response_model=UnitAgreement)
def unit(unit: str):
    return _or_404(tools().unit_agreement(unit))


@app.get("/wells/{well:path}/note", response_model=Note)
def note(well: str):
    return _or_404(tools().explain_well(well))


@app.post("/predict")
async def predict(file: UploadFile) -> dict:
    """Upload a LAS file: returns its ADR-006 quality report. Lithology is not returned for files outside the FORCE
    North Sea setting, because the transfer test failed (ADR-005)."""
    import xgboost as xgb

    from src.quality import las_quality
    raw = await file.read()
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="LAS file larger than 20 MB")
    model = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser() / "models" / "p3_transfer_T.json"
    bst = xgb.Booster(); bst.load_model(str(model))
    r = las_quality(raw, file.filename or "upload.las", None, "upload", bst)
    if not r["row"]["ok"]:
        raise HTTPException(status_code=422, detail=f"Could not read the LAS file: {r['row']['error']}")
    row = {k: v for k, v in r["row"].items() if k not in ("archive", "entry", "kgs_id")}
    return {"quality": row, "lithology": None, "caveat": "Lithology is not validated outside the FORCE North Sea wells (ADR-005)."}
