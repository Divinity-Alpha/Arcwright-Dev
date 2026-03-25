#!/usr/bin/env python3
"""
BlueprintLLM — Universal Compliance Checker
Validates DSL across all domains: Blueprint, Behavior Tree, Data Table.
Auto-detects domain from content or accepts explicit --domain flag.

Usage:
    python universal_compliance.py input.dsl                  # Auto-detect domain
    python universal_compliance.py input.dsl --domain bt      # Explicit domain
    python universal_compliance.py --text "DATATABLE: ..."    # Inline text
    python universal_compliance.py --batch folder/            # Check all files
    python universal_compliance.py input.dsl --json           # Machine-readable
"""

import sys
import os
import json
import argparse
from pathlib import Path

_script_dir = os.path.dirname(os.path.abspath(__file__))

# Add parser directories
for d in ["dsl_parser", "bt_parser", "dt_parser",
          os.path.join("scripts", "dsl_parser"),
          os.path.join("scripts", "bt_parser"),
          os.path.join("scripts", "dt_parser")]:
    full = os.path.join(_script_dir, d)
    if os.path.isdir(full) and full not in sys.path:
        sys.path.insert(0, full)


def detect_domain(text: str) -> str:
    """Auto-detect DSL domain from content."""
    stripped = text.strip()
    if stripped.startswith("BEHAVIORTREE:"):
        return "bt"
    if stripped.startswith("DATATABLE:"):
        return "dt"
    if stripped.startswith("BLUEPRINT:"):
        return "blueprint"
    
    # Heuristic fallbacks
    if "SELECTOR:" in text or "SEQUENCE:" in text and "TASK:" in text:
        return "bt"
    if "COLUMN " in text and "ROW " in text:
        return "dt"
    if "NODE " in text and "EXEC " in text:
        return "blueprint"
    
    return "unknown"


def check_blueprint(text: str) -> dict:
    """Run Blueprint compliance checks."""
    try:
        from parser import parse
        result = parse(text)
        
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        stats = result.get("stats", {})
        
        nodes = stats.get("nodes", 0)
        mapped = stats.get("mapped", 0)
        
        syntax_score = 100.0 if not errors else max(0, 100 - len(errors) * 20)
        mapping_score = (mapped / nodes * 100) if nodes > 0 else 0
        
        return {
            "domain": "blueprint",
            "valid": len(errors) == 0,
            "syntax_score": syntax_score,
            "mapping_score": round(mapping_score, 1),
            "overall_score": round((syntax_score + mapping_score) / 2, 1),
            "nodes": nodes,
            "connections": stats.get("connections", 0),
            "errors": errors,
            "warnings": warnings,
        }
    except ImportError:
        return {"domain": "blueprint", "valid": False, "errors": ["Blueprint parser not available"]}


def check_bt(text: str) -> dict:
    """Run Behavior Tree compliance checks."""
    try:
        from bt_parser import parse
        result = parse(text)
        
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        stats = result.get("stats", {})
        
        total = stats.get("total_nodes", 0)
        mapped = stats.get("mapped", 0)
        
        syntax_score = 100.0 if not errors else max(0, 100 - len(errors) * 20)
        mapping_score = (mapped / total * 100) if total > 0 else 0
        
        return {
            "domain": "behavior_tree",
            "valid": len(errors) == 0,
            "syntax_score": syntax_score,
            "mapping_score": round(mapping_score, 1),
            "overall_score": round((syntax_score + mapping_score) / 2, 1),
            "nodes": total,
            "composites": stats.get("composites", 0),
            "tasks": stats.get("tasks", 0),
            "decorators": stats.get("decorators", 0),
            "services": stats.get("services", 0),
            "blackboard_keys": stats.get("blackboard_keys", 0),
            "errors": errors,
            "warnings": warnings,
        }
    except ImportError:
        return {"domain": "behavior_tree", "valid": False, "errors": ["BT parser not available"]}


def check_dt(text: str) -> dict:
    """Run Data Table compliance checks."""
    try:
        from dt_parser import parse
        result = parse(text)
        
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        stats = result.get("stats", {})
        
        syntax_score = 100.0 if not errors else max(0, 100 - len(errors) * 20)
        
        return {
            "domain": "data_table",
            "valid": len(errors) == 0,
            "syntax_score": syntax_score,
            "mapping_score": 100.0,  # DT doesn't have node mapping
            "overall_score": syntax_score,
            "columns": stats.get("columns", 0),
            "rows": stats.get("rows", 0),
            "column_types": stats.get("column_types", []),
            "errors": errors,
            "warnings": warnings,
        }
    except ImportError:
        return {"domain": "data_table", "valid": False, "errors": ["DT parser not available"]}


def check(text: str, domain: str = None) -> dict:
    """Check DSL text against appropriate domain validator."""
    if not domain:
        domain = detect_domain(text)
    
    checkers = {
        "blueprint": check_blueprint,
        "bp": check_blueprint,
        "bt": check_bt,
        "behavior_tree": check_bt,
        "dt": check_dt,
        "data_table": check_dt,
    }
    
    checker = checkers.get(domain)
    if not checker:
        return {"domain": "unknown", "valid": False, "errors": [f"Unknown domain: {domain}. Use: blueprint, bt, or dt"]}
    
    return checker(text)


def format_report(result: dict) -> str:
    """Format as human-readable text."""
    lines = []
    domain_names = {"blueprint": "Blueprint", "behavior_tree": "Behavior Tree", "data_table": "Data Table"}
    domain = domain_names.get(result["domain"], result["domain"])
    
    lines.append(f"\n{'='*50}")
    lines.append(f"  {domain} Compliance Check")
    lines.append(f"{'='*50}")
    
    valid_icon = "✅" if result["valid"] else "❌"
    lines.append(f"  {valid_icon} Valid: {result['valid']}")
    lines.append(f"  Overall Score: {result.get('overall_score', 0)}%")
    
    # Domain-specific stats
    if result["domain"] == "blueprint":
        lines.append(f"  Nodes: {result.get('nodes', 0)}  Connections: {result.get('connections', 0)}")
    elif result["domain"] == "behavior_tree":
        lines.append(f"  Nodes: {result.get('nodes', 0)} (C={result.get('composites',0)} T={result.get('tasks',0)} D={result.get('decorators',0)} S={result.get('services',0)})")
        lines.append(f"  Blackboard Keys: {result.get('blackboard_keys', 0)}")
    elif result["domain"] == "data_table":
        lines.append(f"  Columns: {result.get('columns', 0)}  Rows: {result.get('rows', 0)}")
        lines.append(f"  Types: {', '.join(result.get('column_types', []))}")
    
    if result.get("errors"):
        lines.append(f"\n  Errors ({len(result['errors'])}):")
        for e in result["errors"]:
            lines.append(f"    ❌ {e}")
    
    if result.get("warnings"):
        lines.append(f"\n  Warnings ({len(result['warnings'])}):")
        for w in result["warnings"]:
            lines.append(f"    ⚠️ {w}")
    
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="BlueprintLLM Universal Compliance Checker")
    ap.add_argument("input", nargs="?", help="DSL file to check")
    ap.add_argument("--text", help="DSL text to check")
    ap.add_argument("--domain", choices=["blueprint", "bp", "bt", "dt"], help="Force domain (auto-detected if not set)")
    ap.add_argument("--batch", help="Check all files in directory")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()
    
    if args.batch:
        results = []
        batch_dir = Path(args.batch)
        files = sorted(batch_dir.glob("*"))
        files = [f for f in files if f.suffix in ('.dsl', '.bt', '.dt', '.txt')]
        
        for f in files:
            text = f.read_text(encoding="utf-8")
            result = check(text, args.domain)
            result["file"] = str(f)
            results.append(result)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\nBatch Results ({len(files)} files)")
            for r in results:
                icon = "✅" if r["valid"] else "❌"
                print(f"  {icon} {Path(r['file']).name:<30} {r['domain']:<15} {r.get('overall_score', 0):>5.1f}%")
            
            valid = sum(1 for r in results if r["valid"])
            print(f"\n  {valid}/{len(results)} valid")
        return
    
    if args.text:
        text = args.text.replace("\\n", "\n")
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        ap.print_help()
        return
    
    result = check(text, args.domain)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))


if __name__ == "__main__":
    main()
