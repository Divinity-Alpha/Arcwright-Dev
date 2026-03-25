"""
BlueprintLLM — Data Table DSL Parser
Parses DT DSL text into structured JSON IR for UE5.7 plugin.

DT DSL is tabular:
    DATATABLE: DT_Weapons
    STRUCT: FWeaponData
    COLUMN Name: String
    COLUMN Damage: Float = 10.0
    ROW Pistol: "Pistol", 15.0
"""

import re
import json
try:
    from dt_type_map import resolve_type, parse_value, get_stats
except ImportError:
    from .dt_type_map import resolve_type, parse_value, get_stats


def parse(raw: str) -> dict:
    """
    Parse Data Table DSL text into IR dict.
    
    Returns:
        {
            "ir": {
                "metadata": {"table_name": ..., "struct_name": ...},
                "columns": [{"name": ..., "type": ..., "default": ...}, ...],
                "rows": [{"name": ..., "values": {...}}, ...],
            },
            "errors": [...],
            "warnings": [...],
            "stats": {...},
        }
    """
    lines = _clean_lines(raw)
    
    metadata = {"table_name": "", "struct_name": ""}
    columns = []
    rows = []
    errors = []
    warnings = []
    
    column_names = []
    
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # DATATABLE: name
        if line.startswith("DATATABLE:"):
            name = line.split(":", 1)[1].strip()
            if not name:
                errors.append(f"L{line_num}: DATATABLE name is empty")
            metadata["table_name"] = name
        
        # STRUCT: name
        elif line.startswith("STRUCT:"):
            name = line.split(":", 1)[1].strip()
            if not name:
                errors.append(f"L{line_num}: STRUCT name is empty")
            metadata["struct_name"] = name
        
        # COLUMN Name: Type [= Default]
        elif line.startswith("COLUMN "):
            col = _parse_column(line, line_num, errors, warnings)
            if col:
                if col["name"] in column_names:
                    errors.append(f"L{line_num}: Duplicate column name: {col['name']}")
                else:
                    columns.append(col)
                    column_names.append(col["name"])
        
        # ROW Name: val1, val2, val3
        elif line.startswith("ROW "):
            row = _parse_row(line, line_num, columns, errors, warnings)
            if row:
                # Check for duplicate row names
                existing_names = [r["name"] for r in rows]
                if row["name"] in existing_names:
                    warnings.append(f"L{line_num}: Duplicate row name: {row['name']}")
                rows.append(row)
        
        # Comments
        elif line.startswith("//"):
            pass
        
        # Unknown
        elif line.strip():
            warnings.append(f"L{line_num}: Unknown directive: {line[:60]}")
    
    # ─── Validation ──────────────────────────────────────────────────────
    
    if not metadata["table_name"]:
        errors.append("Missing DATATABLE: declaration")
    
    if not metadata["struct_name"]:
        errors.append("Missing STRUCT: declaration")
    
    if not columns:
        errors.append("No COLUMN declarations found")
    
    if not rows:
        warnings.append("No ROW entries — table will be empty")
    
    # Check table name convention
    if metadata["table_name"] and not metadata["table_name"].startswith("DT_"):
        warnings.append(f"Table name '{metadata['table_name']}' should start with DT_ prefix")
    
    # Check struct name convention
    if metadata["struct_name"] and not metadata["struct_name"].startswith("F"):
        warnings.append(f"Struct name '{metadata['struct_name']}' should start with F prefix (UE convention)")
    
    return {
        "ir": {
            "metadata": metadata,
            "columns": columns,
            "rows": rows,
        },
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "columns": len(columns),
            "rows": len(rows),
            "has_defaults": sum(1 for c in columns if c.get("has_default", False)),
            "column_types": list(set(c["type"]["name"] for c in columns)),
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    }


def _clean_lines(raw: str) -> list:
    """Clean raw text, return list of stripped lines."""
    lines = []
    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    return lines


def _parse_column(line: str, line_num: int, errors: list, warnings: list) -> dict:
    """Parse a COLUMN declaration."""
    # COLUMN Name: Type [= Default]
    m = re.match(r'COLUMN\s+(\w+)\s*:\s*(\S+?)(?:\s*=\s*(.+))?$', line)
    if not m:
        errors.append(f"L{line_num}: Invalid COLUMN syntax: {line[:60]}")
        return None
    
    col_name = m.group(1)
    type_str = m.group(2)
    default_str = m.group(3)
    
    type_info = resolve_type(type_str)
    
    if type_info["category"] == "unknown":
        warnings.append(f"L{line_num}: Unknown column type: {type_str}")
    
    col = {
        "name": col_name,
        "type": type_info,
        "has_default": default_str is not None,
    }
    
    if default_str is not None:
        try:
            col["default"] = parse_value(default_str.strip(), type_info)
        except (ValueError, TypeError) as e:
            warnings.append(f"L{line_num}: Invalid default for {col_name}: {e}")
            col["default"] = type_info.get("default")
    else:
        col["default"] = type_info.get("default")
    
    return col


def _parse_row(line: str, line_num: int, columns: list, errors: list, warnings: list) -> dict:
    """Parse a ROW entry."""
    # ROW Name: val1, val2, val3
    m = re.match(r'ROW\s+(\w+)\s*:\s*(.+)$', line)
    if not m:
        errors.append(f"L{line_num}: Invalid ROW syntax: {line[:60]}")
        return None
    
    row_name = m.group(1)
    values_str = m.group(2)
    
    # Smart comma splitting that respects quoted strings and parenthesized values
    raw_values = _smart_split(values_str)
    
    if len(raw_values) != len(columns):
        if len(raw_values) < len(columns):
            # Allow missing values if columns have defaults
            missing_count = len(columns) - len(raw_values)
            missing_cols = columns[len(raw_values):]
            all_have_defaults = all(c.get("has_default", False) for c in missing_cols)
            
            if all_have_defaults:
                warnings.append(f"L{line_num}: Row '{row_name}' has {len(raw_values)}/{len(columns)} values — using defaults for remaining")
            else:
                errors.append(f"L{line_num}: Row '{row_name}' has {len(raw_values)} values but {len(columns)} columns expected")
                return None
        else:
            errors.append(f"L{line_num}: Row '{row_name}' has {len(raw_values)} values but {len(columns)} columns expected")
            return None
    
    # Parse each value according to its column type
    values = {}
    for idx, col in enumerate(columns):
        if idx < len(raw_values):
            raw = raw_values[idx].strip()
            try:
                values[col["name"]] = parse_value(raw, col["type"])
            except (ValueError, TypeError) as e:
                warnings.append(f"L{line_num}: Invalid value for column '{col['name']}' in row '{row_name}': {e}")
                values[col["name"]] = col.get("default")
        else:
            values[col["name"]] = col.get("default")
    
    return {"name": row_name, "values": values}


def _smart_split(s: str) -> list:
    """Split by commas, respecting quoted strings and parenthesized groups."""
    parts = []
    current = ""
    depth_paren = 0
    depth_bracket = 0
    depth_brace = 0
    in_quote = False
    quote_char = None
    
    for c in s:
        if in_quote:
            current += c
            if c == quote_char:
                in_quote = False
            continue
        
        if c in ('"', "'"):
            in_quote = True
            quote_char = c
            current += c
        elif c == '(':
            depth_paren += 1
            current += c
        elif c == ')':
            depth_paren -= 1
            current += c
        elif c == '[':
            depth_bracket += 1
            current += c
        elif c == ']':
            depth_bracket -= 1
            current += c
        elif c == '{':
            depth_brace += 1
            current += c
        elif c == '}':
            depth_brace -= 1
            current += c
        elif c == ',' and depth_paren == 0 and depth_bracket == 0 and depth_brace == 0:
            parts.append(current)
            current = ""
        else:
            current += c
    
    if current.strip():
        parts.append(current)
    
    return parts


# ─── IR Save ─────────────────────────────────────────────────────────────────

def save_ir(result: dict, path: str):
    """Save DT IR to JSON file."""
    with open(path, "w") as f:
        json.dump(result["ir"], f, indent=2, default=str)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    
    ap = argparse.ArgumentParser(description="BlueprintLLM Data Table DSL Parser")
    ap.add_argument("input", nargs="?", help="DT DSL file to parse")
    ap.add_argument("--text", help="DT DSL text to parse")
    ap.add_argument("--output", "-o", help="Output IR JSON file")
    ap.add_argument("--json", action="store_true", help="Print full result as JSON")
    ap.add_argument("--stats", action="store_true", help="Print type map stats")
    args = ap.parse_args()
    
    if args.stats:
        stats = get_stats()
        print(f"DT Type Map: {stats['basic_types']} basic types, "
              f"{stats['asset_subtypes']} asset subtypes, {stats['aliases']} aliases")
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
        print(json.dumps(result, indent=2, default=str))
    else:
        ir = result["ir"]
        stats = result["stats"]
        print(f"Data Table: {ir['metadata']['table_name']}")
        print(f"Struct: {ir['metadata']['struct_name']}")
        print(f"Columns: {stats['columns']} ({', '.join(stats['column_types'])})")
        print(f"Rows: {stats['rows']}")
        print(f"Defaults: {stats['has_defaults']}/{stats['columns']} columns have defaults")
        
        if result["errors"]:
            print(f"\nErrors ({len(result['errors'])}):")
            for e in result["errors"]:
                print(f"  ❌ {e}")
        
        if result["warnings"]:
            print(f"\nWarnings ({len(result['warnings'])}):")
            for w in result["warnings"]:
                print(f"  ⚠️ {w}")
        
        if not result["errors"]:
            print(f"\n✅ Valid DT DSL")
    
    if args.output:
        save_ir(result, args.output)
        print(f"\nSaved IR to {args.output}")


if __name__ == "__main__":
    main()
