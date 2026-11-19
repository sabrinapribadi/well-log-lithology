---
name: well-log-lithology
description: Rock-type (lithology) answers from well logs, using a public model trained on the FORCE 2020 North Sea wells and a quality screen of the Kansas Geological Survey LAS archive. Answers what rock a FORCE test well is predicted to have by depth and where to review first, how good the model is on wells it never saw, whether a Kansas well's logs are usable, and whether the model recognised named Kansas units (Heebner, Arbuckle, Hutchinson Salt and others). Use this skill whenever someone asks about lithology, rock types from well logs, facies, strip logs, petrophysical interpretation, FORCE 2020 wells, Kansas LAS files or log quality, even if they do not name the model. Do not use it for wells outside the 20 FORCE test wells and the Kansas archive, for reservoir properties (porosity, saturation), or for seismic.
---

# Well-Log Lithology

Answers from a public, read-only API: model B (XGBoost with engineered features and a penalty-aware decision) predicts rock type every 0.152 m on FORCE 2020 North Sea test wells, and screens Kansas LAS logs for quality. Results page: https://sabrinapribadi.github.io/well-log-lithology/

## How to call it

```bash
python scripts/wll.py about                         # data, splits, model, scores, check time (start here)
python scripts/wll.py lithology 15/9-23             # predicted rock column of a FORCE test well
python scripts/wll.py quality 1001184201            # log quality of a Kansas well (lithology not validated)
python scripts/wll.py unit Heebner                  # Kansas transfer test for one named unit
python scripts/wll.py note 15/9-23                  # short grounded note
python scripts/wll.py chart column 15/9-23 --out column.html   # strip log: rock by depth, probability, doubtful intervals
python scripts/wll.py chart units --out units.html             # Kansas units against the pass bars
```

The same tools exist over MCP at `https://well-log-lithology.vercel.app/mcp`.

## Workflow

1. **Run `about` first** so the answer opens with the data and how the score is read.
2. **Pick the call from the question.**
   - A FORCE well's rock, or where to review → `lithology` and `chart column`.
   - A Kansas well → `quality` only: say plainly that lithology is not validated for Kansas.
   - "Does it work in Kansas" or a named unit → `unit` (one or all) and `chart units`.
3. **Treat `not_found` as an answer.** Only the 20 FORCE test wells and Kansas wells in the archive inventory are served; never guess a rock column for any other well.

## Reading the numbers correctly

- **Blind score** is the official FORCE 2020 penalty per 0.152 m sample on a well the model never saw: **0 is perfect, more negative is worse**. Overall: −0.504 on the 10 hidden test wells (4th of 13 2020 finalists), −0.521 on the 10 open test wells; the baseline scored −0.540. Over ten seeds the model beats the baseline every time (mean +0.134).
- **`split`:** `hidden` wells are the final judge (never used for any choice); `open` wells were scored as a second check.
- **`share_as_interpreted`** is the share of logged depth where the prediction matches the interpreter's label.
- **Doubtful** intervals have probability below 0.5; `doubtful_m` is their total metres. They are where a petrophysicist should look first.
- **Rock shares** are shares of logged depth.
- **Kansas units:** a unit passes with at least 30 wells scored, median agreement ≥ 50% and lift ≥ 2 (lift = share of the expected rock inside the unit ÷ the same share in the rest of the well). No unit passed; Heebner reaches 90% agreement but lift 1.57, because the model also calls much of the other depth shale.
- **Kansas quality:** curves present, coverage of gamma ray, neutron and density together, the share of values outside physical ranges, hole condition. A quality answer is not a lithology answer.

## Answer structure

Geologists decide in seconds whether an answer is useful, so keep it short:

1. **Data line** (one line): FORCE 2020 North Sea (118 wells; hidden wells score −0.504, 0 is perfect), the Kansas archive (quality only), model B, "checked <date> UTC".
2. **Headline** in bold: the answer in one sentence with its key number.
3. **2–4 numbered points**, each a short lead line with one or two indented detail bullets: the score and how to read it; where to review (doubtful metres, the deepest or largest doubtful zones); the caveat that changes the decision (Kansas not validated, open vs hidden well).
4. **One visual when it helps:** the strip log for a well, the unit bars for Kansas. Give the file path and what it shows.
5. **To sharpen this** (one line): core or cuttings descriptions for the doubtful intervals, or the interpreter's picks for comparison.

## Limits

FORCE predictions cover 20 test wells only; Kansas lithology is not validated (the transfer test failed; pre-registered retests reached 3 of 6 and 2 of 6 units, short of 4); FORCE data are CC BY 4.0; no live A/B test.
