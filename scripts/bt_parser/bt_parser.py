"""
BlueprintLLM — Behavior Tree DSL Parser
Parses BT DSL text into structured JSON IR for UE5.7 plugin.

BT DSL uses indentation to define tree hierarchy:
    SELECTOR: Root
      DECORATOR: BlackboardBased [Key=Target, Condition=IsSet]
      SEQUENCE: Attack
        TASK: MoveTo [Key=Target]
        TASK: ApplyDamage [Key=Target, Damage=10]
      TASK: Wait [Duration=3.0]
"""

import re
import json
try:
    from bt_node_map import (
        resolve_node, KEY_TYPES, ABORT_MODES,
        COMPOSITES, TASKS, DECORATORS, SERVICES,
        get_stats,
    )
except ImportError:
    from .bt_node_map import (
        resolve_node, KEY_TYPES, ABORT_MODES,
        COMPOSITES, TASKS, DECORATORS, SERVICES,
        get_stats,
    )


# ─── Cleaning ────────────────────────────────────────────────────────────────

def clean_bt_dsl(raw: str) -> list:
    """Clean raw BT DSL text, return list of (indent_level, stripped_line) tuples."""
    lines = []
    for line in raw.split("\n"):
        # Remove trailing whitespace and garbage
        stripped = line.rstrip()
        if not stripped:
            continue
        # Skip comments
        if stripped.lstrip().startswith("//"):
            continue
        # Calculate indent level (2 spaces = 1 level)
        leading = len(stripped) - len(stripped.lstrip())
        indent = leading // 2
        content = stripped.lstrip()
        if content:
            lines.append((indent, content))
    return lines


def parse_params(param_str: str) -> dict:
    """Parse [Key=Value, Key2=Value2] parameter strings."""
    if not param_str:
        return {}
    params = {}
    key, val, in_key, depth = "", "", True, 0
    for c in param_str:
        if c == '(': depth += 1; val += c
        elif c == ')': depth -= 1; val += c
        elif c == '=' and in_key and depth == 0: in_key = False
        elif c == ',' and depth == 0:
            if key.strip():
                params[key.strip()] = parse_value(val.strip().strip('"'))
            key, val, in_key = "", "", True
        elif in_key: key += c
        else: val += c
    if key.strip():
        params[key.strip()] = parse_value(val.strip().strip('"'))
    return params


def parse_value(val: str):
    """Parse a parameter value — detect type automatically."""
    if val.lower() == "true": return True
    if val.lower() == "false": return False
    try:
        if "." in val: return float(val)
        return int(val)
    except ValueError:
        return val


# ─── Main Parser ─────────────────────────────────────────────────────────────

def parse(raw: str) -> dict:
    """
    Parse BT DSL text into IR dict.
    
    Returns:
        {
            "ir": {
                "metadata": {"name": ..., "blackboard": ...},
                "blackboard_keys": [...],
                "tree": {root node with children recursively},
            },
            "errors": [...],
            "warnings": [...],
            "stats": {...},
        }
    """
    lines = clean_bt_dsl(raw)
    
    metadata = {"name": "", "blackboard": ""}
    blackboard_keys = []
    errors = []
    warnings = []
    
    # ─── Phase 1: Parse header (before TREE:) ────────────────────────────
    
    tree_start = None
    
    for i, (indent, content) in enumerate(lines):
        if content.startswith("BEHAVIORTREE:"):
            metadata["name"] = content.split(":", 1)[1].strip()
        
        elif content.startswith("BLACKBOARD:"):
            metadata["blackboard"] = content.split(":", 1)[1].strip()
        
        elif content.startswith("KEY "):
            m = re.match(r'KEY\s+(\w+)\s*:\s*(\w+)(?:\s*=\s*(.+))?', content)
            if m:
                key_name = m.group(1)
                key_type = m.group(2)
                key_default = m.group(3).strip() if m.group(3) else None
                
                if key_type not in KEY_TYPES:
                    warnings.append(f"Unknown blackboard key type: {key_type} (key: {key_name})")
                
                blackboard_keys.append({
                    "name": key_name,
                    "type": key_type,
                    "ue_type": KEY_TYPES.get(key_type, "UNKNOWN"),
                    "default": parse_value(key_default) if key_default else None,
                })
            else:
                errors.append(f"Invalid KEY syntax: {content}")
        
        elif content == "TREE:":
            tree_start = i + 1
            break
    
    # ─── Validate header ─────────────────────────────────────────────────
    
    if not metadata["name"]:
        errors.append("Missing BEHAVIORTREE: declaration")
    if not metadata["blackboard"]:
        errors.append("Missing BLACKBOARD: declaration")
    if tree_start is None:
        errors.append("Missing TREE: marker — no tree structure found")
        return _build_result(metadata, blackboard_keys, None, errors, warnings)
    
    # ─── Phase 2: Parse tree structure ───────────────────────────────────
    
    tree_lines = lines[tree_start:]
    if not tree_lines:
        errors.append("TREE: section is empty — no nodes defined")
        return _build_result(metadata, blackboard_keys, None, errors, warnings)
    
    # Parse into tree using indent-based hierarchy
    root, tree_errors, tree_warnings = _parse_tree(tree_lines, blackboard_keys)
    errors.extend(tree_errors)
    warnings.extend(tree_warnings)
    
    # ─── Phase 3: Validate tree ──────────────────────────────────────────
    
    if root:
        _validate_tree(root, blackboard_keys, errors, warnings)
    
    return _build_result(metadata, blackboard_keys, root, errors, warnings)


def _parse_tree(lines: list, bb_keys: list) -> tuple:
    """
    Parse indented tree lines into nested node structure.
    
    Returns (root_node, errors, warnings)
    """
    errors = []
    warnings = []
    
    # Stack of (indent_level, node) for tracking hierarchy
    stack = []
    root = None
    node_counter = [0]  # Mutable counter for unique IDs
    
    # Pending decorators/services to attach to the next composite/task
    pending_decorators = []
    pending_services = []
    
    for indent, content in lines:
        node = _parse_node_line(content, node_counter, errors, warnings)
        if not node:
            continue
        
        node_type = node.get("_node_category")
        
        # Decorators and services are collected, then attached
        if node_type == "decorator":
            pending_decorators.append(node)
            continue
        
        if node_type == "service":
            pending_services.append(node)
            continue
        
        # MAIN: and BACKGROUND: are structural markers for SimpleParallel
        if content.startswith("MAIN:"):
            continue
        if content.startswith("BACKGROUND:"):
            continue
        
        # Attach pending decorators/services
        if pending_decorators:
            node["decorators"] = pending_decorators
            pending_decorators = []
        if pending_services:
            node["services"] = pending_services
            pending_services = []
        
        # Place in hierarchy based on indent
        if not root:
            root = node
            stack = [(indent, node)]
        else:
            # Pop stack until we find the parent (indent - 1)
            while stack and stack[-1][0] >= indent:
                stack.pop()
            
            if stack:
                parent = stack[-1][1]
                if "children" not in parent:
                    parent["children"] = []
                parent["children"].append(node)
            else:
                # No parent found — this is a sibling of root or error
                warnings.append(f"Node '{node.get('name', node.get('dsl_type'))}' at indent {indent} has no parent — attaching to root")
                if "children" not in root:
                    root["children"] = []
                root["children"].append(node)
            
            stack.append((indent, node))
    
    # Warn about unused pending decorators/services
    for d in pending_decorators:
        warnings.append(f"Decorator '{d.get('dsl_type')}' has no target node — trailing at end of tree")
    for s in pending_services:
        warnings.append(f"Service '{s.get('dsl_type')}' has no target node — trailing at end of tree")
    
    return root, errors, warnings


def _parse_node_line(content: str, counter: list, errors: list, warnings: list) -> dict:
    """Parse a single tree line into a node dict."""
    
    # Match: TYPE: OptionalName [params]
    # or:   TYPE: [params]  (no name)
    m = re.match(r'(\w+)\s*:\s*(?:(\w+)\s*)?(?:\[(.+?)\])?\s*$', content)
    
    if not m:
        # Try without colon: TASK [params] (shouldn't happen but be lenient)
        m2 = re.match(r'(\w+)\s*(?:\[(.+?)\])?\s*$', content)
        if m2 and m2.group(1) in ('MAIN', 'BACKGROUND'):
            return None  # Structural marker, not a node
        if m2:
            warnings.append(f"Node line missing colon separator: {content[:60]}")
        else:
            errors.append(f"Invalid tree line: {content[:60]}")
        return None
    
    line_type = m.group(1)  # SELECTOR, SEQUENCE, TASK, DECORATOR, SERVICE
    name_or_type = m.group(2) or ""
    param_str = m.group(3) or ""
    
    counter[0] += 1
    node_id = f"bt_{counter[0]}"
    
    # Determine node category and resolve type
    if line_type.upper() in ("SELECTOR", "SEQUENCE", "PARALLEL", "SIMPLEPARALLEL"):
        # Composite — line_type IS the node type, name_or_type is the display name
        # Convert to PascalCase for node map lookup
        type_map = {"SELECTOR": "Selector", "SEQUENCE": "Sequence", 
                    "PARALLEL": "SimpleParallel", "SIMPLEPARALLEL": "SimpleParallel"}
        lookup_type = type_map.get(line_type.upper(), line_type)
        canonical, mapping, cat = resolve_node(lookup_type, "composite")
        return {
            "id": node_id,
            "dsl_type": canonical,
            "name": name_or_type or canonical,
            "ue_class": mapping["ue_class"] if mapping else "UNMAPPED",
            "params": parse_params(param_str),
            "children": [],
            "decorators": [],
            "services": [],
            "_node_category": "composite",
        }
    
    elif line_type == "TASK":
        # Task — name_or_type is the task type
        if not name_or_type:
            errors.append(f"TASK missing type name: {content[:60]}")
            return None
        canonical, mapping, cat = resolve_node(name_or_type, "task")
        if not mapping:
            warnings.append(f"Unknown task type: {name_or_type}")
        return {
            "id": node_id,
            "dsl_type": canonical,
            "name": canonical,
            "ue_class": mapping["ue_class"] if mapping else "UNMAPPED",
            "params": parse_params(param_str),
            "is_custom": mapping.get("custom", False) if mapping else False,
            "_node_category": "task",
        }
    
    elif line_type == "DECORATOR":
        if not name_or_type:
            errors.append(f"DECORATOR missing type name: {content[:60]}")
            return None
        canonical, mapping, cat = resolve_node(name_or_type, "decorator")
        if not mapping:
            warnings.append(f"Unknown decorator type: {name_or_type}")
        
        params = parse_params(param_str)
        
        # Validate abort mode if present
        abort = params.get("AbortMode", "None")
        if abort not in ABORT_MODES:
            warnings.append(f"Unknown AbortMode: {abort} (decorator {canonical})")
        
        # Validate condition if BlackboardBased
        if canonical == "BlackboardBased":
            condition = params.get("Condition", "")
            valid_conditions = mapping.get("conditions", []) if mapping else []
            if condition and valid_conditions and condition not in valid_conditions:
                warnings.append(f"Unknown condition: {condition} (decorator {canonical})")
        
        return {
            "id": node_id,
            "dsl_type": canonical,
            "name": canonical,
            "ue_class": mapping["ue_class"] if mapping else "UNMAPPED",
            "params": params,
            "abort_mode": ABORT_MODES.get(abort, "EBTFlowAbortMode::None"),
            "_node_category": "decorator",
        }
    
    elif line_type == "SERVICE":
        if not name_or_type:
            errors.append(f"SERVICE missing type name: {content[:60]}")
            return None
        canonical, mapping, cat = resolve_node(name_or_type, "service")
        if not mapping:
            warnings.append(f"Unknown service type: {name_or_type}")
        return {
            "id": node_id,
            "dsl_type": canonical,
            "name": canonical,
            "ue_class": mapping["ue_class"] if mapping else "UNMAPPED",
            "params": parse_params(param_str),
            "is_custom": mapping.get("custom", False) if mapping else False,
            "interval": parse_params(param_str).get("Interval", 0.5),
            "_node_category": "service",
        }
    
    else:
        # Could be a composite used directly: "Selector: Name [params]"
        canonical, mapping, cat = resolve_node(line_type)
        if mapping and cat == "composite":
            return {
                "id": node_id,
                "dsl_type": canonical,
                "name": name_or_type or canonical,
                "ue_class": mapping["ue_class"],
                "params": parse_params(param_str),
                "children": [],
                "decorators": [],
                "services": [],
                "_node_category": "composite",
            }
        
        warnings.append(f"Unknown node line type: {line_type} in '{content[:60]}'")
        return None


def _validate_tree(root: dict, bb_keys: list, errors: list, warnings: list):
    """Validate the parsed tree structure."""
    
    bb_key_names = {k["name"] for k in bb_keys}
    
    def validate_node(node, depth=0):
        cat = node.get("_node_category")
        
        # Composites should have children
        if cat == "composite":
            children = node.get("children", [])
            if not children:
                warnings.append(f"Composite '{node.get('name', node['dsl_type'])}' has no children")
        
        # Tasks should NOT have children
        if cat == "task":
            if node.get("children"):
                errors.append(f"Task '{node['dsl_type']}' ({node['id']}) has children — tasks must be leaf nodes")
        
        # Validate blackboard key references in params
        params = node.get("params", {})
        for param_name in ("Key", "TargetKey", "ResultKey", "StartKey", "EndKey",
                           "ConeOrigin", "ObservedKey", "KeyA", "KeyB"):
            if param_name in params:
                key_ref = params[param_name]
                if isinstance(key_ref, str) and key_ref not in bb_key_names:
                    # Allow special values
                    if key_ref not in ("Next", "AwayFromThreat", "Self"):
                        warnings.append(
                            f"Node '{node['dsl_type']}' references blackboard key "
                            f"'{key_ref}' (param {param_name}) which is not declared"
                        )
        
        # Recurse into children
        for child in node.get("children", []):
            validate_node(child, depth + 1)
        
        # Validate decorators
        for dec in node.get("decorators", []):
            validate_node(dec, depth)
        
        # Validate services
        for svc in node.get("services", []):
            validate_node(svc, depth)
    
    # Root must be a composite
    if root.get("_node_category") != "composite":
        errors.append(f"Root node must be a composite (Selector/Sequence), got {root.get('_node_category')}")
    
    validate_node(root)


def _clean_node_for_ir(node: dict) -> dict:
    """Remove internal fields from a node for IR output."""
    clean = {k: v for k, v in node.items() if not k.startswith("_")}
    
    if "children" in clean:
        clean["children"] = [_clean_node_for_ir(c) for c in clean["children"]]
    if "decorators" in clean:
        clean["decorators"] = [_clean_node_for_ir(d) for d in clean["decorators"]]
    if "services" in clean:
        clean["services"] = [_clean_node_for_ir(s) for s in clean["services"]]
    
    return clean


def _count_nodes(node: dict) -> dict:
    """Count nodes by category in the tree."""
    counts = {"composites": 0, "tasks": 0, "decorators": 0, "services": 0}
    
    cat = node.get("_node_category", "")
    if cat == "composite": counts["composites"] += 1
    elif cat == "task": counts["tasks"] += 1
    elif cat == "decorator": counts["decorators"] += 1
    elif cat == "service": counts["services"] += 1
    
    for child in node.get("children", []):
        child_counts = _count_nodes(child)
        for k in counts:
            counts[k] += child_counts[k]
    
    for dec in node.get("decorators", []):
        counts["decorators"] += 1
    
    for svc in node.get("services", []):
        counts["services"] += 1
    
    return counts


def _build_result(metadata, bb_keys, root, errors, warnings):
    """Assemble the final result dict."""
    
    node_counts = _count_nodes(root) if root else {"composites": 0, "tasks": 0, "decorators": 0, "services": 0}
    total = sum(node_counts.values())
    
    # Count unmapped
    unmapped = 0
    def count_unmapped(node):
        nonlocal unmapped
        if node.get("ue_class") == "UNMAPPED":
            unmapped += 1
        for c in node.get("children", []):
            count_unmapped(c)
        for d in node.get("decorators", []):
            count_unmapped(d)
        for s in node.get("services", []):
            count_unmapped(s)
    
    if root:
        count_unmapped(root)
    
    clean_root = _clean_node_for_ir(root) if root else None
    
    return {
        "ir": {
            "metadata": metadata,
            "blackboard_keys": bb_keys,
            "tree": clean_root,
        },
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "total_nodes": total,
            "composites": node_counts["composites"],
            "tasks": node_counts["tasks"],
            "decorators": node_counts["decorators"],
            "services": node_counts["services"],
            "blackboard_keys": len(bb_keys),
            "mapped": total - unmapped,
            "unmapped": unmapped,
            "has_root": root is not None,
        },
    }


# ─── IR Save ─────────────────────────────────────────────────────────────────

def save_ir(result: dict, path: str):
    """Save BT IR to JSON file."""
    with open(path, "w") as f:
        json.dump(result["ir"], f, indent=2)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    """CLI for testing the BT parser."""
    import argparse
    
    ap = argparse.ArgumentParser(description="BlueprintLLM Behavior Tree DSL Parser")
    ap.add_argument("input", nargs="?", help="BT DSL file to parse")
    ap.add_argument("--text", help="BT DSL text to parse")
    ap.add_argument("--output", "-o", help="Output IR JSON file")
    ap.add_argument("--json", action="store_true", help="Print full result as JSON")
    ap.add_argument("--stats", action="store_true", help="Print node map stats")
    args = ap.parse_args()
    
    if args.stats:
        stats = get_stats()
        print(f"BT Node Map: {stats['total']} nodes ({stats['composites']} composites, "
              f"{stats['tasks']} tasks, {stats['decorators']} decorators, {stats['services']} services) "
              f"+ {stats['aliases']} aliases")
        return
    
    if args.text:
        dsl = args.text.replace("\\n", "\n")
    elif args.input:
        with open(args.input) as f:
            dsl = f.read()
    else:
        ap.print_help()
        return
    
    result = parse(dsl)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        ir = result["ir"]
        stats = result["stats"]
        print(f"Behavior Tree: {ir['metadata']['name']}")
        print(f"Blackboard: {ir['metadata']['blackboard']} ({stats['blackboard_keys']} keys)")
        print(f"Nodes: {stats['total_nodes']} ({stats['composites']} composites, {stats['tasks']} tasks, "
              f"{stats['decorators']} decorators, {stats['services']} services)")
        print(f"Mapped: {stats['mapped']}/{stats['total_nodes']}")
        
        if result["errors"]:
            print(f"\nErrors ({len(result['errors'])}):")
            for e in result["errors"]:
                print(f"  ❌ {e}")
        
        if result["warnings"]:
            print(f"\nWarnings ({len(result['warnings'])}):")
            for w in result["warnings"]:
                print(f"  ⚠️ {w}")
        
        if not result["errors"]:
            print(f"\n✅ Valid BT DSL")
    
    if args.output:
        save_ir(result, args.output)
        print(f"\nSaved IR to {args.output}")


if __name__ == "__main__":
    main()
