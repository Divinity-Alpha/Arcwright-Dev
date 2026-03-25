"""
Arcwright — HTML to UE Widget Translator
=========================================
Converts HTML/CSS UI mockups into Unreal Engine Widget Blueprint commands.
Claude designs beautiful UIs in HTML → this translates them into real game HUDs.

Pipeline:
    HTML string → parse DOM → extract styles → map to UE widgets → generate commands

Usage:
    from html_to_widget import translate_html_to_widget

    commands = translate_html_to_widget(html_string, widget_name="WBP_GameHUD")
    
    # commands is a list of dicts ready for the MCP/TCP server:
    # [
    #   {"cmd": "create_widget_blueprint", "name": "WBP_GameHUD"},
    #   {"cmd": "add_widget_child", "widget": "WBP_GameHUD", "type": "CanvasPanel", "name": "Root", ...},
    #   {"cmd": "set_widget_property", "widget": "WBP_GameHUD", "child": "ScoreText", "property": "font_size", "value": 24},
    #   ...
    # ]
"""

import re
import json
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════════
# CSS STYLE PARSER
# ═══════════════════════════════════════════════════════════════════════════════

def parse_inline_style(style_str: str) -> dict:
    """Parse a CSS inline style string into a dict."""
    if not style_str:
        return {}
    props = {}
    for declaration in style_str.split(";"):
        declaration = declaration.strip()
        if ":" not in declaration:
            continue
        prop, value = declaration.split(":", 1)
        props[prop.strip().lower()] = value.strip()
    return props


def parse_css_color(color_str: str) -> Optional[dict]:
    """Parse CSS color to {r, g, b, a} in 0-1 range."""
    color_str = color_str.strip().lower()
    
    # Named colors
    NAMED = {
        "white": (1, 1, 1, 1), "black": (0, 0, 0, 1), "red": (1, 0, 0, 1),
        "green": (0, 0.5, 0, 1), "blue": (0, 0, 1, 1), "yellow": (1, 1, 0, 1),
        "cyan": (0, 1, 1, 1), "magenta": (1, 0, 1, 1), "orange": (1, 0.65, 0, 1),
        "gray": (0.5, 0.5, 0.5, 1), "grey": (0.5, 0.5, 0.5, 1),
        "transparent": (0, 0, 0, 0), "gold": (1, 0.84, 0, 1),
        "lime": (0, 1, 0, 1), "purple": (0.5, 0, 0.5, 1),
    }
    if color_str in NAMED:
        r, g, b, a = NAMED[color_str]
        return {"r": r, "g": g, "b": b, "a": a}
    
    # #hex
    if color_str.startswith("#"):
        h = color_str[1:]
        if len(h) == 3:
            h = h[0]*2 + h[1]*2 + h[2]*2
        if len(h) == 6:
            return {"r": int(h[0:2], 16)/255, "g": int(h[2:4], 16)/255, "b": int(h[4:6], 16)/255, "a": 1.0}
        if len(h) == 8:
            return {"r": int(h[0:2], 16)/255, "g": int(h[2:4], 16)/255, "b": int(h[4:6], 16)/255, "a": int(h[6:8], 16)/255}
    
    # rgb(r, g, b) or rgba(r, g, b, a)
    m = re.match(r'rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+))?\s*\)', color_str)
    if m:
        r, g, b = float(m.group(1)), float(m.group(2)), float(m.group(3))
        a = float(m.group(4)) if m.group(4) else 1.0
        # Assume 0-255 if any value > 1
        if r > 1 or g > 1 or b > 1:
            r, g, b = r/255, g/255, b/255
        return {"r": r, "g": g, "b": b, "a": a}
    
    return None


def parse_css_size(size_str: str, reference_size: float = 1920) -> Optional[float]:
    """Parse CSS size value to pixels."""
    size_str = size_str.strip().lower()
    
    m = re.match(r'([\d.]+)(px|%|em|rem|vw|vh)?', size_str)
    if not m:
        return None
    
    value = float(m.group(1))
    unit = m.group(2) or "px"
    
    if unit == "px":
        return value
    elif unit == "%":
        return value / 100 * reference_size
    elif unit in ("em", "rem"):
        return value * 16  # Assume 16px base
    elif unit == "vw":
        return value / 100 * 1920
    elif unit == "vh":
        return value / 100 * 1080
    
    return value


# ═══════════════════════════════════════════════════════════════════════════════
# DOM NODE → WIDGET NODE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WidgetNode:
    """Intermediate representation of a UE widget."""
    widget_type: str
    name: str
    parent: Optional[str] = None
    properties: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    
    # Position/size from CSS
    pos_x: Optional[float] = None
    pos_y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None


# Element tag → UE widget type mapping
TAG_MAP = {
    # Text elements
    "h1": "TextBlock",
    "h2": "TextBlock",
    "h3": "TextBlock",
    "h4": "TextBlock",
    "h5": "TextBlock",
    "h6": "TextBlock",
    "p": "TextBlock",
    "span": "TextBlock",
    "label": "TextBlock",
    
    # Interactive
    "button": "Button",
    "input": "EditableText",
    
    # Media
    "img": "Image",
    
    # Containers — resolved dynamically based on CSS
    "div": "_container",
    "section": "_container",
    "header": "_container",
    "footer": "_container",
    "main": "_container",
    "nav": "_container",
    "article": "_container",
    "aside": "_container",
    "ul": "VerticalBox",
    "ol": "VerticalBox",
    "li": "HorizontalBox",
}

# Default font sizes for heading tags
HEADING_SIZES = {
    "h1": 36, "h2": 28, "h3": 24, "h4": 20, "h5": 16, "h6": 14,
}

# Counter for unique names
_name_counter = {}


def _unique_name(base: str) -> str:
    """Generate unique widget names."""
    count = _name_counter.get(base, 0)
    _name_counter[base] = count + 1
    if count == 0:
        return base
    return f"{base}_{count}"


def _reset_names():
    global _name_counter
    _name_counter = {}


def resolve_container_type(styles: dict) -> str:
    """Determine UE container type from CSS layout properties.

    In UE, positioning (absolute/relative) is handled by CanvasPanel SLOT properties
    on the parent, NOT by making the element itself a CanvasPanel. So flex/grid
    layout takes priority over positioning — the element's type determines how its
    CHILDREN are arranged, while its position is set via slot properties.
    """
    display = styles.get("display", "block")
    flex_dir = styles.get("flex-direction", "row")
    position = styles.get("position", "static")

    # Flexbox takes priority (child layout)
    if display in ("flex", "inline-flex"):
        if flex_dir == "column":
            return "VerticalBox"
        else:
            return "HorizontalBox"

    # Grid → GridPanel (approximate)
    if display == "grid":
        return "UniformGridPanel"

    # Absolute/fixed positioning without explicit layout → CanvasPanel
    if position in ("absolute", "fixed", "relative"):
        return "CanvasPanel"

    # Default block → VerticalBox (elements stack vertically)
    return "VerticalBox"


def resolve_widget_name(tag: str, element, styles: dict) -> str:
    """Generate a meaningful widget name from the HTML element."""
    # Use id if present (assumed unique in HTML)
    if element.get("id"):
        return element["id"].replace("-", "_").replace(" ", "_")

    # Use data-widget-name if present (custom attribute for control)
    if element.get("data-widget-name"):
        return element["data-widget-name"]

    # Use class names (deduplicate since multiple elements share classes)
    classes = element.get("class", [])
    if classes:
        if isinstance(classes, list):
            base = classes[0].replace("-", "_").replace(" ", "_")
        else:
            base = str(classes).replace("-", "_").replace(" ", "_")
        return _unique_name(base)

    # Generate from tag + content
    text = element.get_text(strip=True)[:20].replace(" ", "_") if element.get_text(strip=True) else ""
    base = f"{tag}_{text}" if text else tag
    return _unique_name(base)


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_embedded_styles(soup: BeautifulSoup) -> dict:
    """Extract <style> block CSS rules into a class→properties dict."""
    class_styles = {}
    for style_tag in soup.find_all("style"):
        css_text = style_tag.string or ""
        # Simple regex parser for class selectors
        # Handles: .class-name { prop: value; }
        pattern = r'\.([a-zA-Z0-9_-]+)\s*\{([^}]+)\}'
        for match in re.finditer(pattern, css_text):
            class_name = match.group(1)
            props_text = match.group(2)
            class_styles[class_name] = parse_inline_style(props_text)
    return class_styles


def get_computed_styles(element, class_styles: dict) -> dict:
    """Merge class styles + inline styles for an element."""
    computed = {}
    
    # Apply class styles
    classes = element.get("class", [])
    if isinstance(classes, str):
        classes = classes.split()
    for cls in classes:
        if cls in class_styles:
            computed.update(class_styles[cls])
    
    # Override with inline styles
    inline = parse_inline_style(element.get("style", ""))
    computed.update(inline)
    
    return computed


# ═══════════════════════════════════════════════════════════════════════════════
# HTML → WIDGET TREE
# ═══════════════════════════════════════════════════════════════════════════════

def html_element_to_widget(element: Tag, class_styles: dict, parent_name: str = None, 
                            depth: int = 0) -> Optional[WidgetNode]:
    """Convert an HTML element and its children to a WidgetNode tree."""
    tag = element.name.lower() if element.name else ""
    
    if tag not in TAG_MAP:
        # Skip unknown tags, but process children
        return None
    
    styles = get_computed_styles(element, class_styles)
    widget_type = TAG_MAP[tag]
    
    # Resolve container types dynamically
    if widget_type == "_container":
        widget_type = resolve_container_type(styles)
    
    name = resolve_widget_name(tag, element, styles)
    
    node = WidgetNode(
        widget_type=widget_type,
        name=name,
        parent=parent_name,
    )
    
    # ─── Extract position/size ───
    
    if "left" in styles:
        node.pos_x = parse_css_size(styles["left"])
    if "top" in styles:
        node.pos_y = parse_css_size(styles["top"])
    if "right" in styles and not node.pos_x:
        right = parse_css_size(styles["right"])
        width = parse_css_size(styles.get("width", "0"))
        if right is not None:
            node.pos_x = 1920 - right - (width or 0)
    if "bottom" in styles and not node.pos_y:
        bottom = parse_css_size(styles["bottom"])
        height = parse_css_size(styles.get("height", "0"))
        if bottom is not None:
            node.pos_y = 1080 - bottom - (height or 0)
    
    if "width" in styles:
        node.width = parse_css_size(styles["width"])
    if "height" in styles:
        node.height = parse_css_size(styles["height"])
    
    # ─── Extract visual properties ───
    
    # Text content and font
    if widget_type == "TextBlock":
        text = element.get_text(strip=True)
        if text:
            node.properties["text"] = text
        
        # Font size
        if "font-size" in styles:
            node.properties["font_size"] = int(parse_css_size(styles["font-size"]) or 14)
        elif tag in HEADING_SIZES:
            node.properties["font_size"] = HEADING_SIZES[tag]
        
        # Text color
        if "color" in styles:
            color = parse_css_color(styles["color"])
            if color:
                node.properties["color"] = color
        
        # Font weight → bold (not yet supported by UE plugin, skip for now)
        # fw = styles.get("font-weight", "")
        # if fw in ("bold", "700", "800", "900"):
        #     node.properties["font_weight"] = "Bold"
        
        # Text alignment
        align = styles.get("text-align", "")
        if align == "center":
            node.properties["justification"] = "Center"
        elif align == "right":
            node.properties["justification"] = "Right"
    
    # Progress bar detection (any container type can be a progress bar)
    if widget_type not in ("TextBlock", "Button", "Image", "EditableText") and _looks_like_progress_bar(element, styles):
        node.widget_type = "ProgressBar"
        node.properties["percent"] = _extract_progress_percent(element, styles)
        if "background-color" in styles:
            color = parse_css_color(styles["background-color"])
            if color:
                node.properties["fill_color"] = color
    
    # Background color on containers (not yet supported by UE plugin for most types, skip)
    # if "background-color" in styles and widget_type not in ("TextBlock", "ProgressBar"):
    #     color = parse_css_color(styles["background-color"])
    #     if color and color["a"] > 0:
    #         node.properties["background_color"] = color
    
    # Opacity
    if "opacity" in styles:
        try:
            node.properties["render_opacity"] = float(styles["opacity"])
        except ValueError:
            pass
    
    # Visibility
    if styles.get("display") == "none" or styles.get("visibility") == "hidden":
        node.properties["visibility"] = "Hidden"
    
    # Padding
    if "padding" in styles:
        pad = parse_css_size(styles["padding"])
        if pad:
            node.properties["padding"] = {"left": pad, "top": pad, "right": pad, "bottom": pad}
    
    # Button special handling
    if widget_type == "Button":
        text = element.get_text(strip=True)
        if text:
            node.properties["button_text"] = text
    
    # Image
    if widget_type == "Image":
        src = element.get("src", "")
        if src:
            node.properties["image_source"] = src
    
    # ─── Recurse into children ───
    # ProgressBar is a leaf widget in UE — its fill is controlled by percent, not children
    if node.widget_type != "ProgressBar":
        for child in element.children:
            if not isinstance(child, Tag):
                continue
            child_node = html_element_to_widget(child, class_styles, parent_name=name, depth=depth+1)
            if child_node:
                node.children.append(child_node)
    
    return node


def _looks_like_progress_bar(element, styles) -> bool:
    """Heuristic: is this element a progress bar?"""
    # data attribute — explicit marker, always trust
    if element.get("data-widget") in ("progress", "progressbar"):
        return True
    # Class name must be EXACTLY a bar-like pattern (not just contain "bar" substring)
    classes = element.get("class", [])
    if isinstance(classes, str):
        classes = classes.split()
    bar_classes = {"progress", "progress-bar", "progressbar", "health-bar", "mana-bar",
                   "stamina-bar", "xp-bar", "fill-bar", "loading-bar", "bar"}
    if any(cls.lower() in bar_classes for cls in classes):
        return True
    # Single child div with width percentage (classic CSS progress bar pattern)
    children = [c for c in element.children if isinstance(c, Tag)]
    if len(children) == 1 and len(list(element.stripped_strings)) == 0:
        child_styles = parse_inline_style(children[0].get("style", ""))
        if "width" in child_styles and "%" in child_styles["width"]:
            return True
    return False


def _extract_progress_percent(element, styles) -> float:
    """Extract fill percentage from a progress bar element."""
    # data-percent attribute
    if element.get("data-percent"):
        return float(element["data-percent"]) / 100
    if element.get("data-value"):
        return float(element["data-value"]) / 100
    # Child div with width percentage
    children = [c for c in element.children if isinstance(c, Tag)]
    if children:
        child_styles = parse_inline_style(children[0].get("style", ""))
        if "width" in child_styles and "%" in child_styles["width"]:
            return float(child_styles["width"].replace("%", "")) / 100
    return 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# WIDGET TREE → COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

def widget_tree_to_commands(root: WidgetNode, widget_bp_name: str) -> list:
    """Flatten a WidgetNode tree into a list of TCP/MCP commands."""
    commands = []
    
    # Create the widget blueprint
    commands.append({
        "cmd": "create_widget_blueprint",
        "name": widget_bp_name,
    })
    
    # Walk tree depth-first
    def walk(node: WidgetNode, parent_name: str = None, is_root: bool = False):
        # Add child widget
        cmd = {
            "cmd": "add_widget_child",
            "widget": widget_bp_name,
            "type": node.widget_type,
            "name": node.name,
        }
        if parent_name:
            cmd["parent"] = parent_name
        commands.append(cmd)

        # Skip position/size on the root widget (it fills the screen)
        if is_root:
            for child in node.children:
                walk(child, node.name)
            return

        # Set position (CanvasPanel slot) — UE plugin uses "position"
        if node.pos_x is not None or node.pos_y is not None:
            commands.append({
                "cmd": "set_widget_property",
                "widget": widget_bp_name,
                "child": node.name,
                "property": "position",
                "value": {
                    "x": node.pos_x or 0,
                    "y": node.pos_y or 0,
                },
            })

        # Set size — UE plugin uses "size"
        if node.width is not None or node.height is not None:
            commands.append({
                "cmd": "set_widget_property",
                "widget": widget_bp_name,
                "child": node.name,
                "property": "size",
                "value": {
                    "x": node.width or 0,
                    "y": node.height or 0,
                },
            })
        
        # Set all other properties
        for prop, value in node.properties.items():
            commands.append({
                "cmd": "set_widget_property",
                "widget": widget_bp_name,
                "child": node.name,
                "property": prop,
                "value": value,
            })
        
        # Recurse children
        for child in node.children:
            walk(child, node.name)

    walk(root, is_root=True)
    
    return commands


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def translate_html_to_widget(html: str, widget_name: str = "WBP_Generated",
                              root_selector: str = None) -> dict:
    """
    Translate an HTML string into UE Widget Blueprint commands.
    
    Args:
        html: The HTML string (can be a full page or a fragment)
        widget_name: Name for the generated Widget Blueprint
        root_selector: CSS selector for the root element to translate
                       (default: first <body> child or first element)
    
    Returns:
        {
            "widget_name": "WBP_Generated",
            "commands": [...],          # List of TCP/MCP commands
            "widget_count": 12,         # Total widgets created
            "tree": {...},              # Debug: widget tree structure
            "warnings": [...]           # Any translation warnings
        }
    """
    _reset_names()
    warnings = []
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Extract embedded CSS
    class_styles = extract_embedded_styles(soup)
    
    # Find root element
    root_element = None
    if root_selector:
        root_element = soup.select_one(root_selector)
    if not root_element:
        body = soup.find("body")
        if body:
            # Find first meaningful child of body
            for child in body.children:
                if isinstance(child, Tag) and child.name not in ("script", "style", "link", "meta"):
                    root_element = child
                    break
        if not root_element:
            # Use first div or container
            root_element = soup.find(["div", "section", "main", "header", "nav"])
    if not root_element:
        # Last resort: wrap everything
        root_element = soup
    
    # Convert to widget tree
    widget_tree = html_element_to_widget(root_element, class_styles)
    
    if not widget_tree:
        return {
            "widget_name": widget_name,
            "commands": [],
            "widget_count": 0,
            "tree": None,
            "warnings": ["Could not parse any widgets from the HTML"],
        }
    
    # If root isn't a CanvasPanel, wrap it
    if widget_tree.widget_type != "CanvasPanel":
        wrapper = WidgetNode(
            widget_type="CanvasPanel",
            name="RootCanvas",
            children=[widget_tree],
        )
        widget_tree.parent = "RootCanvas"
        widget_tree = wrapper
    
    # Generate commands
    commands = widget_tree_to_commands(widget_tree, widget_name)
    
    # Count widgets
    def count_nodes(node):
        return 1 + sum(count_nodes(c) for c in node.children)
    
    widget_count = count_nodes(widget_tree)
    
    # Build debug tree
    def tree_to_dict(node):
        d = {
            "type": node.widget_type,
            "name": node.name,
            "properties": node.properties,
        }
        if node.pos_x is not None: d["x"] = node.pos_x
        if node.pos_y is not None: d["y"] = node.pos_y
        if node.width is not None: d["width"] = node.width
        if node.height is not None: d["height"] = node.height
        if node.children:
            d["children"] = [tree_to_dict(c) for c in node.children]
        return d
    
    return {
        "widget_name": widget_name,
        "commands": commands,
        "widget_count": widget_count,
        "tree": tree_to_dict(widget_tree),
        "warnings": warnings,
    }


def execute_commands(commands: list, client) -> dict:
    """Execute widget commands against a BlueprintLLM client."""
    results = {"success": 0, "failed": 0, "errors": []}

    for cmd in commands:
        try:
            if cmd["cmd"] == "create_widget_blueprint":
                client.create_widget_blueprint(cmd["name"])
            elif cmd["cmd"] == "add_widget_child":
                client.add_widget_child(
                    cmd["widget"], cmd["type"], cmd["name"],
                    parent_widget=cmd.get("parent", "")
                )
            elif cmd["cmd"] == "set_widget_property":
                client.set_widget_property(
                    cmd["widget"], cmd["child"],
                    cmd["property"], cmd["value"]
                )
            results["success"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{cmd['cmd']} {cmd.get('name', '')}: {e}")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    ap = argparse.ArgumentParser(description="Arcwright HTML → UE Widget Translator")
    ap.add_argument("input", nargs="?", help="HTML file to translate")
    ap.add_argument("--html", help="HTML string to translate")
    ap.add_argument("--name", default="WBP_Generated", help="Widget Blueprint name")
    ap.add_argument("--selector", help="CSS selector for root element")
    ap.add_argument("--output", "-o", help="Save commands as JSON")
    ap.add_argument("--tree", action="store_true", help="Print widget tree")
    ap.add_argument("--execute", action="store_true", help="Execute against UE (requires running server)")
    args = ap.parse_args()
    
    if args.html:
        html = args.html
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            html = f.read()
    else:
        ap.print_help()
        return
    
    result = translate_html_to_widget(html, widget_name=args.name, root_selector=args.selector)
    
    print(f"\nWidget Blueprint: {result['widget_name']}")
    print(f"Widgets: {result['widget_count']}")
    print(f"Commands: {len(result['commands'])}")
    
    if result["warnings"]:
        print(f"\nWarnings:")
        for w in result["warnings"]:
            print(f"  ⚠️ {w}")
    
    if args.tree and result["tree"]:
        print(f"\nWidget Tree:")
        print(json.dumps(result["tree"], indent=2))
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result["commands"], f, indent=2)
        print(f"\nSaved {len(result['commands'])} commands to {args.output}")
    
    if args.execute:
        print("\nExecuting commands...")
        import sys
        sys.path.insert(0, "scripts/mcp_client")
        from blueprint_client import ArcwrightClient
        with ArcwrightClient() as client:
            exec_result = execute_commands(result["commands"], client)
            print(f"  Success: {exec_result['success']}")
            print(f"  Failed: {exec_result['failed']}")
            for err in exec_result["errors"]:
                print(f"  ❌ {err}")


if __name__ == "__main__":
    main()
