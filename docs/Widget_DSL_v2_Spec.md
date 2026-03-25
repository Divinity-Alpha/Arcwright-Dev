# Widget DSL v2 — Arcwright UI Builder Specification

> **Version:** 2.0-draft
> **Date:** 2026-03-17
> **Status:** Design spec — not yet implemented
> **Replaces:** HTML-to-Widget translator (scripts/html_to_widget/)
> **Purpose:** A purpose-built DSL for generating production-quality UE5 Widget Blueprints with themes, animations, bindings, and style systems.

---

## 1. Why a New DSL

The HTML-to-Widget translator was a proof of concept. It works but has fundamental limits:
- HTML/CSS doesn't map cleanly to UMG's layout model (anchors, slots, Canvas Panel positioning)
- No concept of UE-specific features: widget animations, property bindings, brush materials, slate fonts
- No style system — every widget is styled individually
- No theme support — can't swap "Sci-Fi" to "Medieval" without rewriting everything
- No animation specification
- No data binding specification

Widget DSL v2 is designed from the ground up for UE5's Widget system. It's what the LLM learns to generate.

---

## 2. DSL Format Overview

```
WIDGET: WBP_GameHUD
THEME: SciFi
PALETTE:
  primary=#00D4FF
  accent=#FF3A5C
  background=#0A1628
  text=#E0E8F0
  success=#2AAA55
  danger=#FF3A5C
  warning=#F59E0B

ROOT: CanvasPanel
  @anchor=Fill

  -- Top Left: Health System --
  OVERLAY: HealthSection
    @anchor=TopLeft
    @offset=20,20
    @size=300,80

    HORIZONTAL_BOX: HealthRow
      @valign=Center

      IMAGE: HealthIcon
        @brush=Icon_Health
        @size=28,28
        @tint=$accent
        @margin=0,0,8,0

      VERTICAL_BOX: HealthBars
        @fill=1.0

        PROGRESS_BAR: HealthBar
          @percent=BIND:PlayerHealth/MaxHealth
          @fill_color=$accent
          @bg_color=$background:0.6
          @size=0,20
          @fill=1.0
          @corner_radius=4
          @anim:OnDamage=Shake|duration=0.3|intensity=4

        SPACER: @height=4

        PROGRESS_BAR: ShieldBar
          @percent=BIND:PlayerShield/MaxShield
          @fill_color=$primary
          @bg_color=$background:0.4
          @size=0,12
          @fill=1.0
          @corner_radius=2
          @visible=BIND:HasShield

      SPACER: @width=12

      TEXT: HealthValue
        @text=BIND:"{PlayerHealth}"
        @font=$heading
        @size=24
        @color=$text
        @anim:OnChange=Pulse|duration=0.2|scale=1.15

  -- Top Right: Score --
  BORDER: ScorePanel
    @anchor=TopRight
    @offset=-20,20
    @size=200,80
    @brush=$panel_bg
    @corner_radius=8
    @padding=16

    VERTICAL_BOX: ScoreLayout
      @halign=Right

      TEXT: ScoreLabel
        @text="SCORE"
        @font=$label
        @size=11
        @color=$primary
        @letter_spacing=4

      TEXT: ScoreValue
        @text=BIND:Score
        @font=$heading
        @size=32
        @color=$text
        @anim:OnScoreUp=CountUp|duration=0.5

  -- Center: Crosshair --
  OVERLAY: Crosshair
    @anchor=Center
    @size=48,48

    IMAGE: CrosshairDot
      @brush=Crosshair_Dot
      @size=4,4
      @tint=$primary:0.9
      @halign=Center
      @valign=Center

    IMAGE: CrosshairLines
      @brush=Crosshair_Lines
      @size=24,24
      @tint=$primary:0.5
      @halign=Center
      @valign=Center
      @anim:OnFire=Expand|duration=0.15|scale=1.4|ease=EaseOut

  -- Bottom Right: Ammo --
  BORDER: AmmoPanel
    @anchor=BottomRight
    @offset=-20,-20
    @size=180,90
    @brush=$panel_bg
    @corner_radius=6
    @padding=12

    VERTICAL_BOX: AmmoLayout
      @halign=Right

      TEXT: AmmoCount
        @text=BIND:"{CurrentAmmo} / {MaxAmmo}"
        @font=$heading
        @size=28
        @color=$text
        @anim:OnReload=Flash|duration=0.8|color=$warning

      TEXT: WeaponName
        @text=BIND:WeaponName
        @font=$body
        @size=14
        @color=$primary

  -- Full Screen: Damage Effects --
  IMAGE: DamageVignette
    @anchor=Fill
    @brush=FX_Vignette_Damage
    @tint=$danger
    @opacity=0
    @anim:OnDamage=FadeInOut|duration=0.4|peak_opacity=0.6
    @hit_test=Invisible
```

---

## 3. Syntax Rules

### 3.1 Document Header

Every Widget DSL document starts with:

```
WIDGET: <WidgetBlueprintName>
THEME: <ThemeName>
PALETTE:
  <color_name>=<hex_value>
  ...
```

- `WIDGET` — name of the Widget Blueprint to create (e.g., WBP_GameHUD)
- `THEME` — theme identifier (SciFi, Medieval, Racing, Fighting, Simulation, Normal, Horror, Cartoon)
- `PALETTE` — color overrides. Theme provides defaults; palette overrides specific colors.

### 3.2 Widget Tree

Widgets are defined by indentation (2 spaces per level):

```
TYPE: Name
  @property=value
  CHILD_TYPE: ChildName
    @property=value
```

- `TYPE` — UE widget class (see Section 4)
- `Name` — unique name for this widget instance
- Properties start with `@`
- Children are indented under their parent
- Comments start with `--`

### 3.3 Property Types

| Syntax | Type | Example |
|---|---|---|
| `@size=200,80` | Vector2D (width,height) | Fixed size |
| `@offset=20,20` | Vector2D (x,y) | Position offset from anchor |
| `@color=#FF3A5C` | Hex color | Direct color |
| `@color=$accent` | Theme color reference | Resolved from palette |
| `@color=$primary:0.5` | Theme color + opacity | Color with alpha override |
| `@opacity=0.8` | Float 0-1 | Transparency |
| `@visible=true` | Boolean | Visibility |
| `@visible=BIND:HasShield` | Binding | Dynamic visibility |
| `@text="SCORE"` | String literal | Static text |
| `@text=BIND:Score` | Binding | Dynamic text from variable |
| `@text=BIND:"{Current}/{Max}"` | Format binding | Template with multiple variables |
| `@percent=BIND:Health/MaxHealth` | Expression binding | Division evaluated at runtime |
| `@font=$heading` | Theme font reference | Resolved from theme |
| `@font=Orbitron` | Direct font name | Specific font |
| `@brush=Icon_Health` | Texture/material name | UI asset reference |
| `@brush=$panel_bg` | Theme brush reference | Resolved from theme |
| `@fill=1.0` | Float | Slot fill weight (like CSS flex-grow) |
| `@margin=10,5,10,5` | 4-value (L,T,R,B) | Margin/padding |
| `@padding=16` | Single value (all sides) | Uniform padding |
| `@corner_radius=8` | Float | Rounded corners on Border |
| `@letter_spacing=4` | Float | Text letter spacing |

### 3.4 Anchor System

Anchors define where a widget attaches to its parent Canvas Panel:

| Anchor | Meaning | UE Equivalent |
|---|---|---|
| `TopLeft` | Fixed top-left | Anchor(0,0) Alignment(0,0) |
| `TopCenter` | Fixed top-center | Anchor(0.5,0) Alignment(0.5,0) |
| `TopRight` | Fixed top-right | Anchor(1,0) Alignment(1,0) |
| `CenterLeft` | Fixed center-left | Anchor(0,0.5) Alignment(0,0.5) |
| `Center` | Fixed center | Anchor(0.5,0.5) Alignment(0.5,0.5) |
| `CenterRight` | Fixed center-right | Anchor(1,0.5) Alignment(1,0.5) |
| `BottomLeft` | Fixed bottom-left | Anchor(0,1) Alignment(0,1) |
| `BottomCenter` | Fixed bottom-center | Anchor(0.5,1) Alignment(0.5,1) |
| `BottomRight` | Fixed bottom-right | Anchor(1,1) Alignment(1,1) |
| `TopFill` | Stretches horizontally, fixed top | Anchor(0,0)-(1,0) |
| `BottomFill` | Stretches horizontally, fixed bottom | Anchor(0,1)-(1,1) |
| `LeftFill` | Stretches vertically, fixed left | Anchor(0,0)-(0,1) |
| `RightFill` | Stretches vertically, fixed right | Anchor(1,0)-(1,1) |
| `Fill` | Stretches both directions | Anchor(0,0)-(1,1) |

### 3.5 Alignment

```
@halign=Left|Center|Right|Fill
@valign=Top|Center|Bottom|Fill
```

These control how a child aligns within its parent slot.

### 3.6 Data Bindings

Bindings connect widget properties to game variables at runtime.

```
@text=BIND:VariableName                    -- simple variable
@text=BIND:"{Current}/{Max}"               -- format string with multiple vars
@percent=BIND:Health/MaxHealth              -- expression (division)
@visible=BIND:HasShield                    -- boolean binding
@tint=BIND:TeamColor                       -- color binding
@opacity=BIND:IF(IsLowHealth,1.0,0.0)     -- conditional
```

**Binding resolution:** The parser generates UE Property Bindings in the Widget Blueprint. The user's game code sets the variables on the Widget instance. Standard UE binding pattern.

**Generated binding interface:**
```
WIDGET: WBP_GameHUD generates:
  - VARIABLE: PlayerHealth Float 100.0
  - VARIABLE: MaxHealth Float 100.0
  - VARIABLE: PlayerShield Float 50.0
  - VARIABLE: MaxShield Float 50.0
  - VARIABLE: HasShield Bool true
  - VARIABLE: Score Integer 0
  - VARIABLE: CurrentAmmo Integer 30
  - VARIABLE: MaxAmmo Integer 30
  - VARIABLE: WeaponName String "M4A1"
  - FUNCTION: UpdateHealth(NewHealth, NewMax)
  - FUNCTION: UpdateAmmo(Current, Max, WeaponName)
  - FUNCTION: TriggerDamageEffect()
  - FUNCTION: TriggerScorePopup(Points)
```

### 3.7 Animations

Animations are defined inline on any widget:

```
@anim:TriggerName=AnimType|param=value|param=value
```

**Trigger names** (when the animation plays):
| Trigger | When It Fires |
|---|---|
| `OnDamage` | Player takes damage |
| `OnHeal` | Player heals |
| `OnChange` | Bound value changes |
| `OnScoreUp` | Score increases |
| `OnFire` | Weapon fires |
| `OnReload` | Weapon reloads |
| `OnLowHealth` | Health below 25% (loops) |
| `OnShow` | Widget becomes visible |
| `OnHide` | Widget becomes hidden |
| `OnHover` | Mouse enters (menus) |
| `OnPress` | Button pressed |
| `OnAppear` | Widget first added to viewport |
| `Custom:EventName` | Custom game event |

**Animation types:**
| Type | Parameters | Effect |
|---|---|---|
| `Shake` | duration, intensity | Rapid position oscillation |
| `Pulse` | duration, scale, count | Scale up and back |
| `Flash` | duration, color | Color flash then revert |
| `FadeIn` | duration, ease | Opacity 0→1 |
| `FadeOut` | duration, ease | Opacity 1→0 |
| `FadeInOut` | duration, peak_opacity | Opacity 0→peak→0 |
| `SlideIn` | duration, from(Left/Right/Top/Bottom), distance | Slide from offscreen |
| `SlideOut` | duration, to(Left/Right/Top/Bottom), distance | Slide to offscreen |
| `Expand` | duration, scale, ease | Scale up from center |
| `Shrink` | duration, scale, ease | Scale down to center |
| `CountUp` | duration | Numeric text counts from old to new value |
| `CountDown` | duration | Numeric text counts from old to new value |
| `Spin` | duration, degrees | Rotation |
| `Bounce` | duration, height, count | Vertical bounce |
| `Glow` | duration, color, intensity | Outer glow effect |
| `Typewriter` | duration, chars_per_sec | Text reveals character by character |
| `ColorShift` | duration, from_color, to_color | Smooth color transition |

**Ease options:** Linear, EaseIn, EaseOut, EaseInOut, Bounce, Elastic

---

## 4. Widget Types

### 4.1 Layout Widgets

| DSL Type | UE Class | Purpose |
|---|---|---|
| `CANVAS_PANEL` | UCanvasPanel | Absolute positioning container |
| `HORIZONTAL_BOX` | UHorizontalBox | Horizontal child layout |
| `VERTICAL_BOX` | UVerticalBox | Vertical child layout |
| `OVERLAY` | UOverlay | Stacked children (same position) |
| `GRID_PANEL` | UGridPanel | Row/column grid |
| `UNIFORM_GRID` | UUniformGridPanel | Equal-sized grid cells |
| `SIZE_BOX` | USizeBox | Force specific size on child |
| `SCALE_BOX` | UScaleBox | Scale child to fit |
| `SCROLL_BOX` | UScrollBox | Scrollable container |
| `WRAP_BOX` | UWrapBox | Wrapping flow layout |
| `WIDGET_SWITCHER` | UWidgetSwitcher | Show one child at a time (tabs) |
| `SPACER` | USpacer | Empty space |
| `SAFE_ZONE` | USafeZone | Respects screen safe area |

### 4.2 Visual Widgets

| DSL Type | UE Class | Purpose |
|---|---|---|
| `TEXT` | UTextBlock | Static or bound text |
| `RICH_TEXT` | URichTextBlock | Styled text with inline formatting |
| `IMAGE` | UImage | Texture, material, or solid color |
| `BORDER` | UBorder | Background + single child container |
| `PROGRESS_BAR` | UProgressBar | Fill bar (health, ammo, XP, cooldown) |
| `CIRCULAR_BAR` | UMaterialProgressBar* | Circular fill (cooldowns, radial menus) |
| `THROBBER` | UThrobber | Loading spinner |
| `SEPARATOR` | USeparator* | Visual divider line |

*Custom implementations where UE doesn't have a direct equivalent

### 4.3 Interactive Widgets

| DSL Type | UE Class | Purpose |
|---|---|---|
| `BUTTON` | UButton | Clickable button with child content |
| `CHECKBOX` | UCheckBox | Toggle |
| `COMBO_BOX` | UComboBoxString | Dropdown selector |
| `SLIDER` | USlider | Numeric slider |
| `SPIN_BOX` | USpinBox | Numeric input with arrows |
| `TEXT_INPUT` | UEditableTextBox | Text entry field |
| `MULTI_LINE_INPUT` | UMultiLineEditableText | Multi-line text entry |

### 4.4 Special Widgets

| DSL Type | Purpose |
|---|---|
| `MINIMAP` | Generates a minimap system (render target + camera + widget) |
| `INVENTORY_GRID` | Generates a grid inventory with slots, drag-drop, tooltips |
| `ABILITY_BAR` | Horizontal bar of ability slots with cooldown overlays |
| `DIALOG_BOX` | Text box with character name, portrait, and typewriter reveal |
| `NOTIFICATION` | Popup notification that slides in and auto-fades |
| `DAMAGE_NUMBER` | Floating damage number that rises and fades |
| `COMPASS` | Top-of-screen compass with cardinal directions and markers |
| `INTERACTION_PROMPT` | "Press E to interact" contextual prompt |
| `KILL_FEED` | Scrolling kill/event feed |
| `OBJECTIVE_TRACKER` | Quest/objective list with progress |
| `TAB_PANEL` | Tabbed container with tab buttons |
| `TOOLTIP` | Hover tooltip for items/abilities |

Special widgets are compound — the parser expands them into multiple standard widgets with pre-built logic.

---

## 5. Theme System

### 5.1 Theme Definition File

Each theme is a JSON file that defines the complete design system:

```json
{
  "theme_name": "SciFi",
  "display_name": "Sci-Fi",
  "description": "Neon accents on dark backgrounds. Sharp edges, holographic effects, grid overlays.",

  "palette": {
    "primary": "#00D4FF",
    "secondary": "#1A2A4A",
    "accent": "#FF3A5C",
    "background": "#0A1628",
    "surface": "#12203A",
    "text": "#E0E8F0",
    "text_secondary": "#607090",
    "success": "#2AAA55",
    "danger": "#FF3A5C",
    "warning": "#F59E0B"
  },

  "typography": {
    "heading": {
      "font": "Orbitron",
      "weight": "Bold",
      "letter_spacing": 2
    },
    "body": {
      "font": "Rajdhani",
      "weight": "Regular",
      "letter_spacing": 0
    },
    "label": {
      "font": "JetBrains Mono",
      "weight": "Regular",
      "letter_spacing": 3,
      "transform": "uppercase"
    },
    "value": {
      "font": "Orbitron",
      "weight": "Bold",
      "letter_spacing": 1
    }
  },

  "shapes": {
    "corner_radius": 4,
    "border_width": 1,
    "border_color": "$primary:0.3",
    "panel_padding": 16,
    "element_spacing": 8
  },

  "brushes": {
    "panel_bg": "M_UI_SciFi_Panel",
    "button_normal": "M_UI_SciFi_Button",
    "button_hover": "M_UI_SciFi_Button_Hover",
    "button_pressed": "M_UI_SciFi_Button_Pressed",
    "progress_fill": "M_UI_SciFi_ProgressFill",
    "progress_bg": "M_UI_SciFi_ProgressBG",
    "separator": "M_UI_SciFi_Line",
    "glow": "M_UI_SciFi_Glow",
    "scanlines": "M_UI_SciFi_Scanlines",
    "vignette": "M_UI_SciFi_Vignette"
  },

  "icons": {
    "health": "T_Icon_SciFi_Health",
    "shield": "T_Icon_SciFi_Shield",
    "ammo": "T_Icon_SciFi_Ammo",
    "coin": "T_Icon_SciFi_Coin",
    "key": "T_Icon_SciFi_Key",
    "skull": "T_Icon_SciFi_Skull",
    "star": "T_Icon_SciFi_Star",
    "arrow": "T_Icon_SciFi_Arrow",
    "crosshair_dot": "T_Crosshair_SciFi_Dot",
    "crosshair_lines": "T_Crosshair_SciFi_Lines"
  },

  "animations": {
    "default_duration": 0.3,
    "default_ease": "EaseOut",
    "damage_shake_intensity": 4,
    "low_health_pulse_speed": 1.5,
    "score_countup_duration": 0.5,
    "panel_open": "SlideIn|from=Top|duration=0.3|ease=EaseOut",
    "panel_close": "SlideOut|to=Top|duration=0.2|ease=EaseIn",
    "notification": "SlideIn|from=Right|duration=0.4|ease=Bounce"
  },

  "effects": {
    "scanlines": true,
    "glow_on_active": true,
    "vignette_on_damage": true,
    "holographic_shimmer": true,
    "noise_overlay": false
  }
}
```

### 5.2 Theme Color Resolution

When the DSL uses `$color_name`, it resolves through this chain:
1. Check PALETTE overrides in the DSL document
2. Check theme palette defaults
3. Fallback to Normal theme palette

The `:opacity` suffix modifies alpha: `$primary:0.5` = primary color at 50% opacity.

### 5.3 Initial Themes (8)

| Theme | Palette Vibe | Font Stack | Shape Language |
|---|---|---|---|
| **SciFi** | Neon on dark, glows, cool blues | Orbitron / Rajdhani / JetBrains Mono | Sharp corners, thin borders, hexagonal accents |
| **Medieval** | Gold on parchment, earth tones, blood red | MedieviSharp / Cinzel / IM Fell | Ornate borders, filigree, shield shapes |
| **Racing** | High contrast, yellow on black, speed | Racing Sans One / Industry / DIN | Angled cuts, italic, diagonal, speed lines |
| **Fighting** | Red/black, electric, fire, explosive | Impact / Bebas Neue / Anton | Thick bold, heavy borders, jagged |
| **Simulation** | Clean blue/gray, data-focused, precise | Inter / Source Code Pro / Roboto | Flat, 1px borders, grid-aligned, no decoration |
| **Normal** | Balanced, white/dark cards, soft accent | Poppins / Source Sans 3 / DM Mono | Rounded corners, soft shadows, familiar |
| **Horror** | Dark red/black, desaturated, flicker | Special Elite / Nosifer / Creepster | Jagged, dripping, distressed, decayed |
| **Cartoon** | Bright primaries, white outlines, playful | Fredoka / Comic Neue / Bubblegum Sans | Very rounded, thick outlines, bouncy |

---

## 6. Component Templates

Each component is a pre-designed widget subtree that the theme system styles. Components are the building blocks users pick from.

### 6.1 HUD Components (in-game overlay)

| Component ID | What It Creates | Bindable Variables |
|---|---|---|
| `health_bar` | Health progress bar with icon and numeric value | PlayerHealth, MaxHealth |
| `shield_bar` | Shield bar (often stacked above/below health) | PlayerShield, MaxShield, HasShield |
| `stamina_bar` | Stamina/energy bar | Stamina, MaxStamina |
| `ammo_counter` | Ammo display with magazine/reserve and weapon name | CurrentAmmo, MaxAmmo, ReserveAmmo, WeaponName |
| `score_panel` | Score display with label and count-up animation | Score |
| `timer` | Countdown or elapsed timer | TimeRemaining or ElapsedTime |
| `minimap` | Minimap with player dot and rotation | PlayerLocation, PlayerRotation, Markers[] |
| `compass` | Directional compass bar | PlayerRotation, Markers[] |
| `crosshair` | Dynamic crosshair (multiple styles) | IsAiming, IsFiring, Accuracy |
| `interaction_prompt` | "Press E to Open" contextual prompt | InteractionText, InputKey, IsVisible |
| `objective_tracker` | Current quest/objective list | Objectives[] |
| `kill_feed` | Scrolling kill/event log | KillEvents[] |
| `wave_counter` | "Wave 3/10" display | CurrentWave, TotalWaves |
| `boss_health_bar` | Wide bar at top of screen for boss encounters | BossName, BossHealth, BossMaxHealth |
| `notification_stack` | Popup notifications that stack and fade | Notifications[] |
| `damage_indicator` | Directional damage flash on screen edges | DamageDirection, DamageAmount |
| `speed_display` | Speedometer for racing/vehicles | Speed, MaxSpeed |
| `gear_indicator` | Current gear display | CurrentGear |
| `lap_counter` | "Lap 2/3" for racing | CurrentLap, TotalLaps |
| `position_display` | "1st Place" ranking | Position, TotalRacers |

### 6.2 Menu Components

| Component ID | What It Creates |
|---|---|
| `main_menu` | Title, Play/Settings/Quit buttons, background |
| `pause_menu` | Resume/Settings/Main Menu/Quit buttons, dim overlay |
| `settings_panel` | Audio/Video/Controls tabs with sliders and toggles |
| `inventory_grid` | Grid of item slots with drag-drop, tooltips, stack counts |
| `character_select` | Horizontal character cards with selection highlight |
| `level_select` | Grid of level cards with stars/lock states |
| `shop_panel` | Item cards with price, buy button, currency display |
| `dialog_box` | Character portrait, name, typewriter text, choice buttons |
| `loading_screen` | Progress bar, tip text, background image |
| `game_over` | Score summary, replay/quit buttons, stats |
| `leaderboard` | Ranked list with player names and scores |

### 6.3 Component Composition

Components can be composed into full HUDs:

```
WIDGET: WBP_GameHUD
THEME: SciFi
PALETTE:
  primary=#00D4FF
  accent=#FF3A5C

COMPONENTS:
  health_bar @anchor=TopLeft @offset=20,20
  shield_bar @anchor=TopLeft @offset=20,70 @visible=BIND:HasShield
  score_panel @anchor=TopRight @offset=-20,20
  ammo_counter @anchor=BottomRight @offset=-20,-20
  crosshair @anchor=Center @style=dot_and_lines
  interaction_prompt @anchor=BottomCenter @offset=0,-120
  damage_indicator @anchor=Fill
  notification_stack @anchor=TopCenter @offset=0,60
```

This shorthand expands into the full widget tree using the component templates + theme styles. The LLM can output either the shorthand COMPONENTS form or the full explicit tree — the parser handles both.

---

## 7. Parser Architecture

```
Widget DSL Text
    ↓
[1] Lexer — tokenizes lines into (indent, type, name, properties)
    ↓
[2] Theme Resolver — loads theme JSON, resolves $references in properties
    ↓
[3] Component Expander — replaces COMPONENTS shorthand with full widget trees
    ↓
[4] Binding Extractor — identifies BIND: properties, generates variable list
    ↓
[5] Animation Compiler — parses @anim: properties into UMG animation sequences
    ↓
[6] Tree Builder — constructs the widget hierarchy as nested dicts
    ↓
[7] Command Generator — converts tree to Arcwright TCP commands:
    create_widget_blueprint → add_widget_child (×N) → set_widget_property (×N)
    ↓
[8] Executor — sends commands to UE via TCP, returns result
```

**New TCP commands needed:**

| Command | Purpose |
|---|---|
| `create_widget_blueprint` | Already exists — creates empty Widget BP |
| `add_widget_child` | Already exists — adds child widget |
| `set_widget_property` | Already exists — sets property on widget |
| `set_widget_anchor` | NEW — set anchor preset + offset + alignment |
| `set_widget_binding` | NEW — bind property to variable |
| `create_widget_animation` | NEW — create UMG animation on widget |
| `add_animation_track` | NEW — add property track to animation |
| `add_animation_keyframe` | NEW — add keyframe to track |
| `set_widget_brush` | NEW — set brush (texture/material) on widget |
| `set_widget_font` | NEW — set font family/size/style on text widget |
| `apply_widget_theme` | NEW — apply theme JSON to entire widget tree |
| `preview_widget` | NEW — render widget in editor preview panel |
| `get_widget_screenshot` | NEW — capture widget render to PNG |

---

## 8. Training Data Format

Each training example is a (prompt, dsl) pair:

### 8.1 Simple Component Example

```
PROMPT: Create a sci-fi health bar with neon blue fill, positioned top-left, shows "HP: 75/100", pulses red when below 25%
THEME: SciFi

OUTPUT:
WIDGET: WBP_HealthBar
THEME: SciFi

ROOT: CanvasPanel
  @anchor=Fill

  HORIZONTAL_BOX: HealthRow
    @anchor=TopLeft
    @offset=20,20
    @size=280,36
    @valign=Center

    IMAGE: HealthIcon
      @brush=Icon_Health
      @size=24,24
      @tint=$primary
      @margin=0,0,8,0

    VERTICAL_BOX: BarStack
      @fill=1.0

      PROGRESS_BAR: HealthFill
        @percent=BIND:PlayerHealth/MaxHealth
        @fill_color=$primary
        @bg_color=$background:0.5
        @size=0,20
        @fill=1.0
        @corner_radius=3
        @anim:OnDamage=Shake|duration=0.3|intensity=3
        @anim:OnLowHealth=Pulse|duration=1.0|scale=1.02|count=0

    SPACER: @width=10

    TEXT: HealthText
      @text=BIND:"HP: {PlayerHealth}/{MaxHealth}"
      @font=$value
      @size=16
      @color=$text
      @anim:OnChange=Flash|duration=0.2|color=$primary
```

### 8.2 Full HUD Example (using COMPONENTS shorthand)

```
PROMPT: Create an FPS HUD with sci-fi theme, neon blue primary, red accent. Include health, shield, ammo, crosshair, and score. Dark background panels.

OUTPUT:
WIDGET: WBP_FPS_HUD
THEME: SciFi
PALETTE:
  primary=#00D4FF
  accent=#FF3A5C

COMPONENTS:
  health_bar @anchor=TopLeft @offset=20,20
  shield_bar @anchor=TopLeft @offset=20,65 @visible=BIND:HasShield
  score_panel @anchor=TopRight @offset=-20,20
  ammo_counter @anchor=BottomRight @offset=-20,-20
  crosshair @anchor=Center @style=dot_and_lines
  damage_indicator @anchor=Fill
```

### 8.3 Training Data Categories

| Category | Example Count | What It Teaches |
|---|---|---|
| Individual components (per theme) | 8 themes × 20 components = 160 | How each component looks in each theme |
| Full HUD compositions | 8 themes × 8 game types = 64 | How to compose components into complete HUDs |
| Style variations | 50 | Same component, different color/size/animation choices |
| Modification requests | 50 | "Make the health bar bigger", "Move score to center", "Add glow effect" |
| Complex menus | 8 themes × 5 menu types = 40 | Inventory, settings, shop, character select, etc. |
| Special widgets | 30 | Minimap, compass, dialog, notification systems |
| Edge cases | 20 | Very small screens, unusual aspect ratios, dense layouts |
| Responsive variations | 20 | Same HUD adapted for different resolutions |
| Artistic requests | 40 | "Like Halo's HUD", "Minimalist", "Retro arcade style" |
| Conversational refinements | 30 | Multi-turn: initial generation → user feedback → improved version |
| **Total** | **~504** | |

---

## 9. File Structure

```
scripts/
├── widget_dsl/
│   ├── __init__.py
│   ├── lexer.py              -- tokenizes DSL text
│   ├── parser.py             -- builds widget tree from tokens
│   ├── theme_resolver.py     -- loads + applies theme JSON
│   ├── component_expander.py -- expands COMPONENTS shorthand
│   ├── binding_extractor.py  -- finds BIND: references, generates variables
│   ├── animation_compiler.py -- parses @anim: into UMG animation data
│   ├── command_generator.py  -- converts tree to TCP commands
│   ├── executor.py           -- sends commands to UE
│   └── validator.py          -- validates DSL syntax before execution
├── widget_themes/
│   ├── scifi.json
│   ├── medieval.json
│   ├── racing.json
│   ├── fighting.json
│   ├── simulation.json
│   ├── normal.json
│   ├── horror.json
│   └── cartoon.json
├── widget_components/
│   ├── health_bar.json       -- component template definitions
│   ├── ammo_counter.json
│   ├── minimap.json
│   ├── crosshair.json
│   ├── ... (20+ components)
│   └── component_index.json
└── widget_training/
    ├── lessons/
    │   ├── widget_lesson_01_simple_components.json
    │   ├── widget_lesson_02_full_huds.json
    │   ├── widget_lesson_03_themes.json
    │   ├── widget_lesson_04_animations.json
    │   ├── widget_lesson_05_bindings.json
    │   ├── widget_lesson_06_menus.json
    │   ├── widget_lesson_07_special.json
    │   ├── widget_lesson_08_modifications.json
    │   └── widget_lesson_09_artistic.json
    └── exams/
        └── widget_exam_suite.json

Content/
├── UI_Themes/
│   ├── SciFi/
│   │   ├── Materials/        -- M_UI_SciFi_Panel, _Button, _ProgressFill, etc.
│   │   ├── Textures/         -- T_Icon_SciFi_Health, _Crosshair, etc.
│   │   └── Fonts/            -- Downloaded/licensed per theme
│   ├── Medieval/
│   ├── Racing/
│   ├── Fighting/
│   ├── Simulation/
│   ├── Normal/
│   ├── Horror/
│   └── Cartoon/
└── UI_Common/
    ├── FX/                   -- Vignette, scanlines, noise overlays
    └── Icons/                -- Universal icons (shared across themes)
```

---

## 10. Implementation Phases

| Phase | Duration | Deliverable |
|---|---|---|
| **Phase 1: DSL Parser** | 2 weeks | lexer, parser, theme_resolver, command_generator — can parse DSL and build widgets in UE via existing commands |
| **Phase 2: New TCP Commands** | 1 week | set_widget_anchor, set_widget_binding, create_widget_animation, set_widget_brush, set_widget_font, preview_widget |
| **Phase 3: Theme System** | 2 weeks | 8 theme JSON files, theme resolver, color/font/brush resolution |
| **Phase 4: Component Templates** | 2 weeks | 20 component templates as JSON, component expander, COMPONENTS shorthand |
| **Phase 5: UI Assets** | 3 weeks | Materials, textures, icons for all 8 themes (~400 assets) |
| **Phase 6: Training Data** | 3 weeks | ~504 examples across 9 lesson categories |
| **Phase 7: Model Training** | 1 week | widget-lora-v1, exam, iterate |
| **Phase 8: Builder Panel** | 3 weeks | Theme picker, color picker, component checklist, live preview, "Ask AI", "Generate" |
| **Phase 9: Testing** | 1 week | End-to-end: pick theme → generate → play → see UI |
| **Total** | **~18 weeks** | Complete UI Builder system |

---

## 11. Success Metrics

| Metric | Target |
|---|---|
| Widget DSL syntax accuracy | 95%+ |
| Theme consistency (visual coherence) | Subjective — all components in a theme look like they belong together |
| Component count | 20+ HUD components, 10+ menu components |
| Theme count | 8 at launch |
| Generation time | <10 seconds per full HUD |
| Preview render time | <200ms per update (real-time feel) |
| User can go from "I want a Sci-Fi HUD" to playing with it | <60 seconds |
