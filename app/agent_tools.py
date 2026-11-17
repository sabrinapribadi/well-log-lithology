"""Lithology agent for the app chat (R26): one tool-using agent over the four lithology tools, calling the public API.

Tool names and parameters mirror src/serving/tools.py; tests/test_streamlit_app.py fails if they drift. The lithology tool hands the
model a summary and the ten thickest doubtful intervals instead of every interval, and the unit tool carries the pass rule, so every
number an answer may need is in a tool result (the number check).
"""
from __future__ import annotations

import wl_data as D

API = D.API
MODEL = "gpt-6-luna"
PRICES = {"input": 0.10, "cached_input": 0.01, "output": 0.50}            # USD per 1M tokens, configs (read 2026-10-12)
PASS_RULE = {"min_wells_scored": 30, "min_median_agreement": 0.5, "min_lift": 2}   # ADR-005
SYSTEM = ('You are a lithology assistant for the FORCE 2020 North Sea test wells and the Kansas LAS archive.\n'
          "Answer questions about a FORCE test well's predicted rock by depth and where to review, a Kansas well's log quality, and"
          ' whether the model recognised named Kansas units.\n'
          'Always use the tools for facts; never guess a number. Every number in your answer must come from the question or a tool '
          'result; do not compute new ones.\n'
          'The blind score is a penalty per 0.152 m sample on a well the model never saw: 0 is perfect, more negative is worse. '
          'Hidden wells are the final judge; open wells are a second check.\n'
          'Doubtful intervals have probability below 0.5: they are where to review first. Shares and coverages are fractions in the'
          ' tools (0.72 = 72%); always write them as percentages.\n'
          'Kansas lithology is not validated (the transfer test failed): for a Kansas well give log quality only, never a rock '
          'type. A Kansas unit passes only if it meets every part of its pass_rule.\n'
          'If a well is not found, say which wells are served. If a question is outside these topics, say what you can help with '
          'instead, without calling tools.\n'
          'Answer in at most 120 words, plain English, no tables.')

SCHEMAS = [
    {"type": "function", "name": "predict_lithology",
     "description": "Lithology predicted by model B for a FORCE North Sea test well (e.g. '15/9-23'): split (hidden or open), blind score "
                    "(0 is perfect), share matching the interpreter, rock shares, doubtful metres and the ten thickest doubtful intervals.",
     "parameters": {"type": "object", "required": ["well"], "properties": {"well": {"type": "string", "description": "FORCE well name"}}}},
    {"type": "function", "name": "well_quality",
     "description": "Log quality of a Kansas well by KGS ID (e.g. '1001184201'): curves present, gamma-neutron-density coverage, share of "
                    "values outside physical ranges, hole condition. Kansas lithology is not validated.",
     "parameters": {"type": "object", "required": ["kgs_id"], "properties": {"kgs_id": {"type": "string", "description": "KGS ID"}}}},
    {"type": "function", "name": "unit_agreement",
     "description": "Kansas transfer test for a named unit (e.g. 'Hutchinson Salt', 'Arbuckle', 'Heebner'): wells scored, median agreement, "
                    "lift, whether it passed, the pass rule and what the model predicted inside the unit.",
     "parameters": {"type": "object", "required": ["unit"], "properties": {"unit": {"type": "string", "description": "Unit name"}}}},
    {"type": "function", "name": "explain_well",
     "description": "A short grounded note on a FORCE test well or a Kansas well; every number comes from the store.",
     "parameters": {"type": "object", "required": ["well_or_kgs_id"],
                    "properties": {"well_or_kgs_id": {"type": "string", "description": "FORCE well or KGS ID"}}}},
]


def _lith(well: str) -> dict:
    d = D.get(f"/wells/{D.q(well)}/lithology")
    if d.get("not_found"):
        return d
    doubt = sorted((i for i in d["intervals"] if i["probability"] < 0.5), key=lambda i: i["top_m"] - i["base_m"])[:10]
    return {k: v for k, v in d.items() if k != "intervals"} | {
        "logged_from_m": min(i["top_m"] for i in d["intervals"]), "logged_to_m": max(i["base_m"] for i in d["intervals"]),
        "thickest_doubtful_intervals": [{"rock": i["rock"], "top_m": i["top_m"], "base_m": i["base_m"], "probability": i["probability"]}
                                        for i in doubt]}


def _unit(unit: str) -> dict:
    d = D.get(f"/units/{D.q(unit)}")
    return d if d.get("not_found") else {**d, "pass_rule": PASS_RULE}


FNS = {"predict_lithology": _lith,
       "well_quality": lambda kgs_id: D.get(f"/kansas/{D.q(kgs_id)}/quality"),
       "unit_agreement": _unit,
       "explain_well": lambda well_or_kgs_id: D.get(f"/wells/{D.q(well_or_kgs_id)}/note")}
TOOLS = {s["name"]: {"schema": s, "fn": FNS[s["name"]]} for s in SCHEMAS}

QUESTIONS = [                                                              # recorded for replay by scripts/record_agent_replays.py
    "What rocks does well 15/9-23 have, and where should I review first?",
    "How good is the model on well 16/2-7?",
    "Compare wells 15/9-14 and 15/9-23.",
    "Can I trust the lithology for Kansas well 1001184201?",
    "Did the model recognise the Arbuckle dolomite in Kansas?",
    "Give me a short note on well 35/9-8.",
    "What's the lithology of well 6507/7-2?",
    "What porosity does well 15/9-23 have?",
]
