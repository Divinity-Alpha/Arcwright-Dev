"""
Debug L01_04 truncation: print generation config, token IDs, check for EOS,
test with various max_new_tokens, and check DSLStoppingCriteria behavior.
"""
import os, sys, json, time
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, StoppingCriteria, StoppingCriteriaList
from peft import PeftModel

MODEL_PATH = "models/blueprint-lora-v9/final"
LESSON_PATH = "lessons/lesson_01.json"
PROMPT_ID = "L01_04"

# ---------- Load model ----------
print("=" * 60)
print("TRUNCATION DEBUGGER")
print("=" * 60)

adapter_cfg = json.load(open(f"{MODEL_PATH}/adapter_config.json"))
base_model_name = adapter_cfg.get("base_model_name_or_path", "meta-llama/Meta-Llama-3.1-70B")
print(f"\nBase model: {base_model_name}")

# Load system prompt
sys_prompt_path = f"{MODEL_PATH}/system_prompt.txt"
if os.path.exists(sys_prompt_path):
    SYSTEM_PROMPT = open(sys_prompt_path, encoding="utf-8").read().strip()
    print(f"System prompt: {len(SYSTEM_PROMPT)} chars")
else:
    print("WARNING: No system_prompt.txt found")
    SYSTEM_PROMPT = ""

print("\nLoading model (8-bit)...")
tokenizer = AutoTokenizer.from_pretrained(base_model_name)
bnb = BitsAndBytesConfig(load_in_8bit=True)
model = AutoModelForCausalLM.from_pretrained(
    base_model_name, quantization_config=bnb,
    device_map={"": 0}, low_cpu_mem_usage=True,
)
model = PeftModel.from_pretrained(model, MODEL_PATH)
model.eval()

# ---------- Load prompt ----------
lesson = json.load(open(LESSON_PATH, encoding="utf-8"))
prompt = None
for p in lesson["prompts"]:
    if p["id"] == PROMPT_ID:
        prompt = p
        break
assert prompt, f"Prompt {PROMPT_ID} not found"

instruction = prompt["instruction"]
expected = prompt["expected_dsl"]
print(f"\nPrompt: {instruction[:80]}...")
print(f"Expected DSL: {len(expected)} chars, {len(expected.splitlines())} lines")

# ---------- Format input ----------
formatted = (
    f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
    f"{SYSTEM_PROMPT}<|eot_id|>"
    f"<|start_header_id|>user<|end_header_id|>\n\n"
    f"{instruction}<|eot_id|>"
    f"<|start_header_id|>assistant<|end_header_id|>\n\n"
)

inputs = tokenizer(formatted, return_tensors="pt").to(model.device)
prompt_len = inputs["input_ids"].shape[1]

# ---------- Diagnostic 1: Generation config ----------
print("\n" + "=" * 60)
print("DIAGNOSTIC 1: Generation Config")
print("=" * 60)
print(f"Prompt length (tokens): {prompt_len}")
print(f"Model max_position_embeddings: {model.config.max_position_embeddings}")
print(f"Model max_length (if set): {getattr(model.config, 'max_length', 'NOT SET')}")
print(f"Model max_new_tokens (if set): {getattr(model.config, 'max_new_tokens', 'NOT SET')}")
print(f"Tokenizer model_max_length: {tokenizer.model_max_length}")

# Check EOS token IDs
eos_id = tokenizer.eos_token_id
eot_id = tokenizer.convert_tokens_to_ids("<|eot_id|>")
eot2_id = tokenizer.convert_tokens_to_ids("<|end_of_text|>")
print(f"\nEOS token ID: {eos_id} ('{tokenizer.decode([eos_id])}')")
print(f"<|eot_id|> token ID: {eot_id}")
print(f"<|end_of_text|> token ID: {eot2_id}")

stop_ids = [eos_id]
for tok_str in ["<|eot_id|>", "<|end_of_text|>"]:
    tid = tokenizer.convert_tokens_to_ids(tok_str)
    if tid is not None and tid != tokenizer.unk_token_id:
        stop_ids.append(tid)
print(f"Stop token IDs: {stop_ids}")

# ---------- Diagnostic 2: Raw generation WITHOUT stopping criteria ----------
print("\n" + "=" * 60)
print("DIAGNOSTIC 2: Raw generation (NO DSLStoppingCriteria)")
print("=" * 60)
print(f"max_new_tokens=2048, no custom stopping criteria")

start = time.time()
with torch.no_grad():
    output_raw = model.generate(
        **inputs, max_new_tokens=2048, temperature=0.1,
        do_sample=True, top_p=0.9, repetition_penalty=1.1,
        eos_token_id=stop_ids,
    )
elapsed = time.time() - start

gen_ids = output_raw[0][prompt_len:]
gen_text = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()
gen_text_with_special = tokenizer.decode(gen_ids, skip_special_tokens=False)

print(f"Generated {len(gen_ids)} tokens in {elapsed:.1f}s")
print(f"Output text length: {len(gen_text)} chars")
print(f"\n--- RAW OUTPUT (with special tokens) ---")
print(gen_text_with_special[:800])
print(f"\n--- DECODED OUTPUT (no special tokens) ---")
print(gen_text[:800])

# Check for EOS/EOT in generated tokens
print(f"\n--- EOS/EOT TOKEN SCAN ---")
for i, tid in enumerate(gen_ids.tolist()):
    if tid in stop_ids:
        context_start = max(0, i - 3)
        context_ids = gen_ids[context_start:i+1].tolist()
        context_text = tokenizer.decode(gen_ids[context_start:i+1])
        print(f"  STOP token {tid} at position {i}/{len(gen_ids)}")
        print(f"  Context tokens: {context_ids}")
        print(f"  Context text: {repr(context_text)}")
        # Show what was generated up to this point
        text_before = tokenizer.decode(gen_ids[:i], skip_special_tokens=True)
        print(f"  Text before stop ({len(text_before)} chars): ...{repr(text_before[-100:])}")
        break
else:
    print(f"  No stop token found in {len(gen_ids)} generated tokens!")
    print(f"  Hit max_new_tokens limit of 2048")

# ---------- Diagnostic 3: WITH stopping criteria (reproduce the bug) ----------
print("\n" + "=" * 60)
print("DIAGNOSTIC 3: With DSLStoppingCriteria (reproduce bug)")
print("=" * 60)

# Import the stopping criteria from exam runner
from scripts_12_run_exam_stopper import DSLStoppingCriteria as _  # won't work, use inline

class DebugDSLStop(StoppingCriteria):
    _DSL_PREFIXES = (
        "BLUEPRINT:", "PARENT:", "CATEGORY:", "GRAPH:",
        "VAR ", "NODE ", "EXEC ", "DATA ", "#",
    )

    def __init__(self, tokenizer, prompt_length, check_every=5):
        self.tokenizer = tokenizer
        self.prompt_length = prompt_length
        self.check_every = check_every
        self._calls = 0
        self.stop_reason = None

    def __call__(self, input_ids, scores, **kwargs):
        self._calls += 1
        gen_len = input_ids.shape[1] - self.prompt_length
        if gen_len < 30:
            return False
        if self._calls % self.check_every != 0:
            return False

        text = self.tokenizer.decode(
            input_ids[0][self.prompt_length:], skip_special_tokens=True,
        )
        if "\n" not in text:
            return False
        completed_text = text.rsplit("\n", 1)[0]
        if not ("BLUEPRINT:" in completed_text and "GRAPH:" in completed_text
                and "NODE " in completed_text
                and ("EXEC " in completed_text or "DATA " in completed_text)):
            return False

        # Double newline check
        if completed_text.rstrip(" ").endswith("\n"):
            self.stop_reason = f"DOUBLE_NEWLINE at call #{self._calls}, gen_len={gen_len}"
            print(f"  ** DSLStop TRIGGERED: {self.stop_reason}")
            print(f"  ** completed_text ends with: {repr(completed_text[-60:])}")
            has_data = "DATA " in completed_text
            print(f"  ** Has DATA lines: {has_data}")
            return True

        lines = completed_text.split("\n")
        last_complete = lines[-1].strip() if lines else ""
        if last_complete and not any(last_complete.startswith(p) for p in self._DSL_PREFIXES):
            self.stop_reason = f"NON_DSL_LINE at call #{self._calls}: '{last_complete[:50]}'"
            print(f"  ** DSLStop TRIGGERED: {self.stop_reason}")
            return True
        return False

stopper = DebugDSLStop(tokenizer, prompt_len)

start = time.time()
with torch.no_grad():
    output_stop = model.generate(
        **inputs, max_new_tokens=2048, temperature=0.1,
        do_sample=True, top_p=0.9, repetition_penalty=1.1,
        eos_token_id=stop_ids,
        stopping_criteria=StoppingCriteriaList([stopper]),
    )
elapsed = time.time() - start

gen_ids_stop = output_stop[0][prompt_len:]
gen_text_stop = tokenizer.decode(gen_ids_stop, skip_special_tokens=True).strip()

print(f"\nGenerated {len(gen_ids_stop)} tokens in {elapsed:.1f}s")
print(f"Stop reason: {stopper.stop_reason or 'EOS/max_tokens (not DSLStop)'}")
print(f"Output text length: {len(gen_text_stop)} chars")
print(f"\n--- OUTPUT ---")
print(gen_text_stop[:600])

# ---------- Diagnostic 4: max_seq_length check ----------
print("\n" + "=" * 60)
print("DIAGNOSTIC 4: max_seq_length impact")
print("=" * 60)
print(f"Prompt tokens: {prompt_len}")
print(f"If max_seq_length=1024 applied: {1024 - prompt_len} tokens left for generation")
print(f"If max_seq_length=2048 applied: {2048 - prompt_len} tokens left for generation")
print(f"Actual max_new_tokens=2048 means: {prompt_len + 2048} total sequence possible")
print(f"model.config.max_position_embeddings: {model.config.max_position_embeddings}")

# ---------- Summary ----------
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Prompt tokens: {prompt_len}")
print(f"Raw gen (no DSLStop): {len(gen_ids)} tokens, {len(gen_text)} chars")
print(f"With DSLStop: {len(gen_ids_stop)} tokens, {len(gen_text_stop)} chars")
print(f"DSLStop reason: {stopper.stop_reason or 'N/A'}")
if len(gen_text) > len(gen_text_stop):
    print(f"\n** DSLStoppingCriteria is cutting output short! **")
    print(f"   Lost {len(gen_text) - len(gen_text_stop)} chars")
