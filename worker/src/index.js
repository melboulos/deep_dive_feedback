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

    const rox = await fetch(
      "https://webhooks.backend.rox.com/webhooks/w/workflow-webhook-318d6a1b",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        },
        body: await request.text(),
      }
    );

    return new Response(await rox.text(), {
      status: rox.status,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  },
};
