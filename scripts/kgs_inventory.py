"""P0: inventory every Kansas LAS file (ADR-002 P0, ADR-003 E3–E4) without extracting the archive.

    python scripts/kgs_inventory.py [--workers 6]

Each yearly zip holds LAS files directly and inside nested zips (one LAS each). For every file: LAS version, wrap,
null code, depth range and unit, API number, location, and its curves with their standard names (src/curves.py).
Locations missing from a header are filled from the KGS LAS index (ks_las_files.txt) by file name.
Writes WLL_DATA_DIR/derived/kgs_files.parquet and kgs_curves.parquet.
"""

from __future__ import annotations

import glob
import io
import os
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.curves import standard_name  # noqa: E402
from src.las_header import parse_header  # noqa: E402

CFG = yaml.safe_load((ROOT / "configs" / "default_config.yaml").read_text())
DATA = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser()
HEAD_BYTES = 256_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def _head(fobj) -> bytes:
    """Bytes up to the ~A line (or HEAD_BYTES), so the data section is never read in full."""
    buf = fobj.read(HEAD_BYTES)
    i = buf.find(b"\n~A")
    return buf if i < 0 else buf[:i + 1]


def one_zip(path: str) -> tuple[list[dict], list[dict]]:
    files, curves = [], []
    year = Path(path).stem
    zf = zipfile.ZipFile(path)

    def record(name: str, raw_head: bytes, size: int, nested: bool):
        row = {"archive": year, "entry": name, "file": Path(name).name, "size": size, "nested": nested, "ok": True, "error": ""}
        try:
            h = parse_header(raw_head)
            cs = h.pop("curves")
            row.update(h)
            for c in cs:
                curves.append({"archive": year, "file": Path(name).name, **c, "standard": standard_name(c["mnemonic"])})
        except Exception as e:                      # noqa: BLE001 — every failure is recorded, not hidden
            row.update(ok=False, error=repr(e)[:120])
        files.append(row)

    for info in zf.infolist():
        low = info.filename.lower()
        try:
            if low.endswith(".las"):
                with zf.open(info) as f:
                    record(info.filename, _head(f), info.file_size, False)
            elif low.endswith(".zip"):
                inner = zipfile.ZipFile(io.BytesIO(zf.read(info)))
                for ii in inner.infolist():
                    if ii.filename.lower().endswith(".las"):
                        with inner.open(ii) as f:
                            record(f"{info.filename}/{ii.filename}", _head(f), ii.file_size, True)
        except Exception as e:                      # noqa: BLE001 — a corrupt container is recorded too
            files.append({"archive": year, "entry": info.filename, "file": Path(info.filename).name, "size": info.file_size,
                          "nested": low.endswith(".zip"), "ok": False, "error": "container: " + repr(e)[:110]})
    return files, curves


def main(workers: int = 6) -> None:
    t0 = time.time()
    zips = sorted(glob.glob(str(DATA / CFG["paths"]["kgs_las_zips"] / "*.zip")), key=os.path.getsize, reverse=True)
    files, curves = [], []
    with ProcessPoolExecutor(workers) as ex:
        for z, (f, c) in zip(zips, ex.map(one_zip, zips)):
            files += f; curves += c
            log(f"{Path(z).name}: {len(f):,} files ({sum(not x['ok'] for x in f)} unreadable)")
    fdf, cdf = pd.DataFrame(files), pd.DataFrame(curves)
    idx = pd.read_csv(zipfile.ZipFile(DATA / CFG["paths"]["kgs_wells"].replace("ks_wells", "ks_las_files")).open("ks_las_files.txt"), dtype=str)
    idx["file"] = idx.URL.str.rsplit("/", n=1).str[-1]
    idx = idx.drop_duplicates("file").set_index("file")
    fdf["kgs_id"] = fdf.file.map(idx.KGS_ID)
    for col, src in (("lat", "Latitude"), ("lon", "Longitude")):
        fill = pd.to_numeric(fdf.file.map(idx[src]), errors="coerce")
        bad = fdf[col].isna() | ~fdf[col].between(-180, 180) | (fdf[col] == 0)
        fdf[f"{col}_source"] = (~bad).map({True: "header", False: "kgs_index"})
        fdf.loc[bad, col] = fill[bad]
    out = DATA / CFG["paths"]["derived"]; out.mkdir(parents=True, exist_ok=True)
    fdf.to_parquet(out / "kgs_files.parquet", index=False); cdf.to_parquet(out / "kgs_curves.parquet", index=False)
    log(f"{len(fdf):,} files, {int(fdf.ok.sum()):,} readable, {len(cdf):,} curve entries, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main(int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6)
