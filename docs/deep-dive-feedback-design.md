# Deep Dive Feedback — Technical Design

**Owner:** Mel Boulos
**Status:** Deployed (single-tenant); multi-tenant pending Rox platform work
**Last updated:** August 2026

> Companion document to [`deep-dive-design.md`](./deep-dive-design.md). Deep Dive is the intelligence agent that surfaces signals and renders the pill buttons; Deep Dive Feedback is the separate agent + infrastructure that those pills call out to. Deep Dive does not know whether a pill was clicked — it only renders the links.

---

## 1. Purpose

Give every rep on the Couchbase team a one-click way to disposition Deep Dive expansion signals, so:

- Their choice is durably logged and can be read back by future Deep Dive runs for suppression / model tuning.
- On pursue, a personalized, grounded outreach email draft is created for review.
- On watch / wrong / already_working, the rep gets a confirmation notification.

The rep experience is: click a pill, see a confirmation card, either get a notification or find a draft email in Rox Home. No app to open, no form to fill.

---

## 2. User-Facing Flow

```
Deep Dive surfaces a signal
    ↓
Rep sees 4 pill buttons (🎯 Pursue, 👀 Watch, ❌ Wrong, ✅ Already Working)
    ↓
Rep clicks one
    ↓
Static confirmation page shows "⏳ Logging your feedback…"
    ↓
Feedback is durably logged in Rox
    ↓
Confirmation card updates to success (or ⚠️ on failure)
    ↓
Side-effect runs asynchronously in Rox:
    - Pursue → email draft appears in rep's Home under Recommended Actions
    - Watch/Wrong/Already Working → notification lands in rep's Rox inbox
```

---

## 3. Architecture

```
Rep's browser
    │
    ├── GET https://melboulos.github.io/deep_dive_feedback/?action=<a>&signal_id=<sid>&…
    │       │
    │       └── GitHub Pages returns static index.html
    │
    └── JavaScript in index.html:
        POST JSON payload → Cloudflare Worker (proxy)
                │
                └── Worker: adds CORS headers on its response,
                    adds browser User-Agent, forwards to Rox webhook
                        │
                        └── Rox webhook: accepts, queues, triggers agentflow
                                │
                                └── Agent (LLM):
                                    - validates payload
                                    - names run
                                    - writes to custom store
                                    - branches on `action`
                                    - drafts email (pursue) or sends notification
```

Three pieces of infrastructure:

- **GitHub Pages** — hosts the static feedback page (`index.html`).
- **Cloudflare Worker** — 30-line proxy that solves two Rox platform limitations (see §6).
- **Rox Agentflow** — the actual business logic; LLM-based, no fixed DAG.

---

## 4. Contracts

### 4.1 Boomerang URL (Deep Dive → browser)

```
https://melboulos.github.io/deep_dive_feedback/?
  action=<pursue|watch|wrong|already_working>&
  signal_id=<stable-uuid-for-the-signal>&
  account_id=<salesforce-account-id>&
  account_name=<url-encoded>&
  motion_type=<url-encoded, e.g. "New Workload">&
  score=<1-10>&
  primary_contact_email=<url-encoded>&
  primary_contact_name=<url-encoded>&
  user_email=<rep-email>&
  user_id=<rep-rox-user-id>&
  workflow_run_id=<deep-dive-source-run-id>
```

All fields are strings. `action`, `signal_id`, `user_id` are required; others are optional but recommended.

### 4.2 Browser → Cloudflare Worker

**Method:** POST · **Content-Type:** `application/json` · **Body:** full URL param object serialized as JSON (URL params flattened; no wrapper).

Example:

```json
{
  "action": "pursue",
  "signal_id": "155a0897b3b4",
  "account_id": "2efd731a-1532-469e-a5f6-3e9d943bcec9",
  "account_name": "Acme Health System",
  "motion_type": "New Workload",
  "score": "8.8",
  "primary_contact_email": "jane.doe@example.com",
  "primary_contact_name": "Jane Doe",
  "user_email": "kyle.lakind@couchbase.com",
  "user_id": "e58b527c-ad82-49ea-9833-bc37ddce89cb",
  "workflow_run_id": "dbf5e7e0-bc1f-4c2b-98e8-36fe8bc357d1"
}
```

### 4.3 Cloudflare Worker → Rox Webhook

**Method:** POST · **URL:** `https://webhooks.backend.rox.com/webhooks/w/<workflow-webhook-id>`
**Headers:** `Content-Type: application/json`, `User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36`
**Body:** passthrough of browser body.

Success response (from Rox): `{"event_id": "<uuid>", "status": "accepted"}`.

### 4.4 Rox Webhook → Agentflow Trigger

The webhook payload lands on `trigger_data.payload` as a structured object (all fields flat, all strings).

---

## 5. Agentflow Logic

Named: **🤿 Deep Dive Feedback**

**Trigger:** webhook. **Runtime:** Rox agentflow (LLM decides tool calls based on instructions).

### 5.1 Available Tools

- `agent_outputs.generate_email` — save an email draft to Home.
- `agent_outputs.generate_agent_response` — research agent with web-search + citations.
- `rox_actions.send_notification` — Rox in-app + email notification to a specific `rox_user_id`.
- `rox_actions.custom_store_get` — read persisted value.
- `rox_actions.custom_store_set` — write persisted value.
- `rox_actions.custom_store_batch_set` — write multiple keys atomically.
- *(Implicit)* RQL data-read tools available to every agentflow at runtime — used to query the Rox catalog (companies, contacts, deals) with rep-scoped permissions.

### 5.2 Execution Sequence

Every run, in order:

1. **Validate payload.** If `action` or `signal_id` is missing / empty / invalid, send one "invalid payload" notification to the workflow owner and halt.

2. **Set run name** to `"{action} · {account_name} · {motion_type}"` via built-in `set_run_name`.

3. **Log to custom store** (always, before branching):
   - `custom_store_get(feedback_log:{user_id})` — read rep's history.
   - `custom_store_batch_set` writing both:
     - `feedback:{signal_id}` → full payload + `logged_at` timestamp (durable per-signal record).
     - `feedback_log:{user_id}` → history list with `{signal_id, action, motion_type, timestamp}` appended.
   - Custom store scope: **workflow** (isolated to this agent, shared across its runs).

4. **Branch on `action`:**

   **pursue:**
   - RQL: account row (industry, size, region, Couchbase footprint columns, initiatives), existing contacts, closed-won opps, open opps.
   - Optional focused research via `generate_agent_response` if RQL alone doesn't ground the motion.
   - `generate_email` with `save_to_homepage="save"`. Prompt enforces: name in greeting; reference specific motion + concrete trigger; discovery framing not pitch; Couchbase relevance as hypothesis; one CTA (15-min discovery call); under 150 words; natural voice; no marketing phrases. Recipient = `primary_contact_email` or `[TODO: find email]` placeholder if missing.

   **watch:**
   - `send_notification` to `user_id`.
   - Subject: `"Watching {account_name} · {motion_type}"`.
   - Body: `"Deep Dive will re-surface this signal when there's a material update."`

   **wrong:**
   - `send_notification` to `user_id`.
   - Subject: `"Feedback logged: {account_name}"`.
   - Body: `"Thanks — Deep Dive will down-weight this account/motion/contact combination in future runs."`

   **already_working:**
   - `send_notification` to `user_id`.
   - Subject: `"Skipping {account_name} · {motion_type}"`.
   - Body: `"Deep Dive will suppress this motion in future runs."`

### 5.3 Guardrails Baked Into the Prompt

- **Log first, branch second.** Store write happens before any branch action so a failed side-effect never loses feedback.
- **Never sends a real email.** Pursue drafts to Home only. `email.send_email` is not attached to the workflow.
- **Invalid payloads halt cleanly.** No partial state; exactly one notification + stop.
- **Pursue emails must be grounded.** No generic "just checking in" language. If RQL returns nothing usable, the draft body carries a `[TODO: needs grounding — RQL returned nothing on X]` note rather than filler.
- **Custom store scope is workflow.** History is shared across runs of this agent but isolated from other workflows.
- **Suppression list format is fixed.** `feedback_log:{user_id}` entries are exactly `{signal_id, action, motion_type, timestamp}`, append-only, chronological.

---

## 6. Why the Cloudflare Worker Exists

Two Rox platform limitations force a proxy:

**A. CORS not supported on webhook OPTIONS preflight.** A browser posting `Content-Type: application/json` to a cross-origin URL triggers a preflight OPTIONS request. Rox's webhook endpoint responds 204 with no `Access-Control-Allow-*` headers, so the browser blocks the actual POST. Verified with `curl -X OPTIONS`.

**B. WAF blocks Cloudflare Worker default User-Agent.** Once the Worker was in place, requests still returned 403 Forbidden (HTML) from a CloudFront layer in front of Rox. Setting the outbound fetch User-Agent to a normal browser string fixed it. Verified by A/B'ing the header.

The Worker exists solely to translate these two things — it does no application logic. If Rox added CORS headers to OPTIONS and stopped WAF-blocking on User-Agent, the Worker could be removed entirely and `index.html` could POST directly to the Rox webhook.

---

## 7. Data Model — Rox Custom Store

Scope: **workflow** (isolated to this agent).

**Key:** `feedback:{signal_id}`
Type: object. Written on every successful run (upserted; last write wins for a given `signal_id`).

```json
{
  "action": "pursue",
  "signal_id": "155a0897b3b4",
  "account_id": "…",
  "account_name": "…",
  "motion_type": "…",
  "score": "…",
  "primary_contact_email": "…",
  "primary_contact_name": "…",
  "user_email": "…",
  "user_id": "…",
  "workflow_run_id": "…",
  "logged_at": "2026-08-28T09:43:23Z"
}
```

Consumer: Deep Dive's suppression / audit / analytics layer.

**Key:** `feedback_log:{user_id}`
Type: array of objects. Append-only. Chronological.

```json
[
  {"signal_id": "…", "action": "watch",           "motion_type": "…", "timestamp": "2026-08-28T09:36:38Z"},
  {"signal_id": "…", "action": "pursue",          "motion_type": "…", "timestamp": "2026-08-28T09:43:23Z"},
  {"signal_id": "…", "action": "already_working", "motion_type": "…", "timestamp": "2026-08-28T09:54:47Z"}
]
```

Consumer: Deep Dive reads this at the top of each run to decide whether to suppress or down-weight signals for that rep. Semantics for reconciliation across duplicate `(account_id, motion_type)` are left to Deep Dive — typical rule is "most recent entry wins."

---

## 8. Failure Modes and Behavior

| Failure | Where | Result | Observability |
|---|---|---|---|
| Missing `action` or `signal_id` | Agent step 1 | Halt after one "invalid payload" notification to workflow owner | Rox run trace |
| Unknown `action` value | Agent step 4 | Halt after one "invalid payload" notification; step 3 log already succeeded | Rox run trace |
| Custom store write failure | Agent step 3 | Run fails; branch does not execute; no notification / draft sent | Rox run trace; no user-visible confirmation |
| `generate_email` failure (Pursue) | Agent step 4 (pursue) | Run fails after log write; no draft in Home. Feedback still logged. | Rox run trace |
| Rox WAF rejects Worker request | Worker → Rox | Worker returns 403 HTML to browser; index.html renders ⚠️ card | Browser DevTools Network + Cloudflare Worker logs |
| Cloudflare Worker down / cold-start slow | Browser → Worker | fetch fails / times out; index.html renders ⚠️ card | Cloudflare Workers dashboard (invocations, error rate) |
| Boomerang page never loads (GitHub Pages outage) | Browser | Rep sees browser error page | GitHub Pages status |
| Rep clicks the same URL twice | End-to-end | Two runs, both log. `feedback:{signal_id}` last write wins; `feedback_log:{user_id}` has both entries. Rep sees two confirmation notifications. | Rox runs list |
| Invalid JSON body | Worker → Rox | Rox returns HTTP 200 `{"message":"Only JSON payloads are supported","status":"rejected"}`. Worker returns that to browser; index.html renders ⚠️. | Cloudflare Worker logs; Rox side won't create a run |

---

## 9. Multi-Tenant Model — Current State and Gap

**Current state (single-tenant):**

- One workflow, owned by Mel.
- One webhook URL.
- All reps' clicks go to that single webhook.
- Because Rox agentflows run under the workflow owner's identity, side effects that are not `send_notification` execute as Mel:
  - `generate_email` drafts land on Mel's Home, regardless of the payload's `user_id`.
  - RQL reads scope to Mel's account permissions.
  - `emit_email_compose_v2` auto-appends Mel's Gmail signature.
  - `send_notification` correctly targets the payload's `user_id`, so watch/wrong/already_working confirmations reach the right person.

**The gap:** for pursue, the acting rep never sees their own draft. If the rep were somehow to see it and send it, it would go out from Mel's mailbox under Mel's signature.

Rox's stated intermediate: sharing the workflow with a rep in the Rox UI generates a per-rep webhook URL; runs triggered via that URL execute under the rep's identity. Delivered by asking Rox support for the per-user webhook URLs.

**Field deployment shape (this workaround):**

- One workflow (Mel-owned), shared with each rep in Rox → per-rep webhook URL from Rox.
- One Cloudflare Worker with a hardcoded `user_id` → `webhook_url` routing table.
- Deep Dive builds the same boomerang URL for every rep. Worker reads `user_id` from the JSON body and forwards to the right per-rep webhook.

Adding a rep = share workflow in Rox → grab webhook URL → add one line to Worker's routing table → commit + push. GitHub Actions auto-deploys the Worker in ~30s.

**Long-term goal (Rox roadmap):** either a mapping API so the Worker can fetch `{user_id: webhook_url}` dynamically without a hardcoded table, or single-webhook + `on_behalf_of` routing so the Worker's routing goes away entirely. Rox has confirmed both are on the roadmap; timeline TBD.

---

## 10. Deployment Artifacts

### 10.1 GitHub Pages

- Repo: `melboulos/deep_dive_feedback`
- Live URL: `https://melboulos.github.io/deep_dive_feedback/`
- Contents: single `index.html` (static, no build step).
- Deploy: push to `main`; GitHub Pages auto-serves.

### 10.2 Cloudflare Worker

- Repo: `melboulos/rox-deep-dive-proxy` (connected to Cloudflare via GitHub Action)
- Live URL: `https://rox-deep-dive-proxy.mel-boulos-97e.workers.dev`
- Contents: `worker.js` (routing + CORS + WAF UA handling), `wrangler.toml`, `.github/workflows/deploy.yml`.
- Deploy: push to `main` → GitHub Action runs `wrangler deploy` → Cloudflare active in ~30s.
- Auth: Cloudflare API token stored in GitHub repo secrets.

### 10.3 Rox Agentflow

- Name: 🤿 Deep Dive Feedback
- Trigger: webhook (auth disabled).
- Tools attached: 6 (see §5.1).
- Owner: Mel Boulos.
- Shared with: (list of reps as onboarded).

---

## 11. Test Strategy

**Unit-level (curl):**

```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"action":"watch","signal_id":"sig-test-001","account_id":"…","account_name":"Test","motion_type":"…","score":"8","user_id":"<rep-rox-user-id>"}' \
  https://rox-deep-dive-proxy.mel-boulos-97e.workers.dev
```

Expected: `{"event_id":"…","status":"accepted"}`. Rejects mean either Worker code regression or Rox WAF change.

**Integration-level (browser):**

Load a well-formed boomerang URL in a real browser. Confirm:

- Boomerang page renders spinner then success card.
- Rox run appears in agentflow's Recent Runs within ~5s.
- Run trace shows all expected tool calls (validate → set run name → log → branch).
- On pursue: draft appears in target rep's Home Recommended Actions.
- On watch/wrong/already_working: notification appears in target rep's Rox inbox and email.

**End-to-end (production):**

Deep Dive fires a real signal. Rep clicks a pill. Confirmation card appears. Draft or notification lands on rep's side.

---

## 12. Observability

- **Rox agentflow runs:** run history in the agentflow UI, plus tool-level traces per run. Every step's inputs and outputs captured.
- **Cloudflare Worker:** invocation count, error rate, and per-request logs in the Cloudflare Workers dashboard.
- **GitHub Pages:** static hosting, no observability beyond GitHub's uptime dashboard.
- **Rox custom store:** durable and queryable via subsequent runs; no dedicated UI, but `custom_store_get` reads are visible in traces.

---

## 13. Known Limitations

- **Multi-tenant routing is manual.** Adding a rep requires editing a hardcoded routing table in `worker.js` and pushing. Blocked on Rox roadmap; see §9.
- **Draft signature is workflow-owner's, not the acting rep's,** if using single-tenant model. Same root cause as §9.
- **No auth on the boomerang page.** Anyone with a URL can log feedback for any signal. Acceptable because signal IDs are UUIDs and the surface area is a rep-only internal tool; not acceptable for external / customer-facing use.
- **Optimistic success rendering fixed, but no retry.** If the initial fetch fails, the ⚠️ card tells the rep to close the tab and try again. There's no in-page retry button.
- **`feedback_log:{user_id}` grows unbounded.** No archival strategy. At current rep volume this is fine for years; would need pruning at scale.
- **Pursue email drafts are LLM-generated and un-reviewed pre-Home.** Rep reviews before sending. Acceptable because human is the send-gate; would not be acceptable if drafts were auto-sent.

---

## 14. Extension Points

- **New action types.** Adding a fifth pill (e.g. `snooze_30d`) is a matter of: new URL param handling in `index.html` (already dynamic), new branch in the agent instructions, new `ACTION_META` entry for the confirmation copy.
- **Richer suppression semantics.** Currently `feedback_log` is a flat append-only list. Could be extended to per-`(account_id, motion_type)` state (`suppressed_until`, `suppressed_reason`) if Deep Dive's read side warrants it.
- **Cross-workflow feedback aggregation.** Custom store scope is workflow, so this agent's log is isolated. If team-wide aggregate reads are desired, either change scope to org (requires care around isolation) or expose an aggregation endpoint.
- **Pull-based agentflow.** If Deep Dive wants the feedback pushed into its own run context instead of pulling from the store, this agent could POST to a Deep Dive webhook as its final step.

---

## 15. Open Questions

- When does Rox ship the mapping API or `on_behalf_of` support? (Blocks fully-automated onboarding.)
- How does Deep Dive read `feedback_log`? Direct custom-store read via its own agentflow, or does it expect a query API? (Consumer contract is currently implicit.)
- Reconciliation rule for duplicate `(account_id, motion_type)` dispositions. Most-recent-wins is intuitive but not enforced by this agent. Should it be?
- Should the workflow-owner get any audit notification when reps disposition signals? Currently silent — only the acting rep is notified.
