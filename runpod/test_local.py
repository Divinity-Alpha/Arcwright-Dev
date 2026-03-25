#!/usr/bin/env python3
"""
Arcwright — Local Handler Test
Simulates RunPod requests locally. Tests all three domains.

Usage:
    python test_local.py                          # Quick mock test (no GPU)
    python test_local.py --live                   # Live test with GPU inference
    python test_local.py --live --domain blueprint # Test specific domain
    python test_local.py --live --prompt "..."    # Custom prompt
"""

import json
import sys
import time
import argparse
from unittest.mock import MagicMock

# Mock runpod before importing handler — runpod isn't installed locally
# and mock tests only need format_prompt, clean_output, input validation
sys.modules['runpod'] = MagicMock()

# ─── Test Prompts ─────────────────────────────────────────────────────────────

TEST_PROMPTS = {
    "blueprint": "Create a health pickup that restores 25 HP when the player overlaps it, then destroys itself.",
    "bt": "Create a patrol AI that walks between two points. When it sees a player within 800 units, chase them. Resume patrol when player escapes.",
    "dt": "Create a weapons data table with columns for weapon name (string), damage (float), fire rate (float), and ammo count (int). Include a pistol, shotgun, and rifle.",
}

# Expected DSL markers per domain
EXPECTED_MARKERS = {
    "blueprint": "BLUEPRINT:",
    "bt": "BEHAVIORTREE:",
    "dt": "DATATABLE:",
}


# ─── Mock Tests (no GPU) ─────────────────────────────────────────────────────


def test_mock_all():
    """Test input validation, prompt formatting, and output cleaning without GPU."""
    print("=" * 60)
    print("  MOCK TESTS (no GPU required)")
    print("=" * 60)

    from handler import format_prompt, clean_output, _load_system_prompts, _system_prompts

    # Load system prompts
    _load_system_prompts()

    passed = 0
    failed = 0

    # Test 1: System prompts loaded
    for domain in ["blueprint", "bt", "dt"]:
        if domain in _system_prompts and len(_system_prompts[domain]) > 50:
            print(f"  [PASS] System prompt loaded: {domain} ({len(_system_prompts[domain])} chars)")
            passed += 1
        else:
            print(f"  [FAIL] System prompt missing or too short: {domain}")
            failed += 1

    # Test 2: Prompt formatting
    for domain in ["blueprint", "bt", "dt"]:
        formatted = format_prompt(domain, TEST_PROMPTS[domain])
        checks = [
            formatted.startswith("<|begin_of_text|>"),
            "<|start_header_id|>system<|end_header_id|>" in formatted,
            "<|start_header_id|>user<|end_header_id|>" in formatted,
            "<|start_header_id|>assistant<|end_header_id|>" in formatted,
            TEST_PROMPTS[domain] in formatted,
        ]
        if all(checks):
            print(f"  [PASS] Prompt formatting: {domain} ({len(formatted)} chars)")
            passed += 1
        else:
            print(f"  [FAIL] Prompt formatting: {domain} — missing template markers")
            failed += 1

    # Test 3: Output cleaning — trailing delimiters
    dirty_outputs = {
        "blueprint": 'BLUEPRINT: BP_Test\nPARENT: Actor\n\nNODE n1: DestroyActor }',
        "bt": 'BEHAVIORTREE: BT_Test\nBLACKBOARD: BB_Test\n\nTREE:\n\nSEQUENCE: Root\n  TASK: Wait [Duration=3.0] }',
        "dt": 'DATATABLE: DT_Test\nSTRUCT: FData\n\nCOLUMN Name: String\n\nROW A: "Alpha" );',
    }

    for domain, dirty in dirty_outputs.items():
        cleaned = clean_output(domain, dirty)
        has_trailing = any(cleaned.endswith(c) for c in ["}", ")", ";", ">"])
        if not has_trailing:
            print(f"  [PASS] Trailing delimiter cleanup: {domain}")
            passed += 1
        else:
            print(f"  [FAIL] Trailing delimiter NOT cleaned: {domain} — ends with '{cleaned[-1]}'")
            failed += 1

    # Test 4: Output cleaning — preamble removal
    preamble_output = 'Here is the Blueprint DSL:\n\nBLUEPRINT: BP_Test\nPARENT: Actor'
    cleaned = clean_output("blueprint", preamble_output)
    if cleaned.startswith("BLUEPRINT:"):
        print(f"  [PASS] Preamble removal: blueprint")
        passed += 1
    else:
        print(f"  [FAIL] Preamble NOT removed — starts with: {cleaned[:30]}")
        failed += 1

    # Test 5: Output cleaning — code fence removal
    fenced_output = '```dsl\nBLUEPRINT: BP_Test\nPARENT: Actor\n```'
    cleaned = clean_output("blueprint", fenced_output)
    if "```" not in cleaned and cleaned.startswith("BLUEPRINT:"):
        print(f"  [PASS] Code fence removal")
        passed += 1
    else:
        print(f"  [FAIL] Code fences NOT removed")
        failed += 1

    # Test 6: Handler input validation (no model needed)
    from handler import handler

    error_cases = [
        ({}, "Missing 'domain'"),
        ({"input": {"domain": "blueprint"}}, "Missing 'prompt'"),
        ({"input": {"domain": "invalid", "prompt": "test"}}, "Invalid domain"),
        ({"input": {"domain": "blueprint", "prompt": "x" * 10001}}, "Prompt too long"),
    ]

    for job, description in error_cases:
        result = handler(job)
        if "error" in result:
            print(f"  [PASS] Input validation: {description}")
            passed += 1
        else:
            print(f"  [FAIL] Input validation: {description} — no error returned")
            failed += 1

    # Test 7: Domain aliases
    from handler import DOMAIN_ALIASES
    alias_tests = [("datatable", "dt"), ("behavior_tree", "bt"), ("behaviortree", "bt")]
    for alias, expected in alias_tests:
        resolved = DOMAIN_ALIASES.get(alias, alias)
        if resolved == expected:
            print(f"  [PASS] Domain alias: {alias} -> {resolved}")
            passed += 1
        else:
            print(f"  [FAIL] Domain alias: {alias} -> {resolved} (expected {expected})")
            failed += 1

    print()
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


# ─── Live Tests (GPU required) ───────────────────────────────────────────────


def test_live(domain: str, prompt: str) -> bool:
    """Test with actual GPU inference."""
    print()
    print("=" * 60)
    print(f"  LIVE TEST: {domain}")
    print("=" * 60)

    from handler import handler, load_model, _load_system_prompts
    import handler as h

    # Load prompts if not already
    _load_system_prompts()

    # Load model if not already
    if h.llm is None:
        print("  Loading model (this takes 2-3 minutes)...")
        load_model()

    job = {
        "id": f"test_{domain}_{int(time.time())}",
        "input": {
            "domain": domain,
            "prompt": prompt,
            "temperature": 0.1,
            "max_tokens": 1024,
        },
    }

    print(f"  Generating {domain} DSL...")
    start = time.time()
    result = handler(job)
    elapsed = time.time() - start

    if "error" in result:
        print(f"  FAIL: {result['error']}")
        return False

    output = result.get("output", result)  # Handle both wrapped and unwrapped
    dsl = output.get("dsl", "")
    tokens = output.get("tokens_generated", 0)
    gen_time = output.get("generation_time_ms", int(elapsed * 1000))

    print(f"  Domain:    {output.get('domain', domain)}")
    print(f"  Tokens:    {tokens}")
    print(f"  Latency:   {gen_time}ms")
    print(f"  DSL lines: {dsl.count(chr(10)) + 1}")

    # Check DSL starts with expected marker
    marker = EXPECTED_MARKERS.get(domain, "")
    starts_ok = dsl.startswith(marker) if marker else True
    print(f"  Starts with {marker}: {'PASS' if starts_ok else 'FAIL'}")

    # Check no trailing delimiters
    last_line = dsl.strip().split("\n")[-1] if dsl.strip() else ""
    trailing_ok = not any(last_line.endswith(c) for c in ["}", ")", ";", ">"])
    print(f"  No trailing delimiters: {'PASS' if trailing_ok else 'FAIL'}")

    # Print first 15 lines
    print()
    print("  DSL Output:")
    lines = dsl.split("\n")
    for line in lines[:15]:
        print(f"    {line}")
    if len(lines) > 15:
        print(f"    ... ({len(lines) - 15} more lines)")

    ok = starts_ok and trailing_ok
    print(f"\n  {'PASS' if ok else 'FAIL'}")
    return ok


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(description="Arcwright Local Handler Test")
    ap.add_argument("--live", action="store_true", help="Run live GPU tests (requires GPU + model)")
    ap.add_argument("--domain", choices=["blueprint", "bt", "dt"], help="Test specific domain")
    ap.add_argument("--prompt", help="Custom prompt (used with --live)")
    args = ap.parse_args()

    if not args.live:
        ok = test_mock_all()
        sys.exit(0 if ok else 1)

    # Live mode
    domains = [args.domain] if args.domain else ["blueprint", "bt", "dt"]
    results = {}
    for d in domains:
        prompt = args.prompt or TEST_PROMPTS[d]
        results[d] = test_live(d, prompt)

    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    for d, passed in results.items():
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {d}")

    all_pass = all(results.values())
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
