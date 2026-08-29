# Deep Dive — how it works and why it isn't guessing

I built this to scan my accounts three mornings a week and surface a small number of high-confidence expansion plays — not summarize everything happening. Most of what it finds, I throw away. That's the point, and this walks through why. Every account, name, and finding below is invented for the walkthrough — none of it is a real customer.

> Full specs: [`deep-dive-design.md`](./deep-dive-design.md) (the agent) · [`deep-dive-feedback-design.md`](./deep-dive-feedback-design.md) (the pill buttons)

## 1. Which accounts I scan

If I own the account, it's in scope. Owning an opportunity on an account means I own the account too, so in practice this is one rule, not two.

| Account | Do I own it? | In scope? |
|---|---|---|
| Meridian Logistics | Yes | ✅ |
| Vantage Retail | No | ❌ |

The only other path in is an account I don't own yet, but where I own a Commit / Best Case / Closed Won opportunity on it — a defensive case for when account and opportunity ownership diverge, which doesn't really come up in our Salesforce setup.

## 2. What I'm looking for

Seven categories, each requiring a dated source — never a bare mention:

| Category | Example finding | Source type |
|---|---|---|
| New business unit | Meridian Logistics opened a digital fulfillment division | Trade press, Aug 2026 |
| New leader | Vantage Retail hired a VP of data platforms from a rival | LinkedIn, Jul 2026 |
| Acquisition | Northfield Bank acquired a fintech payments startup | Press release, Jun 2026 |
| Modernization | Arcadia Health issued an RFP to modernize core systems | Procurement notice, Aug 2026 |
| Real-time app | Solstice Games shipped live multiplayer matchmaking | Engineering blog, Jul 2026 |
| Competitive signal | Cascade Insurance job post lists MongoDB for a new claims platform | Job posting, Aug 2026 |
| Geo expansion | Ferro Manufacturing opened a new APAC distribution center | Trade press, May 2026 |

None of these publish on their own for me — every one still has to survive the gates below.

## 3. How I eliminate candidates

A real run, gate by gate:

| Step | Count | What's cut and why |
|---|---|---|
| Accounts scanned | 53 | — |
| Candidate findings | 25 | — |
| Gate 1 — real change? | 25 → 19 | −6: no dated evidence of an actual change |
| Gate 2 — specific whitespace? (strictest gate) | 19 → 9 | −10: whole-account mention, or already covered by the existing engagement |
| Gate 3 — credible Couchbase fit? | 9 → 6 | −3: generic "could help with scale" claim, no technical chain |
| Gate 4 — named person? | 6 → 6 | 0 discarded — 1 has no named contact, reclassified as watch instead |
| Gate 5 — warm path? | 6 → 6 | Never eliminates — only shifts score ±1–2 |
| Rank & select top 5 | 6 → 5 | −1: lowest-scoring signal held for next run, never padded up to fill a quota |
| **Published** | **5** | |

Gates 4 and 5 don't remove signals — they reclassify or reweight. Worth saying out loud to the team: I'm not tuned for volume, I'm tuned for confidence.

## 4. One that survives vs. one that doesn't

**Meridian Logistics** — new workload, score 7, published:

| Gate | Result |
|---|---|
| Changed? | ✅ Opened a digital fulfillment division, Aug 2026 |
| Specific whitespace? | ✅ New BU, nothing Couchbase touches there today |
| Credible fit? | ✅ Real-time inventory sync across warehouses |
| Named person? | ✅ Sarah Chen, VP digital fulfillment |
| Warm path? | None yet — net-new, still published |

**Vantage Retail** — new CIO hire, discarded:

| Gate | Result |
|---|---|
| Changed? | ✅ New CIO hired, Jul 2026 |
| Specific whitespace? | ❌ Mandate covers the order platform Couchbase already runs |
| — | Stops here. Remaining gates never run. |

Both accounts had a real, dated, verifiable event. I still cut the second one — the "already covered" test is where judgment does the work, not just citation-checking.

## 5. How I match contacts

| Order | Source | Example |
|---|---|---|
| 1 | Salesforce record | Sarah Chen — `linkedin_url` already on file → **used** |
| 2 | Verified enrichment | Only checked if Salesforce has nothing → fallback |
| 3 | Public search | Only a plausible, unverified match → fallback |
| 4 | Nothing checks out | Field left blank, never invented → **omit** |

I treat a fabricated LinkedIn URL as a defect, not a rounding error.

## 6. The four feedback pills

| Pill | What it does |
|---|---|
| 🎯 Pursue | Drafts a grounded outreach email, saved to Home for review |
| 👀 Watch | Logs it, notifies me, re-surfaces on a material update |
| ❌ Wrong | Logs it, down-weights this account/motion/contact combination |
| ✅ Already Working | Logs it, suppresses this motion in future runs |

Clicking a pill hands off to a separate system — boomerang page → Cloudflare relay → Rox webhook → feedback agent. See the feedback design doc for that architecture and the current single-tenant caveat.
