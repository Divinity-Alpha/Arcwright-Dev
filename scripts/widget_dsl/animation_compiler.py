"""
Widget DSL v2 Animation Compiler — parses @anim: properties into animation definitions.

Extracts: @anim:TriggerName = AnimType|param=value|param=value
Validates animation types and parameters.
Returns animation definitions per widget.
"""

from typing import List, Dict, Any, Optional


# Supported animation types and their valid parameters
ANIM_TYPES = {
    "Shake": {"intensity": 5.0, "duration": 0.3, "frequency": 20.0},
    "Pulse": {"scale_min": 0.95, "scale_max": 1.05, "duration": 0.5, "loops": 0},
    "Flash": {"color": "#FFFFFF", "duration": 0.2, "loops": 1},
    "FadeIn": {"duration": 0.3, "from_opacity": 0.0, "to_opacity": 1.0},
    "FadeOut": {"duration": 0.3, "from_opacity": 1.0, "to_opacity": 0.0},
    "SlideIn": {"direction": "Left", "distance": 100.0, "duration": 0.3},
    "SlideOut": {"direction": "Left", "distance": 100.0, "duration": 0.3},
    "ScalePop": {"target_scale": 1.2, "duration": 0.2, "bounce": "true"},
    "ColorShift": {"to_color": "#FF0000", "duration": 0.5},
    "Spin": {"degrees": 360.0, "duration": 1.0, "loops": 1},
}


def _parse_anim_raw(raw: str) -> Optional[dict]:
    """Parse 'AnimType|param=value|param=value' into {type, params}."""
    parts = [p.strip() for p in raw.split("|")]
    if not parts:
        return None

    anim_type = parts[0]
    if anim_type not in ANIM_TYPES:
        return {"type": anim_type, "params": {}, "errors": [f"Unknown animation type: {anim_type}"]}

    defaults = ANIM_TYPES[anim_type]
    params = dict(defaults)  # start with defaults
    errors = []

    for part in parts[1:]:
        if "=" not in part:
            errors.append(f"Invalid param (no '='): {part}")
            continue
        key, val = part.split("=", 1)
        key = key.strip()
        val = val.strip()
        if key in defaults:
            # Coerce to the default's type
            default_val = defaults[key]
            try:
                if isinstance(default_val, float):
                    params[key] = float(val)
                elif isinstance(default_val, int):
                    params[key] = int(val)
                else:
                    params[key] = val
            except (ValueError, TypeError):
                params[key] = val
        else:
            errors.append(f"Unknown param '{key}' for {anim_type}")
            params[key] = val

    result = {"type": anim_type, "params": params}
    if errors:
        result["errors"] = errors
    return result


def _walk_animations(node: dict, result: List[dict]):
    """Recursively collect animations from nodes."""
    for anim in node.get("animations", []):
        trigger = anim.get("trigger", "")
        raw = anim.get("raw", "")
        parsed = _parse_anim_raw(raw)
        if parsed:
            result.append({
                "widget": node.get("name", "?"),
                "trigger": trigger,
                **parsed,
            })

    for child in node.get("children", []):
        _walk_animations(child, result)


def compile_animations(tree: dict) -> List[dict]:
    """Compile all @anim: definitions from the widget tree.

    Returns list of:
        {"widget": "HealthBar", "trigger": "OnDamage", "type": "Shake", "params": {...}}
    """
    result: List[dict] = []
    _walk_animations(tree["root"], result)
    return result
