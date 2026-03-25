# Arcwright Changelog

All notable changes to the Arcwright UE5 plugin are documented here.

---

## 1.0.2 (2026-03-25)

### Added

- **Feedback system** -- Users can submit feedback and bug reports directly from the Arcwright dashboard panel inside UE. Reports are filed as GitHub Issues via a direct GitHub API integration.
- **Feedback token** -- Authenticated issue creation using a scoped GitHub token (create-issues-only permissions).

### Changed

- Replaced the Cloudflare Worker relay with a direct GitHub Issues API call for feedback submission. Simpler architecture, fewer moving parts.

---

## 1.0.1 (2026-03-24)

### Added

- **`hex:#RRGGBB` color support** -- Pass colors to `set_widget_property` using hex notation with the `hex:` prefix. The plugin auto-converts sRGB hex values to the linear color space that UE requires. No more manual sRGB-to-linear math.

- **`srgb:(R=,G=,B=,A=)` color support** -- Alternative sRGB input format with automatic linear conversion. Useful for float-based color values that are specified in sRGB space.

- **`set_widget_design_size` command** -- Change the design-time resolution of any Widget Blueprint after creation. Accepts `width` and `height` parameters.

- **`protect_widget_layout` command** -- Lock visual layout widgets (backgrounds, borders, containers) so that only `txt_*` and `Btn_*` named widgets remain accessible from Blueprint/C++ code. Prevents accidental runtime modification of the visual layer.

- **Auto-clip on root CanvasPanel** -- The root CanvasPanel of every Widget Blueprint now automatically clips its children to bounds, preventing visual overflow at screen edges.

- **1920x1080 default design size** -- `create_widget_blueprint` now defaults to 1920x1080 design resolution when `design_width` and `design_height` are not specified.

### Changed

- **Content path migration** -- All generated assets moved from `/Game/BlueprintLLM/` to `/Game/Arcwright/`. This applies to Blueprints (`/Game/Arcwright/Generated/`), Materials (`/Game/Arcwright/Materials/`), and all other generated content.

- **Display string rename** -- All user-facing strings in the plugin updated from "BlueprintLLM" to "Arcwright" (202 replacements across 8 source files). Menu items, log categories, dashboard labels, and error messages all reflect the new product name.

### Fixed

- **`ParseLinearColor` now handles all color formats** -- Previously, passing sRGB hex values directly to color properties produced washed-out colors because UE interprets `FLinearColor` as linear. The `hex:` and `srgb:` prefixes perform correct gamma-to-linear conversion using `FLinearColor::FromSRGBColor()`.

---

## 1.0.0 (2026-03-21)

### Initial Release

The first public release of Arcwright on the FAB Marketplace.

**Core Features:**

- **TCP Command Server** on `localhost:13377` -- 274 newline-delimited JSON commands processed on the UE game thread via `AsyncTask(ENamedThreads::GameThread)`.

- **MCP Server** (289 tools) -- Stdio JSON-RPC bridge at `scripts/mcp_server/server.py`. Compatible with Claude Desktop, Cursor, Windsurf, Cline, and any MCP client.

- **Blueprint CRUD** -- `create_blueprint`, `add_nodes_batch`, `add_connections_batch`, `compile_blueprint`, `validate_blueprint`, `delete_blueprint`, `get_blueprint_info`, `import_from_ir`, `create_blueprint_from_dsl`.

- **Actor and Level Management** -- `spawn_actor_at`, `find_actors`, `delete_actor`, `set_actor_transform`, `get_actor_properties`. Full World Partition support with external actor package saving.

- **Component System** -- 11 component types (StaticMesh, BoxCollision, SphereCollision, CapsuleCollision, PointLight, SpotLight, Audio, Arrow, Scene, Niagara, SkeletalMesh) with property configuration.

- **Material System** -- `create_simple_material` (works with Substrate and traditional rendering), `apply_material`, `set_actor_material`, `batch_apply_material`.

- **Widget System** -- `create_widget_blueprint`, `add_widget_child`, `set_widget_property`, `get_widget_tree`. Supports CanvasPanel, VerticalBox, HorizontalBox, Overlay, TextBlock, Image, Button, ProgressBar, Border, SizeBox, EditableText, ScrollBox, UniformGridPanel, Spacer.

- **Behavior Trees** -- `create_behavior_tree` from JSON IR, `get_behavior_tree_info`, `setup_ai_for_pawn` (one-command AI controller setup).

- **Data Tables** -- `create_data_table`, `add_data_table_row`, `get_data_table_rows`.

- **Spawn Patterns** -- `spawn_actor_grid`, `spawn_actor_circle`, `spawn_actor_line` for geometric actor placement.

- **Batch Operations** -- `batch_set_variable`, `batch_add_component`, `batch_delete_actors`, `batch_move_actors`, `batch_apply_material`. Fault-tolerant (individual failures do not abort the batch).

- **Query and Discovery** -- `find_blueprints`, `find_assets`, `list_project_assets`, `get_capabilities`.

- **Inspection** -- `get_blueprint_details`, `get_actor_properties`, `verify_all_blueprints`, `get_components`, `get_widget_tree`.

- **Diagnostics** -- `run_map_check`, `get_message_log`, `get_output_log`, `get_stats`, `get_last_error`.

- **PIE Control** -- `play_in_editor`, `stop_play`, `is_playing`, `teleport_player`, `get_player_location`, `teleport_to_actor`, `get_player_view`.

- **29 DSL Parsers** -- Blueprint, BehaviorTree, DataTable, Widget, AnimBP, Material, Dialogue, Quest, Sequence, GAS, Perception, Physics, Tags, Enhanced Input, Smart Objects, Sound, Replication, Control Rig, State Trees, Vehicles, World Partition, Landscape, Foliage, Mass Entity, Shader, ProcMesh, Paper2D, Composure, DMX.

- **Scene Setup** -- `setup_scene_lighting` with presets (indoor_dark, indoor_bright, outdoor_day, outdoor_night), `set_world_settings`, `create_nav_mesh_bounds`.

- **Sequencer** -- `create_sequence`, `add_sequence_track`, `add_keyframe`.

- **HTML to Widget Translator** -- Convert HTML/CSS mockups to UE Widget Blueprints via `create_widget_from_html`.

- **SafeSavePackage** -- All save operations use `FullyLoad()` before `SavePackage()` to prevent crashes on partially-loaded packages.

- **Default Event Nodes** -- `create_blueprint` auto-creates `node_0` (BeginPlay), `node_1` (ActorBeginOverlap), `node_2` (Tick). Wire to these directly instead of recreating them.

- **Auto-type remapping** -- Float functions automatically remap to Double equivalents for UE 5.4+ compatibility (e.g., `Add_FloatFloat` becomes `Add_DoubleDouble`).

**Pricing:** $49.99 one-time purchase. No subscription, no API keys, no remote validation.
