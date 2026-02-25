"""Effect stack and condition management."""

from __future__ import annotations
from .models import Character, Condition, ActiveEffect, DamageType


def apply_rage(char: Character) -> None:
    """Enter rage — add condition and effect."""
    char.conditions.add(Condition.RAGING)
    char.active_effects.append(ActiveEffect(
        name="Rage",
        source="rage",
        duration=10,
        damage_resistance=[DamageType.BLUDGEONING, DamageType.PIERCING, DamageType.SLASHING],
        rage_damage_bonus=2,
    ))


def apply_reckless_attack(char: Character) -> None:
    """Use Reckless Attack — advantage on attacks, enemies get advantage too."""
    char.active_effects.append(ActiveEffect(
        name="Reckless (advantage)",
        source="reckless_attack",
        end_trigger="start_of_turn",
        advantage_on_attacks=True,
    ))
    char.active_effects.append(ActiveEffect(
        name="Reckless (vulnerability)",
        source="reckless_attack_vuln",
        end_trigger="start_of_turn",
        grants_advantage_to_enemies=True,
    ))
