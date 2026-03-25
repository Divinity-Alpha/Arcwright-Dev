# Arcwright Cleanup & Redirect Instructions
# Give this entire file to Arcwright Dev Claude Code

Reference CLAUDE.md. Major product redirect. We are simplifying Arcwright to a pure bridge plugin — no hosted LLM, no subscription, no API keys.

## New Product Model
- **Price**: $49.99 one-time purchase via FAB Marketplace
- **No subscription, no API keys, no Zuplo, no RunPod**
- **The customer's AI does ALL the creative work** — Arcwright is purely the bridge to UE
- **All commands available to all purchasers** — no free/pro tier split

## Task 1: Remove Infrastructure Code

### Remove from C++ plugin source:
1. **TierGating.h** — remove ALL tier checking logic. Every command is available to every user. Remove:
   - Free/Pro tier distinction
   - API key validation against Zuplo
   - validation_cache.json reading/writing
   - api_key.txt reading
   - HTTP calls to any external validation endpoint
   - The entire tier gating check in command dispatch
   - Replace with: every command always executes (or a simple local license check if needed)

2. **RunPodClient.h** — DELETE this file entirely
   - Remove from CommandServer.h includes
   - Remove configure_runpod, generate_dsl_cloud, check_generation commands
   - Remove from dispatch routing

3. **ArcwrightDashboardPanel.cpp** — Remove:
   - API key input field and Activate button
   - The Account & Tier section showing free/pro
   - Any references to Zuplo or RunPod
   - Replace with simple "Licensed" or version display

4. **ArcwrightUIBuilderPanel.cpp** — Remove:
   - RunPod generation code from the Generate button
   - The Generate button should only do local DSL generation (clipboard copy or parse from input)
   - Keep the live preview, theme picker, color picker, component checklist — those are valuable

5. **CommandServer.cpp** — Remove:
   - configure_runpod handler
   - generate_dsl_cloud handler
   - check_generation handler
   - Any tier gating checks before command execution
   - Keep ALL other 263 commands

### Remove from Python scripts:
1. **server.py** — Remove:
   - _is_pro_tier() function and all tier checking
   - _validate_key_remote() and all Zuplo calls
   - _find_validation_cache() and cache logic
   - _read_api_key() and key reading
   - The _safe_call tier check wrapper — all tools should execute without tier checks
   - Remove the 3 RunPod MCP tools (configure_runpod, generate_dsl_cloud, check_generation)
   - Keep ALL other MCP tools

2. **scripts/asset_generation/** — DELETE this entire directory (Tripo/Meshy providers)
   - Remove the 5 mesh3d_* MCP tools from server.py
   - Remove the 5 mesh3d_* TCP commands from CommandServer.cpp

3. **scripts/zuplo/** — DELETE this entire directory
4. **scripts/runpod/** — DELETE this entire directory  
5. **scripts/widget_training/** — DELETE this entire directory (training data not shipped)

### Keep everything else:
- All 29 DSL parsers (widget_dsl, anim_dsl, material_dsl, etc.)
- All widget themes (8 JSON files)
- All widget components (31 JSON files)
- All UI assets (icons + textures)
- html_to_widget translator
- mcp_client
- The Blender MCP references (if any exist in teaching tools)

### Remove ElevenLabs references:
- Remove any ElevenLabs MCP tools from server.py
- Remove any ElevenLabs TCP commands from CommandServer.cpp
- Remove any ElevenLabs provider code from scripts/

## Task 2: Update Command Counts

After removing:
- 3 RunPod commands (configure_runpod, generate_dsl_cloud, check_generation)
- 5 mesh3d commands (mesh3d_set_provider_key, mesh3d_get_providers, mesh3d_generate_from_text, mesh3d_generate_from_image, mesh3d_check_task)
- ElevenLabs commands (count TBD)

Calculate new totals and update everywhere.

## Task 3: Update CLAUDE.md

- Remove all references to:
  - RunPod, Zuplo, API keys, subscription model
  - Free tier, Pro tier, tier gating
  - Hosted LLM generation
  - ElevenLabs, Tripo, Meshy
  - $49/month subscription
- Add:
  - $49.99 one-time purchase via FAB
  - All commands available to all users
  - Pure bridge architecture — customer's AI does all creative work
  - Update command counts

## Task 4: Rebuild Dist Package

Build clean `Arcwright_v1.0.0.zip` with:
- Plugin source (no tier gating, no RunPod, no Zuplo)
- All 29 DSL parsers
- Widget themes, components, icons, textures
- MCP server (no tier checks)
- README, CHANGELOG, LICENSE
- NO: training data, runpod scripts, zuplo scripts, asset_generation scripts

## Task 5: Verify Build

- Build and verify zero warnings
- All commands execute without any tier check
- MCP server starts without needing API keys or validation

Report: final command counts, file list, dist size.
