// Arcwright Feedback Relay — Cloudflare Worker
// Receives feedback from Arcwright plugin → creates GitHub Issue
// Plugin sends pre-built GitHub Issues API payload {title, body, labels}
// Worker adds auth and forwards to GitHub.

const GITHUB_OWNER  = 'Divinity-Alpha';
const GITHUB_REPO   = 'Arcwright-Feedback';  // private repo

export default {
  async fetch(request, env) {

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        }
      });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    // Parse payload
    let payload;
    try {
      payload = await request.json();
    } catch {
      return new Response('Invalid JSON', { status: 400 });
    }

    // Plugin sends {title, body, labels} — validate
    const { title, body } = payload;

    if (!title || title.trim().length < 5) {
      return new Response('Title too short', { status: 400 });
    }
    if (!body || body.trim().length < 10) {
      return new Response('Body too short', { status: 400 });
    }

    // Rate limit by IP — max 3 submissions per hour per IP
    const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    const rl_key = `rl:${ip}`;
    const rl_count = parseInt(
      await env.ARCWRIGHT_RL.get(rl_key) || '0'
    );
    if (rl_count >= 3) {
      return new Response('Rate limited', { status: 429 });
    }
    await env.ARCWRIGHT_RL.put(rl_key,
      String(rl_count + 1), { expirationTtl: 3600 });

    // Forward to GitHub Issues API with auth
    const ghResponse = await fetch(
      `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues`,
      {
        method: 'POST',
        headers: {
          'Authorization': `token ${env.GITHUB_TOKEN_SECRET}`,
          'Content-Type': 'application/json',
          'User-Agent': 'Arcwright-Feedback-Relay/1.0',
          'Accept': 'application/vnd.github.v3+json',
        },
        body: JSON.stringify({
          title: title.trim(),
          body: body.trim(),
          labels: payload.labels || [],
        }),
      }
    );

    if (!ghResponse.ok) {
      const err = await ghResponse.text();
      console.error('GitHub API error:', err);
      return new Response(
        JSON.stringify({
          status: 'ok',
          queued: true,
          debug: err.slice(0, 200)
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    const issue = await ghResponse.json();

    return new Response(
      JSON.stringify({
        status: 'ok',
        issue: issue.number
      }),
      {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        }
      }
    );
  }
};
