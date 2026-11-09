"""P2b candidate D (ADR-009): a 1D convolutional network over 33-sample depth windows (± 2.4 m), within each well.

    python scripts/p2b_cnn.py

Inputs: P1's per-sample inputs (20 logs, position, group and formation codes), standardised on training wells, missing
→ 0 plus a missing flag per log. Three conv layers (64 filters, kernel 5), centre + window average → 12 classes.
Adam 1e-3, batch 2,048, 6 epochs, seed 42, no early stopping; expected-penalty decision. Same 5-fold well-grouped CV
as P2, then fitted on all training wells and scored once on the open and hidden wells.
Writes data/outputs/p2b_cnn.json. Data are loaded before torch is imported (avoids a known loader deadlock).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import os  # noqa: E402

import yaml  # noqa: E402

from src.features import LOGS, baseline_matrix, expected_penalty_decision, labels, strat_codes  # noqa: E402
from src.scoring import penalty_score, report  # noqa: E402

# no XGBoost or LightGBM in this process: their OpenMP runtime crashes alongside PyTorch
CFG = yaml.safe_load((ROOT / "configs" / "default_config.yaml").read_text())
DER = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser() / CFG["paths"]["derived"]

HALF, EPOCHS, BATCH, LR, SEED = 16, 6, 2048, 1e-3, 42
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def arrays(d: pd.DataFrame, codes: dict, stats: tuple | None = None):
    """Channels (N × C) and well boundaries for each row; d must be sorted by WELL, DEPTH_MD."""
    X = baseline_matrix(d, codes)
    if stats is None:
        stats = (X.mean().to_numpy(), X.std().replace(0, 1).fillna(1).to_numpy())
    Z = ((X - stats[0]) / stats[1]).fillna(0).to_numpy(np.float32)
    flags = X[LOGS].isna().to_numpy(np.float32)
    w = d.WELL.to_numpy()
    first = np.r_[0, np.flatnonzero(w[1:] != w[:-1]) + 1]
    last = np.r_[first[1:], len(w)]
    start, end = np.repeat(first, last - first), np.repeat(last, last - first)
    return np.concatenate([Z, flags], axis=1), start, end, stats


def main() -> None:
    global EPOCHS
    smoke = "--smoke" in sys.argv          # one epoch on 10 training wells; no test wells, nothing written
    t0 = time.time()
    sort = lambda d: d.sort_values(["WELL", "DEPTH_MD"]).reset_index(drop=True)
    tr, ot, hd = (sort(pd.read_parquet(DER / f"force_{k}.parquet")) for k in ("train", "open_test", "hidden_test"))
    if smoke:
        tr, EPOCHS = sort(tr[tr.WELL.isin(sorted(tr.WELL.unique())[:10])]), 1
    codes = strat_codes(tr)
    y, g = labels(tr), tr.WELL.to_numpy()

    import torch  # after the data are in memory
    from torch import nn
    dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    offs = torch.arange(-HALF, HALF + 1)

    class Net(nn.Module):
        def __init__(self, c: int):
            super().__init__()
            layers, k = [], c
            for _ in range(3):
                layers += [nn.Conv1d(k, 64, 5, padding=2), nn.BatchNorm1d(64), nn.ReLU()]; k = 64
            self.conv, self.head = nn.Sequential(*layers), nn.Linear(128, 12)

        def forward(self, x):
            h = self.conv(x)
            return self.head(torch.cat([h[:, :, HALF], h.mean(2)], 1))

    def windows(Xt, st, en, idx):
        j = idx[:, None] + offs[None, :]
        ok = (j >= st[idx][:, None]) & (j < en[idx][:, None])
        w = Xt[j.clamp(0, len(Xt) - 1)] * ok[..., None]
        return w.permute(0, 2, 1).contiguous()

    def fit(Xa, sa, ea, ya, rows):
        torch.manual_seed(SEED)
        Xt, st, en = torch.from_numpy(Xa), torch.from_numpy(sa), torch.from_numpy(ea)
        yt, net = torch.from_numpy(ya.astype(np.int64)), Net(Xa.shape[1]).to(dev)
        opt, loss_fn = torch.optim.Adam(net.parameters(), lr=LR), nn.CrossEntropyLoss()
        gen = torch.Generator().manual_seed(SEED)
        rows = torch.from_numpy(rows)
        for ep in range(EPOCHS):
            net.train(); perm = rows[torch.randperm(len(rows), generator=gen)]; tot = 0.0
            for b in range(0, len(perm), BATCH):
                idx = perm[b:b + BATCH]
                xb, yb = windows(Xt, st, en, idx).to(dev), yt[idx].to(dev)
                opt.zero_grad(); loss = loss_fn(net(xb), yb); loss.backward(); opt.step(); tot += loss.item() * len(idx)
            log(f"  epoch {ep + 1}/{EPOCHS} loss {tot / len(perm):.4f}")
        return net

    @torch.no_grad()
    def proba(net, Xa, sa, ea):
        net.eval(); Xt, st, en = torch.from_numpy(Xa), torch.from_numpy(sa), torch.from_numpy(ea)
        out = [torch.softmax(net(windows(Xt, st, en, torch.arange(b, min(b + 8192, len(Xa)))).to(dev)), 1).cpu() for b in range(0, len(Xa), 8192)]
        return torch.cat(out).numpy()

    cv = []
    for fold, (a, b) in enumerate(GroupKFold(n_splits=5).split(tr, y, g)):
        stats = arrays(tr.iloc[a].reset_index(drop=True), codes)[3]          # standardise on the fold's training wells only
        Xa, sa, ea, _ = arrays(tr, codes, stats)
        net = fit(Xa, sa, ea, y, a.astype(np.int64))                          # windows never cross wells, so held-out rows stay unseen
        p = proba(net, Xa, sa, ea)[b]
        cv.append(penalty_score(y[b], expected_penalty_decision(p)))
        log(f"fold {fold + 1}/5 {cv[-1]:.4f}")
        if smoke:
            log(f"smoke run ok in {time.time() - t0:.0f} s on {dev}"); return
    Xa, sa, ea, stats = arrays(tr, codes)
    net = fit(Xa, sa, ea, y, np.arange(len(tr), dtype=np.int64))
    res = {"design": "ADR-009 D", "device": str(dev), "torch": torch.__version__, "window_samples": 2 * HALF + 1, "epochs": EPOCHS,
           "channels": int(Xa.shape[1]), "cv_folds": cv, "cv_mean": float(np.mean(cv))}
    for name, d in (("open_test", ot), ("hidden_test", hd)):
        Xd, sd, ed, _ = arrays(d, codes, stats)
        res[name] = report(labels(d), expected_penalty_decision(proba(net, Xd, sd, ed)), d.WELL.to_numpy())
        log(name, round(res[name]["penalty_score"], 4))
    res["seconds"] = round(time.time() - t0)
    (ROOT / CFG["paths"]["outputs_dir"] / "p2b_cnn.json").write_text(json.dumps(res, indent=1))
    log(f"D CV {res['cv_mean']:.4f}; hidden {res['hidden_test']['penalty_score']:.4f}")


if __name__ == "__main__":
    main()
