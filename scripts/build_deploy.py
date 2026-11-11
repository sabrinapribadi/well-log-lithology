"""Assemble the public deployment bundle (rules R19, R20; ADR-011).

    python scripts/build_deploy.py [--snapshot deploy/serving_snapshot.tar.gz] [--out build/deploy]
    python scripts/build_deploy.py --make-snapshot        # from WLL_DATA_DIR/serving (store + notes cache)

The bundle holds only the read-only serving code (src/serving), the config, the serving snapshot and a slim
requirements file (FastAPI, MCP, pydantic, PyYAML): no model files, no API key. `app.py` exposes the app for
Vercel's Python runtime. The snapshot's SHA-256 is checked against deploy/serving_snapshot.sha256.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "deploy" / "serving_snapshot.tar.gz"
SHA = ROOT / "deploy" / "serving_snapshot.sha256"
REQS = ["fastapi==0.143.0", "mcp==2.3.0", "pydantic>=2.7", "pyyaml>=6.0"]
SERVING = ["__init__.py", "contracts.py", "mcp_server.py", "notes.py", "public.py", "store.py", "tools.py"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def make_snapshot() -> None:
    src = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser() / "serving"
    SNAP.parent.mkdir(exist_ok=True)
    with tarfile.open(SNAP, "w:gz", compresslevel=9) as t:
        for f in ("store.json", "notes_cache.json"):
            if (src / f).exists():
                t.add(src / f, arcname=f"serving/{f}")
    SHA.write_text(sha256(SNAP) + "\n")
    print(f"{SNAP.relative_to(ROOT)} {SNAP.stat().st_size / 1e6:.1f} MB, sha256 {SHA.read_text().strip()[:12]}…")


def build(out: Path, snapshot: Path) -> None:
    if sha256(snapshot) != SHA.read_text().strip():
        raise SystemExit("serving snapshot does not match deploy/serving_snapshot.sha256")
    shutil.rmtree(out, ignore_errors=True)
    (out / "src" / "serving").mkdir(parents=True)
    (out / "src" / "__init__.py").write_text("")
    for f in SERVING:
        shutil.copy(ROOT / "src" / "serving" / f, out / "src" / "serving" / f)
    (out / "configs").mkdir()
    shutil.copy(ROOT / "configs" / "default_config.yaml", out / "configs" / "default_config.yaml")
    with tarfile.open(snapshot) as t:
        t.extractall(out, filter="data")
    (out / "requirements.txt").write_text("\n".join(REQS) + "\n")
    (out / "app.py").write_text('"""Vercel entrypoint."""\nfrom src.serving.public import app  # noqa: F401\n')
    (out / ".python-version").write_text("3.12\n")
    print(f"bundle at {out} ({sum(f.stat().st_size for f in out.rglob('*') if f.is_file()) / 1e6:.1f} MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-snapshot", action="store_true"); ap.add_argument("--snapshot", type=Path, default=SNAP)
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "deploy")
    a = ap.parse_args()
    make_snapshot() if a.make_snapshot else build(a.out, a.snapshot)
