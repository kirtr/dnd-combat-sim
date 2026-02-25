"""YAML loader — hydrates Character objects from build + data files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from sim.models import (
    AbilityScores,
    Character,
    DamageType,
    MasteryProperty,
    Resource,
    Weapon,
    WeaponProperty,
)

# Resolve project root relative to this file
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"


def _load_yaml(path: str | Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# Cache loaded data files
_cache: dict[str, dict] = {}


def _get_data(filename: str) -> dict:
    if filename not in _cache:
        # Try data/<filename> first, then data/<subdir>/<filename>
        candidates = [
            _DATA_DIR / filename,
            _DATA_DIR / "weapons" / filename,
            _DATA_DIR / "armor" / filename,
            _DATA_DIR / "species" / filename,
            _DATA_DIR / "backgrounds" / filename,
            _DATA_DIR / "powers" / filename,
            _DATA_DIR / "classes" / filename,
        ]
        for p in candidates:
            if p.exists():
                _cache[filename] = _load_yaml(p)
                break
        else:
            raise FileNotFoundError(f"Data file {filename} not found in {_DATA_DIR}")
    return _cache[filename]


def _parse_weapon_property(prop: str) -> WeaponProperty | None:
    mapping = {
        "finesse": WeaponProperty.FINESSE,
        "heavy": WeaponProperty.HEAVY,
        "light": WeaponProperty.LIGHT,
        "reach": WeaponProperty.REACH,
        "two_handed": WeaponProperty.TWO_HANDED,
        "versatile": WeaponProperty.VERSATILE,
        "thrown": WeaponProperty.THROWN,
        "ammunition": WeaponProperty.AMMUNITION,
        "loading": WeaponProperty.LOADING,
    }
    return mapping.get(prop.lower())


def _parse_mastery(m: str) -> MasteryProperty | None:
    mapping = {
        "nick": MasteryProperty.NICK,
        "topple": MasteryProperty.TOPPLE,
        "graze": MasteryProperty.GRAZE,
        "push": MasteryProperty.PUSH,
        "sap": MasteryProperty.SAP,
        "slow": MasteryProperty.SLOW,
        "cleave": MasteryProperty.CLEAVE,
        "vex": MasteryProperty.VEX,
    }
    return mapping.get(m.lower())


def _parse_damage_type(dt: str) -> DamageType:
    return DamageType[dt.upper()]


def load_weapon(name: str) -> Weapon:
    """Load a weapon definition from weapons.yaml."""
    weapons = _get_data("weapons.yaml")
    key = name.lower().replace(" ", "_")
    if key not in weapons:
        raise ValueError(f"Unknown weapon: {name}")
    w = weapons[key]

    props = [_parse_weapon_property(p) for p in w.get("properties", [])]
    props = [p for p in props if p is not None]

    mastery = _parse_mastery(w.get("mastery", "")) if w.get("mastery") else None

    # Determine range
    range_normal = w.get("range", 5)
    range_long = w.get("long_range")
    thrown_normal = None
    thrown_long = None
    thrown_range = w.get("thrown_range")
    if thrown_range:
        thrown_normal = thrown_range[0]
        thrown_long = thrown_range[1]

    return Weapon(
        name=w["name"],
        damage_dice=w["damage"],
        damage_type=_parse_damage_type(w["damage_type"]),
        properties=props,
        mastery=mastery,
        category=w.get("category", "simple"),
        versatile_damage=w.get("versatile_damage"),
        range_normal=range_normal,
        range_long=range_long,
        thrown_range_normal=thrown_normal,
        thrown_range_long=thrown_long,
    )


def load_build(path: str | Path) -> Character:
    """Load a character build from a YAML file, resolving class/species/etc."""
    build = _load_yaml(path)

    # Ability scores
    scores_raw = build.get("ability_scores", {})
    ability_scores = AbilityScores(
        strength=scores_raw.get("str", 10),
        dexterity=scores_raw.get("dex", 10),
        constitution=scores_raw.get("con", 10),
        intelligence=scores_raw.get("int", 10),
        wisdom=scores_raw.get("wis", 10),
        charisma=scores_raw.get("cha", 10),
    )

    class_name = build.get("class", "fighter")
    level = build.get("level", 1)
    prof_bonus = 2 if level < 5 else 3  # simplified

    # Load class data
    class_data = _get_data(f"{class_name}.yaml") if class_name else {}
    hit_die_str = class_data.get("hit_die", "d10")
    hp_base = class_data.get("hp_base", 10)

    # Calculate HP: base + CON mod at level 1, then average roll + CON for each level after
    con_mod = ability_scores.modifier("constitution")
    avg_per_level = {
        "d6": 4, "d8": 5, "d10": 6, "d12": 7,
    }
    avg = avg_per_level.get(hit_die_str, 6)
    max_hp = hp_base + con_mod  # level 1
    for _ in range(1, level):
        max_hp += avg + con_mod

    # Weapons
    weapons = []
    for wname in build.get("weapons", []):
        weapons.append(load_weapon(wname))

    # AC calculation
    ac = _calculate_ac(build, ability_scores, class_name, class_data)

    # Speed
    speed = 30
    # Species speed
    species_name = build.get("species", "human")
    species_data_all = _get_data("species.yaml")
    species_data = species_data_all.get(species_name, {})
    speed = species_data.get("speed", 30)

    # Monk unarmored movement
    if class_name == "monk" and level >= 2:
        if build.get("armor", "unarmored") == "unarmored":
            speed += 10

    # Features
    features = list(build.get("powers", []))

    # Merge class features for this level
    class_features_by_level = class_data.get("features", {})
    for lv in range(1, level + 1):
        for feat in class_features_by_level.get(lv, []):
            if feat not in features:
                features.append(feat)

    # Fighting style
    fighting_style = build.get("fighting_style")

    # Weapon mastery
    wm_slots = class_data.get("weapon_mastery_slots", 0)
    # By default, master all weapons the character has
    weapon_masteries = [w.name for w in weapons]

    # Resources
    resources = {}
    if "second_wind" in features:
        # 2024: uses = 2 at level 1-2 (Fighter Features table)
        resources["second_wind"] = Resource("Second Wind", 2, 2, "long_rest")
    if "action_surge" in features:
        resources["action_surge"] = Resource("Action Surge", 1, 1, "short_rest")
    if "rage" in features:
        # 2 rages at level 1-2
        resources["rage"] = Resource("Rage", 2, 2, "long_rest")
    if "flurry_of_blows" in features or "patient_defense" in features or "step_of_the_wind" in features:
        # Focus Points = monk level
        resources["focus_points"] = Resource("Focus Points", level, level, "short_rest")

    # Species traits
    species_traits = species_data.get("traits", {})

    # Relentless Endurance (Orc)
    if "relentless_endurance" in species_traits:
        resources["relentless_endurance"] = Resource("Relentless Endurance", 1, 1, "long_rest")

    # Adrenaline Rush (Orc)
    if "adrenaline_rush" in species_traits:
        resources["adrenaline_rush"] = Resource("Adrenaline Rush", prof_bonus, prof_bonus, "short_rest")

    # Stone's Endurance (Goliath)
    if "stones_endurance" in species_traits:
        resources["stones_endurance"] = Resource("Stone's Endurance", prof_bonus, prof_bonus, "long_rest")

    # Origin feat
    origin_feat = build.get("origin_feat", "")
    has_savage_attacker = origin_feat == "savage_attacker"

    # Initiative bonus
    init_bonus = 0
    if origin_feat == "alert":
        init_bonus = prof_bonus

    # Sneak attack
    sneak_attack_dice = None
    if "sneak_attack" in features:
        # 1d6 at levels 1-2
        sneak_attack_dice = "1d6"

    # Martial Arts
    martial_arts_die = None
    if "martial_arts" in features:
        martial_arts_die = "1d6"  # levels 1-4

    # Shield check — add to features for _has_shield check
    if build.get("shield", False):
        features.append("shield")

    char = Character(
        name=build.get("name", "Unknown"),
        level=level,
        class_name=class_name,
        ability_scores=ability_scores,
        max_hp=max_hp,
        ac=ac,
        proficiency_bonus=prof_bonus,
        speed=speed,
        weapons=weapons,
        resources=resources,
        features=features,
        initiative_bonus=init_bonus,
        extra_attacks=0,  # no extra attack at level 2
        fighting_style=fighting_style,
        weapon_mastery_slots=wm_slots,
        weapon_masteries=weapon_masteries,
        has_savage_attacker=has_savage_attacker,
        sneak_attack_dice=sneak_attack_dice,
        martial_arts_die=martial_arts_die,
        species_traits=species_traits,
    )
    return char


def _calculate_ac(
    build: dict, scores: AbilityScores, class_name: str, class_data: dict,
) -> int:
    """Calculate AC from build data."""
    armor_name = build.get("armor", "unarmored")
    has_shield = build.get("shield", False)

    dex_mod = scores.modifier("dexterity")
    con_mod = scores.modifier("constitution")
    wis_mod = scores.modifier("wisdom")

    # Unarmored Defense
    if armor_name == "unarmored":
        if class_name == "barbarian":
            ac = 10 + dex_mod + con_mod
        elif class_name == "monk":
            ac = 10 + dex_mod + wis_mod
        else:
            ac = 10 + dex_mod
    else:
        armor_data = _get_data("armor.yaml")
        armor = armor_data.get(armor_name, {})
        base_ac = armor.get("base_ac", 10)
        dex_cap = armor.get("dex_cap")
        if dex_cap is not None and dex_cap == 0:
            ac = base_ac  # heavy armor
        elif dex_cap is not None:
            ac = base_ac + min(dex_mod, dex_cap)
        else:
            ac = base_ac + dex_mod

    if has_shield:
        ac += 2

    # Defense fighting style
    if build.get("fighting_style") == "defense" and armor_name != "unarmored":
        ac += 1

    return ac


def load_build_by_name(name: str) -> Character:
    """Load a build by filename (e.g. 'fighter_gwf_greatsword_2')."""
    path = _DATA_DIR / "builds" / name
    if not str(path).endswith(".yaml"):
        path = _DATA_DIR / "builds" / f"{name}.yaml"
    return load_build(path)
