# D&D 5E 2024 Combat Simulator

A Monte Carlo 1v1 combat simulator for **D&D 2024 PHB** (5.5e). Define characters in YAML, run thousands of fights, get hard numbers on win rates, damage per round, and HP remaining. No more bar arguments about whether Berserker or Battle Master wins in the arena — let the dice decide.

---

## What It Is

This simulator runs fully rule-accurate 1v1 combat between any two builds and reports statistical outcomes across N iterations. Everything that matters in a real fight is modeled: initiative, weapon mastery properties, concentration saves, subclass features, condition mechanics, and high-level spell effects including instant-win conditions.

**Output looks like this:**

```
Berserker Greatsword Fire Goliath L5   87.3% | HP remaining: 24.1 avg | 3.2 avg rounds
Evocation Wizard Human L5             12.7% | HP remaining: 0.0 avg  | 3.2 avg rounds
```

The simulator is data-driven: add a `.yaml` file to `data/builds/` and it's immediately available for ranking.

---

## Current Scope

### Levels
**3, 5, and 7** are fully supported with appropriate armor progression, spell slot depth, and subclass features per level. Some L6 builds exist for specific matchup analysis. L9 spells (Power Word Kill, Wish, Meteor Swarm, etc.) are implemented for completeness.

### Classes & Subclasses (12 classes)

| Class | Subclasses |
|---|---|
| **Fighter** | Battle Master, Champion, Eldritch Knight |
| **Barbarian** | Berserker, Bear Totem |
| **Paladin** | Vengeance, Devotion |
| **Ranger** | Hunter, Gloom Stalker |
| **Rogue** | Thief, Arcane Trickster, Assassin |
| **Monk** | Open Hand, Shadow |
| **Cleric** | War, Forge |
| **Druid** | Moon |
| **Sorcerer** | Draconic Bloodline |
| **Warlock** | Fiend, Hexblade (Blade Pact) |
| **Wizard** | Evocation, Bladesinger |
| **Bard** | Lore, Swords |

### Species
Human, Orc, Elf, Halfling, Goliath (Fire, Stone), Dwarf

### Pre-Built Characters
**110+ builds** ready to run. Covers all class/species/weapon combinations across L3, L5, and L7. Use `./dnd-sim list` to see everything.

### Spells (40+)
Full mechanical implementations from cantrips through L9:

| Level | Spells |
|---|---|
| Cantrip | Fire Bolt, Toll the Dead, Sacred Flame, Vicious Mockery, Shillelagh |
| L1–L2 | Magic Missile, Chromatic Orb, Guiding Bolt, Scorching Ray, Spiritual Weapon, Thunderwave, Healing Word, Dissonant Whispers |
| L3 | Fireball, Spirit Guardians, Call Lightning, Hypnotic Pattern |
| L4–L5 | Banishment, Polymorph, Blight, Greater Invisibility, Steel Wind Strike, Hold Monster, Synaptic Static, Destructive Wave, Cone of Cold |
| L6–L7 | Chain Lightning, Sunbeam, Finger of Death, Power Word Pain, Power Word Stun, Harm, Disintegrate, Forcecage |
| L8–L9 | Abi-Dalzim's Horrid Wilting, Sunburst, Meteor Swarm, Power Word Kill, Time Stop, True Polymorph, Wish |

---

## Key Mechanics

Everything is simulated per the 2024 PHB:

**Combat flow**
- Initiative: d20 + DEX modifier, coin flip on ties
- Attack resolution: to-hit vs AC, critical hits, damage rolls
- Action economy: Action, Bonus Action, Reaction tracked per turn
- Armor progression by level (Leather → Plate as characters advance)

**Weapon Mastery (2024)**
All mastery properties implemented: Nick, Topple, Graze, Push, Sap, Slow, Cleave, Vex — with correct once-per-turn restrictions and interaction rules.

**Conditions**
Prone, Stunned, Paralyzed (auto-crit), Banished, Polymorphed, Charmed, Frightened, Poisoned, Greater Invisible, Incapacitated, Pain, Dodging — all with proper attack/save modifiers and end conditions.

**Concentration**
Tracked per character. Constitution saving throws on damage (DC 10 or half damage taken, whichever is higher). Concentration spells drop on failed save or KO.

**Subclass features**
- Battle Master: Superiority Dice (Precision, Trip, Riposte, Menacing, Disarming)
- Berserker: Frenzy (bonus action weapon attack each turn while raging)
- Bear Totem: Resistance to all non-psychic damage while raging
- Champion: Extended crit range (19–20, then 18–20 at higher levels)
- Eldritch Knight: War Magic, Weapon Bond
- Vengeance Paladin: Vow of Enmity (advantage), Divine Smite
- Devotion Paladin: Sacred Weapon, Divine Smite
- Gloom Stalker: Dread Ambusher (extra attack + bonus damage on round 1)
- Hunter Ranger: Colossus Slayer, Multiattack (Hunter's Mark no concentration in 2024)
- Assassin: Assassinate (auto-crit vs surprised targets, advantage)
- Open Hand: Flurry technique (Push/Prone/Deny Reaction), Stunning Strike
- Shadow Monk: Shadow Arts (impose incoming attack disadvantage)
- Moon Druid: Wild Shape, Call Lightning
- Bladesinger: Bladesong (+INT to AC, speed, and concentration saves)
- Hexblade: Hexblade's Curse (bonus damage, crit on 19–20, regain HP on kill)
- Swords Bard: Blade Flourishes, Extra Attack

**High-level spell effects**
Instant-win conditions modeled for L7–L9 spells: Banishment (remove from combat), Polymorph (stat block replacement), Power Word Kill (instant death at ≤100 HP), Time Stop (extra turns), Wish (flexible effect), etc.

**Giant Ancestry (Goliath)**
- Fire: +1d10 fire on hit (PB/LR uses)
- Stone (Frost Goliath): Stone's Endurance — reaction to reduce damage by 1d12+CON
- Large Form (L5+): Goliath expands to Large size for the turn (bonus damage, forced movement)

---

## Usage

### Installation

```bash
git clone <repo>
cd dnd-combat-sim
pip install -e .
```

### Commands

**Show a build's stats:**
```bash
./dnd-sim show berserker_greatsword_orc_5
```

**Run a 1v1 with verbose output:**
```bash
./dnd-sim fight --build1 berserker_greatsword_orc_5 --build2 battlemaster_sb_stone_goliath_5 -n 1000
```

**Round-robin ranking across a tag group:**
```bash
./dnd-sim rank --tag level5 -n 1000
./dnd-sim rank --tag level7 -n 500
```

**List all builds (optionally filtered):**
```bash
./dnd-sim list
./dnd-sim list --tag level5
./dnd-sim list --tag warlock
```

**DPS analysis against static AC targets:**
```bash
./dnd-sim dps --tag level5 --ac 14,16,18
```

**Head-to-head between specific builds:**
```bash
./dnd-sim compare --builds berserker_greatsword_orc_5,vengeance_paladin_orc_5,moon_druid_human_5
```

---

## Sample Findings

### Level 5 Grand Rankings (36 builds, n=1000 per matchup)

The definitive 1v1 tier list at level 5 across all implemented classes:

```
Rank  Build                                  Win%   HP   AC
------------------------------------------------------------
  1.  Berserker Greatsword Fire Goliath       87.3%  55   15
  2.  Berserker S&B Longsword Fire Goliath    86.6%  55   17
  3.  Berserker Greatsword Orc                79.5%  55   15
  4.  Berserker S&B Longsword Orc             79.1%  55   17
  5.  Battle Master S&B Stone Goliath         78.2%  49   18
  6.  Battle Master GWF Stone Goliath         78.0%  49   16
  7.  Battle Master Dueling Orc               77.5%  49   18
  8.  Battle Master S&B Fire Goliath          74.6%  49   18
 ...
 14.  Vengeance Paladin Orc                   60.0%  44   18
 16.  Open Hand Monk Orc                      58.8%  38   17
 26.  Fiend Warlock Orc                       27.8%  48   14
 27.  War Cleric Human                        25.4%  48   18
 36.  Lore Bard Human                          2.8%  38   13
```

**Key findings:**
- **Berserker + Fire Goliath is unkillable.** Frenzy extra attack + Fire ancestry damage + 55 HP at AC 15 produces the highest sustained DPS in the game. The S&B variant is 0.7% behind — extra AC compensates for lower damage almost exactly.
- **Martials completely dominate casters 1v1.** The best caster (War Cleric) peaks at 25.4%. Fireball's 8d6 is halved by Rage resistance, and casters at 32 HP can't survive long enough for spells to matter.
- **Monks overperform their stat block.** Open Hand and Shadow both crack the top 20 despite only 38 HP. Stunning Strike (CON save) forces auto-hit follow-ups — it's doing serious work.
- **Lore Bard is last at 2.8%.** Vicious Mockery deals 1d4 damage. Bard is a party support class, and 1v1 shows it.

### Casters vs. Top Martial (Berserker Fire Goliath L5)
| Caster | Win% | Note |
|---|---|---|
| Draconic Sorcerer | 10.7% | Fireball round 1 is the only real shot |
| Evocation Wizard | 9.8% | AC 12 — dies if Berserker wins initiative |
| War Cleric | 1.2% | Spirit Guardians requires melee range setup turn |
| Moon Druid | 0.2% | Call Lightning tickles 55 HP through Rage |

Casters are balanced for party play, not the arena. In groups, Fireball hits clusters, Spirit Guardians punishes positioning, and frontliners absorb pressure. In 1v1, none of that applies.

---

## Architecture

```
sim/
├── __main__.py      # CLI entry point (show, fight, rank, compare, dps, list)
├── models.py        # Core data models: Character, Weapon, Condition, Resource
├── loader.py        # YAML → Character deserialization
├── combat.py        # Turn engine, initiative, attack resolution, condition handling
├── actions.py       # Action/bonus action logic per class and subclass
├── spells.py        # Spell catalog and effect resolution
├── effects.py       # Ongoing effect tracking (concentration, conditions, per-turn damage)
├── tactics.py       # Decision logic (when to cast, when to melee, target selection)
├── runner.py        # Simulation harness, result aggregation
├── dice.py          # Dice rolling utilities
└── dps.py           # Static DPS analysis (no opponent, pure damage output)

data/
├── builds/          # Character YAML files (one per build)
├── classes/         # Class feature definitions (proficiencies, progression)
├── spells/          # Spell YAML definitions
└── armor/           # Armor registry

docs/
└── character_creation.md   # Build design guidelines (stats, armor, feat choices)
```

---

## What's Not Yet Implemented

This is an active project. Known gaps:

- **Party vs. party combat** — current engine is strict 1v1
- **Opportunity attacks** — no reactions on movement out of reach
- **Death saving throws** — characters drop at 0 HP, no stabilization mechanic
- **Ranged kiting logic** — ranged builds can't disengage and maintain distance; archery rankings are artificially low
- **More species** — Gnome, Tiefling, Dragonborn, Half-Elf pending
- **Feat interactions** — Great Weapon Master, Sharpshooter, Polearm Master not yet modeled
- **Multi-classing** — not supported
- **Area-of-effect for parties** — Fireball, Cone of Cold, etc. only target one opponent in 1v1 mode

---

## Contributing

Builds are just YAML files. Add one, tag it, and it's immediately rankable:

```yaml
name: My Custom Build
class: fighter
subclass: battle_master
level: 5
tags: [level5, fighter, custom]
# ... stats, weapons, features
```

Check `docs/character_creation.md` for stat allocation guidelines, armor rules, and build conventions.
