"""Action resolution: attack rolls, damage, class features."""

from __future__ import annotations

from dataclasses import dataclass

from sim.models import (
    Character,
    Weapon,
    CombatState,
    DamageType,
    ActiveEffect,
    Condition,
    MasteryProperty,
)
from sim.dice import d20, eval_dice, eval_dice_twice_take_best


@dataclass
class AttackResult:
    hit: bool
    critical: bool
    damage: int
    damage_type: DamageType
    attack_roll: int
    target_ac: int


def resolve_attack(
    attacker: Character,
    defender: Character,
    weapon: Weapon,
    state: CombatState,
    *,
    is_thrown: bool = False,
    is_unarmed: bool = False,
    is_nick_attack: bool = False,
) -> AttackResult:
    """Resolve a single attack, apply damage, log, and return result."""
    # Determine advantage / disadvantage
    adv = _has_advantage(attacker, defender)
    disadv = _has_disadvantage(attacker, defender)

    # Attack bonus
    if is_unarmed:
        attack_bonus = attacker.unarmed_attack_mod()
    else:
        attack_bonus = attacker.attack_modifier(weapon)

    roll_result = d20(advantage=adv, disadvantage=disadv)

    # Halfling Luck: reroll natural 1s on d20 attack rolls
    if roll_result == 1 and "luck" in attacker.species_traits:
        reroll = d20()
        state.log(f"  Halfling Luck: rerolled nat 1 -> {reroll}")
        roll_result = reroll  # must use new roll

    is_crit = roll_result == 20
    total = roll_result + attack_bonus
    target_ac = defender.effective_ac

    # Natural 1 auto-miss (but check Graze)
    if roll_result == 1:
        graze_dmg = _try_graze(attacker, weapon, defender, state)
        if graze_dmg == 0:
            state.log(f"  {attacker.name} attacks with {weapon.name}: MISS (nat 1)")
        return AttackResult(
            hit=False, critical=False, damage=graze_dmg,
            damage_type=weapon.damage_type, attack_roll=total, target_ac=target_ac,
        )

    if is_crit or total >= target_ac:
        # HIT — build damage packet with all components
        damage = _calc_damage(attacker, weapon, is_crit, is_unarmed, is_thrown, is_nick_attack)

        # Sneak Attack (same damage type as weapon)
        sa_dmg = _try_sneak_attack(attacker, is_crit, adv and not disadv)
        damage += sa_dmg

        # Build damage packet: [(amount, type), ...]
        damage_packet = [(damage, weapon.damage_type)]

        # Goliath Fire Giant ancestry: +1d10 fire damage on hit
        fire_extra = 0
        if attacker.giant_ancestry == "fire":
            fire_res = attacker.resources.get("fire_giant")
            if fire_res and fire_res.available:
                fire_res.spend()
                fire_extra = eval_dice("1d10").total
                damage_packet.append((fire_extra, DamageType.FIRE))

        # Frost's Chill (Frost Giant): +1d6 cold on hit + reduce speed
        frost_extra = 0
        if attacker.giant_ancestry == "frost":
            frost_res = attacker.resources.get("frost_giant")
            if frost_res and frost_res.available:
                frost_res.spend()
                frost_extra = eval_dice("1d6").total
                damage_packet.append((frost_extra, DamageType.COLD))
                defender.speed = max(0, defender.speed - 10)

        # Apply entire damage packet at once (resistance per type, then reduction on total)
        actual = defender.take_attack_damage(damage_packet, state)

        # Log the hit
        extras = []
        if fire_extra:
            extras.append(f"+{fire_extra} fire")
        if frost_extra:
            extras.append(f"+{frost_extra} cold")
        extra_str = f" ({', '.join(extras)})" if extras else ""

        # Weapon Mastery on hit (post-damage effects)
        if not is_unarmed and attacker.can_use_mastery(weapon):
            _apply_mastery_on_hit(attacker, defender, weapon, state)

        # Hill's Tumble (Hill Giant): free Prone on hit vs Large or smaller, no save
        if attacker.giant_ancestry == "hill":
            hill_res = attacker.resources.get("hill_giant")
            if hill_res and hill_res.available:
                hill_res.spend()
                defender.conditions.add(Condition.PRONE)
                state.log(f"  Hill's Tumble: {defender.name} knocked prone!")

        crit_str = " CRIT!" if is_crit else ""
        sa_str = f" (+SA {sa_dmg})" if sa_dmg else ""
        state.log(
            f"  {attacker.name} attacks with {weapon.name}:{crit_str} HIT"
            f" ({total} vs AC {target_ac}) for {actual} damage{sa_str}{extra_str}"
            f" ({defender.current_hp}/{defender.max_hp} HP)"
        )
        return AttackResult(
            hit=True, critical=is_crit, damage=damage,
            damage_type=weapon.damage_type, attack_roll=total, target_ac=target_ac,
        )
    else:
        # Lucky feat: on miss, spend a luck point to reroll
        luck_res = attacker.resources.get("luck_points")
        if luck_res and luck_res.available:
            luck_res.spend()
            luck_roll = d20(advantage=adv, disadvantage=disadv)
            # Halfling Luck on the lucky reroll too
            if luck_roll == 1 and "luck" in attacker.species_traits:
                luck_roll = d20()
            luck_total = luck_roll + attack_bonus
            state.log(f"  Lucky feat: rerolled {total} -> {luck_total}")
            if luck_roll == 20 or luck_total >= target_ac:
                # Now it's a hit! Build damage packet
                is_crit2 = luck_roll == 20
                damage = _calc_damage(attacker, weapon, is_crit2, is_unarmed, is_thrown, is_nick_attack)
                sa_dmg = _try_sneak_attack(attacker, is_crit2, adv and not disadv)
                damage += sa_dmg

                damage_packet = [(damage, weapon.damage_type)]
                extras = []

                if attacker.giant_ancestry == "fire":
                    fire_res = attacker.resources.get("fire_giant")
                    if fire_res and fire_res.available:
                        fire_res.spend()
                        fire_extra = eval_dice("1d10").total
                        damage_packet.append((fire_extra, DamageType.FIRE))
                        extras.append(f"+{fire_extra} fire")

                if attacker.giant_ancestry == "frost":
                    frost_res = attacker.resources.get("frost_giant")
                    if frost_res and frost_res.available:
                        frost_res.spend()
                        frost_extra = eval_dice("1d6").total
                        damage_packet.append((frost_extra, DamageType.COLD))
                        defender.speed = max(0, defender.speed - 10)
                        extras.append(f"+{frost_extra} cold")

                actual = defender.take_attack_damage(damage_packet, state)

                if not is_unarmed and attacker.can_use_mastery(weapon):
                    _apply_mastery_on_hit(attacker, defender, weapon, state)

                if attacker.giant_ancestry == "hill":
                    hill_res = attacker.resources.get("hill_giant")
                    if hill_res and hill_res.available:
                        hill_res.spend()
                        defender.conditions.add(Condition.PRONE)
                        state.log(f"  Hill's Tumble: {defender.name} knocked prone!")

                extra_str = f" ({', '.join(extras)})" if extras else ""
                crit_str = " CRIT!" if is_crit2 else ""
                sa_str = f" (+SA {sa_dmg})" if sa_dmg else ""
                state.log(
                    f"  {attacker.name} attacks with {weapon.name}:{crit_str} HIT (Lucky)"
                    f" ({luck_total} vs AC {target_ac}) for {actual} damage{sa_str}{extra_str}"
                    f" ({defender.current_hp}/{defender.max_hp} HP)"
                )
                return AttackResult(
                    hit=True, critical=is_crit2, damage=damage,
                    damage_type=weapon.damage_type, attack_roll=luck_total, target_ac=target_ac,
                )

        # MISS — check Graze mastery
        graze_dmg = _try_graze(attacker, weapon, defender, state)
        if graze_dmg == 0:
            state.log(
                f"  {attacker.name} attacks with {weapon.name}:"
                f" MISS ({total} vs AC {target_ac})"
            )
        return AttackResult(
            hit=False, critical=False, damage=graze_dmg,
            damage_type=weapon.damage_type, attack_roll=total, target_ac=target_ac,
        )


# ---------------------------------------------------------------------------
# Damage calculation
# ---------------------------------------------------------------------------

def _calc_damage(
    attacker: Character, weapon: Weapon,
    crit: bool, is_unarmed: bool, is_thrown: bool,
    is_nick_attack: bool = False,
) -> int:
    """Calculate total damage for a hit."""
    dice_expr = weapon.damage_dice
    if is_unarmed:
        dice_expr = attacker.martial_arts_die or "1"

    # GWF: treat 1s and 2s as 3s on damage dice (2024 rules)
    gwf_min = None
    if (attacker.fighting_style == "great_weapon_fighting"
            and (weapon.is_two_handed or weapon.is_versatile)
            and weapon.is_melee
            and not is_unarmed):
        gwf_min = 3

    # Savage Attacker: roll dice twice, take best (once per turn)
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
    elif is_nick_attack and attacker.fighting_style != "two_weapon_fighting":
        # Nick extra attack: no ability modifier unless TWF style
        damage += weapon.bonus  # still add magic weapon bonus
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

def _apply_mastery_on_hit(
    attacker: Character, defender: Character,
    weapon: Weapon, state: CombatState,
) -> None:
    """Apply weapon mastery effects after a successful hit."""
    mastery = weapon.mastery
    if mastery is None:
        return

    if mastery == MasteryProperty.VEX:
        attacker.vex_target = defender.name
        state.log(f"  Vex: advantage on next attack vs {defender.name}")

    elif mastery == MasteryProperty.SAP:
        defender.active_effects.append(ActiveEffect(
            name="Sapped",
            source=weapon.name,
            end_trigger="start_of_turn",
            disadvantage_on_attacks=True,
        ))
        state.log(f"  Sap: {defender.name} has disadvantage on next attack")

    elif mastery == MasteryProperty.SLOW:
        state.log(f"  Slow: {defender.name}'s speed reduced by 10 ft")

    elif mastery == MasteryProperty.TOPPLE:
        ability_mod = attacker._attack_ability_mod(weapon)
        dc = 8 + ability_mod + attacker.proficiency_bonus
        save_roll = d20() + defender.con_mod
        if save_roll < dc:
            defender.conditions.add(Condition.PRONE)
            state.log(f"  Topple: {defender.name} falls prone! (save {save_roll} vs DC {dc})")
        else:
            state.log(f"  Topple: {defender.name} resists (save {save_roll} vs DC {dc})")

    elif mastery == MasteryProperty.PUSH:
        state.distance = min(120, state.distance + 10)
        state.log(f"  Push: {defender.name} pushed 10 ft (distance: {state.distance} ft)")


def _try_graze(
    attacker: Character, weapon: Weapon,
    defender: Character, state: CombatState,
) -> int:
    """Apply Graze mastery on a miss. Returns damage dealt (0 if no graze)."""
    if not weapon.mastery or weapon.mastery != MasteryProperty.GRAZE:
        return 0
    if not attacker.can_use_mastery(weapon):
        return 0
    graze_dmg = max(0, attacker._attack_ability_mod(weapon))
    if graze_dmg > 0:
        actual = defender.take_damage(graze_dmg, weapon.damage_type, state)
        state.log(
            f"  {attacker.name} attacks with {weapon.name}: GRAZE for {actual} damage"
            f" ({defender.current_hp}/{defender.max_hp} HP)"
        )
        return actual
    return 0


# ---------------------------------------------------------------------------
# Advantage / Disadvantage
# ---------------------------------------------------------------------------

def _has_advantage(attacker: Character, defender: Character) -> bool:
    """Check all sources of advantage."""
    if any(e.advantage_on_attacks for e in attacker.active_effects):
        return True
    if attacker.vex_target == defender.name:
        attacker.vex_target = None  # consumed on use
        return True
    # Reckless on defender grants us advantage
    if any(e.grants_advantage_to_enemies for e in defender.active_effects):
        return True
    # Prone grants advantage on melee attacks (within 5ft)
    if Condition.PRONE in defender.conditions:
        return True
    # Heroic Inspiration: spend to gain advantage on this attack
    if hasattr(attacker, '_use_heroic_inspiration') and attacker._use_heroic_inspiration:
        hi_res = attacker.resources.get("heroic_inspiration")
        if hi_res and hi_res.available:
            hi_res.spend()
            attacker._use_heroic_inspiration = False
            return True
    return False


def _has_disadvantage(attacker: Character, defender: Character) -> bool:
    """Check all sources of disadvantage."""
    if defender.is_dodging:
        return True
    if any(e.disadvantage_on_attacks for e in attacker.active_effects):
        return True
    return False


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


def do_dash(char: Character, state: CombatState) -> None:
    """Take the Dash action."""
    char.movement_remaining += char.speed
    state.log(f"  {char.name} dashes (movement: {char.movement_remaining} ft)")
