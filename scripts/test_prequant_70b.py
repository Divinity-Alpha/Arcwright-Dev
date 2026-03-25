"""
test_prequant_70b.py -- Test pre-quantized 70B models (GPTQ then AWQ).

Bypasses bitsandbytes entirely. Tries two pre-quantized models in order:
  1. hugging-quants/Meta-Llama-3.1-70B-GPTQ-INT4
  2. hugging-quants/Meta-Llama-3.1-70B-AWQ-INT4

Modern transformers (>=4.36) has built-in GPTQ/AWQ support via
AutoModelForCausalLM.from_pretrained() -- no auto-gptq or autoawq needed.

Expected: ~38GB VRAM, loads in 5-10 minutes on PRO 6000.
"""

import os
import sys
import time

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODELS = [
    {
        "id": "hugging-quants/Meta-Llama-3.1-70B-Instruct-GPTQ-INT4",
        "type": "GPTQ",
    },
    {
        "id": "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
        "type": "AWQ",
    },
]

PROMPT = "Create a Blueprint that prints Hello World when the game starts"

SYSTEM_PROMPT = """You are a Blueprint programming assistant for Unreal Engine 5. \
Given a natural language description of desired game behavior, you generate \
valid Blueprint DSL code that implements that behavior.

Your output must follow the Blueprint DSL format:
- BLUEPRINT: <n>
- PARENT: <parent class>
- GRAPH: <graph name>
- NODE <id>: <type> [properties]
- EXEC <from>.<pin> -> <to>.<pin>
- DATA <from>.<pin> -> <to>.<pin> [<type>]

Generate only the DSL code, no explanations."""


def try_load_model(model_info):
    """Attempt to load a pre-quantized model. Returns (model, tokenizer, load_time) or raises."""
    model_id = model_info["id"]
    model_type = model_info["type"]

    print(f"\n[2] Loading tokenizer: {model_id}")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = tokenizer.eos_token
    print(f"  Done ({time.time() - t0:.1f}s)")

    print(f"\n[3] Loading {model_type} 4-bit model...")
    print(f"  Model: {model_id}")
    print(f"  Pre-quantized on disk -- no bitsandbytes, no on-the-fly quantization")
    t0 = time.time()

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    )
    model.eval()

    load_time = time.time() - t0
    return model, tokenizer, load_time


def run_inference(model, tokenizer):
    """Run the Hello World inference test. Returns (response, gen_time, new_tokens)."""
    formatted = (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{SYSTEM_PROMPT}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{PROMPT}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )

    inputs = tokenizer(formatted, return_tensors="pt").to(model.device)
    input_len = inputs["input_ids"].shape[1]
    print(f"  Input tokens: {input_len}")

    stop_ids = [tokenizer.eos_token_id]
    for tok in ["<|eot_id|>", "<|end_of_text|>"]:
        tid = tokenizer.convert_tokens_to_ids(tok)
        if tid is not None and tid != tokenizer.unk_token_id:
            stop_ids.append(tid)

    t0 = time.time()
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.1,
            eos_token_id=stop_ids,
        )

    gen_time = time.time() - t0
    new_tokens = output.shape[1] - input_len
    response = tokenizer.decode(output[0][input_len:], skip_special_tokens=True).strip()
    return response, gen_time, new_tokens


def main():
    print("=" * 60)
    print("  Pre-Quantized 70B Test (GPTQ -> AWQ fallback)")
    print("=" * 60)

    # GPU info
    print(f"\n[1] GPU check")
    if not torch.cuda.is_available():
        print("  ERROR: CUDA not available")
        sys.exit(1)

    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    cc = torch.cuda.get_device_capability(0)
    print(f"  GPU: {gpu_name}")
    print(f"  VRAM: {vram_gb:.1f} GB")
    print(f"  Compute capability: {cc[0]}.{cc[1]}")

    # Try each model in order
    model = None
    tokenizer = None
    load_time = 0
    winning_model = None

    for model_info in MODELS:
        model_type = model_info["type"]
        model_id = model_info["id"]

        print(f"\n{'='*60}")
        print(f"  Trying {model_type}: {model_id}")
        print(f"{'='*60}")

        try:
            model, tokenizer, load_time = try_load_model(model_info)
            winning_model = model_info
            break
        except Exception as e:
            print(f"\n  FAIL {model_type}: {type(e).__name__}: {e}")
            # Clean up partial load
            model = None
            torch.cuda.empty_cache()
            continue

    if model is None:
        print("\n" + "=" * 60)
        print("  ALL MODELS FAILED")
        print("=" * 60)
        sys.exit(1)

    # Report load stats
    vram_used = torch.cuda.memory_allocated(0) / 1024**3
    vram_reserved = torch.cuda.memory_reserved(0) / 1024**3
    print(f"\n  Model loaded in {load_time:.1f}s")
    print(f"  VRAM allocated: {vram_used:.1f} GB")
    print(f"  VRAM reserved:  {vram_reserved:.1f} GB")

    if hasattr(model, 'hf_device_map'):
        devices = set(str(v) for v in model.hf_device_map.values())
        print(f"  Device map: {', '.join(sorted(devices))}")

    # Run inference
    print(f"\n[4] Running inference...")
    print(f"  Prompt: \"{PROMPT}\"")

    response, gen_time, new_tokens = run_inference(model, tokenizer)
    tokens_per_sec = new_tokens / gen_time if gen_time > 0 else 0

    print(f"\n  Generation time: {gen_time:.1f}s")
    print(f"  New tokens: {new_tokens}")
    print(f"  Speed: {tokens_per_sec:.1f} tokens/sec")
    print(f"  Peak VRAM: {torch.cuda.max_memory_allocated(0) / 1024**3:.1f} GB")

    # Output
    print(f"\n[5] Model output:")
    print("-" * 60)
    print(response)
    print("-" * 60)

    # Verify output quality
    is_garbage = len(response) > 0 and sum(1 for c in response if c.isalpha()) / max(len(response), 1) < 0.3

    print(f"\n[6] RESULT:")
    if is_garbage:
        print(f"  FAIL -- Output appears corrupted/garbage")
    elif len(response) < 20:
        print(f"  FAIL -- Output too short ({len(response)} chars)")
    else:
        print(f"  PASS -- {winning_model['type']} 4-bit works!")
        print(f"  Model: {winning_model['id']}")
        print(f"  Loaded in {load_time:.1f}s, generates at {tokens_per_sec:.1f} tok/s")
        print(f"  VRAM: {vram_used:.1f} GB allocated")

    # Cleanup
    del model
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
