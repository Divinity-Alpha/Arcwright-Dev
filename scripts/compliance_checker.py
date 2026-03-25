#!/usr/bin/env python3
"""
BlueprintLLM DSL Compliance Checker
Validates DSL text against the BlueprintLLM spec and produces a scored report.

Usage:
    python compliance_checker.py input.dsl
    python compliance_checker.py --text "BLUEPRINT: BP_Test\n..."
    python compliance_checker.py --batch folder_of_dsl_files/
    echo "BLUEPRINT: ..." | python compliance_checker.py --stdin
    python compliance_checker.py input.dsl --json          # Machine-readable output
    python compliance_checker.py input.dsl --compare expected.dsl  # Similarity scoring

Phase 4: DSL Open Standard & Compliance Checker
"""

import sys
import os
import json
import re
import argparse
from pathlib import Path

# Add parser dirs so we can import
_script_dir = os.path.dirname(os.path.abspath(__file__))
_parser_dirs = [
    os.path.join(_script_dir, "dsl_parser"),
    os.path.join(_script_dir, "..", "dsl_parser"),
    os.path.join(_script_dir, "..", "scripts", "dsl_parser"),
]
for d in _parser_dirs:
    if os.path.isdir(d) and d not in sys.path:
        sys.path.insert(0, d)

from parser import parse, clean_dsl
from node_map import resolve, NODE_MAP, ALIASES


# ─── Compliance Dimensions ──────────────────────────────────────────────────

def check_syntax(dsl_text: str) -> dict:
    """Check basic DSL syntax validity."""
    lines = clean_dsl(dsl_text)
    issues = []
    
    has_blueprint = False
    has_parent = False
    has_graph = False
    has_nodes = False
    has_events = False
    node_ids = []
    
    for i, line in enumerate(lines):
        if line.startswith("BLUEPRINT:"):
            has_blueprint = True
            name = line.split(":", 1)[1].strip()
            if not name:
                issues.append({"line": i+1, "severity": "error", "message": "BLUEPRINT name is empty"})
            elif not re.match(r'^BP_\w+$', name):
                issues.append({"line": i+1, "severity": "warning", "message": f"Blueprint name '{name}' should start with BP_ prefix"})
        
        elif line.startswith("PARENT:"):
            has_parent = True
            parent = line.split(":", 1)[1].strip()
            if not parent:
                issues.append({"line": i+1, "severity": "error", "message": "PARENT class is empty"})
        
        elif line.startswith("GRAPH:"):
            has_graph = True
        
        elif line.startswith("NODE "):
            has_nodes = True
            m = re.match(r'NODE\s+(n\d+)\s*:\s*(\S+)', line)
            if m:
                nid = m.group(1)
                if nid in node_ids:
                    issues.append({"line": i+1, "severity": "error", "message": f"Duplicate node ID: {nid}"})
                node_ids.append(nid)
                
                ntype = m.group(2)
                if ntype.startswith("Event_") or ntype in ("Event_CustomEvent",):
                    has_events = True
            else:
                issues.append({"line": i+1, "severity": "error", "message": f"Invalid NODE syntax: {line[:60]}"})
        
        elif line.startswith("EXEC "):
            m = re.match(r'EXEC\s+(n\d+)\.(\S+)\s*->\s*(n\d+)\.(\S+)', line)
            if not m:
                issues.append({"line": i+1, "severity": "error", "message": f"Invalid EXEC syntax: {line[:60]}"})
        
        elif line.startswith("DATA "):
            # Node-to-node data
            m = re.match(r'DATA\s+(n\d+)\.(\S+)\s*->\s*(n\d+)\.(\S+?)(?:\s*\[(\w+)\])?\s*', line)
            if not m:
                # Literal data
                m2 = re.match(r'DATA\s+(\S+)\s*->\s*(n\d+)\.(\S+?)(?:\s*\[(\w+)\])?\s*', line)
                if not m2:
                    issues.append({"line": i+1, "severity": "error", "message": f"Invalid DATA syntax: {line[:60]}"})
                elif not m2.group(4):
                    issues.append({"line": i+1, "severity": "warning", "message": f"DATA connection missing [Type] suffix"})
            elif not m.group(5):
                issues.append({"line": i+1, "severity": "warning", "message": f"DATA connection missing [Type] suffix"})
        
        elif line.startswith("VAR "):
            m = re.match(r'VAR\s+(\w+)\s*:\s*(\S+)', line)
            if not m:
                issues.append({"line": i+1, "severity": "error", "message": f"Invalid VAR syntax: {line[:60]}"})
        
        elif line.startswith("CATEGORY:"):
            pass  # Optional, always valid
        
        elif line.startswith("//"):
            pass  # Comments
        
        elif line.strip():
            issues.append({"line": i+1, "severity": "warning", "message": f"Unknown directive: {line[:60]}"})
    
    # Structure checks
    if not has_blueprint:
        issues.append({"line": 0, "severity": "error", "message": "Missing BLUEPRINT: declaration"})
    if not has_parent:
        issues.append({"line": 0, "severity": "error", "message": "Missing PARENT: declaration"})
    if not has_graph:
        issues.append({"line": 0, "severity": "error", "message": "Missing GRAPH: EventGraph declaration"})
    if not has_nodes:
        issues.append({"line": 0, "severity": "error", "message": "No NODE declarations found"})
    if not has_events:
        issues.append({"line": 0, "severity": "warning", "message": "No Event nodes found — Blueprint has no entry point"})
    
    # Check sequential node IDs
    for idx, nid in enumerate(node_ids):
        expected = f"n{idx+1}"
        if nid != expected:
            issues.append({"line": 0, "severity": "warning", "message": f"Node IDs not sequential: expected {expected}, got {nid}"})
            break
    
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    
    return {
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": issues,
        "score": 100.0 if len(errors) == 0 else max(0, 100 - (len(errors) * 20)),
    }


def check_node_mapping(dsl_text: str) -> dict:
    """Check that all node types map to known UE classes."""
    result = parse(dsl_text)
    nodes = result["ir"]["nodes"]
    
    total = len(nodes)
    mapped = sum(1 for n in nodes if n.get("ue_class") != "UNMAPPED")
    unmapped = [n for n in nodes if n.get("ue_class") == "UNMAPPED"]
    
    issues = []
    for n in unmapped:
        issues.append({
            "node_id": n["id"],
            "dsl_type": n["dsl_type"],
            "severity": "error",
            "message": f"Node type '{n['dsl_type']}' ({n['id']}) not in NODE_MAP"
        })
    
    score = (mapped / total * 100) if total > 0 else 0
    
    return {
        "total_nodes": total,
        "mapped": mapped,
        "unmapped": len(unmapped),
        "unmapped_types": [n["dsl_type"] for n in unmapped],
        "score": round(score, 1),
        "issues": issues,
    }


def check_connections(dsl_text: str) -> dict:
    """Check connection integrity — all references valid, no orphaned nodes."""
    result = parse(dsl_text)
    nodes = result["ir"]["nodes"]
    connections = result["ir"]["connections"]
    
    node_ids = {n["id"] for n in nodes}
    issues = []
    valid_conns = 0
    
    for c in connections:
        valid = True
        if c["type"] != "data_literal":
            if c.get("src_node") not in node_ids:
                issues.append({"severity": "error", "message": f"Connection references unknown source node: {c.get('src_node')}"})
                valid = False
        if c.get("dst_node") not in node_ids:
            issues.append({"severity": "error", "message": f"Connection references unknown destination node: {c.get('dst_node')}"})
            valid = False
        if valid:
            valid_conns += 1
    
    # Check for orphaned nodes (no connections at all)
    connected_nodes = set()
    for c in connections:
        if c.get("src_node"): connected_nodes.add(c["src_node"])
        if c.get("dst_node"): connected_nodes.add(c["dst_node"])
    
    orphaned = []
    for n in nodes:
        if n["id"] not in connected_nodes:
            # Events with no connections are semi-orphaned
            if n["dsl_type"].startswith("Event_"):
                issues.append({"severity": "warning", "message": f"Event node {n['id']} ({n['dsl_type']}) has no connections"})
            else:
                orphaned.append(n["id"])
                issues.append({"severity": "warning", "message": f"Node {n['id']} ({n['dsl_type']}) is orphaned — no connections"})
    
    total = len(connections)
    score = (valid_conns / total * 100) if total > 0 else (100 if len(nodes) <= 1 else 0)
    
    return {
        "total_connections": total,
        "valid_connections": valid_conns,
        "invalid_connections": total - valid_conns,
        "orphaned_nodes": orphaned,
        "score": round(score, 1),
        "issues": issues,
    }


def check_variables(dsl_text: str) -> dict:
    """Check that all variable references match declarations."""
    result = parse(dsl_text)
    nodes = result["ir"]["nodes"]
    variables = result["ir"]["variables"]
    
    declared = {v["name"] for v in variables}
    referenced = set()
    issues = []
    
    for n in nodes:
        if n["dsl_type"] in ("GetVar", "SetVar", "VariableGet", "VariableSet"):
            var_name = n["params"].get("Variable") or n["params"].get("VarName", "")
            if var_name:
                referenced.add(var_name)
                if var_name not in declared:
                    issues.append({
                        "severity": "error",
                        "node_id": n["id"],
                        "message": f"Variable '{var_name}' used in {n['id']} but not declared in VAR section"
                    })
    
    unused = declared - referenced
    for v in unused:
        issues.append({"severity": "info", "message": f"Variable '{v}' declared but never used"})
    
    errors = [i for i in issues if i["severity"] == "error"]
    score = 100.0 if len(errors) == 0 else max(0, 100 - (len(errors) * 25))
    
    return {
        "declared": list(declared),
        "referenced": list(referenced),
        "undeclared_refs": [i["message"] for i in errors],
        "unused": list(unused),
        "score": round(score, 1),
        "issues": issues,
    }


def check_exec_chains(dsl_text: str) -> dict:
    """Check that execution chains are complete — every exec node is reachable from an event."""
    result = parse(dsl_text)
    nodes = result["ir"]["nodes"]
    connections = result["ir"]["connections"]
    
    # Build exec graph
    exec_conns = [c for c in connections if c["type"] == "exec"]
    
    # Find event nodes (roots)
    events = [n for n in nodes if n["dsl_type"].startswith("Event_")]
    
    # BFS from events through exec connections
    reachable = set()
    queue = [e["id"] for e in events]
    reachable.update(queue)
    
    while queue:
        current = queue.pop(0)
        for c in exec_conns:
            if c.get("src_node") == current:
                target = c.get("dst_node")
                if target and target not in reachable:
                    reachable.add(target)
                    queue.append(target)
    
    # Find nodes with exec pins that aren't reachable
    # Pure nodes (math, GetVar, IsValid) don't need exec connections
    pure_types = {"GetVar", "VariableGet", "AddFloat", "SubtractFloat", "MultiplyFloat", 
                  "DivideFloat", "LessThan", "GreaterThan", "LessEqual", "GreaterEqual",
                  "EqualEqual", "NotBool", "IsValid", "GetActorLocation", "GetActorRotation",
                  "GetActorForwardVector", "GetDistanceTo", "GetDisplayName", "MakeVector",
                  "MakeRotator", "VectorLerp", "VectorDistance", "ClampFloat", "Sin",
                  "RandomFloatInRange", "Concatenate", "ArrayLength", "Contains", "Get"}
    
    issues = []
    unreachable = []
    for n in nodes:
        if n["id"] not in reachable and n["dsl_type"] not in pure_types:
            if not n["dsl_type"].startswith("Event_"):
                unreachable.append(n["id"])
                issues.append({
                    "severity": "warning",
                    "message": f"Node {n['id']} ({n['dsl_type']}) not reachable from any event via exec chain"
                })
    
    total_exec = len([n for n in nodes if n["dsl_type"] not in pure_types and not n["dsl_type"].startswith("Event_")])
    reachable_exec = total_exec - len(unreachable)
    score = (reachable_exec / total_exec * 100) if total_exec > 0 else 100
    
    return {
        "event_count": len(events),
        "reachable_nodes": len(reachable),
        "unreachable_exec_nodes": unreachable,
        "score": round(score, 1),
        "issues": issues,
    }


def compute_similarity(dsl_text: str, expected_text: str) -> dict:
    """Compare DSL output to expected answer using line-level matching."""
    actual_lines = set(l.strip() for l in dsl_text.strip().split("\n") if l.strip())
    expected_lines = set(l.strip() for l in expected_text.strip().split("\n") if l.strip())
    
    matching = actual_lines & expected_lines
    missing = expected_lines - actual_lines
    extra = actual_lines - expected_lines
    
    total = len(expected_lines)
    score = (len(matching) / total * 100) if total > 0 else 0
    
    return {
        "matching_lines": len(matching),
        "total_expected_lines": total,
        "missing_lines": sorted(list(missing)),
        "extra_lines": sorted(list(extra)),
        "score": round(score, 1),
    }


# ─── Tier Classification ────────────────────────────────────────────────────

def classify_tier(syntax_score, mapping_score, connection_score, variable_score, exec_score, node_count):
    """Classify into compliance tier based on scores."""
    overall = (syntax_score + mapping_score + connection_score + variable_score + exec_score) / 5
    
    if syntax_score < 100 or mapping_score < 80:
        return "Fail", overall
    
    if overall >= 97 and node_count >= 5:
        return "Production", overall
    elif overall >= 90:
        return "Certified", overall
    elif mapping_score >= 95 and syntax_score == 100:
        return "Advanced", overall
    elif syntax_score == 100 and mapping_score >= 80:
        return "Basic", overall
    else:
        return "Fail", overall


# ─── Report Generation ───────────────────────────────────────────────────────

def generate_report(dsl_text: str, expected_text: str = None) -> dict:
    """Generate a full compliance report for a DSL text."""
    
    syntax = check_syntax(dsl_text)
    mapping = check_node_mapping(dsl_text)
    connections = check_connections(dsl_text)
    variables = check_variables(dsl_text)
    exec_chains = check_exec_chains(dsl_text)
    
    similarity = None
    if expected_text:
        similarity = compute_similarity(dsl_text, expected_text)
    
    tier, overall = classify_tier(
        syntax["score"], mapping["score"], connections["score"],
        variables["score"], exec_chains["score"], mapping["total_nodes"]
    )
    
    report = {
        "overall_score": round(overall, 1),
        "tier": tier,
        "dimensions": {
            "syntax": syntax,
            "node_mapping": mapping,
            "connections": connections,
            "variables": variables,
            "exec_chains": exec_chains,
        },
        "summary": {
            "nodes": mapping["total_nodes"],
            "connections": connections["total_connections"],
            "variables": len(variables["declared"]),
            "errors": syntax["error_count"] + len([i for i in mapping["issues"] if i["severity"] == "error"]) + len([i for i in connections["issues"] if i["severity"] == "error"]),
            "warnings": syntax["warning_count"] + len([i for i in connections["issues"] if i["severity"] == "warning"]),
        }
    }
    
    if similarity:
        report["similarity"] = similarity
    
    return report


def format_report(report: dict, verbose: bool = False) -> str:
    """Format report as human-readable text."""
    lines = []
    
    lines.append("=" * 60)
    lines.append("  BlueprintLLM DSL Compliance Report")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Overall Score: {report['overall_score']}%")
    lines.append(f"  Tier: {report['tier']}")
    lines.append(f"  Nodes: {report['summary']['nodes']}  Connections: {report['summary']['connections']}  Variables: {report['summary']['variables']}")
    lines.append(f"  Errors: {report['summary']['errors']}  Warnings: {report['summary']['warnings']}")
    lines.append("")
    
    dims = report["dimensions"]
    lines.append(f"  {'Dimension':<20} {'Score':>8}  {'Status'}")
    lines.append(f"  {'-'*20} {'-'*8}  {'-'*20}")
    
    for name, dim in dims.items():
        score = dim["score"]
        status = "PASS" if score >= 90 else "WARN" if score >= 70 else "FAIL"
        icon = "✅" if score >= 90 else "⚠️" if score >= 70 else "❌"
        lines.append(f"  {name:<20} {score:>7.1f}%  {icon} {status}")
    
    if "similarity" in report:
        sim = report["similarity"]
        lines.append(f"  {'similarity':<20} {sim['score']:>7.1f}%  {'✅' if sim['score'] >= 90 else '⚠️' if sim['score'] >= 70 else '❌'}")
    
    if verbose:
        lines.append("")
        lines.append("-" * 60)
        all_issues = []
        for dim_name, dim in dims.items():
            for issue in dim.get("issues", []):
                issue["dimension"] = dim_name
                all_issues.append(issue)
        
        if all_issues:
            lines.append("  Issues:")
            for issue in sorted(all_issues, key=lambda x: (0 if x["severity"] == "error" else 1 if x["severity"] == "warning" else 2)):
                sev = issue["severity"].upper()
                dim = issue.get("dimension", "")
                msg = issue["message"]
                line_num = issue.get("line", "")
                prefix = f"L{line_num}: " if line_num else ""
                lines.append(f"    [{sev}] {prefix}{msg} ({dim})")
        else:
            lines.append("  No issues found.")
    
    lines.append("")
    return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BlueprintLLM DSL Compliance Checker — validates DSL against the spec",
        epilog="Phase 4: DSL Open Standard & Compliance Checker"
    )
    parser.add_argument("input", nargs="?", help="DSL file to check")
    parser.add_argument("--text", help="DSL text string to check (use \\n for newlines)")
    parser.add_argument("--stdin", action="store_true", help="Read DSL from stdin")
    parser.add_argument("--batch", help="Check all .dsl files in a directory")
    parser.add_argument("--compare", help="Expected DSL file for similarity scoring")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed issues")
    parser.add_argument("--tier-only", action="store_true", help="Just print the tier")
    
    args = parser.parse_args()
    
    # Determine input
    if args.batch:
        # Batch mode
        dsl_dir = Path(args.batch)
        files = sorted(dsl_dir.glob("*.dsl")) + sorted(dsl_dir.glob("*.txt"))
        if not files:
            print(f"No .dsl or .txt files found in {args.batch}")
            sys.exit(1)
        
        results = []
        for f in files:
            dsl_text = f.read_text(encoding="utf-8")
            report = generate_report(dsl_text)
            report["file"] = str(f)
            results.append(report)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\nBatch Compliance Results ({len(files)} files)")
            print(f"{'='*60}")
            for r in results:
                fname = Path(r["file"]).name
                print(f"  {fname:<30} {r['overall_score']:>6.1f}%  {r['tier']}")
            
            avg = sum(r["overall_score"] for r in results) / len(results)
            tiers = [r["tier"] for r in results]
            print(f"\n  Average: {avg:.1f}%")
            print(f"  Tiers: {', '.join(f'{t}={tiers.count(t)}' for t in set(tiers))}")
        
        sys.exit(0)
    
    if args.stdin:
        dsl_text = sys.stdin.read()
    elif args.text:
        dsl_text = args.text.replace("\\n", "\n")
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            dsl_text = f.read()
    else:
        parser.print_help()
        sys.exit(1)
    
    # Load expected DSL for comparison
    expected = None
    if args.compare:
        with open(args.compare, encoding="utf-8") as f:
            expected = f.read()
    
    # Generate report
    report = generate_report(dsl_text, expected)
    
    # Output
    if args.tier_only:
        print(report["tier"])
    elif args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_report(report, verbose=args.verbose))


if __name__ == "__main__":
    main()
