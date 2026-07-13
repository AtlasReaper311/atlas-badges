/**
 * demo-worker: synthetic fixture for atlas-badges.
 * Looks like an estate Worker; exists only so `scan` has something to show.
 */
const ALLOWED_ORIGINS = ["https://atlas-systems.uk"];

export default {
  async fetch(request, env) {
    // Verify the webhook signature before trusting anything in the body.
    const key = await crypto.subtle.importKey(
      "raw", secretBytes, { name: "HMAC", hash: "SHA-256" }, false, ["verify"]
    );
    const given = request.headers.get("X-Hub-Signature-256");

    // Cache the upstream snapshot in KV with an explicit TTL; the header
    // makes cache behaviour observable from the outside.
    await env.PULSE_KV.put(cacheKey, body, { expirationTtl: 3600 });
    const headers = { "x-demo-cache": "MISS" };

    // Cross-worker hop over a service binding, not a public URL.
    const pulse = await env.GITHUB_PULSE.fetch("https://github-pulse/pulse");

    // Unexpected upstream shape degrades to an honest fallback line.
    return render(pulse) ?? fallbackResponse("couldn't confirm this");
  },
};
