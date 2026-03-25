# Widget Cookbook

Practical, copy-paste-ready examples for building UE5 Widget Blueprints with Arcwright. Each recipe shows the complete TCP command sequence to build a functional UI element.

All examples use `hex:#RRGGBB` colors and a 1920x1080 design size.

---

## Recipe 1: Simple HUD (Health + Score)

A minimal game HUD with a health bar in the top-left and a score counter in the top-right.

### Create the widget

```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_SimpleHUD"}}
```

### Build the hierarchy

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_type": "CanvasPanel", "widget_name": "RootCanvas"}}
```

**Health section (top-left):**

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_type": "TextBlock", "widget_name": "txt_HealthLabel", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_HealthLabel", "property_name": "text", "value": "HEALTH"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_HealthLabel", "property_name": "font_size", "value": 12}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_HealthLabel", "property_name": "color", "value": "hex:#707888"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_HealthLabel", "property_name": "position", "value": {"x": 40, "y": 30}}}
```

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_type": "ProgressBar", "widget_name": "HealthBar", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "HealthBar", "property_name": "percent", "value": 1.0}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "HealthBar", "property_name": "fill_color", "value": "hex:#3DDC84"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "HealthBar", "property_name": "position", "value": {"x": 40, "y": 50}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "HealthBar", "property_name": "size", "value": {"x": 250, "y": 10}}}
```

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_type": "TextBlock", "widget_name": "txt_HealthValue", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_HealthValue", "property_name": "text", "value": "100"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_HealthValue", "property_name": "font_size", "value": 28}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_HealthValue", "property_name": "color", "value": "hex:#D0D4DC"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_HealthValue", "property_name": "position", "value": {"x": 40, "y": 65}}}
```

**Score section (top-right):**

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_type": "TextBlock", "widget_name": "txt_ScoreLabel", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_ScoreLabel", "property_name": "text", "value": "SCORE"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_ScoreLabel", "property_name": "font_size", "value": 12}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_ScoreLabel", "property_name": "color", "value": "hex:#707888"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_ScoreLabel", "property_name": "position", "value": {"x": 1800, "y": 30}}}
```

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_type": "TextBlock", "widget_name": "txt_ScoreValue", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_ScoreValue", "property_name": "text", "value": "0"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_ScoreValue", "property_name": "font_size", "value": 32}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_ScoreValue", "property_name": "color", "value": "hex:#E8A624"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_SimpleHUD", "widget_name": "txt_ScoreValue", "property_name": "position", "value": {"x": 1800, "y": 48}}}
```

### Lock the layout

```json
{"command": "protect_widget_layout", "params": {"widget_blueprint": "WBP_SimpleHUD"}}
```

---

## Recipe 2: Main Menu

A title screen with a game title, three buttons (Play, Settings, Quit), and a version string.

### Create the widget

```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_MainMenu"}}
```

### Build the hierarchy

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_MainMenu", "widget_type": "CanvasPanel", "widget_name": "RootCanvas"}}
```

**Background panel:**

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_MainMenu", "widget_type": "Border", "widget_name": "Background", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "Background", "property_name": "background_color", "value": "hex:#0A0C0F"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "Background", "property_name": "position", "value": {"x": 0, "y": 0}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "Background", "property_name": "size", "value": {"x": 1920, "y": 1080}}}
```

**Title text:**

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_MainMenu", "widget_type": "TextBlock", "widget_name": "txt_Title", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Title", "property_name": "text", "value": "MY GAME"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Title", "property_name": "font_size", "value": 64}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Title", "property_name": "color", "value": "hex:#EEF0F4"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Title", "property_name": "position", "value": {"x": 760, "y": 200}}}
```

**Menu buttons (vertical stack):**

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_MainMenu", "widget_type": "VerticalBox", "widget_name": "ButtonStack", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "ButtonStack", "property_name": "position", "value": {"x": 810, "y": 420}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "ButtonStack", "property_name": "size", "value": {"x": 300, "y": 280}}}
```

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_MainMenu", "widget_type": "Button", "widget_name": "Btn_Play", "parent_name": "ButtonStack"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "Btn_Play", "property_name": "background_color", "value": "hex:#2A3040"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_MainMenu", "widget_type": "TextBlock", "widget_name": "txt_Play", "parent_name": "Btn_Play"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Play", "property_name": "text", "value": "PLAY"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Play", "property_name": "font_size", "value": 24}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Play", "property_name": "color", "value": "hex:#E8A624"}}
```

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_MainMenu", "widget_type": "Button", "widget_name": "Btn_Settings", "parent_name": "ButtonStack"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "Btn_Settings", "property_name": "background_color", "value": "hex:#2A3040"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_MainMenu", "widget_type": "TextBlock", "widget_name": "txt_Settings", "parent_name": "Btn_Settings"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Settings", "property_name": "text", "value": "SETTINGS"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Settings", "property_name": "font_size", "value": 24}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Settings", "property_name": "color", "value": "hex:#D0D4DC"}}
```

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_MainMenu", "widget_type": "Button", "widget_name": "Btn_Quit", "parent_name": "ButtonStack"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "Btn_Quit", "property_name": "background_color", "value": "hex:#2A3040"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_MainMenu", "widget_type": "TextBlock", "widget_name": "txt_Quit", "parent_name": "Btn_Quit"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Quit", "property_name": "text", "value": "QUIT"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Quit", "property_name": "font_size", "value": 24}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Quit", "property_name": "color", "value": "hex:#E04050"}}
```

**Version string (bottom-right):**

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_MainMenu", "widget_type": "TextBlock", "widget_name": "txt_Version", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Version", "property_name": "text", "value": "v1.0.0"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Version", "property_name": "font_size", "value": 12}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Version", "property_name": "color", "value": "hex:#707888"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_MainMenu", "widget_name": "txt_Version", "property_name": "position", "value": {"x": 1830, "y": 1050}}}
```

### Lock the layout

```json
{"command": "protect_widget_layout", "params": {"widget_blueprint": "WBP_MainMenu"}}
```

---

## Recipe 3: Health Bar with Background

A styled health bar with a dark background panel, label, progress bar, and numeric value -- suitable for an RPG or survival game.

### Commands

```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_HealthBar"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_HealthBar", "widget_type": "CanvasPanel", "widget_name": "RootCanvas"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_HealthBar", "widget_type": "Border", "widget_name": "BarBackground", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "BarBackground", "property_name": "background_color", "value": "hex:#12161C"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "BarBackground", "property_name": "position", "value": {"x": 30, "y": 20}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "BarBackground", "property_name": "size", "value": {"x": 320, "y": 80}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "BarBackground", "property_name": "padding", "value": {"left": 12, "top": 8, "right": 12, "bottom": 8}}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_HealthBar", "widget_type": "TextBlock", "widget_name": "txt_Label", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "txt_Label", "property_name": "text", "value": "HP"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "txt_Label", "property_name": "font_size", "value": 11}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "txt_Label", "property_name": "color", "value": "hex:#707888"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "txt_Label", "property_name": "position", "value": {"x": 44, "y": 26}}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_HealthBar", "widget_type": "ProgressBar", "widget_name": "HealthFill", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "HealthFill", "property_name": "percent", "value": 0.75}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "HealthFill", "property_name": "fill_color", "value": "hex:#3DDC84"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "HealthFill", "property_name": "background_color", "value": "hex:#181D26"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "HealthFill", "property_name": "position", "value": {"x": 44, "y": 46}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "HealthFill", "property_name": "size", "value": {"x": 220, "y": 8}}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_HealthBar", "widget_type": "TextBlock", "widget_name": "txt_Value", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "txt_Value", "property_name": "text", "value": "75 / 100"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "txt_Value", "property_name": "font_size", "value": 14}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "txt_Value", "property_name": "color", "value": "hex:#D0D4DC"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HealthBar", "widget_name": "txt_Value", "property_name": "position", "value": {"x": 44, "y": 62}}}

{"command": "protect_widget_layout", "params": {"widget_blueprint": "WBP_HealthBar"}}
```

---

## Recipe 4: Inventory Grid

A 4x3 inventory grid with item slots, each containing a placeholder image and stack count.

### Commands

```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_Inventory"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Inventory", "widget_type": "CanvasPanel", "widget_name": "RootCanvas"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Inventory", "widget_type": "Border", "widget_name": "InvBackground", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "InvBackground", "property_name": "background_color", "value": "hex:#0A0C0F"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "InvBackground", "property_name": "position", "value": {"x": 610, "y": 240}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "InvBackground", "property_name": "size", "value": {"x": 700, "y": 600}}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Inventory", "widget_type": "TextBlock", "widget_name": "txt_Title", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "txt_Title", "property_name": "text", "value": "INVENTORY"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "txt_Title", "property_name": "font_size", "value": 22}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "txt_Title", "property_name": "color", "value": "hex:#EEF0F4"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "txt_Title", "property_name": "position", "value": {"x": 640, "y": 260}}}
```

Create a 4x3 grid of item slots. Each slot is a Border with an Image and a TextBlock for the stack count:

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Inventory", "widget_type": "UniformGridPanel", "widget_name": "ItemGrid", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "ItemGrid", "property_name": "position", "value": {"x": 640, "y": 310}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "ItemGrid", "property_name": "size", "value": {"x": 640, "y": 480}}}
```

Create the first slot as an example (repeat the pattern for all 12):

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Inventory", "widget_type": "Border", "widget_name": "Slot_0_0", "parent_name": "ItemGrid"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "Slot_0_0", "property_name": "background_color", "value": "hex:#12161C"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "Slot_0_0", "property_name": "padding", "value": {"left": 4, "top": 4, "right": 4, "bottom": 4}}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Inventory", "widget_type": "Overlay", "widget_name": "SlotOverlay_0_0", "parent_name": "Slot_0_0"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Inventory", "widget_type": "Image", "widget_name": "SlotIcon_0_0", "parent_name": "SlotOverlay_0_0"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "SlotIcon_0_0", "property_name": "color", "value": "hex:#2A3040"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Inventory", "widget_type": "TextBlock", "widget_name": "txt_Stack_0_0", "parent_name": "SlotOverlay_0_0"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "txt_Stack_0_0", "property_name": "text", "value": ""}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "txt_Stack_0_0", "property_name": "font_size", "value": 12}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "txt_Stack_0_0", "property_name": "color", "value": "hex:#D0D4DC"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "txt_Stack_0_0", "property_name": "alignment", "value": {"x": 1.0, "y": 1.0}}}
```

Repeat the slot pattern for `Slot_0_1` through `Slot_3_2` (changing positions in the grid).

### Close button

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Inventory", "widget_type": "Button", "widget_name": "Btn_Close", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "Btn_Close", "property_name": "position", "value": {"x": 1260, "y": 248}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "Btn_Close", "property_name": "size", "value": {"x": 32, "y": 32}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "Btn_Close", "property_name": "background_color", "value": "hex:#E04050"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Inventory", "widget_type": "TextBlock", "widget_name": "txt_CloseX", "parent_name": "Btn_Close"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "txt_CloseX", "property_name": "text", "value": "X"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "txt_CloseX", "property_name": "font_size", "value": 16}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Inventory", "widget_name": "txt_CloseX", "property_name": "color", "value": "hex:#EEF0F4"}}
```

```json
{"command": "protect_widget_layout", "params": {"widget_blueprint": "WBP_Inventory"}}
```

---

## Recipe 5: Notification Toast

A slide-in notification panel for achievements, pickups, or system messages. Designed as a compact bar at the top-center of the screen.

### Commands

```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_Toast"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Toast", "widget_type": "CanvasPanel", "widget_name": "RootCanvas"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Toast", "widget_type": "Border", "widget_name": "ToastBg", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Toast", "widget_name": "ToastBg", "property_name": "background_color", "value": "hex:#12161C"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Toast", "widget_name": "ToastBg", "property_name": "position", "value": {"x": 660, "y": 40}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Toast", "widget_name": "ToastBg", "property_name": "size", "value": {"x": 600, "y": 60}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Toast", "widget_name": "ToastBg", "property_name": "padding", "value": {"left": 16, "top": 8, "right": 16, "bottom": 8}}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Toast", "widget_type": "HorizontalBox", "widget_name": "ToastContent", "parent_name": "ToastBg"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Toast", "widget_type": "TextBlock", "widget_name": "txt_ToastIcon", "parent_name": "ToastContent"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Toast", "widget_name": "txt_ToastIcon", "property_name": "text", "value": "!"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Toast", "widget_name": "txt_ToastIcon", "property_name": "font_size", "value": 20}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Toast", "widget_name": "txt_ToastIcon", "property_name": "color", "value": "hex:#E8A624"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Toast", "widget_type": "Spacer", "widget_name": "IconSpacer", "parent_name": "ToastContent"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Toast", "widget_name": "IconSpacer", "property_name": "size", "value": {"x": 12, "y": 1}}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_Toast", "widget_type": "TextBlock", "widget_name": "txt_ToastMessage", "parent_name": "ToastContent"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Toast", "widget_name": "txt_ToastMessage", "property_name": "text", "value": "Achievement Unlocked!"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Toast", "widget_name": "txt_ToastMessage", "property_name": "font_size", "value": 18}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_Toast", "widget_name": "txt_ToastMessage", "property_name": "color", "value": "hex:#D0D4DC"}}

{"command": "protect_widget_layout", "params": {"widget_blueprint": "WBP_Toast"}}
```

---

## Recipe 6: Shooter Ammo Display

A bottom-right ammo counter with current magazine and reserve counts, plus a weapon name label.

### Commands

```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_AmmoDisplay"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_type": "CanvasPanel", "widget_name": "RootCanvas"}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_type": "Border", "widget_name": "AmmoBg", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "AmmoBg", "property_name": "background_color", "value": "hex:#0A0C0F"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "AmmoBg", "property_name": "render_opacity", "value": 0.85}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "AmmoBg", "property_name": "position", "value": {"x": 1680, "y": 940}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "AmmoBg", "property_name": "size", "value": {"x": 220, "y": 120}}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_type": "TextBlock", "widget_name": "txt_WeaponName", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_WeaponName", "property_name": "text", "value": "ASSAULT RIFLE"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_WeaponName", "property_name": "font_size", "value": 11}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_WeaponName", "property_name": "color", "value": "hex:#707888"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_WeaponName", "property_name": "position", "value": {"x": 1700, "y": 952}}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_type": "TextBlock", "widget_name": "txt_AmmoCurrent", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_AmmoCurrent", "property_name": "text", "value": "30"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_AmmoCurrent", "property_name": "font_size", "value": 48}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_AmmoCurrent", "property_name": "color", "value": "hex:#EEF0F4"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_AmmoCurrent", "property_name": "position", "value": {"x": 1700, "y": 972}}}

{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_type": "TextBlock", "widget_name": "txt_AmmoReserve", "parent_name": "RootCanvas"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_AmmoReserve", "property_name": "text", "value": "/ 120"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_AmmoReserve", "property_name": "font_size", "value": 18}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_AmmoReserve", "property_name": "color", "value": "hex:#707888"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_AmmoDisplay", "widget_name": "txt_AmmoReserve", "property_name": "position", "value": {"x": 1780, "y": 1000}}}

{"command": "protect_widget_layout", "params": {"widget_blueprint": "WBP_AmmoDisplay"}}
```

---

## Widget Naming Conventions

For widgets that need to be updated at runtime from Blueprint or C++ code, use these prefixes:

| Prefix | Purpose | Example |
|---|---|---|
| `txt_` | Text that changes at runtime | `txt_Score`, `txt_HealthValue`, `txt_AmmoCount` |
| `Btn_` | Buttons with click handlers | `Btn_Play`, `Btn_Settings`, `Btn_Close` |

Widgets without these prefixes (backgrounds, borders, layout containers) are locked by `protect_widget_layout` and cannot be accidentally modified at runtime.

---

## Color Reference

Common UI colors using `hex:` format:

| Purpose | Hex | Description |
|---|---|---|
| Deep background | `hex:#0A0C0F` | Darkest background layer |
| Panel background | `hex:#12161C` | Card/panel fill |
| Card background | `hex:#181D26` | Elevated surface |
| Border | `hex:#2A3040` | Subtle borders |
| Active border | `hex:#3A4560` | Focused/hover borders |
| Accent/gold | `hex:#E8A624` | Primary accent, scores, highlights |
| Success/green | `hex:#3DDC84` | Health, positive states |
| Warning/yellow | `hex:#F0C040` | Caution states |
| Danger/red | `hex:#E04050` | Damage, errors, quit buttons |
| Primary text | `hex:#D0D4DC` | Main readable text |
| Dim text | `hex:#707888` | Labels, secondary text |
| Bright text | `hex:#EEF0F4` | Headers, emphasized text |
