"""
quick_70b_test.py — Verify 70B model loads on this hardware.

Loads Meta-Llama-3.1-70B in 4-bit with RAM-saving settings,
runs a single inference prompt, and reports timing + VRAM usage.
"""

import os
import sys
import time

# Pin to GPU 0 before any torch imports
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_ID = "meta-llama/Meta-Llama-3.1-70B"
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
    print("  STEP 1: Quick 70B Inference Test")
    print("=" * 60)

    # Step 1.1: Check GPU
    print(f"\n[1.1] GPU check")
    if not torch.cuda.is_available():
        print("  ERROR: CUDA not available")
        sys.exit(1)

    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    cc = torch.cuda.get_device_capability(0)
    print(f"  GPU: {gpu_name}")
    print(f"  VRAM: {vram_gb:.1f} GB")
    print(f"  Compute capability: {cc[0]}.{cc[1]}")
    print(f"  System RAM constraint: 32GB -- using low_cpu_mem_usage=True")

    # Step 1.2: Load tokenizer
    print(f"\n[1.2] Loading tokenizer: {MODEL_ID}")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token
    print(f"  Done ({time.time() - t0:.1f}s)")

    # Step 1.3: Load model in 4-bit
    print(f"\n[1.3] Loading 70B model in 4-bit quantization...")
    print(f"  Strategy: device_map='auto', max_memory={{0: '88GiB', 'cpu': '20GiB'}}")
    print(f"  Offload folder: offload/ (disk safety net)")
    t0 = time.time()

    # Create offload folder for safety
    os.makedirs("offload", exist_ok=True)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=False,  # skip double quant to reduce CPU RAM pressure
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        max_memory={0: "88GiB", "cpu": "20GiB"},
        offload_folder="offload",
        low_cpu_mem_usage=True,
    )
    model.eval()

    load_time = time.time() - t0
    vram_used = torch.cuda.memory_allocated(0) / 1024**3
    vram_reserved = torch.cuda.memory_reserved(0) / 1024**3
    print(f"  Model loaded in {load_time:.1f}s")
    print(f"  VRAM allocated: {vram_used:.1f} GB")
    print(f"  VRAM reserved:  {vram_reserved:.1f} GB")

    # Print device map summary
    if hasattr(model, 'hf_device_map'):
        devices = set(str(v) for v in model.hf_device_map.values())
        print(f"  Device map: {', '.join(sorted(devices))}")

    # Step 1.4: Run inference
    print(f"\n[1.4] Running inference...")
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

    # Build stop tokens
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

    # Step 1.5: Show output
    print(f"\n[1.5] Model output:")
    print("-" * 60)
    print(response)
    print("-" * 60)

    # Step 1.6: Summary
    print(f"\n[1.6] RESULT: {'PASS' if len(response) > 20 else 'FAIL'}")
    print(f"  Model loaded and generated {new_tokens} tokens successfully.")
    print(f"  Ready for full pipeline.")

    # Cleanup
    del model
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
