# D&D 2024 Combat Simulator

Monte Carlo combat simulator for comparing character builds under the 2024 Player's Handbook rules.

## Goals

- Data-driven: builds, powers, species, and backgrounds defined in YAML
- Pluggable decision engines: priority scripts now, smarter AI later
- 1v1 first, party vs party later
- Statistical output: DPR, TTK, win rates, survival curves

## Phase 1: Martial Foundations (Levels 1-2)

- Fighter (control) — all subclass-agnostic features
- Barbarian, Monk, Rogue — core martial classes
- Species + Background (2024 origins) as composable trait layers
- 1v1 Monte Carlo runner with basic stats

## Project Structure

```
dnd-combat-sim/
├── sim/                    # Python package
│   ├── __init__.py
│   ├── models.py           # Core data models (Character, Weapon, etc.)
│   ├── combat.py           # Combat loop, turn phases, death
│   ├── effects.py          # Effect stack, conditions, durations
│   ├── dice.py             # Dice rolling, expressions
│   ├── actions.py          # Action resolution (attack, dodge, dash, etc.)
│   ├── loader.py           # YAML → model hydration
│   └── runner.py           # Monte Carlo runner, stats collection
├── data/
│   ├── powers/
│   │   ├── common.yaml     # Dodge, Dash, Help, Grapple, Shove
│   │   └── fighting.yaml   # Fighting styles, Extra Attack, etc.
│   ├── species/
│   │   └── species.yaml
│   ├── backgrounds/
│   │   └── backgrounds.yaml
│   ├── classes/
│   │   ├── fighter.yaml
│   │   ├── barbarian.yaml
│   │   ├── monk.yaml
│   │   └── rogue.yaml
│   └── builds/
│       ├── fighter_gwf_greatsword_2.yaml
│       ├── fighter_dueling_longsword_2.yaml
│       └── ...
├── tactics/
│   └── priority/           # Priority-based decision scripts
│       ├── aggressive.yaml
│       └── defensive.yaml
├── tests/
├── pyproject.toml
└── README.md
```

## Usage

```bash
# Run 10,000 1v1 combats between two builds
python -m sim.runner --build1 builds/fighter_gwf_2.yaml --build2 builds/barbarian_berserker_2.yaml -n 10000
```
