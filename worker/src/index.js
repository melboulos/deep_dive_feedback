// worker/src/index.js
// Deep Dive Feedback proxy with live-editable rep routing.
//
// Routes:
//   POST /            → forward to per-rep Rox webhook based on payload.user_id
//   OPTIONS /         → CORS preflight for the boomerang page
//   GET  /admin       → HTML admin page (basic auth)
//   POST /admin/save  → upsert or remove a rep in KV (basic auth)
//
// Bindings:
//   ROX_ROUTING   — KV namespace: user_id → { name, user_id, webhook_url }
//   ROX_EVENTS    — KV namespace: recent unknown-user_id events (7d TTL)
//   ADMIN_PASSWORD — secret; used by basic auth on /admin

const DEFAULT_WEBHOOK =
  "https://webhooks.backend.rox.com/webhooks/w/workflow-webhook-318d6a1b";
const BROWSER_UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36";

// -------------------- shared helpers --------------------

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
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

// -------------------- feedback proxy --------------------

async function handleProxy(request, env) {
  if (request.method === "OPTIONS")
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  if (request.method !== "POST")
    return new Response("Method not allowed", { status: 405, headers: CORS_HEADERS });

  const body = await request.text();
  let userId = null;
  try {
    userId = JSON.parse(body).user_id;
  } catch (_) {
    /* leave userId null; will fall back to default */
  }

  const mappedJson = userId ? await env.ROX_ROUTING.get(userId) : null;
  const mapped = mappedJson ? JSON.parse(mappedJson) : null;
  const target = mapped?.webhook_url || DEFAULT_WEBHOOK;

  // Record a fail-open event when a user_id was supplied but not mapped.
  if (userId && !mapped) {
    const ts = new Date().toISOString();
    await env.ROX_EVENTS.put(
      `unknown:${ts}:${userId}`,
      JSON.stringify({ timestamp: ts, user_id: userId }),
      { expirationTtl: 7 * 24 * 60 * 60 } // 7 days
    );
  }

  const rox = await fetch(target, {
    method: "POST",
    headers: { "Content-Type": "application/json", "User-Agent": BROWSER_UA },
    body,
  });

  return new Response(await rox.text(), {
    status: rox.status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
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
  // Take the newest 20 (keys are timestamp-ordered ascending; reverse then slice).
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

  const rows = reps.length
    ? reps
        .map(
          (r) => `
      <tr>
        <td>${escapeHtml(r.name || "")}</td>
        <td><code>${escapeHtml(r.user_id)}</code></td>
        <td><code class="wrap">${escapeHtml(r.webhook_url || "")}</code></td>
        <td><button class="danger" onclick="removeRep('${escapeHtml(
          r.user_id
        )}', '${escapeHtml(r.name || "")}')">Remove</button></td>
      </tr>`
        )
        .join("")
    : `<tr><td colspan="4" class="muted">No reps yet — add one below.</td></tr>`;

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
  <title>Deep Dive Feedback — Rep Routing</title>
  <style>
    :root { color-scheme: light dark; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 960px; margin: 32px auto; padding: 20px; }
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
    form button { grid-column: 1 / -1; padding: 10px; background: #2563eb; color: white; border: 0; border-radius: 6px; cursor: pointer; font-size: 14px; }
    form button:hover { background: #1d4ed8; }
    button.danger { background: #fee2e2; color: #b91c1c; border: 0; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }
    button.danger:hover { background: #fecaca; }
    .events { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; font-size: 13px; }
    .events ul { margin: 0; padding-left: 20px; }
    .muted { color: #999; }
    @media (prefers-color-scheme: dark) {
      body { background: #111; color: #eee; }
      th { background: #1c1c1e; }
      td, th { border-color: #2c2c2e; }
      code { color: #aaa; }
      form { background: #1c1c1e; }
      form input { background: #111; color: #eee; border-color: #333; }
      .events { background: #3a2a10; color: #f5d97a; border-color: #a86b00; }
    }
  </style>
</head><body>
  <h1>Deep Dive Feedback — Rep Routing</h1>
  <p class="muted">Each rep listed here has their own Rox webhook URL. Deep Dive clicks are routed by <code>user_id</code>. Reps not listed here fall through to the default webhook (Mel Boulos).</p>

  <h2>Current reps (${reps.length})</h2>
  <table>
    <thead><tr><th>Name</th><th>User ID</th><th>Webhook URL</th><th></th></tr></thead>
    <tbody>${rows}</tbody>
  </table>

  <h2>Add / update rep</h2>
  <form onsubmit="saveRep(event)">
    <label>Name<input name="name" required placeholder="Jane Doe"></label>
    <label>rox_user_id<input name="user_id" required placeholder="e58b527c-…"></label>
    <label class="wide">Webhook URL<input name="webhook_url" required placeholder="https://webhooks.backend.rox.com/webhooks/w/workflow-webhook-…"></label>
    <button type="submit">Save rep</button>
  </form>

  <h2>Recent fail-open events (last 7 days)</h2>
  <div class="events"><ul>${eventRows}</ul></div>

  <script>
    async function saveRep(e) {
      e.preventDefault();
      const form = e.target;
      const body = { name: form.name.value.trim(), user_id: form.user_id.value.trim(), webhook_url: form.webhook_url.value.trim() };
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
  const { name, user_id, webhook_url, _delete } = payload;
  if (!user_id) return new Response("user_id required", { status: 400 });

  if (_delete) {
    await env.ROX_ROUTING.delete(user_id);
    return new Response("removed");
  }

  if (!webhook_url) return new Response("webhook_url required", { status: 400 });
  await env.ROX_ROUTING.put(
    user_id,
    JSON.stringify({ name: name || "", user_id, webhook_url })
  );
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

    return handleProxy(request, env);
  },
};
