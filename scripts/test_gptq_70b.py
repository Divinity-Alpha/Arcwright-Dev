"""
test_gptq_70b.py — Test GPTQ 4-bit quantized 70B model on Blackwell GPU.

Bypasses bitsandbytes entirely. Uses pre-quantized GPTQ model with
exllama/triton kernels which should work on sm_120.
"""

import os
import sys
import time

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Pre-quantized GPTQ model (~35GB in 4-bit)
MODEL_ID = "hugging-quants/Meta-Llama-3.1-70B-Instruct-GPTQ-INT4"
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


def main():
    print("=" * 60)
    print("  GPTQ 4-bit 70B Test on Blackwell (sm_120)")
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

    # Load tokenizer
    print(f"\n[2] Loading tokenizer: {MODEL_ID}")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token
    print(f"  Done ({time.time() - t0:.1f}s)")

    # Load GPTQ model
    print(f"\n[3] Loading GPTQ 4-bit model...")
    print(f"  Model: {MODEL_ID}")
    print(f"  No bitsandbytes involved — uses GPTQ/exllama kernels")
    t0 = time.time()

    try:
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            device_map="auto",
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
        )
        model.eval()
    except Exception as e:
        print(f"\n  GPTQ LOAD FAILED: {type(e).__name__}: {e}")
        sys.exit(1)

    load_time = time.time() - t0
    vram_used = torch.cuda.memory_allocated(0) / 1024**3
    vram_reserved = torch.cuda.memory_reserved(0) / 1024**3
    print(f"  Model loaded in {load_time:.1f}s")
    print(f"  VRAM allocated: {vram_used:.1f} GB")
    print(f"  VRAM reserved:  {vram_reserved:.1f} GB")

    if hasattr(model, 'hf_device_map'):
        devices = set(str(v) for v in model.hf_device_map.values())
        print(f"  Device map: {', '.join(sorted(devices))}")

    # Run inference
    print(f"\n[4] Running inference...")
    print(f"  Prompt: \"{PROMPT}\"")

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
    tokens_per_sec = new_tokens / gen_time if gen_time > 0 else 0

    response = tokenizer.decode(output[0][input_len:], skip_special_tokens=True).strip()

    print(f"\n  Generation time: {gen_time:.1f}s")
    print(f"  New tokens: {new_tokens}")
    print(f"  Speed: {tokens_per_sec:.1f} tokens/sec")
    print(f"  Peak VRAM: {torch.cuda.max_memory_allocated(0) / 1024**3:.1f} GB")

    # Output
    print(f"\n[5] Model output:")
    print("-" * 60)
    print(response)
    print("-" * 60)

    # Verify output quality (check for garbage/corruption)
    has_structure = any(kw in response for kw in ["BLUEPRINT", "NODE", "Blueprint", "Node", "class", "def"])
    is_garbage = len(response) > 0 and sum(1 for c in response if c.isalpha()) / max(len(response), 1) < 0.3

    if is_garbage:
        print(f"\n[6] RESULT: FAIL — Output appears corrupted/garbage")
    elif len(response) < 20:
        print(f"\n[6] RESULT: FAIL — Output too short ({len(response)} chars)")
    else:
        print(f"\n[6] RESULT: PASS")
        print(f"  GPTQ 4-bit works on Blackwell sm_120!")
        print(f"  Model loaded in {load_time:.1f}s, generates at {tokens_per_sec:.1f} tok/s")

    del model
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
