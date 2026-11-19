"""Streamlit companion app (R26, app template v2): overview, the data, a well review, a Kansas log check, the transfer test, the agent.

Only what the static results page cannot do; numbers come from the public API or committed results (data/outputs).
Run: streamlit run app/streamlit_app.py   (theme in .streamlit/config.toml at the repository root)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import frame as F  # noqa: E402  shared app frame (identical in every portfolio app)
import wl_data as D  # noqa: E402  sibling module; the app runs from the repo root on Streamlit Cloud

st.set_page_config(page_title="Well-log lithology", page_icon=":material/layers:", layout="wide", initial_sidebar_state="expanded")
INK = "#a8a49a"
F.setup(st, accent="#f0be6a", title_font="'Barlow Condensed','Source Sans 3',system-ui,sans-serif")

PAGES = [
    F.Page("overview", "Overview", ":material/home:", "The results, the brief and where to start."),
    F.Page("explore", "Explore the data", ":material/query_stats:",
           "What the model learned from (FORCE 2020: rock mix, missing logs, splits) and how complete the Kansas archive is, by year and on a map."),
    F.Page("well", "Review a well", ":material/vertical_split:",
           "Any of the 20 test wells the model never saw: predicted rock by depth, probability, and the thickest doubtful intervals to review first."),
    F.Page("quality", "Check a Kansas log", ":material/fact_check:",
           "Any Kansas well by KGS ID: which logs it holds, gamma-neutron-density coverage, values outside physical ranges, hole condition."),
    F.Page("transfer", "Kansas transfer test", ":material/rule:",
           "Did the model recognise each named Kansas unit's rock? Median agreement and lift against bars set before any prediction."),
    F.Page("agent", "AI Assistant", ":material/smart_toy:",
           "Ask in plain words: recorded answers replay for free with their tool calls; your own OpenAI key runs it live."),
]


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


def retest(r: dict) -> None:
    """P3b (ADR-013): every arm under both gates, scored once on fresh wells (committed result)."""
    st.subheader(f"The retest (P3b): {r['arms']['M1a']['passed_amended']} of 6 on {r['files']} fresh files, short of 4")
    names = {"C": "P3 model, reader fixed (control)", "M0": "Physics rules, no training", "M1a": "Model with physics features (primary)",
             "M1b": "Same, without raw density and neutron", "M2": "Primary plus rock-mix correction"}
    st.dataframe(pd.DataFrame([{"Method": names[a], "Original gate": v["passed_original"], "Amended gate": v["passed_amended"],
                                "Passed (amended)": ", ".join(u for u, x in v["units"].items() if x["gated"] and x["amended"]["passed"]) or "none"}
                               for a, v in r["arms"].items() if a in names]), hide_index=True, width="stretch")
    st.caption("Pre-registered in ADR-013 before modelling; scored once. Amended gate: good-quality samples only, and lift against the 30 m above "
               "and below a unit. A reader bug (density correction read as density, about 1 well in 10) was fixed first. Physics rules recognise "
               "the carbonates; every North Sea-trained model still calls them sandstone.")


def retest_p3c(r: dict) -> None:
    """P3c (ADR-014): the combined arm M3 on new fresh wells, scored once (committed result)."""
    st.subheader(f"The second retest (P3c): {r['arms']['M3']['passed_amended']} of 6 on {r['files']} new fresh files, short of 4")
    st.dataframe(pd.DataFrame([{"Method": n, "Amended gate": r["arms"][a]["passed_amended"],
                                "Passed": ", ".join(u for u, x in r["arms"][a]["units"].items() if x["gated"] and x["amended"]["passed"]) or "none"}
                               for a, n in (("M3", "Physics-feature model + physics rules for carbonates (primary)"), ("C", "P3 model, reader fixed (control)"),
                                            ("M0", "Physics rules, no training"), ("M1a", "Model with physics features")) if a in r["arms"]]),
                 hide_index=True, width="stretch")
    st.caption("Pre-registered in ADR-014 before scoring, on wells no earlier test had used. The combined arm passed the same units as the control; "
               "P3b's Cherokee pass did not replicate. Kansas needs core-based labels, not another rule.")


@st.cache_data
def committed(name: str) -> dict:
    return json.loads((D.OUT / name).read_text())


@st.cache_data
def wells_df() -> pd.DataFrame:
    return pd.DataFrame(D.kansas_wells())


@st.cache_data
def training_rocks() -> pd.DataFrame:
    """Training samples per rock type: FORCE codes from the config, in the order of the colour map."""
    codes = yaml.safe_load((D.ROOT / "configs" / "default_config.yaml").read_text())["lithology_codes"]
    names = list(D.ROCK)
    counts = committed("p0_force.json")["class_counts_train"]
    df = pd.DataFrame([{"rock": names[codes[int(c)]], "samples": n} for c, n in counts.items()])
    return df.assign(share=df["samples"] / df["samples"].sum()).sort_values("samples", ascending=False)


h = D.headline()
units = committed("p3_kansas_transfer.json")
p3b = committed("p3b_test.json")
p3c = committed("p3c_test.json")
page = F.navigate(st, PAGES, brand="Well-log lithology", tagline="Rock type from well logs, checked on unseen wells", icon="◧")
F.sidebar_stats(st, [(f"{h['hidden']:.3f}", "blind score, hidden wells (0 is perfect)"), ("4th of 13", "level among 2020 finalists"),
                     ("118", "North Sea wells (FORCE 2020)"), (f"{len(wells_df()):,}", "Kansas logs on the map")])


def footer() -> None:
    F.sidebar_footer(st, {"Results page": D.PAGES, "Walkthrough": D.PAGES + "build.html", "Live API": D.API + "/docs", "Source": D.REPO,
                          "Agent skill": D.REPO + "/tree/main/skills/well-log-lithology"},
                     "Data: FORCE 2020 North Sea (CC BY 4.0, interpreted rock types) and the Kansas Geological Survey LAS archive.")


# 1. Overview: hero, KPI strip, the 5W1H brief and a card per page (R22, R26 item 7)
if page.key == "overview":
    footer()
    F.hero(st, "FORCE 2020 North Sea · 118 wells · Kansas LAS archive", "Well-log lithology",
           "Rock type every 0.152 m from well logs, scored on wells the model never saw, with the doubtful metres to review first.")
    F.kpis(st, [("Blind score, hidden wells", f"{h['hidden']:.3f}", "0 is perfect · 4th of 13"),
                ("Blind score, open wells", f"{h['open']:.3f}", "second check"),
                ("Beats the baseline", f"{h['seed_wins']} of 10 seeds", f"+{h['seed_gain']:.3f} on hidden wells"),
                ("Kansas units passed", f"{units['units_passed']} of {units['units_gated']}", "lithology not validated")])
    F.brief(st, F.load_brief(D.ROOT, D.REPO))
    F.links_line(st, {"Results page": D.PAGES, "Technical walkthrough": D.PAGES + "build.html", "Live API": D.API + "/docs", "Source": D.REPO})
    F.use_cards(st, PAGES)

# 2. Explore the data: FORCE training wells and the Kansas archive
elif page.key == "explore":
    footer()
    force, q4, rocks = committed("p0_force.json"), committed("p4_quality.json"), training_rocks()
    tr = force["splits"]["train"]
    miss = pd.DataFrame([{"log": k, "missing": v} for k, v in force["checks"]["curve_missing_share_train"].items()]).sort_values("missing", ascending=False)
    yr = pd.DataFrame(q4["by_year"])
    none_before = yr[yr["coverage"] == 0]["archive"].tolist()
    late = yr[yr["archive"].str[:4].astype(int) >= 2015]
    F.header(st, page, "What does the model learn from, and how usable are the Kansas logs it would be applied to?",
             f"{tr['wells']} training wells, {tr['samples']:,} samples: **shale is {rocks.iloc[0]['share']:.0%}** of them and "
             f"{int((rocks['share'] < 0.01).sum())} of {len(rocks)} rock types are under 1% each, so rare rocks are hard. "
             f"{miss.iloc[0]['log']} is missing in {miss.iloc[0]['missing']:.0%} of samples. In Kansas, the "
             f"{len(none_before)} archives from {none_before[0]} to {none_before[-1].split('_')[-1]} have no gamma-neutron-density coverage "
             f"(median); {int((late['coverage'] >= 0.9).sum())} of {len(late)} archives from 2015 on are above 90%.")
    st.subheader("FORCE 2020 North Sea: the training data")
    m = st.columns(4)
    m[0].metric("Training wells", f"{tr['wells']}", f"{force['splits']['open_test']['wells']} open + {force['splits']['hidden_test']['wells']} hidden test",
                delta_color="off", delta_arrow="off", border=True)
    m[1].metric("Training samples", f"{tr['samples']:,}", "one every 0.152 m", delta_color="off", delta_arrow="off", border=True)
    m[2].metric("Rock types", f"{tr['classes_present']}", "interpreted by geologists", delta_color="off", delta_arrow="off", border=True)
    m[3].metric("Wells in two splits", "0" if force["checks"]["no_well_in_two_splits"] else "some", "no leakage across splits",
                delta_color="off", delta_arrow="off", border=True)
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("**Rock mix of the training samples**")
        log_x = st.toggle("Log scale (shows the rare rocks)", False, key="logx")
        st.altair_chart(alt.Chart(rocks).mark_bar(cornerRadiusEnd=4).encode(
            y=alt.Y("rock:N", sort="-x", title=None),
            x=alt.X("samples:Q", title="Samples", scale=alt.Scale(type="log") if log_x else alt.Scale(), axis=alt.Axis(format="~s")),
            color=alt.Color("rock:N", scale=alt.Scale(domain=list(D.ROCK), range=list(D.ROCK.values())), legend=None),
            tooltip=["rock", alt.Tooltip("samples:Q", format=","), alt.Tooltip("share:Q", format=".2%")]
        ).properties(height=30 * len(rocks) + 20), width="stretch", theme="streamlit")
    with b:
        st.markdown("**Share of training samples missing each log**")
        st.altair_chart(alt.Chart(miss).mark_bar(cornerRadiusEnd=4, color="#e0a33a").encode(
            y=alt.Y("log:N", sort="-x", title=None), x=alt.X("missing:Q", title="Missing", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
            tooltip=["log", alt.Tooltip("missing:Q", format=".1%")]).properties(height=30 * len(miss) + 20), width="stretch", theme="streamlit")
        st.caption("Gamma ray (GR) is never missing; shear sonic (DTS) almost always is, so the model cannot lean on it.")

    st.subheader("Kansas LAS archive: what the model would be applied to")
    years = yr["archive"].tolist()
    lo, hi = st.select_slider("Archive years", years, value=(years[0], years[-1]), key="years")
    pick = years[years.index(lo):years.index(hi) + 1]
    yv = yr[yr["archive"].isin(pick)]
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**Files per archive year**")
        st.altair_chart(alt.Chart(yv).mark_bar(cornerRadiusEnd=3, color="#9a8f7a").encode(
            x=alt.X("archive:N", title=None, sort=years), y=alt.Y("files:Q", title="Files"),
            tooltip=["archive", alt.Tooltip("files:Q", format=",")]).properties(height=260), width="stretch", theme="streamlit")
    with c2:
        st.markdown("**Median share of depth with gamma ray, neutron and density**")
        st.altair_chart(alt.Chart(yv).mark_bar(cornerRadiusEnd=3, color="#e0a33a").encode(
            x=alt.X("archive:N", title=None, sort=years), y=alt.Y("coverage:Q", title="Coverage", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
            tooltip=["archive", alt.Tooltip("coverage:Q", format=".0%"), alt.Tooltip("out_of_range:Q", title="Outside physical range", format=".2%")]
        ).properties(height=260), width="stretch", theme="streamlit")
    w = wells_df()
    w = w[w["archive"].astype(str).isin(pick)].copy()
    levels = st.multiselect("Logs held", list(D.LEVELS), list(D.LEVELS), format_func=D.LEVELS.get, key="levels")
    w = w[w["curve_level"].isin(levels)]
    st.markdown(f"**{len(w):,} wells with coordinates in the selection**; {(w['curve_level'] >= 2).mean() if len(w) else 0:.0%} hold gamma ray, "
                "density and neutron")
    palette = {0: [110, 106, 98, 170], 1: [150, 96, 44, 200], 2: [224, 163, 58, 215], 3: [255, 238, 196, 235]}   # one light-to-bright scale
    w["fill"] = w["curve_level"].map(palette)
    w["logs"] = w["curve_level"].map(D.LEVELS)
    layer = pdk.Layer("ScatterplotLayer", data=w, get_position=["lon", "lat"], get_fill_color="fill", get_radius=900,
                      radius_min_pixels=1.5, radius_max_pixels=6, pickable=True)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=pdk.ViewState(latitude=38.5, longitude=-98.4, zoom=5.6),
                             tooltip={"html": "<b>{logs}</b><br/>archive {archive}"}, map_style=None), height=420)
    st.html('<div style="display:flex;gap:14px;flex-wrap:wrap;font-size:.85rem">' + "".join(
        f'<span><i style="display:inline-block;width:10px;height:10px;border-radius:50%;background:rgb({c[0]},{c[1]},{c[2]})"></i> '
        f'{D.LEVELS[k]} ({int((w["curve_level"] == k).sum()):,})</span>' for k, c in palette.items()) + "</div>")
    with st.expander("Table view"):
        st.dataframe(yv.rename(columns={"archive": "Archive", "files": "Files", "coverage": "GR-neutron-density coverage (median)",
                                        "out_of_range": "Outside physical range (median)", "t_conf": "Confidence (median)"}), hide_index=True, width="stretch")

# 3. Review a well: a test well's predicted column
elif page.key == "well":
    sp = committed("p0_force.json")["wells"]
    wells = sp["hidden_test"] + sp["open_test"]
    with st.sidebar:
        F.sidebar_label(st, "Well")
        well = st.selectbox("FORCE test well", wells, index=wells.index("15/9-23"), key="well",
                            format_func=lambda x: f"{x} ({'hidden' if x in sp['hidden_test'] else 'open'} test)")
    footer()
    d = safe(f"/wells/{D.q(well)}/lithology")
    if d and d.get("intervals"):
        iv = pd.DataFrame(d["intervals"])
        iv["doubtful"] = iv["probability"] < 0.5
        dz = iv[iv["doubtful"]].assign(metres=lambda x: (x["base_m"] - x["top_m"]).round(1)).sort_values("metres", ascending=False)
        logged = float(iv["base_m"].max() - iv["top_m"].min())
        first = dz.iloc[0] if len(dz) else None
        F.header(st, page, f"Where in well {well} should a petrophysicist look first?",
                 f"{d['doubtful_m']} m of about {logged:,.0f} m logged is doubtful (probability below 0.5). "
                 + (f"Start at **{first['top_m']:,.1f}–{first['base_m']:,.1f} m** ({first['rock']}, probability {first['probability']:.2f}), "
                    f"the thickest doubtful interval. " if first is not None else "No doubtful interval. ")
                 + f"Over the whole well the model matches the interpreter on {d['share_as_interpreted']:.0%} of logged depth.")
        st.subheader(f"{well}: {d['split']} test well, blind score {d['blind_score']} (0 is perfect); matches the interpreter over "
                     f"{d['share_as_interpreted']:.0%} of logged depth; {d['doubtful_m']} m doubtful")
        left, right = st.columns([1, 1], gap="large")
        with left:
            rocks = [r for r in D.ROCK if r in set(iv["rock"])]
            y = alt.Y("top_m:Q", title="Depth (m)", scale=alt.Scale(reverse=True, domain=[float(iv["top_m"].min()), float(iv["base_m"].max())]))
            unit = alt.Scale(domain=[0, 1])
            col = alt.Chart(iv).mark_rect().encode(
                x=alt.X("zero:Q", scale=unit, axis=None), x2="one:Q", y=y, y2="base_m:Q",
                color=alt.Color("rock:N", scale=alt.Scale(domain=rocks, range=[D.ROCK[r] for r in rocks]), legend=alt.Legend(title=None, orient="bottom", columns=3)),
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
            st.markdown(f"**Where to review first: the {min(10, len(dz))} thickest doubtful intervals**")
            st.dataframe(dz.head(10)[["top_m", "base_m", "metres", "rock", "probability"]].rename(columns={
                "top_m": "Top (m)", "base_m": "Base (m)", "metres": "Metres", "rock": "Predicted rock", "probability": "Probability"}),
                hide_index=True, width="stretch")
            note = safe(f"/wells/{D.q(well)}/note")
            if note and note.get("note"):
                st.markdown(f"**Planner note** ({'model-written, checked' if note.get('grounded') else 'template'}):")
                st.html(f'<div class="f-note">{F.md_html(note["note"])}</div>')
    else:
        F.header(st, page, f"Where in well {well} should a petrophysicist look first?", "The live API did not answer; see the note above.")

# 4. Check a Kansas log: one well's quality
elif page.key == "quality":
    with st.sidebar:
        F.sidebar_label(st, "Kansas well")
        kid = st.text_input("KGS ID", "1001184201", key="kgs", help="Any well in the Kansas Geological Survey LAS archive inventory.")
    footer()
    qd = safe(f"/kansas/{D.q(kid.strip())}/quality") if kid.strip() else None
    ok = bool(qd) and not qd.get("not_found")
    F.header(st, page, f"Is Kansas well {kid.strip() or '…'}'s log complete enough to interpret?",
             (f"It has {len(qd['curves'])} curves ({', '.join(qd['curves']) or 'none'}); gamma ray, neutron and density together cover "
              f"{qd['coverage_gr_neutron_density']:.0%} of its depth and {qd['out_of_range_share']:.0%} of values are outside physical ranges. "
              "Log quality only: the model's Kansas rock types are not validated.") if ok else
             "Type a KGS ID in the sidebar; the answer is the well's log quality, never a rock type (Kansas lithology is not validated).")
    if qd and qd.get("not_found"):
        st.info(qd.get("detail", "Not in the archive inventory."))
    elif ok:
        m = st.columns(4)
        m[0].metric("Curves present", f"{len(qd['curves'])}", ", ".join(qd["curves"]) or "none", delta_color="off", delta_arrow="off", border=True)
        m[1].metric("Gamma-neutron-density coverage", f"{qd['coverage_gr_neutron_density']:.0%}", delta_arrow="off", border=True)
        m[2].metric("Values outside physical range", f"{qd['out_of_range_share']:.0%}", delta_arrow="off", border=True)
        m[3].metric("Hole condition", "unknown" if qd["bad_hole_share"] is None else f"{qd['bad_hole_share']:.0%} bad",
                    delta_arrow="off", border=True)
        st.warning(qd["caveat"])
        st.caption("The whole archive's quality by year, and every well on a map, are on **Explore the data**.")

# 5. Kansas transfer test by unit
elif page.key == "transfer":
    footer()
    rows = [r for r in (safe(f"/units/{D.q(u)}") for u in D.UNITS) if r and not r.get("not_found")]
    if rows:
        u = pd.DataFrame(rows)
        u["verdict"] = u.apply(lambda r: ("passes" if r["passed"] else "fails") if r["gated"] else "reported only", axis=1)
        best = u[u["gated"]].sort_values("median_agreement", ascending=False).iloc[0]
        missed = [m for m, bad in [(f"{best['wells_scored']} wells scored, under 30", best["wells_scored"] < 30),
                                   (f"agreement {best['median_agreement']:.0%}, under 50%", best["median_agreement"] < 0.5),
                                   ("lift not measured" if pd.isna(best["lift"]) else f"lift {best['lift']:.2f}, under 2",
                                    pd.isna(best["lift"]) or best["lift"] < 2)] if bad]
        F.header(st, page, "Can we use the North Sea model to call rock types in Kansas wells?",
                 f"**No.** {int(u[u['gated']]['passed'].sum())} of {int(u['gated'].sum())} gated units passed. Even the closest, {best['unit']} "
                 f"(expected {best['expected_rock']}), misses: {'; '.join(missed) or 'see the chart'}. A pre-registered retest (P3b) reached "
                 f"{p3b['arms']['M1a']['passed_amended']} of 6 on fresh wells and a second (P3c) {p3c['arms']['M3']['passed_amended']} of 6 on new wells, "
                 "short of 4 (below). Use Kansas logs for quality checks only.")
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
                   "High agreement alone is not a pass: the model can call one rock almost everywhere. Mississippian and Precambrian were "
                   "not gated (reported only).")
        retest(p3b)
        retest_p3c(p3c)
    else:
        F.header(st, page, "Can we use the North Sea model to call rock types in Kansas wells?",
                 f"No: {units['units_passed']} of {units['units_gated']} gated units passed (committed result, ADR-005); the live API did not answer.")

# 6. AI Assistant: recorded answers by default, live only with the viewer's own key
elif page.key == "agent":
    footer()
    import agent_tools as AT
    import chat
    rec = json.loads((HERE / "replays.json").read_text())["runs"]
    F.header(st, page, "Can I ask about a well in plain words instead of reading charts?",
             f"Yes. The agent picks the tools (a well's column, a Kansas well's quality, a unit's transfer result, a note) and answers; every "
             f"number must come from a tool. {sum(r['grounded'] for r in rec)} of {len(rec)} recorded answers pass that check. Replay is free; "
             "with your own OpenAI key you can ask anything, 10 questions per session, and the key is never stored.")
    chat.render(st, HERE / "replays.json", AT)
