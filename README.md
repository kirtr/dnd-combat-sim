# D&D 2024 Combat Simulator

Monte Carlo combat simulator for comparing character builds under the 2024 Player's Handbook rules.

## Goals

- Data-driven: builds, powers, species, and backgrounds defined in YAML
- Pluggable decision engines: priority scripts now, smarter AI later
- 1v1 first, party vs party later
- Statistical output: DPR, TTK, win rates, survival curves

## Phase 1: Martial Foundations (Levels 1-2)

**Classes:** Fighter, Barbarian, Monk, Rogue  
**Species:** Human, Orc, Elf, Goliath, Dragonborn, Halfling  
**Builds:** 6 pre-built level 2 characters  

### Combat Model
- Combatants start 60ft apart
- Round 1: ranged attack (if available) then close to melee
- Subsequent rounds: melee combat
- Movement: 30ft base speed, Dash for double
- Fight until one drops to 0 HP (no death saves in v1)
- No opportunity attacks in v1

### Key 2024 PHB Rules Implemented
- **Weapon Mastery** (Graze, Vex, Sap, Slow, Topple, Push, Nick, Cleave)
- **Great Weapon Fighting** (2024): treat 1s/2s as 3s (not reroll)
- **Savage Attacker**: roll weapon damage dice twice, take best
- **Second Wind** (2024): 2 uses/long rest at levels 1-3
- **Rage**: resistance to B/P/S, +2 melee damage, advantage on STR
- **Reckless Attack**: advantage on STR attacks, enemies get advantage
- **Martial Arts**: DEX for monk weapons, 1d6 unarmed, bonus unarmed strike
- **Flurry of Blows**: 2 unarmed strikes for 1 Focus Point
- **Sneak Attack**: 1d6 extra with finesse/ranged when advantage (1v1)
- **Cunning Action**: Hide as bonus action for Sneak Attack advantage

## Project Structure

```
dnd-combat-sim/
├── sim/                    # Python package
│   ├── __init__.py
│   ├── __main__.py         # CLI entry point
│   ├── models.py           # Core data models (Character, Weapon, etc.)
│   ├── combat.py           # Combat loop, turn phases, death
│   ├── effects.py          # Effect stack, conditions, durations
│   ├── dice.py             # Dice rolling, expressions, GWF/SA
│   ├── actions.py          # Action resolution (attack, dodge, dash)
│   ├── loader.py           # YAML → model hydration
│   ├── runner.py           # Monte Carlo runner, stats collection
│   └── tactics.py          # Pluggable decision engine (ABC)
├── data/
│   ├── armor/armor.yaml
│   ├── weapons/weapons.yaml
│   ├── powers/
│   │   ├── common.yaml     # Dodge, Dash, Help, Grapple, Shove
│   │   ├── fighting.yaml   # All 2024 fighting style feats
│   │   └── class_features.yaml
│   ├── species/species.yaml
│   ├── backgrounds/backgrounds.yaml
│   ├── classes/
│   │   ├── fighter.yaml
│   │   ├── barbarian.yaml
│   │   ├── monk.yaml
│   │   └── rogue.yaml
│   ├── builds/             # Pre-built level 2 characters
│   │   ├── fighter_gwf_greatsword_2.yaml
│   │   ├── fighter_dueling_longsword_2.yaml
│   │   ├── fighter_archery_longbow_2.yaml
│   │   ├── barbarian_greatsword_2.yaml
│   │   ├── monk_2.yaml
│   │   └── rogue_rapier_2.yaml
│   └── reference/          # PHB rule notes
├── tactics/
│   └── priority/
│       ├── aggressive.yaml
│       └── defensive.yaml
├── tests/
│   ├── test_dice.py
│   ├── test_actions.py
│   ├── test_combat.py
│   └── test_loader.py
├── pyproject.toml
└── README.md
```

## Usage

```bash
# Install dependencies
pip install pyyaml pytest

# Run 10,000 1v1 combats
python -m sim.runner \
  --build1 data/builds/fighter_gwf_greatsword_2.yaml \
  --build2 data/builds/barbarian_greatsword_2.yaml \
  -n 10000

# Verbose mode (shows first combat log)
python -m sim.runner \
  --build1 data/builds/monk_2.yaml \
  --build2 data/builds/rogue_rapier_2.yaml \
  -n 10000 -v

# Run tests
python -m pytest tests/ -v
```

## Sample Output

```
================================================================
  D&D 2024 Combat Simulator — 10,000 simulations
================================================================

                         A: Fighter (GWF Greatsword)  B: Barbarian (Greatsword)
  Class                              fighter            barbarian
  HP                                      20                   25
  AC                                      16                   15
  Wins                                 1,561                8,439
  Win Rate                             15.6%                84.4%
  Avg DPR                               4.45                 5.82
  Avg HP on Win                          7.4                 12.5

  Draws: 0
  Avg Rounds per Combat: 3.2
  Avg Turns to Kill: 3.2
================================================================
```

## Architecture

### Tactics Engine (Pluggable)
The `TacticsEngine` ABC defines the interface for combat decision-making:
```python
class TacticsEngine(abc.ABC):
    @abc.abstractmethod
    def decide_turn(self, char: Character, state: CombatState) -> list[TurnAction]:
        ...
```
The default `PriorityTactics` uses priority lists ("aggressive", "defensive"). Future engines can implement ML-based or tree-search strategies.

### Data-Driven
All game data is in YAML files. Character builds reference weapons, armor, species, backgrounds, and class features by name. The loader resolves everything into hydrated `Character` objects.

## Future Work (Phase 2+)
- [ ] Levels 3-5 (subclasses, Extra Attack)
- [ ] Opportunity attacks
- [ ] Death saves
- [ ] Multi-combatant fights (party vs party)
- [ ] Spellcaster classes
- [ ] More weapon mastery effects (Nick, Cleave)
- [ ] Survival curves and per-round statistics
