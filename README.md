# Couchbase Sales Intelligence Engine — AE Call List

Generates the AE-facing call list workbook from a scored account report.
One script, one input file, one output file — no hidden state between runs.

## Pipeline

```
output/report<id>_Scored_FINAL.xlsx   (scored accounts, produced upstream by the LLM scoring pass)
              │
              ▼
      build_ae_call_list.py
              │
              ▼
   output/AE_Call_List.xlsx   (what reps actually open)
```

`build_ae_call_list.py` is the **only** place formatting, column widths, chart
placement, or text-generation logic should be edited. The output workbook is a
disposable artifact of running the script against real data — never hand-edit
`AE_Call_List.xlsx` directly and re-save it. A fix made only in the output file
will silently disappear the next time the script runs.

## Input

`INPUT_FILE` (top of the script) points at the scored report produced by the
LLM scoring pipeline — one row per account, including fields like
`engineering_implications`, `couchbase_point_of_view`, `priority_tier`,
`overall_coi`, and the `llm_*` columns used for confidence markers. Update
`INPUT_FILE` to point at the current scored file before running; the script
does not discover it automatically.

Only accounts with a non-empty `engineering_implications` field are treated as
having "validated LLM intelligence" and make it into `call_list` — the
population used for the Overview, Call Briefs, and Top 20 sheets. Accounts
without that field still appear in the Full Landscape industry rollup (which
is computed over *all* scored accounts), just not in the per-account sheets.

## Output: four sheets

**Full Landscape** — one KPI row (total scored, actionable count, actionable
%, Tier 1/2 counts) plus a 15-row industry breakdown table. `Avg COI
(Actionable)` is computed only over Tier 1–3 accounts per industry, not the
full population — averaging in Tier 4 (usually the large majority) produces a
diluted number that hides real opportunity quality in industries with a long
Tier-3 tail. See the comment above `actionable_avg_coi` in the script for the
full reasoning.

**Overview** — flat, filterable list of every qualified account (COI,
tier, industry, business model, owner). One row per account, hyperlinked to
its full brief.

**Call Briefs** — one detailed block per account: title bar with COI/LLM
score/tier, verification markers (Web-Verified / NOT COMPANY-VERIFIED —
driven by `llm_used_web_search` and `llm_narrative_caveated`), a Technical
Opportunity Canvas (why-this-account, business context, workload, an ASCII
bar chart of scoring components, discovery checklist, research confidence),
then the full field-by-field detail (engineering implications, Couchbase
point of view, technical risks, discovery questions).

**Top 20 Accounts** — the 20 highest-COI accounts, with a Tier Distribution
pie chart and an Industry Opportunity Distribution bar chart below the main
table (not overlapping it — see chart-anchor comments in the script if this
regresses).

## Styling conventions

Two font tiers exist on purpose, and they are **not interchangeable**:

- `TITLE_FONT`, `LABEL_FONT`, `BODY_FONT`, `LINK_FONT` — shared constants used
  on Top 20 Accounts and Full Landscape.
- `BRIEF_TITLE_FONT`, `BRIEF_LABEL_FONT`, `BRIEF_BODY_FONT`, `BRIEF_LINK_FONT`,
  `BRIEF_MARKER_FONT`, `BRIEF_CANVAS_HEADER_FONT`, `BRIEF_PRESSURE_BAR_FONT` —
  Call Briefs-only, sized larger for readability.

If a sheet needs a font-size change, use its own tier's constants, or add a
new one. Editing the shared constants to fix one sheet will silently resize
every other sheet that reuses them.

Row heights for any wrap-text column (Why Couchbase, Call Briefs field
values) are computed from real text length, not a fixed guess — see
`CHARS_PER_LINE_AT_E_WIDTH` and the `line_estimate` calculations. If you
change a column's width or a font's size, the chars-per-line divisor and
points-per-line multiplier need to move with it, or wrapped text will get
silently clipped despite the row "looking" tall enough on paper.

## Running it

```bash
python3 -m py_compile build_ae_call_list.py && echo "Syntax OK"
python3 build_ae_call_list.py
```

Requires `pandas` and `openpyxl`. No other project-specific dependencies.

## Deploying a script update (checklist)

Every time a new version of `build_ae_call_list.py` needs to go live, run
these in order — each step should show you real confirmation before you move
to the next one, not an assumption that the previous step worked:

```bash
# 1. Clear any old copy first, so a browser-created duplicate
#    (build_ae_call_list (1).py) can't get picked up by mistake
rm -f ~/Downloads/build_ae_call_list.py

# 2. Download the new file, then confirm exactly one copy landed
ls -la ~/Downloads/build_ae_call_list.py

# 3. Move it into the project
mv ~/Downloads/build_ae_call_list.py build_ae_call_list.py

# 4. Compile check
python3 -m py_compile build_ae_call_list.py && echo "Syntax OK"

# 5. Clear the old output, then run for real
rm -f output/AE_Call_List.xlsx
python3 build_ae_call_list.py
echo "Exit code: $?"

# 6. Confirm the output is fresh, not a leftover
ls -la output/AE_Call_List.xlsx
```

Never hand-edit or hand-place `output/AE_Call_List.xlsx` — always produce it
by running the script. This is the whole guarantee that fixes made in code
actually reach real output, rather than living only in a one-off file.
