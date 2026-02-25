"""Effect stack, conditions, and duration tracking."""

from __future__ import annotations

from sim.models import ActiveEffect, Character, Condition, DamageType


def apply_rage(char: Character) -> None:
    """Enter Rage -- 2024 PHB Barbarian Level 1."""
    char.conditions.add(Condition.RAGING)
    char.active_effects.append(ActiveEffect(
        name="Rage",
        source="barbarian",
        duration=100,  # effectively permanent for a fight
        damage_resistance=[DamageType.BLUDGEONING, DamageType.PIERCING, DamageType.SLASHING],
        rage_damage_bonus=2,  # +2 at levels 1-8
    ))


def apply_reckless_attack(char: Character) -> None:
    """Reckless Attack -- advantage on STR melee attacks, enemies have advantage."""
    char.active_effects.append(ActiveEffect(
        name="Reckless Attack",
        source="barbarian",
        end_trigger="start_of_turn",
        advantage_on_attacks=True,
        grants_advantage_to_enemies=True,
    ))


def apply_dodge(char: Character) -> None:
    """Dodge action -- attacks against you have disadvantage."""
    char.conditions.add(Condition.DODGING)


def apply_defense_style(char: Character) -> None:
    """Defense fighting style -- +1 AC while wearing armor."""
    char.active_effects.append(ActiveEffect(
        name="Defense",
        source="fighting_style",
        ac_bonus=1,
    ))


def has_advantage_on_attack(attacker: Character, defender: Character, weapon=None) -> bool:
    """Determine if attacker has advantage on an attack roll."""
    adv = False
    # Reckless Attack or other effects granting advantage
    for e in attacker.active_effects:
        if e.advantage_on_attacks:
            adv = True
            break
    # Vex mastery
    if attacker.vex_target and defender.name == attacker.vex_target:
        adv = True
        attacker.vex_target = None  # consumed
    return adv


def has_disadvantage_on_attack(attacker: Character, defender: Character) -> bool:
    """Determine if attacker has disadvantage on an attack roll."""
    # Defender is dodging
    if defender.is_dodging:
        return True
    # Sap effect on attacker
    for e in attacker.active_effects:
        if e.disadvantage_on_attacks:
            return True
    return False


def enemy_has_advantage(defender: Character) -> bool:
    """Check if enemies have advantage against defender (e.g. Reckless Attack)."""
    for e in defender.active_effects:
        if e.grants_advantage_to_enemies:
            return True
    return False
