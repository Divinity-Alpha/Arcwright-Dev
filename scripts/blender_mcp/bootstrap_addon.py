"""
Bootstrap script for Blender — installs and enables the Arcwright addon.
Run via: blender --python bootstrap_addon.py

This script:
1. Copies the addon file to Blender's addons directory
2. Enables it
3. Saves user preferences so it persists
"""
import bpy
import shutil
import os
import sys

ADDON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blueprintllm_blender_server.py")
PROC_TEX_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender_procedural_textures.py")

# Get Blender's addon directory
addon_dir = bpy.utils.user_resource('SCRIPTS', path="addons")
os.makedirs(addon_dir, exist_ok=True)

# Copy addon file
dst = os.path.join(addon_dir, "blueprintllm_blender_server.py")
shutil.copy2(ADDON_FILE, dst)
print(f"[Arcwright] Copied addon to {dst}")

# Copy procedural textures module alongside it
proc_dst = os.path.join(addon_dir, "blender_procedural_textures.py")
shutil.copy2(PROC_TEX_FILE, proc_dst)
print(f"[Arcwright] Copied procedural textures to {proc_dst}")

# Refresh and enable
bpy.ops.preferences.addon_refresh()
bpy.ops.preferences.addon_enable(module="blueprintllm_blender_server")
bpy.ops.wm.save_userpref()

print("[Arcwright] Addon installed and enabled. TCP server starting on port 13378.")
