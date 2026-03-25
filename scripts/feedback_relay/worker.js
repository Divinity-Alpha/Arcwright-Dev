// Arcwright Feedback Relay — Cloudflare Worker
// Receives feedback from Arcwright plugin → creates GitHub Issue

const GITHUB_OWNER  = 'Divinity-Alpha';
const GITHUB_REPO   = 'Arcwright-Feedback';  // private repo
const ALLOWED_TYPES = ['Feature Request','Bug Report',
                        'Improvement','New Command'];

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

    // Validate required fields
    const { category, message, plugin_version,
            ue_version, platform, timestamp,
            session_stats } = payload;

    if (!message || message.trim().length < 10) {
      return new Response('Message too short', { status: 400 });
    }
    if (!ALLOWED_TYPES.includes(category)) {
      return new Response('Invalid category', { status: 400 });
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

    // Build GitHub issue
    const label = category.toLowerCase().replace(' ', '-');
    const stats = session_stats || {};

    const issueBody = [
      `## ${category}`,
      ``,
      `### Description`,
      message.trim(),
      ``,
      `### Environment`,
      `| Field | Value |`,
      `|---|---|`,
      `| Plugin Version | ${plugin_version || 'unknown'} |`,
      `| UE Version | ${ue_version || 'unknown'} |`,
      `| Platform | ${platform || 'unknown'} |`,
      `| Submitted | ${timestamp || new Date().toISOString()} |`,
      ``,
      `### Session Stats`,
      `| Field | Value |`,
      `|---|---|`,
      `| Commands this session | ${stats.session_commands || 0} |`,
      `| Total commands | ${stats.total_commands || 0} |`,
      `| Total sessions | ${stats.total_sessions || 0} |`,
      ``,
      `---`,
      `*Submitted anonymously via Arcwright plugin*`,
    ].join('\n');

    // Create GitHub issue
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
          title: `[${category}] ${message.trim().slice(0, 80)}`,
          body: issueBody,
          labels: [label],
        }),
      }
    );

    if (!ghResponse.ok) {
      const err = await ghResponse.text();
      console.error('GitHub API error:', err);
      // Still return 200 to client — don't expose internal errors
      return new Response(
        JSON.stringify({ status: 'ok', queued: true }),
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
