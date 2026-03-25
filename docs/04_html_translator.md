# HTML to UE Widget Translator

Arcwright includes a translator that converts HTML/CSS mockups into UE5 Widget Blueprints. Design your game UI in HTML -- the medium where AI assistants produce their best visual work -- and Arcwright translates it into a fully functional UMG widget hierarchy inside the running editor.

---

## How It Works

```
1. You (or your AI) design a UI in HTML/CSS
2. Arcwright parses the HTML structure and CSS styles
3. The translator maps HTML elements to UE widget types
4. CSS properties become UMG widget properties
5. The result is a Widget Blueprint in UE5 with the exact layout
```

This is particularly powerful with AI assistants like Claude, which can design sophisticated HTML interfaces and then immediately translate them to UE widgets through Arcwright.

---

## Quick Example

Ask your AI assistant:

> "Design a sci-fi shooter HUD with health, shields, ammo, and a minimap, then create it in Unreal."

The AI designs an HTML mockup, then calls `create_widget_from_html`:

```json
{
  "command": "create_widget_from_html",
  "params": {
    "html": "<div class='hud-root' style='width:1920px;height:1080px;position:relative;'><div style='position:absolute;left:40px;top:30px;'><p style='color:#3DDC84;font-size:18px;'>HEALTH</p><div data-widget='progress' data-percent='85' style='width:250px;height:12px;'><div class='fill' style='width:85%;background-color:#3DDC84;'></div></div></div><div style='position:absolute;right:40px;bottom:40px;'><p style='color:#E8A624;font-size:36px;font-weight:bold;' data-widget-name='txt_AmmoCount'>30</p><p style='color:#707888;font-size:14px;'>/ 120</p></div></div>",
    "widget_name": "WBP_SciFiHUD"
  }
}
```

The widget appears in your UE5 Content Browser, ready to use.

---

## Design Guidelines

### Design at 1920x1080

All widget blueprints default to a 1920x1080 design size. Design your HTML mockup at this resolution. All pixel positions map directly to UE canvas slot positions.

```html
<div style="width: 1920px; height: 1080px; position: relative;">
    <!-- Your HUD elements go here -->
</div>
```

### Use absolute positioning for HUD elements

Game HUDs use absolute positioning. The translator maps `left`/`top` CSS properties to CanvasPanel slot positions.

```html
<div style="position: absolute; left: 40px; top: 30px;">
    <p style="color: #3DDC84; font-size: 18px;">HEALTH</p>
</div>
```

### Use `data-widget-name` for bindable widgets

Any widget you plan to update from game code needs a stable name. Use the `data-widget-name` attribute to control the UE widget name:

```html
<p data-widget-name="txt_Score" style="color: #E8A624; font-size: 24px;">0</p>
```

This creates a TextBlock named `txt_Score` in UE that your Blueprint or C++ code can find and update at runtime.

### Use `data-widget="progress"` for bars

Health bars, mana bars, XP bars, and similar progress indicators should use the `data-widget` attribute:

```html
<div data-widget="progress" data-percent="75" style="width: 250px; height: 12px;">
    <div class="fill" style="width: 75%; background-color: #3DDC84;"></div>
</div>
```

The translator creates a `ProgressBar` widget instead of a container, and sets the initial percent and fill color from the CSS.

---

## Color Support

### hex:#RRGGBB (recommended)

Use standard hex colors in your HTML. When the translator generates `set_widget_property` commands, it passes colors with the `hex:` prefix, which tells the plugin to automatically convert from sRGB to linear color space.

```html
<p style="color: #E8A624;">Gold Text</p>
<div style="background-color: #0A0C0F;"></div>
```

The translator outputs:

```json
{"command": "set_widget_property", "params": {"widget_name": "GoldText", "property_name": "color", "value": "hex:#E8A624"}}
```

### Supported CSS color formats

| CSS Format | Example | Supported |
|---|---|---|
| Hex 6-digit | `#E8A624` | Yes |
| Hex 3-digit | `#F00` | Yes (expanded to 6-digit) |
| rgb() | `rgb(232, 166, 36)` | Yes |
| rgba() | `rgba(232, 166, 36, 0.8)` | Yes |
| Named colors | `red`, `white`, `blue` | Yes (common names) |
| hsl() | `hsl(40, 80%, 52%)` | No |

---

## Element to Widget Mappings

| HTML Element | UE Widget | Conditions |
|---|---|---|
| `<div>` | CanvasPanel | Has `position: absolute` or `position: relative` |
| `<div>` | VerticalBox | Default block layout |
| `<div>` | HorizontalBox | Has `display: flex; flex-direction: row` |
| `<div>` | UniformGridPanel | Has `display: grid` |
| `<div data-widget="progress">` | ProgressBar | Explicit progress bar |
| `<h1>` through `<h6>` | TextBlock | With preset font sizes (h1=32, h2=28, h3=24, h4=20, h5=16, h6=14) |
| `<p>`, `<span>` | TextBlock | Standard text |
| `<button>` | Button | Interactive button |
| `<img>` | Image | Image display |
| `<input>` | EditableText | Text input |

---

## CSS to Widget Property Mappings

| CSS Property | UE Widget Property | Notes |
|---|---|---|
| `color` | TextBlock color | Hex, rgb, rgba, named colors |
| `font-size` | TextBlock font_size | In pixels |
| `font-weight: bold` | TextBlock font_weight | Bold weight |
| `text-align` | TextBlock justification | left, center, right |
| `background-color` | Background brush / fill_color | On containers and progress bars |
| `opacity` | Render opacity | 0.0 to 1.0 |
| `width` / `height` | Slot size | px, %, vw, vh supported |
| `left` / `top` | Slot position | CanvasPanel absolute positioning |
| `right` / `bottom` | Calculated slot position | Converted to left/top based on parent size |
| `display: flex` | HorizontalBox / VerticalBox | Based on flex-direction |
| `visibility: hidden` | Widget visibility | Maps to Hidden |
| `padding` | Slot padding | Uniform or per-side (top, right, bottom, left) |

---

## Complete HUD Example

Here is a full HTML mockup for a shooter HUD and the resulting Arcwright commands:

### The HTML

```html
<div style="width: 1920px; height: 1080px; position: relative; font-family: sans-serif;">
    <!-- Health (top-left) -->
    <div style="position: absolute; left: 40px; top: 30px;">
        <p style="color: #707888; font-size: 12px; text-transform: uppercase;">Health</p>
        <div data-widget="progress" data-percent="100"
             style="width: 250px; height: 8px; margin-top: 4px;">
            <div class="fill" style="width: 100%; background-color: #3DDC84;"></div>
        </div>
        <p data-widget-name="txt_HealthValue"
           style="color: #D0D4DC; font-size: 24px; font-weight: bold; margin-top: 2px;">100</p>
    </div>

    <!-- Ammo (bottom-right) -->
    <div style="position: absolute; right: 60px; bottom: 50px; text-align: right;">
        <p data-widget-name="txt_AmmoCount"
           style="color: #EEF0F4; font-size: 48px; font-weight: bold;">30</p>
        <p data-widget-name="txt_AmmoReserve"
           style="color: #707888; font-size: 18px;">/ 120</p>
    </div>

    <!-- Score (top-right) -->
    <div style="position: absolute; right: 40px; top: 30px; text-align: right;">
        <p style="color: #707888; font-size: 12px;">SCORE</p>
        <p data-widget-name="txt_Score"
           style="color: #E8A624; font-size: 28px; font-weight: bold;">0</p>
    </div>

    <!-- Crosshair (center) -->
    <div style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);">
        <p style="color: rgba(255,255,255,0.6); font-size: 24px;">+</p>
    </div>
</div>
```

### What the translator produces

The translator converts this into a sequence of Arcwright TCP commands:

1. `create_widget_blueprint` -- creates `WBP_ShooterHUD` at 1920x1080
2. `add_widget_child` -- adds CanvasPanel root
3. `add_widget_child` -- adds each container and text element
4. `set_widget_property` -- sets colors (using `hex:` prefix), font sizes, positions, text content
5. `protect_widget_layout` -- locks the visual layer so only `txt_*` widgets are modifiable from code

---

## Supported HUD Patterns

The translator handles these common game UI patterns:

### Shooter HUD
- Health/shield bars (top-left)
- Ammo counter (bottom-right)
- Crosshair (center)
- Kill feed (right side)
- Minimap placeholder (top-right)
- Ability cooldowns (bottom-center)

### RPG HUD
- Health/mana bars (top-left)
- Character portrait (top-left)
- Action bar with slots (bottom-center)
- Quest tracker (right side)
- Gold/inventory counters (top-right)

### Racing HUD
- Speedometer (bottom-center)
- Lap counter (top-center)
- Position indicator (top-left)
- Timer (top-right)

### Survival HUD
- Health/hunger/thirst bars (bottom-left, vertical stack)
- Hotbar (bottom-center)
- Temperature indicator
- Compass (top-center)

---

## Limitations

| Limitation | Workaround |
|---|---|
| No CSS animations | Use UE widget animations in a post-build step |
| No CSS gradients | Use an Image widget with a gradient texture |
| Limited font choices | Maps to Roboto (UE default); import custom fonts separately |
| No SVG support | Convert SVGs to PNG and use Image widgets |
| No scrolling in HTML | Use ScrollBox widget type via `data-widget="scrollbox"` |
| No rounded corners | Approximate with Border widget and brush styling |
| No precise CSS grid | UniformGridPanel approximates; manual adjustment may be needed |

---

## Post-Translation: protect_widget_layout

After the translator builds the widget hierarchy, call `protect_widget_layout` to lock the visual structure. This ensures that only text (`txt_*`) and button (`Btn_*`) widgets remain accessible from Blueprint/C++ code, preventing accidental layout modifications at runtime:

```json
{"command": "protect_widget_layout", "params": {"widget_blueprint": "WBP_ShooterHUD"}}
```

---

## Workflow Summary

1. Design your UI in HTML/CSS (or have your AI assistant design it).
2. Call `create_widget_from_html` with the HTML string and a widget name.
3. The translator creates the Widget Blueprint with the full hierarchy.
4. Call `protect_widget_layout` to lock the visual layer.
5. Bind `txt_*` widgets to game variables in your Blueprint or C++ code.
6. Add the widget to the viewport at runtime via `CreateWidget` + `AddToViewport`.
