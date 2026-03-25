"""
dt_run_exam.py
--------------
DT-specific exam runner. Loads DT lesson prompts, runs inference with the DT adapter,
validates output with dt_parser.parse(), and scores syntax validity and similarity.

Usage:
    python scripts/dt_run_exam.py --lesson lessons/dt_lesson_01.json --model models/dt-lora-v1/final
"""

import argparse
import json
import sys
import time
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from stop_signal_utils import is_stop_requested, clear_signal
from error_handler import per_prompt_timeout

# Per-prompt generation timeout (seconds)
GENERATE_TIMEOUT = 300

# Default DT system prompt — prefer loading from model directory
DEFAULT_DT_SYSTEM_PROMPT = (
    "You are an AI that generates Unreal Engine 5 Data Table DSL from natural language "
    "descriptions. Output ONLY valid DT DSL text with no explanation, no markdown, no code fences. "
    "Always start with DATATABLE: and STRUCT: headers, declare columns with COLUMN, then add rows with ROW."
)

# Global — set during load_model()
SYSTEM_PROMPT = DEFAULT_DT_SYSTEM_PROMPT


class DTStoppingCriteria:
    """Stop generation once a complete DT DSL block is detected."""

    _DT_PREFIXES = (
        "DATATABLE:", "STRUCT:", "COLUMN ", "ROW ",
    )

    def __init__(self, tokenizer, prompt_length, check_every=5):
        self.tokenizer = tokenizer
        self.prompt_length = prompt_length
        self.check_every = check_every
        self._calls = 0

    def __call__(self, input_ids, scores, **kwargs):
        self._calls += 1
        gen_len = input_ids.shape[1] - self.prompt_length

        if gen_len < 20:
            return False

        if self._calls % self.check_every != 0:
            return False

        text = self.tokenizer.decode(
            input_ids[0][self.prompt_length:], skip_special_tokens=True,
        )

        if "\n" not in text:
            return False

        completed_text = text.rsplit("\n", 1)[0]

        # Must have basic DT structure
        if not ("DATATABLE:" in completed_text and "STRUCT:" in completed_text):
            return False

        # Must have at least one column
        if "COLUMN " not in completed_text:
            return False

        # Must have at least one row
        if "ROW " not in completed_text:
            return False

        # Double newline after content = done
        if completed_text.rstrip(" ").endswith("\n"):
            return True

        # Last completed line is not a DT keyword = junk started
        lines = completed_text.split("\n")
        last_complete = lines[-1].strip() if lines else ""
        if last_complete and not any(last_complete.startswith(p) for p in self._DT_PREFIXES):
            # Allow comments
            if not last_complete.startswith("//"):
                return True

        return False


def load_model(model_path, base_model=None):
    """Load the DT fine-tuned model and its system prompt."""
    global SYSTEM_PROMPT
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    model_dir = Path(model_path)

    # Auto-detect base model
    if base_model is None:
        adapter_config = model_dir / "adapter_config.json"
        if adapter_config.exists():
            with open(adapter_config) as f:
                ac = json.load(f)
            base_model = ac.get("base_model_name_or_path", "meta-llama/Meta-Llama-3.1-70B")
        else:
            base_model = "meta-llama/Meta-Llama-3.1-70B"

    # Load system prompt from model directory
    prompt_path = model_dir / "system_prompt.txt"
    if not prompt_path.exists():
        prompt_path = model_dir.parent / "system_prompt.txt"
    if prompt_path.exists():
        SYSTEM_PROMPT = prompt_path.read_text(encoding="utf-8").strip()
        print(f"Loaded DT system prompt from {prompt_path} ({len(SYSTEM_PROMPT):,} chars)")
    else:
        # Try project-level DT prompt
        dt_prompt_path = Path(__file__).parent / "dt_system_prompt.txt"
        if dt_prompt_path.exists():
            SYSTEM_PROMPT = dt_prompt_path.read_text(encoding="utf-8").strip()
            print(f"Loaded DT system prompt from {dt_prompt_path} ({len(SYSTEM_PROMPT):,} chars)")
        else:
            SYSTEM_PROMPT = DEFAULT_DT_SYSTEM_PROMPT
            print("WARNING: No dt_system_prompt.txt found, using default")

    print(f"Loading base model: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model)

    if "70b" in base_model.lower():
        bnb_config = BitsAndBytesConfig(load_in_8bit=True)
    else:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
        )

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map={"": 0},
        low_cpu_mem_usage=True,
    )

    print(f"Loading DT LoRA adapter: {model_path}")
    model = PeftModel.from_pretrained(model, model_path)
    model.eval()
    return model, tokenizer, base_model


def generate(model, tokenizer, instruction, max_tokens=1024, temperature=0.1):
    """Generate DT DSL from an instruction."""
    import torch
    from transformers import StoppingCriteriaList

    formatted = (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{SYSTEM_PROMPT}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{instruction}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )

    inputs = tokenizer(formatted, return_tensors="pt").to(model.device)

    stop_ids = [tokenizer.eos_token_id]
    for tok in ["<|eot_id|>", "<|end_of_text|>"]:
        tid = tokenizer.convert_tokens_to_ids(tok)
        if tid is not None and tid != tokenizer.unk_token_id:
            stop_ids.append(tid)

    dt_stop = DTStoppingCriteria(tokenizer, inputs["input_ids"].shape[1])

    with torch.no_grad():
        output = model.generate(
            **inputs, max_new_tokens=max_tokens, temperature=temperature,
            do_sample=temperature > 0, top_p=0.9, repetition_penalty=1.1,
            eos_token_id=stop_ids,
            stopping_criteria=StoppingCriteriaList([dt_stop]),
        )

    raw = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    # Extract DT DSL from output
    lines = raw.split('\n')
    dsl_lines = []
    in_dsl = False
    for line in lines:
        s = line.strip()
        if s.startswith("DATATABLE:"):
            in_dsl = True
        # Stop at hallucinated content
        if in_dsl and s.startswith("Create a "):
            break
        if in_dsl and any(s.startswith(m) for m in ["## ", "---", "**", "### ", "```"]):
            break
        if in_dsl:
            dsl_lines.append(line)

    if dsl_lines:
        while dsl_lines and not dsl_lines[-1].strip():
            dsl_lines.pop()
        # Strip trailing delimiters the model hallucinates on the last line (Lesson #25)
        if dsl_lines:
            dsl_lines[-1] = re.sub(r'\s*[{}\(\);>]+\s*$', '', dsl_lines[-1])
        return '\n'.join(dsl_lines).strip(), raw

    return raw, raw


def validate_dt_dsl(dsl_text):
    """Validate DT DSL using the dt_parser and return structured result."""
    try:
        dt_parser_dir = Path(__file__).parent
        if str(dt_parser_dir) not in sys.path:
            sys.path.insert(0, str(dt_parser_dir))
        from dt_parser.dt_parser import parse as dt_parse

        result = dt_parse(dsl_text)
        ir = result.get("ir")
        errors = result.get("errors", [])
        stats = result.get("stats", {})

        if errors:
            return {
                "valid": False,
                "table_name": ir["metadata"].get("table_name") if ir else None,
                "columns": stats.get("columns", 0),
                "rows": stats.get("rows", 0),
                "error": "; ".join(errors),
            }

        return {
            "valid": True,
            "table_name": ir["metadata"].get("table_name") if ir else None,
            "columns": stats.get("columns", 0),
            "rows": stats.get("rows", 0),
            "error": None,
        }
    except Exception as e:
        return {
            "valid": False,
            "table_name": None,
            "columns": 0,
            "rows": 0,
            "error": str(e),
        }


def compare_dt_outputs(expected_dsl, actual_dsl):
    """Compare expected vs actual DT DSL and produce a diff report."""
    expected_lines = set(
        l.strip() for l in expected_dsl.splitlines() if l.strip()
    )
    actual_lines = set(
        l.strip() for l in actual_dsl.splitlines() if l.strip()
    )

    missing = expected_lines - actual_lines
    extra = actual_lines - expected_lines
    correct = expected_lines & actual_lines

    total = len(expected_lines)
    score = len(correct) / max(total, 1)

    # Categorize
    missing_columns = [l for l in missing if l.startswith("COLUMN ")]
    missing_rows = [l for l in missing if l.startswith("ROW ")]
    missing_headers = [l for l in missing if l.startswith(("DATATABLE:", "STRUCT:"))]

    return {
        "score": round(score, 3),
        "correct_lines": len(correct),
        "total_expected_lines": total,
        "missing_lines": sorted(list(missing)),
        "extra_lines": sorted(list(extra)),
        "missing_columns": missing_columns,
        "missing_rows": missing_rows,
        "missing_headers": missing_headers,
    }


def run_dt_exam(lesson_path, model_path, base_model, output_dir):
    """Run all prompts from a DT lesson through the model."""
    with open(lesson_path, encoding="utf-8") as f:
        lesson = json.load(f)

    print(f"\n{'='*60}")
    print(f"  DT EXAM: {lesson['lesson_name']}")
    print(f"  {len(lesson['prompts'])} prompts")
    print(f"  Model: {model_path}")
    print(f"{'='*60}\n")

    model, tokenizer, detected_base = load_model(model_path, base_model)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"dt_exam_{lesson['lesson_id']}_{ts}.jsonl"
    summary_file = output_dir / f"dt_exam_{lesson['lesson_id']}_{ts}_summary.json"

    results = []
    total_score = 0
    valid_count = 0
    timeout_count = 0

    for i, prompt in enumerate(lesson["prompts"]):
        print(f"[{i+1}/{len(lesson['prompts'])}] {prompt['id']}: {prompt['instruction'][:60]}...")

        start = time.time()

        gen_result, timed_out = per_prompt_timeout(
            lambda p=prompt: generate(model, tokenizer, p["instruction"]),
            timeout_seconds=GENERATE_TIMEOUT,
        )

        if timed_out:
            elapsed = time.time() - start
            cleaned_dsl = "[TIMEOUT]"
            raw_output = f"[Generation timed out after {GENERATE_TIMEOUT}s]"
            timeout_count += 1
            print(f"  [TIMEOUT] Prompt timed out after {GENERATE_TIMEOUT}s")
        else:
            cleaned_dsl, raw_output = gen_result
            elapsed = time.time() - start

        validation = validate_dt_dsl(cleaned_dsl)
        comparison = compare_dt_outputs(prompt["expected_dsl"], cleaned_dsl)

        if timed_out:
            print(f"  [TIMEOUT] Score: 0% | {elapsed:.1f}s")
        else:
            status = "[OK]" if validation["valid"] else "[X]"
            print(f"  {status} Score: {comparison['score']:.0%} | "
                  f"Cols: {validation['columns']} | "
                  f"Rows: {validation['rows']} | "
                  f"{elapsed:.1f}s")

            if not validation["valid"]:
                err = validation["error"]
                if err:
                    print(f"  Error: {err[:80]}")

        result = {
            "prompt_id": prompt["id"],
            "category": prompt["category"],
            "instruction": prompt["instruction"],
            "expected_dsl": prompt["expected_dsl"],
            "actual_dsl": cleaned_dsl,
            "raw_output": raw_output,
            "validation": validation,
            "comparison": comparison,
            "time_seconds": round(elapsed, 1),
            "status": "timeout_skipped" if timed_out else "completed",
        }
        results.append(result)

        if validation["valid"] and not timed_out:
            valid_count += 1
        if not timed_out:
            total_score += comparison["score"]

        # Write incrementally
        with open(results_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

        if is_stop_requested():
            print(f"\n  GRACEFUL STOP after {i+1}/{len(lesson['prompts'])} prompts.")
            clear_signal()
            break

    # Summary
    avg_score = total_score / max(len(results), 1)
    summary = {
        "lesson_id": lesson["lesson_id"],
        "lesson_name": lesson["lesson_name"],
        "domain": "data_table",
        "model": str(model_path),
        "base_model": detected_base,
        "timestamp": ts,
        "total_prompts": len(results),
        "valid_syntax": valid_count,
        "valid_syntax_pct": round(valid_count / max(len(results), 1) * 100, 1),
        "avg_similarity_score": round(avg_score * 100, 1),
        "timeout_count": timeout_count,
        "per_category": {},
    }

    for r in results:
        cat = r["category"]
        if cat not in summary["per_category"]:
            summary["per_category"][cat] = {"count": 0, "valid": 0, "avg_score": 0}
        summary["per_category"][cat]["count"] += 1
        if r["validation"]["valid"]:
            summary["per_category"][cat]["valid"] += 1
        summary["per_category"][cat]["avg_score"] += r["comparison"]["score"]

    for cat in summary["per_category"]:
        s = summary["per_category"][cat]
        s["avg_score"] = round(s["avg_score"] / max(s["count"], 1) * 100, 1)

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"  DT EXAM RESULTS")
    print(f"{'='*60}")
    print(f"  Valid syntax:     {valid_count}/{len(results)} ({summary['valid_syntax_pct']}%)")
    print(f"  Avg similarity:   {summary['avg_similarity_score']}%")
    print(f"  Timeouts:         {timeout_count}")
    print(f"  Results:          {results_file}")
    print(f"  Summary:          {summary_file}")
    print(f"{'='*60}\n")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run a DT lesson exam")
    parser.add_argument("--lesson", required=True, help="Path to DT lesson JSON file")
    parser.add_argument("--model", required=True, help="Path to DT LoRA model (e.g. models/dt-lora-v1/final)")
    parser.add_argument("--base_model", default=None, help="Base model override")
    parser.add_argument("--output", default="results/dt_exams", help="Output directory")
    args = parser.parse_args()

    run_dt_exam(args.lesson, args.model, args.base_model, args.output)


if __name__ == "__main__":
    main()
