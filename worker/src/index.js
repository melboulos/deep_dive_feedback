export default {
  async fetch(request) {
    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405, headers: cors });
    }

    // Wrap the browser payload under `payload` so Rox delivers the fields
    // at trigger_data.payload.<field> — matching how synthetic test runs
    // are shaped when they successfully triggered the agent.
    const incoming = await request.json().catch(() => ({}));
    const wrapped = { payload: incoming };

    const rox = await fetch(
      "https://webhooks.backend.rox.com/webhooks/w/workflow-webhook-318d6a1b",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(wrapped),
      }
    );

    return new Response(await rox.text(), {
      status: rox.status,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  },
};
