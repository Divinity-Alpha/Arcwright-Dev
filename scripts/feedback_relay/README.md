# Arcwright Feedback Relay

Cloudflare Worker that receives plugin feedback and creates GitHub Issues.

## Setup (5 minutes)

### 1. Install Wrangler
```
npm install -g wrangler
wrangler login
```

### 2. Create the private feedback repo on GitHub
Go to github.com/Divinity-Alpha → New repository
- Name: Arcwright-Feedback
- Private: YES
- Create these labels: feature-request, bug-report, improvement, new-command

### 3. Create a GitHub Personal Access Token
github.com → Settings → Developer settings → Personal access tokens → Fine-grained tokens
- Repository access: Arcwright-Feedback only
- Permissions: Issues → Read and Write
- Copy the token.

### 4. Create KV namespace
```
wrangler kv:namespace create "ARCWRIGHT_RL"
```
Copy the id into wrangler.toml

### 5. Set GitHub token as secret
```
wrangler secret put GITHUB_TOKEN_SECRET
```
(paste your token when prompted)

### 6. Deploy
```
wrangler deploy
```

### 7. Update plugin endpoint
The worker URL will be:
`https://arcwright-feedback.YOUR-SUBDOMAIN.workers.dev`

Update `GetFeedbackEndpoint()` in ArcwrightDashboardPanel.cpp to return this URL.
Rebuild and repackage.

### 8. Test
Submit feedback from the plugin dashboard.
Check github.com/Divinity-Alpha/Arcwright-Feedback for the new issue.

## Cost
Free — Cloudflare Workers free tier allows 100,000 requests/day. KV free tier is plenty.
