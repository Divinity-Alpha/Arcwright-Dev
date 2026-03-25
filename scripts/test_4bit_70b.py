"""Quick test: can we load 70B in 4-bit on Blackwell (sm_120)?

Tests bitsandbytes load_in_4bit with NF4 quantization.
Previous attempts segfaulted — this test checks if newer packages fixed it.
"""
import os
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
print(f"Compute: {torch.cuda.get_device_capability(0)}")

import bitsandbytes as bnb
print(f"bitsandbytes: {bnb.__version__}")

from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

model_name = "meta-llama/Meta-Llama-3.1-70B"

print(f"\n{'='*60}")
print(f"Testing 4-bit NF4 quantization: {model_name}")
print(f"{'='*60}")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

t0 = time.time()
try:
    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    load_time = time.time() - t0
    vram_used = torch.cuda.memory_allocated(0) / 1024**3
    print(f"\n*** 4-BIT LOAD SUCCESS ***")
    print(f"Load time: {load_time:.1f}s")
    print(f"VRAM used: {vram_used:.1f} GB")

    # Quick inference test to make sure it doesn't segfault on forward pass
    print("\nTesting forward pass...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    inputs = tokenizer("Hello world", return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=10)
    result = tokenizer.decode(out[0], skip_special_tokens=True)
    print(f"Generated: {result}")
    print(f"\n*** 4-BIT FULLY WORKING ***")

    del model
    torch.cuda.empty_cache()
    sys.exit(0)

except Exception as e:
    elapsed = time.time() - t0
    print(f"\n*** 4-BIT FAILED after {elapsed:.1f}s ***")
    print(f"Error type: {type(e).__name__}")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
