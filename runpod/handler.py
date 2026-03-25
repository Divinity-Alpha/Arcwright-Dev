"""
Arcwright — RunPod Serverless Handler
======================================
Loads the base LLaMA 3.1 70B model in 8-bit on startup,
swaps LoRA adapters per-request for Blueprint, BT, and DT generation.

Deployed as a Docker container on RunPod Serverless.
"""

import os
import re
import json
import time
import logging
import runpod

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("arcwright-worker")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_MODEL = os.getenv("BASE_MODEL", "meta-llama/Meta-Llama-3.1-70B")
MODEL_DIR = os.getenv("MODEL_DIR", "/models")
PROMPT_DIR = os.getenv("PROMPT_DIR", "/app/system_prompts")

# LoRA adapter paths — baked into container or mounted from RunPod network storage
LORA_ADAPTERS = {
    "blueprint": {
        "path": os.getenv("LORA_BLUEPRINT", f"{MODEL_DIR}/blueprint-lora-v14/final"),
        "id": 1,
        "prompt_file": "blueprint.txt",
        "model_label": "arcwright-blueprint-v14",
    },
    "bt": {
        "path": os.getenv("LORA_BT", f"{MODEL_DIR}/bt-lora-v3/final"),
        "id": 2,
        "prompt_file": "bt.txt",
        "model_label": "arcwright-bt-v3",
    },
    "dt": {
        "path": os.getenv("LORA_DT", f"{MODEL_DIR}/dt-lora-v5/final"),
        "id": 3,
        "prompt_file": "dt.txt",
        "model_label": "arcwright-dt-v5",
    },
}

# Domain aliases — accept "datatable" as well as "dt"
DOMAIN_ALIASES = {
    "datatable": "dt",
    "data_table": "dt",
    "behavior_tree": "bt",
    "behaviortree": "bt",
}

# Default generation parameters
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TOP_P = 0.9
DEFAULT_REPETITION_PENALTY = 1.1

# DSL start markers per domain (for stripping preamble)
DSL_MARKERS = {
    "blueprint": "BLUEPRINT:",
    "bt": "BEHAVIORTREE:",
    "dt": "DATATABLE:",
}

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS — loaded from files, with inline fallbacks
# ═══════════════════════════════════════════════════════════════════════════════

_system_prompts: dict[str, str] = {}


def _load_system_prompts():
    """Load system prompts from files on disk. Falls back to inline defaults."""
    for domain, config in LORA_ADAPTERS.items():
        path = os.path.join(PROMPT_DIR, config["prompt_file"])
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                _system_prompts[domain] = f.read().strip()
            logger.info(f"Loaded system prompt: {domain} ({len(_system_prompts[domain])} chars)")
        else:
            logger.warning(f"System prompt file not found: {path} — using inline fallback")

    # Inline fallbacks (short versions — the full prompts should be in the files)
    _system_prompts.setdefault(
        "blueprint",
        "You are a Blueprint programming assistant for Unreal Engine 5. Given a natural language "
        "description of desired game behavior, you generate valid Blueprint DSL code that implements "
        "that behavior. Output ONLY the DSL code — no explanations, no markdown, no code fences.",
    )
    _system_prompts.setdefault(
        "bt",
        "You are an AI that generates Unreal Engine 5 Behavior Tree DSL from natural language "
        "descriptions. Output ONLY valid BT DSL text with no explanation, no markdown, no code fences.",
    )
    _system_prompts.setdefault(
        "dt",
        "You are an AI that generates Unreal Engine 5 Data Table DSL from natural language "
        "descriptions. Output ONLY valid DT DSL text with no explanation, no markdown, no code fences.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL LOADING (runs once on worker startup)
# ═══════════════════════════════════════════════════════════════════════════════

llm = None


def load_model():
    """Load the base 70B model with vLLM + LoRA support. Called once on cold start."""
    global llm

    from vllm import LLM

    logger.info(f"Loading base model: {BASE_MODEL}")
    start = time.time()

    llm = LLM(
        model=BASE_MODEL,
        enable_lora=True,
        max_lora_rank=64,         # Our adapters use rank 32, but allow headroom
        max_loras=1,              # Only one adapter active per request
        gpu_memory_utilization=0.85,
        max_model_len=2048,       # System prompt ~1400 tok + user ~50 tok + output ~500 tok
        tensor_parallel_size=int(os.getenv("TENSOR_PARALLEL", "1")),
        dtype="auto",
        trust_remote_code=True,
        quantization=os.getenv("QUANTIZATION", "bitsandbytes"),
        load_format="auto",
        enforce_eager=True,       # Skip CUDA graph compilation to save memory
    )

    elapsed = time.time() - start
    logger.info(f"Model loaded in {elapsed:.1f}s")

    # Verify LoRA adapters exist on disk
    for domain, config in LORA_ADAPTERS.items():
        adapter_path = config["path"]
        safetensors = os.path.join(adapter_path, "adapter_model.safetensors")
        adapter_cfg = os.path.join(adapter_path, "adapter_config.json")
        if os.path.isfile(safetensors) and os.path.isfile(adapter_cfg):
            size_mb = os.path.getsize(safetensors) / (1024 * 1024)
            logger.info(f"  LoRA {domain}: {adapter_path} ({size_mb:.0f} MB)")
        else:
            logger.error(f"  LoRA {domain}: MISSING at {adapter_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT FORMATTING
# ═══════════════════════════════════════════════════════════════════════════════


def format_prompt(domain: str, user_prompt: str) -> str:
    """Format the prompt with Llama 3.1 chat template + domain system prompt."""
    system = _system_prompts.get(domain, _system_prompts.get("blueprint", ""))

    # Llama 3.1 chat template
    return (
        f"<|begin_of_text|>"
        f"<|start_header_id|>system<|end_header_id|>\n\n"
        f"{system}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{user_prompt}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT CLEANING
# ═══════════════════════════════════════════════════════════════════════════════


def clean_output(domain: str, raw_output: str) -> str:
    """Post-process model output: strip artifacts, trailing delimiters, preamble."""
    text = raw_output.strip()

    # Remove markdown code fences if model includes them
    text = re.sub(r"^```\w*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)

    # Strip trailing hallucinated delimiters — Lesson #25
    # LLM hallucinates block-closing delimiters on last generated line
    lines = text.split("\n")
    if lines:
        lines[-1] = re.sub(r"\s*[{}\(\);>]+\s*$", "", lines[-1])
    text = "\n".join(lines)

    # Remove any preamble text before the DSL start marker
    marker = DSL_MARKERS.get(domain, "")
    if marker and marker in text:
        idx = text.index(marker)
        if idx > 0:
            text = text[idx:]

    # Strip trailing whitespace per line
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    return text.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST HANDLER
# ═══════════════════════════════════════════════════════════════════════════════


def handler(job):
    """
    RunPod serverless handler.

    Input:
    {
        "input": {
            "domain": "blueprint",       # Required: blueprint, bt, dt
            "prompt": "Create a ...",    # Required: natural language prompt
            "temperature": 0.1,          # Optional (default 0.1)
            "max_tokens": 1024           # Optional (default 1024)
        }
    }

    Output:
    {
        "output": {
            "dsl": "BLUEPRINT: BP_HealthPickup\n...",
            "domain": "blueprint",
            "tokens_generated": 245,
            "generation_time_ms": 3200
        }
    }
    """
    global llm

    start_time = time.time()
    job_input = job.get("input", {})

    # ─── Validate input ───

    domain = job_input.get("domain", "").lower().strip()
    prompt = job_input.get("prompt", "").strip()

    # Resolve domain aliases
    domain = DOMAIN_ALIASES.get(domain, domain)

    if not domain:
        return {"error": "Missing required field 'domain'. Use: blueprint, bt, or dt"}

    if domain not in LORA_ADAPTERS:
        return {"error": f"Invalid domain '{domain}'. Valid domains: blueprint, bt, dt"}

    if not prompt:
        return {"error": "Missing required field 'prompt'"}

    if len(prompt) > 10000:
        return {"error": "Prompt exceeds maximum length (10,000 characters)"}

    # ─── Ensure model loaded ───

    if llm is None:
        try:
            load_model()
        except Exception as e:
            logger.error(f"Model load failed: {e}")
            return {"error": f"Model failed to load: {str(e)}"}

    if llm is None:
        return {"error": "Model is not available"}

    # ─── Check adapter exists ───

    adapter_config = LORA_ADAPTERS[domain]
    adapter_path = adapter_config["path"]
    if not os.path.isdir(adapter_path):
        return {"error": f"LoRA adapter not found for domain '{domain}' at {adapter_path}"}

    # ─── Build generation request ───

    temperature = float(job_input.get("temperature", DEFAULT_TEMPERATURE))
    max_tokens = int(job_input.get("max_tokens", DEFAULT_MAX_TOKENS))

    # Clamp to safe ranges
    temperature = max(0.0, min(2.0, temperature))
    max_tokens = max(64, min(4096, max_tokens))

    formatted_prompt = format_prompt(domain, prompt)

    from vllm import SamplingParams
    from vllm.lora.request import LoRARequest

    # Estimate input tokens and cap max_tokens to fit within max_model_len (2048)
    input_token_count = len(formatted_prompt) // 4 + 50  # rough estimate: ~4 chars/token + margin
    try:
        input_token_count = len(llm.get_tokenizer().encode(formatted_prompt))
    except Exception:
        pass  # fall back to rough estimate
    available_tokens = 2048 - input_token_count
    max_tokens = min(max_tokens, max(64, available_tokens))

    sampling_params = SamplingParams(
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=DEFAULT_TOP_P,
        repetition_penalty=DEFAULT_REPETITION_PENALTY,
        stop=["<|eot_id|>", "<|end_of_text|>"],
    )

    # vLLM renamed lora_local_path → lora_path in newer versions
    try:
        lora_request = LoRARequest(
            lora_name=domain,
            lora_int_id=adapter_config["id"],
            lora_path=adapter_path,
        )
    except TypeError:
        lora_request = LoRARequest(
            lora_name=domain,
            lora_int_id=adapter_config["id"],
            lora_local_path=adapter_path,
        )

    # ─── Generate ───

    logger.info(
        f"Generating {domain} DSL | prompt_len={len(prompt)} | "
        f"input_tokens={input_token_count} | max_tokens={max_tokens} | "
        f"temp={temperature}"
    )

    try:
        outputs = llm.generate(
            [formatted_prompt],
            sampling_params,
            lora_request=lora_request,
        )
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return {"error": f"Generation failed: {str(e)}"}

    if not outputs or not outputs[0].outputs:
        return {"error": "Model produced no output"}

    raw_output = outputs[0].outputs[0].text
    dsl_text = clean_output(domain, raw_output)

    # ─── Collect metrics ───

    prompt_tokens = len(outputs[0].prompt_token_ids)
    completion_tokens = len(outputs[0].outputs[0].token_ids)
    elapsed_ms = int((time.time() - start_time) * 1000)

    logger.info(
        f"Done {domain} | tokens={completion_tokens} | latency={elapsed_ms}ms"
    )

    # ─── Build response ───

    return {
        "output": {
            "dsl": dsl_text,
            "domain": domain,
            "tokens_generated": completion_tokens,
            "generation_time_ms": elapsed_ms,
            "model": adapter_config["model_label"],
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONCURRENCY
# ═══════════════════════════════════════════════════════════════════════════════


def concurrency_modifier(current_concurrency):
    """70B models should process one request at a time per worker."""
    return 1


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("Arcwright Worker starting...")
    logger.info(f"Base model: {BASE_MODEL}")

    for domain, config in LORA_ADAPTERS.items():
        logger.info(f"  LoRA {domain}: {config['path']}")

    # Load system prompts from files
    _load_system_prompts()

    # Pre-load model on startup (reduces first-request latency)
    load_model()

    # Start RunPod serverless worker
    runpod.serverless.start({
        "handler": handler,
        "concurrency_modifier": concurrency_modifier,
    })
