# Troubleshooting

Common errors when using Arcwright, what they mean, and how to fix them.

---

## Connection Issues

### "Cannot connect to UE command server" / Connection refused

**Cause:** The MCP server or TCP client cannot reach the Arcwright plugin on port 13377.

**Fixes:**
1. **Is Unreal Editor running?** The TCP server only exists while the editor is open with the Arcwright plugin loaded.
2. **Is the plugin loaded?** Check **Edit > Plugins** in UE and confirm "Arcwright" is enabled.
3. **Is the server started?** Look for `LogArcwright: Arcwright Command Server started on port 13377` in the UE Output Log (Window > Output Log). If not present, check **Tools > Arcwright** to toggle the server.
4. **Is port 13377 in use?** Run `netstat -an | findstr 13377` (Windows) to check. Only one process can bind to a port.
5. **Firewall?** Arcwright uses `localhost` only. Firewall rules should not block local loopback, but check if a security product is interfering.

### Connection times out

**Cause:** The editor is running but the command server is unresponsive (likely the game thread is blocked).

**Fixes:**
1. Check if a modal dialog is open in the UE Editor (Save As, crash reporter, etc.). Dismiss it.
2. If the editor appears frozen, it may be compiling shaders or performing a heavy operation. Wait and retry.
3. Increase the timeout: set `BLUEPRINTLLM_TIMEOUT=120` environment variable.

---

## Blueprint Errors

### "Blueprint not found" / "Blueprint 'BP_Name' not found"

**Cause:** The specified Blueprint does not exist at the expected path.

**Fixes:**
1. Check the exact name. Blueprint names are case-sensitive.
2. Use `find_blueprints` to search for it:
   ```json
   {"command": "find_blueprints", "params": {"name_filter": "Name"}}
   ```
3. Blueprints created by Arcwright are stored at `/Game/Arcwright/Generated/`. If you created it manually in the editor, it may be at a different path.
4. If you recently deleted and recreated it, the old reference may be stale. Try `compile_blueprint` first.

### "Asset cannot be saved as it has only been partially loaded"

**Cause:** `UPackage::SavePackage` crashes on packages that are lazy-loaded from disk but not fully loaded into memory. This happens when recreating an asset that previously existed (e.g., running a test suite twice).

**Fix:** This is handled internally by Arcwright's `SafeSavePackage` function, which calls `Package->FullyLoad()` before saving. If you still encounter this error, it indicates a code path that bypasses the safe save wrapper. Report it as a bug.

### Blueprint compilation errors after editing

**Cause:** Nodes, connections, or variable types may conflict after manual edits.

**Fixes:**
1. Check the Blueprint in the UE Editor for compile errors (red nodes, broken connections).
2. Use `get_blueprint_info` to inspect the Blueprint structure and identify issues.
3. If a variable type changed, nodes referencing it may have stale pin types. Delete and recreate the affected nodes.

---

## Material Issues

### Material appears gray / default on spawned actors

**Cause:** SCS `OverrideMaterials` do not reliably persist through the Blueprint compile and spawn pipeline. This is a known UE5 issue.

**Fix:** Use `set_actor_material` instead of `apply_material` for placed actors. `set_actor_material` operates on the spawned actor's registered mesh component directly, which always works:

```json
{
  "command": "set_actor_material",
  "params": {
    "actor_label": "MyActor_1",
    "material_path": "/Game/Arcwright/Materials/MAT_Gold"
  }
}
```

Call this AFTER `spawn_actor_at`. Re-apply after any re-spawn operation.

### create_material_instance color does not show (renders gray)

**Cause:** UE 5.7 uses Substrate rendering. `BasicShapeMaterial` (the default parent for `create_material_instance`) does not expose `BaseColor` as a modifiable vector parameter under Substrate.

**Fix:** Use `create_simple_material` instead. It creates a proper `UMaterial` with `UMaterialExpressionConstant3Vector` nodes connected to BaseColor, which works with both Substrate and traditional rendering:

```json
{
  "command": "create_simple_material",
  "params": {
    "name": "MAT_MyColor",
    "color": {"r": 1.0, "g": 0.5, "b": 0.0}
  }
}
```

### Light colors are extremely overbright (white)

**Cause:** `FLinearColor` uses a 0.0 to 1.0 range, not 0 to 255. Passing `{"r": 255, "g": 200, "b": 80}` makes each channel 255x the intended brightness.

**Fix:** Normalize all color values to 0.0-1.0:

| Desired Color | Correct | Incorrect |
|---|---|---|
| Warm yellow | `{"r": 1.0, "g": 0.78, "b": 0.31}` | `{"r": 255, "g": 200, "b": 80}` |
| Bright red | `{"r": 1.0, "g": 0.0, "b": 0.0}` | `{"r": 255, "g": 0, "b": 0}` |

---

## Actor and Spawn Issues

### Spawned actors do not have updated components

**Cause:** Adding components to a Blueprint via `add_component` updates the asset, but already-placed actors do not pick up the changes.

**Fix:** Delete existing actors and re-spawn them:

```json
{"command": "delete_actor", "params": {"label": "MyActor_1"}}
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_MyActor.BP_MyActor", "location": {"x": 100, "y": 200, "z": 0}, "label": "MyActor_1"}}
```

Or use batch delete to remove all instances:

```json
{"command": "batch_delete_actors", "params": {"class_filter": "BP_MyActor"}}
```

### spawn_actor_at creates a plain actor (no Blueprint logic)

**Cause:** The `class` parameter uses a short name like `"BP_Pickup"` instead of the full path. Short names resolve via `TObjectIterator` and may match the wrong class or fall back to AActor.

**Fix:** Use the full `/Game/` path:

```json
{
  "command": "spawn_actor_at",
  "params": {
    "class": "/Game/Arcwright/Generated/BP_Pickup.BP_Pickup"
  }
}
```

### Actors disappear after reloading the level

**Cause:** World Partition stores actors as external `.uasset` files, not embedded in the `.umap`. A simple map save does not save these external actor packages.

**Fix:** Use `save_all`, which explicitly saves World Partition external actor packages. The response includes an `external_actors_saved` count:

```json
{"command": "save_all", "params": {}}
// Response: {"status": "ok", "data": {"saved": true, "external_actors_saved": 23}}
```

If `external_actors_saved` is 0 but you have actors in the level, there may be a save issue. Try `save_level` followed by `save_all`.

---

## Play In Editor (PIE) Issues

### play_in_editor returns success but nothing happens

**Cause:** This is a known UE 5.7 limitation. `RequestPlaySession()` queues a PIE request, but the engine tick loop does not process it when invoked from an external TCP command. `FEngineLoop::Tick()` does not run in editor idle mode triggered from the command server.

**Fix:** Use the **Play** button in the UE Editor manually. This limitation affects both `play_in_editor` and `play_sequence` commands.

---

## Performance and Stability

### Editor becomes unresponsive after many rapid commands

**Cause:** Rapid sequential commands (especially material creation, Blueprint compilation, and shader compilation) can trigger recursive `FlushRenderingCommands` calls that crash or freeze the editor.

**Fixes:**
1. Add brief pauses (0.5-1 second) between commands that trigger shader compilation (material creation, material application).
2. Batch similar operations where possible (e.g., `batch_apply_material` instead of individual `set_actor_material` calls).
3. The plugin has a `FlushRenderingCommands` guard at the command dispatch level, but very rapid fire can still cause issues.

### Editor crashes when saving

**Cause:** Partially-loaded packages crash `UPackage::SavePackage`. This happens when an asset was previously on disk, got lazy-loaded into memory, and then `SavePackage` is called without fully loading it.

**Fix:** Arcwright uses `SafeSavePackage` which calls `FullyLoad()` before saving. If you encounter crashes on save, ensure you are using the latest plugin version with this fix applied across all save paths.

---

## Command-Specific Issues

### "Unknown command" error

**Cause:** The command name is misspelled or does not exist.

**Fixes:**
1. Check spelling against the [Command Reference](command-reference.md).
2. Use `health_check` to verify the server is responding.
3. Use `get_last_error` to see the most recent error details.

### Behavior tree MoveTo silently fails

**Cause:** NavMesh may not be built in World Partition maps. The `MoveTo` task uses pathfinding by default and silently fails without NavMesh data.

**Fixes:**
1. Create a `NavMeshBoundsVolume`:
   ```json
   {"command": "create_nav_mesh_bounds", "params": {"location": {"x": 0, "y": 0, "z": 0}, "extents": {"x": 5000, "y": 5000, "z": 500}}}
   ```
2. Or disable pathfinding in the BT task params: set `bUsePathfinding` to `false` for direct-line movement.

### set_class_defaults does not take effect on placed actors

**Cause:** CDO (Class Default Object) changes affect new instances only. Existing actors keep their previous defaults.

**Fix:** Re-spawn the affected actors after changing class defaults. If another Blueprint references the changed Blueprint (e.g., `AIControllerClass`), you must also re-apply `set_class_defaults` and re-spawn those actors too.

### Widget text is invisible

**Cause:** The default text color may be black on a dark background, or the widget position places it off-screen.

**Fixes:**
1. Set an explicit color:
   ```json
   {"command": "set_widget_property", "params": {"widget_blueprint": "WBP_HUD", "widget_name": "MyText", "property_name": "color", "value": {"r": 1, "g": 1, "b": 1, "a": 1}}}
   ```
2. Check the position and size:
   ```json
   {"command": "get_widget_tree", "params": {"widget_blueprint": "WBP_HUD"}}
   ```

---

## Diagnostic Commands

Use these commands to diagnose issues:

| Command | What It Shows |
|---|---|
| `health_check` | Server status, version, engine version. |
| `get_last_error` | Last error message and which command caused it. |
| `get_level_info` | Current level name, path, actor count. |
| `get_actors` | All actors in the level. |
| `get_blueprint_info` | Blueprint structure (nodes, pins, variables, compile status). |
| `get_blueprint_details` | Extended Blueprint details. |
| `get_components` | All SCS components on a Blueprint. |
| `get_widget_tree` | Full widget hierarchy and properties. |
| `find_blueprints` | Search Blueprints by name, class, variable, component. |
| `find_actors` | Search actors by name, class, tag, proximity. |
| `find_assets` | Search asset registry by type and name. |
| `list_available_materials` | All available material assets. |
| `list_available_blueprints` | All available Blueprint assets. |
| `get_output_log` | Read UE output log lines (with optional filter). |

---

## Getting Help

If your issue is not covered here:

1. Check the [Command Reference](command-reference.md) for correct parameter formats.
2. Use `get_output_log` with a filter to find related UE log messages:
   ```json
   {"command": "get_output_log", "params": {"last_n_lines": 50, "filter": "Error"}}
   ```
3. Check the UE Output Log window directly for `LogArcwright` messages.
4. File an issue at `github.com/Divinity-Alpha/Arcwright/issues`.
