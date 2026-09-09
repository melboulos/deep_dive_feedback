// worker/src/index.js
// Deep Dive Feedback proxy with live-editable rep routing + booking URL injection,
// plus Fresh Catch Pursue signed forwarding and per-rep Pursue webhook mapping.
//
// Routes:
//   POST /                       → route to per-rep Rox webhook based on payload.user_id,
//                                  inject rep's booking_url into payload before forwarding
//   POST /fresh-catch-pursue     → validate + rate-limit + sign + forward to the
//                                  authenticated Fresh Catch Pursue Rox webhook
//   GET  /pursue-webhooks.json   → public read-only map { rep_email_lower: pursue_url }
//                                  consumed by Fresh Catch to render per-rep 🎯 Pursue pills
//   OPTIONS /                    → CORS preflight for the boomerang page
//   GET  /admin                  → HTML admin page (basic auth)
//   POST /admin/save             → upsert or remove a rep in KV (basic auth)
//
// Bindings:
//   ROX_ROUTING                    — KV namespace: user_id → { name, email, user_id, webhook_url, booking_url, pursue_webhook_url }
//   ROX_EVENTS                     — KV namespace: recent unknown-user_id events (7d TTL)
//                                     + pursue rate-limit buckets (2m TTL)
//   ADMIN_PASSWORD                 — secret; used by basic auth on /admin
//   ROX_PURSUE_WEBHOOK_URL         — secret/var; Rox-generated URL for the Fresh Catch Pursue workflow
//   ROX_PURSUE_WEBHOOK_SIGNING_KEY — secret; signing key issued by Rox when the Pursue workflow was saved

const DEFAULT_WEBHOOK =
  "https://webhooks.backend.rox.com/webhooks/w/workflow-webhook-318d6a1b";
const BROWSER_UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36";

// -------------------- shared helpers --------------------

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function requireBasicAuth(request, env) {
  const auth = request.headers.get("Authorization") || "";
  const expected = "Basic " + btoa(`admin:${env.ADMIN_PASSWORD}`);
  if (auth !== expected) {
    return new Response("Unauthorized", {
      status: 401,
      headers: { "WWW-Authenticate": 'Basic realm="rox-deep-dive-admin"' },
    });
  }
  return null;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

// -------------------- feedback proxy (Deep Dive — unchanged) --------------------

async function handleProxy(request, env) {
  if (request.method === "OPTIONS")
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  if (request.method !== "POST")
    return new Response("Method not allowed", { status: 405, headers: CORS_HEADERS });

  const rawBody = await request.text();
  let userId = null;
  let parsed = null;
  try {
    parsed = JSON.parse(rawBody);
    userId = parsed.user_id;
  } catch (_) {
    // fall through — will forward raw and let Rox reject
  }

  const mappedJson = userId ? await env.ROX_ROUTING.get(userId) : null;
  const mapped = mappedJson ? JSON.parse(mappedJson) : null;
  const target = mapped?.webhook_url || DEFAULT_WEBHOOK;

  if (userId && !mapped) {
    const ts = new Date().toISOString();
    await env.ROX_EVENTS.put(
      `unknown:${ts}:${userId}`,
      JSON.stringify({ timestamp: ts, user_id: userId }),
      { expirationTtl: 7 * 24 * 60 * 60 }
    );
  }

  let bodyToForward = rawBody;
  if (mapped?.booking_url && parsed && typeof parsed === "object") {
    parsed.booking_url = mapped.booking_url;
    bodyToForward = JSON.stringify(parsed);
  }

  const rox = await fetch(target, {
    method: "POST",
    headers: { "Content-Type": "application/json", "User-Agent": BROWSER_UA },
    body: bodyToForward,
  });

  return new Response(await rox.text(), {
    status: rox.status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
}

// -------------------- fresh catch pursue --------------------

const PURSUIT_ID_RE = /^fc-\d{8}-[a-z0-9]{2}-[a-z0-9]{6}$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

async function pursueRateLimit(request, env) {
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const bucket = Math.floor(Date.now() / 60000);
  const key = `pursue-rl:${ip}:${bucket}`;
  const current = parseInt((await env.ROX_EVENTS.get(key)) || "0", 10);
  if (current >= 10) return true;
  await env.ROX_EVENTS.put(key, String(current + 1), { expirationTtl: 120 });
  return false;
}

async function handleFreshCatchPursue(request, env) {
  if (request.method === "OPTIONS")
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  if (request.method !== "POST")
    return new Response("Method not allowed", { status: 405, headers: CORS_HEADERS });

  if (await pursueRateLimit(request, env))
    return new Response("Rate limit exceeded", { status: 429, headers: CORS_HEADERS });

  let payload;
  try {
    payload = await request.json();
  } catch {
    return new Response("Invalid JSON", { status: 400, headers: CORS_HEADERS });
  }

  const { pursuit_id, rep_email, contact_email, test } = payload;
  if (!pursuit_id || !PURSUIT_ID_RE.test(pursuit_id))
    return new Response("Invalid pursuit_id", { status: 400, headers: CORS_HEADERS });
  if (!rep_email || !EMAIL_RE.test(rep_email))
    return new Response("Invalid rep_email", { status: 400, headers: CORS_HEADERS });

  const enriched = {
    pursuit_id,
    rep_email: rep_email.toLowerCase(),
    clicked_at: new Date().toISOString(),
  };
  if (contact_email) enriched.contact_email = contact_email;
  if (test) enriched.test = test;

  const target = env.ROX_PURSUE_WEBHOOK_URL;
  if (!target)
    return new Response("ROX_PURSUE_WEBHOOK_URL not configured", {
      status: 500,
      headers: CORS_HEADERS,
    });

  const headers = { "Content-Type": "application/json", "User-Agent": BROWSER_UA };
  if (env.ROX_PURSUE_WEBHOOK_SIGNING_KEY) {
    headers["Authorization"] = `Bearer ${env.ROX_PURSUE_WEBHOOK_SIGNING_KEY}`;
  }

  const rox = await fetch(target, {
    method: "POST",
    headers,
    body: JSON.stringify(enriched),
  });

  return new Response(
    JSON.stringify({ forwarded: true, rox_status: rox.status }),
    {
      status: 200,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    }
  );
}

// -------------------- public: pursue-webhooks.json --------------------

async function handlePursueWebhooksJson(request, env) {
  if (request.method === "OPTIONS")
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  if (request.method !== "GET")
    return new Response("Method not allowed", { status: 405, headers: CORS_HEADERS });

  const reps = await listReps(env);
  const map = {};
  for (const r of reps) {
    if (!r.email || !r.pursue_webhook_url) continue;
    const email = String(r.email).toLowerCase().trim();
    const url = String(r.pursue_webhook_url).trim();
    if (!EMAIL_RE.test(email)) continue;
    if (!url.startsWith("http://") && !url.startsWith("https://")) continue;
    map[email] = url;
  }

  return new Response(JSON.stringify(map), {
    status: 200,
    headers: {
      ...CORS_HEADERS,
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
  });
}

// -------------------- admin: data access --------------------

async function listReps(env) {
  const list = await env.ROX_ROUTING.list();
  const reps = [];
  for (const key of list.keys) {
    const raw = await env.ROX_ROUTING.get(key.name);
    if (!raw) continue;
    try {
      reps.push(JSON.parse(raw));
    } catch (_) {
      /* skip malformed */
    }
  }
  return reps.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
}

async function listEvents(env) {
  const list = await env.ROX_EVENTS.list({ prefix: "unknown:" });
  const events = [];
  for (const key of list.keys.slice(-20).reverse()) {
    const raw = await env.ROX_EVENTS.get(key.name);
    if (!raw) continue;
    try {
      events.push(JSON.parse(raw));
    } catch (_) {
      /* skip */
    }
  }
  return events;
}

// -------------------- admin: HTML page --------------------

async function renderAdmin(env) {
  const reps = await listReps(env);
  const events = await listEvents(env);

  // Serialize rep data for the client-side edit function. JSON.stringify inside
  // a JS string requires escaping < and quotes to survive HTML embedding.
  const repsJson = JSON.stringify(reps)
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/&/g, "\\u0026");

  const rows = reps.length
    ? reps
        .map(
          (r) => `
      <tr>
        <td>${escapeHtml(r.name || "")}</td>
        <td><code>${escapeHtml(r.email || "")}</code></td>
        <td><code>${escapeHtml(r.user_id)}</code></td>
        <td><code class="wrap">${escapeHtml(r.webhook_url || "")}</code></td>
        <td><code class="wrap">${escapeHtml(r.booking_url || "")}</code></td>
        <td><code class="wrap">${escapeHtml(r.pursue_webhook_url || "")}</code></td>
        <td>
          <button class="edit" onclick="editRep('${escapeHtml(r.user_id)}')">Edit</button>
          <button class="danger" onclick="removeRep('${escapeHtml(
            r.user_id
          )}', '${escapeHtml(r.name || "")}')">Remove</button>
        </td>
      </tr>`
        )
        .join("")
    : `<tr><td colspan="7" class="muted">No reps yet — add one below.</td></tr>`;

  const eventRows = events.length
    ? events
        .map(
          (e) =>
            `<li><code>${escapeHtml(e.timestamp)}</code> — unknown <code>${escapeHtml(
              e.user_id
            )}</code></li>`
        )
        .join("")
    : `<li class="muted">No fail-open events in the last 7 days.</li>`;

  const html = `<!doctype html>
<html><head>
  <meta charset="utf-8">
  <title>Rox Rep Routing — Deep Dive + Fresh Catch Pursue</title>
  <style>
    :root { color-scheme: light dark; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 1200px; margin: 32px auto; padding: 20px; }
    h1 { margin-top: 0; }
    h2 { margin-top: 32px; font-size: 16px; text-transform: uppercase; letter-spacing: 0.05em; color: #666; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 10px 8px; border-bottom: 1px solid #e5e7eb; text-align: left; vertical-align: top; }
    th { background: #f9fafb; font-weight: 600; }
    code { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12px; color: #555; }
    code.wrap { word-break: break-all; }
    form { background: #f6f7f9; padding: 20px; border-radius: 10px; margin-top: 12px; display: grid; gap: 12px; grid-template-columns: 1fr 1fr; }
    form label { display: flex; flex-direction: column; font-size: 12px; color: #666; }
    form label.wide { grid-column: 1 / -1; }
    form input { margin-top: 4px; padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
    form input[readonly] { background: #eee; color: #666; }
    form .form-actions { grid-column: 1 / -1; display: flex; gap: 8px; }
    form button { flex: 1; padding: 10px; background: #2563eb; color: white; border: 0; border-radius: 6px; cursor: pointer; font-size: 14px; }
    form button:hover { background: #1d4ed8; }
    form button.secondary { background: #6b7280; }
    form button.secondary:hover { background: #4b5563; }
    button.edit { background: #dbeafe; color: #1e40af; border: 0; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; margin-right: 4px; }
    button.edit:hover { background: #bfdbfe; }
    button.danger { background: #fee2e2; color: #b91c1c; border: 0; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }
    button.danger:hover { background: #fecaca; }
    .events { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; font-size: 13px; }
    .events ul { margin: 0; padding-left: 20px; }
    .muted { color: #999; }
    .hint { font-size: 12px; color: #888; margin-top: 4px; }
    .form-title { grid-column: 1 / -1; font-size: 14px; font-weight: 600; color: #333; margin: 0 0 4px 0; }
    .form-title .badge { display: inline-block; margin-left: 8px; padding: 2px 8px; background: #dbeafe; color: #1e40af; border-radius: 4px; font-size: 11px; font-weight: 600; }
    @media (prefers-color-scheme: dark) {
      body { background: #111; color: #eee; }
      th { background: #1c1c1e; }
      td, th { border-color: #2c2c2e; }
      code { color: #aaa; }
      form { background: #1c1c1e; }
      form input { background: #111; color: #eee; border-color: #333; }
      form input[readonly] { background: #222; color: #888; }
      .events { background: #3a2a10; color: #f5d97a; border-color: #a86b00; }
      .form-title { color: #eee; }
    }
  </style>
</head><body>
  <h1>Rox Rep Routing</h1>
  <p class="muted">Each rep has their own Rox webhooks. <strong>Deep Dive Feedback</strong> is routed by <code>user_id</code> (falls back to Mel Boulos if not mapped). <strong>Fresh Catch Pursue</strong> is routed by <code>email</code> (silently omitted from the email if not mapped). If a rep has a <code>booking_url</code>, it's injected into Deep Dive payloads so the Rox agent can insert a one-click booking link in drafts.</p>

  <h2>Current reps (${reps.length})</h2>
  <table>
    <thead><tr><th>Name</th><th>Email</th><th>User ID</th><th>Deep Dive Webhook</th><th>Booking URL</th><th>Pursue Webhook</th><th></th></tr></thead>
    <tbody>${rows}</tbody>
  </table>

  <h2 id="form-heading">Add rep</h2>
  <form id="rep-form" onsubmit="saveRep(event)">
    <div class="form-title" id="form-title">Add a new rep <span class="badge" id="edit-badge" style="display:none;">EDITING</span></div>
    <label>Name<input name="name" required placeholder="Jane Doe"></label>
    <label>Email<input name="email" required type="email" placeholder="jane.doe@couchbase.com"></label>
    <label class="wide">rox_user_id<input name="user_id" required placeholder="e58b527c-…"></label>
    <label class="wide">Deep Dive Webhook URL<input name="webhook_url" required placeholder="https://webhooks.backend.rox.com/webhooks/w/workflow-webhook-…"></label>
    <label class="wide">Booking URL (optional)<input name="booking_url" placeholder="https://calendly.com/jane-doe/30min">
      <span class="hint">If set, injected into Deep Dive payloads as <code>booking_url</code>.</span>
    </label>
    <label class="wide">Fresh Catch Pursue Webhook URL (optional)<input name="pursue_webhook_url" placeholder="https://webhooks.backend.rox.com/webhooks/w/workflow-webhook-…">
      <span class="hint">If set, Fresh Catch renders a 🎯 Pursue pill on each contact row that fires this rep's own Pursue instance. Leave blank to silently omit the pill.</span>
    </label>
    <div class="form-actions">
      <button type="submit" id="submit-btn">Save rep</button>
      <button type="button" class="secondary" id="cancel-btn" style="display:none;" onclick="cancelEdit()">Cancel edit</button>
    </div>
  </form>

  <h2>Recent fail-open events (last 7 days)</h2>
  <div class="events"><ul>${eventRows}</ul></div>

  <script>
    const REPS = ${repsJson};

    function editRep(userId) {
      const rep = REPS.find(r => r.user_id === userId);
      if (!rep) return alert("Rep not found");
      const form = document.getElementById("rep-form");
      form.name.value = rep.name || "";
      form.email.value = rep.email || "";
      form.user_id.value = rep.user_id || "";
      form.user_id.readOnly = true;
      form.webhook_url.value = rep.webhook_url || "";
      form.booking_url.value = rep.booking_url || "";
      form.pursue_webhook_url.value = rep.pursue_webhook_url || "";
      document.getElementById("form-heading").textContent = "Edit rep";
      document.getElementById("form-title").firstChild.textContent = "Editing " + (rep.name || rep.user_id) + " ";
      document.getElementById("edit-badge").style.display = "inline-block";
      document.getElementById("submit-btn").textContent = "Update rep";
      document.getElementById("cancel-btn").style.display = "block";
      window.scrollTo({ top: document.getElementById("form-heading").offsetTop - 20, behavior: "smooth" });
    }

    function cancelEdit() {
      const form = document.getElementById("rep-form");
      form.reset();
      form.user_id.readOnly = false;
      document.getElementById("form-heading").textContent = "Add rep";
      document.getElementById("form-title").firstChild.textContent = "Add a new rep ";
      document.getElementById("edit-badge").style.display = "none";
      document.getElementById("submit-btn").textContent = "Save rep";
      document.getElementById("cancel-btn").style.display = "none";
    }

    async function saveRep(e) {
      e.preventDefault();
      const form = e.target;
      const body = {
        name: form.name.value.trim(),
        email: form.email.value.trim(),
        user_id: form.user_id.value.trim(),
        webhook_url: form.webhook_url.value.trim(),
        booking_url: form.booking_url.value.trim() || null,
        pursue_webhook_url: form.pursue_webhook_url.value.trim() || null,
      };
      const r = await fetch("/admin/save", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (r.ok) location.reload();
      else alert("Save failed: " + (await r.text()));
    }

    async function removeRep(userId, name) {
      if (!confirm("Remove " + (name || userId) + " from routing?")) return;
      const r = await fetch("/admin/save", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_id: userId, _delete: true }) });
      if (r.ok) location.reload();
      else alert("Remove failed: " + (await r.text()));
    }
  </script>
</body></html>`;

  return new Response(html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

// -------------------- admin: upsert / delete --------------------

async function saveRep(request, env) {
  let payload;
  try {
    payload = await request.json();
  } catch (_) {
    return new Response("invalid JSON", { status: 400 });
  }
  const { name, email, user_id, webhook_url, booking_url, pursue_webhook_url, _delete } = payload;
  if (!user_id) return new Response("user_id required", { status: 400 });

  if (_delete) {
    await env.ROX_ROUTING.delete(user_id);
    return new Response("removed");
  }

  if (!webhook_url) return new Response("webhook_url required", { status: 400 });
  const row = { name: name || "", user_id, webhook_url };
  if (email) row.email = String(email).toLowerCase().trim();
  if (booking_url) row.booking_url = booking_url;
  if (pursue_webhook_url) row.pursue_webhook_url = pursue_webhook_url;
  await env.ROX_ROUTING.put(user_id, JSON.stringify(row));
  return new Response("saved");
}

// -------------------- router --------------------

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/admin") {
      const authFail = requireBasicAuth(request, env);
      if (authFail) return authFail;
      return renderAdmin(env);
    }

    if (url.pathname === "/admin/save") {
      const authFail = requireBasicAuth(request, env);
      if (authFail) return authFail;
      return saveRep(request, env);
    }

    if (url.pathname === "/fresh-catch-pursue") {
      return handleFreshCatchPursue(request, env);
    }

    if (url.pathname === "/pursue-webhooks.json") {
      return handlePursueWebhooksJson(request, env);
    }

    return handleProxy(request, env);
  },
};
