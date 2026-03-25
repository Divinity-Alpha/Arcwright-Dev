"""
intent_server.py
-----------------
DEVELOPMENT/TESTING TOOL ONLY — NOT part of the deployed product.

This server powers the Arcwright Generator Panel (Community/Pro/Studio tiers).
It is NOT used in the primary AI-first workflow where external AI assistants
(Claude, GPT, Cursor, etc.) connect directly via MCP/TCP and send explicit commands.

DO NOT auto-launch this server on plugin startup. It requires the 70B model
loaded on the PRO 6000 GPU and is only needed when testing the Generator Panel.

TCP server for multi-stage LLM-based intent classification.
Listens on localhost:13380 for JSON requests from the Arcwright Generator Panel.
Uses the base LLaMA 3.1 70B model (no LoRA) with few-shot prompting.

Multi-stage pipeline:
  Stage 1 — Classify: LLM classifies intent mode + rough plan + target keywords
  Stage 2 — Discover: For MODIFY/MULTI, queries UE editor for real asset names
  Stage 3 — Refine: Second LLM call with discovery results for exact plan
  Stage 4 — Return: Final refined plan sent to panel

Usage:
    python scripts/intent_server.py

Protocol (same as UE command server — newline-delimited JSON):
    Request:  {"prompt": "Change the wall texture to brick"}\n
    Response: {"mode": "MODIFY", "summary": "...", ...}\n
"""

import json
import os
import re
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path

# Add parent to path for imports
PROJECT_ROOT = str(Path(__file__).parent.parent)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

INTENT_PORT = 13380
UE_PORT = 13377
BASE_MODEL = "meta-llama/Meta-Llama-3.1-70B"

# LoRA adapter paths for DSL generation (Fix 1)
DSL_ADAPTERS = {
    "blueprint": os.path.join(PROJECT_ROOT, "models", "blueprint-lora-v12", "final"),
    "bt": os.path.join(PROJECT_ROOT, "models", "bt-lora-v3", "final"),
    "dt": os.path.join(PROJECT_ROOT, "models", "dt-lora-v3", "final"),
}

# System prompt paths for DSL generation
SYSTEM_PROMPT_PATHS = {
    "blueprint": os.path.join(PROJECT_ROOT, "scripts", "system_prompt.txt"),
    "bt": os.path.join(PROJECT_ROOT, "scripts", "bt_system_prompt.txt"),
    "dt": os.path.join(PROJECT_ROOT, "scripts", "dt_system_prompt.txt"),
}

# ============================================================
# Command whitelist and validation (Fix 1 from patch)
# ============================================================

COMMAND_WHITELIST = {
    # Blueprint authoring
    "create_blueprint_from_dsl",
    "import_blueprint_ir",
    "get_blueprint_info",
    "modify_blueprint",
    "duplicate_blueprint",
    "rename_asset",
    "reparent_blueprint",
    # Level / actors
    "spawn_actor",
    "get_actors",
    "move_actor",
    "delete_actor",
    "get_level_info",
    "save_all",
    "save_level",
    "quit_editor",
    "get_output_log",
    "play_in_editor",
    "stop_play",
    # Components
    "add_component",
    "get_components",
    "remove_component",
    "set_component_property",
    # Materials
    "create_material_instance",
    "apply_material",
    "set_actor_material",
    "create_simple_material",
    "create_textured_material",
    # AI / BehaviorTree
    "create_behavior_tree_from_dsl",
    "get_behavior_tree_info",
    "setup_ai_for_pawn",
    # DataTable
    "create_data_table_from_dsl",
    "get_data_table_info",
    # Widgets
    "create_widget_blueprint",
    "add_widget_child",
    "set_widget_property",
    "get_widget_tree",
    "remove_widget",
    "create_widget_from_html",
    # Scene
    "setup_scene_lighting",
    "set_game_mode",
    "add_post_process_volume",
    "set_post_process_settings",
    # Physics / movement
    "set_movement_defaults",
    "add_physics_constraint",
    "break_constraint",
    # Splines
    "create_spline_actor",
    "add_spline_point",
    "get_spline_info",
    # Asset import
    "import_static_mesh",
    "import_texture",
    "import_sound",
    # Batch / query
    "find_blueprints",
    "find_actors",
    "find_assets",
    "batch_set_variable",
    "batch_add_component",
    "batch_apply_material",
    "batch_set_property",
    "batch_delete_actors",
    "batch_replace_material",
    # Misc
    "health_check",
    # Procedural spawn patterns
    "spawn_actor_grid",
    "spawn_actor_circle",
    "spawn_actor_line",
    # Batch transforms
    "batch_scale_actors",
    "batch_move_actors",
    # Actor config & utility
    "set_physics_enabled",
    "set_actor_visibility",
    "set_actor_mobility",
    "attach_actor_to",
    "detach_actor",
    "list_project_assets",
    "copy_actor",
    # Actor config & lifecycle
    "set_player_input_mapping",
    "set_actor_tick",
    "set_actor_lifespan",
    "get_actor_bounds",
    "set_actor_enabled",
    # SaveGame
    "create_save_game",
    # DataTable row operations
    "add_data_table_row",
    "edit_data_table_row",
    "get_data_table_rows",
    # Animation Blueprint & Montage
    "create_anim_blueprint",
    "add_anim_state",
    "add_anim_transition",
    "set_anim_state_animation",
    "create_anim_montage",
    "add_montage_section",
    "create_blend_space",
    "add_blend_space_sample",
    # Skeletal mesh & animation playback
    "set_skeletal_mesh",
    "play_animation",
    "get_skeleton_bones",
    "get_available_animations",
    # Niagara parameters
    "set_niagara_parameter",
    "activate_niagara",
    "get_niagara_parameters",
    # Sublevel / streaming
    "create_sublevel",
    "set_level_visibility",
    "get_sublevel_list",
    "move_actor_to_sublevel",
    "get_world_settings",
    "set_world_settings",
    "get_actor_class",
    "set_actor_scale",
    # Legacy names the LLM/test suite uses (mapped to real commands at execution)
    "create_blueprint",
    "create_behavior_tree",
    "create_data_table",
    "spawn_actor_at",
    "set_actor_transform",
}

COMMAND_REQUIRED_PARAMS = {
    "rename_asset":         ["old_name", "new_name"],
    "reparent_blueprint":   ["blueprint_name", "new_parent"],
    "modify_blueprint":     [],  # uses "name" — handled by command-specific alias
    "spawn_actor":          ["blueprint_name"],
    "move_actor":           ["actor_label"],
    "delete_actor":         ["actor_label"],
    "add_component":        ["blueprint_name", "component_type"],
    "remove_component":     ["blueprint_name", "component_name"],
    "set_component_property": ["blueprint_name", "component_name", "property", "value"],
    "apply_material":       ["blueprint_name", "material_path"],
    "batch_delete_actors":  ["labels"],
    # batch_apply_material, batch_set_variable, batch_set_property, batch_add_component:
    # These use params.operations[] arrays — required params live INSIDE each operation entry,
    # not at the top level. Don't enforce top-level required params for these.
    "create_behavior_tree_from_dsl": ["dsl"],
    "create_data_table_from_dsl":    ["dsl"],
    "create_blueprint_from_dsl":     ["dsl"],
    "setup_ai_for_pawn":    ["pawn_blueprint"],
}

# Map hallucinated command names to real commands
COMMAND_ALIASES = {
    "batch_spawn_actor":    "spawn_actor_at",
    "batch_create_actor":   "spawn_actor_at",
    "batch_add_actor":      "spawn_actor_at",
    "place_actor_at":       "spawn_actor_at",
    "place_actor":          "spawn_actor_at",
    "place_randomly":       "spawn_actor_at",
    "batch_scale_up":       "batch_set_property",
    "batch_scale":          "batch_set_property",
    "batch_move_by":        "batch_set_property",
    "batch_move":           "batch_set_property",
    "batch_set_visibility": "batch_set_property",
    "set_visibility":       "batch_set_property",
    "add_point_light":      "add_component",
    "set_variable":         "batch_set_variable",
    "set_default_value":    "batch_set_variable",
}

# Param name aliases (LLM uses variant names for the same thing)
# NOTE: These are applied GLOBALLY across all commands, so they must be safe for all.
# Command-specific aliases are handled in _postprocess_plan().
PARAM_ALIASES = {
    "new_value":     "value",
    "class":         "blueprint_name",
    "blueprint":     "blueprint_name",
    "actor":         "actor_label",
    "label":         "actor_label",
}

# Per-command param aliases (applied after global aliases)
# These handle cases where the same param name means different things for different commands.
COMMAND_PARAM_ALIASES = {
    "modify_blueprint": {
        "blueprint_name": "name",   # handler expects "name", not "blueprint_name"
    },
    "rename_asset": {
        "blueprint_name": "old_name",  # rename uses old_name/new_name
    },
    "batch_set_variable": {
        "value": "default_value",  # handler expects "default_value" inside operations[]
    },
}


def validate_plan(plan: dict) -> dict:
    """Validate a plan dict returned by the LLM. Removes unknown commands and
    catches missing required params. Returns a (possibly modified) plan dict."""
    warnings = []

    operations = plan.get("operations", [])
    if not isinstance(operations, list):
        cmd = plan.get("command")
        if cmd:
            warnings.append(f"Flat params detected for '{cmd}' — wrapping in operations list")
            wrapped_params = {k: v for k, v in plan.items()
                              if k not in ("command", "mode", "targets", "validation_warnings",
                                           "summary", "requires_confirmation")}
            plan["operations"] = [{"command": cmd, **wrapped_params}]
            operations = plan["operations"]
        else:
            warnings.append("No operations[] array and no top-level command — plan may be malformed")
            plan["validation_warnings"] = warnings
            return plan

    valid_operations = []
    for i, op in enumerate(operations):
        cmd = op.get("command", "")

        # Try alias mapping before whitelist rejection
        if cmd and cmd not in COMMAND_WHITELIST and cmd in COMMAND_ALIASES:
            real_cmd = COMMAND_ALIASES[cmd]
            warnings.append(
                f"Operation {i}: '{cmd}' → aliased to '{real_cmd}'"
            )
            op["command"] = real_cmd
            cmd = real_cmd

        # Check against whitelist
        if cmd and cmd not in COMMAND_WHITELIST:
            warnings.append(
                f"Operation {i}: unknown command '{cmd}' — removed. "
                f"Hint: 'add_point_light' → use add_component with component_type='PointLight'"
            )
            continue  # Drop this operation

        # Normalize param names via global aliases
        params = op.get("params", {})
        if isinstance(params, dict):
            for alias, canonical in PARAM_ALIASES.items():
                if alias in params and canonical not in params:
                    params[canonical] = params.pop(alias)

            # Apply command-specific aliases (override global where needed)
            cmd_aliases = COMMAND_PARAM_ALIASES.get(cmd, {})
            for alias, canonical in cmd_aliases.items():
                if alias in params and canonical not in params:
                    params[canonical] = params.pop(alias)

        # Check required params (only for commands that have strict requirements)
        required = COMMAND_REQUIRED_PARAMS.get(cmd, [])
        check_params = op.get("params", op)  # params may be nested or flat
        missing = [p for p in required if p not in check_params and p not in op]
        if missing:
            warnings.append(
                f"Operation {i}: command '{cmd}' missing required params: {missing} — removed"
            )
            continue  # Drop this operation

        # batch_delete_actors: labels must be a list, not a string
        if cmd == "batch_delete_actors":
            labels = op.get("labels", op.get("params", {}).get("labels"))
            if isinstance(labels, str):
                if "params" in op:
                    op["params"]["labels"] = [labels]
                else:
                    op["labels"] = [labels]
                warnings.append(
                    f"Operation {i}: batch_delete_actors.labels was a string, converted to list"
                )

        valid_operations.append(op)

    plan["operations"] = valid_operations
    if warnings:
        plan["validation_warnings"] = warnings

    return plan


def should_run_discovery(mode: str, summary: str, targets: list) -> bool:
    """Returns True if Stage 2 discovery should run.
    Extended beyond MODIFY/MULTI to catch CREATE requests that reference existing assets."""
    if mode in ("MODIFY", "MULTI"):
        return True
    if mode in ("CREATE", "SETUP"):
        asset_prefixes = ("BP_", "WBP_", "BT_", "DT_", "SM_", "T_", "MAT_", "M_")
        if any(p in summary for p in asset_prefixes):
            return True
        spawn_hints = (
            "place", "spawn", "add to level", "put", "scatter",
            "coin", "enemy", "door", "wall", "torch", "chest", "pickup",
            "around the level", "in the level", "instances of"
        )
        summary_lower = summary.lower()
        if any(hint in summary_lower for hint in spawn_hints):
            return True
    return False


# ============================================================
# Stage 1: Classification prompt
# ============================================================

CLASSIFY_PROMPT = r"""Classify user intent for Arcwright (UE5 game content tool).

MODES: CREATE (one new asset), MODIFY (change existing), QUERY (list/count), MULTI (multiple separate operations), CLARIFY (too vague)

RULES:
- One complex Blueprint = CREATE, not MULTI. A BP with timers, AI, components = still one asset.
- MULTI only when explicitly multiple separate assets/operations ("X and Y", "create X, spawn N")
- Material on actors: find_actors + batch_apply_material. Two material names: batch_replace_material.
- Never guess asset names — set targets to [] for Stage 2 discovery.
- batch_set_property is ONLY for transform/visibility/tags, never materials.

Output ONLY JSON: {"mode":"...","summary":"...","targets":[],"requires_confirmation":false,"operations":[{"step":1,"command":"...","params":{...},"depends_on":null}]}

User: Create a health pickup that heals 25 HP
{"mode":"CREATE","summary":"Create health pickup BP","targets":[],"requires_confirmation":false,"operations":[{"step":1,"command":"create_blueprint","params":{"prompt":"health pickup that heals 25 HP"},"depends_on":null}]}
User: Make a patrol AI for enemies
{"mode":"CREATE","summary":"Create patrol AI BT","targets":[],"requires_confirmation":false,"operations":[{"step":1,"command":"create_behavior_tree","params":{"prompt":"patrol AI for enemies"},"depends_on":null}]}
User: Set health to 200 on all enemies
{"mode":"MODIFY","summary":"Set Health=200 on enemies","targets":["enemy"],"requires_confirmation":true,"operations":[{"step":1,"command":"batch_set_variable","params":{"variable_name":"Health","default_value":"200"},"depends_on":null}]}
User: Delete all coins
{"mode":"MODIFY","summary":"Delete coin actors","targets":["coin"],"requires_confirmation":true,"operations":[{"step":1,"command":"batch_delete_actors","params":{},"depends_on":null}]}
User: How many enemies are in the level?
{"mode":"QUERY","summary":"Count enemies","targets":[],"requires_confirmation":false,"operations":[{"step":1,"command":"find_actors","params":{"name_filter":"enemy"},"depends_on":null}]}
User: List all blueprints
{"mode":"QUERY","summary":"List blueprints","targets":[],"requires_confirmation":false,"operations":[{"step":1,"command":"find_blueprints","params":{},"depends_on":null}]}
User: Create an enemy and spawn 5 of them
{"mode":"MULTI","summary":"Create enemy and spawn 5","targets":[],"requires_confirmation":true,"operations":[{"step":1,"command":"create_blueprint","params":{"prompt":"enemy"},"depends_on":null},{"step":2,"command":"spawn_actor_at","params":{"count":5},"depends_on":1}]}
User: Make it better
{"mode":"CLARIFY","summary":"What specifically would you like to improve?","targets":[],"requires_confirmation":false,"operations":[]}
User: """

# ============================================================
# Stage 3: Refinement prompt template
# ============================================================

REFINE_PROMPT_TEMPLATE = r"""You are the plan generator for Arcwright, a tool that creates Unreal Engine 5 game content.

You have been given the user's request, discovered assets from the UE project, and the classified intent mode.
Your job: produce a concrete execution plan using only valid Arcwright commands and the REAL asset names from discovery.

=== CRITICAL FORMAT RULE ===
ALL batch commands MUST use params with an "operations" array inside.
NEVER return flat params at the top level of a batch command.

CORRECT: {{"command":"batch_set_variable","params":{{"operations":[{{"blueprint":"BP_Enemy","variable_name":"Health","default_value":"200"}}]}}}}
WRONG:   {{"command":"batch_set_variable","params":{{"variable_name":"Health","default_value":"200"}}}}

CORRECT: {{"command":"batch_set_property","params":{{"operations":[{{"actor_label":"Wall_01","property":"visibility","value":false}}]}}}}
WRONG:   {{"command":"batch_set_property","params":{{"property_name":"visibility","value":false}}}}

This rule applies to: batch_set_variable, batch_add_component, batch_apply_material, batch_set_property.

=== ASSET NAME RULE ===
Use ONLY asset names from the discovered assets provided to you. If the user said "gold coin" and discovery found "BP_Coin", use "BP_Coin". Never guess asset names.

=== COMMAND REFERENCE ===
batch_set_variable: params.operations = [{{"blueprint":"BP_Name","variable_name":"Var","default_value":"val"}}]
batch_add_component: params.operations = [{{"blueprint":"BP_Name","component_type":"PointLight","component_name":"Light1"}}]
batch_apply_material: params.operations = [{{"actor_label":"Actor1","material_path":"/Game/..."}}]
batch_set_property: params.operations = [{{"actor_label":"Actor1","property":"scale","value":{{"x":1.5,"y":1.5,"z":1.5}}}}]
batch_delete_actors: params.labels = ["Actor1","Actor2"] (MUST be a list)
batch_replace_material: params.old_material + params.new_material (full paths from discovery)
rename_asset: params.old_name + params.new_name (BOTH required)
modify_blueprint: params.name + set_class_defaults/add_variables/remove_variables

Output ONLY valid JSON:

Example:
User request: "Set health to 200 on all enemies"
Classification: mode=MODIFY
Discovery: Blueprints=[{{"name":"BP_Enemy","variables":["Health","Speed"]}},{{"name":"BP_EnemyBoss","variables":["Health","Armor"]}}]
{{"mode":"MODIFY","summary":"Set Health=200 on BP_Enemy and BP_EnemyBoss","requires_confirmation":true,"operations":[{{"step":1,"command":"batch_set_variable","params":{{"operations":[{{"blueprint":"BP_Enemy","variable_name":"Health","default_value":"200"}},{{"blueprint":"BP_EnemyBoss","variable_name":"Health","default_value":"200"}}]}},"depends_on":null}}]}}

Example:
User request: "Hide all the torches"
Classification: mode=MODIFY
Discovery: Actors=[{{"label":"BP_Torch_01","class":"BP_Torch_C"}},{{"label":"BP_Torch_02","class":"BP_Torch_C"}}]
{{"mode":"MODIFY","summary":"Hide all torches","requires_confirmation":true,"operations":[{{"step":1,"command":"batch_set_property","params":{{"operations":[{{"actor_label":"BP_Torch_01","property":"visibility","value":false}},{{"actor_label":"BP_Torch_02","property":"visibility","value":false}}]}},"depends_on":null}}]}}

Example:
User request: "Scale all enemies up by 1.5"
Classification: mode=MODIFY
Discovery: Actors=[{{"label":"Enemy_01","class":"BP_Enemy_C"}},{{"label":"Enemy_02","class":"BP_Enemy_C"}}]
{{"mode":"MODIFY","summary":"Scale enemies up 1.5x","requires_confirmation":true,"operations":[{{"step":1,"command":"batch_set_property","params":{{"operations":[{{"actor_label":"Enemy_01","property":"scale","value":{{"x":1.5,"y":1.5,"z":1.5}}}},{{"actor_label":"Enemy_02","property":"scale","value":{{"x":1.5,"y":1.5,"z":1.5}}}}]}},"depends_on":null}}]}}

Example:
User request: "Clear out all the torches"
Classification: mode=MODIFY
Discovery: Actors=[{{"label":"BP_Torch_01","class":"BP_Torch"}},{{"label":"BP_Torch_02","class":"BP_Torch"}}]
{{"mode":"MODIFY","summary":"Delete all torch actors","requires_confirmation":true,"operations":[{{"step":1,"command":"batch_delete_actors","params":{{"labels":["BP_Torch_01","BP_Torch_02"]}},"depends_on":null}}]}}

User request: "{user_prompt}"
Classification: mode={mode}
Discovery: {discovery_text}
"""


def log(msg):
    """Print with timestamp, handling Windows encoding."""
    ts = time.strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}")
    except UnicodeEncodeError:
        print(f"[{ts}] {msg.encode('ascii', errors='replace').decode()}")
    sys.stdout.flush()


# ============================================================
# Lightweight TCP client for querying UE command server
# ============================================================

class UECommandClient:
    """Minimal TCP client for querying UE command server on port 13377."""

    def __init__(self, host="127.0.0.1", port=UE_PORT, timeout=10.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send_command(self, command, params=None):
        """Send a single command and return parsed response. Creates a new connection per call."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.host, self.port))
            request = {"command": command, "params": params or {}}
            sock.sendall((json.dumps(request) + "\n").encode("utf-8"))

            # Read response
            data = b""
            while True:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break

            response_str = data.decode("utf-8").strip()
            if not response_str:
                return None

            return json.loads(response_str)
        except Exception as e:
            log(f"UE query error ({command}): {e}")
            return None
        finally:
            sock.close()

    def find_actors(self, **kwargs):
        return self.send_command("find_actors", kwargs)

    def find_blueprints(self, **kwargs):
        return self.send_command("find_blueprints", kwargs)

    def find_assets(self, **kwargs):
        return self.send_command("find_assets", kwargs)

    def get_level_info(self):
        return self.send_command("get_level_info")


# ============================================================
# JSON extraction and repair utilities
# ============================================================

def extract_json(response):
    """Extract and validate JSON from LLM output. Returns parsed dict or None."""
    # Strip markdown code fences
    if "```" in response:
        fence_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if fence_match:
            response = fence_match.group(1)

    # Strip any text after the final } (LLM sometimes appends explanatory text)
    last_brace = response.rfind("}")
    if last_brace >= 0:
        response = response[:last_brace + 1]

    # Extract first complete JSON object
    json_start = response.find("{")
    json_end = response.rfind("}") + 1
    if json_start < 0 or json_end <= json_start:
        return None

    json_str = response[json_start:json_end]
    # Trim to first balanced object (handles nested braces correctly)
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(json_str):
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                json_str = json_str[:i + 1]
                break

    # Try parse directly
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Try repair common LLM JSON errors
    repaired = json_str
    repaired = re.sub(r'([^"\\])"([^",:\[\]{}]+)([}\]])', r'\1"\2"\3', repaired)
    repaired = re.sub(r'([a-zA-Z0-9_ .!?])(})', r'\1"\2', repaired)
    try:
        parsed = json.loads(repaired)
        log("JSON repaired successfully")
        return parsed
    except json.JSONDecodeError:
        return None


# ============================================================
# Intent Server
# ============================================================

class IntentServer:
    """TCP server with multi-stage intent classification via LLM inference."""

    def __init__(self, port=INTENT_PORT):
        self.port = port
        self.model = None
        self.tokenizer = None
        self.running = False
        self.gpu_lock = threading.Lock()
        self.adapters_loaded = False
        self._gen_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gen")

    def load_model(self):
        """Load the base LLaMA 3.1 70B model in 8-bit (no LoRA adapter)."""
        log(f"Loading base model: {BASE_MODEL}")
        log("This uses the BASE model (no LoRA) -- intent classification is a general task")

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # PRO 6000

        log("Loading tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        log("Loading model in 8-bit quantization...")
        self.model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            load_in_8bit=True,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        self.model.eval()
        log(f"Base model loaded. VRAM: {torch.cuda.memory_allocated(0) / 1e9:.1f} GB")

        # Load LoRA adapters for DSL generation (Fix 1)
        self._load_adapters()

        log(f"Ready. VRAM: {torch.cuda.memory_allocated(0) / 1e9:.1f} GB")

    def _llm_generate(self, prompt_text, max_tokens=400, timeout=120):
        """Run LLM inference and return extracted JSON dict, or None on failure.
        Hard timeout prevents cascading GPU lock starvation from hung generation.
        """
        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

        inputs = self.tokenizer(prompt_text, return_tensors="pt").to(self.model.device)
        input_len = inputs["input_ids"].shape[1]
        log(f"[LLMGenerate] input_len={input_len} tokens, max_new={max_tokens}, timeout={timeout}s")

        # Stop when we detect a complete JSON object
        class JsonStopCriteria(StoppingCriteria):
            def __init__(self, tokenizer, input_length):
                self.tokenizer = tokenizer
                self.input_length = input_length

            def __call__(self, input_ids, scores, **kwargs):
                generated = input_ids[0][self.input_length:]
                if len(generated) < 5:
                    return False
                text = self.tokenizer.decode(generated, skip_special_tokens=True)
                depth = 0
                in_string = False
                escape = False
                started = False
                for ch in text:
                    if escape:
                        escape = False
                        continue
                    if ch == '\\':
                        escape = True
                        continue
                    if ch == '"':
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if ch == '{':
                        depth += 1
                        started = True
                    elif ch == '}':
                        depth -= 1
                        if started and depth == 0:
                            return True
                return False

        stop_criteria = StoppingCriteriaList([JsonStopCriteria(self.tokenizer, input_len)])

        def _do_generate():
            with torch.no_grad():
                return self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.0,
                    do_sample=False,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    stopping_criteria=stop_criteria,
                )

        # Use thread pool with hard timeout to prevent GPU lock starvation
        gen_start = time.time()
        try:
            future = self._gen_executor.submit(_do_generate)
            outputs = future.result(timeout=timeout)
        except FuturesTimeout:
            elapsed = time.time() - gen_start
            log(f"[LLMGenerate] TIMEOUT after {elapsed:.0f}s — generation cancelled")
            # Cancel won't stop CUDA, but at least we release the GPU lock
            future.cancel()
            return None
        except Exception as e:
            log(f"[LLMGenerate] ERROR: {e}")
            return None

        elapsed = time.time() - gen_start
        generated = outputs[0][input_len:]
        response = self.tokenizer.decode(generated, skip_special_tokens=True).strip()
        log(f"Raw model output ({elapsed:.1f}s, {len(generated)} tokens): {response[:300]}")

        return extract_json(response)

    # ── LoRA Adapter Management (Fix 1) ─────────────────────

    def _load_adapters(self):
        """Load LoRA adapters for DSL generation onto the base model."""
        from peft import PeftModel

        first = True
        for domain, adapter_path in DSL_ADAPTERS.items():
            if not os.path.isdir(adapter_path):
                log(f"WARNING: Adapter not found for {domain}: {adapter_path}")
                continue
            try:
                if first:
                    log(f"Loading first adapter ({domain}) from {adapter_path}")
                    self.model = PeftModel.from_pretrained(
                        self.model, adapter_path, adapter_name=domain
                    )
                    first = False
                else:
                    log(f"Loading adapter ({domain}) from {adapter_path}")
                    self.model.load_adapter(adapter_path, adapter_name=domain)
                log(f"  Adapter '{domain}' loaded")
            except Exception as e:
                log(f"WARNING: Failed to load adapter '{domain}': {e}")

        if not first:
            # Adapters loaded — disable them so base model is used for intent classification
            self.model.disable_adapter_layers()
            self.adapters_loaded = True
            log("All adapters loaded and disabled (base model active for classification)")
        else:
            log("WARNING: No adapters loaded — DSL generation will not be available")

    def _generate_dsl(self, domain, prompt):
        """Generate DSL text using LoRA-adapted model for the given domain."""
        import torch

        if not self.adapters_loaded:
            return None, "No adapters loaded"

        # Read system prompt
        prompt_path = SYSTEM_PROMPT_PATHS.get(domain)
        if not prompt_path or not os.path.isfile(prompt_path):
            return None, f"System prompt not found for domain '{domain}'"

        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()

        # Format as Llama 3.1 chat (manual template — base model tokenizer may not have chat_template)
        input_text = (
            f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
            f"{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
            f"{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        )

        inputs = self.tokenizer(input_text, return_tensors="pt")
        input_ids = inputs["input_ids"].to("cuda:0")
        attention_mask = inputs["attention_mask"].to("cuda:0")
        input_len = input_ids.shape[1]

        # Enable adapter for this domain
        self.model.enable_adapter_layers()
        self.model.set_adapter(domain)

        # Stop token IDs
        stop_ids = [self.tokenizer.eos_token_id]
        for special in ["<|eot_id|>", "<|end_of_text|>"]:
            tid = self.tokenizer.convert_tokens_to_ids(special)
            if tid is not None and tid != self.tokenizer.unk_token_id:
                stop_ids.append(tid)

        max_tokens = 2048 if domain == "blueprint" else 1024

        try:
            with torch.no_grad():
                outputs = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=max_tokens,
                    temperature=0.1,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    eos_token_id=stop_ids,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
        finally:
            # Always disable adapters after generation (back to base model)
            self.model.disable_adapter_layers()

        generated = outputs[0][input_len:]
        raw = self.tokenizer.decode(generated, skip_special_tokens=True).strip()
        log(f"DSL raw output ({domain}, {len(generated)} tokens): {raw[:200]}")

        dsl = self._extract_dsl(domain, raw)
        return dsl, raw

    def _extract_dsl(self, domain, raw):
        """Extract DSL text from raw model output."""
        markers = {
            "blueprint": "BLUEPRINT:",
            "bt": "BEHAVIORTREE:",
            "dt": "DATATABLE:",
        }
        marker = markers.get(domain, "BLUEPRINT:")

        lines = raw.split("\n")
        dsl_lines = []
        in_dsl = False

        for line in lines:
            s = line.strip()
            if s.startswith(marker):
                in_dsl = True
            if in_dsl and s and any(s.startswith(m) for m in [
                "## ", "Valid node", "Rules for", "---", "Line |",
                "**", "### ", "IN:", "OUT:", "Your output",
                "END OUTPUT", "OUTPUT FORMAT",
            ]):
                break
            if in_dsl and s.startswith("Create a Blueprint"):
                break
            if in_dsl and "Event_Unknown" in s:
                break
            if in_dsl and s in ("{", "}"):
                break
            if in_dsl:
                dsl_lines.append(line)

        # Trim trailing blanks
        while dsl_lines and not dsl_lines[-1].strip():
            dsl_lines.pop()

        # Strip trailing delimiters (Lesson #25)
        if dsl_lines:
            dsl_lines[-1] = re.sub(r'\s*[{}\(\);>]+\s*$', '', dsl_lines[-1])

        return "\n".join(dsl_lines).strip()

    def _handle_generate_dsl(self, domain, prompt):
        """Handle a generate_dsl command. Returns JSON string."""
        if domain not in DSL_ADAPTERS:
            return json.dumps({
                "status": "error",
                "message": f"Unknown domain: {domain}. Use 'blueprint', 'bt', or 'dt'.",
            })
        if not prompt:
            return json.dumps({"status": "error", "message": "Empty prompt"})

        log(f"[Generate DSL] domain={domain}, prompt={prompt[:100]}")
        start = time.time()

        # Acquire GPU lock with timeout (don't block forever if another op is hung)
        GPU_LOCK_TIMEOUT = 180  # 3 min — classification takes ~20s, generation ~120s max
        GENERATION_TIMEOUT = 300  # 5 min — absolute max for any single generation
        acquired = self.gpu_lock.acquire(timeout=GPU_LOCK_TIMEOUT)
        if not acquired:
            log(f"[Generate DSL] TIMEOUT: Could not acquire GPU lock after {GPU_LOCK_TIMEOUT}s")
            return json.dumps({"status": "error", "message": f"GPU busy — try again in a few seconds"})
        try:
            future = self._gen_executor.submit(self._generate_dsl, domain, prompt)
            dsl, raw = future.result(timeout=GENERATION_TIMEOUT)
        except FuturesTimeoutError:
            log(f"[Generate DSL] TIMEOUT: Generation exceeded {GENERATION_TIMEOUT}s")
            return json.dumps({"status": "error", "message": f"Generation timed out after {GENERATION_TIMEOUT}s"})
        except Exception as e:
            log(f"[Generate DSL] ERROR: {e}")
            return json.dumps({"status": "error", "message": str(e)})
        finally:
            self.gpu_lock.release()

        elapsed = time.time() - start
        log(f"[Generate DSL] Done in {elapsed:.1f}s, DSL length={len(dsl) if dsl else 0}")

        if not dsl:
            return json.dumps({
                "status": "error",
                "message": "Empty DSL generated",
                "raw_output": (raw or "")[:500],
            })

        return json.dumps({
            "status": "ok",
            "domain": domain,
            "dsl": dsl,
        })

    # ── Stage 1: Classify ──────────────────────────────────

    def _stage1_classify(self, prompt):
        """First LLM call: classify intent mode and extract rough plan + target keywords."""
        log(f"[Stage 1] Classifying: {prompt[:100]}")

        input_text = CLASSIFY_PROMPT + prompt + "\n"
        parsed = self._llm_generate(input_text, max_tokens=300)

        if parsed is None:
            # Fix 2: Fall back to CREATE (not CLARIFY) — assume user wants to create something
            log(f"[Stage 1] WARNING: LLM returned invalid JSON, falling back to CREATE")
            return {
                "mode": "CREATE",
                "summary": prompt,
                "targets": [],
                "requires_confirmation": False,
                "operations": [{
                    "step": 1,
                    "command": "create_blueprint",
                    "params": {"prompt": prompt},
                    "depends_on": None,
                }],
            }

        # Ensure required fields
        parsed.setdefault("mode", "CREATE")
        parsed.setdefault("summary", prompt)
        parsed.setdefault("targets", [])
        parsed.setdefault("operations", [])
        parsed.setdefault("requires_confirmation", parsed["mode"] in ("MODIFY", "MULTI"))

        # Validate plan against command whitelist (Fix 1)
        parsed = validate_plan(parsed)
        if parsed.get("validation_warnings"):
            for w in parsed["validation_warnings"]:
                log(f"[Stage 1] WARN: {w}")

        log(f"[Stage 1] Result: mode={parsed['mode']}, targets={parsed.get('targets', [])}, ops={len(parsed['operations'])}")
        return parsed

    # ── Stage 2: Discover ──────────────────────────────────

    def _stage2_discover(self, stage1_result):
        """Query UE editor for real asset names based on classification targets."""
        targets = stage1_result.get("targets", [])
        operations = stage1_result.get("operations", [])

        log(f"[Stage 2] Discovering targets: {targets}")

        try:
            ue = UECommandClient(timeout=10.0)
        except Exception as e:
            log(f"[Stage 2] Cannot create UE client: {e}")
            return None

        discovery = {}

        try:
            # Query actors for each target keyword
            for target in targets:
                key = f"actors_{target}"
                if key not in discovery:
                    result = ue.find_actors(name_filter=target)
                    if result and result.get("status") == "ok":
                        discovery[key] = result.get("data", {})
                        actors = result.get("data", {}).get("actors", [])
                        log(f"[Stage 2] find_actors({target}): {len(actors)} found")

            # Query blueprints for each target keyword
            for target in targets:
                key = f"blueprints_{target}"
                if key not in discovery:
                    result = ue.find_blueprints(name_filter=target)
                    if result and result.get("status") == "ok":
                        discovery[key] = result.get("data", {})
                        bps = result.get("data", {}).get("blueprints", [])
                        log(f"[Stage 2] find_blueprints({target}): {len(bps)} found")

            # For batch_add_component, ensure we query blueprints even with empty targets
            needs_bp_query = any(
                op.get("command", "") in ("batch_add_component", "batch_set_variable")
                for op in operations
            )
            if needs_bp_query and not any(k.startswith("blueprints_") for k in discovery):
                # Broad blueprint search when no target-specific results found
                for target in (targets if targets else ["*"]):
                    key = f"blueprints_{target}"
                    if key not in discovery:
                        result = ue.find_blueprints(name_filter=target if target != "*" else "")
                        if result and result.get("status") == "ok":
                            discovery[key] = result.get("data", {})
                            bps = result.get("data", {}).get("blueprints", [])
                            log(f"[Stage 2] find_blueprints({target}): {len(bps)} found")

            # For batch_delete_actors or batch_apply_material, ensure we query actors
            needs_actor_query = any(
                op.get("command", "") in ("batch_delete_actors", "batch_apply_material", "find_actors")
                for op in operations
            )
            if needs_actor_query and not any(k.startswith("actors_") for k in discovery):
                for target in (targets if targets else ["*"]):
                    key = f"actors_{target}"
                    if key not in discovery:
                        result = ue.find_actors(name_filter=target if target != "*" else "")
                        if result and result.get("status") == "ok":
                            discovery[key] = result.get("data", {})
                            actors = result.get("data", {}).get("actors", [])
                            log(f"[Stage 2] find_actors({target}): {len(actors)} found")

            # For material-related operations, also query available materials
            needs_materials = any(
                op.get("command", "") in ("batch_apply_material", "batch_replace_material")
                for op in operations
            )
            if needs_materials:
                # Search for materials by name from operation params first
                mat_search_terms = set()
                for op in operations:
                    mat_path = op.get("params", {}).get("material_path", "")
                    if mat_path:
                        mat_search_terms.add(mat_path)
                    old_mat = op.get("params", {}).get("old_material", "")
                    new_mat = op.get("params", {}).get("new_material", "")
                    if old_mat: mat_search_terms.add(old_mat)
                    if new_mat: mat_search_terms.add(new_mat)

                # Search for materials matching param names (highest priority)
                for term in mat_search_terms:
                    key = f"materials_{term}"
                    result = ue.find_assets(type="Material", name_filter=term)
                    if result and result.get("status") == "ok":
                        discovery[key] = result.get("data", {})
                        assets = result.get("data", {}).get("assets", [])
                        log(f"[Stage 2] find_assets(Material, {term}): {len(assets)} found")

                # Also search by target keywords
                for target in targets:
                    key = f"materials_{target}"
                    if key not in discovery:
                        result = ue.find_assets(type="Material", name_filter=target)
                        if result and result.get("status") == "ok":
                            discovery[key] = result.get("data", {})
                            assets = result.get("data", {}).get("assets", [])
                            log(f"[Stage 2] find_assets(Material, {target}): {len(assets)} found")

                # Broad material search if no keyword-specific results
                if not any(k.startswith("materials_") for k in discovery):
                    result = ue.find_assets(type="Material", max_results=30)
                    if result and result.get("status") == "ok":
                        discovery["materials_all"] = result.get("data", {})

            # Get level info for context
            result = ue.get_level_info()
            if result and result.get("status") == "ok":
                discovery["level_info"] = result.get("data", {})

        except Exception as e:
            log(f"[Stage 2] Discovery error: {e}")

        if not discovery:
            log("[Stage 2] No discovery results")
            return None

        log(f"[Stage 2] Discovery complete: {len(discovery)} result sets")
        return discovery

    # ── Stage 3: Refine ────────────────────────────────────

    def _stage3_refine(self, original_prompt, stage1_result, discovery):
        """Second LLM call: generate exact plan with concrete asset names from discovery."""
        mode = stage1_result.get("mode", "MODIFY")

        # Condense discovery results into a compact text block
        discovery_parts = []

        for key, data in discovery.items():
            if key == "level_info":
                level_name = data.get("level_name", "unknown")
                actor_count = data.get("actor_count", 0)
                discovery_parts.append(f"Level: {level_name} ({actor_count} actors)")
                continue

            if key.startswith("actors_"):
                actors = data.get("actors", [])
                if actors:
                    # Condense: show up to 20 actors with label and class
                    entries = []
                    for a in actors[:20]:
                        label = a.get("label", "?")
                        cls = a.get("class", "?")
                        entries.append(f'{{"label":"{label}","class":"{cls}"}}')
                    discovery_parts.append(f"Actors=[{','.join(entries)}]")
                    if len(actors) > 20:
                        discovery_parts.append(f"  ...and {len(actors) - 20} more actors")

            elif key.startswith("blueprints_"):
                bps = data.get("blueprints", [])
                if bps:
                    entries = []
                    for b in bps[:10]:
                        name = b.get("name", "?")
                        variables = [v.get("name", "?") for v in b.get("variables", [])][:5]
                        entries.append(f'{{"name":"{name}","variables":{json.dumps(variables)}}}')
                    discovery_parts.append(f"Blueprints=[{','.join(entries)}]")

            elif key.startswith("materials_"):
                assets = data.get("assets", [])
                if assets:
                    entries = []
                    for a in assets[:15]:
                        name = a.get("name", "?")
                        path = a.get("path", "?")
                        entries.append(f'{{"name":"{name}","path":"{path}"}}')
                    discovery_parts.append(f"Materials=[{','.join(entries)}]")

        discovery_text = "\n".join(discovery_parts) if discovery_parts else "No assets found"

        log(f"[Stage 3] Refining with {len(discovery_parts)} discovery sections")

        # Build refinement prompt
        refine_prompt = REFINE_PROMPT_TEMPLATE.format(
            user_prompt=original_prompt,
            mode=mode,
            discovery_text=discovery_text,
        )

        parsed = self._llm_generate(refine_prompt, max_tokens=500)

        if parsed is None:
            log("[Stage 3] WARNING: Refinement LLM call failed, returning Stage 1 result")
            return json.dumps(stage1_result)

        # Ensure required fields
        parsed.setdefault("mode", mode)
        parsed.setdefault("summary", stage1_result.get("summary", original_prompt))
        parsed.setdefault("operations", [])
        parsed.setdefault("requires_confirmation", mode in ("MODIFY", "MULTI"))

        # If refinement produced 0 operations, fall back to Stage 1
        if not parsed.get("operations"):
            log("[Stage 3] WARNING: Refined plan has 0 operations, falling back to Stage 1")
            return json.dumps(stage1_result)

        # Validate plan against command whitelist (Fix 1)
        parsed = validate_plan(parsed)
        if parsed.get("validation_warnings"):
            for w in parsed["validation_warnings"]:
                log(f"[Stage 3] WARN: {w}")

        log(f"[Stage 3] Refined plan: mode={parsed['mode']}, ops={len(parsed['operations'])}")
        return json.dumps(parsed)

    # ── Post-processing: hard override for known LLM mistakes ──────

    def _postprocess_plan(self, plan):
        """Hard-override post-processing for known LLM routing mistakes.
        Fixes plans AFTER LLM generation so even if the prompt is ignored,
        the correct commands are used.
        """
        log(f"[PostProcess] ENTER — plan type={type(plan).__name__}")
        if isinstance(plan, str):
            try:
                plan = json.loads(plan)
            except json.JSONDecodeError:
                log(f"[PostProcess] EXIT — unparseable string, returning as-is")
                return plan  # can't fix what we can't parse

        ops = plan.get("operations", [])
        log(f"[PostProcess] mode={plan.get('mode','?')}, {len(ops)} operations: "
            f"{[op.get('command','?') for op in ops]}")

        MATERIAL_KEYWORDS = {"material", "texture", "mat_", "m_", "brick", "stone",
                             "wood", "metal", "concrete", "marble", "glass"}

        operations = plan.get("operations", [])
        changed = False
        for op in operations:
            cmd = op.get("command", "")
            params = op.get("params", {})

            # Fix 1: batch_set_property with material-like values → batch_apply_material
            if cmd == "batch_set_property":
                prop_name = str(params.get("property_name", "") or params.get("property", "")).lower()
                value = str(params.get("value", "")).lower()

                is_material = (
                    prop_name in ("material", "texture", "material_path") or
                    any(kw in value for kw in MATERIAL_KEYWORDS)
                )

                if is_material:
                    log(f"[PostProcess] REWRITE: batch_set_property(material) → batch_apply_material")
                    actual_value = params.get("value", "") or params.get("material_path", "")
                    # Rebuild as batch_apply_material — operations[] will be filled
                    # from discovery at execution time, or we build a placeholder
                    op_list = params.get("operations", [])
                    if not op_list:
                        # Build from flat params if no operations array
                        op_list = [{"material_path": actual_value}]
                    else:
                        # Ensure each operation has material_path
                        for sub_op in op_list:
                            if "material_path" not in sub_op:
                                sub_op["material_path"] = actual_value
                    op["command"] = "batch_apply_material"
                    op["params"] = {"operations": op_list}
                    changed = True

            # Fix 2: batch_apply_material with flat params → wrap in operations[]
            elif cmd == "batch_apply_material":
                if "operations" not in params:
                    mat_path = params.get("material_path", params.get("value", ""))
                    if mat_path:
                        log(f"[PostProcess] RESHAPE: batch_apply_material flat → operations[]")
                        op["params"] = {"operations": [{"material_path": mat_path}]}
                        changed = True

            # Fix 3: batch_set_variable with flat params → wrap in operations[]
            elif cmd == "batch_set_variable":
                if "operations" not in params:
                    # LLM outputs flat: {variable_name: "Health", value: 200} or {blueprint_name: ..., ...}
                    bp_name = params.get("blueprint_name", params.get("name", ""))
                    var_name = params.get("variable_name", "")
                    var_value = params.get("default_value", params.get("value", params.get("new_value", "")))
                    if var_name:
                        log(f"[PostProcess] RESHAPE: batch_set_variable flat → operations[]")
                        op["params"] = {"operations": [{"blueprint": bp_name, "variable_name": var_name, "default_value": str(var_value)}]}
                        changed = True

            # Fix 4: batch_set_property with flat params → wrap in operations[]
            elif cmd == "batch_set_property":
                if "operations" not in params:
                    actor_label = params.get("actor_label", "")
                    prop = params.get("property", params.get("property_name", params.get("property_path", "")))
                    value = params.get("value", "")
                    relative = params.get("relative", False)
                    if prop or actor_label:
                        log(f"[PostProcess] RESHAPE: batch_set_property flat → operations[]")
                        sub_op = {"actor_label": actor_label, "property": prop, "value": value}
                        if relative:
                            sub_op["relative"] = True
                        op["params"] = {"operations": [sub_op]}
                        changed = True

            # Fix 5: modify_blueprint normalization
            elif cmd == "modify_blueprint":
                # Ensure "name" param exists (LLM may use "blueprint_name")
                if "name" not in params and "blueprint_name" in params:
                    params["name"] = params.pop("blueprint_name")
                    changed = True

                # Strip _C suffix from blueprint name (LLM hallucinates class suffix)
                bp_name = params.get("name", "")
                if bp_name.endswith("_C"):
                    params["name"] = bp_name[:-2]
                    log(f"[PostProcess] STRIP: modify_blueprint name '{bp_name}' → '{params['name']}'")
                    changed = True

                # Fix set_class_defaults: array of {variable_name, default_value} → dict
                scd = params.get("set_class_defaults")
                if isinstance(scd, list):
                    # Convert [{variable_name: "Health", default_value: "200"}, ...] → {Health: "200", ...}
                    defaults_dict = {}
                    for entry in scd:
                        if isinstance(entry, dict):
                            vn = entry.get("variable_name", entry.get("name", ""))
                            dv = entry.get("default_value", entry.get("value", ""))
                            if vn:
                                defaults_dict[vn] = str(dv)
                    if defaults_dict:
                        log(f"[PostProcess] RESHAPE: modify_blueprint set_class_defaults array → dict")
                        params["set_class_defaults"] = defaults_dict
                        changed = True

            # Fix 6: batch_set_variable — strip _C suffix from blueprint names
            elif cmd == "batch_set_variable":
                for sub_op in params.get("operations", []):
                    bp = sub_op.get("blueprint", "")
                    if bp.endswith("_C"):
                        sub_op["blueprint"] = bp[:-2]
                        log(f"[PostProcess] STRIP: batch_set_variable blueprint '{bp}' → '{sub_op['blueprint']}'")
                        changed = True

            # Fix 7: batch_delete_actors with operations[] → labels[]
            elif cmd == "batch_delete_actors":
                if "operations" in params and "labels" not in params:
                    labels = []
                    for sub_op in params["operations"]:
                        if isinstance(sub_op, dict):
                            label = sub_op.get("actor_label", sub_op.get("label", sub_op.get("name", "")))
                            if label:
                                labels.append(label)
                        elif isinstance(sub_op, str):
                            labels.append(sub_op)
                    if labels:
                        log(f"[PostProcess] RESHAPE: batch_delete_actors operations[] → labels[] ({len(labels)} labels)")
                        params.pop("operations")
                        params["labels"] = labels
                        changed = True

            # Fix 8: Aliased commands with wrong param formats
            # batch_set_property from aliased batch_scale/batch_scale_up
            if cmd == "batch_set_property" and "operations" not in params:
                sf = params.get("scale_factor", params.get("scale", None))
                if sf is not None:
                    try:
                        sf = float(sf)
                    except (ValueError, TypeError):
                        sf = 2.0
                    log(f"[PostProcess] RESHAPE: batch_set_property scale_factor → scale ops")
                    op["params"] = {"operations": [{"property": "scale", "value": {"x": sf, "y": sf, "z": sf}}]}
                    changed = True
                elif "visible" in params or "visibility" in params:
                    vis = params.get("visible", params.get("visibility", True))
                    if isinstance(vis, str):
                        vis = vis.lower() not in ("false", "0", "no", "off", "hidden")
                    log(f"[PostProcess] RESHAPE: batch_set_property visible → visibility ops")
                    op["params"] = {"operations": [{"property": "visibility", "value": bool(vis)}]}
                    changed = True
                elif "direction" in params:
                    direction = str(params.get("direction", "up")).lower()
                    distance = float(params.get("distance", params.get("amount", 100)))
                    vec = {"x": 0, "y": 0, "z": 0}
                    if direction == "up":
                        vec["z"] = distance
                    elif direction == "down":
                        vec["z"] = -distance
                    elif direction in ("forward", "north"):
                        vec["x"] = distance
                    elif direction in ("back", "backward", "south"):
                        vec["x"] = -distance
                    elif direction in ("right", "east"):
                        vec["y"] = distance
                    elif direction in ("left", "west"):
                        vec["y"] = -distance
                    log(f"[PostProcess] RESHAPE: batch_set_property direction → location relative ops")
                    op["params"] = {"operations": [{"property": "location", "value": vec, "relative": True}]}
                    changed = True

        if changed:
            log(f"[PostProcess] Plan rewritten with {len(operations)} operations")

        # Fix 3: Type normalization on all operations
        for op in operations:
            params = op.get("params", {})
            if not isinstance(params, dict):
                continue

            # Cast count to int
            if "count" in params:
                try:
                    params["count"] = int(params["count"])
                except (ValueError, TypeError):
                    pass

            # Cast numeric string values
            if "value" in params and isinstance(params["value"], str):
                v = params["value"]
                try:
                    params["value"] = int(v) if v.isdigit() or (v.startswith("-") and v[1:].isdigit()) else float(v)
                except (ValueError, TypeError):
                    pass  # keep as string

            # Also normalize inside nested operations[] arrays
            for sub_op in params.get("operations", []):
                if not isinstance(sub_op, dict):
                    continue
                if "count" in sub_op:
                    try:
                        sub_op["count"] = int(sub_op["count"])
                    except (ValueError, TypeError):
                        pass
                for vkey in ("value", "default_value"):
                    if vkey in sub_op and isinstance(sub_op[vkey], str):
                        v = sub_op[vkey]
                        try:
                            sub_op[vkey] = int(v) if v.isdigit() or (v.startswith("-") and v[1:].isdigit()) else float(v)
                        except (ValueError, TypeError):
                            pass

        ops_out = plan.get("operations", []) if isinstance(plan, dict) else []
        log(f"[PostProcess] EXIT — {len(ops_out)} operations: "
            f"{[op.get('command','?') for op in ops_out]}")
        return plan if isinstance(plan, dict) else json.dumps(plan)

    # ── Code-built plans from discovery (no LLM needed) ──────

    def _build_plan_from_discovery(self, override, discovery):
        """Build an execution plan directly from discovery data without LLM.
        Used for hard-override cases where the LLM truncates large plans.
        Returns a plan dict, or None to fall back to LLM.
        """
        operations = override.get("operations", [])
        if not operations:
            return None

        cmd = operations[0].get("command", "")
        params = operations[0].get("params", {})

        if cmd == "batch_apply_material" or cmd == "find_actors":
            # Collect all actor labels from discovery
            actor_labels = []
            for key, data in discovery.items():
                if key.startswith("actors_"):
                    for actor in data.get("actors", []):
                        label = actor.get("label", "")
                        if label:
                            actor_labels.append(label)

            # Get material path from the batch_apply_material operation
            mat_path = ""
            for op in operations:
                if op.get("command") == "batch_apply_material":
                    mat_path = op.get("params", {}).get("material_path", "")
                    break
            if not mat_path:
                mat_path = params.get("material_path", "")

            # Try to resolve material path from discovery
            for key, data in discovery.items():
                if key.startswith("materials_"):
                    for asset in data.get("assets", []):
                        name = asset.get("name", "")
                        path = asset.get("path", "")
                        if mat_path.lower() in name.lower() or name.lower() in mat_path.lower():
                            mat_path = path  # Use full path from discovery
                            break

            # Extract the find_actors filter from the override targets
            targets = override.get("targets", ["*"])
            name_filter = targets[0] if targets and targets[0] != "*" else ""

            if actor_labels:
                # Build 2-step plan with concrete actor labels from discovery
                mat_ops = [{"actor_label": label, "material_path": mat_path} for label in actor_labels]
                plan = {
                    "mode": "MODIFY",
                    "summary": override.get("summary", "Apply material"),
                    "requires_confirmation": True,
                    "operations": [
                        {
                            "step": 1,
                            "command": "find_actors",
                            "description": f"Find {name_filter or 'all'} actors ({len(actor_labels)} found)",
                            "params": {"name_filter": name_filter},
                            "depends_on": None,
                        },
                        {
                            "step": 2,
                            "command": "batch_apply_material",
                            "description": f"Apply {mat_path} to {len(actor_labels)} actors",
                            "params": {"operations": mat_ops},
                            "depends_on": 1,
                        },
                    ],
                }
                log(f"[BuildPlan] 2-step plan: find_actors({name_filter}) → batch_apply_material({len(mat_ops)} actors, material={mat_path})")
                return plan
            else:
                # No actors found during discovery — return 2-step plan anyway.
                # The executor (Generator Panel) will run find_actors at runtime
                # and inject the results into batch_apply_material.
                log(f"[BuildPlan] No actors found in discovery — returning deferred 2-step plan")
                plan = {
                    "mode": "MODIFY",
                    "summary": override.get("summary", "Apply material"),
                    "requires_confirmation": True,
                    "operations": [
                        {
                            "step": 1,
                            "command": "find_actors",
                            "description": f"Find {name_filter or 'all'} actors in level",
                            "params": {"name_filter": name_filter},
                            "depends_on": None,
                        },
                        {
                            "step": 2,
                            "command": "batch_apply_material",
                            "description": f"Apply {mat_path} to found actors",
                            "params": {"material_path": mat_path},
                            "depends_on": 1,
                        },
                    ],
                }
                return plan

        elif cmd == "batch_replace_material":
            # For replace, we need old and new material paths from discovery
            old_mat = params.get("old_material", "")
            new_mat = params.get("new_material", "")

            # Resolve paths from discovery
            for key, data in discovery.items():
                if key.startswith("materials_"):
                    for asset in data.get("assets", []):
                        name = asset.get("name", "")
                        path = asset.get("path", "")
                        if old_mat and old_mat.lower() in name.lower():
                            old_mat = path
                        if new_mat and new_mat.lower() in name.lower():
                            new_mat = path

            plan = {
                "mode": "MODIFY",
                "summary": override.get("summary", "Replace materials"),
                "requires_confirmation": True,
                "operations": [{
                    "step": 1,
                    "command": "batch_replace_material",
                    "params": {"old_material": old_mat, "new_material": new_mat},
                    "depends_on": None,
                }],
            }
            log(f"[BuildPlan] batch_replace_material: old={old_mat}, new={new_mat}")
            return plan

        elif cmd == "batch_delete_actors":
            actor_labels = []
            for key, data in discovery.items():
                if key.startswith("actors_"):
                    for actor in data.get("actors", []):
                        label = actor.get("label", "")
                        if label:
                            actor_labels.append(label)

            if not actor_labels:
                # Fall back to class_filter from targets
                targets = override.get("targets", [])
                plan = {
                    "mode": "MODIFY",
                    "summary": override.get("summary", "Delete actors"),
                    "requires_confirmation": True,
                    "operations": [{
                        "step": 1,
                        "command": "batch_delete_actors",
                        "params": {"class_filter": targets[0] if targets else ""},
                        "depends_on": None,
                    }],
                }
                log(f"[BuildPlan] batch_delete_actors: using class_filter (no actors found)")
                return plan

            plan = {
                "mode": "MODIFY",
                "summary": override.get("summary", "Delete actors"),
                "requires_confirmation": True,
                "operations": [{
                    "step": 1,
                    "command": "batch_delete_actors",
                    "params": {"labels": actor_labels},
                    "depends_on": None,
                }],
            }
            log(f"[BuildPlan] batch_delete_actors: {len(actor_labels)} actors")
            return plan

        return None  # Unknown command, fall back to LLM

    # ── Main classify_intent: orchestrates all stages ──────

    def _hard_override_check(self, prompt):
        """Hard-coded pattern matching for prompts the LLM consistently misclassifies.
        Returns a stage1-like dict if matched, or None to fall through to LLM.
        """
        lower = prompt.lower().strip()
        original = prompt.strip()  # preserve case for rename etc.
        import re

        # ── Complex single-Blueprint requests the LLM often misclassifies as MULTI ──
        # Pattern 1: "create/make/build [a/an] [noun] that/which/with [complex description]"
        # Pattern 2: "I need/want a [noun] [noun]" (no conjunction needed for simple creates)
        # Pattern 3: "set up [noun] for [context]"
        complex_create = re.match(
            r'^(?:create|make|build|generate|set\s+up|i\s+(?:need|want))\s+(?:a|an|me\s+a|me\s+an)?\s*\w+.*?(?:that|which|with|where|when)\s+',
            lower,
        )
        # Also catch "I need a [noun phrase]" without conjunction (e.g. "I need a weapons stats table")
        if not complex_create:
            complex_create = re.match(
                r'^(?:i\s+(?:need|want)|create|make|build|generate|set\s+up)\s+(?:a|an|me\s+a|me\s+an)?\s*(?:\w+\s+){1,4}(?:table|hud|widget|system|manager|spawner|controller|controls|pickup|enemy|door|platform|checkpoint|turret)\b',
                lower,
            )
        if complex_create:
            # Check it's not actually MULTI (contains "and spawn" or "and create" etc.)
            multi_signals = re.search(
                r'\band\s+(?:spawn|place|put|create|make|build|add\s+lighting|set\s+up|delete|remove)',
                lower,
            )
            if not multi_signals:
                # Determine domain
                domain = "blueprint"
                if any(w in lower for w in ["behavior tree", "bt ", "patrol", "chase", "ai that", "npc that"]):
                    domain = "bt"
                elif any(w in lower for w in ["table with", "table containing", "stats table", "data table"]):
                    domain = "dt"

                cmd = {"blueprint": "create_blueprint", "bt": "create_behavior_tree", "dt": "create_data_table"}[domain]
                log(f"[HardOverride] Complex CREATE detected: domain={domain}, prompt={lower[:80]}")
                return {
                    "mode": "CREATE",
                    "summary": f"Create {domain} from description",
                    "targets": [],
                    "requires_confirmation": False,
                    "operations": [{
                        "step": 1,
                        "command": cmd,
                        "params": {"prompt": lower},
                        "depends_on": None,
                    }],
                }

        # ── Distinguish: targeted material apply vs global material swap ──
        #
        # "replace/change/swap the material/texture ON [targets] with/to [mat]"
        #   → find_actors + batch_apply_material (actors named, ONE material)
        #
        # "replace [old_mat] with [new_mat]" / "swap stone for brick"
        #   → batch_replace_material (TWO materials named, no actor targets)
        #
        # Key signal: "on/of [target]" between the verb and "with/to" means targeted apply.

        # Check for targeted apply FIRST: "replace/change/swap the material/texture on/of [targets]"
        targeted_apply = re.match(
            r"(?:replace|change|swap|switch|update)\s+(?:the\s+)?(?:material|texture)s?\s+(?:on|of)\s+",
            lower,
        )
        if targeted_apply:
            # This is a targeted apply — extract targets and material
            targets = []
            for word in ["wall", "floor", "ceiling", "enemy", "torch",
                         "door", "actor", "mesh", "object", "block",
                         "pillar", "column", "platform", "cube", "sphere"]:
                if word in lower:
                    targets.append(word)
            if not targets:
                targets = ["*"]

            mat_name = ""
            quoted = re.search(r'[\'"]([^\'"]+)[\'"]', original)
            if quoted:
                mat_name = quoted.group(1).strip()
            if not mat_name:
                asset_name = re.search(r'\b((?:M_|MAT_|MI_)\w+)\b', original, re.IGNORECASE)
                if asset_name:
                    mat_name = asset_name.group(1).strip()
            if not mat_name:
                unquoted = re.search(
                    r'\b(?:to|with|using)\s+(?:be\s+|use\s+)?(.+?)\s*$',
                    lower,
                )
                if unquoted:
                    raw = unquoted.group(1).strip()
                    NOISE = {"everywhere", "globally", "in", "the", "level", "scene",
                             "world", "all", "across", "throughout", "on"}
                    cleaned = " ".join(w for w in raw.split() if w not in NOISE)
                    mat_name = cleaned.split(" and ")[0].strip()

            if not mat_name:
                log(f"[HardOverride] Targeted material apply but no material name, falling through")
                pass  # fall through
            else:
                log(f"[HardOverride] Targeted material apply: targets={targets}, material={mat_name}")
                return {
                    "mode": "MODIFY",
                    "summary": f"Apply {mat_name} to {', '.join(targets)}",
                    "targets": targets,
                    "requires_confirmation": True,
                    "operations": [
                        {
                            "step": 1,
                            "command": "find_actors",
                            "params": {"name_filter": targets[0] if targets[0] != "*" else ""},
                            "depends_on": None,
                        },
                        {
                            "step": 2,
                            "command": "batch_apply_material",
                            "params": {"material_path": mat_name},
                            "depends_on": 1,
                        },
                    ],
                }

        # Global material swap: "replace [old_mat] with [new_mat]"
        # Only matches when TWO materials are named — no actor targets
        replace_mat = re.match(
            r"(?:replace|swap)\s+(?:all\s+)?(\S+(?:\s+\S+)?)\s+(?:material\s+|texture\s+)?(?:with|for)\s+(.+?)\s*$",
            lower,
        )
        if replace_mat:
            old_clean = replace_mat.group(1).strip()
            new_clean = replace_mat.group(2).strip()
            # Strip trailing noise words
            NOISE = {"everywhere", "globally", "in", "the", "level", "scene",
                     "world", "all", "across", "throughout"}
            old_clean = " ".join(w for w in old_clean.split() if w not in NOISE)
            new_clean = " ".join(w for w in new_clean.split() if w not in NOISE)
            # Reject if old_clean is "the material" or similar — not a real material name
            if not old_clean or old_clean in ("material", "texture", "materials", "textures"):
                pass  # fall through to material change patterns below
            else:
                log(f"[HardOverride] Material swap detected: old={old_clean}, new={new_clean}")
                return {
                    "mode": "MODIFY",
                    "summary": f"Replace {old_clean} with {new_clean}",
                    "targets": [old_clean, new_clean],
                    "requires_confirmation": True,
                    "operations": [{
                        "step": 1,
                        "command": "batch_replace_material",
                        "params": {"old_material": old_clean, "new_material": new_clean},
                        "depends_on": None,
                    }],
                }

        # ── Material change: change/set/apply + material/texture → batch_apply_material
        # e.g. "Change all wall textures to M_Pack_Bonus_Stone_2"
        # e.g. "change the texture of all the walls to be "M_Pack_Bonus_Stone_2""
        # e.g. "Set the material on all enemies to red"
        # e.g. "change walls to stone"
        mat_change = re.match(
            r"(change|set|apply|update|switch|swap|replace|use|make)\b.*"
            r"(material|texture|mat_|m_)\b.*"
            r"\b(to|with|using)\b",
            lower,
        )
        # Also catch: "change all X to <material_name>" where material_name looks like M_ or MAT_
        mat_change2 = re.match(
            r"(change|set|apply|update|switch|replace)\b.*\bto\s+(?:be\s+)?['\"]?(m_|mat_)",
            lower,
        )
        # Also catch: "change walls to stone" (no explicit material/texture keyword, but target + "to" + noun)
        mat_change3 = re.match(
            r"(change|set|apply|update|switch|swap|replace)\b.*"
            r"\b(wall|floor|ceiling|enemy|torch|door|block|pillar|column|platform|cube|sphere)s?\b.*"
            r"\b(to|with|using)\b",
            lower,
        )
        if mat_change or mat_change2 or mat_change3:
            # Extract target keywords
            targets = []
            for word in ["wall", "floor", "ceiling", "enemy", "torch",
                         "door", "actor", "mesh", "object", "block",
                         "pillar", "column", "platform", "cube", "sphere"]:
                if word in lower:
                    targets.append(word)
            if not targets:
                targets = ["*"]  # query all actors

            # Extract material name — robust multi-strategy approach:
            mat_name = ""
            # Strategy 1: quoted material name
            quoted = re.search(r'[\'"]([^\'"]+)[\'"]', original)
            if quoted:
                mat_name = quoted.group(1).strip()
            if not mat_name:
                # Strategy 2: PascalCase/underscore name (M_Stone, MAT_Brick, etc.)
                asset_name = re.search(r'\b((?:M_|MAT_|MI_)\w+)\b', original, re.IGNORECASE)
                if asset_name:
                    mat_name = asset_name.group(1).strip()
            if not mat_name:
                # Strategy 3: last word after "to/with/using" — strip noise words
                unquoted = re.search(
                    r'\b(?:to|with|using)\s+(?:be\s+|use\s+)?(.+?)\s*$',
                    lower,
                )
                if unquoted:
                    raw = unquoted.group(1).strip()
                    # Remove trailing noise: "in the level", "everywhere", etc.
                    NOISE = {"everywhere", "globally", "in", "the", "level", "scene",
                             "world", "all", "across", "throughout", "on"}
                    cleaned = " ".join(w for w in raw.split() if w not in NOISE)
                    # If multiple words remain, take just the material part
                    # "concrete on all walls" → "concrete"
                    # "marble and make the room brighter" → "marble"
                    and_split = cleaned.split(" and ")
                    mat_name = and_split[0].strip()

            # Guard: never return an empty material_path — fall through to LLM instead
            if not mat_name:
                log(f"[HardOverride] Material change detected but could not extract material name, falling through")
                pass  # fall through to LLM
            else:
                log(f"[HardOverride] Material change detected: targets={targets}, material={mat_name}")
                return {
                    "mode": "MODIFY",
                    "summary": f"Apply {mat_name} to {', '.join(targets)}",
                    "targets": targets,
                    "requires_confirmation": True,
                    "operations": [
                        {
                            "step": 1,
                            "command": "find_actors",
                            "params": {"name_filter": targets[0] if targets[0] != "*" else ""},
                            "depends_on": None,
                        },
                        {
                            "step": 2,
                            "command": "batch_apply_material",
                            "params": {"material_path": mat_name},
                            "depends_on": 1,
                        },
                    ],
                }

        # Pattern: delete/remove/clear actors
        delete_match = re.match(
            r"(delete|remove|clear|destroy|get rid of)\b.*"
            r"\b(all|every|the)\b",
            lower,
        )
        if delete_match:
            # Only override if it's clearly about level actors, not creating BPs
            # Avoid matching "create a BP that deletes itself"
            if not any(kw in lower for kw in ["create", "make", "build", "blueprint", "bp"]):
                targets = []
                for word in re.findall(r'\b(\w+)\b', lower):
                    if word not in ("delete", "remove", "clear", "destroy", "get", "rid",
                                    "of", "all", "every", "the", "in", "from", "level",
                                    "scene", "a", "an", "my"):
                        targets.append(word)
                        break  # take first meaningful noun
                if not targets:
                    targets = ["*"]
                log(f"[HardOverride] Delete actors detected: targets={targets}")
                return {
                    "mode": "MODIFY",
                    "summary": f"Delete {', '.join(targets)} actors",
                    "targets": targets,
                    "requires_confirmation": True,
                    "operations": [{
                        "step": 1,
                        "command": "batch_delete_actors",
                        "params": {},
                        "depends_on": None,
                    }],
                }

        # ── MODIFY: variable changes ──
        # "set X to Y on all Z" / "change X to Y on Z" / "make all Z have X of Y"
        var_change = re.search(
            r'(?:set|change|update|make)\s+(?:the\s+)?(\w+)\s+(?:to|=)\s+(\S+)\s+(?:on|for)\s+(?:all\s+)?(?:the\s+)?(\w+)',
            lower,
        )
        if var_change:
            var_name = var_change.group(1)
            var_val = var_change.group(2)
            target = var_change.group(3)
            log(f"[HardOverride] Variable change: {var_name}={var_val} on {target}")
            return {
                "mode": "MODIFY",
                "summary": f"Set {var_name}={var_val} on {target}",
                "targets": [target],
                "requires_confirmation": True,
                "operations": [{
                    "step": 1,
                    "command": "batch_set_variable",
                    "params": {"variable_name": var_name, "default_value": var_val},
                    "depends_on": None,
                }],
            }

        # ── MODIFY: scale/move/hide/rotate all ──
        transform_match = re.search(
            r'(scale|resize|move|hide|show|rotate)\s+(?:all|every)\s+(?:the\s+)?(\w+)',
            lower,
        )
        if transform_match:
            action = transform_match.group(1)
            target = transform_match.group(2)
            prop_map = {
                "scale": "scale", "resize": "scale",
                "move": "location", "hide": "visibility",
                "show": "visibility", "rotate": "rotation",
            }
            prop = prop_map.get(action, "scale")
            # Extract numeric value if present
            num = re.search(r'(?:by|to)\s+(\d+(?:\.\d+)?)', lower)
            if action in ("scale", "resize"):
                sf = float(num.group(1)) if num else 1.5
                value = {"x": sf, "y": sf, "z": sf}
            elif action == "hide":
                value = False
            elif action == "show":
                value = True
            elif action == "move":
                direction = "up"
                dist = float(num.group(1)) if num else 100
                for d in ["up", "down", "left", "right", "forward", "back"]:
                    if d in lower:
                        direction = d
                vec = {"x": 0, "y": 0, "z": 0}
                if direction == "up": vec["z"] = dist
                elif direction == "down": vec["z"] = -dist
                elif direction == "left": vec["y"] = -dist
                elif direction == "right": vec["y"] = dist
                elif direction == "forward": vec["x"] = dist
                elif direction == "back": vec["x"] = -dist
                value = vec
                prop = "location"
            else:
                value = {"x": 0, "y": 0, "z": 0}

            log(f"[HardOverride] Transform: {action} all {target}")
            return {
                "mode": "MODIFY",
                "summary": f"{action.title()} all {target}",
                "targets": [target],
                "requires_confirmation": True,
                "operations": [{
                    "step": 1,
                    "command": "batch_set_property",
                    "params": {"operations": [{"property": prop, "value": value}]},
                    "depends_on": None,
                }],
            }

        # ── MODIFY: add component to all ──
        # "add a X to every Y" / "give all Y a X"
        comp_add = re.search(
            r'(?:add|give|attach)\s+(?:a\s+)?(\w+(?:\s+\w+)?)\s+(?:to|on)\s+(?:all|every)\s+(?:the\s+)?(\w+)',
            lower,
        )
        if not comp_add:
            comp_add = re.search(
                r'(?:give)\s+(?:all|every)\s+(?:the\s+)?(\w+)\s+(?:a\s+)?(\w+(?:\s+\w+)?)',
                lower,
            )
            if comp_add:
                # Swap groups — "give all X a Y" → component=Y, target=X
                comp_add = type('M', (), {'group': lambda s,i: [None, comp_add.group(2), comp_add.group(1)][i]})()
        if comp_add:
            comp_type = comp_add.group(1).strip()
            target = comp_add.group(2).strip()
            log(f"[HardOverride] Add component: {comp_type} to all {target}")
            return {
                "mode": "MODIFY",
                "summary": f"Add {comp_type} to all {target}",
                "targets": [target],
                "requires_confirmation": True,
                "operations": [{
                    "step": 1,
                    "command": "batch_add_component",
                    "params": {"component_type": comp_type},
                    "depends_on": None,
                }],
            }

        # ── MODIFY: rename (use original case) ──
        rename_match = re.search(r'rename\s+(\S+)\s+to\s+(\S+)', original, re.IGNORECASE)
        if rename_match:
            old_name = rename_match.group(1)
            new_name = rename_match.group(2)
            log(f"[HardOverride] Rename: {old_name} → {new_name}")
            return {
                "mode": "MODIFY",
                "summary": f"Rename {old_name} to {new_name}",
                "targets": [],
                "requires_confirmation": True,
                "operations": [{
                    "step": 1,
                    "command": "rename_asset",
                    "params": {"old_name": old_name, "new_name": new_name},
                    "depends_on": None,
                }],
            }

        # ── MODIFY: lighting setup ──
        lighting_match = re.search(
            r'(?:set\s+up|setup|add|change|switch)\s+.*?(?:light|lighting|illumination)',
            lower,
        )
        if lighting_match and not any(kw in lower for kw in ["create", "make", "build"]):
            preset = "outdoor_day"
            if "dark" in lower or "night" in lower: preset = "indoor_dark"
            elif "bright" in lower or "indoor" in lower: preset = "indoor_bright"
            elif "outdoor" in lower and "night" in lower: preset = "outdoor_night"
            log(f"[HardOverride] Lighting setup: preset={preset}")
            return {
                "mode": "MODIFY",
                "summary": f"Setup {preset} lighting",
                "targets": [],
                "requires_confirmation": False,
                "operations": [{
                    "step": 1,
                    "command": "setup_scene_lighting",
                    "params": {"preset": preset},
                    "depends_on": None,
                }],
            }

        # ── QUERY patterns ──
        query_match = re.match(
            r'^(?:how many|list|show me|what|which|count|find|what\'s|whats)\s+',
            lower,
        )
        if query_match:
            # Determine what to query
            if any(w in lower for w in ["blueprint", "bp_", "bp "]):
                cmd = "find_blueprints"
                params = {}
            elif any(w in lower for w in ["asset", "material", "texture", "mesh", "sound"]):
                asset_type = "Blueprint"
                for t in ["Material", "Texture2D", "StaticMesh", "SoundWave"]:
                    if t.lower() in lower:
                        asset_type = t
                        break
                cmd = "find_assets"
                params = {"type": asset_type}
            else:
                cmd = "find_actors"
                # Extract target filter
                target = ""
                for word in re.findall(r'\b(\w+)\b', lower):
                    if word not in ("how", "many", "list", "show", "me", "what", "which",
                                    "count", "find", "are", "is", "in", "the", "level",
                                    "scene", "there", "all", "whats", "what's", "do", "i",
                                    "have", "of", "a", "an"):
                        target = word
                        break
                params = {"name_filter": target} if target else {}
            log(f"[HardOverride] Query: cmd={cmd}")
            return {
                "mode": "QUERY",
                "summary": f"Query {cmd}",
                "targets": [],
                "requires_confirmation": False,
                "operations": [{
                    "step": 1,
                    "command": cmd,
                    "params": params,
                    "depends_on": None,
                }],
            }

        # ── MULTI: create + spawn ──
        # "create X and spawn Y of them" / "make X and place N"
        create_spawn = re.search(
            r'(?:create|make|build)\s+(.+?)\s+and\s+(?:spawn|place|put)\s+(\d+)',
            lower,
        )
        if create_spawn:
            asset_desc = create_spawn.group(1).strip()
            count = int(create_spawn.group(2))
            domain = "blueprint"
            if any(w in lower for w in ["behavior tree", "bt ", "patrol", "ai"]):
                domain = "bt"
            cmd = "create_behavior_tree" if domain == "bt" else "create_blueprint"
            log(f"[HardOverride] Create+spawn: {asset_desc} × {count}")
            ops = [{"step": 1, "command": cmd, "params": {"prompt": asset_desc}, "depends_on": None}]
            for i in range(count):
                ops.append({
                    "step": i + 2,
                    "command": "spawn_actor_at",
                    "params": {"location": {"x": i * 300, "y": 0, "z": 0}},
                    "depends_on": 1,
                })
            return {
                "mode": "MULTI",
                "summary": f"Create {asset_desc} and spawn {count}",
                "targets": [],
                "requires_confirmation": True,
                "operations": ops,
            }

        # ── MULTI: delete + replace ──
        # "delete all X and replace with Y" / "remove X and create Y"
        delete_replace = re.search(
            r'(?:delete|remove)\s+(?:all\s+)?(?:the\s+)?(\w+)\s+and\s+(?:replace|create|make|build)\s+(.+)',
            lower,
        )
        if delete_replace:
            old_thing = delete_replace.group(1).strip()
            new_thing = delete_replace.group(2).strip()
            # Strip "with" / "them with" prefix
            new_thing = re.sub(r'^(?:them\s+)?(?:with\s+)?', '', new_thing).strip()
            log(f"[HardOverride] Delete+replace: {old_thing} → {new_thing}")
            return {
                "mode": "MULTI",
                "summary": f"Delete {old_thing}, create {new_thing}",
                "targets": [old_thing],
                "requires_confirmation": True,
                "operations": [
                    {"step": 1, "command": "batch_delete_actors", "params": {}, "depends_on": None},
                    {"step": 2, "command": "create_blueprint", "params": {"prompt": new_thing}, "depends_on": None},
                ],
            }

        # ── MULTI: explicit "and" joining two different operations ──
        # "make X tougher and change Y" / "set X and add Y"
        multi_modify = re.search(
            r'(?:make|set|change|update)\s+(.+?)\s+and\s+(?:change|set|make|add|update|also|then)\s+(.+)',
            lower,
        )
        if multi_modify and not complex_create:
            part1 = multi_modify.group(1).strip()
            part2 = multi_modify.group(2).strip()
            log(f"[HardOverride] Multi-modify: '{part1}' + '{part2}'")
            return {
                "mode": "MULTI",
                "summary": f"Multiple modifications",
                "targets": [],
                "requires_confirmation": True,
                "operations": [
                    {"step": 1, "command": "modify_blueprint", "params": {"description": part1}, "depends_on": None},
                    {"step": 2, "command": "modify_blueprint", "params": {"description": part2}, "depends_on": None},
                ],
            }

        # ── MULTI: create multiple named assets ──
        # "create a sword, a shield, and a health potion" / "make X and Y"
        # Only trigger if "create/make" + at least 2 "and"/"," separated nouns
        multi_create = re.match(
            r'^(?:create|make|build)\s+(.+,\s*.+\s+and\s+.+)',
            lower,
        )
        if multi_create:
            items_str = multi_create.group(1)
            # Split on comma and "and"
            items = re.split(r'\s*,\s*|\s+and\s+', items_str)
            items = [re.sub(r'^(?:a|an|the)\s+', '', i.strip()) for i in items if i.strip()]
            if len(items) >= 2:
                log(f"[HardOverride] Multi-create: {items}")
                ops = []
                for i, item in enumerate(items):
                    domain = "blueprint"
                    if any(w in item for w in ["behavior tree", "bt", "patrol ai"]):
                        domain = "bt"
                    elif any(w in item for w in ["table", "data table"]):
                        domain = "dt"
                    cmd = {"blueprint": "create_blueprint", "bt": "create_behavior_tree", "dt": "create_data_table"}[domain]
                    ops.append({"step": i + 1, "command": cmd, "params": {"prompt": item}, "depends_on": None})
                return {
                    "mode": "MULTI",
                    "summary": f"Create {len(items)} assets",
                    "targets": [],
                    "requires_confirmation": True,
                    "operations": ops,
                }

        # ── Fix 1: Implicit/vague MODIFY patterns the LLM punts to CLARIFY ──
        # "Make X faster/slower/stronger/weaker/tougher/bigger/smaller/brighter/dimmer/darker"
        # "X is/are too weak/bright/dark/small" etc.
        implicit_modify = re.search(
            r'(?:make|get)\s+(?:the\s+)?(?:all\s+)?(?:the\s+)?(\w+)\s+.*?'
            r'(faster|slower|stronger|weaker|tougher|bigger|smaller|brighter|dimmer|darker|louder|quieter)',
            lower,
        )
        if not implicit_modify:
            # "the enemies are too weak" / "torches are too bright"
            implicit_modify = re.search(
                r'(?:the\s+)?(\w+)\s+(?:are|is|look|looks)\s+(?:too\s+)?'
                r'(weak|strong|fast|slow|bright|dim|dark|big|small|loud|quiet|plain)',
                lower,
            )
            if implicit_modify:
                # Normalize adjective to standard form
                adj_normalize = {
                    "weak": "weaker", "strong": "stronger", "fast": "faster",
                    "slow": "slower", "bright": "brighter", "dim": "dimmer",
                    "dark": "darker", "big": "bigger", "small": "smaller",
                    "loud": "louder", "quiet": "quieter", "plain": "darker",
                }
                target = implicit_modify.group(1)
                adj = adj_normalize.get(implicit_modify.group(2), implicit_modify.group(2))
                # Re-wrap as a named tuple-like with group()
                class _M:
                    def group(self, i):
                        return [None, target, adj][i]
                implicit_modify = _M()
        if implicit_modify:
            target = implicit_modify.group(1)
            adjective = implicit_modify.group(2)
            adj_map = {
                "faster": ("Speed", "increase", 2.0),
                "slower": ("Speed", "decrease", 0.5),
                "stronger": ("Damage", "increase", 2.0),
                "weaker": ("Damage", "decrease", 0.5),
                "tougher": ("Health", "increase", 2.0),
                "bigger": ("scale", "increase", 1.5),
                "smaller": ("scale", "decrease", 0.5),
                "brighter": ("Intensity", "increase", 2.0),
                "dimmer": ("Intensity", "decrease", 0.5),
                "darker": ("Intensity", "decrease", 0.5),
                "louder": ("Volume", "increase", 2.0),
                "quieter": ("Volume", "decrease", 0.5),
            }
            if adjective in adj_map:
                var_name, direction, factor = adj_map[adjective]
                # Check for explicit numeric value
                num = re.search(r'(?:to|by)\s+(\d+(?:\.\d+)?)', lower)
                if var_name == "scale":
                    sf = float(num.group(1)) if num else factor
                    log(f"[HardOverride] Implicit modify: scale all {target} by {sf}")
                    return {
                        "mode": "MODIFY",
                        "summary": f"Scale all {target} by {sf}",
                        "targets": [target],
                        "requires_confirmation": True,
                        "operations": [
                            {"step": 1, "command": "find_actors", "params": {"name_filter": target}, "depends_on": None},
                            {"step": 2, "command": "batch_set_property",
                             "params": {"operations": [{"property": "scale", "value": {"x": sf, "y": sf, "z": sf}}]},
                             "depends_on": 1},
                        ],
                    }
                else:
                    val = float(num.group(1)) if num else None
                    log(f"[HardOverride] Implicit modify: {direction} {var_name} on all {target}")
                    ops = [
                        {"step": 1, "command": "find_blueprints", "params": {"name_filter": target}, "depends_on": None},
                    ]
                    if val is not None:
                        ops.append({
                            "step": 2, "command": "batch_set_variable",
                            "params": {"variable_name": var_name, "default_value": val},
                            "depends_on": 1,
                        })
                    else:
                        # No explicit value — use modify_blueprint to signal "increase/decrease"
                        ops.append({
                            "step": 2, "command": "batch_set_variable",
                            "params": {"variable_name": var_name, "default_value": f"*{factor}"},
                            "depends_on": 1,
                        })
                    return {
                        "mode": "MODIFY",
                        "summary": f"{direction.title()} {var_name} on all {target}",
                        "targets": [target],
                        "requires_confirmation": True,
                        "operations": ops,
                    }

        # ── Fix 1b: "Reduce/set/lower/raise X Y to Z" ──
        # "reduce torch intensity to 2000" / "set enemy health to 500"
        explicit_set = re.search(
            r'(?:reduce|set|lower|raise|increase|decrease|change)\s+(?:the\s+)?(?:all\s+)?(?:the\s+)?'
            r'(\w+)\s+(\w+)\s+to\s+(\S+)',
            lower,
        )
        if explicit_set:
            target = explicit_set.group(1)
            var_name = explicit_set.group(2)
            value = explicit_set.group(3)
            # Try to parse as number
            try:
                value = float(value)
                if value == int(value):
                    value = int(value)
            except ValueError:
                pass
            log(f"[HardOverride] Explicit set: {target}.{var_name} = {value}")
            return {
                "mode": "MODIFY",
                "summary": f"Set {var_name}={value} on {target}",
                "targets": [target],
                "requires_confirmation": True,
                "operations": [
                    {"step": 1, "command": "find_blueprints", "params": {"name_filter": target}, "depends_on": None},
                    {"step": 2, "command": "batch_set_variable",
                     "params": {"variable_name": var_name, "default_value": value},
                     "depends_on": 1},
                ],
            }

        # ── Fix 1c: "Give all X a Y component" ──
        # "give all enemies a sphere collision component"
        # Different from existing comp_add — catches when "component" is trailing
        give_comp = re.search(
            r'(?:give|add)\s+(?:all\s+)?(?:the\s+)?(?:every\s+)?(\w+)\s+(?:a\s+)?(\w+(?:\s+\w+)?)\s*(?:component)?',
            lower,
        )
        if give_comp:
            target = give_comp.group(1)
            comp_raw = give_comp.group(2).strip()
            # Check if this looks like a component type
            COMP_TYPES = {"box", "sphere", "capsule", "collision", "point", "spot",
                          "light", "mesh", "audio", "arrow", "scene", "static"}
            comp_words = set(comp_raw.lower().split())
            if comp_words & COMP_TYPES:
                log(f"[HardOverride] Give component: {comp_raw} to all {target}")
                return {
                    "mode": "MODIFY",
                    "summary": f"Add {comp_raw} to all {target}",
                    "targets": [target],
                    "requires_confirmation": True,
                    "operations": [
                        {"step": 1, "command": "find_blueprints", "params": {"name_filter": target}, "depends_on": None},
                        {"step": 2, "command": "batch_add_component",
                         "params": {"component_type": comp_raw},
                         "depends_on": 1},
                    ],
                }

        # ── Fix 3: Property changes that need find_actors first ──
        # "scale all X by Y" / "hide all X" / "move all X up by Y"
        # These go through LLM but come back without actor targets.
        prop_change = re.search(
            r'(scale|resize|move|hide|show|rotate)\s+(?:all\s+)?(?:the\s+)?(?:every\s+)?(\w+)\s',
            lower,
        )
        if prop_change:
            action = prop_change.group(1)
            target = prop_change.group(2)
            if target in ("all", "the", "every"):
                # "hide all the X" — need next word
                rest = re.search(r'(?:all|the|every)\s+(?:the\s+)?(\w+)', lower[prop_change.start():])
                if rest:
                    target = rest.group(1)
            prop_map = {
                "scale": "scale", "resize": "scale",
                "move": "location", "hide": "visibility",
                "show": "visibility", "rotate": "rotation",
            }
            prop = prop_map.get(action, "scale")
            num = re.search(r'(?:by|to)\s+(\d+(?:\.\d+)?)', lower)
            if action in ("scale", "resize"):
                sf = float(num.group(1)) if num else 1.5
                value = {"x": sf, "y": sf, "z": sf}
            elif action == "hide":
                value = False
            elif action == "show":
                value = True
            elif action == "move":
                direction = "up"
                dist = float(num.group(1)) if num else 100
                for d in ["up", "down", "left", "right", "forward", "back"]:
                    if d in lower:
                        direction = d
                vec = {"x": 0, "y": 0, "z": 0}
                if direction == "up": vec["z"] = dist
                elif direction == "down": vec["z"] = -dist
                elif direction == "left": vec["y"] = -dist
                elif direction == "right": vec["y"] = dist
                elif direction == "forward": vec["x"] = dist
                elif direction == "back": vec["x"] = -dist
                value = vec
                prop = "location"
            else:
                value = {"x": 0, "y": 0, "z": 0}

            log(f"[HardOverride] Property change: {action} all {target}")
            return {
                "mode": "MODIFY",
                "summary": f"{action.title()} all {target}",
                "targets": [target],
                "requires_confirmation": True,
                "operations": [
                    {"step": 1, "command": "find_actors", "params": {"name_filter": target}, "depends_on": None},
                    {"step": 2, "command": "batch_set_property",
                     "params": {"operations": [{"property": prop, "value": value}]},
                     "depends_on": 1},
                ],
            }

        # ── Fix 4: MULTI patterns misclassified as CREATE/MODIFY ──
        # "X and Y" where X and Y are clearly different operation types

        # "change/replace/swap X and [make/add/set] Y" — two different modify ops
        modify_and_other = re.search(
            r'(?:change|replace|swap|make)\s+(.+?)\s+and\s+(?:change|make|add|set|increase|also|then)\s+(.+)',
            lower,
        )
        if modify_and_other and not complex_create:
            part1 = modify_and_other.group(1).strip()
            part2 = modify_and_other.group(2).strip()
            # Check if parts look like separate operations (not "make a big and heavy sword")
            if len(part1.split()) >= 2 and len(part2.split()) >= 2:
                log(f"[HardOverride] MULTI modify+other: '{part1}' + '{part2}'")
                ops = []
                # Try to classify each part
                for i, part in enumerate([part1, part2], 1):
                    # Check if it's a material/lighting/property change
                    if any(w in part for w in ["material", "texture", "marble", "stone", "brick", "gold", "lava", "concrete"]):
                        ops.append({"step": i, "command": "batch_replace_material", "params": {"description": part}, "depends_on": None})
                    elif any(w in part for w in ["light", "bright", "dark", "lighting"]):
                        preset = "outdoor_day"
                        if "dark" in part or "night" in part: preset = "indoor_dark"
                        elif "bright" in part: preset = "indoor_bright"
                        ops.append({"step": i, "command": "setup_scene_lighting", "params": {"preset": preset}, "depends_on": None})
                    else:
                        ops.append({"step": i, "command": "modify_blueprint", "params": {"description": part}, "depends_on": None})
                return {
                    "mode": "MULTI",
                    "summary": "Multiple modifications",
                    "targets": [],
                    "requires_confirmation": True,
                    "operations": ops,
                }

        # "set up X: A, B, C" — colon/comma list of setup tasks
        setup_list = re.search(r'set\s+up\s+(?:the\s+)?(.+?)[:]\s*(.+)', lower)
        if setup_list:
            context = setup_list.group(1).strip()
            items_str = setup_list.group(2).strip()
            items = re.split(r'\s*,\s*|\s+and\s+', items_str)
            items = [i.strip() for i in items if i.strip()]
            if len(items) >= 2:
                log(f"[HardOverride] Setup list: {context} → {items}")
                ops = []
                for i, item in enumerate(items, 1):
                    if any(w in item for w in ["light", "lighting"]):
                        ops.append({"step": i, "command": "setup_scene_lighting", "params": {"preset": "outdoor_day"}, "depends_on": None})
                    elif any(w in item for w in ["floor", "ground"]):
                        ops.append({"step": i, "command": "spawn_actor_at", "params": {"class": "StaticMeshActor", "description": "floor"}, "depends_on": None})
                    elif any(w in item for w in ["wall", "walls"]):
                        ops.append({"step": i, "command": "spawn_actor_at", "params": {"class": "StaticMeshActor", "description": "walls"}, "depends_on": None})
                    else:
                        ops.append({"step": i, "command": "create_blueprint", "params": {"prompt": item}, "depends_on": None})
                return {
                    "mode": "MULTI",
                    "summary": f"Set up {context} with {len(items)} items",
                    "targets": [],
                    "requires_confirmation": True,
                    "operations": ops,
                }

        # ── Fix 4b: "create X, set Y to Z, spawn N" — comma-separated multi-step ──
        # "Create a patrol enemy, set health to 200, spawn 5 of them"
        comma_steps = re.match(
            r'^(?:create|make|build)\s+(.+?),\s*(?:set|change|make)\s+(.+?),\s*(?:spawn|place|put)\s+(\d+)',
            lower,
        )
        if comma_steps:
            asset = comma_steps.group(1).strip()
            modify_part = comma_steps.group(2).strip()
            count = int(comma_steps.group(3))
            log(f"[HardOverride] Create+modify+spawn: {asset}, {modify_part}, ×{count}")
            ops = [
                {"step": 1, "command": "create_blueprint", "params": {"prompt": asset}, "depends_on": None},
            ]
            # Parse the modify part: "health to 200"
            var_match = re.search(r'(\w+)\s+to\s+(\S+)', modify_part)
            if var_match:
                ops.append({
                    "step": 2, "command": "batch_set_variable",
                    "params": {"variable_name": var_match.group(1), "default_value": var_match.group(2)},
                    "depends_on": 1,
                })
            for i in range(count):
                ops.append({
                    "step": len(ops) + 1,
                    "command": "spawn_actor_at",
                    "params": {"location": {"x": i * 300, "y": 0, "z": 0}},
                    "depends_on": 1,
                })
            return {
                "mode": "MULTI",
                "summary": f"Create {asset}, modify, spawn {count}",
                "targets": [],
                "requires_confirmation": True,
                "operations": ops,
            }

        # ── Fix 4c: "X and Y" where both are different action types ──
        # "delete all coins and replace them with gems worth 100"
        # More general than existing delete_replace — handles "replace them with [description]"
        delete_and = re.search(
            r'(?:delete|remove|clear)\s+(?:all\s+)?(?:the\s+)?(\w+)\s+and\s+(?:replace\s+(?:them\s+)?with|create|make|build)\s+(.+)',
            lower,
        )
        if delete_and:
            old_thing = delete_and.group(1).strip()
            new_thing = delete_and.group(2).strip()
            log(f"[HardOverride] Delete+replace: {old_thing} → {new_thing}")
            return {
                "mode": "MULTI",
                "summary": f"Delete {old_thing}, create {new_thing}",
                "targets": [old_thing],
                "requires_confirmation": True,
                "operations": [
                    {"step": 1, "command": "batch_delete_actors", "params": {"class_filter": old_thing}, "depends_on": None},
                    {"step": 2, "command": "create_blueprint", "params": {"prompt": new_thing}, "depends_on": None},
                ],
            }

        # ── Fix 4d: "change enemy parent class to Character" → reparent_blueprint ──
        reparent_match = re.search(
            r'(?:change|set|switch)\s+(?:the\s+)?(\w+)\s+(?:parent\s+)?class\s+to\s+(\w+)',
            lower,
        )
        if reparent_match:
            target = reparent_match.group(1)
            new_parent = reparent_match.group(2)
            log(f"[HardOverride] Reparent: {target} → {new_parent}")
            return {
                "mode": "MODIFY",
                "summary": f"Reparent {target} to {new_parent}",
                "targets": [target],
                "requires_confirmation": True,
                "operations": [
                    {"step": 1, "command": "find_blueprints", "params": {"name_filter": target}, "depends_on": None},
                    {"step": 2, "command": "reparent_blueprint", "params": {"new_parent": new_parent}, "depends_on": 1},
                ],
            }

        # ── Fix 3b: "X should/need be/have Y" — declarative modify ──
        # "Gold coins should be worth 50 each" / "enemies need 500 HP"
        declarative = re.search(
            r'(?:the\s+)?(\w+(?:\s+\w+)?)\s+(?:should|need|needs)\s+(?:be\s+|have\s+|to\s+(?:be\s+|have\s+)?)(?:worth\s+)?(\S+)',
            lower,
        )
        if declarative:
            target = declarative.group(1).strip()
            value = declarative.group(2).strip()
            # Try to find a variable name hint in the prompt
            var_hints = {"worth": "Value", "hp": "Health", "health": "Health",
                         "damage": "Damage", "speed": "Speed", "range": "Range"}
            var_name = "Value"
            for hint, vn in var_hints.items():
                if hint in lower:
                    var_name = vn
                    break
            try:
                value = float(value)
                if value == int(value):
                    value = int(value)
            except ValueError:
                pass
            log(f"[HardOverride] Declarative modify: {target}.{var_name} = {value}")
            return {
                "mode": "MODIFY",
                "summary": f"Set {var_name}={value} on {target}",
                "targets": [target],
                "requires_confirmation": True,
                "operations": [
                    {"step": 1, "command": "find_blueprints", "params": {"name_filter": target.split()[-1]}, "depends_on": None},
                    {"step": 2, "command": "batch_set_variable",
                     "params": {"variable_name": var_name, "default_value": value},
                     "depends_on": 1},
                ],
            }

        # ── Fix 3c: "increase/decrease X Y to Z" ──
        # "Increase enemy detection range to 1200"
        inc_dec = re.search(
            r'(?:increase|decrease|raise|lower|boost|reduce|bump)\s+(?:the\s+)?(?:all\s+)?(?:the\s+)?'
            r'(\w+)\s+(\w+(?:\s+\w+)?)\s+(?:to|by)\s+(\S+)',
            lower,
        )
        if inc_dec:
            target = inc_dec.group(1)
            var_name = inc_dec.group(2).strip()
            # CamelCase the variable name
            var_name = "".join(w.capitalize() for w in var_name.split())
            value = inc_dec.group(3)
            try:
                value = float(value)
                if value == int(value):
                    value = int(value)
            except ValueError:
                pass
            log(f"[HardOverride] Inc/dec: {target}.{var_name} = {value}")
            return {
                "mode": "MODIFY",
                "summary": f"Set {var_name}={value} on {target}",
                "targets": [target],
                "requires_confirmation": True,
                "operations": [
                    {"step": 1, "command": "find_blueprints", "params": {"name_filter": target}, "depends_on": None},
                    {"step": 2, "command": "batch_set_variable",
                     "params": {"variable_name": var_name, "default_value": value},
                     "depends_on": 1},
                ],
            }

        # ── Fix 1d: "Make the X look like Y" → material change ──
        # "Make the torches look like gold" → apply gold material to torches
        look_like = re.search(
            r'make\s+(?:the\s+)?(?:all\s+)?(?:the\s+)?(\w+)\s+look\s+(?:like\s+)?(\w+)',
            lower,
        )
        if look_like:
            target = look_like.group(1)
            material = look_like.group(2)
            log(f"[HardOverride] Look like: apply {material} material to {target}")
            return {
                "mode": "MODIFY",
                "summary": f"Apply {material} material to {target}",
                "targets": [target],
                "requires_confirmation": True,
                "operations": [
                    {"step": 1, "command": "find_actors", "params": {"name_filter": target}, "depends_on": None},
                    {"step": 2, "command": "batch_apply_material",
                     "params": {"material_path": material},
                     "depends_on": 1},
                ],
            }

        # ── Fix 3d: "make all coins worth double" → multiply variable ──
        worth_double = re.search(
            r'make\s+(?:all\s+)?(?:the\s+)?(\w+)\s+(?:worth|cost)\s+(double|triple|half)',
            lower,
        )
        if worth_double:
            target = worth_double.group(1)
            multiplier = {"double": 2, "triple": 3, "half": 0.5}[worth_double.group(2)]
            log(f"[HardOverride] Worth multiplier: {target} × {multiplier}")
            return {
                "mode": "MODIFY",
                "summary": f"Multiply value on {target} by {multiplier}",
                "targets": [target],
                "requires_confirmation": True,
                "operations": [
                    {"step": 1, "command": "find_blueprints", "params": {"name_filter": target}, "depends_on": None},
                    {"step": 2, "command": "batch_set_variable",
                     "params": {"variable_name": "Value", "default_value": f"*{multiplier}"},
                     "depends_on": 1},
                ],
            }

        return None  # No override — fall through to LLM

    def classify_intent(self, prompt):
        """Multi-stage intent classification. Returns JSON string.

        GPU lock held for the entire classification pipeline to prevent
        adapter state corruption from concurrent generate_dsl requests.
        Stage 2 (UE TCP queries) doesn't need GPU but runs inside the lock
        for simplicity — it's fast (<1s) compared to LLM inference (~20-90s).
        """
        GPU_LOCK_TIMEOUT = 180  # 3 min
        acquired = self.gpu_lock.acquire(timeout=GPU_LOCK_TIMEOUT)
        if not acquired:
            log(f"[ClassifyIntent] TIMEOUT: Could not acquire GPU lock after {GPU_LOCK_TIMEOUT}s")
            return json.dumps({
                "mode": "ERROR",
                "summary": "GPU busy — try again",
                "operations": [],
            })
        try:
            return self._classify_intent_locked(prompt)
        finally:
            self.gpu_lock.release()

    def _classify_intent_locked(self, prompt):
        """Internal: runs with gpu_lock already held."""
        # Stage 0: Hard-coded pattern overrides for known LLM failures
        override = self._hard_override_check(prompt)
        if override:
            mode = override["mode"]
            log(f"[HardOverride] Bypassing LLM — mode={mode}")
            # For MODIFY: run Stage 2 discovery, then build plan directly in code
            # (skip Stage 3 LLM refinement — it truncates with large actor lists)
            if mode in ("MODIFY", "MULTI"):
                discovery = self._stage2_discover(override)
                if discovery:
                    plan = self._build_plan_from_discovery(override, discovery)
                    if plan:
                        result = self._postprocess_plan(plan)
                        return json.dumps(result) if isinstance(result, dict) else result
            result = self._postprocess_plan(override)
            return json.dumps(result) if isinstance(result, dict) else result

        # Stage 1: Classify
        stage1 = self._stage1_classify(prompt)
        mode = stage1.get("mode", "CREATE")
        summary = stage1.get("summary", prompt)
        targets = stage1.get("targets", [])

        # Check if discovery is needed (Fix 4: extended beyond MODIFY/MULTI)
        if should_run_discovery(mode, summary, targets):
            log(f"Multi-stage flow for {mode} (discovery needed)")

            # Stage 2: Discover (TCP queries — fast, kept inside lock for safety)
            discovery = self._stage2_discover(stage1)

            if discovery and mode in ("MODIFY", "MULTI"):
                # Stage 3: Refine with LLM (only for MODIFY/MULTI)
                pass  # Fall through to Stage 3 below
            elif discovery and mode == "CREATE":
                # CREATE with discovery: just enrich Stage 1 result, don't refine
                # This helps resolve asset names for spawn operations
                log(f"CREATE with discovery: enriching Stage 1 result")
                result = self._postprocess_plan(stage1)
                return json.dumps(result) if isinstance(result, dict) else result
            else:
                log("Stage 2 returned no results, returning Stage 1 plan")
                result = self._postprocess_plan(stage1)
                return json.dumps(result) if isinstance(result, dict) else result
        elif mode in ("QUERY", "CLARIFY", "HELP"):
            log(f"Single-stage result ({mode})")
            result = self._postprocess_plan(stage1)
            return json.dumps(result) if isinstance(result, dict) else result
        else:
            # CREATE without discovery hints — return directly
            log(f"Single-stage result ({mode})")
            result = self._postprocess_plan(stage1)
            return json.dumps(result) if isinstance(result, dict) else result

        # Stage 3: Refine (needs GPU)
        refined = self._stage3_refine(prompt, stage1, discovery)
        result = self._postprocess_plan(refined)
        return json.dumps(result) if isinstance(result, dict) else result

    def handle_client(self, conn, addr):
        """Handle a single client connection."""
        log(f"Client connected: {addr}")
        try:
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break

            request_str = data.decode("utf-8").strip()
            if not request_str:
                return

            log(f"Request: {request_str[:200]}")

            try:
                request = json.loads(request_str)
            except json.JSONDecodeError:
                request = {"prompt": request_str}

            # Check if this is a generate_dsl command (Fix 1)
            command = request.get("command", "")
            if command == "generate_dsl":
                domain = request.get("domain", "blueprint")
                prompt = request.get("prompt", "")
                response = self._handle_generate_dsl(domain, prompt)
            else:
                prompt = request.get("prompt", "")
                if not prompt:
                    response = json.dumps({
                        "mode": "CLARIFY",
                        "summary": "Empty prompt received.",
                        "requires_confirmation": False,
                        "operations": [],
                    })
                else:
                    start = time.time()
                    response = self.classify_intent(prompt)
                    elapsed = time.time() - start
                    log(f"Intent classified in {elapsed:.1f}s (multi-stage)")

            conn.sendall((response + "\n").encode("utf-8"))
            log(f"Response sent: {response[:200]}")

        except Exception as e:
            log(f"ERROR handling client: {e}")
            try:
                error_response = json.dumps({
                    "mode": "CLARIFY",
                    "summary": f"Server error: {str(e)}",
                    "requires_confirmation": False,
                    "operations": [],
                })
                conn.sendall((error_response + "\n").encode("utf-8"))
            except Exception:
                pass
        finally:
            conn.close()

    def start(self):
        """Load model and start the TCP server."""
        self.load_model()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", self.port))
        server.listen(5)
        server.settimeout(1.0)  # Allow periodic check for shutdown

        self.running = True
        log(f"Intent server listening on localhost:{self.port}")
        log("Ready for multi-stage intent classification requests")
        log(f"  Stage 1: Classify (LLM) → Stage 2: Discover (UE:{UE_PORT}) → Stage 3: Refine (LLM)")

        try:
            while self.running:
                try:
                    conn, addr = server.accept()
                    # Handle each client in a thread (inference is sequential due to GPU)
                    t = threading.Thread(target=self.handle_client, args=(conn, addr))
                    t.daemon = True
                    t.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            log("Shutting down...")
        finally:
            server.close()
            self.running = False
            log("Intent server stopped")


def main():
    # Set encoding for Windows
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    log("=" * 60)
    log("Arcwright Intent Classification Server (Multi-Stage)")
    log(f"Intent port: {INTENT_PORT}")
    log(f"UE query port: {UE_PORT}")
    log(f"Model: {BASE_MODEL} (base, no LoRA)")
    log("=" * 60)

    server = IntentServer()
    server.start()


if __name__ == "__main__":
    main()
