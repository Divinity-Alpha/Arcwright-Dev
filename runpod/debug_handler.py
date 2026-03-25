"""
Arcwright — RunPod Debug Handler
=================================
Minimal handler that logs every step of startup to diagnose crash-looping.
No model loading, no vLLM — just environment probing and a keep-alive handler.
"""

import runpod
import sys
import os

print("=== ARCWRIGHT DEBUG START ===", flush=True)
print(f"Python: {sys.version}", flush=True)
print(f"Working dir: {os.getcwd()}", flush=True)
print(f"Files in /: {os.listdir('/')}", flush=True)

# Check disk space
import shutil
total, used, free = shutil.disk_usage("/")
print(f"Disk: total={total//1e9:.1f}GB used={used//1e9:.1f}GB free={free//1e9:.1f}GB", flush=True)

# Check GPU
try:
    import torch
    print(f"CUDA available: {torch.cuda.is_available()}", flush=True)
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}", flush=True)
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem/1e9:.1f} GB", flush=True)
except Exception as e:
    print(f"GPU check failed: {e}", flush=True)

# Check if model files exist
for path in ["/models", "/models/blueprint-lora-v14", "/models/bt-lora-v3", "/models/dt-lora-v5", "/models/widget-lora-v4"]:
    exists = os.path.exists(path)
    print(f"Path {path}: exists={exists}", flush=True)
    if exists and os.path.isdir(path):
        try:
            print(f"  Contents: {os.listdir(path)}", flush=True)
        except Exception as e:
            print(f"  listdir failed: {e}", flush=True)

# Check HF token
hf_token = os.environ.get("HUGGING_FACE_HUB_TOKEN", "NOT SET")
print(f"HF Token: {'SET (' + hf_token[:8] + '...)' if hf_token != 'NOT SET' else 'NOT SET'}", flush=True)

# Check all environment variables that matter
for key in ["BASE_MODEL", "MODEL_DIR", "PROMPT_DIR", "TENSOR_PARALLEL", "QUANTIZATION", "HF_HOME", "HF_TOKEN", "CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES"]:
    val = os.environ.get(key, "NOT SET")
    print(f"ENV {key}: {val}", flush=True)

# Try importing vllm
try:
    import vllm
    print(f"vLLM version: {vllm.__version__}", flush=True)
except Exception as e:
    print(f"vLLM import failed: {e}", flush=True)

# Try importing other critical packages
for pkg_name in ["bitsandbytes", "transformers", "accelerate", "huggingface_hub", "sentencepiece"]:
    try:
        pkg = __import__(pkg_name)
        ver = getattr(pkg, "__version__", "unknown")
        print(f"{pkg_name}: {ver}", flush=True)
    except Exception as e:
        print(f"{pkg_name} import failed: {e}", flush=True)

# Check system prompts
prompt_dir = os.environ.get("PROMPT_DIR", "/app/system_prompts")
print(f"System prompts dir ({prompt_dir}): exists={os.path.exists(prompt_dir)}", flush=True)
if os.path.exists(prompt_dir):
    try:
        print(f"  Contents: {os.listdir(prompt_dir)}", flush=True)
    except Exception as e:
        print(f"  listdir failed: {e}", flush=True)

# Check /app contents
print(f"Files in /app: {os.listdir('/app') if os.path.exists('/app') else 'NOT FOUND'}", flush=True)

print("=== DEBUG: Starting simple handler ===", flush=True)


def handler(event):
    return {"status": "debug", "message": "Container is alive", "input": event.get("input", {})}


runpod.serverless.start({"handler": handler})
