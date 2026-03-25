#!/usr/bin/env python3
"""
BlueprintLLM — Preflight Checks System
Automated validation before every pipeline operation.
Codifies all lessons learned from CLAUDE.md into guardrails.

Usage:
    python preflight_checks.py --training         # Before training runs
    python preflight_checks.py --blueprint FILE   # Before Blueprint creation
    python preflight_checks.py --bt FILE          # Before BT creation
    python preflight_checks.py --spawn CLASS      # Before actor spawning
    python preflight_checks.py --save             # Before saving
    python preflight_checks.py --session          # Full session audit
    python preflight_checks.py --all              # Run everything

Can also be imported:
    from preflight_checks import PreflightChecker
    checker = PreflightChecker()
    result = checker.check_training()
"""

import sys
import os
import re
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


class CheckResult:
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"
    
    def __init__(self, status, message, lesson=None, fix=None):
        self.status = status
        self.message = message
        self.lesson = lesson  # Reference to CLAUDE.md lesson number
        self.fix = fix  # How to fix if failed
    
    def __repr__(self):
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭️"}[self.status]
        ref = f" [Lesson #{self.lesson}]" if self.lesson else ""
        return f"{icon} {self.status}: {self.message}{ref}"


class PreflightChecker:
    """Automated preflight checks for all pipeline operations."""
    
    def __init__(self, project_root=None):
        self.project_root = project_root or r"C:\BlueprintLLM"
        self.results = []
    
    def _add(self, status, message, lesson=None, fix=None):
        r = CheckResult(status, message, lesson, fix)
        self.results.append(r)
        return r
    
    def _pass(self, msg, lesson=None):
        return self._add(CheckResult.PASS, msg, lesson)
    
    def _warn(self, msg, lesson=None, fix=None):
        return self._add(CheckResult.WARN, msg, lesson, fix)
    
    def _fail(self, msg, lesson=None, fix=None):
        return self._add(CheckResult.FAIL, msg, lesson, fix)
    
    # ═══════════════════════════════════════════════════════════════════════
    # TRAINING PREFLIGHT
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_training(self, config_path=None):
        """Run all training preflight checks. Returns (passed, results)."""
        self.results = []
        print("\n" + "=" * 60)
        print("  TRAINING PREFLIGHT CHECKS")
        print("=" * 60)
        
        self._check_zombie_processes()
        self._check_vram_free()
        self._check_golden_config(config_path)
        self._check_lesson_files()
        self._check_ue_running()
        self._check_backup_current()
        self._check_nvidia_smi_responsive()
        self._check_disk_space()
        
        return self._summarize()
    
    def _check_zombie_processes(self):
        """Lesson #13, #20, #21: Kill zombie GPU processes."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid,name", "--format=csv,noheader", "-i", "1"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                self._warn("nvidia-smi query failed — can't check for zombies", lesson=13)
                return
            
            lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
            python_procs = [l for l in lines if "python" in l.lower()]
            
            if python_procs:
                self._fail(
                    f"Found {len(python_procs)} Python process(es) on training GPU — likely zombies",
                    lesson=13,
                    fix="Kill with: taskkill //F //PID <pid> for each process, then verify VRAM freed"
                )
                for p in python_procs:
                    self._warn(f"  Zombie: {p}")
            else:
                self._pass("No zombie Python processes on training GPU", lesson=13)
        except subprocess.TimeoutExpired:
            self._fail(
                "nvidia-smi hung (>10s) — GPU driver may be stuck",
                lesson=20,
                fix="Reboot required if nvidia-smi hangs"
            )
        except FileNotFoundError:
            self._warn("nvidia-smi not found on PATH")
    
    def _check_vram_free(self):
        """Lesson #20: Verify training GPU has enough free VRAM."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits", "-i", "1"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                used = int(parts[0].strip())
                total = int(parts[1].strip())
                
                if used > 5000:
                    self._fail(
                        f"Training GPU has {used} MiB used ({total} MiB total) — need <5000 MiB",
                        lesson=20,
                        fix="Kill zombie processes or wait for current training to finish"
                    )
                else:
                    self._pass(f"Training GPU VRAM: {used}/{total} MiB — sufficient headroom", lesson=20)
        except Exception as e:
            self._warn(f"Could not check VRAM: {e}")
    
    def _check_golden_config(self, config_path=None):
        """Rule 13b: Verify config matches golden values."""
        config_path = config_path or os.path.join(self.project_root, "pipeline_config.json")
        
        golden = {
            "epochs": 3,
            "learning_rate": 0.0002,
            "gradient_accumulation_steps": 4,
            "lora_rank": 32,
            "lora_alpha": 64,
            "max_seq_length": 1024,
        }
        
        if not os.path.exists(config_path):
            self._warn(f"Config file not found: {config_path}")
            return
        
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            mismatches = []
            for key, expected in golden.items():
                actual = config.get(key)
                if actual is not None and actual != expected:
                    mismatches.append(f"{key}: expected {expected}, got {actual}")
            
            if mismatches:
                self._fail(
                    f"Config deviates from golden values: {'; '.join(mismatches)}",
                    lesson="5b",
                    fix=f"Update {config_path} to match CLAUDE.md golden config"
                )
            else:
                self._pass("Config matches golden values (epochs=3, lr=0.0002, GA=4, rank=32)", lesson="13b")
            
            # Check 8-bit quantization
            if config.get("use_4bit", False):
                self._fail("4-bit quantization enabled — does NOT work on Blackwell", lesson=5,
                           fix="Set use_4bit=false, use_8bit=true")
            elif config.get("use_8bit", True):
                self._pass("8-bit quantization confirmed", lesson=5)
                
        except json.JSONDecodeError:
            self._fail(f"Config file is not valid JSON: {config_path}")
    
    def _check_lesson_files(self):
        """Lesson #14: Verify lesson files use correct field names."""
        lessons_dir = os.path.join(self.project_root, "lessons")
        if not os.path.exists(lessons_dir):
            self._warn("Lessons directory not found")
            return
        
        for f in Path(lessons_dir).glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                
                prompts = data.get("prompts", [])
                for p in prompts:
                    if "expected_output" in p and "expected_dsl" not in p:
                        self._fail(
                            f"{f.name}: uses 'expected_output' instead of 'expected_dsl'",
                            lesson=14,
                            fix="Rename field to 'expected_dsl'"
                        )
                        break
                else:
                    # Check passed for this file
                    pass
            except Exception as e:
                self._warn(f"Could not validate {f.name}: {e}")
        
        self._pass("All lesson files use correct field names", lesson=14)
    
    def _check_ue_running(self):
        """Rule 20: UE Editor should be launched before training."""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("localhost", 13377))
            s.close()
            self._pass("UE Editor TCP server reachable on port 13377", lesson=19)
        except (ConnectionRefusedError, socket.timeout, OSError):
            self._warn(
                "UE Editor not reachable on port 13377 — launch BEFORE training",
                lesson=19,
                fix="Launch UE Editor with -skipcompile, wait for TCP 13377, then start training"
            )
    
    def _check_backup_current(self):
        """Rule 22: Verify backups exist on secondary drive."""
        models_dir = os.path.join(self.project_root, "models")
        backup_dir = r"D:\BlueprintLLMBackup\models"
        
        if not os.path.exists(models_dir):
            self._warn("Models directory not found")
            return
        
        if not os.path.exists(backup_dir):
            self._fail(
                "Backup drive D:\\BlueprintLLMBackup\\models\\ does not exist",
                lesson=26,
                fix="Create directory and sync all model adapters to D:"
            )
            return
        
        # Check each adapter has a backup
        primary_adapters = set()
        for d in Path(models_dir).iterdir():
            if d.is_dir():
                adapter_file = d / "final" / "adapter_model.safetensors"
                if adapter_file.exists():
                    primary_adapters.add(d.name)
        
        backup_adapters = set()
        for d in Path(backup_dir).iterdir():
            if d.is_dir():
                adapter_file = d / "final" / "adapter_model.safetensors"
                if adapter_file.exists():
                    backup_adapters.add(d.name)
        
        missing = primary_adapters - backup_adapters
        if missing:
            self._fail(
                f"Adapters NOT backed up to D:: {', '.join(sorted(missing))}",
                lesson=26,
                fix=f"Copy missing adapters: xcopy /E /I models\\<name> D:\\BlueprintLLMBackup\\models\\<name>"
            )
        elif primary_adapters:
            self._pass(f"All {len(primary_adapters)} adapters backed up to D:", lesson=26)
        else:
            self._warn("No trained adapters found to verify")
    
    def _check_nvidia_smi_responsive(self):
        """Lesson #20: Verify nvidia-smi responds (not hung from driver issue)."""
        try:
            result = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                gpu_count = len([l for l in result.stdout.strip().split("\n") if "GPU" in l])
                self._pass(f"nvidia-smi responsive — {gpu_count} GPUs detected")
            else:
                self._fail("nvidia-smi returned error", fix="Check GPU driver status")
        except subprocess.TimeoutExpired:
            self._fail(
                "nvidia-smi hung — GPU driver stuck",
                lesson=20,
                fix="Reboot required"
            )
        except FileNotFoundError:
            self._warn("nvidia-smi not found")
    
    def _check_disk_space(self):
        """Ensure enough disk space for training."""
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.project_root)
            free_gb = free / (1024**3)
            if free_gb < 10:
                self._fail(f"Only {free_gb:.1f} GB free on primary drive — need at least 10 GB for training")
            elif free_gb < 50:
                self._warn(f"{free_gb:.1f} GB free on primary drive — consider cleanup")
            else:
                self._pass(f"{free_gb:.1f} GB free on primary drive")
        except Exception as e:
            self._warn(f"Could not check disk space: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # BLUEPRINT DSL PREFLIGHT
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_blueprint_dsl(self, dsl_text):
        """Validate Blueprint DSL before sending to UE."""
        self.results = []
        print("\n" + "=" * 60)
        print("  BLUEPRINT DSL PREFLIGHT CHECKS")
        print("=" * 60)
        
        # Basic syntax
        if not dsl_text.strip().startswith("BLUEPRINT:"):
            self._fail("DSL doesn't start with BLUEPRINT: declaration")
        else:
            self._pass("BLUEPRINT: declaration present")
        
        if "PARENT:" not in dsl_text:
            self._fail("Missing PARENT: declaration")
        
        if "GRAPH:" not in dsl_text:
            self._fail("Missing GRAPH: declaration")
        
        # Lesson #15: CastToCharacter warning
        if "CastToCharacter" in dsl_text or "Cast To Character" in dsl_text:
            self._warn(
                "DSL contains CastToCharacter — fails with DefaultPawn",
                lesson=15,
                fix="Use direct overlap handling without casting, or set up a Character pawn"
            )
        
        # Check for overlap events without mentioning collision
        has_overlap = "ActorBeginOverlap" in dsl_text or "ActorEndOverlap" in dsl_text
        if has_overlap:
            self._warn(
                "DSL uses overlap events — ensure Blueprint has a collision component with generate_overlap_events=true",
                lesson=17
            )
        
        # Validate with parser if available
        try:
            sys.path.insert(0, os.path.join(self.project_root, "scripts", "dsl_parser"))
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "dsl_parser"))
            from parser import parse
            result = parse(dsl_text)
            
            errors = result.get("errors", [])
            warnings = result.get("warnings", [])
            stats = result.get("stats", {})
            
            if errors:
                for e in errors:
                    self._fail(f"Parser error: {e}")
            else:
                self._pass(f"Parser validation passed — {stats.get('nodes', 0)} nodes, {stats.get('connections', 0)} connections")
            
            if stats.get("unmapped", 0) > 0:
                self._warn(f"{stats['unmapped']} unmapped node types — may not compile in UE")
            
            for w in warnings:
                self._warn(f"Parser warning: {w}")
                
        except ImportError:
            self._warn("DSL parser not available — skipping deep validation")
        
        # Lesson #33: Material warning
        if "BasicShapeMaterial" in dsl_text:
            self._warn(
                "Reference to BasicShapeMaterial — doesn't work with Substrate rendering",
                lesson=33,
                fix="Use create_simple_material instead of create_material_instance"
            )
        
        return self._summarize()
    
    # ═══════════════════════════════════════════════════════════════════════
    # BEHAVIOR TREE DSL PREFLIGHT
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_bt_dsl(self, dsl_text):
        """Validate BT DSL before sending to UE."""
        self.results = []
        print("\n" + "=" * 60)
        print("  BEHAVIOR TREE DSL PREFLIGHT CHECKS")
        print("=" * 60)
        
        if not dsl_text.strip().startswith("BEHAVIORTREE:"):
            self._fail("DSL doesn't start with BEHAVIORTREE: declaration")
        
        if "BLACKBOARD:" not in dsl_text:
            self._fail("Missing BLACKBOARD: declaration")
        
        if "TREE:" not in dsl_text:
            self._fail("Missing TREE: section")
        
        # Lesson #32: MoveTo without NavMesh
        if "MoveTo" in dsl_text:
            self._warn(
                "BT uses MoveTo — requires NavMesh or bUsePathfinding=false workaround",
                lesson=32,
                fix="Ensure NavMeshBoundsVolume exists in level, or use MoveToLocation with bUsePathfinding=false in Blueprint"
            )
        
        # Lesson #25: Trailing delimiters
        self._warn(
            "BT model may hallucinate trailing delimiters (}, ), >) — ensure exam runner strips these",
            lesson=25
        )
        
        # Validate with parser if available
        try:
            sys.path.insert(0, os.path.join(self.project_root, "scripts", "bt_parser"))
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bt_parser"))
            from bt_parser import parse
            result = parse(dsl_text)
            
            errors = result.get("errors", [])
            stats = result.get("stats", {})
            
            if errors:
                for e in errors:
                    self._fail(f"BT Parser error: {e}")
            else:
                self._pass(f"BT Parser validation passed — {stats.get('total_nodes', 0)} nodes, {stats.get('blackboard_keys', 0)} BB keys")
                
        except ImportError:
            self._warn("BT parser not available — skipping deep validation")
        
        return self._summarize()
    
    # ═══════════════════════════════════════════════════════════════════════
    # SPAWN PREFLIGHT
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_spawn(self, class_path, label=""):
        """Validate before spawning an actor."""
        self.results = []
        print("\n" + "=" * 60)
        print("  SPAWN PREFLIGHT CHECKS")
        print("=" * 60)
        
        # Lesson #29: Full /Game/ path required for Blueprint classes
        if class_path.startswith("BP_") and not class_path.startswith("/Game/"):
            self._fail(
                f"Blueprint class '{class_path}' needs full /Game/ path",
                lesson=29,
                fix=f"Use '/Game/Arcwright/Generated/{class_path}' instead"
            )
        elif class_path.startswith("/Game/"):
            self._pass("Class path uses full /Game/ path", lesson=29)
        else:
            self._pass(f"Native class '{class_path}' — no path prefix needed")
        
        # Lesson #17: Re-spawn warning
        self._warn(
            "Remember: if Blueprint components were recently changed, existing actors need re-spawn",
            lesson=17
        )
        
        return self._summarize()
    
    # ═══════════════════════════════════════════════════════════════════════
    # SAVE PREFLIGHT
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_save(self):
        """Validate before saving."""
        self.results = []
        print("\n" + "=" * 60)
        print("  SAVE PREFLIGHT CHECKS")
        print("=" * 60)
        
        # Lesson #22: Untitled map warning
        self._warn(
            "Ensure current level is NOT 'Untitled' — untitled maps block save_all",
            lesson=22,
            fix="Use save_level first to name the map, or set EditorStartupMap in DefaultEngine.ini"
        )
        
        # Lesson #23: World Partition external actors
        self._warn(
            "World Partition stores actors externally — save_level alone may not save actors",
            lesson=23,
            fix="Always call save_all after save_level to flush external actor packages"
        )
        
        return self._summarize()
    
    # ═══════════════════════════════════════════════════════════════════════
    # NODE EDITING PREFLIGHT  
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_node_editing(self, operation="", pin_type=""):
        """Validate before node editing operations."""
        self.results = []
        print("\n" + "=" * 60)
        print("  NODE EDITING PREFLIGHT CHECKS")
        print("=" * 60)
        
        # Lesson #27: Object pins
        if pin_type and pin_type.lower() in ("object", "class", "softobject"):
            self._warn(
                f"Setting {pin_type} pin — must use DefaultObject (LoadObject), not DefaultValue",
                lesson=27,
                fix="HandleSetNodeParam auto-detects pin category — ensure using updated plugin"
            )
        
        # Lesson #28: By-ref struct pins
        if pin_type and pin_type.lower() in ("vector", "rotator", "transform", "fname"):
            self._warn(
                f"By-ref {pin_type} pin cannot accept string defaults",
                lesson=28,
                fix="Wire through helper nodes: MakeVector for FVector, MakeLiteralName for FName"
            )
        
        # Lesson #30: Blueprint recreation invalidates references
        if operation == "recreate":
            self._warn(
                "Recreating a Blueprint invalidates class references on other BPs",
                lesson=30,
                fix="Re-apply set_class_defaults on all BPs that reference this one, then re-spawn affected actors"
            )
        
        return self._summarize()
    
    # ═══════════════════════════════════════════════════════════════════════
    # SESSION AUDIT
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_session(self):
        """Full session health audit."""
        self.results = []
        print("\n" + "=" * 60)
        print("  SESSION AUDIT")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        self._check_nvidia_smi_responsive()
        self._check_zombie_processes()
        self._check_vram_free()
        self._check_backup_current()
        self._check_disk_space()
        
        # Check UE connection
        self._check_ue_running()
        
        # Check Blender connection
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("localhost", 13378))
            s.close()
            self._pass("Blender TCP server reachable on port 13378")
        except (ConnectionRefusedError, socket.timeout, OSError):
            self._warn("Blender not reachable on port 13378 — launch Blender with addon if needed")
        
        return self._summarize()
    
    # ═══════════════════════════════════════════════════════════════════════
    # SCENE LIGHTING PREFLIGHT
    # ═══════════════════════════════════════════════════════════════════════

    def check_scene_lighting(self):
        """Lesson #42: Check that the level has scene lighting (DirectionalLight + SkyLight)."""
        self.results = []
        print("\n" + "=" * 60)
        print("  SCENE LIGHTING PREFLIGHT CHECKS")
        print("=" * 60)

        try:
            # Handle import from both CLI and package contexts
            try:
                from scripts.mcp_client.blueprint_client import ArcwrightClient
            except ImportError:
                sys.path.insert(0, os.path.join(self.project_root, "scripts"))
                from mcp_client.blueprint_client import ArcwrightClient
            c = ArcwrightClient()
            r = c.send_command('get_actors', {})
            c.close()

            actors = r.get('data', {}).get('actors', [])
            classes = [a.get('class', '') for a in actors]

            has_dir = any('DirectionalLight' in c for c in classes)
            has_sky = any('SkyLight' in c for c in classes)
            has_point = any('PointLight' in c for c in classes)

            if has_dir:
                self._pass("DirectionalLight found in level", lesson=42)
            else:
                self._warn(
                    "No DirectionalLight in level — scene will have no directional sun/moon lighting",
                    lesson=42,
                    fix="Call setup_scene_lighting or spawn a DirectionalLight actor"
                )

            if has_sky:
                self._pass("SkyLight found in level", lesson=42)
            else:
                self._warn(
                    "No SkyLight in level — areas without point lights will be pure black",
                    lesson=42,
                    fix="Call setup_scene_lighting or spawn a SkyLight actor"
                )

            if not has_dir and not has_sky:
                if has_point:
                    self._warn(
                        "Level has only PointLights — no ambient scene lighting. Level will appear very dark.",
                        lesson=42,
                        fix="Call setup_scene_lighting with preset 'indoor_dark' for moody indoor lighting"
                    )
                else:
                    self._fail(
                        "No lighting actors found at all — level will be completely dark",
                        lesson=42,
                        fix="Call setup_scene_lighting before spawning any game actors"
                    )

        except Exception as e:
            self._warn(f"Could not check scene lighting (UE not connected?): {e}")

        return self._summarize()

    # ═══════════════════════════════════════════════════════════════════════
    # FLOOR / FPS CONTROLS PREFLIGHT
    # ═══════════════════════════════════════════════════════════════════════

    def check_floor_exists(self):
        """Lesson #43: Check that the level has a floor/ground plane."""
        self.results = []
        print("\n" + "=" * 60)
        print("  FLOOR PREFLIGHT CHECK")
        print("=" * 60)

        try:
            try:
                from scripts.mcp_client.blueprint_client import ArcwrightClient
            except ImportError:
                sys.path.insert(0, os.path.join(self.project_root, "scripts"))
                from mcp_client.blueprint_client import ArcwrightClient
            c = ArcwrightClient()
            r = c.send_command('get_actors', {})
            c.close()

            actors = r.get('data', {}).get('actors', [])
            labels = [a.get('label', '').lower() for a in actors]
            classes = [a.get('class', '').lower() for a in actors]

            # Check for floor/ground actors by label or by StaticMeshActor with large scale
            has_floor = any(
                'floor' in l or 'ground' in l or 'plane' in l
                for l in labels
            )
            has_landscape = any('landscape' in c for c in classes)

            if has_floor or has_landscape:
                self._pass("Floor/ground surface found in level", lesson=43)
            else:
                self._fail(
                    "No floor/ground surface found — player will fall through the void",
                    lesson=43,
                    fix="Spawn StaticMeshActor with /Engine/BasicShapes/Plane.Plane mesh at large scale"
                )

        except Exception as e:
            self._warn(f"Could not check floor (UE not connected?): {e}")

        return self._summarize()

    def check_fps_controls(self):
        """Lesson #44: Check that FPS controls are configured (PlayerController + GameMode)."""
        self.results = []
        print("\n" + "=" * 60)
        print("  FPS CONTROLS PREFLIGHT CHECK")
        print("=" * 60)

        try:
            try:
                from scripts.mcp_client.blueprint_client import ArcwrightClient
            except ImportError:
                sys.path.insert(0, os.path.join(self.project_root, "scripts"))
                from mcp_client.blueprint_client import ArcwrightClient
            c = ArcwrightClient()

            # Check for FPS PlayerController BP
            r = c.get_blueprint_info('BP_FPSPlayerController')
            has_controller = r.get('status') == 'ok'

            # Check for GameMode BP
            r2 = c.get_blueprint_info('BP_TempleGameMode')
            has_gamemode = r2.get('status') == 'ok'
            if not has_gamemode:
                # Try generic name
                r2 = c.get_blueprint_info('BP_GameMode')
                has_gamemode = r2.get('status') == 'ok'

            c.close()

            if has_controller:
                self._pass("FPS PlayerController Blueprint found", lesson=44)
            else:
                self._warn(
                    "No FPS PlayerController Blueprint — mouse may not be captured during play",
                    lesson=44,
                    fix="Create BP_FPSPlayerController (parent: PlayerController) with BeginPlay→SetInputMode_GameOnly"
                )

            if has_gamemode:
                self._pass("GameMode Blueprint found", lesson=44)
            else:
                self._warn(
                    "No custom GameMode Blueprint — level uses default GameMode",
                    lesson=44,
                    fix="Create GameMode BP, set PlayerControllerClass, then set_game_mode on world"
                )

        except Exception as e:
            self._warn(f"Could not check FPS controls (UE not connected?): {e}")

        return self._summarize()

    # ═══════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════════
    
    def _summarize(self):
        """Print summary and return (all_passed, results)."""
        passes = sum(1 for r in self.results if r.status == CheckResult.PASS)
        warns = sum(1 for r in self.results if r.status == CheckResult.WARN)
        fails = sum(1 for r in self.results if r.status == CheckResult.FAIL)
        
        print()
        for r in self.results:
            print(f"  {r}")
            if r.fix and r.status == CheckResult.FAIL:
                print(f"      Fix: {r.fix}")
        
        print(f"\n  Summary: {passes} passed, {warns} warnings, {fails} failures")
        
        if fails > 0:
            print(f"  ❌ PREFLIGHT FAILED — fix {fails} issue(s) before proceeding")
        elif warns > 0:
            print(f"  ⚠️ PREFLIGHT PASSED WITH WARNINGS — review before proceeding")
        else:
            print(f"  ✅ PREFLIGHT PASSED — all checks clear")
        
        return fails == 0, self.results


# ─── Status enum (for MCP server and external callers) ───────────────────────

class Status:
    """Status enum matching CheckResult for external consumers."""
    PASS = CheckResult.PASS
    WARN = CheckResult.WARN
    FAIL = CheckResult.FAIL
    SKIP = CheckResult.SKIP


# ─── PreflightReport (for pipeline orchestrator) ────────────────────────────

class PreflightReport:
    """Wraps results for the pipeline orchestrator's expected API."""

    def __init__(self, passed, results):
        self.passed = passed
        self.results = results
        self.fail_count = sum(1 for r in results if r.status == CheckResult.FAIL)
        self.warn_count = sum(1 for r in results if r.status == CheckResult.WARN)
        self.has_warnings = self.warn_count > 0


# ─── Standalone convenience functions ────────────────────────────────────────
# These match the import signatures expected by the pipeline orchestrator
# and MCP server:
#   from preflight_checks import check_training, check_blueprint, check_bt, ...

def check_training(config_path=None, skip_ue=False):
    """Standalone training preflight. Returns PreflightReport."""
    checker = PreflightChecker()
    if skip_ue:
        # Run all checks except UE connection
        checker.results = []
        checker._check_zombie_processes()
        checker._check_vram_free()
        checker._check_golden_config(config_path)
        checker._check_lesson_files()
        checker._check_backup_current()
        checker._check_nvidia_smi_responsive()
        checker._check_disk_space()
        passed = all(r.status != CheckResult.FAIL for r in checker.results)
    else:
        passed, _ = checker.check_training(config_path)
    return PreflightReport(passed, checker.results)


def check_blueprint(dsl_text):
    """Standalone Blueprint DSL preflight. Returns PreflightReport."""
    checker = PreflightChecker()
    passed, _ = checker.check_blueprint_dsl(dsl_text)
    return PreflightReport(passed, checker.results)


def check_bt(dsl_text):
    """Standalone BT DSL preflight. Returns PreflightReport."""
    checker = PreflightChecker()
    passed, _ = checker.check_bt_dsl(dsl_text)
    return PreflightReport(passed, checker.results)


def check_spawn(class_path, label=""):
    """Standalone spawn preflight. Returns PreflightReport."""
    checker = PreflightChecker()
    passed, _ = checker.check_spawn(class_path, label)
    return PreflightReport(passed, checker.results)


def check_scene_lighting():
    """Standalone scene lighting check. Returns PreflightReport."""
    checker = PreflightChecker()
    passed, _ = checker.check_scene_lighting()
    return PreflightReport(passed, checker.results)


def check_floor_exists():
    """Standalone floor check. Returns PreflightReport."""
    checker = PreflightChecker()
    passed, _ = checker.check_floor_exists()
    return PreflightReport(passed, checker.results)


def check_fps_controls():
    """Standalone FPS controls check. Returns PreflightReport."""
    checker = PreflightChecker()
    passed, _ = checker.check_fps_controls()
    return PreflightReport(passed, checker.results)


def check_ir_file(ir_path):
    """Validate an IR JSON file before import. Returns PreflightReport."""
    checker = PreflightChecker()
    checker.results = []

    if not os.path.exists(ir_path):
        checker._fail(f"IR file not found: {ir_path}")
    else:
        try:
            with open(ir_path) as f:
                ir = json.load(f)

            if "metadata" not in ir:
                checker._fail("IR missing 'metadata' section")
            else:
                name = ir["metadata"].get("name", "")
                if not name:
                    checker._fail("IR metadata missing 'name'")
                else:
                    checker._pass(f"IR metadata valid: {name}")

            nodes = ir.get("nodes", [])
            connections = ir.get("connections", [])
            checker._pass(f"IR has {len(nodes)} nodes, {len(connections)} connections")

            # Check connection field names (Lesson: wrong field names = silent failure)
            if connections:
                sample = connections[0]
                if "source_node" in sample and "src_node" not in sample:
                    checker._fail(
                        "IR uses 'source_node/source_pin' — must be 'src_node/src_pin'",
                        fix="Rename: source_node→src_node, source_pin→src_pin, target_node→dst_node, target_pin→dst_pin"
                    )
                else:
                    checker._pass("IR connection field names correct (src_node/dst_node)")
        except json.JSONDecodeError as e:
            checker._fail(f"IR file is not valid JSON: {e}")

    passed = all(r.status != CheckResult.FAIL for r in checker.results)
    return PreflightReport(passed, checker.results)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="BlueprintLLM Preflight Checks")
    ap.add_argument("--training", action="store_true", help="Training preflight checks")
    ap.add_argument("--blueprint", metavar="FILE", help="Validate Blueprint DSL file")
    ap.add_argument("--bt", metavar="FILE", help="Validate BT DSL file")
    ap.add_argument("--spawn", metavar="CLASS", help="Validate spawn class path")
    ap.add_argument("--save", action="store_true", help="Save preflight checks")
    ap.add_argument("--lighting", action="store_true", help="Scene lighting checks")
    ap.add_argument("--floor", action="store_true", help="Floor/ground surface check")
    ap.add_argument("--fps", action="store_true", help="FPS controls check")
    ap.add_argument("--session", action="store_true", help="Full session audit")
    ap.add_argument("--all", action="store_true", help="Run all checks")
    ap.add_argument("--project", default=r"C:\BlueprintLLM", help="Project root path")
    args = ap.parse_args()
    
    checker = PreflightChecker(args.project)
    
    if args.training or args.all:
        passed, _ = checker.check_training()
        if not passed and not args.all:
            sys.exit(1)
    
    if args.blueprint:
        with open(args.blueprint) as f:
            dsl = f.read()
        passed, _ = checker.check_blueprint_dsl(dsl)
        if not passed:
            sys.exit(1)
    
    if args.bt:
        with open(args.bt) as f:
            dsl = f.read()
        passed, _ = checker.check_bt_dsl(dsl)
        if not passed:
            sys.exit(1)
    
    if args.spawn:
        passed, _ = checker.check_spawn(args.spawn)
        if not passed:
            sys.exit(1)
    
    if args.save or args.all:
        checker.check_save()

    if args.lighting or args.all:
        checker.check_scene_lighting()

    if args.floor or args.all:
        checker.check_floor_exists()

    if args.fps or args.all:
        checker.check_fps_controls()

    if args.session or args.all:
        checker.check_session()
    
    if not any([args.training, args.blueprint, args.bt, args.spawn, args.save, args.lighting, args.floor, args.fps, args.session, args.all]):
        ap.print_help()


if __name__ == "__main__":
    main()
