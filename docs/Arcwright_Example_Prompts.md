# Arcwright — Example User Prompts

> 60 realistic requests showing what users would ask Arcwright to build.
> These range from simple to complex, covering common game development patterns.

---

## Blueprint DSL (20 Examples)

### Simple
1. "Create a coin pickup that adds 10 points when collected and destroys itself"
2. "Make a door that opens when the player walks up to it"
3. "Build a spotlight that turns on and off every 3 seconds"
4. "Create an actor that spins slowly on its Z axis"
5. "Make a trigger zone that prints 'Welcome!' when entered"

### Intermediate
6. "Create a health system with 100 HP. When the player takes damage, subtract it from health. If health reaches zero, print 'Game Over' and destroy the actor"
7. "Build a switch that toggles between on and off states. When on, print 'Activated'. When off, print 'Deactivated'"
8. "Make a timed bomb that starts a 5 second countdown on overlap. When the timer expires, print 'BOOM!' and destroy everything within range"
9. "Create a checkpoint system. When the player touches it, save their position to a variable and print 'Checkpoint reached'"
10. "Build a moving platform that goes up 300 units over 3 seconds, waits 2 seconds, then comes back down"

### Advanced
11. "Create a complete treasure chest. It starts closed. When the player overlaps, it opens (set IsOpen to true), adds a random amount between 10 and 50 gold to a GoldCount variable, prints how much gold was found, and plays a sound. Can only be opened once"
12. "Build a turret that checks distance to the player every half second. If within 1000 units, rotate to face the player and print 'Firing'. If the player leaves range, print 'Target lost' and stop tracking"
13. "Make a score manager that tracks Score, HighScore, and Multiplier. Has custom events for AddScore (adds Score × Multiplier), ResetMultiplier, and IncreaseMultiplier. When Score exceeds HighScore, update HighScore and print 'New High Score!'"
14. "Create a day/night cycle controller. A Timer variable increments on tick. When Timer crosses 60, toggle IsNight boolean, reset Timer, and print either 'Night falls' or 'Dawn breaks'"
15. "Build a wave-based spawning system. WaveNumber starts at 1. Every 15 seconds, spawn WaveNumber × 2 enemies, increment WaveNumber, and print 'Wave X'. After wave 10, print 'You survived all waves!'"

### Game Systems
16. "Create a full inventory pickup. It has an ItemName string and ItemCount integer. On overlap, print 'Picked up [ItemName] x[ItemCount]', add to a global inventory, and destroy"
17. "Make a lava floor that damages the player 10 HP per second while standing on it, with a visual warning when entering"
18. "Build a key and lock system. The key pickup sets HasKey to true. The locked door checks HasKey on overlap — if true, opens and prints 'Door unlocked'. If false, prints 'You need a key'"
19. "Create a respawn system. When health reaches zero, wait 3 seconds, teleport the player back to the spawn point, reset health to 100, and print 'Respawned'"
20. "Build a shop terminal. On overlap, create and display a shop widget. The player can see item names and prices. On leaving the overlap zone, remove the widget"

---

## Behavior Tree DSL (20 Examples)

### Simple
1. "Create an AI that stands still and waits 5 seconds in a loop"
2. "Make an enemy that walks to a single patrol point and waits there forever"
3. "Build an AI that just chases the player whenever it can see them"
4. "Create a guard that rotates to face the player at all times"
5. "Make an NPC that walks between point A and point B repeatedly"

### Patrol & Chase
6. "Build a patrol guard. It walks between three waypoints with 2 second pauses. If it detects a player within 800 units, it abandons patrol and chases. When the player gets away, it returns to patrolling"
7. "Create an enemy that patrols a route. If it hears a noise (blackboard key SoundLocation is set), it investigates that location. If it finds nothing after 5 seconds, clears the key and resumes patrol"
8. "Make a flying enemy that patrols at a set height. When the player is below, it dives to attack then returns to patrol height"
9. "Build a thief AI. It patrols normally, but when it sees a treasure item (TreasureActor key set), it runs to grab it. After grabbing, it flees to an escape point"
10. "Create a pack hunter. It follows a leader (LeaderActor key). If the leader attacks, all pack members attack the same target"

### Combat
11. "Make a boss with three phases. Above 70% health: basic melee attacks. Between 30-70%: ranged attacks with a 3 second cooldown. Below 30%: rage mode with fast melee and no cooldown"
12. "Build a sniper AI. It finds a hiding spot (CoverPoint key), moves there, then repeatedly shoots at the player with a 2 second delay between shots. If the player gets within 300 units, flee to a new cover point"
13. "Create a healer AI. It scans for nearby allies. If any ally has low health (below 50%), move to them and heal. If no ally needs healing, follow the player at a safe distance"
14. "Make a berserker that attacks the nearest target relentlessly. No fleeing, no cover. Just find closest enemy, run at them, attack, wait 0.5 seconds, repeat"
15. "Build a tactical enemy. It checks line of sight. If it has LOS, it attacks from range. If it loses LOS, it flanks by moving to a side position. Uses services to continuously update distance and LOS"

### Complex Behaviors
16. "Create a shopkeeper NPC. When the player approaches, face them and set IsInConversation to true. While in conversation, play idle animation. When the player leaves, set IsInConversation to false and resume wandering"
17. "Build a zombie AI. It wanders randomly when no target is near. When it detects a player (sound or sight), it shambles toward them slowly. When within attack range, it lunges forward, attacks, then pauses for 3 seconds"
18. "Make a companion AI that follows the player at 400 units distance. If the player enters combat (IsPlayerInCombat key), the companion runs to help and attacks the player's target. After combat ends, return to following"
19. "Create a stealth enemy. It patrols silently. When it spots the player, it sets an alert state and calls for reinforcements (sets GlobalAlert key). Then it chases the player. If it loses the player for 10 seconds, returns to patrol and clears alert"
20. "Build a dragon boss. Phase 1: fly overhead and breathe fire downward every 5 seconds. Phase 2: land and do tail swipe attacks when player is behind, bite attacks when in front. Phase 3: enraged flying with rapid fire breath. Transition between phases based on health thresholds"

---

## Data Table DSL (20 Examples)

### Weapons & Equipment
1. "Create a weapons table with name, damage, fire rate, reload time, ammo capacity, and weapon type"
2. "Make an armor table with armor name, defense rating, weight, durability, required level, and armor slot"
3. "Build a crafting materials table with material name, rarity, stack limit, sell value, and description"
4. "Create a shield table with name, block percentage, stamina cost to block, weight, and whether it can parry"

### Characters & Enemies
5. "Make an enemy stats table with enemy name, health, damage, speed, detection range, attack range, XP reward, and loot table name"
6. "Create a character class table. Each class has a name, base health, base mana, strength, dexterity, intelligence, starting weapon, and description"
7. "Build an NPC merchant table with NPC name, shop location, greeting dialogue, gold carried, reputation required, and what category they sell"
8. "Make a companion stats table with name, class, health, damage, special ability name, and loyalty requirement"

### Progression & Economy
9. "Create a level-up requirements table. Each level has required XP, health bonus, damage bonus, and what skill unlocks at that level"
10. "Build a shop inventory with item name, buy price, sell price, stock quantity, restock time in hours, and required player level"
11. "Make an achievement table with achievement name, title, description, unlock condition, target value, and XP reward"
12. "Create a season pass rewards table with tier number, free reward, free amount, premium reward, premium amount, and XP needed"

### Game Configuration
13. "Build a difficulty settings table with difficulty name, enemy health multiplier, enemy damage multiplier, player damage multiplier, XP rate, and loot drop rate"
14. "Create a wave configuration table for a survival game with wave number, enemy type, enemy count, spawn interval, bonus enemy health, and boss flag"
15. "Make a sound effects config table with event name, volume, pitch, falloff distance, priority, and category"
16. "Build a UI theme table with theme name, primary color, secondary color, background color, text color, and accent color"

### Quests & Dialogue
17. "Create a quest table with quest name, description, quest giver, required level, XP reward, gold reward, quest type, and prerequisite quest"
18. "Build a dialogue table with line ID, speaker name, dialogue text, display duration, next line ID, and required game flag"
19. "Make a quest objectives table with objective ID, parent quest, description, objective type, target name, target count, and whether it is optional"
20. "Create a recipe crafting table with result item, ingredient 1 name, ingredient 1 count, ingredient 2 name, ingredient 2 count, crafting time, and required crafting level"

---

*These 60 prompts represent the range of what game developers would actually ask Arcwright to build.*
