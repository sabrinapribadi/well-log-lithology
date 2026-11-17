"""Streamlit companion app (R26): a well's rock column, the Kansas transfer test, Kansas log quality on a map, and the agent chat.

Only what the static results page cannot do; numbers come from the public API or committed results (data/outputs).
Run: streamlit run app/streamlit_app.py   (theme in .streamlit/config.toml at the repository root)
"""
from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wl_data as D  # sibling module; the app runs from the repo root on Streamlit Cloud

st.set_page_config(page_title="Well-log lithology", layout="wide", initial_sidebar_state="collapsed")
INK = "#a8a49a"
st.html("""<style>
.eyebrow{font-size:.76rem;letter-spacing:.1em;text-transform:uppercase;font-weight:600;opacity:.65;margin:0}
.hero-title{font-family:'Barlow Condensed','Source Sans 3',system-ui,sans-serif;font-size:clamp(2.2rem,4.6vw,3.4rem);font-weight:700;line-height:1;margin:.2rem 0 .45rem}
.hero-sub{font-size:1.02rem;opacity:.8;max-width:72ch;margin:0 0 .4rem}
.brief-w{font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:#f0be6a;margin-bottom:.2rem}
.brief-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px;margin:.2rem 0 .3rem}
.bcard{border:1px solid #2e2c27;border-radius:10px;padding:8px 12px;font-size:.86rem;line-height:1.4;background:#151513}
.bcard a{color:#f0be6a}
</style>""")


@st.cache_data(ttl=3600, show_spinner=False)
def api(path: str) -> dict:
    return D.get(path)


def safe(path: str) -> dict | None:
    try:
        return api(path)
    except D.ApiError as err:
        st.warning(f"The live API did not answer ({err}). It may be waking up or paused on the free tier; try again in a minute, "
                   f"or read the [results page]({D.PAGES}), which is always on.")
        return None


@st.cache_data
def wells_df() -> pd.DataFrame:
    return pd.DataFrame(D.kansas_wells())


# 1. Hero, KPI strip and the brief (R22, R26 item 7)
h = D.headline()
st.html("""<p class="eyebrow">FORCE 2020 North Sea · 118 wells · Kansas LAS archive</p>
<h1 class="hero-title">Well-log lithology</h1>
<p class="hero-sub">Rock type every 0.152 m from well logs, scored on wells the model never saw, with the doubtful metres to review first.</p>""")
kp = st.columns(4)
kp[0].metric("Blind score, hidden wells", f"{h['hidden']:.3f}", "0 is perfect · 4th of 13", delta_color="off", delta_arrow="off", border=True)
kp[1].metric("Blind score, open wells", f"{h['open']:.3f}", "second check", delta_color="off", delta_arrow="off", border=True)
kp[2].metric("Beats the baseline", f"{h['seed_wins']} of 10 seeds", f"+{h['seed_gain']:.3f} on hidden wells", delta_color="off", delta_arrow="off", border=True)
kp[3].metric("Kansas units passed", "0 of 6", "lithology not validated", delta_color="off", delta_arrow="off", border=True)
items = D.brief()
st.html('<div class="brief-grid">' + "".join(f'<div class="bcard"><div class="brief-w">{w}</div><div>{D.md_html(lines[0])}</div></div>'
                                           for w, lines in items) + "</div>")
with st.expander("Full brief"):
    for w, lines in items:
        st.markdown(f"**{w}:** " + " ".join(lines))
st.caption(f"[Results page]({D.PAGES}) · [Technical walkthrough]({D.PAGES}build.html) · [Live API]({D.API}/docs) · [Source]({D.REPO}) · "
           f"Free Streamlit app: it sleeps after 12 hours without visits; the [results page]({D.PAGES}) is always on and carries every result.")

col_tab, unit_tab, ks_tab, agent_tab = st.tabs(["Well column", "Kansas transfer test", "Kansas log quality", "Ask the agent"],
                                               key="view", on_change="rerun")   # lazy: only the open tab runs

# 2. A FORCE test well's predicted column
with col_tab:
    if col_tab.open:
        root = safe("/")
        wells = (root or {}).get("force_wells") or ["15/9-23"]
        well = st.selectbox("FORCE test well", wells, index=wells.index("15/9-23") if "15/9-23" in wells else 0, key="well")
        d = safe(f"/wells/{D.q(well)}/lithology")
        if d and d.get("intervals"):
            iv = pd.DataFrame(d["intervals"])
            iv["doubtful"] = iv["probability"] < 0.5
            st.subheader(f"{well}: {d['split']} test well, blind score {d['blind_score']} (0 is perfect); matches the interpreter over "
                         f"{d['share_as_interpreted']:.0%} of logged depth; {d['doubtful_m']} m doubtful")
            left, right = st.columns([1, 1], gap="large")
            with left:
                rocks = [r for r in D.ROCK if r in set(iv["rock"])]
                y = alt.Y("top_m:Q", title="Depth (m)", scale=alt.Scale(reverse=True, domain=[float(iv["top_m"].min()), float(iv["base_m"].max())]))
                unit = alt.Scale(domain=[0, 1])
                col = alt.Chart(iv).mark_rect().encode(
                    x=alt.X("zero:Q", scale=unit, axis=None), x2="one:Q", y=y, y2="base_m:Q",
                    color=alt.Color("rock:N", scale=alt.Scale(domain=rocks, range=[D.ROCK[r] for r in rocks]), legend=alt.Legend(title=None, orient="top")),
                    tooltip=[alt.Tooltip("rock:N"), alt.Tooltip("top_m:Q", title="Top (m)"), alt.Tooltip("base_m:Q", title="Base (m)"),
                             alt.Tooltip("probability:Q", format=".2f")]
                ).transform_calculate(zero="0", one="1").properties(width=130, height=640, title="Predicted rock")
                prob = alt.Chart(iv).mark_rect(color="#e0a33a", opacity=0.8).encode(
                    x=alt.X("zero:Q", scale=unit, title="Probability", axis=alt.Axis(values=[0, 0.5, 1])), x2="probability:Q",
                    y=alt.Y("top_m:Q", scale=alt.Scale(reverse=True, domain=[float(iv["top_m"].min()), float(iv["base_m"].max())]), axis=None),
                    y2="base_m:Q", tooltip=[alt.Tooltip("probability:Q", format=".2f"), alt.Tooltip("top_m:Q", title="Top (m)")]
                ).transform_calculate(zero="0")
                half = alt.Chart(pd.DataFrame([{"x": 0.5}])).mark_rule(color=INK, strokeDash=[4, 3]).encode(x=alt.X("x:Q", scale=unit))
                st.altair_chart(alt.hconcat(col, (prob + half).properties(width=200, height=640, title="Probability (dashed: 0.5)"), spacing=12),
                                theme="streamlit")
                st.caption("Left: predicted rock (conventional lithology colours). Right: probability; the dashed line is 0.5, and intervals "
                           "short of it are doubtful.")
            with right:
                shares = pd.DataFrame([{"rock": r, "share": s} for r, s in d["rock_shares"].items()])
                st.markdown("**Rock shares of logged depth**")
                st.altair_chart(alt.Chart(shares).mark_bar(cornerRadiusEnd=4).encode(
                    y=alt.Y("rock:N", sort="-x", title=None), x=alt.X("share:Q", title=None, axis=alt.Axis(format="%")),
                    color=alt.Color("rock:N", scale=alt.Scale(domain=list(D.ROCK), range=list(D.ROCK.values())), legend=None),
                    tooltip=[alt.Tooltip("rock:N"), alt.Tooltip("share:Q", format=".1%")]).properties(height=36 * len(shares) + 20),
                    width="stretch", theme="streamlit")
                dz = iv[iv["doubtful"]].assign(metres=lambda x: (x["base_m"] - x["top_m"]).round(1)).sort_values("metres", ascending=False)
                st.markdown(f"**Where to review first: the {min(10, len(dz))} thickest doubtful intervals**")
                st.dataframe(dz.head(10)[["top_m", "base_m", "metres", "rock", "probability"]].rename(columns={
                    "top_m": "Top (m)", "base_m": "Base (m)", "metres": "Metres", "rock": "Predicted rock", "probability": "Probability"}),
                    hide_index=True, width="stretch")
                note = safe(f"/wells/{D.q(well)}/note")
                if note and note.get("note"):
                    st.markdown(f"**Planner note** ({'model-written, checked' if note.get('grounded') else 'template'}): {note['note']}")

# 3. Kansas transfer test by unit
with unit_tab:
    if unit_tab.open:
        rows = [r for r in (safe(f"/units/{D.q(u)}") for u in D.UNITS) if r and not r.get("not_found")]
        if rows:
            u = pd.DataFrame(rows)
            u["verdict"] = u.apply(lambda r: ("passes" if r["passed"] else "fails") if r["gated"] else "reported only", axis=1)
            st.subheader(f"No Kansas unit passed: {int(u['gated'].sum())} gated units, none met all three bars (30+ wells, median agreement "
                         "of at least 50%, lift of at least 2)")
            bars = alt.Chart(u).mark_bar(cornerRadiusEnd=4, color="#e0a33a").encode(
                y=alt.Y("unit:N", sort=None, title=None, axis=alt.Axis(labelLimit=220)),
                x=alt.X("median_agreement:Q", title="Median agreement with the unit's known rock",
                                                                   axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
                tooltip=["unit", "expected_rock", "wells_scored", alt.Tooltip("median_agreement:Q", format=".0%"), "lift", "verdict"])
            rule = alt.Chart(pd.DataFrame([{"x": 0.5}])).mark_rule(color=INK, strokeDash=[4, 3]).encode(x="x:Q")
            text = alt.Chart(u).mark_text(align="left", dx=6, color=INK).encode(
                y=alt.Y("unit:N", sort=None), x="median_agreement:Q", text=alt.Text("label:N")).transform_calculate(
                label="'lift ' + (datum.lift == null ? 'n/a' : format(datum.lift, '.2f')) + ' · ' + datum.verdict")
            st.altair_chart((bars + rule + text).properties(height=34 * len(u) + 30), width="stretch", theme="streamlit")
            pick = st.selectbox("What did the model predict inside a unit?", list(u["unit"]), key="unit")
            r = next(x for x in rows if x["unit"] == pick)
            mix = pd.DataFrame([{"rock": k, "share": v} for k, v in r["predicted_mix_inside"].items()])
            st.markdown(f"**{pick}** (expected {r['expected_rock']}; {r['wells_scored']} wells): predicted inside the unit")
            st.altair_chart(alt.Chart(mix).mark_bar(cornerRadiusEnd=4).encode(
                y=alt.Y("rock:N", sort="-x", title=None), x=alt.X("share:Q", title=None, axis=alt.Axis(format="%")),
                color=alt.Color("rock:N", scale=alt.Scale(domain=list(D.ROCK), range=list(D.ROCK.values())), legend=None),
                tooltip=["rock", alt.Tooltip("share:Q", format=".0%")]).properties(height=34 * len(mix) + 20), width="stretch", theme="streamlit")
            st.caption("Lift = share of the expected rock inside the unit ÷ the same share in the rest of those wells (ADR-005). "
                       "High agreement alone is not a pass: the model can call one rock almost everywhere.")

# 4. Kansas log quality: the archive on a map, and one well
with ks_tab:
    if ks_tab.open:
        w = wells_df()
        st.subheader(f"{len(w):,} Kansas LAS files with coordinates; {(w['curve_level'] >= 2).mean():.0%} have gamma ray, density and neutron")
        palette = {0: [110, 106, 98, 170], 1: [150, 96, 44, 200], 2: [224, 163, 58, 215], 3: [255, 238, 196, 235]}   # one light-to-bright scale
        w["fill"] = w["curve_level"].map(palette)
        w["logs"] = w["curve_level"].map(D.LEVELS)
        layer = pdk.Layer("ScatterplotLayer", data=w, get_position=["lon", "lat"], get_fill_color="fill", get_radius=900,
                          radius_min_pixels=1.5, radius_max_pixels=6, pickable=True)
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=pdk.ViewState(latitude=38.5, longitude=-98.4, zoom=5.6),
                                 tooltip={"html": "<b>{logs}</b><br/>archive {archive}"}, map_style=None), height=430)
        st.html('<div style="display:flex;gap:14px;flex-wrap:wrap;font-size:.85rem">' + "".join(
            f'<span><i style="display:inline-block;width:10px;height:10px;border-radius:50%;background:rgb({c[0]},{c[1]},{c[2]})"></i> '
            f'{D.LEVELS[k]} ({int((w["curve_level"] == k).sum()):,})</span>' for k, c in palette.items()) + "</div>")
        kid = st.text_input("Check one Kansas well by KGS ID", "1001184201", key="kgs")
        qd = safe(f"/kansas/{D.q(kid.strip())}/quality") if kid.strip() else None
        if qd and qd.get("not_found"):
            st.info(qd.get("detail", "Not in the archive inventory."))
        elif qd:
            m = st.columns(4)
            m[0].metric("Curves present", f"{len(qd['curves'])}", ", ".join(qd["curves"]) or "none", delta_color="off", delta_arrow="off", border=True)
            m[1].metric("Gamma-neutron-density coverage", f"{qd['coverage_gr_neutron_density']:.0%}", delta_arrow="off", border=True)
            m[2].metric("Values outside physical range", f"{qd['out_of_range_share']:.0%}", delta_arrow="off", border=True)
            m[3].metric("Hole condition", "unknown" if qd["bad_hole_share"] is None else f"{qd['bad_hole_share']:.0%} bad",
                        delta_arrow="off", border=True)
            st.warning(qd["caveat"])

# 5. The lithology agent: recorded answers by default, live only with the viewer's own key
with agent_tab:
    if agent_tab.open:
        import agent_tools as AT
        import chat
        st.markdown("Ask the lithology agent in plain words. It picks the tools (a well's column, a Kansas well's quality, a unit's "
                    "transfer result, a note), reads their results and answers; every number must come from a tool.")
        chat.render(st, Path(__file__).resolve().parent / "replays.json", AT)
