"""
intent_server.py
-----------------
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
# Stage 1: Classification prompt
# ============================================================

CLASSIFY_PROMPT = r"""Classify this UE5 editor request. Output ONLY valid JSON.
Commands: find_actors, find_blueprints, find_assets, get_level_info, batch_set_variable, batch_add_component, batch_apply_material, batch_set_property, batch_delete_actors, batch_replace_material, rename_asset, reparent_blueprint, create_blueprint, create_behavior_tree, create_data_table, setup_scene_lighting, spawn_actor_at, create_widget_blueprint, modify_blueprint
For MODIFY/MULTI modes, include a "targets" array with search keywords.

IMPORTANT — find_actors vs find_assets:
- find_actors = search for PLACED ACTORS in the current level (things visible in the viewport). Use when the user says "in the level", "in the scene", "on the map", "that I placed", or refers to objects they can see.
- find_assets = search the Content Browser for asset FILES (Blueprints, materials, textures on disk). Use when the user says "in the project", "in my assets", "that I created".
- For material/texture change operations on placed objects → ALWAYS use find_actors first to get the actor names, then batch_apply_material.
- For queries about what exists in the level → find_actors.
- For queries about what assets exist in the project → find_assets.

IMPORTANT — CREATE vs MULTI:
- CREATE = one single Blueprint/asset, even if it has complex internal logic (branches, checks, multiple nodes, AI behaviors). A door that checks for a key = ONE Blueprint with branch logic = CREATE.
- MULTI = user explicitly asks for multiple DISTINCT assets OR a mix of create + modify/spawn operations.
- When in doubt, prefer CREATE over MULTI.

IMPORTANT — Material/texture changes:
- Material/texture changes on placed actors ALWAYS need 2 steps: step 1 = find_actors (to get actor names), step 2 = batch_apply_material (with those actors). NEVER batch_set_property.
- batch_set_property is ONLY for transform, visibility, and tags.
- "Replace all X material with Y" uses batch_replace_material (no find step needed).

User: Set health to 200 on all enemies
{"mode":"MODIFY","summary":"Set Health=200 on enemies","targets":["enemy"],"requires_confirmation":true,"operations":[{"step":1,"command":"batch_set_variable","params":{"variable_name":"Health","default_value":"200"},"depends_on":null}]}
User: How many enemies are in the level?
{"mode":"QUERY","summary":"Count enemies","targets":[],"requires_confirmation":false,"operations":[{"step":1,"command":"find_actors","params":{"name_filter":"enemy"},"depends_on":null}]}
User: Create a health pickup that heals 25 HP
{"mode":"CREATE","summary":"Create health pickup BP","targets":[],"requires_confirmation":false,"operations":[{"step":1,"command":"create_blueprint","params":{"prompt":"health pickup that heals 25 HP"},"depends_on":null}]}
User: Create a health pickup that heals 25 HP when touched and destroys itself
{"mode":"CREATE","summary":"Create health pickup BP","targets":[],"requires_confirmation":false,"operations":[{"step":1,"command":"create_blueprint","params":{"prompt":"health pickup that heals 25 HP when touched and destroys itself"},"depends_on":null}]}
User: Make a door that checks if the player has a key before opening
{"mode":"CREATE","summary":"Create door BP with key check","targets":[],"requires_confirmation":false,"operations":[{"step":1,"command":"create_blueprint","params":{"prompt":"a door that checks if the player has a key before opening"},"depends_on":null}]}
User: I need a score manager that tracks points and prints New High Score when the record is beaten
{"mode":"CREATE","summary":"Create score manager BP","targets":[],"requires_confirmation":false,"operations":[{"step":1,"command":"create_blueprint","params":{"prompt":"score manager that tracks points and prints New High Score when the record is beaten"},"depends_on":null}]}
User: Make a patrol AI that walks between two points and chases the player when spotted
{"mode":"CREATE","summary":"Create patrol AI behavior tree","targets":[],"requires_confirmation":false,"operations":[{"step":1,"command":"create_behavior_tree","params":{"prompt":"patrol AI that walks between two points and chases the player when spotted"},"depends_on":null}]}
User: Change all walls to brick material
{"mode":"MODIFY","summary":"Apply brick material to walls","targets":["wall"],"requires_confirmation":true,"operations":[{"step":1,"command":"find_actors","params":{"name_filter":"wall"},"depends_on":null},{"step":2,"command":"batch_apply_material","params":{"material_path":"brick"},"depends_on":1}]}
User: Change the material on all the walls to "M_Pack_Bonus_Stone_2"
{"mode":"MODIFY","summary":"Apply M_Pack_Bonus_Stone_2 to walls","targets":["wall"],"requires_confirmation":true,"operations":[{"step":1,"command":"find_actors","params":{"name_filter":"wall"},"depends_on":null},{"step":2,"command":"batch_apply_material","params":{"material_path":"M_Pack_Bonus_Stone_2"},"depends_on":1}]}
User: Find all the walls in the level and replace the texture on them with M_Pack_Bonus_Stone_2
{"mode":"MODIFY","summary":"Apply M_Pack_Bonus_Stone_2 to walls","targets":["wall"],"requires_confirmation":true,"operations":[{"step":1,"command":"find_actors","params":{"name_filter":"wall"},"depends_on":null},{"step":2,"command":"batch_apply_material","params":{"material_path":"M_Pack_Bonus_Stone_2"},"depends_on":1}]}
User: Replace all stone materials with marble
{"mode":"MODIFY","summary":"Replace stone with marble","targets":["stone","marble"],"requires_confirmation":true,"operations":[{"step":1,"command":"batch_replace_material","params":{"old_material":"stone","new_material":"marble"},"depends_on":null}]}
User: Delete all the gold coins
{"mode":"MODIFY","summary":"Delete coin actors","targets":["coin"],"requires_confirmation":true,"operations":[{"step":1,"command":"batch_delete_actors","params":{},"depends_on":null}]}
User: Clear out all the torches
{"mode":"MODIFY","summary":"Delete torch actors","targets":["torch"],"requires_confirmation":true,"operations":[{"step":1,"command":"batch_delete_actors","params":{},"depends_on":null}]}
User: Add a point light to every torch
{"mode":"MODIFY","summary":"Add PointLight to torch BPs","targets":["torch"],"requires_confirmation":true,"operations":[{"step":1,"command":"batch_add_component","params":{"component_type":"PointLight"},"depends_on":null}]}
User: Spawn 3 enemies in the level
{"mode":"MULTI","summary":"Spawn 3 enemies","targets":["enemy"],"requires_confirmation":false,"operations":[{"step":1,"command":"spawn_actor_at","params":{"class":"BP_Enemy","location":{"x":-200,"y":0,"z":0}},"depends_on":null},{"step":2,"command":"spawn_actor_at","params":{"class":"BP_Enemy","location":{"x":0,"y":200,"z":0}},"depends_on":null},{"step":3,"command":"spawn_actor_at","params":{"class":"BP_Enemy","location":{"x":200,"y":0,"z":0}},"depends_on":null}]}
User: Make it better
{"mode":"CLARIFY","summary":"What specifically would you like to improve?","targets":[],"requires_confirmation":false,"operations":[]}
User: Create enemies, spawn them, and set up dark lighting
{"mode":"MULTI","summary":"Create enemies with dark lighting","targets":["enemy"],"requires_confirmation":true,"operations":[{"step":1,"command":"setup_scene_lighting","params":{"preset":"indoor_dark"},"depends_on":null},{"step":2,"command":"create_blueprint","params":{"prompt":"enemy"},"depends_on":null},{"step":3,"command":"spawn_actor_at","params":{"count":3},"depends_on":2}]}
User: Make a door AND a key pickup
{"mode":"MULTI","summary":"Create door and key BPs","targets":[],"requires_confirmation":true,"operations":[{"step":1,"command":"create_blueprint","params":{"prompt":"door"},"depends_on":null},{"step":2,"command":"create_blueprint","params":{"prompt":"key pickup"},"depends_on":null}]}
User: """

# ============================================================
# Stage 3: Refinement prompt template
# ============================================================

REFINE_PROMPT_TEMPLATE = r"""Given UE5 editor discovery results, create an exact execution plan using ONLY the real asset names found.
Output ONLY valid JSON with the final plan. Use ONLY commands from the list below — do NOT invent new commands.

Available commands: find_actors, find_blueprints, find_assets, batch_set_variable, batch_add_component, batch_apply_material, batch_set_property, batch_delete_actors, batch_replace_material, rename_asset, modify_blueprint, spawn_actor_at, setup_scene_lighting
IMPORTANT: To delete/remove/clear actors from the level, use batch_delete_actors with "labels" array. There is NO batch_delete_blueprints command.

Example:
User request: "Set health to 200 on all enemies"
Classification: mode=MODIFY
Discovery: Blueprints=[{{"name":"BP_Enemy","variables":["Health","Speed"]}},{{"name":"BP_EnemyBoss","variables":["Health","Armor"]}}]
{{"mode":"MODIFY","summary":"Set Health=200 on BP_Enemy and BP_EnemyBoss","requires_confirmation":true,"operations":[{{"step":1,"command":"batch_set_variable","params":{{"operations":[{{"blueprint":"BP_Enemy","variable_name":"Health","default_value":"200"}},{{"blueprint":"BP_EnemyBoss","variable_name":"Health","default_value":"200"}}]}},"depends_on":null}}]}}

Example:
User request: "Change all walls to M_Brick"
Classification: mode=MODIFY
Discovery: Actors=[{{"label":"Wall_01","class":"StaticMeshActor"}},{{"label":"Wall_02","class":"StaticMeshActor"}}], Assets=[{{"name":"M_Brick","path":"/Game/Materials/M_Brick"}}]
{{"mode":"MODIFY","summary":"Apply M_Brick to Wall_01, Wall_02","requires_confirmation":true,"operations":[{{"step":1,"command":"batch_apply_material","params":{{"operations":[{{"actor_label":"Wall_01","material_path":"/Game/Materials/M_Brick"}},{{"actor_label":"Wall_02","material_path":"/Game/Materials/M_Brick"}}]}},"depends_on":null}}]}}

Example:
User request: "Change the material on all the walls to M_Pack_Bonus_Stone_2"
Classification: mode=MODIFY
Discovery: Actors=[{{"label":"Wall_01","class":"StaticMeshActor"}},{{"label":"Wall_02","class":"StaticMeshActor"}},{{"label":"Wall_03","class":"StaticMeshActor"}}]
{{"mode":"MODIFY","summary":"Apply M_Pack_Bonus_Stone_2 to walls","requires_confirmation":true,"operations":[{{"step":1,"command":"batch_apply_material","params":{{"operations":[{{"actor_label":"Wall_01","material_path":"M_Pack_Bonus_Stone_2"}},{{"actor_label":"Wall_02","material_path":"M_Pack_Bonus_Stone_2"}},{{"actor_label":"Wall_03","material_path":"M_Pack_Bonus_Stone_2"}}]}},"depends_on":null}}]}}

Example:
User request: "Replace all stone materials with marble"
Classification: mode=MODIFY
Discovery: Assets=[{{"name":"M_StoneWall","path":"/Game/Materials/M_StoneWall"}},{{"name":"M_StoneFloor","path":"/Game/Materials/M_StoneFloor"}},{{"name":"M_Marble","path":"/Game/Materials/M_Marble"}}]
{{"mode":"MODIFY","summary":"Replace stone materials with marble","requires_confirmation":true,"operations":[{{"step":1,"command":"batch_replace_material","params":{{"old_material":"/Game/Materials/M_StoneWall","new_material":"/Game/Materials/M_Marble"}},"depends_on":null}},{{"step":2,"command":"batch_replace_material","params":{{"old_material":"/Game/Materials/M_StoneFloor","new_material":"/Game/Materials/M_Marble"}},"depends_on":null}}]}}

Example:
User request: "Add a point light to every torch"
Classification: mode=MODIFY
Discovery: Blueprints=[{{"name":"BP_Torch","variables":["LightIntensity"],"components":["StaticMesh"]}}]
{{"mode":"MODIFY","summary":"Add PointLight to BP_Torch","requires_confirmation":true,"operations":[{{"step":1,"command":"batch_add_component","params":{{"operations":[{{"blueprint":"BP_Torch","component_type":"PointLight","component_name":"TorchLight","properties":{{"intensity":1000}}}}]}},"depends_on":null}}]}}

Example:
User request: "Clear out all the torches"
Classification: mode=MODIFY
Discovery: Actors=[{{"label":"BP_Torch_01","class":"BP_Torch"}},{{"label":"BP_Torch_02","class":"BP_Torch"}},{{"label":"BP_Torch_03","class":"BP_Torch"}}]
{{"mode":"MODIFY","summary":"Delete all torch actors","requires_confirmation":true,"operations":[{{"step":1,"command":"batch_delete_actors","params":{{"labels":["BP_Torch_01","BP_Torch_02","BP_Torch_03"]}},"depends_on":null}}]}}

Example:
User request: "Remove all enemies from the level"
Classification: mode=MODIFY
Discovery: Blueprints=[{{"name":"BP_Enemy"}}], Actors=[]
{{"mode":"MODIFY","summary":"Delete all enemy actors","requires_confirmation":true,"operations":[{{"step":1,"command":"batch_delete_actors","params":{{"class_filter":"BP_Enemy"}},"depends_on":null}}]}}

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

    # Extract first complete JSON object
    json_start = response.find("{")
    json_end = response.rfind("}") + 1
    if json_start < 0 or json_end <= json_start:
        return None

    json_str = response[json_start:json_end]
    # Trim to first balanced object
    depth = 0
    for i, ch in enumerate(json_str):
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

    def _llm_generate(self, prompt_text, max_tokens=400):
        """Run LLM inference and return extracted JSON dict, or None on failure."""
        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList

        inputs = self.tokenizer(prompt_text, return_tensors="pt").to(self.model.device)
        input_len = inputs["input_ids"].shape[1]

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

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=0.1,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id,
                stopping_criteria=stop_criteria,
            )

        generated = outputs[0][input_len:]
        response = self.tokenizer.decode(generated, skip_special_tokens=True).strip()
        log(f"Raw model output: {response[:300]}")

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

        try:
            with self.gpu_lock:
                dsl, raw = self._generate_dsl(domain, prompt)
        except Exception as e:
            log(f"[Generate DSL] ERROR: {e}")
            return json.dumps({"status": "error", "message": str(e)})

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

        log(f"[Stage 3] Refined plan: mode={parsed['mode']}, ops={len(parsed['operations'])}")
        return json.dumps(parsed)

    # ── Post-processing: hard override for known LLM mistakes ──────

    def _postprocess_plan(self, plan):
        """Hard-override post-processing for known LLM routing mistakes.
        Fixes plans AFTER LLM generation so even if the prompt is ignored,
        the correct commands are used.
        """
        if isinstance(plan, str):
            try:
                plan = json.loads(plan)
            except json.JSONDecodeError:
                return plan  # can't fix what we can't parse

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

        if changed:
            log(f"[PostProcess] Plan rewritten with {len(operations)} operations")

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
        import re

        # ── MUST CHECK FIRST: "replace X material with Y" → batch_replace_material
        # Must come before material change (which would also match "replace")
        replace_mat = re.match(
            r"replace\b.*\b(material|texture).*\bwith\b", lower
        )
        if replace_mat:
            parts = re.split(r'\bwith\b', lower, maxsplit=1)
            old_part = parts[0] if len(parts) > 1 else ""
            new_part = parts[1] if len(parts) > 1 else ""
            # Clean up: extract just the material-sounding words
            old_clean = re.sub(r'^replace\s+(all\s+)?', '', old_part).strip()
            old_clean = re.sub(r'\s*(material|texture)s?\s*$', '', old_clean).strip()
            new_clean = new_part.strip()
            log(f"[HardOverride] Material replace detected: old={old_clean}, new={new_clean}")
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
            r"(change|set|apply|update|switch|swap|use|make)\b.*"
            r"(material|texture|mat_|m_)\b.*"
            r"\b(to|with|using)\b",
            lower,
        )
        # Also catch: "change all X to <material_name>" where material_name looks like M_ or MAT_
        mat_change2 = re.match(
            r"(change|set|apply|update|switch)\b.*\bto\s+(?:be\s+)?['\"]?(m_|mat_)",
            lower,
        )
        # Also catch: "change walls to stone" (no explicit material/texture keyword, but target + "to" + noun)
        mat_change3 = re.match(
            r"(change|set|apply|update|switch)\b.*"
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

            # Extract material name — robust regex handling:
            # "to M_Stone" / "to be M_Stone" / "to 'M_Stone'" / 'to be "M_Stone"'
            mat_name = ""
            # First try: extract quoted material name
            quoted = re.search(r'[\'"]([^\'"]+)[\'"]', lower)
            if quoted:
                mat_name = quoted.group(1).strip()
            else:
                # Unquoted: take everything after the last "to/with/using [be/use]"
                unquoted = re.search(
                    r'\b(?:to|with|using)\s+(?:be\s+|use\s+)?(\S+(?:\s+\S+)*?)\s*$',
                    lower,
                )
                if unquoted:
                    mat_name = unquoted.group(1).strip()

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

        return None  # No override — fall through to LLM

    def classify_intent(self, prompt):
        """Multi-stage intent classification. Returns JSON string.

        GPU lock held for the entire classification pipeline to prevent
        adapter state corruption from concurrent generate_dsl requests.
        Stage 2 (UE TCP queries) doesn't need GPU but runs inside the lock
        for simplicity — it's fast (<1s) compared to LLM inference (~20-90s).
        """
        with self.gpu_lock:
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

            # CREATE, QUERY, CLARIFY, HELP: return Stage 1 result directly
            if mode in ("CREATE", "QUERY", "CLARIFY", "HELP"):
                log(f"Single-stage result ({mode})")
                result = self._postprocess_plan(stage1)
                return json.dumps(result) if isinstance(result, dict) else result

            # MODIFY, MULTI: run Stage 2 (Discover) + Stage 3 (Refine)
            log(f"Multi-stage flow for {mode}")

            # Stage 2: Discover (TCP queries — fast, kept inside lock for safety)
            discovery = self._stage2_discover(stage1)
            if not discovery:
                log("Stage 2 returned no results, returning Stage 1 plan")
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
