"""Action resolution: attack rolls, damage, class features."""

from __future__ import annotations
from .models import Character, Weapon, CombatState, DamageType, ActiveEffect, Condition
from .dice import d20, eval_dice, eval_dice_twice_take_best


def resolve_attack(
    attacker: Character,
    defender: Character,
    weapon: Weapon,
    state: CombatState,
    *,
    is_thrown: bool = False,
    is_unarmed: bool = False,
) -> None:
    """Resolve a single attack, apply damage, and log the result."""
    # Determine advantage / disadvantage
    adv = _has_advantage(attacker, defender)
    disadv = _has_disadvantage(attacker, defender)

    # Attack bonus
    if is_unarmed:
        attack_bonus = attacker.unarmed_attack_mod()
    else:
        attack_bonus = attacker.attack_modifier(weapon)

    roll_result = d20(advantage=adv, disadvantage=disadv)
    is_crit = roll_result == 20
    total = roll_result + attack_bonus

    if roll_result == 1:
        # Auto-miss, but check Graze mastery
        graze = _try_graze(attacker, weapon, defender, state)
        if not graze:
            state.log(f"  {attacker.name} attacks with {weapon.name}: MISS (nat 1)")
        return

    if is_crit or total >= defender.effective_ac:
        # HIT
        damage = _calc_damage(attacker, weapon, is_crit, is_unarmed, is_thrown)

        # Sneak Attack
        sa_dmg = _try_sneak_attack(attacker, is_crit, adv and not disadv)
        damage += sa_dmg

        actual = defender.take_damage(damage, weapon.damage_type)

        # Vex: grant advantage on next attack vs this target
        if not is_unarmed and _can_use_mastery(attacker, weapon, "vex"):
            attacker.vex_target = defender.name

        crit_str = " CRIT!" if is_crit else ""
        sa_str = f" (+SA {sa_dmg})" if sa_dmg else ""
        state.log(
            f"  {attacker.name} attacks with {weapon.name}:{crit_str} HIT"
            f" ({total} vs AC {defender.effective_ac}) for {actual} damage{sa_str}"
            f" ({defender.current_hp}/{defender.max_hp} HP)"
        )
    else:
        # MISS — check Graze mastery
        graze = _try_graze(attacker, weapon, defender, state)
        if not graze:
            state.log(
                f"  {attacker.name} attacks with {weapon.name}:"
                f" MISS ({total} vs AC {defender.effective_ac})"
            )


# ---------------------------------------------------------------------------
# Damage calculation
# ---------------------------------------------------------------------------

def _calc_damage(
    attacker: Character, weapon: Weapon,
    crit: bool, is_unarmed: bool, is_thrown: bool,
) -> int:
    """Calculate total damage for a hit."""
    dice_expr = weapon.damage_dice
    if is_unarmed:
        dice_expr = attacker.martial_arts_die or "1"

    # GWF: treat 1s and 2s as 3s on damage dice
    gwf_min = None
    if (attacker.fighting_style == "great_weapon_fighting"
            and weapon.is_two_handed and not is_unarmed):
        gwf_min = 3  # 2024 GWF: treat 1-2 as 3

    # Savage Attacker: roll dice twice, take best
    if attacker.has_savage_attacker and not getattr(attacker, "_savage_used_this_turn", False):
        base_result = eval_dice_twice_take_best(dice_expr, minimum=gwf_min)
        attacker._savage_used_this_turn = True  # type: ignore[attr-defined]
    else:
        base_result = eval_dice(dice_expr, minimum=gwf_min)

    damage = base_result.total

    # Crit: roll damage dice again
    if crit:
        crit_result = eval_dice(dice_expr, minimum=gwf_min)
        damage += crit_result.total

    # Flat modifier
    if is_unarmed:
        damage += attacker.unarmed_damage_mod()
        if attacker.is_raging:
            damage += attacker.rage_damage
    else:
        damage += attacker.damage_modifier(weapon, is_thrown=is_thrown)

    return max(1, damage)


# ---------------------------------------------------------------------------
# Sneak Attack
# ---------------------------------------------------------------------------

def _try_sneak_attack(attacker: Character, is_crit: bool, had_advantage: bool) -> int:
    """Returns extra SA damage if applicable, else 0."""
    if not attacker.sneak_attack_dice:
        return 0
    if attacker.sneak_attack_used:
        return 0
    if not had_advantage:
        return 0  # 1v1: need advantage

    extra = eval_dice(attacker.sneak_attack_dice).total
    if is_crit:
        extra += eval_dice(attacker.sneak_attack_dice).total
    attacker.sneak_attack_used = True
    return extra


# ---------------------------------------------------------------------------
# Weapon Mastery helpers
# ---------------------------------------------------------------------------

def _can_use_mastery(attacker: Character, weapon: Weapon, mastery_name: str) -> bool:
    if weapon.mastery and weapon.mastery.value == mastery_name:
        return attacker.can_use_mastery(weapon)
    return False


def _try_graze(
    attacker: Character, weapon: Weapon,
    defender: Character, state: CombatState,
) -> bool:
    """Apply Graze mastery on a miss. Returns True if graze damage applied."""
    if not _can_use_mastery(attacker, weapon, "graze"):
        return False
    graze_dmg = max(0, attacker.damage_modifier(weapon))
    if graze_dmg > 0:
        actual = defender.take_damage(graze_dmg, weapon.damage_type)
        state.log(
            f"  {attacker.name} attacks with {weapon.name}: GRAZE for {actual} damage"
            f" ({defender.current_hp}/{defender.max_hp} HP)"
        )
        return True
    return False


# ---------------------------------------------------------------------------
# Advantage / Disadvantage
# ---------------------------------------------------------------------------

def _has_advantage(attacker: Character, defender: Character) -> bool:
    """Check all sources of advantage."""
    if any(e.advantage_on_attacks for e in attacker.active_effects):
        return True
    if attacker.vex_target == defender.name:
        return True
    # Reckless on defender grants us advantage
    if any(e.grants_advantage_to_enemies for e in defender.active_effects):
        return True
    return False


def _has_disadvantage(attacker: Character, defender: Character) -> bool:
    """Check all sources of disadvantage."""
    return defender.is_dodging


# ---------------------------------------------------------------------------
# Utility actions used by combat.py
# ---------------------------------------------------------------------------

def do_second_wind(char: Character, state: CombatState) -> None:
    """Use Second Wind as a bonus action."""
    res = char.resources.get("second_wind")
    if not res or not res.available or char.bonus_action_used:
        return
    res.spend()
    char.bonus_action_used = True
    healing = eval_dice("1d10").total + char.level
    actual = char.heal(healing)
    state.log(f"  {char.name} uses Second Wind, heals {actual} HP ({char.current_hp}/{char.max_hp})")


def do_dodge(char: Character, state: CombatState) -> None:
    """Take the Dodge action (or as part of Patient Defense)."""
    char.conditions.add(Condition.DODGING)
    state.log(f"  {char.name} takes the Dodge action")


def do_dash(char: Character, state: CombatState) -> None:
    """Take the Dash action."""
    char.movement_remaining += char.speed
    state.log(f"  {char.name} dashes (movement: {char.movement_remaining} ft)")
