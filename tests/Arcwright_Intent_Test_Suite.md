# Arcwright — Plain Talk Intent Test Suite

> **Purpose:** Test that natural language commands route correctly and execute through the intent system
> **Method:** Send each prompt to the intent server, verify classification, then execute against live UE editor
> **Prerequisite:** UE editor running on TCP 13377, intent server running on TCP 13380

---

## TEST SETUP

Before running tests, create a known level state:
1. Create 5 Blueprints: BP_WallSegment, BP_EnemyGuard, BP_GoldCoin, BP_Torch, BP_HealthPotion
2. Each BP_EnemyGuard has: Health (Float=100), Damage (Float=15), Speed (Float=300)
3. Each BP_GoldCoin has: Value (Int=10)
4. Each BP_Torch has: Intensity (Float=5000)
5. Spawn in level: 8x BP_WallSegment, 3x BP_EnemyGuard, 5x BP_GoldCoin, 4x BP_Torch, 2x BP_HealthPotion
6. Apply MI_Stone to all WallSegment actors
7. Apply MI_GoldMetal to all GoldCoin actors

---

## CATEGORY 1: SIMPLE MODIFY — Material Changes (10 tests)

| # | Prompt | Expected Mode | Expected Action |
|---|---|---|---|
| 1.01 | "Change the wall texture to brick" | MODIFY | find *wall* → batch_apply_material brick |
| 1.02 | "Make all the walls look like marble" | MODIFY | find *wall* → batch_apply_material marble |
| 1.03 | "Swap the stone material on the walls for concrete" | MODIFY | find *wall* → batch_replace_material stone→concrete |
| 1.04 | "Replace every gold material with silver" | MODIFY | batch_replace_material gold→silver |
| 1.05 | "The walls need a different texture, use wood" | MODIFY | find *wall* → batch_apply_material wood |
| 1.06 | "Give the floor a lava material" | MODIFY | find *floor* → batch_apply_material lava |
| 1.07 | "Update torch materials to something warmer" | MODIFY | find *torch* → batch_apply_material (warm suggestion) |
| 1.08 | "I want the coins to look more realistic" | MODIFY | find *coin* → suggest material options |
| 1.09 | "Everything stone should be brick instead" | MODIFY | batch_replace_material stone→brick |
| 1.10 | "Paint the walls red" | MODIFY | find *wall* → batch_apply_material or create_simple_material red |

## CATEGORY 2: SIMPLE MODIFY — Variable Changes (10 tests)

| # | Prompt | Expected Mode | Expected Action |
|---|---|---|---|
| 2.01 | "Set health to 200 on all enemies" | MODIFY | find *enemy* → batch_set_variable Health=200 |
| 2.02 | "Make the enemies faster" | MODIFY | find *enemy* → batch_set_variable Speed (increase) |
| 2.03 | "Double the enemy damage" | MODIFY | find *enemy* → batch_set_variable Damage=30 |
| 2.04 | "Gold coins should be worth 50 each" | MODIFY | find *coin* → batch_set_variable Value=50 |
| 2.05 | "Reduce enemy health to 50" | MODIFY | find *enemy* → batch_set_variable Health=50 |
| 2.06 | "Make the torches brighter" | MODIFY | find *torch* → batch_set_variable Intensity (increase) |
| 2.07 | "Enemies are too slow, speed them up" | MODIFY | find *enemy* → batch_set_variable Speed (increase) |
| 2.08 | "Turn down the torch intensity to 2000" | MODIFY | find *torch* → batch_set_variable Intensity=2000 |
| 2.09 | "Health potions should heal 50 instead" | MODIFY | find *health* → batch_set_variable (heal amount)=50 |
| 2.10 | "All enemies need 500 HP, 40 damage, and 600 speed" | MODIFY | find *enemy* → batch_set_variable Health=500, Damage=40, Speed=600 |

## CATEGORY 3: SIMPLE MODIFY — Transform and Properties (10 tests)

| # | Prompt | Expected Mode | Expected Action |
|---|---|---|---|
| 3.01 | "Scale all enemies up by 1.5" | MODIFY | find *enemy* → batch_set_property scale=1.5 |
| 3.02 | "Make the coins smaller" | MODIFY | find *coin* → batch_set_property scale (decrease) |
| 3.03 | "Hide all the torches" | MODIFY | find *torch* → batch_set_property visibility=false |
| 3.04 | "Show all hidden actors" | MODIFY | find (hidden) → batch_set_property visibility=true |
| 3.05 | "Move all coins up by 50 units" | MODIFY | find *coin* → batch_set_property location Z+50 relative |
| 3.06 | "Rotate all enemies to face north" | MODIFY | find *enemy* → batch_set_property rotation yaw=0 |
| 3.07 | "Delete all the gold coins" | MODIFY | find *coin* → batch_delete_actors |
| 3.08 | "Remove every torch from the level" | MODIFY | find *torch* → batch_delete_actors |
| 3.09 | "Clear out all the enemies" | MODIFY | find *enemy* → batch_delete_actors |
| 3.10 | "Resize the walls to be twice as tall" | MODIFY | find *wall* → batch_set_property scale Z=2.0 |

## CATEGORY 4: SIMPLE MODIFY — Component Changes (5 tests)

| # | Prompt | Expected Mode | Expected Action |
|---|---|---|---|
| 4.01 | "Add a point light to every torch" | MODIFY | find_blueprints *torch* → batch_add_component PointLight |
| 4.02 | "Give all enemies a sphere collision" | MODIFY | find_blueprints *enemy* → batch_add_component SphereCollision |
| 4.03 | "Add audio components to the torches" | MODIFY | find_blueprints *torch* → batch_add_component Audio |
| 4.04 | "Put a box collision on every coin" | MODIFY | find_blueprints *coin* → batch_add_component BoxCollision |
| 4.05 | "Every health potion needs a point light" | MODIFY | find_blueprints *health* → batch_add_component PointLight |

## CATEGORY 5: SIMPLE MODIFY — Rename and Reparent (5 tests)

| # | Prompt | Expected Mode | Expected Action |
|---|---|---|---|
| 5.01 | "Rename BP_GoldCoin to BP_TreasureCoin" | MODIFY | rename_asset GoldCoin→TreasureCoin |
| 5.02 | "Rename the enemy blueprint to BP_SkeletonWarrior" | MODIFY | rename_asset EnemyGuard→SkeletonWarrior |
| 5.03 | "Change the coin's parent class to Pawn" | MODIFY | reparent_blueprint GoldCoin→Pawn |
| 5.04 | "Make BP_EnemyGuard extend Character instead of Actor" | MODIFY | reparent_blueprint EnemyGuard→Character |
| 5.05 | "Rename all the wall blueprints to BP_StoneWall" | MODIFY | rename_asset WallSegment→StoneWall |

## CATEGORY 6: QUERY — Find and Inspect (10 tests)

| # | Prompt | Expected Mode | Expected Action |
|---|---|---|---|
| 6.01 | "How many enemies are in the level?" | QUERY | find_actors *enemy* → count |
| 6.02 | "List all blueprints in the project" | QUERY | find_blueprints → list |
| 6.03 | "Show me all the actors in the level" | QUERY | find_actors → list all |
| 6.04 | "What materials exist in the project?" | QUERY | find_assets type=MaterialInstance → list |
| 6.05 | "Which blueprints have a Health variable?" | QUERY | find_blueprints has_variable=Health → list |
| 6.06 | "How many coins are placed in the level?" | QUERY | find_actors *coin* → count |
| 6.07 | "What's in the level right now?" | QUERY | get_level_info or find_actors → summary |
| 6.08 | "Show me the enemy blueprint details" | QUERY | find_blueprints *enemy* → get_info |
| 6.09 | "Are there any torches near the entrance?" | QUERY | find_actors *torch* (location filter) → list |
| 6.10 | "What components does the enemy have?" | QUERY | find_blueprints *enemy* → components list |

## CATEGORY 7: CREATE — New Assets (10 tests)

| # | Prompt | Expected Mode | Expected Action |
|---|---|---|---|
| 7.01 | "Create a health pickup that heals 25 HP" | CREATE | create_blueprint (health pickup) |
| 7.02 | "Make a new enemy that shoots projectiles" | CREATE | create_blueprint (ranged enemy) |
| 7.03 | "Build a pressure plate that opens a door" | CREATE | create_blueprint (pressure plate) |
| 7.04 | "Generate a patrol AI for the guards" | CREATE | create_behavior_tree (patrol) |
| 7.05 | "I need a weapons stats table" | CREATE | create_data_table (weapons) |
| 7.06 | "Create a wave spawner that sends enemies every 10 seconds" | CREATE | create_blueprint (wave spawner) |
| 7.07 | "Make a score HUD with health bar and coin counter" | CREATE | create_widget_blueprint (HUD) |
| 7.08 | "Set up FPS controls for the game" | CREATE | setup game base fps |
| 7.09 | "Add dark indoor lighting to the level" | CREATE | setup_scene_lighting indoor_dark |
| 7.10 | "Create a new brick material" | CREATE | create_textured_material brick |

## CATEGORY 8: MULTI — Complex Multi-Step (10 tests)

| # | Prompt | Expected Mode | Expected Operations |
|---|---|---|---|
| 8.01 | "Make a dark dungeon with tough enemies and gold loot" | MULTI | lighting + enemy BP + coin BP + spawn both |
| 8.02 | "Create a patrol enemy, give it 200 HP, and spawn 5 of them" | MULTI | create BP + set variable + spawn ×5 |
| 8.03 | "Add torches to the hallway and make them glow warm" | MULTI | spawn torches + create material + apply material |
| 8.04 | "Set up the arena: FPS controls, dark lighting, spawn 3 enemies" | MULTI | game base + lighting + spawn enemies |
| 8.05 | "Create a boss room with one strong enemy, health pickups, and dramatic lighting" | MULTI | lighting + boss BP + health BP + spawn all |
| 8.06 | "Replace all stone with marble and make the room brighter" | MULTI | batch_replace_material + modify lighting |
| 8.07 | "Delete all coins, create a gem pickup worth 100, and spawn 8 of them" | MULTI | delete coins + create gem BP + spawn ×8 |
| 8.08 | "Create an enemy, a behavior tree for it, and wire them together" | MULTI | create BP + create BT + setup_ai_for_pawn |
| 8.09 | "Build a complete checkpoint system with save, respawn, and a visual indicator" | MULTI | create checkpoint BP + create respawn BP + spawn |
| 8.10 | "Make all enemies tougher, add more coins, and change the walls to brick" | MULTI | batch_set_variable enemies + spawn coins + batch_apply_material walls |

## CATEGORY 9: CONVERSATIONAL / VAGUE (10 tests)

| # | Prompt | Expected Mode | Expected Behavior |
|---|---|---|---|
| 9.01 | "These walls are too plain" | MODIFY or CLARIFY | Suggest material change or ask what style |
| 9.02 | "The level feels empty" | MULTI or CLARIFY | Suggest adding actors or ask what to add |
| 9.03 | "Make it better" | CLARIFY | Ask what specifically to improve |
| 9.04 | "Something isn't right with the enemies" | CLARIFY | Ask what's wrong (health? speed? behavior?) |
| 9.05 | "I want more variety" | CLARIFY | Ask variety of what (enemies? textures? pickups?) |
| 9.06 | "This room needs atmosphere" | MULTI or CLARIFY | Suggest lighting + fog + post-process or ask |
| 9.07 | "Can you help me with the boss fight?" | CLARIFY | Ask what kind of boss, what mechanics |
| 9.08 | "Too many coins" | MODIFY | find *coin* → suggest deleting some or reducing count |
| 9.09 | "The game is too easy" | MODIFY or CLARIFY | Suggest increasing enemy stats or ask specifics |
| 9.10 | "I'm stuck" | CLARIFY | Ask what they're trying to accomplish |

## CATEGORY 10: NON-ENGLISH (12 tests — one per language)

| # | Prompt | Language | Expected Mode | Expected Action |
|---|---|---|---|---|
| 10.01 | "Cambia la textura de las paredes a ladrillo" | Spanish | MODIFY | walls → brick material |
| 10.02 | "Augmente la santé de tous les ennemis à 300" | French | MODIFY | enemies → Health=300 |
| 10.03 | "Lösche alle Goldmünzen" | German | MODIFY | delete coins |
| 10.04 | "Crie um inimigo com 500 de vida" | Portuguese | CREATE | enemy BP with 500 HP |
| 10.05 | "壁のマテリアルをレンガに変えて" | Japanese | MODIFY | walls → brick |
| 10.06 | "적의 체력을 200으로 설정하세요" | Korean | MODIFY | enemies → Health=200 |
| 10.07 | "把所有敌人的伤害改为50" | Chinese | MODIFY | enemies → Damage=50 |
| 10.08 | "Удали все факелы с уровня" | Russian | MODIFY | delete torches |
| 10.09 | "احذف جميع العملات الذهبية" | Arabic | MODIFY | delete coins |
| 10.10 | "सभी दुश्मनों को तेज़ बनाओ" | Hindi | MODIFY | enemies → Speed increase |
| 10.11 | "Tüm düşmanları sil" | Turkish | MODIFY | delete enemies |
| 10.12 | "Erstelle einen Gesundheits-Pickup" | German | CREATE | health pickup BP |

---

## SCORING

For each test, score:
1. **Intent correct** (1 point): Did the LLM return the right mode? (CREATE/MODIFY/QUERY/MULTI/CLARIFY)
2. **Target correct** (1 point): Did it identify the right entities? (walls, enemies, coins, etc.)
3. **Action correct** (1 point): Did it plan the right commands? (batch_apply_material, batch_set_variable, etc.)
4. **Execution correct** (1 point): Did the commands actually run and produce the right result in UE?

**Total possible: 92 tests × 4 points = 368 points**

| Score Range | Grade |
|---|---|
| 350-368 (95%+) | Production ready |
| 330-349 (90%+) | Minor fixes needed |
| 295-329 (80%+) | Significant gaps, needs iteration |
| Below 295 | Major rework needed |

---

## RUNNING THE TESTS

```bash
# Start UE editor and verify TCP 13377
python scripts/mcp_client/test_connection.py

# Start intent server on 13380
python scripts/intent_server.py

# Run setup to create known level state
python scripts/tests/intent_test_setup.py

# Run full test suite
python scripts/tests/test_intent_suite.py --all --verbose

# Run specific category
python scripts/tests/test_intent_suite.py --category 1 --verbose

# Run non-English only
python scripts/tests/test_intent_suite.py --category 10 --verbose
```

---

*92 tests. 12 languages. Every way a human could phrase a game development request.*
