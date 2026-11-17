"""Self-contained HTML/SVG charts for the well-log skill (standard library only; no external scripts). Shared design with the
portfolio's other skills: light and dark tokens, hover/focus tooltips, a table view under every chart.

- strip_log: rock column by depth with doubtful intervals hatched, and a probability track.
- unit_bars: Kansas units, median agreement against the 50% pass line, with lift and the verdict printed.
"""
from __future__ import annotations

import html

CSS = """
:root{--surface:#fcfcfb;--page:#f9f9f7;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;
--c1:#2a78d6;--c2:#eb6834;--c3:#1baf7a;--ctx:#c3c2b7;--pos:#e34948;--neg:#2a78d6;--ring:rgba(11,11,11,.10);color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--surface:#1a1a19;--page:#0d0d0d;--ink:#f0efec;--ink2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--axis:#383835;--c1:#3987e5;--c2:#d95926;--c3:#199e70;--ctx:#52514e;--pos:#e66767;--neg:#3987e5;--ring:rgba(255,255,255,.10);color-scheme:dark}}
:root[data-theme=dark]{--surface:#1a1a19;--page:#0d0d0d;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;
--c1:#3987e5;--c2:#d95926;--c3:#199e70;--ctx:#52514e;--pos:#e66767;--neg:#3987e5;--ring:rgba(255,255,255,.10);color-scheme:dark}
body{margin:0;background:var(--page);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
.card{max-width:860px;margin:16px auto;padding:18px 20px;background:var(--surface);border:1px solid var(--ring);border-radius:10px}
h1{font-size:18px;margin:0 0 4px;text-wrap:balance}.sub{color:var(--ink2);margin:0 0 12px}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--ink2);margin:0 0 6px}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
svg{width:100%;height:auto;display:block}svg text{fill:var(--ink2);font-size:12px}svg .val{fill:var(--ink);font-variant-numeric:tabular-nums}
svg .lab{fill:var(--ink)}svg rect.bar{cursor:default;outline:none}svg rect.bar:focus,svg rect.bar:hover{stroke:var(--ink);stroke-width:1.5}
.tip{position:fixed;pointer-events:none;background:var(--surface);color:var(--ink);border:1px solid var(--ring);border-radius:6px;
padding:6px 8px;font-size:12.5px;box-shadow:0 2px 8px rgba(0,0,0,.12);display:none;max-width:280px}
details{margin-top:10px;font-size:13px}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:4px 8px;border-bottom:1px solid var(--grid);text-align:left}td.n,th.n{text-align:right}
.foot{color:var(--muted);font-size:12px;margin-top:10px}
"""

JS = """<script>
const tip=document.querySelector('.tip');
function show(e,t){tip.innerHTML=t;tip.style.display='block';const r=e.target.getBoundingClientRect();
tip.style.left=Math.min(window.innerWidth-290,(e.clientX||r.right)+12)+'px';tip.style.top=((e.clientY||r.top)+12)+'px';}
document.querySelectorAll('rect.bar').forEach(b=>{const t=b.dataset.tip;
b.addEventListener('mousemove',e=>show(e,t));b.addEventListener('focus',e=>show(e,t));
['mouseleave','blur'].forEach(ev=>b.addEventListener(ev,()=>tip.style.display='none'));});
</script>"""


def _fmt(v: float) -> str:
    return f"{v:,.0f}"


def _page(title: str, sub: str, legend: list[tuple[str, str]], svg: str, table: str, foot: str) -> str:
    leg = "".join(f'<span><span class="sw" style="background:var({c})"></span>{html.escape(n)}</span>' for n, c in legend)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class=\"card\"><h1>{html.escape(title)}</h1>"
            f'<p class="sub">{html.escape(sub)}</p>{f"<div class=legend>{leg}</div>" if legend else ""}{svg}'
            f"<details><summary>Table view</summary>{table}</details><p class=\"foot\">{html.escape(foot)}</p></div>"
            f'<div class="tip" role="tooltip"></div>{JS}</body></html>')


# Conventional lithology colours (petrophysics practice), so a geologist reads the column at a glance; legend and table always shown.
ROCK = {"Sandstone": "#e8c547", "Sandstone/Shale": "#c2ad6e", "Shale": "#6f8f72", "Marl": "#9fc4a5", "Dolomite": "#a77fb8",
        "Limestone": "#4f9bd9", "Chalk": "#cfe0ea", "Halite": "#e59ab8", "Anhydrite": "#c48ad8", "Tuff": "#d9774f", "Coal": "#2b2b2b",
        "Basement": "#a8432f"}


def strip_log(d: dict, title: str, sub: str, foot: str) -> str:
    """Strip log: rock column by depth (doubtful intervals hatched) and a probability track; legend with each rock's share."""
    iv = d["intervals"]
    top, base = min(i["top_m"] for i in iv), max(i["base_m"] for i in iv)
    w, h, t, b = 820, 720, 10, 30
    Y = lambda z: t + (h - t - b) * (z - top) / ((base - top) or 1)  # noqa: E731
    cx, cw, px, pw = 120, 150, 320, 260
    parts = ['<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             '<line x1="0" y1="0" x2="0" y2="6" stroke="var(--ink)" stroke-width="1.4" stroke-opacity="0.55"/></pattern></defs>']
    for i in iv:
        y0, y1 = Y(i["top_m"]), Y(i["base_m"])
        hh = max(y1 - y0, 0.6)
        tip = html.escape(f"<b>{i['rock']}</b><br>{i['top_m']}–{i['base_m']} m<br>probability {i['probability']:.2f}"
                          + ("<br>doubtful: review first" if i["probability"] < 0.5 else ""), quote=True)
        parts.append(f'<rect class="bar" tabindex="0" x="{cx}" y="{y0:.2f}" width="{cw}" height="{hh:.2f}" fill="{ROCK.get(i["rock"], "#888")}" data-tip="{tip}"/>')
        if i["probability"] < 0.5:
            parts.append(f'<rect x="{cx}" y="{y0:.2f}" width="{cw}" height="{hh:.2f}" fill="url(#hatch)" pointer-events="none"/>')
        parts.append(f'<rect x="{px}" y="{y0:.2f}" width="{pw * i["probability"]:.1f}" height="{hh:.2f}" fill="var(--c1)" fill-opacity="0.55" pointer-events="none"/>')
    for k in range(6):
        z = top + (base - top) * k / 5
        parts.append(f'<line x1="{cx - 6}" y1="{Y(z):.1f}" x2="{cx}" y2="{Y(z):.1f}" stroke="var(--axis)"/>'
                     f'<text x="{cx - 10}" y="{Y(z) + 4:.1f}" text-anchor="end">{z:,.0f} m</text>')
    parts.append(f'<line x1="{px + pw / 2:.1f}" y1="{t}" x2="{px + pw / 2:.1f}" y2="{h - b}" stroke="var(--c2)" stroke-dasharray="4 3"/>')
    parts += [f'<text x="{cx + cw / 2}" y="{h - 8}" text-anchor="middle">Predicted rock</text>',
              f'<text x="{px + pw / 2}" y="{h - 8}" text-anchor="middle">Probability (dashed: 0.5)</text>']
    svg = f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}">{"".join(parts)}</svg>'
    shares = sorted(d["rock_shares"].items(), key=lambda kv: -kv[1])
    def share(s: float) -> str:
        return f"{s:.0%}" if s >= 0.01 else "&lt;1%"
    legend = "".join(f'<span><span class="sw" style="background:{ROCK.get(r, "#888")}"></span>{html.escape(r)} {share(s)}</span>' for r, s in shares)
    legend += '<span><span class="sw" style="background:repeating-linear-gradient(45deg,#888 0 2px,transparent 2px 5px)"></span>doubtful</span>'
    doubt = [i for i in iv if i["probability"] < 0.5][:30]
    table = ("<table><tr><th>Rock</th><th class=n>Share of logged depth</th></tr>"
             + "".join(f"<tr><td>{html.escape(r)}</td><td class=n>{s:.1%}</td></tr>" for r, s in shares)
             + "</table><p>First doubtful intervals (probability below 0.5):</p><table><tr><th>Top (m)</th><th>Base (m)</th><th>Rock</th>"
               "<th class=n>Probability</th></tr>"
             + "".join(f"<tr><td>{i['top_m']}</td><td>{i['base_m']}</td><td>{html.escape(i['rock'])}</td><td class=n>{i['probability']:.2f}</td></tr>" for i in doubt)
             + "</table>")
    page = _page(title, sub, [], svg, table, foot)
    return page.replace('<svg viewBox', f'<div class="legend">{legend}</div><svg viewBox', 1)


def unit_bars(rows: list[dict], title: str, sub: str, foot: str) -> str:
    """Kansas units: median agreement (bar, 50% pass line) with lift and the verdict printed; ungated units marked."""
    lw, w, bh, rh = 230, 820, 16, 34
    plot = w - lw - 250
    X = lambda v: lw + plot * v  # noqa: E731
    parts = []
    for k, r in enumerate(rows):
        y = 8 + k * rh
        ag = r.get("median_agreement") or 0.0
        lift = r.get("lift")
        label = f"{r['unit']} ({r['expected_rock']})" + ("" if r.get("gated") else " *")
        verdict = ("passes" if r.get("passed") else "fails") if r.get("gated") else "reported only"
        tip = html.escape(f"<b>{r['unit']}</b><br>expected {r['expected_rock']}<br>median agreement {ag:.0%} (needs 50%)<br>"
                          f"lift {lift if lift is not None else 'n/a'} (needs 2)<br>{r['wells_scored']} wells; {verdict}", quote=True)
        parts.append(f'<text class="lab" x="{lw - 10}" y="{y + bh - 3}" text-anchor="end">{html.escape(label)}</text>')
        parts.append(f'<rect class="bar" tabindex="0" x="{lw}" y="{y}" width="{max(2, plot * ag):.1f}" height="{bh}" rx="3" fill="var(--c1)" data-tip="{tip}"/>')
        parts.append(f'<text class="val" x="{X(max(ag, 0.0)) + 6:.1f}" y="{y + bh - 3}">{ag:.0%} · lift {lift if lift is not None else "n/a"} · {verdict}</text>')
    hgt = 8 + len(rows) * rh
    parts.append(f'<line x1="{X(0.5):.1f}" y1="0" x2="{X(0.5):.1f}" y2="{hgt}" stroke="var(--c2)" stroke-dasharray="4 3"/>'
                 f'<text x="{X(0.5) + 4:.1f}" y="{hgt + 14}" style="fill:var(--c2)">50% pass line</text>')
    svg = (f'<svg viewBox="0 0 {w} {hgt + 22}" role="img" aria-label="{html.escape(title)}">'
           f'<line x1="{lw}" y1="0" x2="{lw}" y2="{hgt}" stroke="var(--axis)"/>{"".join(parts)}</svg>')
    head = ("<tr><th>Unit</th><th>Expected rock</th><th class=n>Wells</th><th class=n>Median agreement</th>"
            "<th class=n>Lift</th><th>Gated</th><th>Passed</th></tr>")
    table = ("<table>" + head
             + "".join(f"<tr><td>{html.escape(r['unit'])}</td><td>{html.escape(r['expected_rock'])}</td><td class=n>{r['wells_scored']}</td>"
                       f"<td class=n>{(r.get('median_agreement') or 0):.1%}</td><td class=n>{r.get('lift')}</td>"
                       f"<td>{r.get('gated')}</td><td>{r.get('passed')}</td></tr>" for r in rows)
             + "</table><p>* reported, not gated (ADR-005).</p>")
    return _page(title, sub, [("Median agreement", "--c1")], svg, table, foot)
