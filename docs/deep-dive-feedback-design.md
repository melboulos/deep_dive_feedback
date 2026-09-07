# Deep Dive Feedback Agent — Technical Design Document

**Owner:** Mel Boulos (mel.boulos@couchbase.com)
**Workflow ID:** `deep-dive-feedback`
**Type:** Agentflow (Rox Workflows)
**Trigger:** Webhook
**Status:** Production (field-deployed)
**Version:** 6 (Sept 2026 — deterministic write path via `add_email`)

> Companion document to [`deep-dive-design.md`](./deep-dive-design.md). Deep Dive is the intelligence agent that surfaces signals and renders the pill buttons; Deep Dive Feedback is the separate agent + infrastructure that those pills call out to. Deep Dive does not know whether a pill was clicked — it only renders the links.

---

## 1. Purpose

Turn Deep Dive account-signal pill clicks into two outputs:

1. A durable feedback log the upstream Deep Dive agent can learn from — every action (`pursue` / `watch` / `wrong` / `already_working`) is written to an org-scoped custom store keyed by `signal_id`, with the acting rep's email as the top-level bucket.
2. On **Pursue only**, a single reviewed customer-outreach draft on the acting rep's Home — the product of deep account research, relationship classification, target selection, warm-path evaluation, calendar retrieval, and QA — plus a maintainer-only shadow developer notification containing the full diagnostic trail.

Nothing is sent automatically. The rep is always the last gate.

---

## 2. System Context

```
┌────────────────────────────┐
│  Deep Dive boomerang page  │
│  (GitHub Pages, static)    │
│  melboulos.github.io/      │
│  deep_dive_feedback/       │
└────────────┬───────────────┘
             │  fetch() from browser
             │  (rep clicks Pursue/Watch/Wrong/Already Working)
             ▼
┌────────────────────────────┐
│  Cloudflare Worker proxy   │
│  (per-rep booking URL      │
│  injection, JSON encode,   │
│  ack-to-browser)           │
└────────────┬───────────────┘
             │  POST Content-Type: application/json
             ▼
┌────────────────────────────┐
│  Rox Workflows webhook     │
│  (this agentflow trigger)  │
└────────────┬───────────────┘
             │  trigger_data.payload
             ▼
┌────────────────────────────┐
│  Deep Dive Feedback Agent  │
│  (runtime LLM +            │
│  Rox action catalog)       │
└────┬───────────┬───────────┘
     │           │
     │           ├── Reads: RQL catalog, Gmail history, calendar, org store
     │           ├── Writes: org store (every action), Home draft (Pursue only)
     │           └── Notifies: workflow maintainer (Pursue, non-self-click only)
     │
     ▼
┌────────────────────────────┐
│  Upstream Deep Dive agent  │
│  (reads org store on its   │
│  next run to learn from    │
│  rep dispositions)         │
└────────────────────────────┘
```

**Trust boundaries:**

- The GitHub Pages boomerang is untrusted UI — no secrets, no direct webhook auth.
- The Cloudflare Worker is the trust-injection point: it authenticates the rep by whatever mechanism it uses (currently trusted origin + rep-identifying payload) and adds the optional `booking_url`.
- The Rox webhook accepts the Worker's JSON payload as-is and hands it to the agentflow. Webhook auth is currently `use_auth: false` — the Worker's origin check is the perimeter.

---

## 3. Trigger Contract

**Trigger type:** webhook
**Content type:** `application/json`
**Webhook URL:** `https://webhooks.backend.rox.com/webhooks/w/workflow-webhook-318d6a1b`

Payload shape (arrives at `trigger_data.payload`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `signal_id` | string | yes | Stable hash from Deep Dive; used as-is as the sub-key in the store |
| `action` | string | yes | One of `pursue`, `watch`, `wrong`, `already_working` |
| `user_email` | string | yes | Acting rep's email; lowercased before use |
| `account_id` | string | no | Rox company ID |
| `account_name` | string | no | |
| `motion_type` | string | no | Deep Dive's classification (e.g. New Business Unit, New Workload, Acquisition, New Leader) |
| `primary_contact_email` | string \| null | no | Deep Dive's suggested contact — may be overridden by target selection logic |
| `primary_contact_name` | string \| null | no | |
| `workflow_run_id` | string | no | Deep Dive's source run ID (for provenance) |
| `clicked_at` | string (ISO 8601 UTC) | no | Boomerang page timestamp |
| `booking_url` | string \| null | no | Cloudflare Worker–injected — optional per-rep Calendly / Google appointment URL |

**Validation:** If `signal_id`, `action`, or `user_email` is missing/empty, the run halts at Step 1 without touching the store or drafting anything.

---

## 4. State Model — Org-Scoped Custom Store

**Key:** `deep_dive_feedback`
**Scope:** org
**Access:** Read + write in this workflow. Read-only from the upstream Deep Dive agent's next run.

Shape:

```json
{
  "<lowercased_user_email>": {
    "<signal_id>": {
      "action": "pursue|watch|wrong|already_working",
      "account_id": "…",
      "account_name": "…",
      "motion_type": "…",
      "primary_contact_email": "…" | null,
      "primary_contact_name": "…" | null,
      "workflow_run_id": "…",
      "clicked_at": "2026-09-05T12:45:00Z"
    }
  }
}
```

**Invariants:**

- Top-level keys are lowercase rep emails.
- Second-level keys are the raw `signal_id` (no rewriting).
- Each entry contains exactly the 8 fields above. `booking_url` is deliberately excluded — it's an ephemeral routing hint from the Worker, not a durable disposition fact.
- Latest click wins — upserts overwrite in place. No arrays, no history.
- Read/write is soft-failed — if the store errors, the run continues and notes the failure in the final message, but does not fail.

**Action semantics** (for the upstream Deep Dive agent to interpret — see §Open Questions on whether this is confirmed live yet):

| Action | Deep Dive's interpretation |
|---|---|
| `pursue` | Rep is following through; we also drafted outreach in this run |
| `watch` | Suppress `signal_id` until material change |
| `wrong` | Down-weight the `(account_id, motion_type, primary_contact_email)` tuple |
| `already_working` | Suppress `(account_id, motion_type)` |

> **Note:** This table defines the *contract* this agent writes against. Whether Deep Dive's own instructions actually read `deep_dive_feedback` and act on it is tracked as an open question (§15) until confirmed.

---

## 5. Runtime Architecture

**Kind:** Agentflow — a single LLM run with a system prompt (instructions), a tool set, and trigger payload / metadata / variables handed to it as the initial user message. There are no discrete "steps" as JSON — the agent decides which tools to call in what order, guided by the numbered steps in its instructions.

**Model runtime:** Whatever the Rox agentflow runtime defaults to (Claude family as of this writing).

**Timezone:** `America/New_York` (workflow setting; used for run_name templating and any cron-adjacent reasoning).

**Run naming:** `settings.run_name = "{{ trigger_data.payload.action }} · {{ trigger_data.payload.account_name }} · {{ trigger_data.payload.motion_type }}"` — resolved once at trigger time. Step 2 also calls the built-in `set_run_name` for cases where a segment is missing (substituting `"(unknown)"`).

---

## 6. Tool Set

**Attached actions (9 total):**

| Package.Action | Purpose | Called in |
|---|---|---|
| `rox_actions.custom_store_get` | Read org-scoped `deep_dive_feedback` key | Step 3 (every run) |
| `rox_actions.custom_store_set` | Write updated store | Step 3 (every run) |
| `rox_actions.add_email` | Deterministic raw-store write to rep's Home — signature lands as authored | Step 10 (Pursue only) |
| `agent_outputs.generate_agent_response` | Focused external research (signal verification) | Step 5 optional |
| `email.list_emails` | Company-scoped Gmail thread scan | Step 6 |
| `email.get_email` | Read individual thread bodies | Step 6 |
| `rox_actions.get_all_meetings` | Rep's calendar for slot computation | Step 9 |
| `rox_actions.send_notification` | Maintainer-only shadow developer notification | Step 11 (Pursue, non-self-click) |
| `rox_actions.enrich_email` | Recipient repair — resolve missing email addresses | Step 10.2 (Pursue only) |

**Built-in runtime tools also used** (not listed in tools, always available):

- `set_run_name` — override run name when segments are missing
- `search_rql_catalog`, `plan_and_execute_rql_query`, `discover_join_keys` — the RQL toolset for CRM reads (accounts, contacts, opportunities)
- `write_file`, `read_file`, `edit_file`, `run` — scratchpad + Python execution for self-QA (word counting, slot distribution checks)
- `add_todo`, `mark_todo_done`, `update_task_list` — internal planning

**Deliberately NOT attached** (with reasons):

| Not attached | Reason |
|---|---|
| `agent_outputs.generate_email` | Compose skill activates `edit_email_compose_v2` post-hoc, which stripped required signatures on ~50% of test runs. Replaced by `add_email`. |
| `email.send_email` | Rep is the last gate. Nothing sends automatically. |
| `agent_outputs.generate_webpage` | Rep's Home gets ONE artifact on Pursue — the draft. All reasoning goes to the shadow notification. |
| Any single-record `find_or_create` / lookup_account | RQL handles all account reads. |

---

## 7. Execution Flow

Steps 1–4 run on every action. Steps 5–11 run only when `action == "pursue"`. Step 11 is skipped when the acting rep IS the maintainer (self-click).

### 7.1 Every-Action Path (Steps 1–4)

1. **Validate payload.** Halt on missing `signal_id`, `action`, or `user_email`.
2. **Set run name.** `"{action} · {account_name} · {motion_type}"`.
3. **Read → merge → write org store.** Read `deep_dive_feedback`, coerce to dict, ensure a sub-dict for lowercased `user_email`, upsert the 8-field entry keyed by `signal_id`, write back. Soft-failed on read or write.
4. **Branch by action.**
   - `pursue` → continue to Step 5.
   - `watch` / `wrong` / `already_working` → return `"Logged <action> on signal <signal_id> for <lowercased user_email>."`
   - Any other value → return an "unrecognized action" message.

### 7.2 Pursue Branch (Steps 5–11)

5. **Research the signal + account.**
   - Signal freshness: prefer the most recent, most distinct, most narratively specific event. Record 1–2 rejected alternatives for the shadow.
   - Account read (RQL): industry / revenue / region / Couchbase custom columns (`estimated_couchbase_apps`, `using_couchbase*`, `deployments`, `tech_stack`, `mobile_app_tech_stack`, AI initiatives, strategic priorities). Both `rox_id` and `sfdc_account_id` lookups; capture `sfdc_parent_name` and any subsidiaries.
   - Contacts (RQL): name, title, seniority, last_email, last_meeting.
   - Opportunities (RQL): closed-won (primary source for footprint), open, closed-lost (with age caveat).
   - Optional focused external research via `generate_agent_response` — one tight query naming account + motion + what needs verifying. No open-ended research.

6. **Investigate Gmail** — human relationship, not email existence.
   - Call `list_emails` scoped by `rox_company_ids: [account_id]`, `lookback_days=365`.
   - Pick 2–3 most-recent + most-on-topic threads; read bodies via `get_email`.
   - Assess participants, recency, substance, champion signals, credibility of any warm-intro path.
   - Recency + substance > quantity. Soft-fail on any Gmail error.

7. **Classify.**
   - Relationship status (exactly one): Active / Warm / Historical-Stale / Weak / None / Unknown.
   - Existing use case: capture concretely by workload + team + BU + current-or-historical, plus the concrete evidence artifact (opp name, deployment note, workload label) the email will cite by name.
   - Couchbase bridge (exactly one): Strong / Potential / None identified / Unknown.
   - Account vs opportunity relationship: Active customer + new BU/workload/team = expansion motion (first-class), not net-new.
   - Warm path: who do we know, what for, how recently, can they credibly introduce?

8. **Strategy + target.**
   - Pursuit strategy: warm-intro request / existing customer expansion / multi-threading / direct outreach / executive-to-executive / technical entry.
   - Warm-intro default rule: for Active/Warm accounts with a known contact who does NOT demonstrably own the workload, default to Warm-intro request — asking for a pointer is lower-friction than asking a technical question the contact may not own.
   - Target selection hierarchy (7 tiers) — role relevance to the signal beats title seniority.
   - Executive Entry Point vs Technical/Operational Owner — may be different people. Target confidence rated High/Medium/Low.
   - Acquisition/M&A heuristic: prefer platform/engineering leadership at the acquiring company over the acquired-company founder unless the founder has a verified continuing technical role.
   - Internal Couchbase hypothesis: where Couchbase may fit, what would need to be true, what's unverified. Never dumped into the customer email — lives in the shadow.

9. **Calendar.**
   - Always call `get_all_meetings` first (never rely on `booking_url` alone).
   - Compute 3 open 30-minute slots in the rep's business hours over the next 5–10 business days.
   - Spread across ≥2 days AND ≥2 time-of-day windows (morning/afternoon).
   - Format: `"Tuesday, Sept. 8 at 10:00 AM ET"`.
   - Four outcome states → PASS (3 slots + booking URL) / PASS (3 slots) / PARTIAL (booking URL only) / FAIL (open-ended ask).
   - Never invent slots. Never put `[TODO:]` into the customer body.

10. **Author + save the draft.**
    - Author the full body in the agent's own reasoning per the composition rules (see §8).
    - Recipient resolution — required sequence:
      1. Verified email from RQL/Gmail/payload → use it
      2. No verified email → `enrich_email` with target's name + company + LinkedIn slug
      3. Enrichment fails → `[TODO: find email for <name>]` placeholder
    - A placeholder recipient can NEVER be marked PASS. Execution Status becomes BLOCKED.
    - Call `add_email` exactly once with `subject`, `body` (full composed string), `to` (single-element list), optional `output_summary`.
    - Retain returned `inbox_item_id` and `rox_file_id` for Step 11.
    - No re-edit path exists. Signature/format failures are diagnostic-only.

11. **Shadow developer notification** (Pursue, non-self-click only).
    - `send_notification` to maintainer (`db14b483-5501-44aa-9181-64c8e45f9f1e`).
    - Subject: `"[Dev · Pursue] {user_email} · {account_name} · {motion_type}"`.
    - Body: markdown, structured per §9 schema. Draft body must be verbatim — same subject, body, signature line as passed to `add_email`.
    - Return a brief final message — non-pursue log confirmation, or Pursue result with Pursuit Decision + Execution Status.

---

## 8. Email Composition Rules

**Target:** 60–90 words before signature (excluding meeting slots and booking links).

**Structure — 4 body sections in order:**

1. **Signal** (1 sentence) — specific verified event, not generic "your recent growth."
2. **Insight / bridge** (1–2 sentences) — why it caught attention. If bridge is Strong or Potential AND connection credible in one sentence, cite the concrete evidence artifact by name (opp name, deployment, workload label) — not vague filler like "our work with your team."
3. **ONE primary question** — genuinely one. No "or", no multiple clauses. Hypothesis language: "I'd be curious how you're handling", "I was wondering whether".
4. **Meeting ask** — always 30 minutes. One of 4 exact forms (per calendar outcome from Step 9).

**Followed by:**

- **Redirect line** — verbatim: *"If you're not the right person on this, I'd appreciate a pointer."*
- **Signature block** — 3 lines: `Best,` / `{first name}` / `{email}` from `metadata.user`.

**Decision tree for content pattern:**

| Relationship + Bridge | Pattern |
|---|---|
| Active/Warm + Strong bridge | Feature relationship + verified use case prominently, cite artifact by name |
| Active/Warm + Potential bridge | Reference relationship as credibility, use case as careful one-sentence bridge |
| Active customer + None-identified bridge + no personal relationship | Reference customer relationship when appropriate; don't force the use case |
| Historical-Stale / Weak / None | Do not imply active relationship. Signal-first. |

**Hypothesis discipline** — avoid: "I'd guess", "I know you're using", "you need Couchbase", "your architecture requires", "we work closely with your team" (unless supported).

**Style targets:** curious, technically credible, concise, natural, executive-friendly, phone-readable. NOT promotional, marketing-automation, or research-report.

---

## 9. Shadow Notification Schema

The maintainer-only Pursue notification is the primary observability surface. Schema:

- **Pursuit Summary** — Account, Motion, Signal, Target + confidence, Acting rep, Relationship status, Existing Couchbase use case, Couchbase bridge, Pursuit decision, Draft status, Execution status, Calendar status
- **Why Pursue** — Why now, signal candidates considered (chosen + 1–2 rejected), existing relationship, existing use case, concrete evidence artifact cited in email, connection to signal, why this target, biggest remaining uncertainty
- **Draft that landed on the rep's Home** — Subject / To / From + verbatim body
- **Evidence** — signal, why-now citation, relationship, use case, relevant people, recent Gmail/meeting evidence, historical transactions
- **Strategy** — approach, why, leverage existing relationship, warm intro decision, multi-threading recommendation
- **Internal Couchbase Hypothesis** — hypothesis, what would need to be true, what remains unverified
- **Discovery Questions** — 3–4 for rep prep (NOT in the customer email)
- **Next Best Actions** — up to 3 prioritized
- **Email QA** — every check (specific signal / existing relationship researched / leveraged / concrete artifact cited by name / recent activity leveraged / one primary question / word count / 30-min ask / natural tone / recipient / recipient repair attempted / redirect present / signature present / single `add_email` call)
- **Calendar QA** — calendar access / acting rep calendar used / three actual slots / spread across ≥2 days AND ≥2 time-of-day windows / 30-min duration / slots included / individual slot links (currently always NO) / general booking link / no fabricated availability
- **Workflow / Technical Diagnostics** — draft file ID, inbox item ID, write path (`rox_actions.add_email` — raw store, no re-edit), store write status, signal ID, workflow run ID, account ID, acting rep, booking URL supplied, `primary_contact` override delta if any, tool failures, soft failures, repair attempts, final repair result, validation failures

---

## 10. Failure Modes + Handling

**Design principle:** Staying green matters more than any single write, draft, or notification succeeding. Step 3 (org store write) is the primary contract; everything else is soft-failed.

| Failure | Handling |
|---|---|
| Missing required payload field | Halt at Step 1. Return message naming missing field. Store not touched. |
| Store read error | Treat as `{}`, continue. |
| Store write error | Note in final message, do NOT fail the run. |
| RQL error / no contacts / no opps | Record explicitly ("none") and continue. |
| Gmail error / no threads | Continue with RQL data. Never fail on Gmail. |
| External research error | Continue without it. |
| Calendar retrieval error | Fall back to booking URL if present (PARTIAL), else open-ended ask (FAIL). |
| Recipient email unresolvable via `enrich_email` | Use `[TODO: find email for <name>]` placeholder. Execution Status = BLOCKED. |
| `add_email` error | Note in final message + shadow (if it reaches Step 11). |
| `send_notification` error | Soft-fail. Final message notes it. Run finishes green. |

**Pursuit Decision vs Execution Status:** Reported separately.

- **Pursuit Decision:** PASS / WATCH / DISCARD based on research quality.
- **Execution Status:** READY (verified recipient + all QA PASS) / BLOCKED (placeholder recipient or critical QA failure) / PARTIAL (calendar PARTIAL or non-critical QA failure).

A pursuit can be strategically PASS while execution is BLOCKED.

---

## 11. Hard Rules

**Scope:**
- Steps 5–11 apply only to `pursue`. Watch / Wrong / Already Working remain log-only.
- Rep's Home gets ONE artifact on Pursue: the draft email. No webpage, dashboard, HTML report, chart, strategy brief.

**Investigation:**
- Steps 5–8 MUST complete before authoring in Step 10, even when the account looks net-new. Record absence explicitly; never assume.
- Preserve the Deep Dive hypothesis — every downstream action traces to original payload fields.

**Content:**
- Never hallucinate or overstate the relationship. Distinguish account-level customer status from personal relationship with the recipient.
- Cite the concrete evidence artifact by name when one exists. Vague filler when a named artifact was available fails Email QA.
- Existing use case is a lever, not a filler. Mention in email only when bridge is Strong or Potential + credible in one sentence + concrete artifact citable by name.
- One customer question only. Multiple discovery questions belong in the shadow.
- Warm-intro default rule (§7.2 Step 8) applies for Active/Warm accounts with known-but-not-technically-verified contacts.

**Calendar:**
- Always try `get_all_meetings` first. Booking URL alone is PARTIAL, not PASS.
- Never invent calendar availability. Never put `[TODO:]` in the customer body.
- Always 30-minute meetings, never 15.

**Recipient:**
- Enrichment is the ONLY approved repair path (via `enrich_email` before `add_email`).
- Placeholder recipient can NEVER be marked PASS.

**Write path:**
- `add_email` is a raw store — one call, no compose skill, no re-edit.
- `generate_email`, `edit_email_compose_v2`, `emit_email_compose_v2` are NOT attached and must not be requested.
- Signature/format failures are diagnostic-only — preserve artifact, do not attempt repair.

**Store:**
- `scope="org"`, only the `deep_dive_feedback` key. Never touch other org keys.
- `signal_id` sub-key used as-is. Lowercase `user_email`. Latest wins.
- Do not store `booking_url` in the log.

**Notifications:**
- Only Pursue authors and shadow-notifies.
- Shadow notification is maintainer-only telemetry — targets `db14b483-5501-44aa-9181-64c8e45f9f1e` exclusively.
- Skipped entirely when the acting rep IS the maintainer.
- Never send Rox notifications, confirmation emails, or in-app messages to the acting rep on any action — the Cloudflare Worker owns the rep-facing ack.

**Control:**
- The rep is in control. Nothing goes out automatically. No auto-send, no auto-schedule, no calendar events, no Rox tasks.
- Never send email or create calendar events. `email.send_email` is not attached. Calendar tool is read-only.

**Green:**
- Any failure in Steps 5–11 is a soft failure — note it + finish. Step 3 is the primary contract.
- Do not hide failures. Every FAIL surfaces explicitly in the shadow's Validation failures line.

---

## 12. Extension Points

**Configurable per rep** (currently via Cloudflare Worker):
- `booking_url` — Calendly / Google appointment URL, injected into every payload.

**Extension opportunities** (not yet implemented — see parking lot):
- Native calendar integration with per-slot bookable links (removes Cloudflare Worker workaround, upgrades every calendar outcome from text-slots to click-slots).
- Reply-tracking integration — feed reply/booking outcomes back into the Deep Dive learning loop.
- Per-team pursuit-decision policies — some teams may want stricter thresholds for "Pursuit: PASS" than others.
- Additional motion-type heuristics — the acquisition/M&A heuristic (target the acquiring company, not the acquired founder) is the pattern; others may need similar rules.

---

## 13. Test Runs Reference

Field-comparable test runs used during development:

| Run | Signal | Outcome | Key learning |
|---|---|---|---|
| Quantic | UK launch (Breathe Payments + HBM) | READY — signature stripped | First compose-skill truncation observed |
| Sierra.AI | Takeoff acquisition → Horizon | BLOCKED — placeholder recipient (`enrich_email` not yet attached) | Recipient enrichment gap identified |
| Wawa (Fly Thru) | Mobile pickup windows | BLOCKED — signature stripped | Signal freshness weaker than EV alternative |
| Wawa (EV) | Wawa-branded EV chargers | READY — clean | Warm-intro judgment call went the right way |
| NASA JPL | Quantum Space Innovation Center | BLOCKED — signature stripped | Prompt hardening insufficient; escalation needed |
| Wawa (`add_email`) | Wawa-branded EV chargers | READY — signature verified via `read_rox_file` | Structural fix eliminated the failure class; emergent word-count self-QA |

---

## 14. Deployment Notes

- **Save state:** Changes made via `set_agent_tools` / `update_instructions` / `update_agentflow` land as previews in the Rox workflow editor. They are NOT live until saved via the editor UI.
- **Webhook URL:** Regenerated only when the trigger is deleted and re-created. Save-then-copy after any trigger change.
- **Custom store:** Persistent across runs. To reset (e.g. before a fresh test cycle), call `rox_actions.custom_store_delete` on `deep_dive_feedback` scoped to org. Test runs write live to production store.
- **Test-run consequences:** Test runs are NOT sandboxed. `add_email` will actually save a draft to the acting rep's Home. `send_notification` will actually email the maintainer. `enrich_email` will actually consume provider credits. Use test runs judiciously.

---

## 15. Open Questions

- **Does Deep Dive's read side actually exist yet?** §4's action-semantics table defines the contract this agent writes against (suppress on watch/already_working, down-weight on wrong). Confirm whether the upstream Deep Dive agent's instructions have been updated to read `deep_dive_feedback` and act on it, or whether this is still write-only today.
- When does Rox ship the mapping API or `on_behalf_of` support, if per-rep webhook routing is still needed for any remaining single-tenant gaps?
- Reconciliation rule for duplicate `(account_id, motion_type)` dispositions across reps, if that scenario is possible — latest-wins is enforced per rep/signal_id, but cross-rep collisions aren't addressed here.
- Should the workflow maintainer's shadow notification include a way to flag a bad Pursue draft back into the QA loop, beyond the diagnostic trail already captured?
