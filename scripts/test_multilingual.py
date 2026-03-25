"""
test_multilingual.py
--------------------
Tests whether fine-tuned LoRA adapters accept non-English prompts and produce
correct English-only DSL output. LLaMA 3.1 70B natively understands these
languages; this test checks whether LoRA fine-tuning degraded that capability.

Usage:
    python scripts/test_multilingual.py
    python scripts/test_multilingual.py --domain blueprint
    python scripts/test_multilingual.py --domain behavior_tree
    python scripts/test_multilingual.py --domain data_table
    python scripts/test_multilingual.py --languages en,ja,zh,ko
    python scripts/test_multilingual.py --skip-load  # reuse cached results

Reports a language x domain matrix of pass/fail results.
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import io
if os.name == 'nt':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# Force unbuffered output for background task monitoring
os.environ['PYTHONUNBUFFERED'] = '1'

# ── Config ────────────────────────────────────────────────────────────
BASE_MODEL = "meta-llama/Meta-Llama-3.1-70B"

ADAPTERS = {
    "blueprint": "models/blueprint-lora-v11/final",
    "behavior_tree": "models/bt-lora-v3/final",
    "data_table": "models/dt-lora-v3/final",
}

SYSTEM_PROMPTS = {
    "blueprint": "scripts/system_prompt.txt",
    "behavior_tree": "scripts/bt_system_prompt.txt",
    "data_table": "scripts/dt_system_prompt.txt",
}

TEST_SUITE = "tests/multilingual_test_suite.json"
RESULTS_DIR = "results/multilingual"

# Multilingual addendum appended to each system prompt
MULTILINGUAL_ADDENDUM = (
    "\n\nIMPORTANT: The user may write their request in any language "
    "(English, Spanish, French, German, Japanese, Korean, Chinese, Portuguese, "
    "Russian, Arabic, Hindi, Turkish, or others). Regardless of the input language, "
    "you MUST always output valid English DSL. Never translate DSL keywords, node names, "
    "pin names, or type names into other languages. Only the DSL output matters — "
    "understand the user's intent in their language, then produce English DSL."
)

# ── Non-ASCII leakage detection ───────────────────────────────────────
# DSL keyword positions where non-ASCII characters indicate language leakage
# We allow non-ASCII in string literal values (e.g. PrintString content)
# but NOT in structural keywords

BP_STRUCTURAL_RE = re.compile(
    r'^(BLUEPRINT|PARENT|CATEGORY|GRAPH|VAR|NODE|EXEC|DATA)\b',
    re.MULTILINE
)
BT_STRUCTURAL_RE = re.compile(
    r'^(BEHAVIORTREE|BLACKBOARD|KEY|TREE|SELECTOR|SEQUENCE|SIMPLEPARARALLEL|'
    r'TASK|DECORATOR|SERVICE)\b',
    re.MULTILINE
)
DT_STRUCTURAL_RE = re.compile(
    r'^(DATATABLE|STRUCT|COLUMN|ROW)\b',
    re.MULTILINE
)

STRUCTURAL_RES = {
    "blueprint": BP_STRUCTURAL_RE,
    "behavior_tree": BT_STRUCTURAL_RE,
    "data_table": DT_STRUCTURAL_RE,
}


def has_nonascii_leakage(dsl_text: str, domain: str) -> tuple[bool, list[str]]:
    """Check if non-ASCII characters appear in DSL keyword positions.

    Returns (has_leak, list_of_offending_lines).
    Allows non-ASCII in string literal values (quoted content).
    """
    issues = []
    struct_re = STRUCTURAL_RES.get(domain, BP_STRUCTURAL_RE)

    for line in dsl_text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Check if this line starts with a known structural keyword
        if struct_re.match(stripped):
            # Remove quoted string content before checking for non-ASCII
            # This preserves structural parts but ignores string literal values
            cleaned = re.sub(r'"[^"]*"', '""', stripped)
            cleaned = re.sub(r"'[^']*'", "''", cleaned)

            # Check remaining text for non-ASCII
            for ch in cleaned:
                if ord(ch) > 127:
                    cat = unicodedata.category(ch)
                    # Allow some punctuation/symbols that might slip through
                    if cat.startswith('L') or cat.startswith('M'):
                        issues.append(f"Non-ASCII letter in keyword line: {stripped[:80]}")
                        break

    return len(issues) > 0, issues


# ── Domain-specific syntax validation ─────────────────────────────────

def validate_blueprint_syntax(dsl_text: str) -> tuple[bool, str]:
    """Validate Blueprint DSL syntax."""
    try:
        from utils.dsl_parser import parse_dsl
        result = parse_dsl(dsl_text)
        if result and hasattr(result, 'name') and result.name:
            return True, "Valid"
        if result:
            return True, "Valid"
        return False, "Parser returned empty result"
    except Exception as e:
        return False, str(e)[:100]


def validate_bt_syntax(dsl_text: str) -> tuple[bool, str]:
    """Validate Behavior Tree DSL syntax."""
    try:
        from bt_parser.bt_parser import parse as parse_bt
        result = parse_bt(dsl_text)
        if not result:
            return False, "Parser returned empty result"
        errors = result.get('errors', [])
        stats = result.get('stats', {})
        if errors:
            return False, f"{len(errors)} errors: {errors[0]}"
        if stats.get('has_root') and stats.get('total_nodes', 0) > 0:
            return True, f"Valid ({stats['total_nodes']} nodes)"
        return False, "No root or zero nodes"
    except Exception as e:
        return False, str(e)[:100]


def validate_dt_syntax(dsl_text: str) -> tuple[bool, str]:
    """Validate DataTable DSL syntax."""
    try:
        from dt_parser.dt_parser import parse as parse_dt
        result = parse_dt(dsl_text)
        if not result:
            return False, "Parser returned empty result"
        errors = result.get('errors', [])
        stats = result.get('stats', {})
        if errors:
            return False, f"{len(errors)} errors: {errors[0]}"
        if stats.get('columns', 0) > 0:
            return True, f"Valid ({stats['columns']} cols, {stats.get('rows', 0)} rows)"
        return False, "No columns found"
    except Exception as e:
        return False, str(e)[:100]


VALIDATORS = {
    "blueprint": validate_blueprint_syntax,
    "behavior_tree": validate_bt_syntax,
    "data_table": validate_dt_syntax,
}


def check_semantic_match(dsl_text: str, expected_keywords: list[str], expected_header: str) -> tuple[bool, str]:
    """Check if the generated DSL contains expected structural keywords."""
    if expected_header not in dsl_text:
        return False, f"Missing header: {expected_header}"

    missing = [kw for kw in expected_keywords if kw not in dsl_text]
    if missing:
        return False, f"Missing keywords: {', '.join(missing)}"

    return True, "Semantic match"


# ── Model loading and generation ──────────────────────────────────────

def load_model_for_domain(domain: str):
    """Load the fine-tuned model for a given domain."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    adapter_path = Path(ADAPTERS[domain])
    if not adapter_path.exists():
        # Try absolute path
        adapter_path = Path("C:/BlueprintLLM") / ADAPTERS[domain]
    if not adapter_path.exists():
        raise FileNotFoundError(f"Adapter not found: {ADAPTERS[domain]}")

    # Load system prompt
    prompt_path = Path("C:/BlueprintLLM") / SYSTEM_PROMPTS[domain]
    if prompt_path.exists():
        system_prompt = prompt_path.read_text(encoding='utf-8').strip()
    else:
        system_prompt = f"You generate {domain} DSL. Output ONLY valid DSL."

    # Append multilingual instruction
    system_prompt += MULTILINGUAL_ADDENDUM

    print(f"  Loading base model: {BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    bnb_config = BitsAndBytesConfig(load_in_8bit=True)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map={"": 0},
        low_cpu_mem_usage=True,
    )

    print(f"  Loading LoRA adapter: {adapter_path}")
    model = PeftModel.from_pretrained(model, str(adapter_path))
    model.eval()

    return model, tokenizer, system_prompt


def generate_dsl(model, tokenizer, system_prompt: str, user_prompt: str,
                 domain: str, max_tokens: int = 1024, temperature: float = 0.1) -> str:
    """Generate DSL from a prompt using the fine-tuned model."""
    import torch

    formatted = (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{system_prompt}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{user_prompt}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )

    inputs = tokenizer(formatted, return_tensors="pt").to(model.device)
    prompt_len = inputs["input_ids"].shape[1]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated = tokenizer.decode(outputs[0][prompt_len:], skip_special_tokens=True)

    # Clean up: strip trailing delimiter hallucinations (Lesson #25)
    lines = generated.strip().split('\n')
    if lines:
        lines[-1] = re.sub(r'\s*[{}\(\);>]+\s*$', '', lines[-1])

    # Remove anything after a blank line following complete DSL
    cleaned_lines = []
    blank_count = 0
    for line in lines:
        if line.strip() == '':
            blank_count += 1
            if blank_count >= 2 and len(cleaned_lines) > 3:
                break
            cleaned_lines.append(line)
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines).strip()


# ── Main test runner ──────────────────────────────────────────────────

def run_tests(args):
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"

    project_root = Path("C:/BlueprintLLM")
    os.chdir(project_root)

    # Load test suite
    suite_path = project_root / TEST_SUITE
    if not suite_path.exists():
        print(f"ERROR: Test suite not found: {suite_path}")
        sys.exit(1)

    with open(suite_path, encoding='utf-8') as f:
        suite = json.load(f)

    languages = suite["languages"]
    if args.languages:
        lang_filter = set(args.languages.split(','))
        languages = {k: v for k, v in languages.items() if k in lang_filter}

    # Determine which domains to test
    domains_to_test = []
    if args.domain:
        domains_to_test = [args.domain]
    else:
        domains_to_test = ["blueprint", "behavior_tree", "data_table"]

    # Verify adapters exist
    for domain in domains_to_test:
        adapter_path = project_root / ADAPTERS[domain]
        if not adapter_path.exists():
            print(f"WARNING: Adapter not found for {domain}: {adapter_path}")
            print(f"  Skipping {domain}")
            domains_to_test.remove(domain)

    if not domains_to_test:
        print("ERROR: No valid adapters found. Exiting.")
        sys.exit(1)

    # Results storage
    results = {
        "timestamp": datetime.now().isoformat(),
        "base_model": BASE_MODEL,
        "adapters": {d: ADAPTERS[d] for d in domains_to_test},
        "multilingual_addendum": True,
        "languages_tested": list(languages.keys()),
        "domains_tested": domains_to_test,
        "results": {},
        "matrix": {},
    }

    total_tests = 0
    total_pass = 0

    for domain in domains_to_test:
        print(f"\n{'='*60}")
        print(f"  DOMAIN: {domain.upper()}")
        print(f"{'='*60}")

        # Load model once per domain
        print(f"\n  Loading model for {domain}...")
        t0 = time.time()
        model, tokenizer, system_prompt = load_model_for_domain(domain)
        load_time = time.time() - t0
        print(f"  Model loaded in {load_time:.1f}s")

        domain_results = []
        test_cases = suite["tests"].get(domain, [])

        for test in test_cases:
            test_id = test["id"]
            expected_keywords = test.get("expected_keywords", [])
            expected_header = test.get("expected_header", "")

            for lang_code, lang_name in languages.items():
                prompts = test.get("prompts", {})
                if lang_code not in prompts:
                    continue

                prompt = prompts[lang_code]
                total_tests += 1

                print(f"\n  [{test_id}] {lang_code} ({lang_name})...")
                print(f"    Prompt: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")

                t1 = time.time()
                try:
                    dsl_output = generate_dsl(model, tokenizer, system_prompt, prompt, domain)
                    gen_time = time.time() - t1
                except Exception as e:
                    gen_time = time.time() - t1
                    entry = {
                        "test_id": test_id,
                        "language": lang_code,
                        "language_name": lang_name,
                        "prompt": prompt,
                        "output": "",
                        "gen_time_s": gen_time,
                        "syntax_valid": False,
                        "syntax_error": f"Generation error: {str(e)[:100]}",
                        "semantic_match": False,
                        "semantic_error": "N/A (generation failed)",
                        "no_leakage": False,
                        "leakage_issues": ["Generation failed"],
                        "pass": False,
                    }
                    domain_results.append(entry)
                    print(f"    FAIL: Generation error ({gen_time:.1f}s)")
                    continue

                # Print first few lines of output
                preview = dsl_output[:150].replace('\n', ' | ')
                print(f"    Output: {preview}...")
                print(f"    Generated in {gen_time:.1f}s")

                # 1. Syntax validation
                validator = VALIDATORS.get(domain, validate_blueprint_syntax)
                syntax_valid, syntax_msg = validator(dsl_output)
                print(f"    Syntax: {'PASS' if syntax_valid else 'FAIL'} — {syntax_msg}")

                # 2. Semantic match (expected keywords present)
                sem_match, sem_msg = check_semantic_match(dsl_output, expected_keywords, expected_header)
                print(f"    Semantic: {'PASS' if sem_match else 'FAIL'} — {sem_msg}")

                # 3. Non-ASCII leakage check
                has_leak, leak_issues = has_nonascii_leakage(dsl_output, domain)
                no_leak = not has_leak
                print(f"    Leakage: {'PASS (clean)' if no_leak else 'FAIL — ' + '; '.join(leak_issues[:2])}")

                # Overall pass: syntax valid AND no leakage
                # Semantic match is informational (soft check)
                passed = syntax_valid and no_leak
                if passed:
                    total_pass += 1

                status = "PASS" if passed else "FAIL"
                print(f"    Result: {status}")

                entry = {
                    "test_id": test_id,
                    "language": lang_code,
                    "language_name": lang_name,
                    "prompt": prompt,
                    "output": dsl_output,
                    "gen_time_s": round(gen_time, 1),
                    "syntax_valid": syntax_valid,
                    "syntax_error": syntax_msg if not syntax_valid else None,
                    "semantic_match": sem_match,
                    "semantic_error": sem_msg if not sem_match else None,
                    "no_leakage": no_leak,
                    "leakage_issues": leak_issues if has_leak else [],
                    "pass": passed,
                }
                domain_results.append(entry)

        results["results"][domain] = domain_results

        # Free GPU memory before loading next model
        import torch
        del model
        del tokenizer
        torch.cuda.empty_cache()
        import gc
        gc.collect()
        print(f"\n  GPU memory freed for {domain}")

    # ── Build language x domain matrix ────────────────────────────────
    print(f"\n\n{'='*70}")
    print("  MULTILINGUAL TEST RESULTS — LANGUAGE x DOMAIN MATRIX")
    print(f"{'='*70}")

    matrix = {}
    for domain in domains_to_test:
        for entry in results["results"].get(domain, []):
            lang = entry["language"]
            if lang not in matrix:
                matrix[lang] = {}
            if domain not in matrix[lang]:
                matrix[lang][domain] = {"total": 0, "syntax_pass": 0, "semantic_pass": 0, "no_leak": 0, "full_pass": 0}
            m = matrix[lang][domain]
            m["total"] += 1
            if entry["syntax_valid"]:
                m["syntax_pass"] += 1
            if entry["semantic_match"]:
                m["semantic_pass"] += 1
            if entry["no_leakage"]:
                m["no_leak"] += 1
            if entry["pass"]:
                m["full_pass"] += 1

    results["matrix"] = matrix

    # Print matrix
    domain_abbrevs = {"blueprint": "BP", "behavior_tree": "BT", "data_table": "DT"}
    header_cols = [domain_abbrevs.get(d, d[:4]) for d in domains_to_test]

    # Header
    print(f"\n  {'Lang':<8}", end="")
    for col in header_cols:
        print(f"  {col:>10}", end="")
    print(f"  {'Overall':>10}")
    print(f"  {'----':<8}", end="")
    for _ in header_cols:
        print(f"  {'----------':>10}", end="")
    print(f"  {'----------':>10}")

    # Rows
    sorted_langs = sorted(matrix.keys(), key=lambda x: (x != 'en', x))
    for lang in sorted_langs:
        lang_label = f"{lang}"
        print(f"  {lang_label:<8}", end="")
        lang_total = 0
        lang_pass = 0
        for domain in domains_to_test:
            m = matrix.get(lang, {}).get(domain, {"total": 0, "full_pass": 0})
            lang_total += m["total"]
            lang_pass += m["full_pass"]
            if m["total"] == 0:
                cell = "—"
            else:
                pct = m["full_pass"] / m["total"] * 100
                cell = f"{m['full_pass']}/{m['total']} ({pct:.0f}%)"
            print(f"  {cell:>10}", end="")

        # Overall for this language
        if lang_total > 0:
            overall_pct = lang_pass / lang_total * 100
            overall = f"{lang_pass}/{lang_total} ({overall_pct:.0f}%)"
        else:
            overall = "—"
        print(f"  {overall:>10}")

    # Totals row
    print(f"  {'----':<8}", end="")
    for _ in header_cols:
        print(f"  {'----------':>10}", end="")
    print(f"  {'----------':>10}")

    print(f"  {'TOTAL':<8}", end="")
    grand_total = 0
    grand_pass = 0
    for domain in domains_to_test:
        d_total = sum(matrix.get(l, {}).get(domain, {}).get("total", 0) for l in matrix)
        d_pass = sum(matrix.get(l, {}).get(domain, {}).get("full_pass", 0) for l in matrix)
        grand_total += d_total
        grand_pass += d_pass
        if d_total > 0:
            pct = d_pass / d_total * 100
            cell = f"{d_pass}/{d_total} ({pct:.0f}%)"
        else:
            cell = "—"
        print(f"  {cell:>10}", end="")
    if grand_total > 0:
        pct = grand_pass / grand_total * 100
        print(f"  {grand_pass}/{grand_total} ({pct:.0f}%)")
    else:
        print(f"  {'—':>10}")

    # ── Detailed breakdown ────────────────────────────────────────────
    print(f"\n\n  Detailed Breakdown:")
    print(f"  {'Test ID':<25} {'Lang':<6} {'Syntax':<8} {'Semantic':<10} {'Leakage':<10} {'Result':<8}")
    print(f"  {'-'*25} {'-'*6} {'-'*8} {'-'*10} {'-'*10} {'-'*8}")
    for domain in domains_to_test:
        for entry in results["results"].get(domain, []):
            syn = "PASS" if entry["syntax_valid"] else "FAIL"
            sem = "PASS" if entry["semantic_match"] else "FAIL"
            leak = "CLEAN" if entry["no_leakage"] else "LEAK"
            overall = "PASS" if entry["pass"] else "FAIL"
            print(f"  {entry['test_id']:<25} {entry['language']:<6} {syn:<8} {sem:<10} {leak:<10} {overall:<8}")

    # ── Summary ───────────────────────────────────────────────────────
    print(f"\n  SUMMARY: {total_pass}/{total_tests} tests passed ({total_pass/max(total_tests,1)*100:.1f}%)")
    print(f"  Domains: {', '.join(domains_to_test)}")
    print(f"  Languages: {', '.join(sorted(languages.keys()))}")

    # ── Save results ──────────────────────────────────────────────────
    results_dir = project_root / RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = results_dir / f"multilingual_{timestamp}.json"

    # Don't save the full DSL output to keep file manageable
    save_results = json.loads(json.dumps(results, default=str))
    for domain in save_results.get("results", {}):
        for entry in save_results["results"][domain]:
            if len(entry.get("output", "")) > 500:
                entry["output_preview"] = entry["output"][:500] + "..."
                entry["output_length"] = len(entry["output"])
                del entry["output"]

    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(save_results, f, indent=2, ensure_ascii=False)

    print(f"\n  Results saved to: {results_path}")
    return total_pass == total_tests


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multilingual DSL generation test")
    parser.add_argument("--domain", choices=["blueprint", "behavior_tree", "data_table"],
                        help="Test a single domain (default: all)")
    parser.add_argument("--languages", type=str, default=None,
                        help="Comma-separated language codes to test (default: all)")
    args = parser.parse_args()

    success = run_tests(args)
    sys.exit(0 if success else 1)
