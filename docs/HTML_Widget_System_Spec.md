# Arcwright — HTML to UE Widget System

> **Feature:** Design game UIs in HTML/CSS, auto-translate to UE Widget Blueprints
> **Status:** Parser complete, needs MCP integration and Claude Desktop workflow

---

## 1. What This Enables

Claude is exceptional at designing HTML/CSS interfaces. UE Widget Blueprints are tedious to build manually. This system bridges the gap:

1. User says: "Design a sci-fi shooter HUD with health, ammo, minimap, and ability bar"
2. Claude designs a beautiful HTML mockup (its strongest visual medium)
3. The translator converts it to UE Widget Blueprint commands
4. The widget appears in-game looking exactly like the HTML design

**This gives Arcwright AI-designed game UIs** — something no other tool offers.

---

## 2. How It Works

### HTML Conventions for Game UIs

The HTML mockup should follow these conventions for best translation:

**Use `data-widget-name` for important widgets:**
```html
<p class="score" data-widget-name="ScoreText">0</p>
```
This controls the widget name in UE — essential for binding to game variables later.

**Use `data-widget="progress"` for health/mana bars:**
```html
<div class="health-bar" data-widget="progress" data-percent="75">
    <div class="fill" style="width: 75%; background-color: #00ff88;"></div>
</div>
```
The translator detects this and creates a ProgressBar instead of a container.

**Use absolute positioning for HUD layout:**
```html
<div style="position: absolute; left: 40px; top: 30px;">
```
Game HUDs use absolute positioning. The translator maps `left`/`top` to CanvasPanel slot positions.

**Design at 1920x1080:**
The root container should be 1920x1080 (standard game resolution). All positions are in pixels.

### Supported CSS → Widget Mappings

| CSS Property | UE Widget Property | Notes |
|---|---|---|
| `color` | TextBlock color | Supports hex, rgb, rgba, named colors |
| `font-size` | TextBlock font_size | Pixels |
| `font-weight: bold` | TextBlock font_weight | Bold |
| `text-align` | TextBlock justification | Left, Center, Right |
| `background-color` | Background brush / fill_color | On containers and progress bars |
| `opacity` | Render opacity | 0.0 - 1.0 |
| `width` / `height` | Slot size | px, %, vw, vh supported |
| `left` / `top` | Slot position (CanvasPanel) | Absolute positioning |
| `right` / `bottom` | Calculated slot position | Converted to left/top |
| `display: flex` | HorizontalBox / VerticalBox | Based on flex-direction |
| `display: grid` | UniformGridPanel | Approximate |
| `visibility: hidden` | Widget visibility | Hidden |
| `padding` | Slot padding | Uniform or per-side |

### Element → Widget Mappings

| HTML Tag | UE Widget | When |
|---|---|---|
| `<div>` | CanvasPanel | position: absolute/relative |
| `<div>` | VerticalBox | display: block (default) |
| `<div>` | HorizontalBox | display: flex; flex-direction: row |
| `<h1>`-`<h6>` | TextBlock | With preset font sizes |
| `<p>`, `<span>` | TextBlock | |
| `<button>` | Button | |
| `<img>` | Image | |
| `<input>` | EditableText | |
| `<div data-widget="progress">` | ProgressBar | Health, mana, XP bars |

---

## 3. Integration Points

### MCP Tool: `create_widget_from_html`

```python
# New MCP tool
@tool("create_widget_from_html")
def create_widget_from_html(html: str, widget_name: str = "WBP_Generated"):
    """Create a UE Widget Blueprint from an HTML mockup."""
    result = translate_html_to_widget(html, widget_name)
    execute_commands(result["commands"], ue_client)
    return {
        "widget_name": widget_name,
        "widget_count": result["widget_count"],
        "commands_executed": len(result["commands"]),
    }
```

### Claude Desktop Workflow

```
User: "Design a fantasy RPG HUD with health, mana, gold counter, and quest tracker"

Claude: [designs HTML mockup internally]
        [calls create_widget_from_html with the HTML]
        [UE creates the widget]

"I've created WBP_RPGHUD with 28 widgets including health/mana bars, 
 gold counter, and quest tracker. The health bar is green, mana is blue, 
 gold is displayed in the top-right."
```

### Claude API Workflow (Arcwright Cloud)

```
POST /v1/generate
{
    "domain": "widget",
    "prompt": "Design a sci-fi shooter HUD with health, shields, ammo, minimap, and ability cooldowns",
    "options": {
        "format": "widget_commands"
    }
}

Response:
{
    "html_design": "<div class='hud-root'>...",
    "widget_name": "WBP_SciFiHUD",
    "commands": [...],
    "widget_count": 34
}
```

---

## 4. Supported HUD Patterns

### Shooter HUD
- Health bar (top-left)
- Shield bar (below health)
- Ammo counter (bottom-right)
- Crosshair (center)
- Minimap (top-right corner)
- Kill feed (right side, scrolling)
- Ability bar (bottom-center)

### RPG HUD
- Health/Mana bars (top-left)
- Character portrait (top-left)
- Action bar (bottom-center, horizontal slots)
- Quest tracker (right side)
- Gold/inventory counters (top-right)
- Minimap (corner)
- Dialogue box (bottom, full width)

### Racing HUD
- Speedometer (bottom-center, large)
- Lap counter (top-center)
- Position display (top-left)
- Timer (top-right)
- Minimap (corner, track layout)

### Survival HUD
- Health, hunger, thirst bars (bottom-left, vertical)
- Hotbar (bottom-center)
- Temperature indicator
- Compass (top-center)
- Day counter

---

## 5. Limitations and Workarounds

| Limitation | Workaround |
|---|---|
| No CSS animations | Map to UE widget animations in a post-process step |
| No CSS gradients on text | Use Image widget with gradient texture behind text |
| Limited font choices | Map to UE project fonts; Roboto is default |
| No SVG support | Use Image widget with imported SVG-to-PNG |
| No scrolling containers | Use ScrollBox widget type (add as special case) |
| No rounded corners | Approximate with Border widget + brush |
| No CSS grid precise control | UniformGridPanel approximates; manual adjustment may be needed |

---

## 6. File Locations

| File | Location | Purpose |
|---|---|---|
| `html_to_widget.py` | `scripts/html_to_widget/` | Core translator |
| Test HUD HTMLs | `scripts/html_to_widget/templates/` | Example HTML designs |
| Generated commands | Output JSON | For debugging/replay |

---

*This feature transforms Arcwright from "describe UIs in text" to "design UIs visually" — a massive leap in UI quality.*
