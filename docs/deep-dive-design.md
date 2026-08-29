# Deep Dive — Design Specification

**Version:** dd-v1.0 · **Config version:** 1
**Last updated:** August 28, 2026
**Status:** Live, cron-scheduled (Mon / Wed / Fri, 7:00 AM ET)

---

## 1. Purpose

Deep Dive is an **existing-account expansion intelligence agent**. Its job is to surface **Qualified Signals** — recent, evidence-backed changes inside a rep's existing named accounts that indicate credible whitespace for a new Couchbase selling motion.

**Optimizes for:** new selling conversations created inside logos already owned.
**Not optimized for:** signal volume, breaking news, cold prospecting.

> Tagline: "Deep Dive finds new business inside logos we already own."

Logo: 🤿 (snorkel — locked, never a fish emoji).

---

## 2. Ownership Model

Each rep runs their own copy of the agent (Mel shares → rep duplicates → rep owns). **The executing user IS the target rep** — no per-rep configuration required.

At runtime, `{{ metadata.user.* }}` resolves to:

| Field | Purpose |
|---|---|
| `metadata.user.name` | The rep's display name |
| `metadata.user.email` | The rep's email (used for CC lookup) |
| `metadata.user.id` | The rep's `rox_user_id` (used for RQL scoping) |

Everything downstream — account universe, Gmail mining, header, subject line, `support_by_rep` lookup — binds to these three values.

---

## 3. Trigger

- Type: Cron schedule
- Expression: `0 7 * * 5,1,3` (Monday, Wednesday, Friday at 7:00 AM)
- Timezone: `America/New_York`

Duplicates inherit the trigger, but the new owner must confirm it's enabled after duplication.

---

## 4. Variables

Only one workflow variable:

| Name | Type | Purpose |
|---|---|---|
| `feedback_url` | str | Base URL for feedback buttons on each signal card |

All rep-specific values come from `metadata.user.*` — no per-rep variables.

---

## 5. Attached Tools

| Package | Action | Purpose |
|---|---|---|
| `rox_actions` | `custom_store_get` | Read the org-scoped `support_by_rep` map |
| `rox_actions` | `custom_store_set` | Seed the org-scoped `support_by_rep` map (one-shot) |
| `rox_actions` | `get_insights` | Pull recent Rox insights for the account universe |
| `rox_actions` | `add_html` | Publish the rendered report to the rep's Home |
| `email` | `list_emails` | Mine Gmail threads for warm-path evidence |
| `email` | `get_email` | Fetch email bodies for materially informative threads |
| `email` | `send_email_as_user` | Send the report from the rep's connected mailbox |
| `agent_outputs` | `generate_agent_response` | Web-research candidate account changes with citations |
| `code` | `execute_python` | Run the locked Python renderer |

**Not attached (deliberately):**
- `agent_outputs.generate_webpage` — the report is rendered by locked Python, not the generic HTML generator
- `email.send_email` — the report sends from the rep's mailbox, not the Rox workflow address

**Built-in runtime tools used** (never listed in tools):
- RQL toolset (`search_rql_catalog`, `plan_and_execute_rql_query`, `discover_join_keys`) for account/deal/person/list reads
- Scratchpad (`write_file`, `run`) for local data processing
- `set_run_name`, `add_todo` / `mark_todo_done` for run metadata

---

## 6. The Support-By-Rep Custom Store

### 6.1 Purpose

Cross-agent map of rep email → list of CC email addresses (SEs, SDRs, coverage support). Read by every workflow in the org that needs to CC coverage on a rep's outputs.

### 6.2 Shape

Org-scoped custom store key: `support_by_rep`

```json
{
  "<rep.email@couchbase.com>": ["<cc1@couchbase.com>", "<cc2@couchbase.com>"]
}
```

### 6.3 Seeder Behavior

Step 1 of every Deep Dive run reads the key. Step 2 is a mandatory one-shot seeder:

- If Step 1 returns `found: false` OR value is `null`/`{}`/empty → Step 2's next tool call **must** be `custom_store_set` with the full seed map. No other tool call (including `set_run_name`, `add_todo`, RQL) may come between Step 1 and the seeder write.
- If Step 1 returns a non-empty map → skip Step 2 entirely. Never overwrite.

Rationale: the map is org-wide state. Once populated, all agents in the org (Deep Dive + siblings) read it. Deep Dive is the single writer; other agents are read-only consumers.

### 6.4 Editing the Map After Seeding

Editing the seed in Deep Dive's instructions does **not** retroactively update the stored value — the store is already populated, so Step 2 skips forever. To change the mapping:

- Delete the org-scoped `support_by_rep` key, letting the next Deep Dive run re-seed with the current instructions map, **OR**
- Overwrite the value directly via a one-off `custom_store_set` call.

### 6.5 Current Seed (27 reps)

Kept in Deep Dive's instructions verbatim. Alphabetical by rep email. Preston Cattanach and Poret Kyesmu are SDRs and appear on multiple rep entries as expected.

---

## 7. Execution Pipeline

**Step 1 — Load rep→CC mapping**
`custom_store_get(key="support_by_rep", scope="org")` → save as `support_by_rep_raw`. Never fail on read error; treat as `{}` and continue.

**Step 2 — One-shot seed**
If store empty → `custom_store_set` with the seed map immediately (no interleaving tool calls). Otherwise skip.

**Step 3 — Account universe**
Fetch every account owned by the executing user, PLUS every account with an opportunity in Commit / Best Case / Closed Won stages owned by that user. Deduplicate by SFDC Account ID. Understand parent-subsidiary hierarchy.

If empty → render empty-state variant, still publish, still email.

**Step 4 — Existing coverage**
Pull open opps, closed-won history, existing contacts, workload/product/BU coverage columns per account.

**Step 5 — Rox insights**
`get_insights(lookback_days=7, limit=200, company_ids=[...])`.

**Step 6 — Candidate research**
`agent_outputs.generate_agent_response` per-account, batched. Look for:
- New BUs, subsidiaries
- New engineering/data leaders
- Acquisitions
- Modernization initiatives
- Real-time apps
- Competitive database signals
- Geographic expansion

Every finding requires dated citations.

**Step 7 — Gmail relationship paths**
`email.list_emails(lookback_days=90, participant_rox_user_ids=[user.id], rox_company_ids=[...])`. Sample selectively; `get_email` for bodies only when materially informative.

**Step 8 — Motion statements**
One investigative sentence per candidate: *"Explore &lt;surface&gt; with &lt;BU/team/owner&gt; inside &lt;account&gt; because &lt;observed change&gt;."* Never start with "Sell."

**Step 9 — Gates**
Apply in strict order 1→2→3→4→5. Gates 1-4 kill; Gate 5 only modifies.

**Step 10 — Deduplicate**
By SFDC Account ID, opportunity coverage (three-question test), contact match order, signal consolidation.

**Step 11 — Signal IDs**
Stable hash: `sha256(account_id + motion_type + primary_contact_email + YYYYMMDD)[:16]`.

**Step 12 — Score**
1–10 scale. Status band matters more than score value.

**Step 13 — Select top 3-5**
If fewer than 3 clear all gates with score ≥ 6 → publish only what qualifies. Never pad.

**Step 14 — Classify**
Assign each surviving signal one Motion Type (see §9).

**Step 15 — Relationship state**
Per signal: direct / internal / new (see §8.3).

**Step 16 — LinkedIn URLs**
For each contact on a card, populate `linkedin_url` when available. Preference order:
1. SFDC person record `linkedin_url`
2. Verified via `enrich_and_validate_public_contacts` (`validation_status: VERIFIED`)
3. Plausible from public contact search

Omit rather than guess. Fabricated URLs are a defect.

**Step 17 — Render & publish**
Assemble payload, call locked Python renderer, publish to Home, email to rep.

---

## 8. Qualification Framework

### 8.1 First Principle

A person, event, announcement, or technology discovery cannot qualify by itself. It must be connected to a specific potential selling motion.

Bare signals that never publish alone: new hire, funding round, product launch, acquisition, competitive database mention, news/LinkedIn item. Each needs a downstream workload/BU/initiative AND a specific owner tied to it.

### 8.2 Key Definitions

**Whitespace** — a meaningful organizational, workload, geographic, product, or initiative-level opening not already covered by the existing Couchbase engagement. Whitespace ≠ "no one is talking to Couchbase" (that's just cold).

**Already covered** — the existing Couchbase engagement demonstrably addresses the same BU + same workload + same initiative. High bar. Ask three questions; if any answer is "no," it's not covered.

**Couchbase hypothesis quality bar** — a technically credible reason to investigate Couchbase for this workload, tied to specific workload characteristics: real-time, distributed, high-volume transactional, low-latency, mobile, IoT, personalization, session management, app modernization, cloud migration, AI. Not "could help with scalability."

**Why It Matters — the locked chain.** Every "Why It Matters" walks the same four steps:
1. Business event
2. Data workload
3. Technical characteristic
4. Couchbase hypothesis

If the chain doesn't walk, the signal fails Gate 3.

### 8.3 Relationship State (card-level)

| State | Definition |
|---|---|
| Direct 🟢 | Rep has ≥1 contact tied to this motion with an active Gmail thread within 90 days |
| Internal 🟡 | Known SFDC contact tied to the motion exists, but no recent Gmail relationship |
| New ⚪ | No existing relationship; net-new outreach or Watch card |

### 8.4 The Gates

**Gate 1 — Change? (kill)**
No identifiable recent change → DISCARD.

**Gate 2 — Specific whitespace? (kill — most important gate)**
- 2a. Name a specific BU/product/team/geo/workload. Whole-account = not specific → DISCARD.
- 2b. Three-question "already covered" test. DISCARD only if same BU + same workload + same initiative all "yes."

**Gate 3 — Couchbase hypothesis? (kill)**
Must meet the quality bar AND walk the four-step chain. Generic → DISCARD.

**Gate 4 — Relevant person? (kill with Watch classification)**
- Named relevant person → PASS
- No person, strong motion → Watch (opportunity-development, score capped at 6, monitoring action)
- No person, weak motion → DISCARD

**Gate 5 — Action path? (classification modifier, NEVER a kill gate)**
- Warm path → status = Warm path, +1 to +2 to score
- No warm path → status = Net-new relationship required, −1 to −2 to score, floor at 5
- Keep the signal either way.

### 8.5 Expansion Score (1–10)

Status band matters more than raw score.

- Warm path: +1/+2
- Net-new: −1/−2, floor at 5
- Watch: capped at 6
- Vague motion: −2

Order signals in the report by status band first, then score descending.

### 8.6 Motion Types

| Emoji | Motion |
|---|---|
| 🏢 | New Business Unit |
| ⚙️ | New Workload |
| 👤 | New Leader |
| 📈 | Expansion |
| 🔀 | Acquisition |
| ⚔️ | Competitive Displacement |
| 🏗️ | Modernization |
| 🌍 | Geographic Expansion |
| 🤝 | Relationship Expansion |

---

## 9. Voice & Copy Rules

- Investigative, not salesy. Motion sentence starts with a verb of investigation: *Explore / Investigate / Open a technical conversation about / Look at the data architecture behind*. Never start with "Sell."
- The Couchbase POV lives inside "Why It Matters," not the motion sentence.
- Cite everything. External claims need dated URLs.
- No padding. If fewer than 3 signals qualify, publish fewer. Empty day → empty-state variant.

---

## 10. Rendering Pipeline (LOCKED)

### 10.1 Step A — Payload

JSON object with these top-level fields:

| Field | Type | Notes |
|---|---|---|
| `target_rep_name` | str | `{{ metadata.user.name }}` |
| `target_rep_email` | str | `{{ metadata.user.email }}` |
| `target_rep_id` | str | `{{ metadata.user.id }}` |
| `date_line` | str | Human-readable weekday + date |
| `haul_count` | int | Total qualified signals |
| `status_counts` | object | `{warm, net_new, watch}` counts |
| `motion_chips` | array | `[{emoji, label, count}]` per motion type |
| `signals` | array | Signal objects (see below) |
| `gmail_disclaimer` | str/null | Omit or null — rep IS executing user, no visibility caveat |
| `generated_at` | str | Human-readable America/New_York, e.g. "August 28, 2026 at 1:49 PM ET". Never ISO 8601. |
| `feedback_url` | str | From variable |
| `workflow_run_id` | str | `{{ metadata.workflow.run_id }}` |
| `triggered_at` | str | `{{ metadata.run.triggered_at }}` |
| `config_version` | str | `"1"` |
| `design_spec_version` | str | `"dd-v1.0"` |
| `is_test_run` | bool | true when `{{ metadata.run.trigger_type }}` is null |
| `empty` | bool | true → render empty-state variant |

**Each signal:**

| Field | Notes |
|---|---|
| `signal_id` | Stable hash from Step 11 |
| `status` | "warm" / "net_new" / "watch" |
| `status_label` | "Warm path" / "Net-new relationship required" / "Watch" |
| `score` | 1–10 |
| `account_name`, `account_parent` | Parent optional |
| `motion_emoji`, `motion_label` | From Motion Types table |
| `motion_sentence` | Investigative verb, never "Sell" |
| `what_changed_html` | Prose + inline `<a>` citations |
| `why_it_matters` | Walks the four-step chain |
| `where_to_go` | Concrete next surface / team |
| `contacts` | Array of `{name, title, path, path_label, linkedin_url}` |
| `watch_target_roles` | Only on Watch cards; `contacts=[]` |
| `relationship_state` | "direct" / "internal" / "new" |
| `relationship_label` | Human label |
| `recommended_action` | Rep's next step |
| `why_survived` | One-line qualification rationale |
| `account_id`, `primary_contact_email`, `primary_contact_name` | For feedback buttons |

Contact `path` values: "sfdc" / "gmail" / "cold". `linkedin_url` populated only when verified per Step 16; renderer falls back to plain-text name otherwise.

### 10.2 Step B — Renderer

Locked Python code, ~400 lines, called via `code.execute_python` with the payload passed as `context.data`. The code is copied verbatim into the tool call — never modified.

Renders:
- **Header block** — snorkel logo, "Today's Deep Dive — {rep name}", date, tagline
- **Summary bar** — Haul count · Status chips · Motion Type chips
- **Signal cards** — one per signal, colored by status, with all sections
- **Footer** — Sources line · optional Gmail disclaimer · "Generated {date}" · optional test-run banner · attribution lines
- **Attribution lines** — "🤿 Deep Dive · Run {date} · config_version=X · design_spec_version=Y" and "Questions or feedback? mel@couchbase.com". No "Built by" line.
- **Empty-state variant** — "Calm waters today." with the same attribution and test banner treatment

Design tokens locked in the renderer (colors, backgrounds, typography, LinkedIn SVG data-URI, etc.). Never edit the renderer to change styling — swap the whole locked block if a v1.1 is needed and bump `design_spec_version`.

### 10.3 Step C — Publish to Home

`rox_actions.add_html` with:
- `title` = "🤿 Today's Deep Dive — {rep name}"
- `html` = exact stdout from Step B
- `output_summary` NOT set (auto-generated summary)

### 10.4 Step D — Email

**CC resolution** — apply this exact normalization sequence to `support_by_rep_raw`; never fail the run on normalization errors:

1. Lowercase `{{ metadata.user.email }}` → `user_email_lc`
2. Lowercase all keys and values of the raw map
3. Lookup `user_email_lc`; missing → no CC
4. Coerce mapped value: string → `[value]`, list → as-is, anything else → `[]`
5. Filter to strings containing `@` with a `.` after the `@`
6. Lowercase every remaining address
7. Remove `user_email_lc` (no self-CC)
8. Deduplicate preserving order
9. Never invent, add, or substitute entries — only drop malformed ones
10. Empty result → omit `cc_addresses` (still email the rep)

Any exception → treat CC as empty, continue.

**Send via `email.send_email_as_user`:**
- `to_addresses` = `["{{ metadata.user.email }}"]`
- `cc_addresses` = resolved per above
- `email_subject` = `🤿 Today's Deep Dive — {rep name} — {weekday}, {date}`
- `email_body` = exact HTML stdout from Step B
- `body_format` = `"html"`

Requires the rep's Gmail or Outlook mailbox to be connected in Rox. If unconnected, the send fails silently and no email lands. This is the most common cause of "I got the Home item but not the email."

---

## 11. Hard Rules

**Never:**
- Call `agent_outputs.generate_webpage` or `email.send_email`. Neither is attached.
- Modify the Python renderer — copy verbatim.
- Use a fish emoji. Only 🤿.
- Reference Fresh Catch anywhere.
- Start the motion sentence with "Sell."
- Skip the four-step chain in "Why It Matters."
- Discard a signal at Gate 5 (classification only).
- Pad the report to hit 3–5.
- Fabricate LinkedIn URLs.
- Skip the email when the account universe is empty. The empty-state report still publishes and emails.
- Skip the email for an unmapped rep. Unmapped reps get no CC but still receive the report.
- Invent, add, or substitute CC entries during normalization — only drop malformed ones.
- Fail the run because of a custom_store error or CC normalization exception. Both fall back to "no CC" and continue.
- Overwrite `support_by_rep` when Step 1 already returned data.
- Skip Step 2 seeder when Step 1 returned empty — `custom_store_set` MUST be the very next tool call. Interleaving anything else is a defect.
- Put ISO 8601 in `generated_at`. Human-readable America/New_York only.
- Render a "Built by" line.

**Always:**
- Scope every read to `{{ metadata.user.id }}`.
- Load `support_by_rep` as the very first step — before any other work.
- Fire Step 2 seeder immediately when Step 1 returned empty (this is how sibling agents get the mapping).
- Apply the full defensive normalization sequence in Step D on every run.
- Write the investigative motion sentence before running gates.
- Walk the four-step chain in every "Why It Matters."
- Compute card-level `relationship_state`.
- Include verified LinkedIn URLs when available.
- Render via Python, publish via `add_html`, email via `send_email_as_user`.
- Populate `is_test_run`, `triggered_at`, `generated_at` on every run.
- Format `generated_at` as human-readable America/New_York.

---

## 12. Deployment Model

- Mel owns the master copy of the workflow.
- Mel shares the agent.
- Reps duplicate into their own workspace → they become the owner.
- Their duplicate runs with `metadata.user.*` bound to them automatically. No config changes required.
- Their duplicate reads (not writes) the org-scoped `support_by_rep` map. Deep Dive remains the single writer; siblings and duplicates are read-only.

**Post-duplication checklist for the rep**
1. Confirm cron trigger is enabled on their copy.
2. Connect Gmail (or Outlook) to Rox — required for `send_email_as_user`.
3. First run should produce a Home item + inbox email. If the Home item lands but the email doesn't, the mailbox connection is the first suspect.

---

## 13. Known Open Items

- **Patrick Gryzan vs Gryzen** — stored as `patrick.gryzan@couchbase.com` in the seed map. Spelling to be confirmed.
- **New UPS rep under Jenn Lewis** — placeholder; awaiting name/email to add to seed map.

---

## 14. Change Control

- `config_version` — bumps when workflow logic changes (steps, gates, tool wiring, seed map).
- `design_spec_version` — bumps when the rendered output changes (renderer code, payload schema, visual design).

---

## Changelog

- **dd-v1.0** (current) — Multi-rep ownership model: agent is duplicated per rep rather than variable-swapped for a single hardcoded target (`metadata.user.*` replaces `target_rep_*` variables). Introduces the org-scoped `support_by_rep` custom store (single-writer seed pattern, read by sibling agents) replacing the old single-rep CC lookup. Cron moved to Mon/Wed/Fri 7:00 AM ET (from Mon–Fri). Payload gains `workflow_run_id`, `triggered_at`, `config_version`, `design_spec_version`, `is_test_run` fields. Formal config_version / design_spec_version change-control scheme introduced (§14).
- **v4** — investigative voice rules, locked 4-step "Why It Matters" chain, card-level relationship state (Direct/Internal/New), Gate 5 reclassified as non-kill modifier, deterministic Python renderer replacing `generate_webpage`, ocean/diving visual system locked, `send_email_as_user` replacing `generate_webpage`-driven email. Deployment infra: Worker source and CI/CD pipeline added to git — Cloudflare dashboard no longer the source of truth for `worker.js`.
- **v2** — Kyle-scoped instructions, feedback-link-aware report, initial 5-gate sequence, HTML report via `generate_webpage`.
