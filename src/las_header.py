"""LAS header parser (ADR-003 E3): reads the ~V, ~W and ~C sections of a LAS 1.2 / 2.0 file, stopping at ~A.

LAS lines look like  `MNEM.UNIT   VALUE : DESCRIPTION`. In LAS 1.2 files the well-information value is often written
in the description field instead, so for ~W the value falls back to the description when the value is empty.
Only the header is read (the data section is skipped), so a 50 MB file costs a few kilobytes.
"""

from __future__ import annotations

import re

LINE = re.compile(r"^\s*([^.\s][^.]*?)\s*\.(\S*)\s+(.*?)\s*:\s*(.*?)\s*$")
LINE_NOUNIT = re.compile(r"^\s*([^.\s][^.]*?)\s*\.\s*(.*?)\s*:\s*(.*?)\s*$")


def _parse_line(s: str) -> tuple[str, str, str, str] | None:
    m = LINE.match(s)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), m.group(4).strip()
    m = LINE_NOUNIT.match(s)
    if m:
        return m.group(1).strip(), "", m.group(2).strip(), m.group(3).strip()
    return None


def _num(v: str) -> float | None:
    try:
        return float(v.replace(",", "").split()[0])
    except (ValueError, IndexError, AttributeError):
        return None


def parse_header(raw: bytes) -> dict:
    """Header fields and curve list of one LAS file. Raises ValueError when no ~C section is found."""
    text = raw.decode("latin-1", errors="replace")
    sections: dict[str, list[str]] = {}
    cur = None
    for line in text.splitlines():
        st = line.strip()
        if not st or st.startswith("#"):
            continue
        if st.startswith("~"):
            cur = st[1:2].upper()
            if cur == "A":
                break
            sections.setdefault(cur, [])
            continue
        if cur:
            sections[cur].append(line)
    if "C" not in sections:
        raise ValueError("no ~C (curve) section")
    ver = {}
    for s in sections.get("V", []):
        p = _parse_line(s)
        if p:
            ver[p[0].upper()] = p[2] or p[3]
    well = {}
    for s in sections.get("W", []):
        p = _parse_line(s)
        if p:
            mn, unit, val, desc = p
            well[mn.upper()] = (unit, val if val else desc)
    curves = []
    for s in sections["C"]:
        p = _parse_line(s)
        if p:
            curves.append({"mnemonic": p[0], "unit": p[1], "description": p[3] or p[2]})
    g = lambda k: well.get(k, ("", ""))[1]
    strt, stop, step = _num(g("STRT")), _num(g("STOP")), _num(g("STEP"))
    null = _num(g("NULL"))
    return {"version": (ver.get("VERS") or "").split()[0] if ver.get("VERS") else "", "wrap": (ver.get("WRAP") or "").split()[0].upper() if ver.get("WRAP") else "",
            "null": null, "strt": strt, "stop": stop, "step": step, "depth_unit": well.get("STRT", ("", ""))[0].upper(),
            "api": g("API") or g("UWI"), "lat": _num(g("LAT") or g("LATI")), "lon": _num(g("LON") or g("LONG")),
            "well": g("WELL"), "company": g("COMP"), "county": g("CNTY"), "n_curves": len(curves), "curves": curves}
