# Deep Dive — Design Doc

**Existing Account Expansion Intelligence Agent · Fresh Catch family**
**Version:** v4 (investigative voice, 4-step chain, relationship chip, Kyle-scoped)
**Status:** Live, cron-scheduled, Mon–Fri 7:00 AM ET

---

## 1. Mission & Positioning

Deep Dive helps sales reps find new selling motions inside existing named accounts.

> Fresh Catch finds new logos. Deep Dive finds new business inside logos we already own.

Deep Dive is an **intelligence agent, not a pitching agent**. It proposes credible reasons to investigate, not conclusions about what to sell. The rep decides what to sell; Deep Dive's job is to expose the surface.

Core question it answers:

> "Where is there a credible new selling motion inside an account I already own, and what is the best way to pursue it?"

It optimizes for **new selling conversations created inside existing accounts**, not signal volume.

---

## 2. Core Principle: Qualified Signals, Not News

A **Qualified Signal** is:

> A recent, evidence-backed change inside an existing customer account that indicates potential whitespace for a new Couchbase selling motion, and provides a reasonable path for the rep to act.

News is evidence, never output. A signal that fails any part of the chain — no specific whitespace, no credible workload fit, no named person — is discarded.

---

## 3. First Principle: Connection to a Specific Selling Motion

A person, event, announcement, or technology discovery cannot qualify on its own. It must connect to a specific potential selling motion.

**Bare signals that must never be published alone:**

- New hire — needs the workload/BU/initiative they own
- Funding round, earnings beat, $-amount announcement — needs the specific spend area
- Product launch — needs the org, workload, or contact tied to it
- Acquisition — needs the specific whitespace it opens
- Competitive database mention (MongoDB, DynamoDB, etc.) — needs the app/workload/team using it
- News or LinkedIn item with no downstream owner or workload

Every Qualified Signal states its motion in **one investigative sentence** before it earns a card.

---

## 4. Key Definitions

**Whitespace** — a meaningful organizational, workload, geographic, product, or initiative-level opening not already covered by the existing Couchbase engagement. Whitespace is *not* "no one is talking to Couchbase" (that's just cold) — it requires a specific opening the current engagement doesn't already address.

**Already covered** — the existing engagement demonstrably addresses the *same BU + same workload + same initiative*. High bar. Governed by the three-question test (§8); if any answer is "no," it's not covered.

**Couchbase hypothesis quality bar** — a technically credible reason to investigate Couchbase for the workload. Not proof it's the answer.

- ❌ "Couchbase could help with scalability."
- ✅ "The new payments platform will process high-volume transactional events across regions, suggesting a distributed operational workload where Couchbase's low-latency access and horizontal scalability may be relevant."

**Why It Matters — the locked 4-step chain.** Every "Why It Matters" walks:

1. Business event — what changed
2. Data workload — the shape of the data behind it
3. Technical characteristic — properties (real-time, distributed, high write rate, etc.)
4. Couchbase hypothesis — which Couchbase capabilities are a technically credible fit

If the chain doesn't walk, the signal fails Gate 3.

**Relationship state** (card-level, strongest to weakest):

| Icon | State | Meaning |
|---|---|---|
| 🟢 | Direct | Active Gmail thread with a contact tied to this motion, within 90 days |
| 🟡 | Internal | Known SFDC contact tied to the motion, no recent Gmail |
| ⚪ | New | No existing relationship; net-new outreach or Watch card |

---

## 5. Voice: Investigative, Not Salesy

Two hard rules:

1. The motion sentence starts with an investigative verb — *Explore / Investigate / Open a technical conversation about / Look at the data architecture behind.* Never "Sell." The rep decides what to sell.
2. The Couchbase POV lives in **Why It Matters**, not the motion sentence. The motion names the surface; Why It Matters explains why Couchbase is a credible answer to investigate for that surface.

---

## 6. The Gates (kill sequence 1→4, modifier 5)

Evaluated sequentially. All five must connect to the *same* motion.

| Gate | Test | On fail |
|---|---|---|
| **1 — Change?** | Identifiable, recent, evidence-backed change (BU, workload, leader, acquisition, modernization, etc.) | Discard |
| **2 — Specific whitespace?** (most important) | 2a. Name the specific BU/product/team/geo/workload — whole-account is not specific. 2b. Run the three-question "already covered" test; only discard if same BU + same workload + same initiative are *all* "yes." Don't rubber-stamp. | Discard |
| **3 — Couchbase hypothesis?** | Must meet the quality bar (§4) and walk the full 4-step chain | Discard |
| **4 — Relevant person?** | Named relevant person tied to the motion → pass. No person + strong motion → **Watch** (score capped at 6, monitoring action). No person + weak motion → discard. | Discard *or* Watch |
| **5 — Action path?** (classification modifier, never a kill) | Warm path → label "Warm path," +1 to +2 score. No warm path → label "Net-new relationship required," −1 to −2 score, floor at 5. Signal is kept either way. | — |

Note: a Gate 4 "Watch" and a Gate 5 "Net-new" are independent — a card can be both.

---

## 7. Motion Types (locked emoji)

| Emoji | Motion Type |
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

## 8. Deduplication Rules

- **Account identity:** SFDC Account ID primary. Resolve parent/subsidiary/acquired hierarchy before collapsing.
- **Opportunity dedup:** strict three-question test. An existing opp on the account is not automatic coverage.
- **Contact dedup match order:** (1) SFDC Contact ID → (2) email → (3) LinkedIn URL → (4) name+company → (5) name+title+company/domain.
- **Signal consolidation:** multiple findings pointing to the same person or motion collapse into ONE recommendation.

---

## 9. Expansion Score (1–10)

Status matters more than the numeric score — a Warm path 6 and a Net-new 8 are both Pursue-ready.

**Baseline factors:** meaningful change, clear org whitespace, workload relevance, evidence strength, decision-maker fit, competitive signal (esp. MongoDB), recency, action clarity.

**Modulators (small, deliberate):**

- Warm path: +1 to +2
- Net-new: −1 to −2, floor at 5
- Watch: cap at 6
- Vague motion: −2 (safety net)

**Anti-inflation rule:** a $500M announcement with no owner or workload scores lower than a specific new VP Eng standing up a real-time customer app.

---

## 10. Report Structure

**Header banner**
- 🤿 logo (never a fish)
- "Today's Deep Dive — {rep name}"
- Date subtitle: "Thursday, Aug 28 · Morning dive"
- Tagline: "Deep Dive finds new business inside logos we already own."

**Executive summary strip**
- 🌊 The Haul — count of qualified signals
- Status chips: 🟢 Warm path · 🟠 Net-new · 🔵 Watch
- Motion Type chips with counts

**Per-signal card** (ordered by status band, then score):
- Colored top strip (green/amber/blue by status) — status label + score chip
- Account name (with parent note if subsidiary)
- Motion Type chip
- Relationship chip (🟢 Direct / 🟡 Internal / ⚪ New) with short label
- **The Motion** — investigative sentence, aqua-bordered callout
- 🌊 **What Changed** — 1–3 sentences, inline `[source]` citation links
- 💡 **Why It Matters** — walks the 4-step chain
- 🎯 **Where to Go** — specific BU/workload/team/product/geo
- 👤 **Who to Talk To** — 1–3 contacts with per-contact path pills (🟢 SFDC / 🔵 Gmail / 🟠 cold), or "target roles" for Watch cards
- ⚓ **Recommended Action** — amber-bordered callout, tuned to card status (§11)
- 🧭 **Why this survived** — audit trail line summarizing gate outcomes
- Action pills — 🎯 Pursue · 👀 Watch · ❌ Wrong · Already Working (identical style, 36px height, `#d5e2ea` border, white bg, hover to teal)

**Footer**
- 🌊 Quality-over-quantity reminder
- Sources: Salesforce · Rox insights · Web research · Gmail
- Gmail visibility disclaimer (conditional)
- Generated-at timestamp

**Empty-state variant** — big 🌊, "Calm waters today," confidence-signaling copy about not padding.

---

## 11. Recommended Action, Tuned by Status

- **Warm path** → "Ask [existing champion] to introduce you to [new VP] on the [initiative]"
- **Net-new** → "Send discovery email to [name] referencing [specific initiative]" or "Prospect [role] at [BU] via LinkedIn"
- **Watch** → "Set a watch on [BU/workload]; re-evaluate when a named leader emerges"

---

## 12. Visual Design System (LOCKED)

**Palette**
- Background gradient: `#e6f2f5 → #c7e4ec → #a9d4e0`
- Navy `#0d2b3f` · Deep ocean `#1e4d6b` · Teal `#2e8b9e` · Aqua `#4fb8c9`
- Warm (kelp green) `#2f9e6a` · Net-new (sunset amber) `#e08a3c` · Watch (deep blue) `#3a7bb8`
- Text primary `#0d2b3f` · Secondary `#436577` · Muted `#6f8898`
- Border `#d5e2ea` · Hover `#f3fafc`

**Typography** — system font stack; 32px/700 header, 20px/600 motion, 15px/1.55 body, 12px/600 uppercase small labels.

**Layout** — 880px max width, 16px card radius, 24px card padding, 24px card gap.

**Iconography (locked list)**
- Brand mark: 🤿 (never a fish)
- Section icons: 🌊 What Changed · 💡 Why It Matters · 🎯 Where to Go · 👤 Who to Talk To · ⚓ Recommended Action · 🧭 Why this survived
- Motion Type emojis: §7
- Status dots: 🟢 🟠 🔵
- Relationship dots: 🟢 Direct · 🟡 Internal · ⚪ New

**Determinism** — the report is rendered by a **locked Python renderer**, not an LLM. Same HTML skeleton, byte-identical, every day. Inline styles only — no `<style>` tag — so it renders the same in Home and in email (Outlook, Gmail).

---

## 13. Trigger & Schedule

- Trigger: cron schedule
- Expression: `0 7 * * 1-5` (Mon–Fri, 7:00 AM)
- Timezone: `America/New_York`

---

## 14. Variables

| Name | Type | Value |
|---|---|---|
| `target_rep_id` | str | `e58b527c-ad82-49ea-9833-bc37ddce89cb` (Kyle Lakind) |
| `target_rep_name` | str | Kyle Lakind |
| `target_rep_email` | str | kyle.lakind@couchbase.com |
| `feedback_url` | str | https://melboulos.github.io/deep_dive_feedback/ |

Swap `target_rep_*` per subscriber. For team rollout: fan out per rep, or duplicate the agent per rep.

---

## 15. Whose Book, Whose Home

- **Running user** (report recipient): sends the report to themselves; email uses their own connected mailbox.
- **Target rep** (analyzed): accounts / opps / contacts / Gmail all scoped to the target rep's `rox_user_id`.
- **Where the report lands:** running user's Home + running user's inbox.
- **Feedback attribution:** buttons carry the target rep's identifiers so feedback logs against their history.
- **Governance caveat:** RQL runs as the running user. Naming the target rep's `rox_user_id` in the read filters on them, but the result set is intersected with what the running user can see. Works cleanly when the running user has broad account visibility (SE, admin). If Gmail isn't visible for the target rep, a footer disclaimer fires.

---

## 16. Rendering Pipeline

Zero drift is achieved by taking the LLM out of the rendering path:

1. Agent computes the **payload** (JSON, pure data, no HTML) — passes all gates, dedup, scoring, motion sentences, relationship states, contacts, why-survived audit lines.
2. `code.execute_python` runs a **locked renderer** (baked into the instructions verbatim) that renders the payload into HTML with inline styles.
3. `rox_actions.add_html` publishes to Home.
4. `email.send_email_as_user` emails the same HTML from the running user's mailbox to themselves.

Home render and email render are identical strings. No LLM re-generation between runs. Editing the visuals means editing the Python template, not the instructions.

---

## 17. Tools Attached

| Tool | Purpose |
|---|---|
| `agent_outputs.generate_agent_response` | External research per account, with citations |
| `rox_actions.get_insights` | Pre-computed Rox change signals (last 7 days) |
| `email.list_emails` / `email.get_email` | Gmail relationship mining, scoped to target rep |
| `code.execute_python` | Locked HTML renderer |
| `rox_actions.add_html` | Publish to Home |
| `email.send_email_as_user` | Email from running user's own Gmail/Outlook |

**Deliberately not attached:**
- `agent_outputs.generate_webpage` — LLM-based, causes drift
- `email.send_email` — Rox platform sender, triggers graymail
- `sql.*` — RQL is built-in for CRM reads

---

## 18. Hard Rules

**Never:**
- Call `generate_webpage` or `send_email`
- Modify the Python renderer code
- Substitute palette, fonts, icons, button spec, or layout
- Use a fish emoji as the logo
- Reference Fresh Catch in the report
- Start the motion sentence with "Sell"
- Skip the 4-step chain in Why It Matters
- Publish a bare person / event / announcement / tech mention
- Recommend a motion already being actively pursued
- Rubber-stamp "already covered" — always run the three-question test
- Discard at Gate 5 — it's a classification modifier
- Pad the report to 3–5 when fewer qualify
- Scope reads to the running user when a target rep is set

**Always:**
- Scope every read to the target rep
- Write the investigative motion sentence before evaluating gates
- Walk the 4-step chain on every card
- Compute the card-level relationship state
- Include the "Why this survived" audit line on every card
- Order signals by status band (Warm > Net-new > Watch), then score descending
- Render deterministically via Python, publish via `add_html`, email via `send_email_as_user`

---

## 19. Feedback Loop (companion agent, currently blocked)

**Deep Dive Feedback** — webhook-triggered sibling agent.

```
Report card button
  → https://melboulos.github.io/deep_dive_feedback/?action=… (GitHub Pages boomerang)
    → https://rox-deep-dive-proxy.mel-boulos-97e.workers.dev (Cloudflare Worker, adds CORS)
      → https://webhooks.backend.rox.com/webhooks/w/… (Rox webhook)
        → Deep Dive Feedback agent
```

**Branch behavior:**
- 🎯 Pursue → grounded personalized outreach email draft to Home
- 👀 Watch → log + in-app notification
- ❌ Wrong → log + notification, down-weight in future runs
- ✅ Already Working → log + notification, suppress in future runs

**Persistence:** each feedback event → workflow custom store under `feedback:{signal_id}` + per-user log at `feedback_log:{user_id}`. Future Deep Dive runs read this history to suppress previously actioned signals.

**Current status:** Rox webhook returns 200 to POSTs but doesn't fire runs. Agent logic works via synthetic test. Support ticket open. Not blocking Deep Dive itself — pills render as anchor links regardless; they'll activate retroactively once Rox fixes the ingress.

---

## 20. Deep Dive Insights (analytics companion, spec ready)

Daily org-wide dashboard, 8:00 AM ET, rolling 7-day view. Publishes to Home + emails Mel.

**Scope:** all Salesforce account owners (auto-discovered).

**What it measures:**
- Adoption — which reps are receiving Deep Dive, which aren't
- Volume — runs / signals per rep
- Engagement — feedback rate, action breakdown
- Quality mix — status band + motion-type distribution across the team

**Layout:**
1. Team Haul summary (runs, signals, feedback, feedback rate %)
2. Team status mix + motion mix + action breakdown
3. 🧭 Adoption gap card — reps who own accounts but aren't yet subscribed
4. Per-rep drill-down cards (status mix, action mix, motion mix, last report timestamp, quiet-week flag)
5. Feedback-data-delayed banner (conditional, until the webhook fix ships)

Config drafted; ready to paste when the shell agent is created.

---

## 21. Progressive Autonomy Ladder

| Level | Behavior | Deep Dive Status |
|---|---|---|
| 1 — Intelligence | Find → Explain → Recommend | ✅ Live |
| 2 — Preparation | Research → Draft → Prepare action | ✅ Pursue draft (blocked on webhook) |
| 3 — Assisted Execution | Performs approved actions after rep confirmation | Not yet |
| 4 — Trusted Autonomy | Auto-executes authorized action classes | Not yet |

---

## 22. Parking Lot (future capability)

- **Calendar intelligence** — brief agenda-driven prep 30 min before customer meetings; new-attendee detection; introduction opportunities
- **Feedback-informed suppression** — Step 0 on each run reads `feedback_log` to skip signals the rep already actioned
- **Multi-rep fan-out** — one Deep Dive run per rep in the roster, each report on that rep's Home
- **Slack delivery** — daily digest snippet to a shared Slack channel for leadership visibility (requires Slack integration)
- **Rep training loop** — feedback events tune per-rep weights (e.g. rep A weights Competitive Displacement higher; rep B ignores Geographic Expansion)

---

## 23. North-Star Metric

Deep Dive optimizes for:

> New selling conversations created inside existing customer accounts.

Not:
- Number of signals surfaced
- Number of news stories found
- Number of contacts identified
- Volume of research

The ideal daily outcome is a small number of high-confidence, actionable expansion plays that make the rep say:

> "I didn't know that was happening inside my account. I know exactly who I should call."

---

## 24. Current Build Status

| Component | Status |
|---|---|
| Deep Dive agent | ✅ Saved, active, cron-scheduled |
| Instructions | ✅ v4 (investigative voice, 4-step chain, relationship chip, Kyle-scoped) |
| Locked Python renderer | ✅ Baked into instructions |
| Cloudflare Worker relay | ✅ Deployed with CORS, **now git-tracked with CI/CD (see §25)** |
| GitHub Pages boomerang | ✅ Deployed, git-backed |
| Home publish | ✅ Working |
| Email delivery (`send_email_as_user`) | ✅ Fixes graymail |
| Deep Dive Feedback agent | ✅ Logic works, ⚠️ webhook blocked on Rox platform bug |
| Deep Dive Insights | 📋 Full config ready to paste |

---

## 25. Repo & Deployment Infrastructure

Both pieces of Deep Dive Feedback's supporting infrastructure — the GitHub Pages boomerang page and the Cloudflare Worker CORS relay — now live entirely in [`melboulos/deep_dive_feedback`](https://github.com/melboulos/deep_dive_feedback) as the single source of truth. Neither the Cloudflare dashboard nor GitHub Pages settings should be hand-edited going forward; every change flows through git.

### Repo layout

```
deep_dive_feedback/
├── index.html                        # GitHub Pages boomerang page
├── worker/
│   ├── src/index.js                  # Cloudflare Worker source (CORS relay → Rox webhook)
│   └── wrangler.toml                 # Worker config: name, main entry, compatibility date, account_id
├── docs/
│   ├── deep-dive-design.md           # this document
│   └── DEPLOYMENT.md                 # full deploy runbook, secrets setup, rollback steps
└── .github/workflows/
    └── deploy-worker.yml             # CI: deploys worker/ to Cloudflare on every push to main
```

### How each piece deploys

| Component | Trigger | Mechanism |
|---|---|---|
| `index.html` | Push to `main` | GitHub Pages' built-in `pages-build-deployment` — no custom Action needed, was already git-backed |
| `worker/src/index.js` | Push to `main` touching `worker/**` | Custom GitHub Action (`deploy-worker.yml`) using `cloudflare/wrangler-action@v3`, authenticated via repo secrets |

### One-time setup completed

- Pulled the live Worker script out of the Cloudflare dashboard via the Workers API (`GET /accounts/{account_id}/workers/scripts/{script_name}`) and committed it as the git baseline.
- Added `worker/wrangler.toml` with explicit `main = "src/index.js"` and `account_id` — both required for Wrangler to run non-interactively in CI (relying only on the Action's `accountId` input was insufficient; Wrangler needs it in-file too).
- Created a Cloudflare API token (Edit Cloudflare Workers template, no IP restriction — GitHub-hosted runners don't have stable IPs to allowlist) and stored it as the `CLOUDFLARE_API_TOKEN` repo secret, alongside `CLOUDFLARE_ACCOUNT_ID`.
- Widened the GitHub PAT used for git auth to include the `workflow` scope — required specifically to push changes under `.github/workflows/`, which GitHub blocks by default on tokens without it.

### Ongoing workflow

```bash
# edit worker/src/index.js
git add worker/src/index.js
git commit -m "describe the change"
git push origin main
# Action deploys to Cloudflare automatically, ~20s
```

Rollback is a `git revert` + push — both the Action and Pages redeploy the reverted state the same as any other push. Full runbook, including secret rotation and troubleshooting notes, lives in `docs/DEPLOYMENT.md`.

### Known open item

The Worker's CORS header is currently `Access-Control-Allow-Origin: "*"`, meaning any origin — not just the GitHub Pages boomerang page — can invoke the relay and trigger the Rox webhook. Low risk today given the relay only forwards structured feedback-button payloads, but worth tightening to the specific Pages origin (`https://melboulos.github.io`) if this relay's exposure ever needs hardening.

---

## Changelog

- **v4** (current) — investigative voice rules, locked 4-step "Why It Matters" chain, card-level relationship state (Direct/Internal/New), Gate 5 reclassified as non-kill modifier, deterministic Python renderer replacing `generate_webpage`, ocean/diving visual system locked, `send_email_as_user` replacing `generate_webpage`-driven email. **Deployment infra**: Worker source and CI/CD pipeline added to git (§25) — Cloudflare dashboard is no longer the source of truth for `worker.js`.
- **v2** — Kyle-scoped instructions, feedback-link-aware report, initial 5-gate sequence, HTML report via `generate_webpage`.
