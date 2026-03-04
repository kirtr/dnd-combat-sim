"""Spell registry and spell metadata loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from sim.models import DamageType


@dataclass
class SpellData:
    name: str
    level: int
    school: str
    damage_dice: str
    damage_type: Optional[DamageType]
    attack_type: str
    save_ability: str
    half_on_save: bool
    concentration: bool
    cantrip_scaling: bool
    extra_attacks: int
    upcast_dice: str = ""
    missing_hp_dice: str = ""
    aura: bool = False
    aura_range: int = 0
    bonus_action: bool = False
    grants_advantage: bool = False
    description: str = ""
    # New fields (L4-L9 spell effects) — all default to safe values for backward compat
    effect: str = ""                     # "paralyze", "stun", "banishment", "polymorph",
                                         # "extra_turns", "stun_no_save", "disintegrate",
                                         # "harm", "pain", "greater_invisibility", "wish"
    instant_kill_threshold: int = 0      # Power Word Kill: kill if target HP <= this
    hp_percentage_cap: float = 0.0       # Harm: reduce to this fraction of max HP on fail
    polymorph_cr: int = -1               # Polymorph target CR (-1 = disabled)
    replicate_slot: int = 0              # Wish: cast as slot of this level
    instant_kill_on_zero: bool = False   # Disintegrate: no stabilize at 0


def load_spell_registry(data_dir: Path) -> dict[str, SpellData]:
    """Load all spell YAMLs from data_dir/spells/."""
    spells_path = data_dir / "spells"
    registry: dict[str, SpellData] = {}
    if not spells_path.exists():
        return registry

    for spell_file in spells_path.glob("*.yaml"):
        raw = yaml.safe_load(spell_file.read_text()) or {}
        dt_str = raw.get("damage_type", "")
        try:
            damage_type = DamageType[dt_str.upper()] if dt_str else None
        except KeyError:
            damage_type = None

        spell = SpellData(
            name=raw["name"],
            level=raw.get("level", 0),
            school=raw.get("school", ""),
            damage_dice=raw.get("damage_dice", ""),
            damage_type=damage_type,
            attack_type=raw.get("attack_type", "none"),
            save_ability=raw.get("save_ability", ""),
            half_on_save=raw.get("half_on_save", False),
            concentration=raw.get("concentration", False),
            cantrip_scaling=raw.get("cantrip_scaling", False),
            extra_attacks=raw.get("extra_attacks", 1),
            upcast_dice=raw.get("upcast_dice", ""),
            missing_hp_dice=raw.get("missing_hp_dice", ""),
            aura=raw.get("aura", False),
            aura_range=raw.get("aura_range", 0),
            bonus_action=raw.get("bonus_action", False),
            grants_advantage=raw.get("grants_advantage", False),
            description=raw.get("description", ""),
            # New effect fields
            effect=raw.get("effect") or "",        # null → ""
            instant_kill_threshold=raw.get("instant_kill_threshold", 0),
            hp_percentage_cap=float(raw.get("hp_percentage_cap", 0.0)),
            polymorph_cr=raw.get("polymorph_cr", -1),
            replicate_slot=raw.get("replicate_slot", 0),
            instant_kill_on_zero=raw.get("instant_kill_on_zero", False),
        )
        registry[spell.name] = spell

    return registry


def get_spell(name: str) -> Optional[SpellData]:
    return SPELL_REGISTRY.get(name)


def cantrip_die_count(spell: SpellData, caster_level: int) -> int:
    """Return the number of dice for a cantrip based on caster level."""
    if caster_level >= 17:
        return 4
    if caster_level >= 11:
        return 3
    if caster_level >= 5:
        return 2
    return 1


DATA_DIR = Path(__file__).parent.parent / "data"
SPELL_REGISTRY = load_spell_registry(DATA_DIR)
