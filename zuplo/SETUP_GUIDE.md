# Arcwright — Zuplo Setup Guide

## What Zuplo Handles For You

After this setup, Zuplo manages: API key auth, rate limiting, tier enforcement, request validation, developer portal, API docs, Stripe billing, and CORS. You never build or maintain any of these.

---

## Step 1: Create Zuplo Account

1. Go to https://portal.zuplo.com
2. Sign up with GitHub (recommended — enables GitOps workflow)
3. Create a new project: "arcwright-api"
4. Choose "Blank Project" template

---

## Step 2: Import the OpenAPI Routes

1. In the Zuplo Portal, go to **Code** tab
2. Click **routes.oas.json**
3. Click **Import OpenAPI** (top right)
4. Paste or upload the contents of `routes.oas.json` from this directory
5. The Route Designer should show 8 routes:
   - POST /v1/generate
   - POST /v1/generate/batch
   - POST /v1/validate
   - GET /v1/templates
   - GET /v1/templates/{category}/{templateId}
   - POST /v1/widget/from-html
   - GET /v1/health
   - POST /v1/feedback

---

## Step 3: Import Policies

1. Go to **Code** tab → **policies.json**
2. Replace the contents with `policies.json` from this directory
3. This defines 7 policies:
   - `api-key-auth` — API key validation
   - `rate-limit-generate` — Per-tier rate limiting for generation
   - `rate-limit-validate` — Rate limiting for validation endpoint
   - `rate-limit-batch` — Rate limiting for batch endpoint
   - `request-validation` — Schema validation against OpenAPI
   - `tier-check-pro` — Blocks non-Pro users
   - `tier-check-studio` — Blocks non-Studio users

---

## Step 4: Add Custom Modules

1. In the **Code** tab, create folder `modules/`
2. Create file `modules/tier-check.ts` — paste from `tier-check.ts`

---

## Step 5: Set Environment Variables

1. Go to **Settings** → **Environment Variables**
2. Add:

| Variable | Value | Type |
|---|---|---|
| `BACKEND_URL` | `https://api.runpod.ai/v2/<endpoint-id>/runsync` | Text |
| `RUNPOD_API_KEY` | Your RunPod API key | **Secret** |
| `STRIPE_SECRET_KEY` | sk_live_xxx... | **Secret** |
| `STRIPE_PUBLISHABLE_KEY` | pk_live_xxx... | Text |
| `STRIPE_WEBHOOK_SECRET` | whsec_xxx... | **Secret** |
| `STRIPE_PRICING_TABLE_ID` | prctbl_xxx... | Text |

Get `BACKEND_URL` and `RUNPOD_API_KEY` from the RunPod dashboard after deploying the serverless endpoint (see `runpod/DEPLOYMENT_GUIDE.md`). Leave Stripe fields empty until Step 7.

---

## Step 6: Configure Rate Limits

Rate limits enforce tier boundaries. Configure in `policies.json`:

| Tier | Monthly Generations | Per-Minute Burst | Notes |
|---|---|---|---|
| **No API key** | 0 | 0 | `/v1/generate` rejected. `/v1/health` allowed. |
| **Maker** | 500/month | 5/min | Free tier with account |
| **Pro** | 2,000/month | 10/min | All 3 domains (BP+BT+DT) |
| **Studio** | 10,000/month | 20/min | Batch API, priority queue |

The `rate-limit-generate` policy reads the consumer's `tier` metadata and applies the corresponding limits. Monthly counters reset on the 1st of each month.

**Implementation:** The `tier-check.ts` module reads `request.user.data.tier` (set by the API Key Service consumer metadata). The rate limit policy uses `request.user.data.tier` to select the matching limit window.

---

## Step 7: Configure Developer Portal

1. Go to **Code** tab → **dev-portal.json**
2. Enable:
   - Auto-generated API documentation from the OpenAPI spec
   - Self-service API key management (users sign up, get key)
   - Stripe pricing table integration (upgrade path)
   - Arcwright branding and theme

The portal will be accessible at `api.arcwright.app/docs` after custom domain setup.

---

## Step 8: Set Up Stripe

1. Create Stripe account at https://dashboard.stripe.com
2. Start in **Test Mode** (toggle at top of dashboard)
3. Create 3 Products:

**Product 1: Maker (Free)**
- Name: "Arcwright Maker"
- Price: $0/month (free plan)
- Metadata: `tier: maker`

**Product 2: Pro**
- Name: "Arcwright Pro"
- Price: Monthly recurring
- Metadata: `tier: pro`

**Product 3: Studio**
- Name: "Arcwright Studio"
- Price: Monthly recurring
- Metadata: `tier: studio`

4. Create a **Pricing Table** in Stripe:
   - Dashboard → Product Catalog → Pricing Tables → Create
   - Add all 3 products
   - Customize the look
   - Copy the `pricing-table-id` and `publishable-key`

5. Set up Stripe **API Keys**:
   - Dashboard → Developers → API Keys
   - Copy Secret Key → set as `STRIPE_SECRET_KEY` in Zuplo
   - Copy Publishable Key → set as `STRIPE_PUBLISHABLE_KEY`

6. Set up **Webhooks**:
   - Dashboard → Developers → Webhooks → Add endpoint
   - URL: `https://api.arcwright.app/webhooks/stripe`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`
   - Copy webhook signing secret → set as `STRIPE_WEBHOOK_SECRET` in Zuplo

---

## Step 9: Create API Key Consumers

When a user signs up through the Developer Portal:
1. They're created as a "Consumer" in Zuplo
2. Default tier is `maker` (set in metadata):
   ```json
   {
     "tier": "maker"
   }
   ```
3. When they subscribe via Stripe, the webhook updates their tier to `pro` or `studio`

For testing, manually create a consumer:
1. Go to **Services** → **API Key Service** → **Configure**
2. Click **Create Consumer**
3. Set name, email, and metadata: `{"tier": "pro"}`
4. An API key is generated — copy it for testing

---

## Step 10: Deploy and Test

1. Click **Save** in Zuplo Portal (deploys automatically)
2. Your API is live at: `https://your-project.zuplo.dev`
3. Test the health endpoint (no auth needed):
   ```bash
   curl https://your-project.zuplo.dev/v1/health
   ```
4. Test generation with API key:
   ```bash
   curl -X POST https://your-project.zuplo.dev/v1/generate \
     -H "Authorization: Bearer zpka_xxxxx" \
     -H "Content-Type: application/json" \
     -d '{"domain":"blueprint","prompt":"Create a health pickup that heals 25 HP on overlap"}'
   ```
5. Expected response:
   ```json
   {
     "output": {
       "dsl": "BLUEPRINT: BP_HealthPickup\nPARENT: Actor\n...",
       "domain": "blueprint",
       "tokens_generated": 142,
       "generation_time_ms": 4200,
       "model": "arcwright-blueprint-v14"
     }
   }
   ```
6. Test feedback:
   ```bash
   curl -X POST https://your-project.zuplo.dev/v1/feedback \
     -H "Authorization: Bearer zpka_xxxxx" \
     -H "Content-Type: application/json" \
     -d '{"generation_id":"job-123","rating":"good"}'
   ```

---

## Step 11: Custom Domain

1. Go to **Settings** → **Custom Domain**
2. Add: `api.arcwright.app`
3. Zuplo provides DNS records to add at your registrar
4. Add the CNAME/A records at Cloudflare or your domain provider
5. SSL is automatic

After DNS propagation:
```bash
curl https://api.arcwright.app/v1/health
```

Developer portal: `https://api.arcwright.app/docs`

---

## Request Flow

```
Client → api.arcwright.app (Zuplo)
  → API key auth (reject if missing/invalid)
  → Tier check (reject if insufficient tier)
  → Rate limit (reject if over limit, return X-RateLimit headers)
  → Request validation (reject if schema mismatch)
  → Forward to RunPod: https://api.runpod.ai/v2/<endpoint>/runsync
    → RunPod adds Authorization: Bearer <RUNPOD_API_KEY>
    → RunPod routes to serverless worker
    → Worker loads appropriate LoRA adapter
    → Generates DSL
    → Returns response
  → Zuplo returns response to client
```

---

## Ongoing Management

| Task | Where | How Often |
|---|---|---|
| View usage analytics | Zuplo Portal → Analytics | Weekly |
| Manage consumers | Zuplo Portal → Services | As needed |
| View revenue | Stripe Dashboard | Weekly |
| Update rate limits | policies.json → commit | As needed |
| Add new routes | routes.oas.json → commit | As features ship |
| Check errors | Zuplo Portal → Logs | If alerts fire |
| Update RunPod endpoint | Settings → BACKEND_URL | When endpoint changes |

All config changes deploy automatically when you commit to GitHub (GitOps). No manual deploys needed.

---

*Setup guide v2.0 — updated 2026-03-16 for v14/v3/v5 adapters and RunPod backend.*
