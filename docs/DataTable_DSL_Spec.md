# Arcwright — Data Table DSL Specification

> **Version:** 0.1 (Draft)
> **Last Updated:** 2026-03-07
> **Status:** Design phase — not yet implemented
> **Depends on:** DT parser, DT plugin builder, DT training data

## 1. Why Data Tables

Every game with items, weapons, abilities, enemies, levels, dialogue, or loot uses Data Tables. UE5's UDataTable is the standard way to store structured game data. Without Data Table support, designers must manually create and populate tables in the UE editor — tedious and error-prone.

Data Tables are the simplest DSL domain because:
- Flat tabular structure (no graphs, no trees, no nesting)
- Well-defined column types
- Every row follows the same schema
- Direct mapping to UE's UDataTable + FTableRowBase

This should train faster than both Blueprints and Behavior Trees.

---

## 2. UE5 Data Table Architecture

**UDataTable** — The table asset. References a row struct and contains rows of that struct.

**FTableRowBase** — Base class for row structs. Custom structs inherit from this and define columns as UPROPERTY fields.

**UScriptStruct** — The struct definition that determines column names and types.

**In practice:** You create a struct (defines columns), then a DataTable (references the struct, contains rows). The struct must exist before the table.

---

## 3. Data Table DSL Structure

```
DATATABLE: <table_name>
STRUCT: <struct_name>

COLUMN <column_name>: <type> [= <default>]
COLUMN <column_name>: <type> [= <default>]

ROW <row_name>: <value1>, <value2>, <value3>
ROW <row_name>: <value1>, <value2>, <value3>
```

### Rules:
- `DATATABLE:` names the UDataTable asset (e.g. DT_Weapons, DT_Items)
- `STRUCT:` names the row struct (e.g. FWeaponData, FItemData)
- `COLUMN` declarations define the schema — name, type, optional default
- `ROW` entries provide data — row name followed by comma-separated values in column order
- Values must match column types
- String values are quoted: `"Fire Sword"`
- Numeric values are unquoted: `25.0`, `100`
- Bool values: `true`, `false`
- Vector values: `(100,200,300)`
- Enum values: unquoted identifiers: `Rare`, `Common`
- Asset references: quoted paths: `"/Game/Meshes/Sword.Sword"`
- Empty/null values: `_` or `null`

---

## 4. Column Types

| DSL Type | UE Type | Example Values |
|---|---|---|
| `String` | FString | `"Fire Sword"`, `"Health Potion"` |
| `Name` | FName | `"WeaponSlot1"` |
| `Text` | FText | `"This is a legendary blade"` |
| `Int` | int32 | `100`, `0`, `-5` |
| `Float` | float | `25.5`, `0.0`, `3.14` |
| `Bool` | bool | `true`, `false` |
| `Vector` | FVector | `(100,200,300)` |
| `Rotator` | FRotator | `(0,90,0)` |
| `Color` | FLinearColor | `(1.0,0.0,0.0,1.0)` |
| `Enum:<name>` | UEnum | `Rare`, `Common`, `Legendary` |
| `Asset:StaticMesh` | TSoftObjectPtr<UStaticMesh> | `"/Game/Meshes/Sword.Sword"` |
| `Asset:Texture` | TSoftObjectPtr<UTexture2D> | `"/Game/Textures/Icon.Icon"` |
| `Asset:Sound` | TSoftObjectPtr<USoundBase> | `"/Game/Sounds/Hit.Hit"` |
| `Asset:Blueprint` | TSoftClassPtr<AActor> | `"/Game/BP_Projectile.BP_Projectile_C"` |
| `Struct:<name>` | nested struct | `{10,20,30}` |
| `Array:<type>` | TArray | `[1,2,3]` or `["a","b","c"]` |

---

## 5. Common Game Data Patterns

### Weapons Table

```
DATATABLE: DT_Weapons
STRUCT: FWeaponData

COLUMN Name: String
COLUMN Damage: Float
COLUMN FireRate: Float = 1.0
COLUMN Range: Float = 1000.0
COLUMN AmmoType: String = "Standard"
COLUMN MaxAmmo: Int = 30
COLUMN Rarity: String = "Common"
COLUMN Icon: Asset:Texture
COLUMN Mesh: Asset:StaticMesh

ROW Pistol: "Pistol", 15.0, 0.5, 500.0, "Light", 12, "Common", "/Game/UI/Icons/Pistol", "/Game/Meshes/Pistol"
ROW Shotgun: "Shotgun", 45.0, 1.2, 300.0, "Shell", 8, "Uncommon", "/Game/UI/Icons/Shotgun", "/Game/Meshes/Shotgun"
ROW AssaultRifle: "Assault Rifle", 22.0, 0.1, 800.0, "Standard", 30, "Common", "/Game/UI/Icons/AR", "/Game/Meshes/AR"
ROW Sniper: "Sniper Rifle", 90.0, 2.0, 3000.0, "Heavy", 5, "Rare", "/Game/UI/Icons/Sniper", "/Game/Meshes/Sniper"
ROW Railgun: "Railgun", 150.0, 3.5, 5000.0, "Energy", 3, "Legendary", "/Game/UI/Icons/Railgun", "/Game/Meshes/Railgun"
```

### Items / Inventory

```
DATATABLE: DT_Items
STRUCT: FItemData

COLUMN DisplayName: String
COLUMN Description: Text
COLUMN MaxStack: Int = 1
COLUMN Value: Int = 0
COLUMN Weight: Float = 0.0
COLUMN ItemType: String = "Misc"
COLUMN IsConsumable: Bool = false
COLUMN UseEffect: String = ""
COLUMN Icon: Asset:Texture

ROW HealthPotion: "Health Potion", "Restores 50 health points", 10, 25, 0.5, "Consumable", true, "Heal:50", _
ROW ManaPotion: "Mana Potion", "Restores 30 mana points", 10, 30, 0.5, "Consumable", true, "RestoreMana:30", _
ROW IronSword: "Iron Sword", "A basic iron sword", 1, 100, 5.0, "Weapon", false, "", _
ROW WoodenShield: "Wooden Shield", "Blocks some damage", 1, 75, 8.0, "Armor", false, "", _
ROW GoldCoin: "Gold Coin", "Currency", 999, 1, 0.01, "Currency", false, "", _
```

### Enemy Stats

```
DATATABLE: DT_Enemies
STRUCT: FEnemyData

COLUMN DisplayName: String
COLUMN MaxHealth: Float
COLUMN Damage: Float
COLUMN MoveSpeed: Float = 300.0
COLUMN DetectionRange: Float = 1000.0
COLUMN AttackRange: Float = 200.0
COLUMN AttackCooldown: Float = 1.0
COLUMN XPReward: Int = 10
COLUMN LootTable: String = ""
COLUMN BehaviorTree: Asset:Blueprint

ROW Goblin: "Goblin", 50.0, 8.0, 400.0, 800.0, 150.0, 0.8, 15, "LT_Goblin", "/Game/AI/BT_Goblin"
ROW Skeleton: "Skeleton", 80.0, 12.0, 250.0, 600.0, 200.0, 1.5, 25, "LT_Skeleton", "/Game/AI/BT_Skeleton"
ROW Dragon: "Dragon", 500.0, 50.0, 200.0, 2000.0, 500.0, 3.0, 500, "LT_Dragon", "/Game/AI/BT_Dragon"
ROW Slime: "Slime", 20.0, 3.0, 150.0, 400.0, 100.0, 0.5, 5, "LT_Slime", "/Game/AI/BT_Slime"
```

### Level / Wave Configuration

```
DATATABLE: DT_Waves
STRUCT: FWaveData

COLUMN WaveNumber: Int
COLUMN EnemyType: String
COLUMN EnemyCount: Int
COLUMN SpawnInterval: Float = 2.0
COLUMN BonusHealth: Float = 0.0
COLUMN BonusDamage: Float = 0.0

ROW Wave1: 1, "Goblin", 3, 3.0, 0.0, 0.0
ROW Wave2: 2, "Goblin", 5, 2.5, 0.0, 0.0
ROW Wave3: 3, "Skeleton", 3, 2.0, 10.0, 2.0
ROW Wave4: 4, "Goblin", 4, 1.5, 0.0, 0.0
ROW Wave5: 5, "Dragon", 1, 0.0, 50.0, 10.0
```

### Dialogue

```
DATATABLE: DT_Dialogue
STRUCT: FDialogueEntry

COLUMN Speaker: String
COLUMN Text: Text
COLUMN Duration: Float = 3.0
COLUMN NextRow: Name = ""
COLUMN Condition: String = ""
COLUMN Animation: String = ""

ROW Intro1: "Guard", "Halt! Who goes there?", 2.5, "Intro2", "", "Alert"
ROW Intro2: "Player", "Just a traveler.", 2.0, "Intro3", "", ""
ROW Intro3: "Guard", "Very well. The village is ahead.", 3.0, "", "", "Wave"
ROW Quest1: "Elder", "Dark times are upon us. Will you help?", 4.0, "Quest2", "HasMetElder", "Worried"
ROW Quest2: "Player", "What do you need?", 2.0, "Quest3", "", ""
ROW Quest3: "Elder", "Defeat the dragon in the northern cave.", 3.5, "", "", "Point"
```

### Ability / Skill Table

```
DATATABLE: DT_Abilities
STRUCT: FAbilityData

COLUMN DisplayName: String
COLUMN Description: Text
COLUMN ManaCost: Float = 0.0
COLUMN Cooldown: Float = 1.0
COLUMN Damage: Float = 0.0
COLUMN Healing: Float = 0.0
COLUMN Range: Float = 500.0
COLUMN CastTime: Float = 0.0
COLUMN AbilityType: String = "Active"

ROW Fireball: "Fireball", "Launches a fireball dealing fire damage", 25.0, 3.0, 40.0, 0.0, 1000.0, 0.5, "Active"
ROW Heal: "Heal", "Restores health to the caster", 30.0, 5.0, 0.0, 60.0, 0.0, 1.0, "Active"
ROW Shield: "Shield", "Reduces damage taken by 50% for 5 seconds", 20.0, 10.0, 0.0, 0.0, 0.0, 0.0, "Buff"
ROW Dash: "Dash", "Quick dash forward", 10.0, 2.0, 0.0, 0.0, 500.0, 0.0, "Movement"
ROW PoisonCloud: "Poison Cloud", "Creates a poisonous area", 35.0, 8.0, 15.0, 0.0, 600.0, 0.8, "Active"
```

---

## 6. Validation Checklist

- [ ] Starts with `DATATABLE:` (no preamble)
- [ ] Has `STRUCT:` declaration
- [ ] At least one `COLUMN` defined
- [ ] At least one `ROW` defined
- [ ] All ROW value counts match COLUMN count
- [ ] String values are properly quoted
- [ ] Numeric values are valid numbers
- [ ] Bool values are `true` or `false`
- [ ] Vector values use `(x,y,z)` format
- [ ] No duplicate row names
- [ ] No duplicate column names
- [ ] Default values match column types
- [ ] Asset paths start with `/Game/` or `/Engine/`

---

## 7. Implementation Plan

### Phase 1: Parser
- `dt_parser.py` — parse DSL to IR JSON
- `dt_node_map.py` — column type mappings
- Validate schema, check row/column consistency
- Output IR: `{"table_name": "...", "struct_name": "...", "columns": [...], "rows": [...]}`

### Phase 2: Plugin Builder
- Create UScriptStruct dynamically (or use UUserDefinedStruct)
- Create UDataTable referencing the struct
- Populate rows from IR
- TCP command: `create_data_table_from_dsl`
- TCP command: `get_data_table_info`

### Phase 3: Training Data
- DT Lesson 01: weapons, items, enemies, waves (common patterns)
- Should train very fast — simpler format than BT or Blueprint
- Target: 98%+ accuracy in 1-2 training runs

### Phase 4: Integration
- Blueprint nodes to read Data Table rows at runtime
- Template: "enemy spawner that reads stats from DT_Enemies"
- Template: "shop UI that lists items from DT_Items"

---

## 8. DT DSL vs Other DSLs

| Aspect | Blueprint DSL | BT DSL | DT DSL |
|---|---|---|---|
| Structure | Flat graph | Indented tree | Tabular rows/columns |
| Complexity | High (179+ nodes) | Medium (37 nodes) | Low (types + data) |
| Training difficulty | Hard (6+ versions) | Easy (95% on v1) | Expected: Very easy |
| Use case | Logic | AI behavior | Game data |
| Estimated training | 2-3 hours | 6 hours | ~30 minutes |

---

## 9. Version History

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-03-07 | Initial draft — structure, types, patterns, implementation plan |

---

*Draft specification. Will be refined through implementation.*
