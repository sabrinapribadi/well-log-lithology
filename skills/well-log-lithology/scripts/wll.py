"""Client for the public well-log lithology API (standard library only).

    python wll.py about                          # data, splits, model, scores and the time of this check (start here)
    python wll.py lithology WELL                 # predicted rock column of a FORCE test well, e.g. 15/9-23
    python wll.py quality KGS_ID                 # log quality of a Kansas well, e.g. 1001184201 (lithology not validated)
    python wll.py unit NAME                      # Kansas transfer test for a named unit, e.g. Heebner, 'Hutchinson Salt'
    python wll.py note WELL_OR_KGS_ID            # short grounded note for a well
    python wll.py chart column WELL [--out chart.html]   # strip log: rock by depth, probability, doubtful intervals
    python wll.py chart units [--out chart.html]         # Kansas units: median agreement and lift against the pass bars

Exit 0 on success, 1 on a network error. A 404 comes back as data ({"not_found": true, ...}).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_BASE = "https://well-log-lithology.vercel.app"
UNITS = ["Heebner", "Stone Corral", "Lansing-Kansas City", "Cherokee", "Mississippian", "Arbuckle", "Precambrian", "Hutchinson Salt"]
FACTS = {                                     # committed results (ADR-002, ADR-005, ADR-010); checked by scripts/skill_live_check.py
    "force": "FORCE 2020 North Sea: 118 wells with interpreted rock types (CC BY 4.0): 98 training, 10 open test, 10 hidden test",
    "model": "B: XGBoost with engineered features and a penalty-aware decision (chosen by well-grouped cross-validation, ADR-004)",
    "hidden_score": -0.504, "open_score": -0.521, "baseline_hidden": -0.540, "finalists_rank": "4th of 13 2020 finalists",
    "seeds": "beats the baseline on 10 of 10 seeds; mean +0.134 on the hidden wells (95% interval +0.055 to +0.213)",
    "score_meaning": "official FORCE penalty per 0.152 m sample on wells the model never saw; 0 is perfect, more negative is worse",
    "kansas": ("Kansas Geological Survey LAS archive: log quality only; lithology not validated "
               "(the transfer test failed, ADR-005; retests 3 of 6, ADR-013, and 2 of 6, ADR-014; 4 needed)"),
    "unit_gate": "a unit passes with at least 30 wells scored, median agreement >= 50% and lift >= 2",
}


def quote(x: str) -> str:
    return urllib.parse.quote(str(x), safe="")


def get(base: str, path: str, timeout: float = 60) -> dict:
    url = base.rstrip("/") + path
    req = urllib.request.Request(url, headers={"User-Agent": "well-log-lithology-skill/1.0", "Accept": "application/json"})
    last = None
    for attempt in range(2):                      # one retry covers a cold start
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"not_found": True, **json.loads(e.read().decode(errors="replace") or "{}")}
            if e.code < 500:
                raise SystemExit(f"HTTP {e.code} for {url}: {e.read().decode(errors='replace')[:300]}")
            last = e
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        time.sleep(3 * (attempt + 1))
    print(f"error: could not reach {url}: {last}", file=sys.stderr)
    sys.exit(1)


def about(base: str) -> dict:
    root = get(base, "/")
    return {"checked_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),  # noqa: UP017 - Python 3.8+
            **FACTS, "force_test_wells": root.get("force_wells"), "kansas_wells_in_inventory": root.get("kansas_wells"),
            "kansas_lithology_validated": root.get("kansas_lithology_validated"), "results_page": root.get("results_page")}


def data_line(ab: dict) -> str:
    return (f"Data: FORCE 2020 North Sea (118 wells; 10 hidden test wells score {FACTS['hidden_score']}, 0 is perfect) and the Kansas LAS "
            f"archive ({ab['kansas_wells_in_inventory']:,} wells, quality only); model B (XGBoost); checked {ab['checked_at_utc']} UTC.")


def make_chart(base: str, a: argparse.Namespace) -> Path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import charts
    ab = about(base)
    if a.what == "column":
        d = get(base, f"/wells/{quote(a.well)}/lithology")
        if d.get("not_found"):
            raise SystemExit(d.get("detail", "well not found"))
        page = charts.strip_log(d, f"Well {d['well']}: predicted rock by depth",
                                f"{d['split'].capitalize()} test well; blind score {d['blind_score']} (0 is perfect); matches the interpreter over "
                                f"{d['share_as_interpreted']:.0%} of logged depth; {d['doubtful_m']} m doubtful (probability below 0.5), hatched.",
                                data_line(ab))
    else:
        rows = [get(base, f"/units/{quote(u)}") for u in UNITS]
        page = charts.unit_bars([r for r in rows if not r.get("not_found")], "Kansas transfer test: did the model recognise each unit's rock?",
                                "A unit passes with median agreement of at least 50% and lift of at least 2 (ADR-005). None passed, so Kansas "
                                "lithology is not validated.", data_line(ab))
    out = Path(a.out).resolve()
    out.write_text(page, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default=DEFAULT_BASE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("about")
    sub.add_parser("lithology").add_argument("well")
    sub.add_parser("quality").add_argument("kgs_id")
    sub.add_parser("unit").add_argument("name")
    sub.add_parser("note").add_argument("well")
    ch = sub.add_parser("chart"); cs = ch.add_subparsers(dest="what", required=True)
    c1 = cs.add_parser("column"); c1.add_argument("well"); c1.add_argument("--out", default="chart.html")
    cs.add_parser("units").add_argument("--out", default="chart.html")
    a = ap.parse_args(argv)
    if a.cmd == "chart":
        print(f"chart written: {make_chart(a.base, a)}")
        return
    if a.cmd == "about":
        out = about(a.base)
    elif a.cmd == "lithology":
        out = get(a.base, f"/wells/{quote(a.well)}/lithology")
    elif a.cmd == "quality":
        out = get(a.base, f"/kansas/{quote(a.kgs_id)}/quality")
    elif a.cmd == "unit":
        out = get(a.base, f"/units/{quote(a.name)}")
    else:
        out = get(a.base, f"/wells/{quote(a.well)}/note")
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
