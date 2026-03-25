# Arcwright — RunPod Deployment Guide

## Prerequisites

1. **RunPod account** — https://runpod.io (sign up, add payment method)
2. **HuggingFace account** — with access to Meta-Llama-3.1-70B (request at https://huggingface.co/meta-llama/Meta-Llama-3.1-70B)
3. **Docker** installed locally
4. **Trained LoRA adapters**: blueprint-lora-v14, bt-lora-v3, dt-lora-v5

---

## Step 1: Prepare the Build Directory

```
C:\Arcwright\runpod\
├── handler.py                        # Serverless worker
├── Dockerfile                        # Container definition
├── requirements.txt                  # Python dependencies
├── test_local.py                     # Local test script
├── system_prompts/                   # Domain system prompts
│   ├── blueprint.txt
│   ├── bt.txt
│   └── dt.txt
└── models/                           # LoRA adapters (for baking into image)
    ├── blueprint-lora-v14/final/
    │   ├── adapter_model.safetensors
    │   └── adapter_config.json
    ├── bt-lora-v3/final/
    │   ├── adapter_model.safetensors
    │   └── adapter_config.json
    └── dt-lora-v5/final/
        ├── adapter_model.safetensors
        └── adapter_config.json
```

Copy your adapters into the build directory:
```powershell
# From project root
xcopy /E /I models\blueprint-lora-v14\final runpod\models\blueprint-lora-v14\final
xcopy /E /I models\bt-lora-v3\final runpod\models\bt-lora-v3\final
xcopy /E /I models\dt-lora-v5\final runpod\models\dt-lora-v5\final
```

---

## Step 2: Test Locally (Mock — No GPU)

```powershell
cd C:\Arcwright\runpod
python test_local.py
```

This validates prompt formatting, output cleaning, input validation, and domain aliases without a GPU. All tests should pass.

---

## Step 3: Build the Docker Image

```powershell
cd C:\Arcwright\runpod
docker build -t arcwright-worker:latest .
```

The image will be ~15-20 GB (PyTorch + vLLM + adapters). The base 70B model is NOT included — it downloads from HuggingFace on first cold start, then RunPod caches it.

---

## Step 4: Push to Docker Registry

**Option A: Docker Hub**
```powershell
docker login
docker tag arcwright-worker:latest divinityalpha/arcwright-worker:latest
docker push divinityalpha/arcwright-worker:latest
```

**Option B: RunPod Container Registry** (recommended — faster pulls)
Follow https://docs.runpod.io/serverless/workers/deploy

---

## Step 5: Create RunPod Serverless Endpoint

1. Go to https://runpod.io/console/serverless
2. Click **New Endpoint**
3. Configure:

| Setting | Value | Notes |
|---|---|---|
| Container Image | `divinityalpha/arcwright-worker:latest` | Or your registry path |
| GPU Type | **A100 80GB SXM** | Minimum for 70B 8-bit. A6000 48GB won't fit. |
| Min Workers | 0 | Scales to zero when idle |
| Max Workers | 3 | Caps cost. Increase based on demand. |
| Idle Timeout | 60 seconds | Keeps worker warm for burst traffic |
| FlashBoot | Enabled | Faster cold starts |
| GPU Count | 1 | Single GPU — no tensor parallelism needed |

4. Add **Environment Variables**:

| Variable | Value | Secret? |
|---|---|---|
| `HF_TOKEN` | Your HuggingFace token | **Yes** |
| `BASE_MODEL` | `meta-llama/Meta-Llama-3.1-70B` | No |
| `TENSOR_PARALLEL` | `1` | No |
| `QUANTIZATION` | `bitsandbytes` | No |

5. Click **Create Endpoint**

---

## Step 6: Test the Deployed Endpoint

Get your endpoint URL and API key from the RunPod dashboard.

**Submit a job:**
```bash
curl -X POST "https://api.runpod.ai/v2/<endpoint-id>/run" \
  -H "Authorization: Bearer <runpod-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"input": {"domain": "blueprint", "prompt": "Create a health pickup that heals 25 HP on overlap"}}'
```

**Check job status:**
```bash
curl "https://api.runpod.ai/v2/<endpoint-id>/status/<job-id>" \
  -H "Authorization: Bearer <runpod-api-key>"
```

**Use /runsync for synchronous requests** (waits for result):
```bash
curl -X POST "https://api.runpod.ai/v2/<endpoint-id>/runsync" \
  -H "Authorization: Bearer <runpod-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"input": {"domain": "blueprint", "prompt": "Create a health pickup that heals 25 HP on overlap"}}'
```

First request will be slow (cold start: model download ~5 min + load ~2 min). Subsequent requests within idle window: 3-8 seconds.

---

## Step 7: Alternative — RunPod Network Storage

Instead of baking adapters into the Docker image (Option A), mount them from network storage (Option B — smaller image, faster deploys):

1. Create a **Network Volume** (10 GB) in RunPod dashboard
2. Start a temporary GPU pod with the volume mounted
3. Upload adapters via SCP or RunPod file manager:
   ```bash
   mkdir -p /runpod-volume/models/blueprint-lora-v14/final
   mkdir -p /runpod-volume/models/bt-lora-v3/final
   mkdir -p /runpod-volume/models/dt-lora-v5/final
   # Upload adapter_model.safetensors + adapter_config.json to each
   ```
4. Update your endpoint to mount this volume
5. Add env vars:
   ```
   LORA_BLUEPRINT=/runpod-volume/models/blueprint-lora-v14/final
   LORA_BT=/runpod-volume/models/bt-lora-v3/final
   LORA_DT=/runpod-volume/models/dt-lora-v5/final
   ```
6. Remove the `COPY models/` lines from Dockerfile, rebuild, and push

---

## Step 8: Note Endpoint URL for Zuplo

After deployment, save:
- **Endpoint URL**: `https://api.runpod.ai/v2/<endpoint-id>/runsync`
- **RunPod API Key**: From Settings → API Keys

These go into the Zuplo configuration as `BACKEND_URL` and `RUNPOD_API_KEY`.

---

## Updating Models

When a new adapter version is trained:

1. Upload new adapter to network storage (or rebuild Docker image)
2. Update env var: `LORA_BLUEPRINT=/runpod-volume/models/blueprint-lora-v15/final`
3. Restart workers (Settings → Restart All Workers)
4. New workers use new adapter on next cold start
5. No downtime — old workers finish current requests first

---

## Monitoring

- **RunPod Dashboard** → Serverless → your endpoint → Logs tab
- Shows: request count, latency distribution, cold starts, errors, GPU utilization
- Set up Discord webhook alerts for errors (RunPod supports this natively)

---

## Cost Estimates

| Scenario | GPU | Cost/hr | Notes |
|---|---|---|---|
| A100 80GB SXM | RunPod Flex | ~$1.64/hr | Pay per second, scales to zero |
| A100 80GB PCIe | RunPod Flex | ~$1.44/hr | Slightly cheaper, same capability |
| 100 requests/day | ~1.5 hrs active | ~$2.50/day | Assumes 60s idle timeout, 5s/request |
| 1000 requests/day | ~5 hrs active | ~$8.20/day | With warm workers |

**Cost optimization tips:**
- Idle timeout 60s: keeps worker warm for bursts, scales to zero when quiet
- FlashBoot: reduces cold start overhead
- Monitor daily: if >8 hrs/day active, Active Workers pricing may be cheaper than Flex

---

*Deployment guide v2.0 — updated 2026-03-16 for v14/v3/v5 adapters.*
