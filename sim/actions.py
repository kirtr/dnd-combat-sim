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
from sim.dice import d20, d20_detail, eval_dice, eval_dice_twice_take_best, flush_rolls, D20Result, DiceResult, SavageResult


@dataclass
class AttackResult:
    hit: bool
    critical: bool
    damage: int
    damage_type: DamageType
    attack_roll: int
    target_ac: int


@dataclass
class DamageInfo:
    """Structured damage info for formatting."""
    base_rolls: tuple[int, ...]
    flat_mod: int
    total: int
    is_savage: bool = False
    savage_set1: tuple[int, ...] | None = None
    savage_set2: tuple[int, ...] | None = None
    crit_rolls: tuple[int, ...] | None = None


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_rolls(rolls: tuple[int, ...]) -> str:
    """Format dice rolls like [6] or [4,3]."""
    return "[" + ",".join(str(r) for r in rolls) + "]"


def _fmt_d20(d20r: D20Result, adv_sources: list[str], disadv_sources: list[str]) -> str:
    """Format d20 portion: d20=16↑9 (Reckless+prone) or d20=14."""
    s = f"d20={d20r.chosen}"
    if d20r.advantage and d20r.other is not None:
        s += f"↑{d20r.other}"
        if adv_sources:
            s += f" ({'+'.join(adv_sources)})"
    elif d20r.disadvantage and d20r.other is not None:
        s += f"↓{d20r.other}"
        if disadv_sources:
            s += f" ({'+'.join(disadv_sources)})"
    return s


def _fmt_damage(info: DamageInfo) -> str:
    """Format damage: [6]+3=9 dmg or best([4,5],[2,1])+[3,2]+5=24 dmg."""
    parts = []
    if info.is_savage and info.savage_set1 is not None and info.savage_set2 is not None:
        parts.append(f"best({_fmt_rolls(info.savage_set1)},{_fmt_rolls(info.savage_set2)})")
        if info.crit_rolls:
            parts.append(f"+{_fmt_rolls(info.crit_rolls)}")
    else:
        parts.append(_fmt_rolls(info.base_rolls))
        if info.crit_rolls:
            parts.append(f"+{_fmt_rolls(info.crit_rolls)}")

    if info.flat_mod > 0:
        parts.append(f"+{info.flat_mod}")
    elif info.flat_mod < 0:
        parts.append(str(info.flat_mod))

    return "".join(parts) + f"={info.total} dmg"


def _pad_label(label: str) -> str:
    """Pad attack label to 9 chars for alignment (8 + at least 1 space)."""
    return f"{label:<9}"


def _normalize_save_ability(ability: str) -> str:
    return {
        "strength": "str",
        "dexterity": "dex",
        "constitution": "con",
        "intelligence": "int",
        "wisdom": "wis",
        "charisma": "cha",
    }.get(ability, ability)


def _saving_throw_roll(char: Character, ability: str) -> int:
    return d20() + char.saving_throw_total(_normalize_save_ability(ability))


def resolve_save_damage(
    target: Character,
    save_ability: str,
    save_roll: int,
    dc: int,
    damage: int,
    *,
    half_on_save: bool = True,
) -> tuple[int, bool, bool]:
    """Resolve save-for-damage outcomes, including Evasion."""
    normalized_ability = _normalize_save_ability(save_ability)
    has_evasion = "evasion" in target.features and normalized_ability == "dex"
    save_succeeds = save_roll >= dc

    if has_evasion:
        actual_damage = 0 if save_succeeds else damage // 2
    elif save_succeeds:
        actual_damage = damage // 2 if half_on_save else 0
    else:
        actual_damage = damage

    return actual_damage, save_succeeds, has_evasion


# ---------------------------------------------------------------------------
# Advantage / Disadvantage — with source tracking
# ---------------------------------------------------------------------------

def _adv_sources(attacker: Character, defender: Character) -> list[str]:
    """Return list of advantage source names."""
    sources = []
    for e in attacker.active_effects:
        if e.advantage_on_attacks:
            if e.name == "Reckless Attack":
                sources.append("Reckless")
            elif e.name == "Hidden":
                sources.append("Hidden")
            elif e.name == "Fast Hands Help":
                sources.append("Fast Hands")
            elif e.name == "Steady Aim":
                sources.append("Steady Aim")
            else:
                sources.append(e.name)
    if attacker.vow_of_enmity_active:
        sources.append("Vow of Enmity")
    if attacker.vex_target == defender.name:
        sources.append("Vex")
    for e in defender.active_effects:
        if not e.grants_advantage_to_enemies:
            continue
        if e.name == "GuidingBoltMarked":
            sources.append("Guiding Bolt")
        else:
            sources.append("Reckless")
    if Condition.PRONE in defender.conditions:
        sources.append("prone")
    if Condition.STUNNED in defender.conditions:
        sources.append("stunned")
    # GREATER_INVISIBLE attacker
    if Condition.GREATER_INVISIBLE in attacker.conditions:
        sources.append("greater_invisible")
    # PARALYZED / POLYMORPHED defender
    if any(c in defender.conditions for c in [Condition.PARALYZED, Condition.POLYMORPHED]):
        sources.append("target_incapacitated")
    if hasattr(attacker, '_use_heroic_inspiration') and attacker._use_heroic_inspiration:
        hi_res = attacker.resources.get("heroic_inspiration")
        if hi_res and hi_res.available:
            sources.append("Heroic Inspiration")
    return sources


def _disadv_sources(attacker: Character, defender: Character) -> list[str]:
    """Return list of disadvantage source names."""
    sources = []
    if defender.is_dodging:
        sources.append("Dodge")
    for e in attacker.active_effects:
        if e.disadvantage_on_attacks:
            if e.name == "Sapped":
                sources.append("Sap")
            else:
                sources.append(e.name)
    if Condition.FRIGHTENED in attacker.conditions:
        sources.append("frightened")
    if any(e.name == "Shadow Darkness" for e in defender.active_effects):
        sources.append("Darkness")
    # GREATER_INVISIBLE defender: attackers have disadvantage
    if Condition.GREATER_INVISIBLE in defender.conditions:
        sources.append("target_greater_invisible")
    # Lucky defensive
    if not defender.reaction_used:
        luck_res = defender.resources.get("luck_points")
        if luck_res and luck_res.available:
            sources.append("Lucky")
    return sources


def _has_advantage(attacker: Character, defender: Character) -> bool:
    """Check all sources of advantage (consuming Vex, Heroic Inspiration)."""
    if any(e.advantage_on_attacks for e in attacker.active_effects):
        return True
    if attacker.vow_of_enmity_active:
        return True
    if attacker.vex_target == defender.name:
        attacker.vex_target = None
        return True
    if any(e.grants_advantage_to_enemies for e in defender.active_effects):
        return True
    if any(e.name == "GuidingBoltMarked" for e in defender.active_effects):
        return True
    if Condition.PRONE in defender.conditions:
        return True
    if Condition.STUNNED in defender.conditions:
        return True
    # GREATER_INVISIBLE attacker has advantage
    if Condition.GREATER_INVISIBLE in attacker.conditions:
        return True
    # PARALYZED / POLYMORPHED defender
    if any(c in defender.conditions for c in [Condition.PARALYZED, Condition.POLYMORPHED]):
        return True
    if hasattr(attacker, '_use_heroic_inspiration') and attacker._use_heroic_inspiration:
        hi_res = attacker.resources.get("heroic_inspiration")
        if hi_res and hi_res.available:
            hi_res.spend()
            attacker._use_heroic_inspiration = False
            return True
    return False


def _has_disadvantage(attacker: Character, defender: Character) -> bool:
    """Check all sources of disadvantage (consuming Lucky defensive)."""
    if defender.is_dodging:
        return True
    vicious_mockery = next((e for e in attacker.active_effects if e.name == "ViciousMockery"), None)
    if vicious_mockery:
        attacker.active_effects.remove(vicious_mockery)
        return True
    # Sap: consume on use (like Vex) — remove the effect when it fires
    sapped = next((e for e in attacker.active_effects if e.name == "Sapped"), None)
    if sapped:
        attacker.active_effects.remove(sapped)
        return True
    if any(e.disadvantage_on_attacks for e in attacker.active_effects):
        return True
    if Condition.FRIGHTENED in attacker.conditions:
        return True
    if any(e.name == "Shadow Darkness" for e in defender.active_effects):
        return True
    # GREATER_INVISIBLE defender: attackers have disadvantage
    if Condition.GREATER_INVISIBLE in defender.conditions:
        return True
    if not defender.reaction_used:
        luck_res = defender.resources.get("luck_points")
        if luck_res and luck_res.available:
            luck_res.spend()
            defender.reaction_used = True
            return True
    return False


# ---------------------------------------------------------------------------
# Damage calculation — returns DamageInfo for formatting
# ---------------------------------------------------------------------------

def _calc_damage_info(
    attacker: Character, weapon: Weapon,
    crit: bool, is_unarmed: bool, is_thrown: bool,
    is_nick_attack: bool = False,
) -> DamageInfo:
    """Calculate damage and return structured info for formatting."""
    shillelagh = _get_shillelagh_effect(attacker, weapon, is_unarmed)

    dice_expr = weapon.damage_dice
    if shillelagh is not None:
        dice_expr = "1d8"
    if is_unarmed:
        dice_expr = attacker.martial_arts_die or "1"

    gwf_min = None
    if (attacker.fighting_style == "great_weapon_fighting"
            and (weapon.is_two_handed or weapon.is_versatile)
            and weapon.is_melee
            and not is_unarmed):
        gwf_min = 3

    is_savage = False
    savage_set1 = None
    savage_set2 = None
    if attacker.has_savage_attacker and not getattr(attacker, "_savage_used_this_turn", False):
        base_result = eval_dice_twice_take_best(dice_expr, minimum=gwf_min)
        attacker._savage_used_this_turn = True
        is_savage = True
        savage_set1 = base_result.set1
        savage_set2 = base_result.set2
        base_rolls = base_result.rolls
        base_total = base_result.total
    else:
        base_result = eval_dice(dice_expr, minimum=gwf_min)
        base_rolls = base_result.rolls
        base_total = base_result.total

    crit_rolls = None
    crit_total = 0
    if crit:
        if is_savage:
            # Savage Attacker applies to crit dice too — roll twice, take best
            crit_result = eval_dice_twice_take_best(dice_expr, minimum=gwf_min)
        else:
            crit_result = eval_dice(dice_expr, minimum=gwf_min)
        crit_rolls = crit_result.rolls
        crit_total = crit_result.total

    # Flat modifier
    if is_unarmed:
        flat_mod = attacker.unarmed_damage_mod()
        if attacker.is_raging:
            flat_mod += attacker.rage_damage
    elif shillelagh is not None:
        flat_mod = int(shillelagh.extra.get("wis_mod", attacker.wis_mod)) + weapon.bonus
        if attacker.fighting_style == "dueling" and weapon.is_melee and not weapon.is_two_handed:
            flat_mod += 2
    elif is_nick_attack and attacker.fighting_style != "two_weapon_fighting":
        flat_mod = weapon.bonus
    else:
        flat_mod = attacker.damage_modifier(weapon, is_thrown=is_thrown)

    total = sum(base_rolls) + crit_total + flat_mod
    total = max(1, total)

    return DamageInfo(
        base_rolls=base_rolls,
        flat_mod=flat_mod,
        total=total,
        is_savage=is_savage,
        savage_set1=savage_set1,
        savage_set2=savage_set2,
        crit_rolls=crit_rolls,
    )


def _calc_damage(
    attacker: Character, weapon: Weapon,
    crit: bool, is_unarmed: bool, is_thrown: bool,
    is_nick_attack: bool = False,
) -> int:
    """Calculate total damage for a hit (legacy wrapper)."""
    info = _calc_damage_info(attacker, weapon, crit, is_unarmed, is_thrown, is_nick_attack)
    return info.total


def _get_shillelagh_effect(attacker: Character, weapon: Weapon, is_unarmed: bool) -> ActiveEffect | None:
    if is_unarmed:
        return None
    if weapon.name.lower() != "quarterstaff":
        return None
    return next((e for e in attacker.active_effects if e.name == "Shillelagh"), None)


# ---------------------------------------------------------------------------
# Sneak Attack — returns (damage, rolls)
# ---------------------------------------------------------------------------

def _try_sneak_attack(attacker: Character, is_crit: bool, had_advantage: bool) -> tuple[int, tuple[int, ...]]:
    """Returns (extra_damage, raw_rolls) if applicable, else (0, ())."""
    if not attacker.sneak_attack_dice:
        return 0, ()
    if attacker.sneak_attack_used:
        return 0, ()
    if not had_advantage:
        return 0, ()

    result = eval_dice(attacker.sneak_attack_dice)
    rolls = list(result.rolls)
    total = result.total
    if is_crit:
        crit_result = eval_dice(attacker.sneak_attack_dice)
        rolls.extend(crit_result.rolls)
        total += crit_result.total
    attacker.sneak_attack_used = True
    return total, tuple(rolls)


# ---------------------------------------------------------------------------
# Divine Smite — returns (actual_damage, rolls)
# ---------------------------------------------------------------------------

def _try_divine_smite(
    attacker: Character, defender: Character,
    is_crit: bool, state: CombatState,
) -> tuple[int, tuple[int, ...]]:
    """Divine Smite: returns (actual_damage, rolls) or (0, ())."""
    if "divine_smite" not in attacker.features:
        return 0, ()

    # Use highest available slot in our current abstraction (1st/2nd level support).
    if attacker.has_spell_slot(2):
        slot_level = 2
        smite_dice = "3d8"
    elif attacker.has_spell_slot(1):
        slot_level = 1
        smite_dice = "2d8"
    else:
        return 0, ()

    attacker.spend_spell_slot(slot_level)
    result = eval_dice(smite_dice)
    rolls = list(result.rolls)
    total = result.total
    if is_crit:
        crit_result = eval_dice(smite_dice)
        rolls.extend(crit_result.rolls)
        total += crit_result.total
    actual = defender.take_damage(total, DamageType.RADIANT, state)
    return actual, tuple(rolls)


def _try_stunning_strike(attacker: Character, defender: Character, weapon: Weapon, state: CombatState) -> str:
    """Monk Stunning Strike: spend 1 FP after melee hit, force CON save."""
    if "stunning_strike" not in attacker.features:
        return ""
    if not weapon.is_melee:
        return ""
    res = attacker.resources.get("focus_points")
    if not res or not res.available:
        return ""

    res.spend()
    dc = 8 + attacker.proficiency_bonus + attacker.wis_mod
    save_roll = _saving_throw_roll(defender, "con")
    if save_roll < dc:
        defender.apply_condition(Condition.STUNNED)
        existing = next((e for e in defender.active_effects if e.name == "Stunning Strike" and e.extra.get("source") == attacker.name), None)
        if existing:
            existing.extra["remaining_source_turn_ends"] = 2
        else:
            defender.active_effects.append(ActiveEffect(
                name="Stunning Strike",
                source="stunning_strike",
                extra={"source": attacker.name, "remaining_source_turn_ends": 2},
            ))
        return f"Stunning Strike FP-1 · CON save {save_roll}/DC {dc} → STUNNED"
    return f"Stunning Strike FP-1 · CON save {save_roll}/DC {dc} → resisted"


# ---------------------------------------------------------------------------
# Battle Master maneuver helpers — return structured data
# ---------------------------------------------------------------------------

def _try_trip_attack(attacker: Character, defender: Character, state: CombatState) -> tuple[int, str]:
    """Trip Attack: returns (damage, formatted_segment) or (0, "")."""
    if "trip" not in attacker.maneuvers:
        return 0, ""
    if Condition.PRONE in defender.conditions:
        return 0, ""
    sup_res = attacker.resources.get("superiority_dice")
    if not sup_res or not sup_res.available:
        return 0, ""
    sup_res.spend()
    result = eval_dice(attacker.superiority_die_size)
    dmg = result.total
    die_val = result.rolls[0] if result.rolls else dmg
    dc = 8 + attacker.str_mod + attacker.proficiency_bonus
    save = _saving_throw_roll(defender, "str")
    if save < dc:
        defender.apply_condition(Condition.PRONE)
        segment = f"Trip [d8={die_val}] → prone (save {save}/DC {dc})"
    else:
        segment = f"Trip [d8={die_val}] → resisted (save {save}/DC {dc})"
    return dmg, segment


def _try_menacing_attack(attacker: Character, defender: Character, state: CombatState) -> tuple[int, str]:
    """Menacing Attack: returns (damage, formatted_segment) or (0, "")."""
    if "menacing" not in attacker.maneuvers:
        return 0, ""
    if Condition.FRIGHTENED in defender.conditions:
        return 0, ""
    sup_res = attacker.resources.get("superiority_dice")
    if not sup_res or not sup_res.available:
        return 0, ""
    if "trip" in attacker.maneuvers:
        return 0, ""
    sup_res.spend()
    result = eval_dice(attacker.superiority_die_size)
    dmg = result.total
    die_val = result.rolls[0] if result.rolls else dmg
    dc = 8 + attacker.str_mod + attacker.proficiency_bonus
    save_roll = _saving_throw_roll(defender, "wis")
    if save_roll < dc:
        if defender.apply_condition(Condition.FRIGHTENED):
            defender.active_effects.append(ActiveEffect(
                name="Frightened",
                source="menacing_attack",
                duration=1,
                end_trigger="end_of_turn",
            ))
            segment = f"Menacing [d8={die_val}] → frightened (save {save_roll}/DC {dc})"
        else:
            segment = f"Menacing [d8={die_val}] → immune (save {save_roll}/DC {dc})"
    else:
        segment = f"Menacing [d8={die_val}] → resisted (save {save_roll}/DC {dc})"
    return dmg, segment


# ---------------------------------------------------------------------------
# Main attack resolution
# ---------------------------------------------------------------------------

def resolve_attack(
    attacker: Character,
    defender: Character,
    weapon: Weapon,
    state: CombatState,
    *,
    is_thrown: bool = False,
    is_unarmed: bool = False,
    is_nick_attack: bool = False,
    attack_label: str = "ACTION",
) -> AttackResult:
    """Resolve a single attack, apply damage, log single line, return result."""

    # Collect adv/disadv sources BEFORE consuming them
    adv_src = _adv_sources(attacker, defender)
    disadv_src = _disadv_sources(attacker, defender)

    # Determine advantage / disadvantage (this consumes Vex, Lucky, etc.)
    adv = _has_advantage(attacker, defender)
    disadv = _has_disadvantage(attacker, defender)

    # Attack bonus
    shillelagh = _get_shillelagh_effect(attacker, weapon, is_unarmed)
    if is_unarmed:
        attack_bonus = attacker.unarmed_attack_mod()
    elif shillelagh is not None:
        attack_bonus = attacker.spell_attack_bonus + weapon.bonus
    else:
        attack_bonus = attacker.attack_modifier(weapon)

    # Sacred Weapon (Devotion Paladin): +CHA mod to attack rolls
    sacred_weapon_effect = next((e for e in attacker.active_effects if e.name == "SacredWeapon"), None)
    if sacred_weapon_effect and weapon.is_melee:
        attack_bonus += int(sacred_weapon_effect.extra.get("cha_mod", attacker.cha_mod))

    # Blessing of the Forge (Forge Cleric): +1 attack with primary weapon
    if "blessing_of_the_forge" in attacker.features and weapon.is_melee:
        attack_bonus += 1

    # Shield spell reaction
    if (not defender.reaction_used
            and "shield_spell" in defender.features):
        shield_res = defender.resources.get("shield_spell")
        if shield_res and shield_res.available:
            if not any(e.name == "Shield Spell" for e in defender.active_effects):
                shield_res.spend()
                defender.reaction_used = True
                defender.active_effects.append(ActiveEffect(
                    name="Shield Spell",
                    source="arcane_trickster",
                    end_trigger="start_of_turn",
                    ac_bonus=5,
                ))
                state.log(f"REACTION {defender.name}: Shield → +5 AC")

    d20r = d20_detail(advantage=adv, disadvantage=disadv)
    roll_result = d20r.chosen

    # Halfling Luck
    if roll_result == 1 and "luck" in attacker.species_traits:
        d20r2 = d20_detail()
        roll_result = d20r2.chosen
        # Update d20r to reflect the reroll for display
        d20r = d20r2
        # We don't show the original nat 1 in the new format, just the reroll

    # Hexblade Curse: crit on 19-20 against cursed target
    effective_crit_threshold = attacker.crit_threshold
    if (
        "hexblade_curse" in attacker.features
        and attacker.hexblade_curse_target == defender.name
        and effective_crit_threshold > 19
    ):
        effective_crit_threshold = 19

    # Assassinate: auto-crit pending (first attack after surprise)
    _assassinate_crit = False
    if getattr(attacker, "_assassinate_auto_crit_pending", False):
        _assassinate_crit = True
        attacker._assassinate_auto_crit_pending = False
        is_crit = True
    else:
        is_crit = roll_result >= effective_crit_threshold

    total = roll_result + attack_bonus
    target_ac = defender.effective_ac

    # Build the d20 portion
    d20_str = _fmt_d20(d20r, adv_src, disadv_src)

    # Collect mechanic tags to append
    tags: list[str] = []
    if is_nick_attack:
        tags.append("Nick")
    if _assassinate_crit:
        tags.append("Assassinate!")

    # PARALYZED / STUNNED defender at melee range → auto-crit
    if not is_crit and any(c in defender.conditions for c in [Condition.PARALYZED, Condition.STUNNED]):
        if state.distance <= 5:
            is_crit = True
            tags.append("auto-crit")

    label = _pad_label(attack_label)

    # Natural 1 auto-miss
    if roll_result == 1:
        graze_dmg = _try_graze_new(attacker, weapon, defender, state, label, d20_str, tags, target_ac)
        if graze_dmg == 0:
            tag_str = (" · " + " · ".join(tags)) if tags else ""
            state.log(f"{label}{weapon.name} {d20_str} → MISS ({total}/{target_ac}){tag_str}")
        return AttackResult(
            hit=False, critical=False, damage=graze_dmg,
            damage_type=weapon.damage_type, attack_roll=total, target_ac=target_ac,
        )

    if is_crit or total >= target_ac:
        return _resolve_hit(
            attacker, defender, weapon, state,
            is_crit=is_crit, is_thrown=is_thrown, is_unarmed=is_unarmed,
            is_nick_attack=is_nick_attack, attack_label=attack_label,
            adv=adv, disadv=disadv, d20r=d20r, d20_str=d20_str,
            roll_result=roll_result, total=total, target_ac=target_ac,
            tags=tags, adv_src=adv_src, disadv_src=disadv_src,
        )
    else:
        # Precision Attack
        if (total < target_ac
                and "precision" in attacker.maneuvers
                and not is_unarmed):
            sup_res = attacker.resources.get("superiority_dice")
            if sup_res and sup_res.available:
                gap = target_ac - total
                if gap <= 8:
                    precision_result = eval_dice(attacker.superiority_die_size)
                    precision_roll = precision_result.total
                    precision_die = precision_result.rolls[0] if precision_result.rolls else precision_roll
                    sup_res.spend()
                    new_total = total + precision_roll
                    if new_total >= target_ac:
                        # Precision turned miss into hit
                        return _resolve_hit(
                            attacker, defender, weapon, state,
                            is_crit=False, is_thrown=is_thrown, is_unarmed=is_unarmed,
                            is_nick_attack=is_nick_attack, attack_label=attack_label,
                            adv=adv, disadv=disadv, d20r=d20r, d20_str=d20_str,
                            roll_result=roll_result, total=new_total, target_ac=target_ac,
                            tags=tags, adv_src=adv_src, disadv_src=disadv_src,
                            precision_die=precision_die, precision_bonus=precision_roll,
                            original_total=total,
                        )

        # Lucky feat reroll
        luck_res = attacker.resources.get("luck_points")
        if luck_res and luck_res.available:
            luck_res.spend()
            d20r_luck = d20_detail(advantage=adv, disadvantage=disadv)
            luck_roll = d20r_luck.chosen
            if luck_roll == 1 and "luck" in attacker.species_traits:
                d20r_luck = d20_detail()
                luck_roll = d20r_luck.chosen
            luck_total = luck_roll + attack_bonus
            if luck_roll >= attacker.crit_threshold or luck_total >= target_ac:
                is_crit2 = luck_roll >= attacker.crit_threshold
                tags.append("Lucky")
                return _resolve_hit(
                    attacker, defender, weapon, state,
                    is_crit=is_crit2, is_thrown=is_thrown, is_unarmed=is_unarmed,
                    is_nick_attack=is_nick_attack, attack_label=attack_label,
                    adv=adv, disadv=disadv, d20r=d20r_luck,
                    d20_str=_fmt_d20(d20r_luck, adv_src, disadv_src),
                    roll_result=luck_roll, total=luck_total, target_ac=target_ac,
                    tags=tags, adv_src=adv_src, disadv_src=disadv_src,
                )

        # MISS
        graze_dmg = _try_graze_new(attacker, weapon, defender, state, label, d20_str, tags, target_ac)
        if graze_dmg == 0:
            tag_str = (" · " + " · ".join(tags)) if tags else ""
            state.log(f"{label}{weapon.name} {d20_str} → MISS ({total}/{target_ac}){tag_str}")

        # Riposte on miss
        if not is_unarmed:
            try_riposte(defender, attacker, weapon, state)

        return AttackResult(
            hit=False, critical=False, damage=graze_dmg,
            damage_type=weapon.damage_type, attack_roll=total, target_ac=target_ac,
        )


def _resolve_hit(
    attacker: Character, defender: Character, weapon: Weapon,
    state: CombatState, *,
    is_crit: bool, is_thrown: bool, is_unarmed: bool, is_nick_attack: bool,
    attack_label: str, adv: bool, disadv: bool,
    d20r: D20Result, d20_str: str,
    roll_result: int, total: int, target_ac: int,
    tags: list[str], adv_src: list[str], disadv_src: list[str],
    precision_die: int | None = None, precision_bonus: int = 0,
    original_total: int | None = None,
) -> AttackResult:
    """Resolve a confirmed hit, format and log."""
    label = _pad_label(attack_label)

    # Calculate damage
    dmg_info = _calc_damage_info(attacker, weapon, is_crit, is_unarmed, is_thrown, is_nick_attack)
    damage = dmg_info.total

    # Sneak Attack
    sa_dmg, sa_rolls = _try_sneak_attack(attacker, is_crit, adv and not disadv)
    damage += sa_dmg

    # Hunter's Mark
    hm_dmg = 0
    hm_rolls: tuple[int, ...] = ()
    if attacker.hunters_mark_active:
        hm_result = eval_dice("1d6")
        hm_rolls = hm_result.rolls
        hm_dmg = hm_result.total
        if is_crit:
            hm_crit = eval_dice("1d6")
            hm_rolls = hm_rolls + hm_crit.rolls
            hm_dmg += hm_crit.total
        damage += hm_dmg

    # Colossus Slayer
    cs_dmg = 0
    cs_rolls: tuple[int, ...] = ()
    if (attacker.has_colossus_slayer
            and not attacker.colossus_slayer_used
            and defender.current_hp < defender.max_hp):
        cs_result = eval_dice("1d8")
        cs_rolls = cs_result.rolls
        cs_dmg = cs_result.total
        if is_crit:
            cs_crit = eval_dice("1d8")
            cs_rolls = cs_rolls + cs_crit.rolls
            cs_dmg += cs_crit.total
        damage += cs_dmg
        attacker.colossus_slayer_used = True

    # Hexblade's Curse: +PB damage against cursed target
    hex_curse_dmg = 0
    if (
        "hexblade_curse" in attacker.features
        and attacker.hexblade_curse_target == defender.name
    ):
        hex_curse_dmg = attacker.proficiency_bonus
        damage += hex_curse_dmg

    # Blessing of the Forge (Forge Cleric): +1 damage with primary weapon
    if "blessing_of_the_forge" in attacker.features and weapon.is_melee:
        damage += 1

    # Blade Flourish (Swords Bard): add rolled die to damage (already tracked in combat.py)
    blade_flourish_dmg = 0
    bf_effect = next((e for e in attacker.active_effects if e.name == "BladeFlourish"), None)
    if bf_effect and not getattr(attacker, "_blade_flourish_used_this_turn", False):
        # The roll is stored in ac_bonus (same die for both)
        blade_flourish_dmg = bf_effect.ac_bonus
        damage += blade_flourish_dmg

    # Trip Attack
    trip_dmg, trip_seg = _try_trip_attack(attacker, defender, state)
    damage += trip_dmg

    # Menacing Attack
    menacing_dmg, menacing_seg = _try_menacing_attack(attacker, defender, state)
    damage += menacing_dmg

    # Build damage packet
    damage_packet = [(damage, weapon.damage_type)]

    # Giant ancestry extras
    fire_extra = 0
    fire_rolls: tuple[int, ...] = ()
    if attacker.giant_ancestry == "fire":
        fire_res = attacker.resources.get("fire_giant")
        if fire_res and fire_res.available:
            fire_res.spend()
            fire_result = eval_dice("1d10")
            fire_extra = fire_result.total
            fire_rolls = fire_result.rolls
            damage_packet.append((fire_extra, DamageType.FIRE))

    frost_extra = 0
    frost_rolls: tuple[int, ...] = ()
    if attacker.giant_ancestry == "frost":
        frost_res = attacker.resources.get("frost_giant")
        if frost_res and frost_res.available:
            frost_res.spend()
            frost_result = eval_dice("1d6")
            frost_extra = frost_result.total
            frost_rolls = frost_result.rolls
            damage_packet.append((frost_extra, DamageType.COLD))
            defender.speed = max(0, defender.speed - 10)

    # Apply damage
    pre_temp_hp = defender.temp_hp
    actual = defender.take_attack_damage(damage_packet, state, is_attack=True)

    # AoA retaliation
    if not weapon.is_ranged and not is_thrown:
        _try_aoa_retaliation(attacker, defender, state, pre_temp_hp)

    # Weapon mastery on hit
    mastery_tags: list[str] = []
    if not is_unarmed and attacker.can_use_mastery(weapon):
        mastery_tags = _apply_mastery_on_hit_new(attacker, defender, weapon, state)

    # Hill's Tumble
    if attacker.giant_ancestry == "hill":
        hill_res = attacker.resources.get("hill_giant")
        if hill_res and hill_res.available:
            hill_res.spend()
            defender.conditions.add(Condition.PRONE)
            tags.append("Hill's Tumble → prone")

    # Divine Smite
    smite_actual, smite_rolls = _try_divine_smite(attacker, defender, is_crit, state)

    # --- Build the single log line ---
    hit_type = "CRIT" if is_crit else "HIT"

    # Precision display
    if precision_die is not None and original_total is not None:
        line = f"{label}{weapon.name} {d20_str} → MISS ({original_total}/{target_ac}) · Precision [d8={precision_die}] → HIT ({total}/{target_ac})"
    else:
        line = f"{label}{weapon.name} {d20_str} → {hit_type} ({total}/{target_ac})"

    # Tags before damage (Nick, Lucky, Frenzy etc.)
    for t in tags:
        line += f" · {t}"

    # Damage portion
    line += f" · {_fmt_damage(dmg_info)}"

    # Extra damage labels
    if sa_dmg:
        line += f" +SA {_fmt_rolls(sa_rolls)}={sa_dmg}"
    if hm_dmg:
        line += f" +Hunter's Mark {_fmt_rolls(hm_rolls)}={hm_dmg}" if len(hm_rolls) > 1 else f" +Hunter's Mark [{hm_rolls[0]}]"
    if cs_dmg:
        line += f" +Colossus Slayer {_fmt_rolls(cs_rolls)}={cs_dmg}" if len(cs_rolls) > 1 else f" +Colossus Slayer [{cs_rolls[0]}]"
    if hex_curse_dmg:
        line += f" +HexCurse+{hex_curse_dmg}"
    if blade_flourish_dmg:
        line += f" +Flourish+{blade_flourish_dmg}"
    if smite_actual:
        line += f" +Smite {_fmt_rolls(smite_rolls)}={smite_actual} radiant"
    if fire_extra:
        line += f" +Fire Giant {_fmt_rolls(fire_rolls)}={fire_extra} fire"
    if frost_extra:
        line += f" +Frost Giant {_fmt_rolls(frost_rolls)}={frost_extra} cold"

    # Mechanic segments (Trip, Menacing)
    if trip_seg:
        line += f" · {trip_seg}"
    if menacing_seg:
        line += f" · {menacing_seg}"

    # Mastery condition tags (Vex, Sap, Topple)
    for mt in mastery_tags:
        line += f" · {mt}"

    # Stunning Strike (monk)
    ss_seg = _try_stunning_strike(attacker, defender, weapon, state)
    if ss_seg:
        line += f" · {ss_seg}"

    # HP
    line += f" [{defender.current_hp}/{defender.max_hp} HP]"

    state.log(line)

    return AttackResult(
        hit=True, critical=is_crit, damage=damage,
        damage_type=weapon.damage_type, attack_roll=total, target_ac=target_ac,
    )


# ---------------------------------------------------------------------------
# Graze (new format)
# ---------------------------------------------------------------------------

def _try_graze_new(
    attacker: Character, weapon: Weapon,
    defender: Character, state: CombatState,
    label: str, d20_str: str, tags: list[str], target_ac: int,
) -> int:
    """Apply Graze mastery on a miss. Logs GRAZE line. Returns damage dealt."""
    if not weapon.mastery or weapon.mastery != MasteryProperty.GRAZE:
        return 0
    if not attacker.can_use_mastery(weapon):
        return 0
    attack_bonus = attacker.attack_modifier(weapon)
    graze_dmg = max(0, attacker._attack_ability_mod(weapon))
    if graze_dmg > 0:
        actual = defender.take_damage(graze_dmg, weapon.damage_type, state)
        tag_str = (" · " + " · ".join(tags)) if tags else ""
        # Reconstruct total for display
        # We don't have d20r here easily, so compute from d20_str
        state.log(f"{label}{weapon.name} {d20_str} → GRAZE · {actual} dmg{tag_str} [{defender.current_hp}/{defender.max_hp} HP]")
        return actual
    return 0


# Legacy graze wrapper (unused but kept for safety)
def _try_graze(attacker, weapon, defender, state, attack_label="ACTION"):
    return 0  # Replaced by _try_graze_new


# ---------------------------------------------------------------------------
# Weapon Mastery on hit — returns tags
# ---------------------------------------------------------------------------

def _apply_mastery_on_hit_new(
    attacker: Character, defender: Character,
    weapon: Weapon, state: CombatState,
) -> list[str]:
    """Apply weapon mastery effects after a hit. Returns formatted tag strings."""
    mastery = weapon.mastery
    if mastery is None:
        return []

    tags = []
    if mastery == MasteryProperty.VEX:
        attacker.vex_target = defender.name
        tags.append("Vex → adv next attack")

    elif mastery == MasteryProperty.SAP:
        defender.active_effects.append(ActiveEffect(
            name="Sapped",
            source=weapon.name,
            disadvantage_on_attacks=True,
        ))
        tags.append("Sap → disadv next attack")

    elif mastery == MasteryProperty.SLOW:
        tags.append("Slow → -10 speed")

    elif mastery == MasteryProperty.TOPPLE:
        ability_mod = attacker._attack_ability_mod(weapon)
        dc = 8 + ability_mod + attacker.proficiency_bonus
        save_roll = _saving_throw_roll(defender, "con")
        if save_roll < dc:
            defender.apply_condition(Condition.PRONE)
            tags.append(f"Topple → prone (save {save_roll}/DC {dc})")
        else:
            tags.append(f"Topple → resisted (save {save_roll}/DC {dc})")

    elif mastery == MasteryProperty.PUSH:
        state.distance = min(120, state.distance + 10)
        tags.append(f"Push → 10 ft (distance: {state.distance} ft)")

    return tags


def _try_aoa_retaliation(
    attacker: Character, defender: Character,
    state: CombatState, had_temp_hp: int,
) -> None:
    """Armor of Agathys retaliation."""
    if had_temp_hp <= 0:
        return
    aoa_dmg = getattr(defender, "aoa_cold_damage", 0)
    if aoa_dmg <= 0:
        return
    aoa_effect = next((e for e in defender.active_effects if e.name == "Armor of Agathys"), None)
    if aoa_effect is None:
        return
    actual_aoa = attacker.take_damage(aoa_dmg, DamageType.COLD, state)
    state.log(
        f"REACTION Armor of Agathys: {attacker.name} takes {actual_aoa} cold"
        f" [{attacker.current_hp}/{attacker.max_hp} HP]"
    )


# ---------------------------------------------------------------------------
# Riposte
# ---------------------------------------------------------------------------

def try_riposte(defender: Character, attacker: Character, weapon: Weapon, state: CombatState) -> None:
    """Riposte: reaction attack when enemy misses."""
    if "riposte" not in defender.maneuvers:
        return
    if defender.reaction_used:
        return
    sup_res = defender.resources.get("superiority_dice")
    if not sup_res or not sup_res.available:
        return
    mw = defender.best_melee_weapon()
    if not mw or state.distance > 5:
        return
    sup_res.spend()
    defender.reaction_used = True

    attack_bonus = defender.attack_modifier(mw)
    d20r = d20_detail()
    roll_result = d20r.chosen
    total_roll = roll_result + attack_bonus
    is_crit = roll_result >= defender.crit_threshold
    target_ac = attacker.effective_ac
    label = _pad_label("REACTION")
    d20_str = f"d20={roll_result}"

    if roll_result == 1:
        state.log(f"{label}{mw.name} {d20_str} → MISS ({total_roll}/{target_ac}) · Riposte")
        return

    if is_crit or total_roll >= target_ac:
        dmg_info = _calc_damage_info(defender, mw, is_crit, False, False, False)
        damage = dmg_info.total
        riposte_result = eval_dice(defender.superiority_die_size)
        riposte_dmg = riposte_result.total
        riposte_die = riposte_result.rolls[0] if riposte_result.rolls else riposte_dmg
        damage += riposte_dmg
        actual = attacker.take_attack_damage([(damage, mw.damage_type)], state, is_attack=True)

        # Rebuild dmg_info total to include riposte
        hit_type = "CRIT" if is_crit else "HIT"
        # Format: include riposte die in the damage display
        dmg_str = _fmt_damage(dmg_info)
        line = f"{label}{mw.name} {d20_str} → {hit_type} ({total_roll}/{target_ac}) · Riposte · {dmg_str} +Riposte [d8={riposte_die}] [{attacker.current_hp}/{attacker.max_hp} HP]"
        state.log(line)
    else:
        state.log(f"{label}{mw.name} {d20_str} → MISS ({total_roll}/{target_ac}) · Riposte")


# ---------------------------------------------------------------------------
# Spell resolution helpers
# ---------------------------------------------------------------------------

def resolve_spell_attack(
    caster: Character,
    target: Character,
    damage_dice: str,
    damage_type: DamageType,
    spell_name: str,
    state: CombatState,
    *,
    damage_mod: int = 0,
    attack_label: str = "ACTION",
) -> bool:
    """Resolve a spell attack roll. Returns True if hit."""
    d20r = d20_detail()
    attack_roll = d20r.chosen + caster.spell_attack_bonus
    target_ac = target.effective_ac
    label = _pad_label(attack_label)
    d20_str = f"d20={d20r.chosen}"
    hit = attack_roll >= target_ac
    if hit:
        result = eval_dice(damage_dice)
        total_damage = max(1, result.total + damage_mod)
        actual = target.take_attack_damage([(total_damage, damage_type)], state, is_attack=True)
        mod_str = f"{damage_mod:+d}" if damage_mod else ""
        state.log(
            f"{label}{spell_name} {d20_str} → HIT ({attack_roll}/{target_ac})"
            f" · {_fmt_rolls(result.rolls)}{mod_str}={actual} {damage_type.name.lower()} dmg"
            f" [{target.current_hp}/{target.max_hp} HP]"
        )
    else:
        state.log(f"{label}{spell_name} {d20_str} → MISS ({attack_roll}/{target_ac})")
    return hit


def resolve_spell_save(
    caster: Character,
    target: Character,
    damage_dice: str,
    damage_type: DamageType,
    spell_name: str,
    save_ability: str,
    state: CombatState,
    half_on_save: bool = True,
    *,
    return_details: bool = False,
) -> int | tuple[int, bool, int, int]:
    """Resolve a saving throw spell.

    Returns actual damage dealt by default. When return_details=True, returns
    (actual_damage, save_succeeds, save_roll, dc).
    """
    dc = caster.spell_save_dc
    save_roll = _saving_throw_roll(target, save_ability)
    result = eval_dice(damage_dice)
    dmg = result.total

    # Elemental Affinity (Sorcerer L6 Draconic): add CHA mod when damage matches ancestry
    affinity_bonus = 0
    if (
        "elemental_affinity" in caster.features
        and damage_type == getattr(caster, "breath_weapon_damage_type", None)
    ):
        affinity_bonus = caster.cha_mod
        dmg += affinity_bonus

    actual_dmg, save_succeeds, has_evasion = resolve_save_damage(
        target,
        save_ability,
        save_roll,
        dc,
        dmg,
        half_on_save=half_on_save,
    )

    # Potent Cantrip (Evocation Wizard L6): target takes half damage on successful save vs cantrip
    # This is applied when damage_dice comes from a cantrip (handled externally by checking spell.level==0)
    # Here we receive a flag via the spell_name prefixed with "cantrip:" convention or via caller
    # Simpler: check if caster has potent_cantrip and save_succeeds and actual_dmg == 0 and half_on_save==False
    if (
        "potent_cantrip" in caster.features
        and save_succeeds
        and actual_dmg == 0
        and not half_on_save
    ):
        actual_dmg = dmg // 2

    actual = target.take_damage(actual_dmg, damage_type, state)
    label = _pad_label("ACTION")
    result_str = "saves" if save_succeeds else "fails"
    msg = (
        f"{label}{spell_name}: {target.name} {result_str} ({save_roll}/DC {dc})"
        f" · {_fmt_rolls(result.rolls)}={actual} {damage_type.name.lower()} dmg"
    )
    if affinity_bonus:
        msg += f" +Affinity({affinity_bonus})"
    if has_evasion:
        msg += f" · Evasion → {actual_dmg} dmg"
    state.log(msg + f" [{target.current_hp}/{target.max_hp} HP]")
    if return_details:
        return actual, save_succeeds, save_roll, dc
    return actual


def do_second_wind(char: Character, state: CombatState) -> None:
    """Use Second Wind as a bonus action."""
    res = char.resources.get("second_wind")
    if not res or not res.available or char.bonus_action_used:
        return
    res.spend()
    char.bonus_action_used = True
    result = eval_dice("1d10")
    die_val = result.rolls[0] if result.rolls else result.total
    healing = result.total + char.level
    actual = char.heal(healing)
    label = _pad_label("BONUS")
    state.log(f"{label}Second Wind → [1d10={die_val}]+{char.level}={healing} healed [{char.current_hp}/{char.max_hp} HP]")


def do_dodge(char: Character, state: CombatState) -> None:
    """Take the Dodge action."""
    char.conditions.add(Condition.DODGING)


def do_dash(char: Character, state: CombatState) -> None:
    """Take the Dash action."""
    char.movement_remaining += char.speed
    state.log(f"  {char.name} dashes (movement: {char.movement_remaining} ft)")
