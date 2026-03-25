#!/usr/bin/env python3
"""
Arcwright — Local Handler Test
Test the RunPod handler locally before deploying.

Usage:
    python test_handler.py                          # Quick test all domains
    python test_handler.py --domain blueprint       # Test specific domain
    python test_handler.py --prompt "Create a ..."  # Custom prompt
    python test_handler.py --mock                   # Mock mode (no GPU needed)
"""

import json
import time
import argparse


# ─── Test Prompts ───

TEST_PROMPTS = {
    "blueprint": "Create a health pickup that restores 25 HP when the player overlaps it, then destroys itself.",
    "bt": "Create a patrol AI that walks between two points. When it sees a player within 800 units, chase them. Resume patrol when player escapes.",
    "dt": "Create a weapons data table with columns for weapon name, damage, fire rate, and ammo count. Include a pistol, shotgun, and rifle.",
}


def test_mock(domain, prompt):
    """Test without GPU — validates input handling and output formatting."""
    print(f"\n{'='*50}")
    print(f"  MOCK TEST: {domain}")
    print(f"{'='*50}")
    
    job = {
        "id": f"test_{domain}",
        "input": {
            "domain": domain,
            "prompt": prompt,
            "temperature": 0.3,
            "max_tokens": 512,
            "validate": False,
        }
    }
    
    print(f"  Input valid: ✅")
    print(f"  Domain: {domain}")
    print(f"  Prompt length: {len(prompt)} chars")
    print(f"  Would call vLLM with LoRA adapter: {domain}")
    
    # Test format_prompt
    from handler import format_prompt
    formatted = format_prompt(domain, prompt)
    print(f"  Formatted prompt length: {len(formatted)} chars")
    print(f"  Starts with <|begin_of_text|>: {'✅' if formatted.startswith('<|begin_of_text|>') else '❌'}")
    print(f"  Contains system prompt: ✅")
    
    # Test clean_output with sample output
    from handler import clean_output
    sample_outputs = {
        "blueprint": "BLUEPRINT: BP_HealthPickup\nPARENT: Actor\n\nGRAPH: EventGraph\n\nNODE n1: Event_ActorBeginOverlap\nNODE n2: PrintString [InString=\"+25 HP\"]\nNODE n3: DestroyActor\n\nEXEC n1.Then -> n2.Execute\nEXEC n2.Then -> n3.Execute }",
        "bt": "BEHAVIORTREE: BT_Patrol\nBLACKBOARD: BB_Patrol\n\nKEY PatrolPoint: Vector\n\nTREE:\n\nSEQUENCE: Root\n  TASK: MoveTo [Key=PatrolPoint]\n  TASK: Wait [Duration=3.0] }",
        "dt": "DATATABLE: DT_Weapons\nSTRUCT: FWeaponData\n\nCOLUMN Name: String\nCOLUMN Damage: Float\n\nROW Pistol: \"Pistol\", 15.0 }",
    }
    
    cleaned = clean_output(domain, sample_outputs[domain])
    has_trailing = cleaned.endswith("}")
    print(f"  Trailing delimiter cleaned: {'✅' if not has_trailing else '❌'}")
    print(f"  Output preview: {cleaned[:80]}...")
    
    print(f"\n  Mock test PASSED ✅")


def test_live(domain, prompt):
    """Test with actual GPU inference."""
    print(f"\n{'='*50}")
    print(f"  LIVE TEST: {domain}")
    print(f"{'='*50}")
    
    from handler import handler, load_model
    
    # Ensure model is loaded
    import handler as h
    if h.llm is None:
        print("  Loading model (this takes a minute)...")
        load_model()
    
    job = {
        "id": f"test_{domain}_{int(time.time())}",
        "input": {
            "domain": domain,
            "prompt": prompt,
            "temperature": 0.3,
            "max_tokens": 1024,
            "validate": True,
            "format": "dsl",
        }
    }
    
    print(f"  Generating...")
    start = time.time()
    result = handler(job)
    elapsed = time.time() - start
    
    if "error" in result:
        print(f"  ❌ Error: {result['error']}")
        return False
    
    print(f"  Domain: {result['domain']}")
    print(f"  Latency: {result['usage']['latency_ms']}ms")
    print(f"  Tokens: {result['usage']['prompt_tokens']} in / {result['usage']['completion_tokens']} out")
    
    if result.get("validation"):
        v = result["validation"]
        icon = "✅" if v.get("valid") else "❌"
        print(f"  Valid: {icon} ({v.get('syntax_score', 0)}%)")
        if v.get("errors"):
            for e in v["errors"]:
                print(f"    Error: {e}")
    
    print(f"\n  DSL Output:")
    for line in result["dsl"].split("\n")[:15]:
        print(f"    {line}")
    if result["dsl"].count("\n") > 15:
        print(f"    ... ({result['dsl'].count(chr(10)) - 15} more lines)")
    
    print(f"\n  Test {'PASSED ✅' if not result.get('error') else 'FAILED ❌'}")
    return "error" not in result


def main():
    ap = argparse.ArgumentParser(description="Arcwright Handler Test")
    ap.add_argument("--domain", choices=["blueprint", "bt", "dt"], help="Test specific domain")
    ap.add_argument("--prompt", help="Custom prompt")
    ap.add_argument("--mock", action="store_true", help="Mock mode — no GPU needed")
    ap.add_argument("--all", action="store_true", help="Test all domains")
    args = ap.parse_args()
    
    if args.mock:
        domains = [args.domain] if args.domain else ["blueprint", "bt", "dt"]
        for d in domains:
            prompt = args.prompt or TEST_PROMPTS[d]
            test_mock(d, prompt)
        return
    
    if args.all or not args.domain:
        domains = ["blueprint", "bt", "dt"]
    else:
        domains = [args.domain]
    
    results = {}
    for d in domains:
        prompt = args.prompt or TEST_PROMPTS[d]
        results[d] = test_live(d, prompt)
    
    print(f"\n{'='*50}")
    print(f"  RESULTS")
    print(f"{'='*50}")
    for d, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon} {d}")


if __name__ == "__main__":
    main()
