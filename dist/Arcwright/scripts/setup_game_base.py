#!/usr/bin/env python3
"""
setup_game_base.py — Copy UE5 official template files into project.

Copies the EXACT Config, Content, and C++ Source from Epic's templates so we get
proven WASD/mouse/jump/camera controls without recreating anything.

Usage:
    python scripts/setup_game_base.py --type fps --project "C:\\Junk\\BlueprintLLMTest"
    python scripts/setup_game_base.py --type fps --project "C:\\Junk\\BlueprintLLMTest" --verify

Supported types: fps, thirdperson, topdown, driving
"""
import argparse
import configparser
import io
import os
import shutil
import sys

# ─── Constants ────────────────────────────────────────────────────────────────

UE_ROOT = r"C:\Program Files\Epic Games\UE_5.7"
TEMPLATES_DIR = os.path.join(UE_ROOT, "Templates")
TEMPLATE_RESOURCES = os.path.join(TEMPLATES_DIR, "TemplateResources")

# Map game types to template names and content paths
GAME_TYPES = {
    "fps": {
        "template_dir": "TP_FirstPerson",
        "module_name": "TP_FirstPerson",
        "content_subdir": "FirstPerson",
        "game_mode_path": "/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode.BP_FirstPersonGameMode_C",
        "shared_packs": ["Input"],
        "description": "First Person Shooter — WASD movement, mouse look, jump",
        "source_files_base": [
            # Only base files, no Variant_Horror or Variant_Shooter
            "TP_FirstPerson.Build.cs",
            "TP_FirstPerson.h",
            "TP_FirstPerson.cpp",
            "TP_FirstPersonCharacter.h",
            "TP_FirstPersonCharacter.cpp",
            "TP_FirstPersonPlayerController.h",
            "TP_FirstPersonPlayerController.cpp",
            "TP_FirstPersonGameMode.h",
            "TP_FirstPersonGameMode.cpp",
            "TP_FirstPersonCameraManager.h",
            "TP_FirstPersonCameraManager.cpp",
        ],
        "extra_engine_config": {
            "/Script/Engine.CollisionProfile": [
                '+Profiles=(Name="Projectile",CollisionEnabled=QueryOnly,ObjectTypeName="Projectile",CustomResponses=,HelpMessage="Preset for projectiles",bCanModify=True)',
                '+DefaultChannelResponses=(Channel=ECC_GameTraceChannel1,Name="Projectile",DefaultResponse=ECR_Block,bTraceType=False,bStaticObject=False)',
                '+EditProfiles=(Name="Trigger",CustomResponses=((Channel=Projectile, Response=ECR_Ignore)))',
            ],
            "/Script/AIModule.AISystem": [
                "bForgetStaleActors=True",
            ],
            "/Script/Engine.Engine": [
                "NearClipPlane=5.000000",
            ],
        },
        "uproject_plugins": [
            {"Name": "StateTree", "Enabled": True},
            {"Name": "GameplayStateTree", "Enabled": True},
        ],
        "build_cs_extra_modules": ["AIModule", "StateTreeModule", "GameplayStateTreeModule", "UMG", "Slate"],
        "test_checklist": [
            "Mouse cursor hidden during Play",
            "Mouse rotates camera (yaw 360, pitch -70 to +80)",
            "WASD moves relative to camera direction",
            "Spacebar jumps with gravity",
            "Character collides with walls/floors",
            "Escape key exits Play mode",
        ],
    },
    "thirdperson": {
        "template_dir": "TP_ThirdPerson",
        "module_name": "TP_ThirdPerson",
        "content_subdir": "ThirdPerson",
        "game_mode_path": "/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode_C",
        "shared_packs": ["Characters", "Input"],
        "description": "Third Person — camera behind character, WASD movement, mouse orbits camera, jump",
        "source_files_base": [
            # Core files only, no Variant_Combat/Platforming/SideScrolling
            "TP_ThirdPerson.Build.cs",
            "TP_ThirdPerson.h",
            "TP_ThirdPerson.cpp",
            "TP_ThirdPersonCharacter.h",
            "TP_ThirdPersonCharacter.cpp",
            "TP_ThirdPersonPlayerController.h",
            "TP_ThirdPersonPlayerController.cpp",
            "TP_ThirdPersonGameMode.h",
            "TP_ThirdPersonGameMode.cpp",
        ],
        "extra_engine_config": {
            "/Script/AIModule.AISystem": [
                "bForgetStaleActors=True",
            ],
        },
        "uproject_plugins": [
            {"Name": "StateTree", "Enabled": True},
            {"Name": "GameplayStateTree", "Enabled": True},
        ],
        "build_cs_extra_modules": ["AIModule", "StateTreeModule", "GameplayStateTreeModule", "UMG", "Slate"],
        "test_checklist": [
            "Camera behind character at ~400 units distance",
            "Mouse orbits camera around character",
            "WASD moves character, character faces movement direction",
            "Spacebar jumps with gravity",
            "Character visible on screen (Mannequin mesh)",
            "Camera pulls in on collision with walls",
        ],
        "verify_input_actions": ["IA_Move", "IA_Jump", "IA_Look", "IA_MouseLook"],
        "verify_imcs": ["IMC_Default", "IMC_MouseLook"],
    },
    "topdown": {
        "template_dir": "TP_TopDown",
        "module_name": "TP_TopDown",
        "content_subdir": "TopDown",
        "game_mode_path": "/Game/TopDown/Blueprints/BP_TopDownGameMode.BP_TopDownGameMode_C",
        "shared_packs": ["Characters"],  # Mannequin mesh; Input is template-local
        "description": "Top Down — overhead camera, click-to-move, visible cursor, NavMesh pathfinding",
        "source_files_base": [
            # Core files only, no Variant_Strategy/TwinStick
            "TP_TopDown.Build.cs",
            "TP_TopDown.h",
            "TP_TopDown.cpp",
            "TP_TopDownCharacter.h",
            "TP_TopDownCharacter.cpp",
            "TP_TopDownPlayerController.h",
            "TP_TopDownPlayerController.cpp",
            "TP_TopDownGameMode.h",
            "TP_TopDownGameMode.cpp",
        ],
        "extra_engine_config": {
            "/Script/AIModule.AISystem": [
                "bForgetStaleActors=True",
            ],
            "/Script/NavigationSystem.RecastNavMesh": [
                "RuntimeGeneration=Dynamic",
                "bForceRebuildOnLoad=True",
                "AgentRadius=34.0",
                "AgentHeight=144.0",
                "AgentMaxHeight=160.0",
                "TileSizeUU=1000.0",
            ],
        },
        "uproject_plugins": [
            {"Name": "StateTree", "Enabled": True},
            {"Name": "GameplayStateTree", "Enabled": True},
        ],
        "build_cs_extra_modules": ["AIModule", "NavigationSystem", "Niagara", "StateTreeModule", "GameplayStateTreeModule", "UMG", "Slate"],
        "test_checklist": [
            "Overhead camera looking down at ~60 degree angle",
            "Mouse cursor visible during Play",
            "Click anywhere to move character to that location",
            "Character navigates around obstacles (NavMesh)",
            "Character faces movement direction",
            "Short click = NavMesh path, hold = continuous move toward cursor",
        ],
        "verify_input_actions": [],  # TopDown has its own input inside Content/TopDown/Input/
        "verify_imcs": [],
    },
    "driving": {
        "template_dir": "TP_VehicleAdv",
        "module_name": "TP_VehicleAdv",
        "content_subdir": "VehicleTemplate",
        "game_mode_path": "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvGameMode.BP_VehicleAdvGameMode_C",
        "shared_packs": ["Track"],  # Track meshes
        "description": "Driving / Vehicle — chase camera, throttle/brake/steering, Chaos vehicle physics",
        "source_files_base": [
            # Base + SportsCar (one working vehicle variant)
            "TP_VehicleAdv.Build.cs",
            "TP_VehicleAdv.h",
            "TP_VehicleAdv.cpp",
            "TP_VehicleAdvPawn.h",
            "TP_VehicleAdvPawn.cpp",
            "TP_VehicleAdvWheelFront.h",
            "TP_VehicleAdvWheelFront.cpp",
            "TP_VehicleAdvWheelRear.h",
            "TP_VehicleAdvWheelRear.cpp",
            "TP_VehicleAdvPlayerController.h",
            "TP_VehicleAdvPlayerController.cpp",
            "TP_VehicleAdvGameMode.h",
            "TP_VehicleAdvGameMode.cpp",
            "TP_VehicleAdvUI.h",
            "TP_VehicleAdvUI.cpp",
            # SportsCar variant — header in subdir, cpp in base dir
            "TP_VehicleAdvSportsCar.cpp",
            "SportsCar/TP_VehicleAdvSportsCar.h",
            "SportsCar/TP_VehicleAdvSportsWheelFront.h",
            "SportsCar/TP_VehicleAdvSportsWheelFront.cpp",
            "SportsCar/TP_VehicleAdvSportsWheelRear.h",
            "SportsCar/TP_VehicleAdvSportsWheelRear.cpp",
            # OffroadCar variant
            "OffroadCar/TP_VehicleAdvOffroadCar.h",
            "OffroadCar/TP_VehicleAdvOffroadCar.cpp",
            "OffroadCar/TP_VehicleAdvOffroadWheelFront.h",
            "OffroadCar/TP_VehicleAdvOffroadWheelFront.cpp",
            "OffroadCar/TP_VehicleAdvOffroadWheelRear.h",
            "OffroadCar/TP_VehicleAdvOffroadWheelRear.cpp",
        ],
        "extra_engine_config": {
            "/Script/Engine.PhysicsSettings": [
                "bSubstepping=False",
                "bSubsteppingAsync=True",
            ],
        },
        "uproject_plugins": [
            {"Name": "ChaosVehiclesPlugin", "Enabled": True},
        ],
        "build_cs_extra_modules": ["ChaosVehicles", "PhysicsCore", "UMG", "Slate"],
        "test_checklist": [
            "Camera behind vehicle (chase camera)",
            "W/S for throttle/brake",
            "A/D for steering",
            "Space for handbrake",
            "Vehicle has physics (acceleration, braking, turning)",
            "Tab to toggle front/back camera",
        ],
        "verify_input_actions": [],  # Vehicle has its own input inside Content/VehicleTemplate/Input/
        "verify_imcs": [],
    },
}


def log(msg, verbose=True):
    if verbose:
        print(f"  [GameBase] {msg}")


# ─── Config Merging ──────────────────────────────────────────────────────────

def read_ini_raw(path):
    """Read an .ini file preserving UE's +/- prefix lines."""
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_ini_sections(text):
    """Parse UE .ini into dict of {section_name: [lines]}."""
    sections = {}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped
            if current not in sections:
                sections[current] = []
        elif current and stripped:
            sections[current].append(stripped)
    return sections


def merge_engine_ini(project_ini_path, extra_sections, game_mode_path, verbose=True):
    """Merge template engine settings into project's DefaultEngine.ini.

    Strategy:
    - Preserve ALL existing project settings
    - Add new sections that don't exist
    - Add GlobalDefaultGameMode to GameMapsSettings (keep existing EditorStartupMap)
    - Add collision profiles, AI settings, etc.
    """
    content = read_ini_raw(project_ini_path)
    existing = parse_ini_sections(content)

    lines = content.splitlines()
    additions = []

    # 1. Set GlobalDefaultGameMode in GameMapsSettings
    gms_section = "[/Script/EngineSettings.GameMapsSettings]"
    has_global_gm = any("GlobalDefaultGameMode" in l for l in existing.get(gms_section, []))

    if gms_section in existing:
        # Insert GlobalDefaultGameMode after the section header if not present
        if not has_global_gm:
            new_lines = []
            for line in lines:
                new_lines.append(line)
                if line.strip() == gms_section:
                    new_lines.append(f"GlobalDefaultGameMode={game_mode_path}")
                    log(f"Added GlobalDefaultGameMode to existing {gms_section}", verbose)
            lines = new_lines
        else:
            # Update existing
            new_lines = []
            for line in lines:
                if line.strip().startswith("GlobalDefaultGameMode="):
                    new_lines.append(f"GlobalDefaultGameMode={game_mode_path}")
                    log(f"Updated GlobalDefaultGameMode", verbose)
                else:
                    new_lines.append(line)
            lines = new_lines
    else:
        additions.append("")
        additions.append(gms_section)
        additions.append(f"GlobalDefaultGameMode={game_mode_path}")
        log(f"Added {gms_section} with GlobalDefaultGameMode", verbose)

    # 2. Add extra sections (collision profiles, AI, etc.)
    for section, section_lines in extra_sections.items():
        if section not in existing:
            additions.append("")
            additions.append(section)
            for sl in section_lines:
                additions.append(sl)
            log(f"Added new section {section}", verbose)
        else:
            # Add lines that don't already exist in that section
            existing_lines = set(existing[section])
            new_entries = [sl for sl in section_lines if sl not in existing_lines]
            if new_entries:
                # Find section in lines and append
                new_lines = []
                in_section = False
                added = False
                for line in lines:
                    new_lines.append(line)
                    if line.strip() == section:
                        in_section = True
                    elif in_section and (line.strip().startswith("[") or line.strip() == ""):
                        if not added:
                            for ne in new_entries:
                                new_lines.insert(-1, ne)
                            added = True
                        in_section = False
                if in_section and not added:
                    for ne in new_entries:
                        new_lines.append(ne)
                lines = new_lines
                log(f"Added {len(new_entries)} lines to existing {section}", verbose)

    result = "\n".join(lines)
    if additions:
        result += "\n" + "\n".join(additions) + "\n"

    with open(project_ini_path, "w", encoding="utf-8") as f:
        f.write(result)


def merge_input_ini(project_ini_path, template_ini_path, verbose=True):
    """Merge template DefaultInput.ini into project's DefaultInput.ini.

    Strategy: replace the entire [/Script/Engine.InputSettings] section
    with the template's version since it contains the correct Enhanced Input setup.
    """
    template_content = read_ini_raw(template_ini_path)
    if not template_content.strip():
        log("Template DefaultInput.ini is empty, skipping", verbose)
        return

    project_content = read_ini_raw(project_ini_path)

    # Parse both files
    template_sections = parse_ini_sections(template_content)
    input_section = "[/Script/Engine.InputSettings]"

    if input_section not in template_sections:
        log("No InputSettings in template, skipping", verbose)
        return

    # Replace project's InputSettings with template's
    project_lines = project_content.splitlines()
    new_lines = []
    skip = False
    replaced = False

    for line in project_lines:
        stripped = line.strip()
        if stripped == input_section:
            skip = True
            # Insert template's section instead
            new_lines.append(input_section)
            for tl in template_sections[input_section]:
                new_lines.append(tl)
            new_lines.append("")
            replaced = True
            continue
        if skip:
            if stripped.startswith("[") and stripped.endswith("]"):
                skip = False
                new_lines.append(line)
            # else skip this line (old section content)
            continue
        new_lines.append(line)

    if not replaced:
        # Section didn't exist, append it
        new_lines.append("")
        new_lines.append(input_section)
        for tl in template_sections[input_section]:
            new_lines.append(tl)
        new_lines.append("")

    with open(project_ini_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))

    log(f"Merged InputSettings ({len(template_sections[input_section])} lines)", verbose)


# ─── Module Integration ──────────────────────────────────────────────────────

def add_module_to_uproject(uproject_path, module_name, plugins, verbose=True):
    """Add the template module to .uproject and ensure plugins are enabled."""
    import json

    with open(uproject_path, "r", encoding="utf-8") as f:
        proj = json.load(f)

    # Add module if not present
    module_names = [m["Name"] for m in proj.get("Modules", [])]
    if module_name not in module_names:
        proj.setdefault("Modules", []).append({
            "Name": module_name,
            "Type": "Runtime",
            "LoadingPhase": "Default",
            "AdditionalDependencies": [
                "Engine",
                "AIModule",
                "UMG"
            ]
        })
        log(f"Added module '{module_name}' to .uproject", verbose)

    # Add plugins if not present
    existing_plugins = {p["Name"] for p in proj.get("Plugins", [])}
    for plugin in plugins:
        if plugin["Name"] not in existing_plugins:
            proj.setdefault("Plugins", []).append(plugin)
            log(f"Added plugin '{plugin['Name']}'", verbose)

    with open(uproject_path, "w", encoding="utf-8") as f:
        json.dump(proj, f, indent="\t")

    return proj


def add_module_to_targets(project_dir, module_name, verbose=True):
    """Add ExtraModuleNames.Add("module") to both Target.cs files."""
    for target_file in ["Source/BlueprintLLMTestEditor.Target.cs", "Source/BlueprintLLMTest.Target.cs"]:
        target_path = os.path.join(project_dir, target_file)
        if not os.path.exists(target_path):
            log(f"WARNING: {target_file} not found, skipping", verbose)
            continue

        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()

        add_line = f'ExtraModuleNames.Add("{module_name}");'
        if add_line in content:
            log(f"{target_file}: module already listed", verbose)
            continue

        # Insert after existing ExtraModuleNames line
        lines = content.splitlines()
        new_lines = []
        added = False
        for line in lines:
            new_lines.append(line)
            if "ExtraModuleNames.Add(" in line and not added:
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(f'{indent}ExtraModuleNames.Add("{module_name}");')
                added = True

        with open(target_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        log(f"{target_file}: added {module_name}", verbose)


def copy_source_files(template_dir, project_dir, module_name, base_files, verbose=True):
    """Copy the template's C++ source as a secondary module.

    Critical: change IMPLEMENT_PRIMARY_GAME_MODULE to IMPLEMENT_GAME_MODULE
    since the project already has a primary module.

    Supports subdirectory paths in base_files (e.g. "SportsCar/Foo.h").
    """
    import re

    src = os.path.join(template_dir, "Source", module_name)
    dst = os.path.join(project_dir, "Source", module_name)

    os.makedirs(dst, exist_ok=True)

    copied = 0
    for filename in base_files:
        src_file = os.path.join(src, filename)
        dst_file = os.path.join(dst, filename)

        if not os.path.exists(src_file):
            log(f"WARNING: {filename} not found in template source", verbose)
            continue

        # Create subdirectory if needed
        dst_subdir = os.path.dirname(dst_file)
        if dst_subdir and not os.path.exists(dst_subdir):
            os.makedirs(dst_subdir, exist_ok=True)

        with open(src_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Critical fix: can't have two primary game modules
        # IMPLEMENT_PRIMARY_GAME_MODULE takes 3 args, IMPLEMENT_GAME_MODULE takes 2
        content = re.sub(
            r'IMPLEMENT_PRIMARY_GAME_MODULE\(\s*(\w+)\s*,\s*(\w+)\s*,\s*"[^"]*"\s*\)',
            r'IMPLEMENT_GAME_MODULE( \1, \2 )',
            content
        )

        # Remove variant include paths from Build.cs (we only copy base files)
        if filename.endswith(".Build.cs"):
            lines = content.splitlines()
            new_lines = []
            for line in lines:
                if "Variant_" in line:
                    continue  # Skip variant include paths
                new_lines.append(line)
            content = "\n".join(new_lines)

        # ── FPS-specific: fix camera attachment ──
        if module_name == "TP_FirstPerson" and filename.endswith("Character.cpp"):
            content = content.replace(
                'FirstPersonCameraComponent->SetupAttachment(FirstPersonMesh, FName("head"));',
                'FirstPersonCameraComponent->SetupAttachment(GetCapsuleComponent());'
            )
            content = content.replace(
                'FirstPersonCameraComponent->SetRelativeLocationAndRotation(FVector(-2.8f, 5.89f, 0.0f), FRotator(0.0f, 90.0f, -90.0f));',
                'FirstPersonCameraComponent->SetRelativeLocation(FVector(0.0f, 0.0f, 64.0f));'
            )
            content = content.replace(
                '\tFirstPersonCameraComponent->bEnableFirstPersonFieldOfView = true;\n'
                '\tFirstPersonCameraComponent->bEnableFirstPersonScale = true;\n'
                '\tFirstPersonCameraComponent->FirstPersonFieldOfView = 70.0f;\n'
                '\tFirstPersonCameraComponent->FirstPersonScale = 0.6f;\n',
                ''
            )

        with open(dst_file, "w", encoding="utf-8") as f:
            f.write(content)
        copied += 1

    log(f"Copied {copied} C++ source files to Source/{module_name}/", verbose)
    return copied


# ─── Content Copy ─────────────────────────────────────────────────────────────

def copy_content(template_dir, project_dir, content_subdir, verbose=True):
    """Copy template Content (Blueprints, Anims, materials) to project.

    Copies Content/<subdir>/ excluding the level map file (we keep our own levels).
    """
    src = os.path.join(template_dir, "Content", content_subdir)
    dst = os.path.join(project_dir, "Content", content_subdir)

    if not os.path.exists(src):
        log(f"WARNING: Template content dir not found: {src}", verbose)
        return 0

    # Copy everything except level map files
    copied = 0
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        dst_root = os.path.join(dst, rel) if rel != "." else dst

        os.makedirs(dst_root, exist_ok=True)

        for f in files:
            # Skip level maps — we keep our own
            if f.endswith(".umap"):
                log(f"Skipping level map: {f}", verbose)
                continue

            src_file = os.path.join(root, f)
            dst_file = os.path.join(dst_root, f)
            shutil.copy2(src_file, dst_file)
            copied += 1

    log(f"Copied {copied} content files to Content/{content_subdir}/", verbose)
    return copied


def copy_shared_packs(shared_packs, project_dir, verbose=True):
    """Copy shared TemplateResources content packs (Input actions, etc.)."""
    total = 0
    for pack_name in shared_packs:
        src = os.path.join(TEMPLATE_RESOURCES, "High", pack_name, "Content")
        dst = os.path.join(project_dir, "Content", pack_name)

        if not os.path.exists(src):
            log(f"WARNING: Shared pack not found: {src}", verbose)
            continue

        copied = 0
        for root, dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            dst_root = os.path.join(dst, rel) if rel != "." else dst
            os.makedirs(dst_root, exist_ok=True)

            for f in files:
                src_file = os.path.join(root, f)
                dst_file = os.path.join(dst_root, f)
                shutil.copy2(src_file, dst_file)
                copied += 1

        log(f"Copied shared pack '{pack_name}': {copied} files to Content/{pack_name}/", verbose)
        total += copied

    return total


# ─── Main Setup ───────────────────────────────────────────────────────────────

def setup_game_base(game_type, project_dir, verbose=True):
    """
    Complete game base setup: copies template Source, Content, Input, and merges Config.

    Steps:
      1. Validate template exists
      2. Copy C++ source as secondary module
      3. Add module to .uproject and Target.cs files
      4. Copy Content (Blueprints, Anims, materials)
      5. Copy shared Input assets (IA_Move, IA_Jump, etc.)
      6. Merge Config (DefaultEngine.ini: GameMode, collision, AI)
      7. Merge Config (DefaultInput.ini: Enhanced Input settings)

    Returns dict with results.
    """
    if game_type not in GAME_TYPES:
        raise ValueError(f"Unknown game type: {game_type}. Supported: {', '.join(GAME_TYPES.keys())}")

    config = GAME_TYPES[game_type]
    template_dir = os.path.join(TEMPLATES_DIR, config["template_dir"])

    results = {"steps": [], "success": True, "game_type": game_type}

    def step(msg):
        log(msg, verbose)
        results["steps"].append(msg)

    step(f"Setting up {config['description']}")
    step(f"Template: {template_dir}")
    step(f"Project: {project_dir}")

    # Validate
    if not os.path.isdir(template_dir):
        step(f"ERROR: Template directory not found: {template_dir}")
        results["success"] = False
        return results

    uproject = None
    for f in os.listdir(project_dir):
        if f.endswith(".uproject"):
            uproject = os.path.join(project_dir, f)
            break

    if not uproject:
        step(f"ERROR: No .uproject file found in {project_dir}")
        results["success"] = False
        return results

    step(f"Found project file: {os.path.basename(uproject)}")

    # Step 1: Copy C++ source
    step("Step 1: Copying C++ source module...")
    n = copy_source_files(
        template_dir, project_dir,
        config["module_name"],
        config["source_files_base"],
        verbose
    )
    step(f"  {n} source files copied")

    # Step 2: Add module to .uproject + Target.cs
    step("Step 2: Adding module to project files...")
    add_module_to_uproject(uproject, config["module_name"], config.get("uproject_plugins", []), verbose)
    add_module_to_targets(project_dir, config["module_name"], verbose)

    # Step 3: Copy Content
    step("Step 3: Copying template Content...")
    n = copy_content(template_dir, project_dir, config["content_subdir"], verbose)
    step(f"  {n} content files copied")

    # Step 4: Copy shared Input assets
    step("Step 4: Copying shared Input assets...")
    n = copy_shared_packs(config.get("shared_packs", []), project_dir, verbose)
    step(f"  {n} shared assets copied")

    # Step 5: Merge DefaultEngine.ini
    step("Step 5: Merging DefaultEngine.ini...")
    engine_ini = os.path.join(project_dir, "Config", "DefaultEngine.ini")
    merge_engine_ini(
        engine_ini,
        config.get("extra_engine_config", {}),
        config["game_mode_path"],
        verbose
    )

    # Step 6: Merge DefaultInput.ini
    step("Step 6: Merging DefaultInput.ini...")
    template_input_ini = os.path.join(template_dir, "Config", "DefaultInput.ini")
    project_input_ini = os.path.join(project_dir, "Config", "DefaultInput.ini")
    merge_input_ini(project_input_ini, template_input_ini, verbose)

    step("")
    step("Setup complete! Next steps:")
    step("  1. Build the project: Build.bat BlueprintLLMTestEditor Win64 Development ...")
    step("  2. Launch UE Editor with -skipcompile")
    step("  3. Press Play and test:")
    for item in config.get("test_checklist", []):
        step(f"     - {item}")

    return results


def verify_game_base(game_type, project_dir, verbose=True):
    """Verify that a game base was properly set up."""
    if game_type not in GAME_TYPES:
        print(f"Unknown game type: {game_type}")
        return False

    config = GAME_TYPES[game_type]
    issues = []

    def check(label, ok, detail=""):
        status = "OK" if ok else "FAIL"
        if verbose:
            msg = f"  [{status}] {label}"
            if detail:
                msg += f" - {detail}"
            print(msg)
        if not ok:
            issues.append(label)

    if verbose:
        print(f"\n=== {game_type.upper()} Game Base Verification ===\n")

    # Check C++ source exists
    module_dir = os.path.join(project_dir, "Source", config["module_name"])
    check("C++ source module exists", os.path.isdir(module_dir), module_dir)

    for f in config["source_files_base"]:
        check(f"  {f}", os.path.exists(os.path.join(module_dir, f)))

    # Check IMPLEMENT_GAME_MODULE (not PRIMARY)
    cpp_file = os.path.join(module_dir, f"{config['module_name']}.cpp")
    if os.path.exists(cpp_file):
        with open(cpp_file, "r") as f:
            cpp_content = f.read()
        check("Uses IMPLEMENT_GAME_MODULE (not PRIMARY)",
              "IMPLEMENT_GAME_MODULE" in cpp_content and "PRIMARY" not in cpp_content)

    # Check Content
    content_dir = os.path.join(project_dir, "Content", config["content_subdir"])
    check("Content directory exists", os.path.isdir(content_dir))

    bp_dir = os.path.join(content_dir, "Blueprints")
    check("Blueprints directory exists", os.path.isdir(bp_dir))

    # Check shared Input (only if template uses shared Input pack)
    verify_ias = config.get("verify_input_actions", ["IA_Move", "IA_Jump", "IA_Look", "IA_MouseLook"])
    verify_imcs = config.get("verify_imcs", ["IMC_Default", "IMC_MouseLook"])

    if verify_ias or verify_imcs:
        input_dir = os.path.join(project_dir, "Content", "Input")
        check("Shared Input assets exist", os.path.isdir(input_dir))

        for ia in verify_ias:
            check(f"  {ia}.uasset",
                  os.path.exists(os.path.join(input_dir, "Actions", f"{ia}.uasset")))

        for imc in verify_imcs:
            check(f"  {imc}.uasset",
                  os.path.exists(os.path.join(input_dir, f"{imc}.uasset")))

    # Check .uproject has module
    import json
    for f in os.listdir(project_dir):
        if f.endswith(".uproject"):
            with open(os.path.join(project_dir, f), "r") as fp:
                proj = json.load(fp)
            module_names = [m["Name"] for m in proj.get("Modules", [])]
            check(f".uproject has {config['module_name']} module",
                  config["module_name"] in module_names)
            break

    # Check DefaultEngine.ini has GameMode
    engine_ini = os.path.join(project_dir, "Config", "DefaultEngine.ini")
    if os.path.exists(engine_ini):
        with open(engine_ini, "r") as f:
            ei = f.read()
        check("DefaultEngine.ini has GlobalDefaultGameMode",
              "GlobalDefaultGameMode=" in ei and config["game_mode_path"] in ei)

    # Check DefaultInput.ini has Enhanced Input
    input_ini = os.path.join(project_dir, "Config", "DefaultInput.ini")
    if os.path.exists(input_ini):
        with open(input_ini, "r") as f:
            ii = f.read()
        check("DefaultInput.ini has EnhancedPlayerInput",
              "EnhancedInput.EnhancedPlayerInput" in ii)

    if verbose:
        total = len(issues) + sum(1 for _ in config["source_files_base"]) + 10  # approx
        passed = total - len(issues)
        print(f"\n{len(issues)} issues found.")
        if not issues:
            print("Game base looks good! Build and launch UE to test.")
        else:
            print(f"Issues: {', '.join(issues)}")

    return len(issues) == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up UE5 game base from official templates")
    parser.add_argument("--type", required=True, choices=list(GAME_TYPES.keys()),
                        help="Game type (fps, thirdperson, topdown, driving)")
    parser.add_argument("--project", required=True,
                        help="Path to UE project directory")
    parser.add_argument("--verify", action="store_true",
                        help="Verify existing setup instead of installing")
    args = parser.parse_args()

    if args.verify:
        ok = verify_game_base(args.type, args.project)
        sys.exit(0 if ok else 1)
    else:
        print(f"\n=== Setting up {args.type.upper()} Game Base ===\n")
        result = setup_game_base(args.type, args.project)
        sys.exit(0 if result["success"] else 1)
