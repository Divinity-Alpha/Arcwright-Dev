# ═══════════════════════════════════════════════════════════════════════════════
# Arcwright — RunPod Serverless Container
# ═══════════════════════════════════════════════════════════════════════════════
#
# Builds a Docker container with:
#   - vLLM for fast 70B inference with LoRA hot-swap
#   - All three domain system prompts
#   - RunPod serverless SDK
#   - Pre-downloaded LoRA adapters (or mount from network storage)
#
# Build:
#   docker build -t arcwright-worker .
#
# Test locally:
#   docker run --gpus all -e HF_TOKEN=hf_xxx arcwright-worker
#
# Deploy to RunPod:
#   docker push <your-registry>/arcwright-worker:latest
# ═══════════════════════════════════════════════════════════════════════════════

FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /app

# ─── System dependencies ───
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# ─── Python dependencies ───
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Copy handler ───
COPY handler.py .

# ─── Copy system prompts (the prompts the model was trained with) ───
COPY system_prompts/ ./system_prompts/

# ─── Copy LoRA adapters ───
# Option A: Bake into container (simple, larger image ~5GB for 3 adapters)
COPY models/blueprint-lora-v14/final /models/blueprint-lora-v14/final
COPY models/bt-lora-v3/final /models/bt-lora-v3/final
COPY models/dt-lora-v5/final /models/dt-lora-v5/final

# Option B: Mount from RunPod network storage (smaller image, shared across workers)
# Remove the 3 COPY lines above and set these env vars in RunPod dashboard:
#   LORA_BLUEPRINT=/runpod-volume/models/blueprint-lora-v14/final
#   LORA_BT=/runpod-volume/models/bt-lora-v3/final
#   LORA_DT=/runpod-volume/models/dt-lora-v5/final

# ─── Environment ───
ENV BASE_MODEL="meta-llama/Meta-Llama-3.1-70B"
ENV MODEL_DIR="/models"
ENV PROMPT_DIR="/app/system_prompts"
ENV TENSOR_PARALLEL="1"
ENV QUANTIZATION="bitsandbytes"
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/hf_cache

# ─── HuggingFace token for gated model access ───
# Set this in RunPod dashboard as a secret, NOT here
# ENV HF_TOKEN="your_token_here"

# ─── Entrypoint ───
CMD ["python", "-u", "handler.py"]
