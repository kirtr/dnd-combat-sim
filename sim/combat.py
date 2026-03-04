"""Combat loop: initiative, turn phases, death, distance tracking."""

from __future__ import annotations

import re

from sim.dice import d20, eval_dice, roll
from sim.models import Character, CombatState, CombatPhase, Condition, ActiveEffect, DamageType, MasteryProperty
from sim.actions import (
    resolve_attack,
    do_second_wind,
    do_dash,
    do_dodge,
    resolve_spell_attack,
    resolve_spell_save,
    resolve_save_damage,
)
from sim.effects import apply_rage, apply_bear_totem_rage, apply_reckless_attack
from sim.spells import cantrip_die_count, get_spell, SpellData
from sim.tactics import TacticsEngine, TurnAction


def _pad_label(label: str) -> str:
    return f"{label:<9}"


def _find_effect(char: Character, name: str) -> ActiveEffect | None:
    return next((e for e in char.active_effects if e.name == name), None)


def roll_initiative(char: Character) -> int:
    """Roll initiative for a character."""
    roll1 = d20()
    # Feral Instinct (Barbarian L7): roll with advantage
    if "feral_instinct" in char.features:
        roll2 = d20()
        roll1 = max(roll1, roll2)
    return roll1 + char.dex_mod + char.initiative_bonus


def run_combat(
    a: Character,
    b: Character,
    tactics_a: TacticsEngine,
    tactics_b: TacticsEngine,
    *,
    starting_distance: int = 20,
    verbose: bool = False,
) -> CombatState:
    """Run a full 1v1 combat to completion. Returns the final CombatState."""
    state = CombatState(
        combatant_a=a,
        combatant_b=b,
        distance=starting_distance,
        starting_distance=starting_distance,
        verbose=verbose,
        phase=CombatPhase.RANGED,
    )

    # Roll initiative
    init_a = roll_initiative(a)
    init_b = roll_initiative(b)
    if init_a > init_b:
        state.turn_order = [a, b]
    elif init_b > init_a:
        state.turn_order = [b, a]
    else:
        # Tied initiative: pure coin flip — no DEX bonus
        import random
        state.turn_order = [a, b] if random.random() < 0.5 else [b, a]

    state.log(f"Initiative: {a.name}={init_a}, {b.name}={init_b}")
    state.log(f"Turn order: {state.turn_order[0].name} → {state.turn_order[1].name}")
    state.log(f"Starting distance: {state.distance} ft")

    # Combat loop
    max_rounds = 100
    while a.is_alive and b.is_alive and state.round_number < max_rounds:
        state.round_number += 1
        state.log(f"\n=== Round {state.round_number} ===")

        for char in state.turn_order:
            if not char.is_alive:
                continue
            opponent = state.opponent_of(char)
            tactics = tactics_a if char is a else tactics_b

            _apply_start_of_turn_auras(char, opponent, state)
            if not char.is_alive:
                state.log(f"\n{char.name} has fallen! {opponent.name} wins!")
                break

            if hasattr(char, "_savage_used_this_turn"):
                char._savage_used_this_turn = False

            _execute_turn(char, opponent, tactics, state)

            if not opponent.is_alive:
                state.log(f"\n{opponent.name} has fallen! {char.name} wins!")
                break

            # Extra turns (Time Stop): take additional turns if granted
            extra_turn_limit = 10  # safety cap
            while char.extra_turns_remaining > 0 and extra_turn_limit > 0 and char.is_alive and opponent.is_alive:
                char.extra_turns_remaining -= 1
                extra_turn_limit -= 1
                state.log(f"\n=== {char.name} EXTRA TURN (Time Stop) ===")
                _execute_turn(char, opponent, tactics, state)
                if not opponent.is_alive:
                    state.log(f"\n{opponent.name} has fallen! {char.name} wins!")
                    break

        # Transition from ranged phase to melee at end of round 1
        if state.phase == CombatPhase.RANGED:
            state.phase = CombatPhase.MELEE
            state.distance = 5
            state.log("--- Both sides close to melee range. ---")

    return state


def _execute_turn(
    char: Character,
    opponent: Character,
    tactics: TacticsEngine,
    state: CombatState,
) -> None:
    """Execute a single character's turn."""
    # Log status changes from start_turn BEFORE calling it
    _log_start_of_turn_status(char, state)

    char.start_turn()
    state.log(f"\n--- {char.name}'s turn (HP: {char.current_hp}/{char.max_hp}) ---")

    # --- Assassinate: set auto-crit pending on first turn if going first ---
    if (
        "assassinate" in char.features
        and state.round_number == 1
        and not char.assassin_surprised_this_combat
        and not getattr(char, "_assassinate_auto_crit_pending", False)
    ):
        # Going first means we're acting before the opponent this round
        # The turn_order list: if char is index 0, they go first
        if state.turn_order and state.turn_order[0] is char:
            char.assassin_surprised_this_combat = True
            char._assassinate_auto_crit_pending = True
            state.log(f"  {char.name} ASSASSINATE — first attack this turn is an automatic critical hit!")

    # --- Condition checks at turn start ---

    # BANISHED: skip turn entirely (caster concentration handled — if concentration breaks, condition ends)
    if Condition.BANISHED in char.conditions:
        # Check if the caster's concentration is still up (simplified: always hold unless a check fires)
        state.log(f"  {char.name} is banished — skips turn")
        char.end_turn()
        _tick_stunning_strike_expiry(char, state)
        return

    # PARALYZED: WIS save to end condition
    if Condition.PARALYZED in char.conditions:
        paralysis_effect = next((e for e in char.active_effects if e.name == "Paralyzed"), None)
        dc = paralysis_effect.extra.get("dc", 15) if paralysis_effect else 15
        save = d20() + char.saving_throw_total("wis")
        if save >= dc:
            char.conditions.discard(Condition.PARALYZED)
            if paralysis_effect:
                char.active_effects.remove(paralysis_effect)
            state.log(f"  {char.name} breaks free of paralysis (WIS save {save} vs DC {dc})")
        else:
            state.log(f"  {char.name} is paralyzed — skips turn (WIS save {save} vs DC {dc})")
            char.end_turn()
            _tick_stunning_strike_expiry(char, state)
            return

    # POLYMORPHED: can only make one weak bite attack
    if Condition.POLYMORPHED in char.conditions:
        _do_polymorph_attack(char, opponent, state)
        char.end_turn()
        _tick_stunning_strike_expiry(char, state)
        return

    # PAIN: CON save DC 12 to take actions this turn
    if Condition.PAIN in char.conditions:
        save = d20() + char.saving_throw_total("con")
        if save >= 12:
            char.conditions.discard(Condition.PAIN)
            state.log(f"  {char.name} shakes off Power Word Pain")
        else:
            char._pain_blocked_actions = True
            char.action_used = True  # block actions (movement still OK)
            state.log(f"  {char.name} wracked with pain — no actions this turn")

    # STUNNED: CON save to end; auto-skip if still stunned
    if Condition.STUNNED in char.conditions:
        stun_effect = next((e for e in char.active_effects if e.name == "Stunned"), None)
        dc = stun_effect.extra.get("dc", 15) if stun_effect else 15
        save = d20() + char.saving_throw_total("con")
        if save >= dc:
            char.conditions.discard(Condition.STUNNED)
            if stun_effect:
                char.active_effects.remove(stun_effect)
            state.log(f"  {char.name} recovers from stun (CON save {save} vs DC {dc})")
        else:
            state.log(f"  {char.name} is stunned — skips turn")
            char.end_turn()
            _tick_stunning_strike_expiry(char, state)
            return

    # INCAPACITATED (e.g. Hypnotic Pattern): skip turn
    if Condition.INCAPACITATED in char.conditions:
        state.log(f"STATUS   {char.name}: incapacitated — skips turn")
        char.end_turn()
        _tick_stunning_strike_expiry(char, state)
        return

    decisions = tactics.decide_turn(char, state)

    is_ranged_phase = state.phase == CombatPhase.RANGED
    _melee_skip_logged = False

    _melee_action_kinds = frozenset({
        "attack", "action_surge", "frenzy_attack", "flurry",
        "martial_arts_strike", "open_hand_flurry", "booming_blade",
    })

    for action in decisions:
        if not opponent.is_alive:
            break

        if action.kind in _melee_action_kinds:
            if is_ranged_phase:
                if not _melee_skip_logged:
                    state.log(f"  [Ranged phase — {char.name} cannot attack in melee]")
                    _melee_skip_logged = True
                continue

        if action.kind == "rage":
            _do_rage(char, state)
        elif action.kind == "reckless":
            _do_reckless(char, state)
        elif action.kind == "ranged_attack":
            if not char.action_used:
                _do_ranged_attack(char, opponent, action, state)
        elif action.kind == "move":
            _do_move(char, opponent, state)
        elif action.kind == "attack":
            if not char.action_used:
                _do_melee_attack(char, opponent, action, state)
        elif action.kind == "cast_spell":
            spell_name = action.extra.get("spell", "")
            spell = get_spell(spell_name) if spell_name else None
            is_bonus_spell = bool(spell and (spell.bonus_action or spell_name == "shillelagh"))
            if spell_name and spell and is_bonus_spell:
                if not char.bonus_action_used:
                    _do_cast_spell(char, opponent, spell_name, action.extra.get("slot_level", 0), state)
            elif not char.action_used and spell_name:
                _do_cast_spell(char, opponent, spell_name, action.extra.get("slot_level", 0), state)
        elif action.kind == "call_lightning_bolt":
            if not char.action_used:
                effect = _find_effect(char, "CallLightning")
                if effect is not None:
                    char.action_used = True
                    _resolve_call_lightning_bolt(char, opponent, int(effect.extra.get("slot_level", 3)), state)
        elif action.kind == "spiritual_weapon_attack":
            _do_spiritual_weapon_attack(char, opponent, state)
        elif action.kind == "flurry":
            _do_flurry(char, opponent, state)
        elif action.kind == "martial_arts_strike":
            _do_martial_arts_strike(char, opponent, state)
        elif action.kind == "cunning_hide":
            _do_cunning_hide(char, state)
        elif action.kind == "action_surge":
            _do_action_surge(char, opponent, action, state, decisions)
        elif action.kind == "second_wind":
            _do_second_wind_action(char, state)
        elif action.kind == "patient_defense":
            _do_patient_defense(char, state)
        elif action.kind == "adrenaline_rush":
            _do_adrenaline_rush(char, opponent, state)
        elif action.kind == "vow_of_enmity":
            _do_vow_of_enmity(char, state)
        elif action.kind == "hunters_mark":
            _do_hunters_mark(char, state)
        elif action.kind == "heroic_inspiration":
            _do_heroic_inspiration(char, state)
        elif action.kind == "large_form":
            _do_large_form(char, state)
        elif action.kind == "eldritch_blast":
            if not char.action_used:
                _do_eldritch_blast(char, opponent, state)
        elif action.kind == "armor_of_agathys":
            _do_armor_of_agathys(char, state)
        elif action.kind == "hex":
            _do_hex(char, state)
        elif action.kind == "breath_weapon":
            if not char.action_used:
                _do_breath_weapon(char, opponent, state)
        elif action.kind == "frenzy_attack":
            _do_frenzy_attack(char, opponent, state)
        elif action.kind == "open_hand_flurry":
            _do_open_hand_flurry(char, opponent, state)
        elif action.kind == "shadow_arts":
            _do_shadow_arts(char, state)
        elif action.kind == "fast_hands":
            _do_fast_hands(char, state)
        elif action.kind == "steady_aim":
            _do_steady_aim(char, state)
        elif action.kind == "booming_blade":
            if not char.action_used:
                _do_booming_blade(char, opponent, state)
        elif action.kind == "bladesong":
            _do_bladesong(char, state)
        elif action.kind == "hexblade_curse":
            _do_hexblade_curse(char, opponent, state)
        elif action.kind == "sacred_weapon":
            _do_sacred_weapon(char, state)
        elif action.kind == "blade_flourish":
            _do_blade_flourish(char, opponent, state)
        elif action.kind == "war_magic_attack":
            _do_war_magic_attack(char, opponent, state)
        elif action.kind == "shadow_step":
            _do_shadow_step(char, state)
        elif action.kind == "wholeness_of_body":
            _do_wholeness_of_body(char, state)

    char.end_turn()
    _tick_stunning_strike_expiry(char, state)


def _log_start_of_turn_status(char: Character, state: CombatState) -> None:
    """Log STATUS lines for effects that will expire at start of turn."""
    for e in char.active_effects:
        if e.end_trigger == "start_of_turn":
            if e.name == "Frightened":
                state.log(f"STATUS   {char.name}: frightened expires")
            elif e.name == "Sapped":
                state.log(f"STATUS   {char.name}: Sap expires")
            elif e.name == "Reckless Attack":
                pass  # Don't log reckless expiry (it's re-applied each turn)
            elif e.name == "Hidden":
                pass
            elif e.name == "Fast Hands Help":
                pass
            elif e.name == "Steady Aim":
                pass
            elif e.name == "Shield Spell":
                state.log(f"STATUS   {char.name}: Shield expires")
            else:
                state.log(f"STATUS   {char.name}: {e.name} expires")
        elif e.duration is not None and e.duration <= 1:
            if e.name == "Rage":
                pass  # Rage doesn't normally expire mid-combat in our sim
            elif e.name == "Frightened":
                state.log(f"STATUS   {char.name}: frightened expires")
            else:
                state.log(f"STATUS   {char.name}: {e.name} expires")


def _tick_stunning_strike_expiry(source_char: Character, state: CombatState) -> None:
    """Expire Stunning Strike at the end of the source monk's next turn."""
    for target in (state.combatant_a, state.combatant_b):
        to_remove = []
        for e in target.active_effects:
            if e.name != "Stunning Strike":
                continue
            if e.extra.get("source") != source_char.name:
                continue
            remaining = int(e.extra.get("remaining_source_turn_ends", 0)) - 1
            e.extra["remaining_source_turn_ends"] = remaining
            if remaining <= 0:
                to_remove.append(e)
        for e in to_remove:
            target.active_effects.remove(e)
            if Condition.STUNNED in target.conditions:
                target.conditions.discard(Condition.STUNNED)
                state.log(f"STATUS   {target.name}: stunned expires")



# ---------------------------------------------------------------------------
# Individual action handlers
# ---------------------------------------------------------------------------

def _do_rage(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    res = char.resources.get("rage")
    if not res or not res.available:
        return
    res.spend()
    label = _pad_label("BONUS")
    if "bear_totem_spirit" in char.features:
        apply_bear_totem_rage(char)
        state.log(f"{label}Rage → active (Bear Totem — resist all)")
    else:
        apply_rage(char)
        state.log(f"{label}Rage → active")
    char.bonus_action_used = True


def _do_reckless(char: Character, state: CombatState) -> None:
    apply_reckless_attack(char)
    label = _pad_label("FREE")
    state.log(f"{label}Reckless → adv on attacks, enemies adv vs you")


def _do_move(char: Character, opponent: Character, state: CombatState) -> None:
    if state.phase == CombatPhase.RANGED:
        return
    if state.distance <= 5:
        return
    move = min(char.movement_remaining, state.distance - 5)
    if move > 0:
        state.distance -= move
        char.movement_remaining -= move
        char.has_moved = True
        state.log(f"  {char.name} moves {move} ft closer (distance: {state.distance} ft)")


def _scale_dice_count(dice_str: str, multiplier: int) -> str:
    match = re.match(r"(\d+)(d\d+.*)", dice_str)
    if not match:
        return dice_str
    return f"{int(match.group(1)) * multiplier}{match.group(2)}"


def _add_upcast_dice(base_dice: str, upcast_dice: str, extra_levels: int) -> str:
    if extra_levels <= 0:
        return base_dice

    match_base = re.match(r"(\d+)(d\d+)(.*)", base_dice)
    match_up = re.match(r"(\d+)(d\d+)(.*)", upcast_dice)
    if not match_base or not match_up:
        return base_dice
    if match_base.group(2) != match_up.group(2) or match_base.group(3) or match_up.group(3):
        return base_dice

    base_count = int(match_base.group(1))
    up_count = int(match_up.group(1))
    return f"{base_count + up_count * extra_levels}{match_base.group(2)}"


def _normalize_save_ability(save_ability: str) -> str:
    return {
        "strength": "str",
        "dexterity": "dex",
        "constitution": "con",
        "intelligence": "int",
        "wisdom": "wis",
        "charisma": "cha",
    }.get(save_ability, save_ability)


def _saving_throw_total(char: Character, ability: str) -> int:
    return d20() + char.saving_throw_total(ability)


def _resolve_call_lightning_bolt(
    char: Character,
    opponent: Character,
    slot_level: int,
    state: CombatState,
) -> int:
    dice_str = _add_upcast_dice("3d10", "1d10", max(0, slot_level - 3))
    dc = char.spell_save_dc
    save_roll = _saving_throw_total(opponent, "dex")
    result = eval_dice(dice_str)
    damage = result.total
    resolved_damage, save_succeeds, has_evasion = resolve_save_damage(
        opponent,
        "dex",
        save_roll,
        dc,
        damage,
        half_on_save=True,
    )
    actual = opponent.take_damage(resolved_damage, DamageType.LIGHTNING, state)
    outcome = "saves" if save_succeeds else "fails"
    evasion_suffix = f" · Evasion → {resolved_damage} dmg" if has_evasion else ""
    state.log(
        f"  [{char.name}] Call Lightning bolt → {actual} lightning"
        f" ({outcome} {save_roll}/DC {dc}){evasion_suffix} [{opponent.current_hp}/{opponent.max_hp} HP]"
    )
    return actual


def _spell_dc(caster: Character) -> int:
    """8 + proficiency + spellcasting mod."""
    return 8 + caster.proficiency_bonus + caster.spellcasting_mod


def _apply_polymorph(caster: Character, target: Character, spell: SpellData, spell_dc: int, state: CombatState) -> None:
    """Replace target stats with CR 0 beast (rabbit)."""
    # Save original stats
    target.polymorph_original_stats = {
        "max_hp": target.max_hp,
        "current_hp": target.current_hp,
        "ac": target.ac,
        "str": target.ability_scores.strength,
        "dex": target.ability_scores.dexterity,
        "con": target.ability_scores.constitution,
    }
    # Apply CR 0 beast stats (rabbit)
    target.max_hp = 3
    target.current_hp = 3
    target.ac = 13
    target.ability_scores.strength = 2
    target.ability_scores.dexterity = 15
    target.ability_scores.constitution = 8
    target.conditions.add(Condition.POLYMORPHED)
    target.active_effects.append(ActiveEffect(
        name="Polymorphed",
        source=spell.name,
        extra={"dc": spell_dc, "original_hp": target.polymorph_original_stats["current_hp"]},
        duration=100,
    ))
    state.log(f"  {target.name} is POLYMORPHED into a CR 0 beast (HP 3, AC 13)")


def _do_polymorph_attack(char: Character, opponent: Character, state: CombatState) -> None:
    """Polymorphed creature can only make one weak bite (1d3)."""
    atk_roll = d20() + 0  # no attack bonus as a bunny
    state.log(f"  {char.name} (polymorphed) bite attack: {atk_roll} vs AC {opponent.effective_ac}")
    if atk_roll >= opponent.effective_ac:
        dmg = eval_dice("1d3").total
        actual = opponent.take_damage(dmg, DamageType.PIERCING, state)
        state.log(f"  {char.name} (polymorphed) bites for {actual} damage [{opponent.current_hp}/{opponent.max_hp} HP]")
    else:
        state.log(f"  {char.name} (polymorphed) bite misses")


def _apply_wish(caster: Character, target: Character, spell: SpellData, state: CombatState) -> None:
    """Wish: replicate the best available spell up to replicate_slot level."""
    best_spell = None
    best_avg = 0
    for spell_name in caster.spells_known:
        s = get_spell(spell_name)
        if s and s.level <= spell.replicate_slot and s.damage_dice and s.level > 0:
            try:
                avg = eval_dice(s.damage_dice).total
                if avg > best_avg:
                    best_avg = avg
                    best_spell = s
            except Exception:
                pass
    if best_spell:
        state.log(f"  WISH — {caster.name} replicates {best_spell.name} (free, slot {spell.replicate_slot})")
        _cast_spell_on_target(caster, target, best_spell, spell.replicate_slot, state)
    else:
        state.log(f"  WISH — {caster.name}: no suitable spell found to replicate")


def _cast_spell_on_target(
    caster: Character, target: Character, spell: SpellData, slot_level: int, state: CombatState,
    *, free: bool = False,
) -> None:
    """Cast a spell directly (used by Wish — no slot consumption if free=True)."""
    if not free and slot_level > 0:
        caster.spend_spell_slot(slot_level)

    dice_str = spell.damage_dice
    if not dice_str:
        return

    if slot_level > spell.level and spell.upcast_dice:
        dice_str = _add_upcast_dice(dice_str, spell.upcast_dice, slot_level - spell.level)

    if spell.attack_type == "spell_attack":
        from sim.actions import resolve_spell_attack
        resolve_spell_attack(
            caster, target, dice_str,
            spell.damage_type or DamageType.FORCE,
            spell.name, state,
        )
    elif spell.attack_type in ("save", "none"):
        if spell.attack_type == "save":
            from sim.actions import resolve_spell_save
            result = resolve_spell_save(
                caster, target, dice_str,
                spell.damage_type or DamageType.FORCE,
                spell.name,
                _normalize_save_ability(spell.save_ability),
                state, spell.half_on_save,
                return_details=True,
            )
            actual, save_succeeded, _, _ = result
            _apply_spell_effect(caster, target, spell, save_succeeded, state)
        else:
            result = eval_dice(dice_str)
            actual = target.take_damage(result.total, spell.damage_type or DamageType.FORCE, state)
            _apply_spell_effect(caster, target, spell, False, state)


def _apply_spell_effect(
    caster: Character, target: Character, spell: SpellData,
    save_succeeded: bool, state: CombatState,
) -> None:
    """Apply special spell effects beyond damage."""
    if not spell.effect and not spell.instant_kill_threshold:
        return

    spell_dc = _spell_dc(caster)

    # Instant kill threshold (Power Word Kill — no effect field needed)
    if spell.instant_kill_threshold > 0:
        if target.current_hp <= spell.instant_kill_threshold:
            state.log(f"  POWER WORD KILL — {target.name} has {target.current_hp} HP ≤ {spell.instant_kill_threshold} → INSTANT DEATH")
            target.current_hp = 0
        else:
            state.log(f"  Power Word Kill — {target.name} has {target.current_hp} HP > {spell.instant_kill_threshold} — no effect")
        return

    if not spell.effect:
        return

    # Harm — reduce to fraction of max HP on failed save
    if spell.effect == "harm" and spell.hp_percentage_cap > 0:
        if not save_succeeded:
            new_hp = max(1, int(target.max_hp * spell.hp_percentage_cap))
            if target.current_hp > new_hp:
                target.current_hp = new_hp
                state.log(f"  Harm — {target.name} reduced to {new_hp} HP ({int(spell.hp_percentage_cap*100)}% of {target.max_hp})")
        return  # damage already handled by normal save path

    # Paralyzed (Hold Monster)
    if spell.effect == "paralyze" and not save_succeeded:
        target.conditions.add(Condition.PARALYZED)
        target.active_effects.append(ActiveEffect(
            name="Paralyzed",
            source=spell.name,
            extra={"dc": spell_dc},
            duration=None,
        ))
        state.log(f"  {target.name} is PARALYZED (Hold Monster)")

    # Banishment / Forcecage
    elif spell.effect == "banishment" and not save_succeeded:
        target.conditions.add(Condition.BANISHED)
        target.active_effects.append(ActiveEffect(
            name="Banished",
            source=spell.name,
            extra={"dc": spell_dc, "caster": caster.name},
            duration=10,
        ))
        state.log(f"  {target.name} is BANISHED")

    # Polymorph / True Polymorph
    elif spell.effect == "polymorph" and not save_succeeded:
        _apply_polymorph(caster, target, spell, spell_dc, state)

    # Power Word Stun (no initial save)
    elif spell.effect == "stun_no_save":
        target.conditions.add(Condition.STUNNED)
        target.active_effects.append(ActiveEffect(
            name="Stunned",
            source=spell.name,
            extra={"dc": spell_dc},
            duration=None,
        ))
        state.log(f"  {target.name} is STUNNED (Power Word Stun) — CON save DC {spell_dc} each turn to end")

    # Power Word Pain
    elif spell.effect == "pain":
        if target.current_hp <= 100:
            if not save_succeeded:
                target.conditions.add(Condition.PAIN)
                state.log(f"  {target.name} is wracked with PAIN (Power Word Pain)")
        else:
            state.log(f"  Power Word Pain — {target.name} has {target.current_hp} HP > 100 — no effect")

    # Greater Invisibility (self)
    elif spell.effect == "greater_invisibility":
        caster.conditions.add(Condition.GREATER_INVISIBLE)
        caster.active_effects.append(ActiveEffect(
            name="GreaterInvisible",
            source=spell.name,
            extra={},
            duration=10,
        ))
        state.log(f"  {caster.name} is GREATER INVISIBLE — advantage on attacks, disadvantage against")

    # Time Stop — extra turns
    elif spell.effect == "extra_turns":
        n = eval_dice("1d4").total + 1
        caster.extra_turns_remaining += n
        state.log(f"  TIME STOP — {caster.name} gains {n} extra turns")

    # Wish — replicate best available spell
    elif spell.effect == "wish" and spell.replicate_slot > 0:
        _apply_wish(caster, target, spell, state)

    # Disintegrate — no stabilize if reduced to 0
    elif spell.effect == "disintegrate":
        if target.current_hp <= 0:
            state.log(f"  {target.name} is DISINTEGRATED — destroyed utterly")


def _do_cast_spell(
    char: Character,
    opponent: Character,
    spell_name: str,
    slot_level: int,
    state: CombatState,
) -> None:
    """Resolve a spell cast. slot_level=0 for cantrips."""
    label = f"  [{char.name}] CAST "
    spell = get_spell(spell_name)
    if spell is None:
        state.log(f"{label}{spell_name} — UNKNOWN SPELL")
        return

    if slot_level > 0:
        if not char.spend_spell_slot(slot_level):
            state.log(f"{label}{spell_name} — NO SLOT AVAILABLE (level {slot_level})")
            return

    if spell.name == "shillelagh" and slot_level == 0:
        char.bonus_action_used = True
        existing = _find_effect(char, "Shillelagh")
        if existing is not None:
            char.active_effects.remove(existing)
        char.active_effects.append(ActiveEffect(
            name="Shillelagh",
            source="shillelagh",
            duration=10,
            extra={"wis_mod": char.wis_mod},
        ))
        state.log(f"  [{char.name}] Shillelagh — quarterstaff empowered (WIS to hit/dmg, 1d8)")
        return

    if spell.attack_type == "heal":
        heal_dice = _add_upcast_dice(spell.damage_dice, spell.upcast_dice, max(0, slot_level - spell.level))
        heal_result = eval_dice(heal_dice)
        heal_amount = heal_result.total + char.spellcasting_mod
        char.heal(heal_amount)
        char.bonus_action_used = True
        state.log(f"  [{char.name}] Healing Word → +{heal_amount} HP (now {char.current_hp}/{char.max_hp})")
        return

    if spell.name == "spiritual_weapon":
        char.bonus_action_used = True
        existing = _find_effect(char, "SpiritualWeapon")
        if existing is not None:
            char.active_effects.remove(existing)
        char.active_effects.append(ActiveEffect(
            name="SpiritualWeapon",
            source="spiritual_weapon",
            duration=10,
            extra={"slot_level": slot_level},
        ))
        state.log(f"{_pad_label('BONUS')}Spiritual Weapon → active (slot {slot_level})")
        return

    char.action_used = True

    if spell.name == "call_lightning":
        char.concentrate("call_lightning")
        existing = _find_effect(char, "CallLightning")
        if existing is not None:
            char.active_effects.remove(existing)
        char.active_effects.append(ActiveEffect(
            name="CallLightning",
            source="call_lightning",
            duration=10,
            extra={"slot_level": slot_level},
        ))
        state.log(f"{label}{spell_name} → active (slot {slot_level}, concentration)")
        _resolve_call_lightning_bolt(char, opponent, slot_level, state)
        return

    if spell.name == "spirit_guardians":
        char.concentrate("spirit_guardians")
        existing = _find_effect(char, "SpiritGuardiansAura")
        if existing is not None:
            char.active_effects.remove(existing)
        char.active_effects.append(ActiveEffect(
            name="SpiritGuardiansAura",
            source="spirit_guardians",
            duration=10,
            extra={"slot_level": slot_level},
        ))
        state.log(f"{label}{spell_name} → active (slot {slot_level}, concentration)")
        return

    if spell.name == "hypnotic_pattern":
        char.concentrate("hypnotic_pattern")
        dc = char.spell_save_dc
        save_roll = _saving_throw_total(opponent, "wis")
        if save_roll < dc:
            opponent.apply_condition(Condition.INCAPACITATED)
            existing = _find_effect(opponent, "HypnoticPattern")
            if existing is not None:
                opponent.active_effects.remove(existing)
            opponent.active_effects.append(ActiveEffect(
                name="HypnoticPattern",
                source="hypnotic_pattern",
                duration=10,
                end_trigger="on_damage",
            ))
            state.log(f"  [{char.name}] Hypnotic Pattern — {opponent.name} is INCAPACITATED")
        else:
            state.log(f"  [{char.name}] Hypnotic Pattern — {opponent.name} resisted ({save_roll}/DC {dc})")
        return

    if spell.concentration:
        char.concentrate(spell_name)

    dice_str = spell.damage_dice
    if not dice_str:
        slot_str = f" (slot {slot_level})" if slot_level > 0 else ""
        state.log(f"{label}{spell_name}{slot_str} (no damage)")
        # Still apply spell effects (e.g. greater_invisibility, time_stop, power word effects)
        _apply_spell_effect(char, opponent, spell, False, state)
        return

    if spell.cantrip_scaling and spell.level == 0:
        dice_str = _scale_dice_count(dice_str, cantrip_die_count(spell, char.level))
        # War Magic (Eldritch Knight L7): after casting a cantrip, allow bonus weapon attack
        if "war_magic" in char.features and char.level >= 7:
            char._war_magic_available = True

    if slot_level > spell.level and spell.upcast_dice:
        dice_str = _add_upcast_dice(dice_str, spell.upcast_dice, slot_level - spell.level)

    if spell.name == "toll_the_dead" and spell.missing_hp_dice and opponent.current_hp < opponent.max_hp:
        count = cantrip_die_count(spell, char.level) if spell.cantrip_scaling else 1
        match = re.match(r"\d+(d\d+.*)", spell.missing_hp_dice)
        if match:
            dice_str = f"{count}{match.group(1)}"

    if spell.attack_type == "spell_attack":
        attack_count = spell.extra_attacks
        if spell.name == "scorching_ray" and slot_level > spell.level:
            attack_count += slot_level - spell.level
        for _ in range(attack_count):
            if not opponent.is_alive:
                break
            hit = resolve_spell_attack(
                char,
                opponent,
                dice_str,
                spell.damage_type or DamageType.FORCE,
                spell_name,
                state,
            )
            if hit and spell.grants_advantage:
                existing = _find_effect(opponent, "GuidingBoltMarked")
                if existing is not None:
                    opponent.active_effects.remove(existing)
                opponent.active_effects.append(ActiveEffect(
                    name="GuidingBoltMarked",
                    source="guiding_bolt",
                    duration=2,
                    grants_advantage_to_enemies=True,
                ))
        return

    if spell.attack_type == "save":
        result = resolve_spell_save(
            char,
            opponent,
            dice_str,
            spell.damage_type or DamageType.FORCE,
            spell_name,
            _normalize_save_ability(spell.save_ability),
            state,
            spell.half_on_save,
            return_details=True,
        )
        actual, save_succeeds, _, _ = result
        if spell.name == "vicious_mockery" and not save_succeeds:
            existing = _find_effect(opponent, "ViciousMockery")
            if existing is not None:
                opponent.active_effects.remove(existing)
            opponent.active_effects.append(ActiveEffect(
                name="ViciousMockery",
                source="vicious_mockery",
                duration=1,
                disadvantage_on_attacks=True,
                end_trigger="on_attack",
            ))
            state.log(f"  [{char.name}] Vicious Mockery — {opponent.name} has disadvantage on next attack")
        # Apply special spell effects (paralyze, banishment, polymorph, harm, etc.)
        if opponent.is_alive or spell.effect == "disintegrate":
            _apply_spell_effect(char, opponent, spell, save_succeeds, state)
        return

    if spell.attack_type == "none":
        dart_count = spell.extra_attacks + max(0, slot_level - spell.level)
        damage_type = spell.damage_type or DamageType.FORCE
        total_damage = 0
        parts: list[str] = []
        for _ in range(dart_count):
            result = eval_dice(dice_str)
            actual = opponent.take_damage(result.total, damage_type, state)
            total_damage += actual
            parts.append(str(actual))
            if not opponent.is_alive:
                break
        # Apply no-damage effects (greater_invisibility, time_stop, wish) even if dice_str is empty
        _apply_spell_effect(char, opponent, spell, False, state)
        if total_damage > 0:
            slot_str = f" (slot {slot_level})" if slot_level > 0 else " (cantrip)"
            detail = " · ".join(parts)
            state.log(f"{label}{spell_name}{slot_str} → {detail} = {total_damage} {damage_type.name.lower()}")


def _do_ranged_attack(
    char: Character, opponent: Character, action: TurnAction, state: CombatState
) -> None:
    weapon = _find_weapon(char, action.weapon)
    if not weapon:
        return

    if state.phase == CombatPhase.MELEE and state.distance <= 5:
        state.log(f"  {char.name} can't use ranged in melee")
        return

    check_distance = state.starting_distance if state.phase == CombatPhase.RANGED else state.distance

    eff_range = weapon.effective_range
    if weapon.is_thrown and weapon.thrown_range_normal:
        eff_range = weapon.thrown_range_normal
    if check_distance > eff_range:
        state.log(f"  {char.name} can't reach with {weapon.name} (range {eff_range}, distance {check_distance})")
        return

    char.action_used = True
    is_thrown = weapon.is_thrown and not weapon.is_ranged
    num_attacks = 1 + char.extra_attacks

    for i in range(num_attacks):
        if not opponent.is_alive:
            break
        resolve_attack(char, opponent, weapon, state, is_thrown=is_thrown, attack_label="ACTION")

    _do_move(char, opponent, state)


def _do_melee_attack(
    char: Character, opponent: Character, action: TurnAction, state: CombatState
) -> None:
    if state.distance > 5:
        _do_move(char, opponent, state)
        if state.distance > 5:
            rw = char.best_ranged_weapon()
            if rw and state.distance <= rw.effective_range:
                char.action_used = True
                resolve_attack(char, opponent, rw, state, is_thrown=rw.is_thrown, attack_label="ACTION")
            return

    weapon = _find_weapon(char, action.weapon)
    if not weapon:
        weapon = char.best_melee_weapon()
    if not weapon:
        char.action_used = True
        resolve_attack(char, opponent, _unarmed_weapon(char), state, is_unarmed=True, attack_label="ACTION")
        return

    char.action_used = True
    num_attacks = 1 + char.extra_attacks

    # Dread Ambusher (Gloom Stalker): extra attack on first turn of combat
    dread_ambusher_active = (
        "dread_ambusher" in char.features
        and not char.gloom_stalker_ambush_used
        and state.round_number == 1
    )
    if dread_ambusher_active:
        num_attacks += 1
        char.gloom_stalker_ambush_used = True
        state.log(f"  [{char.name}] Dread Ambusher — +1 attack this turn!")

    for i in range(num_attacks):
        if not opponent.is_alive:
            break
        result = resolve_attack(char, opponent, weapon, state, attack_label="ACTION")
        if result.hit and char.is_concentrating("Hex"):
            _apply_hex(char, opponent, state)
        # Dread Ambusher: +1d8 on first attack hit
        if dread_ambusher_active and i == 0 and result.hit:
            bonus_dmg = eval_dice("1d8").total
            actual_bonus = opponent.take_damage(bonus_dmg, weapon.damage_type, state)
            state.log(f"  [{char.name}] Dread Ambusher +1d8 = {actual_bonus} bonus damage")
            dread_ambusher_active = False  # only first hit

    if opponent.is_alive:
        _try_nick_extra_attack(char, opponent, weapon, state)


def _do_flurry(char: Character, opponent: Character, state: CombatState) -> None:
    if char.bonus_action_used or state.distance > 5:
        return
    res = char.resources.get("focus_points")
    if not res or not res.available:
        return
    res.spend()
    char.bonus_action_used = True
    label = _pad_label("BONUS")
    state.log(f"{label}Flurry of Blows")
    for _ in range(2):
        if not opponent.is_alive:
            break
        resolve_attack(char, opponent, _unarmed_weapon(char), state, is_unarmed=True, attack_label="BONUS")


def _do_martial_arts_strike(char: Character, opponent: Character, state: CombatState) -> None:
    if char.bonus_action_used or state.distance > 5:
        return
    char.bonus_action_used = True
    resolve_attack(char, opponent, _unarmed_weapon(char), state, is_unarmed=True, attack_label="BONUS")


def _do_cunning_hide(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    from sim.dice import d20 as roll_d20
    hide_roll = roll_d20() + char.dex_mod + char.proficiency_bonus
    dc = 10 + state.opponent_of(char).wis_mod
    label = _pad_label("BONUS")
    if hide_roll >= dc:
        char.active_effects.append(ActiveEffect(
            name="Hidden",
            source="cunning_action",
            end_trigger="start_of_turn",
            advantage_on_attacks=True,
        ))
        state.log(f"{label}Hide → success (roll {hide_roll}/DC {dc})")
    else:
        state.log(f"{label}Hide → fail (roll {hide_roll}/DC {dc})")
    char.bonus_action_used = True


def _do_action_surge(
    char: Character, opponent: Character, action: TurnAction,
    state: CombatState, decisions: list[TurnAction]
) -> None:
    res = char.resources.get("action_surge")
    if not res or not res.available or not char.action_used:
        return
    res.spend()
    char.action_used = False
    label = _pad_label("SURGE")
    state.log(f"{label}Action Surge!")

    if state.distance > 5:
        _do_move(char, opponent, state)

    from sim.tactics import _pick_melee_weapon
    mw = _pick_melee_weapon(char) or char.best_melee_weapon()
    if state.distance <= 5 and mw:
        num_attacks = 1 + char.extra_attacks
        for _ in range(num_attacks):
            if not opponent.is_alive:
                break
            resolve_attack(char, opponent, mw, state, attack_label="SURGE")
        if opponent.is_alive:
            _try_nick_extra_attack(char, opponent, mw, state)
    else:
        rw = char.best_ranged_weapon()
        if rw and state.distance <= rw.effective_range:
            num_attacks = 1 + char.extra_attacks
            for _ in range(num_attacks):
                if not opponent.is_alive:
                    break
                resolve_attack(char, opponent, rw, state, is_thrown=rw.is_thrown, attack_label="SURGE")
    char.action_used = True


def _do_second_wind_action(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    do_second_wind(char, state)


def _do_patient_defense(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    res = char.resources.get("focus_points")
    if not res or not res.available:
        return
    res.spend()
    char.bonus_action_used = True
    do_dodge(char, state)
    label = _pad_label("BONUS")
    state.log(f"{label}Patient Defense (Dodge)")


def _do_adrenaline_rush(char: Character, opponent: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    res = char.resources.get("adrenaline_rush")
    if not res or not res.available:
        return
    res.spend()
    char.bonus_action_used = True
    temp_hp = char.proficiency_bonus
    char.gain_temp_hp(temp_hp)
    label = _pad_label("BONUS")
    if state.phase == CombatPhase.RANGED:
        state.log(f"{label}Adrenaline Rush → +{temp_hp} temp HP")
        return
    char.movement_remaining += char.speed
    state.log(f"{label}Adrenaline Rush → Dash + {temp_hp} temp HP")
    if state.distance > 5:
        move = min(char.movement_remaining, state.distance - 5)
        if move > 0:
            state.distance -= move
            char.movement_remaining -= move
            char.has_moved = True
            state.log(f"  {char.name} rushes {move} ft closer (distance: {state.distance} ft)")


def _do_vow_of_enmity(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    res = char.resources.get("channel_divinity")
    if not res or not res.available:
        return
    res.spend()
    char.bonus_action_used = True
    char.vow_of_enmity_active = True
    label = _pad_label("BONUS")
    state.log(f"{label}Vow of Enmity → adv on all attacks")


def _do_hunters_mark(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    res = char.resources.get("hunters_mark")
    if not res or not res.available:
        return
    if char.hunters_mark_active:
        return
    res.spend()
    char.bonus_action_used = True
    char.hunters_mark_active = True
    label = _pad_label("BONUS")
    state.log(f"{label}Hunter's Mark → active")


def _do_heroic_inspiration(char: Character, state: CombatState) -> None:
    res = char.resources.get("heroic_inspiration")
    if res and res.available:
        char._use_heroic_inspiration = True
        label = _pad_label("FREE")
        state.log(f"{label}Heroic Inspiration → queued for next attack")


def _do_large_form(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    if any(e.name == "Large Form" for e in char.active_effects):
        return
    char.bonus_action_used = True
    char.active_effects.append(ActiveEffect(
        name="Large Form",
        source="goliath",
        duration=char.proficiency_bonus,
    ))
    char.speed += 10
    char.movement_remaining += 10
    label = _pad_label("BONUS")
    state.log(f"{label}Large Form → +10 speed for {char.proficiency_bonus} rounds")


def _do_breath_weapon(char: Character, opponent: Character, state: CombatState) -> None:
    res = char.resources.get("breath_weapon")
    if not res or not res.available:
        return
    shape = getattr(char, "breath_weapon_shape", "cone")
    max_range = 15 if shape == "cone" else 30
    if state.distance > max_range:
        return
    res.spend()
    char.action_used = True
    dc = 8 + char.con_mod + char.proficiency_bonus
    save_roll = _saving_throw_total(opponent, "dex")
    result = eval_dice("1d10")
    damage_roll = result.total
    dmg_type = getattr(char, "breath_weapon_damage_type", DamageType.FIRE)
    label = _pad_label("ACTION")
    resolved_damage, save_succeeds, has_evasion = resolve_save_damage(
        opponent,
        "dex",
        save_roll,
        dc,
        damage_roll,
        half_on_save=True,
    )
    actual = opponent.take_damage(resolved_damage, dmg_type, state)
    outcome = "saves" if save_succeeds else "fails"
    evasion_suffix = f" · Evasion → {resolved_damage} dmg" if has_evasion else ""
    state.log(
        f"{label}Breath Weapon: {opponent.name} {outcome} ({save_roll}/DC {dc})"
        f" · {actual} dmg{evasion_suffix} [{opponent.current_hp}/{opponent.max_hp} HP]"
    )


def _do_frenzy_attack(char: Character, opponent: Character, state: CombatState) -> None:
    if char.bonus_action_used or not char.is_raging or state.distance > 5:
        return
    char.bonus_action_used = True
    mw = char.best_melee_weapon()
    if not mw:
        return
    resolve_attack(char, opponent, mw, state, attack_label="BONUS")


def _do_open_hand_flurry(char: Character, opponent: Character, state: CombatState) -> None:
    if char.bonus_action_used or state.distance > 5:
        return
    res = char.resources.get("focus_points")
    if not res or not res.available:
        return
    res.spend()
    char.bonus_action_used = True
    label = _pad_label("BONUS")
    state.log(f"{label}Flurry of Blows (Open Hand)")
    for i in range(2):
        if not opponent.is_alive:
            break
        result = resolve_attack(char, opponent, _unarmed_weapon(char), state, is_unarmed=True, attack_label="BONUS")
        if result.hit:
            opponent.conditions.add(Condition.PRONE)
            state.log(f"STATUS   {opponent.name}: knocked prone (Open Hand)")


def _do_shadow_arts(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    if any(e.name == "Shadow Darkness" for e in char.active_effects):
        return
    res = char.resources.get("focus_points")
    if not res or res.current < 2:
        return
    res.spend(2)
    char.bonus_action_used = True
    char.active_effects.append(ActiveEffect(
        name="Shadow Darkness",
        source="shadow_arts",
        duration=10,
    ))
    label = _pad_label("BONUS")
    state.log(f"{label}Darkness (Shadow Arts) → active")


def _do_fast_hands(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    char.bonus_action_used = True
    char.active_effects.append(ActiveEffect(
        name="Fast Hands Help",
        source="fast_hands",
        end_trigger="start_of_turn",
        advantage_on_attacks=True,
    ))
    label = _pad_label("BONUS")
    state.log(f"{label}Fast Hands (Help) → adv on next attack")


def _do_steady_aim(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    char.bonus_action_used = True
    char.movement_remaining = 0
    char.active_effects.append(ActiveEffect(
        name="Steady Aim",
        source="steady_aim",
        end_trigger="start_of_turn",
        advantage_on_attacks=True,
    ))
    label = _pad_label("BONUS")
    state.log(f"{label}Steady Aim → adv, speed 0")


def _do_booming_blade(char: Character, opponent: Character, state: CombatState) -> None:
    if state.distance > 5:
        _do_move(char, opponent, state)
        if state.distance > 5:
            return
    mw = char.best_melee_weapon()
    if not mw:
        return
    char.action_used = True
    result = resolve_attack(char, opponent, mw, state, attack_label="ACTION")
    if result.hit:
        from sim.dice import d20 as _d20
        if _d20() >= 11:
            boom_result = eval_dice("1d8")
            actual = opponent.take_damage(boom_result.total, DamageType.THUNDER, state)
            label = _pad_label("FREE")
            state.log(f"{label}Booming Blade detonates · [{boom_result.rolls[0]}]={actual} thunder [{opponent.current_hp}/{opponent.max_hp} HP]")


# ---------------------------------------------------------------------------
# New subclass action handlers
# ---------------------------------------------------------------------------

def _do_bladesong(char: Character, state: CombatState) -> None:
    """Activate Bladesong as a bonus action (Bladesinger Wizard)."""
    if char.bonus_action_used:
        return
    if any(e.name == "Bladesong" for e in char.active_effects):
        return
    res = char.resources.get("bladesong")
    if not res or not res.available:
        return
    res.spend()
    char.bonus_action_used = True
    char.active_effects.append(ActiveEffect(
        name="Bladesong",
        source="bladesong",
        duration=10,
    ))
    char.bladesong_active = True
    label = _pad_label("BONUS")
    state.log(f"{label}Bladesong → active (+{char.int_mod} AC, concentration protection)")


def _do_hexblade_curse(char: Character, opponent: Character, state: CombatState) -> None:
    """Apply Hexblade's Curse as a bonus action."""
    if char.bonus_action_used:
        return
    if char.hexblade_curse_target is not None:
        return
    char.bonus_action_used = True
    char.hexblade_curse_target = opponent.name
    label = _pad_label("BONUS")
    state.log(f"{label}Hexblade's Curse → {opponent.name} cursed (crit 19-20, +PB dmg, heal on kill)")


def _do_sacred_weapon(char: Character, state: CombatState) -> None:
    """Activate Sacred Weapon as a bonus action (Devotion Paladin)."""
    if char.bonus_action_used:
        return
    if any(e.name == "SacredWeapon" for e in char.active_effects):
        return
    res = char.resources.get("channel_divinity")
    if not res or not res.available:
        return
    res.spend()
    char.bonus_action_used = True
    char.active_effects.append(ActiveEffect(
        name="SacredWeapon",
        source="sacred_weapon",
        duration=10,
        extra={"cha_mod": char.cha_mod},
    ))
    label = _pad_label("BONUS")
    state.log(f"{label}Sacred Weapon → active (+{char.cha_mod} to attack rolls)")


def _do_blade_flourish(char: Character, opponent: Character, state: CombatState) -> None:
    """Blade Flourish (Swords Bard): add bardic inspiration die to damage and AC."""
    if char._blade_flourish_used_this_turn:
        return
    res = char.resources.get("bardic_inspiration")
    if not res or not res.available:
        return
    # Determine die size by level
    if char.level >= 15:
        die = "1d12"
    elif char.level >= 10:
        die = "1d10"
    elif char.level >= 5:
        die = "1d8"
    else:
        die = "1d6"
    res.spend()
    char._blade_flourish_used_this_turn = True
    roll_result = eval_dice(die).total
    # Defensive Flourish: add to AC until next turn
    char.active_effects.append(ActiveEffect(
        name="BladeFlourish",
        source="blade_flourish",
        ac_bonus=roll_result,
        end_trigger="start_of_turn",
    ))
    label = _pad_label("FREE")
    state.log(f"{label}Blade Flourish ({die}={roll_result}) → +{roll_result} dmg on next hit, +{roll_result} AC until next turn")


def _do_war_magic_attack(char: Character, opponent: Character, state: CombatState) -> None:
    """War Magic: weapon attack as bonus action after casting a cantrip (EK L7+)."""
    if char.bonus_action_used:
        return
    if not char._war_magic_available:
        return
    if "war_magic" not in char.features:
        return
    if state.distance > 5:
        return
    char.bonus_action_used = True
    char._war_magic_available = False
    mw = char.best_melee_weapon()
    if not mw:
        return
    label = _pad_label("BONUS")
    state.log(f"{label}War Magic → bonus weapon attack")
    resolve_attack(char, opponent, mw, state, attack_label="BONUS")


def _do_shadow_step(char: Character, state: CombatState) -> None:
    """Shadow Step (Shadow Monk L6): teleport and gain advantage on next attack."""
    if char._shadow_step_used or char.bonus_action_used:
        return
    char.bonus_action_used = True
    char._shadow_step_used = True
    char.active_effects.append(ActiveEffect(
        name="ShadowStep",
        source="shadow_step",
        advantage_on_attacks=True,
        end_trigger="on_attack",
    ))
    label = _pad_label("BONUS")
    state.log(f"{label}Shadow Step → advantage on next attack this turn")


def _do_wholeness_of_body(char: Character, state: CombatState) -> None:
    """Wholeness of Body (Open Hand Monk L6): heal 3 × monk level as bonus action."""
    if char.bonus_action_used:
        return
    res = char.resources.get("wholeness_of_body")
    if not res or not res.available:
        return
    res.spend()
    char.bonus_action_used = True
    heal_amount = 3 * char.level
    actual = char.heal(heal_amount)
    label = _pad_label("BONUS")
    state.log(f"{label}Wholeness of Body → healed {actual} HP [{char.current_hp}/{char.max_hp}]")


# ---------------------------------------------------------------------------
# Spell action handlers
# ---------------------------------------------------------------------------

def _do_eldritch_blast(char: Character, opponent: Character, state: CombatState) -> None:
    if char.action_used:
        return
    char.action_used = True

    bonus = char.cha_mod if "agonizing_blast" in getattr(char, "invocations", []) else 0
    beam_count = 2 if (char.level >= 5 or "eldritch_blast_upgrade" in char.features) else 1

    for beam_idx in range(beam_count):
        if not opponent.is_alive:
            break

        adv = any(e.advantage_on_attacks for e in char.active_effects)
        disadv = (
            Condition.FRIGHTENED in char.conditions
            or opponent.is_dodging
            or any(e.disadvantage_on_attacks for e in char.active_effects)
            or any(e.name == "Shadow Darkness" for e in opponent.active_effects)
        )

        from sim.dice import d20_detail
        d20r = d20_detail(advantage=adv, disadvantage=disadv)
        attack_roll = d20r.chosen + char.spell_attack_bonus
        target_ac = opponent.effective_ac
        label = _pad_label("ACTION")
        d20_str = f"d20={d20r.chosen}"
        if d20r.advantage and d20r.other is not None:
            d20_str = f"d20={d20r.chosen}↑{d20r.other}"
        elif d20r.disadvantage and d20r.other is not None:
            d20_str = f"d20={d20r.chosen}↓{d20r.other}"

        beam_label = "Eldritch Blast" if beam_count == 1 else f"Eldritch Blast (Beam {beam_idx + 1})"

        hit = attack_roll >= target_ac
        if hit:
            dmg_result = eval_dice("1d10")
            dmg = dmg_result.total + bonus
            actual = opponent.take_attack_damage([(dmg, DamageType.FORCE)], state, is_attack=True)
            hex_dmg = _apply_hex(char, opponent, state) if char.is_concentrating("Hex") else 0
            hex_str = f" +Hex [{hex_dmg}]" if hex_dmg else ""
            state.log(
                f"{label}{beam_label} {d20_str} → HIT ({attack_roll}/{target_ac})"
                f" · [{dmg_result.rolls[0]}]+{bonus}={actual} force{hex_str}"
                f" [{opponent.current_hp}/{opponent.max_hp} HP]"
            )
        else:
            state.log(f"{label}{beam_label} {d20_str} → MISS ({attack_roll}/{target_ac})")


def _apply_hex(char: Character, target: Character, state: CombatState) -> int:
    if not char.is_concentrating("Hex"):
        return 0
    result = eval_dice("1d6")
    actual = target.take_damage(result.total, DamageType.NECROTIC, state)
    return actual


def _do_armor_of_agathys(char: Character, state: CombatState) -> None:
    if char.action_used:
        return
    slot_level = char.highest_available_spell_slot()
    if slot_level is None:
        return
    if any(e.name == "Armor of Agathys" for e in char.active_effects):
        return
    char.spend_spell_slot(slot_level)
    char.action_used = True
    temp_hp = 5 * slot_level
    char.gain_temp_hp(temp_hp)
    char.active_effects.append(ActiveEffect(
        name="Armor of Agathys",
        source="armor_of_agathys",
        duration=99,
    ))
    char.aoa_cold_damage = 10
    label = _pad_label("ACTION")
    state.log(f"{label}Armor of Agathys → +{temp_hp} temp HP, {temp_hp} cold retaliation")


def _apply_start_of_turn_auras(char: Character, opponent: Character, state: CombatState) -> None:
    if not opponent.is_alive or not opponent.is_concentrating("spirit_guardians"):
        return

    spell = get_spell("spirit_guardians")
    if spell is None or not spell.aura or state.distance > spell.aura_range:
        return

    aura = _find_effect(opponent, "SpiritGuardiansAura")
    slot_level = int(aura.extra.get("slot_level", spell.level)) if aura is not None else spell.level
    dice_str = spell.damage_dice
    if slot_level > spell.level and spell.upcast_dice:
        dice_str = _add_upcast_dice(dice_str, spell.upcast_dice, slot_level - spell.level)

    dc = opponent.spell_save_dc
    save_roll = _saving_throw_total(char, "wis")
    result = eval_dice(dice_str)
    damage, save_succeeds, _ = resolve_save_damage(
        char,
        "wis",
        save_roll,
        dc,
        result.total,
        half_on_save=True,
    )
    actual = char.take_damage(damage, spell.damage_type or DamageType.RADIANT, state)
    outcome = "save" if save_succeeds else "fail"
    state.log(f"{opponent.name} Spirit Guardians → {actual} radiant (WIS save {save_roll}/DC {dc} {outcome})")


def _do_spiritual_weapon_attack(char: Character, opponent: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    effect = _find_effect(char, "SpiritualWeapon")
    if effect is None:
        return

    slot_level = int(effect.extra.get("slot_level", 2))
    dice_count = 1 + max(0, (slot_level - 2) // 2)
    char.bonus_action_used = True
    resolve_spell_attack(
        char,
        opponent,
        f"{dice_count}d8",
        DamageType.FORCE,
        "Spiritual Weapon",
        state,
        damage_mod=char.spellcasting_mod,
        attack_label="BONUS",
    )


def _do_hex(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    if char.is_concentrating():
        return
    slot_level = char.highest_available_spell_slot()
    if slot_level is None:
        return
    char.spend_spell_slot(slot_level)
    char.bonus_action_used = True
    char.concentrate("Hex")
    label = _pad_label("BONUS")
    state.log(f"{label}Hex → +1d6 necrotic on each hit")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _try_nick_extra_attack(
    char: Character, opponent: Character,
    main_weapon: "Weapon", state: CombatState,
) -> None:
    if not main_weapon.mastery or main_weapon.mastery != MasteryProperty.NICK:
        return
    if char.nick_used_this_turn:
        return
    if not char.can_use_mastery(main_weapon):
        return
    from sim.models import WeaponProperty
    offhand = None
    for w in char.weapons:
        if w is not main_weapon and w.name != main_weapon.name and w.is_light and w.is_melee:
            offhand = w
            break
    if offhand is None:
        return
    char.nick_used_this_turn = True
    resolve_attack(char, opponent, offhand, state, is_nick_attack=True, attack_label="ACTION")


def _find_weapon(char: Character, name: str | None) -> Weapon | None:
    if name is None:
        return None
    for w in char.weapons:
        if w.name.lower() == name.lower():
            return w
    return None


def _unarmed_weapon(char: Character) -> "Weapon":
    from sim.models import Weapon, DamageType, WeaponProperty
    return Weapon(
        name="Unarmed Strike",
        damage_dice=char.martial_arts_die or "1",
        damage_type=DamageType.BLUDGEONING,
        properties=[],
        category="simple",
        range_normal=5,
    )
