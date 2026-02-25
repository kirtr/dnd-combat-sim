"""Combat loop: initiative, turn phases, death, distance tracking."""

from __future__ import annotations

from sim.dice import d20, eval_dice
from sim.models import Character, CombatState, Condition, ActiveEffect, DamageType, MasteryProperty
from sim.actions import resolve_attack, do_second_wind, do_dash, do_dodge
from sim.effects import apply_rage, apply_reckless_attack
from sim.tactics import TacticsEngine, TurnAction


def roll_initiative(char: Character) -> int:
    """Roll initiative for a character."""
    return d20() + char.dex_mod + char.initiative_bonus


def run_combat(
    a: Character,
    b: Character,
    tactics_a: TacticsEngine,
    tactics_b: TacticsEngine,
    *,
    starting_distance: int = 60,
    verbose: bool = False,
) -> CombatState:
    """Run a full 1v1 combat to completion. Returns the final CombatState."""
    state = CombatState(
        combatant_a=a,
        combatant_b=b,
        distance=starting_distance,
        verbose=verbose,
    )

    # Roll initiative
    init_a = roll_initiative(a)
    init_b = roll_initiative(b)
    # Tie-break: higher DEX goes first, then random
    if init_a > init_b:
        state.turn_order = [a, b]
    elif init_b > init_a:
        state.turn_order = [b, a]
    else:
        if a.dex_mod >= b.dex_mod:
            state.turn_order = [a, b]
        else:
            state.turn_order = [b, a]

    state.log(f"Initiative: {a.name}={init_a}, {b.name}={init_b}")
    state.log(f"Turn order: {state.turn_order[0].name} → {state.turn_order[1].name}")
    state.log(f"Starting distance: {state.distance} ft")

    # Combat loop
    max_rounds = 100  # safety valve
    while a.is_alive and b.is_alive and state.round_number < max_rounds:
        state.round_number += 1
        state.log(f"\n=== Round {state.round_number} ===")

        for char in state.turn_order:
            if not char.is_alive:
                continue
            opponent = state.opponent_of(char)
            tactics = tactics_a if char is a else tactics_b

            # Reset savage attacker tracking
            if hasattr(char, "_savage_used_this_turn"):
                char._savage_used_this_turn = False

            _execute_turn(char, opponent, tactics, state)

            if not opponent.is_alive:
                state.log(f"\n{opponent.name} has fallen! {char.name} wins!")
                break

    return state


def _execute_turn(
    char: Character,
    opponent: Character,
    tactics: TacticsEngine,
    state: CombatState,
) -> None:
    """Execute a single character's turn."""
    char.start_turn()
    state.log(f"\n--- {char.name}'s turn (HP: {char.current_hp}/{char.max_hp}) ---")

    decisions = tactics.decide_turn(char, state)
    action_surge_available = False

    for action in decisions:
        if not opponent.is_alive:
            break

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

    char.end_turn()


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
    apply_rage(char)
    char.bonus_action_used = True
    state.log(f"  {char.name} RAGES!")


def _do_reckless(char: Character, state: CombatState) -> None:
    apply_reckless_attack(char)
    state.log(f"  {char.name} attacks recklessly!")


def _do_move(char: Character, opponent: Character, state: CombatState) -> None:
    if state.distance <= 5:
        return
    move = min(char.movement_remaining, state.distance - 5)
    if move > 0:
        state.distance -= move
        char.movement_remaining -= move
        char.has_moved = True
        state.log(f"  {char.name} moves {move} ft closer (distance: {state.distance} ft)")


def _do_ranged_attack(
    char: Character, opponent: Character, action: TurnAction, state: CombatState
) -> None:
    weapon = _find_weapon(char, action.weapon)
    if not weapon:
        return

    # Check range
    eff_range = weapon.effective_range
    if weapon.is_thrown and weapon.thrown_range_normal:
        eff_range = weapon.thrown_range_normal
    if state.distance > eff_range:
        state.log(f"  {char.name} can't reach with {weapon.name} (range {eff_range}, distance {state.distance})")
        return

    char.action_used = True
    is_thrown = weapon.is_thrown and not weapon.is_ranged
    num_attacks = 1 + char.extra_attacks

    for i in range(num_attacks):
        if not opponent.is_alive:
            break
        resolve_attack(char, opponent, weapon, state, is_thrown=is_thrown)

    # Move remaining distance after ranged attack
    _do_move(char, opponent, state)


def _do_melee_attack(
    char: Character, opponent: Character, action: TurnAction, state: CombatState
) -> None:
    if state.distance > 5:
        # Not in melee range — try to close first
        _do_move(char, opponent, state)
        if state.distance > 5:
            # Still not in melee, try ranged instead
            rw = char.best_ranged_weapon()
            if rw and state.distance <= rw.effective_range:
                char.action_used = True
                resolve_attack(char, opponent, rw, state, is_thrown=rw.is_thrown)
            return

    weapon = _find_weapon(char, action.weapon)
    if not weapon:
        weapon = char.best_melee_weapon()
    if not weapon:
        # Unarmed strike as action
        char.action_used = True
        resolve_attack(char, opponent, _unarmed_weapon(char), state, is_unarmed=True)
        return

    char.action_used = True
    num_attacks = 1 + char.extra_attacks

    for i in range(num_attacks):
        if not opponent.is_alive:
            break
        resolve_attack(char, opponent, weapon, state)

    # Nick mastery: extra attack with offhand light weapon
    if opponent.is_alive:
        _try_nick_extra_attack(char, opponent, weapon, state)


def _do_flurry(char: Character, opponent: Character, state: CombatState) -> None:
    """Flurry of Blows — 1 Focus Point, 2 unarmed strikes as bonus action."""
    if char.bonus_action_used or state.distance > 5:
        return
    res = char.resources.get("focus_points")
    if not res or not res.available:
        # Fall back to free martial arts strike
        return
    res.spend()
    char.bonus_action_used = True
    state.log(f"  {char.name} uses Flurry of Blows!")
    for _ in range(2):
        if not opponent.is_alive:
            break
        resolve_attack(char, opponent, _unarmed_weapon(char), state, is_unarmed=True)


def _do_martial_arts_strike(char: Character, opponent: Character, state: CombatState) -> None:
    """Martial Arts bonus unarmed strike (free, no resource)."""
    if char.bonus_action_used or state.distance > 5:
        return
    char.bonus_action_used = True
    state.log(f"  {char.name} makes a Martial Arts bonus unarmed strike")
    resolve_attack(char, opponent, _unarmed_weapon(char), state, is_unarmed=True)


def _do_cunning_hide(char: Character, state: CombatState) -> None:
    """Cunning Action: Hide — gives advantage on next attack (simplified)."""
    if char.bonus_action_used:
        return
    # In v1, we simplify: Hide grants advantage on next attack via Vex-like mechanic
    # This is a simplification — in real D&D, hiding requires obscurement
    # For sim purposes, we give ~50% chance of successful hide
    from sim.dice import d20 as roll_d20
    hide_roll = roll_d20() + char.dex_mod + char.proficiency_bonus
    # DC is opponent's passive perception (10 + WIS mod)
    dc = 10 + state.opponent_of(char).wis_mod
    if hide_roll >= dc:
        # Grant advantage on next attack (using a temp effect)
        char.active_effects.append(ActiveEffect(
            name="Hidden",
            source="cunning_action",
            end_trigger="start_of_turn",
            advantage_on_attacks=True,
        ))
        state.log(f"  {char.name} hides successfully (roll {hide_roll} vs DC {dc})")
    else:
        state.log(f"  {char.name} fails to hide (roll {hide_roll} vs DC {dc})")
    char.bonus_action_used = True


def _do_action_surge(
    char: Character, opponent: Character, action: TurnAction,
    state: CombatState, decisions: list[TurnAction]
) -> None:
    """Action Surge — take another action."""
    res = char.resources.get("action_surge")
    if not res or not res.available or not char.action_used:
        return
    res.spend()
    char.action_used = False  # reset to allow another action
    state.log(f"  {char.name} uses ACTION SURGE!")

    # Find the attack action in decisions and repeat it
    from sim.tactics import _pick_melee_weapon
    mw = _pick_melee_weapon(char) or char.best_melee_weapon()
    if state.distance <= 5 and mw:
        num_attacks = 1 + char.extra_attacks
        for _ in range(num_attacks):
            if not opponent.is_alive:
                break
            resolve_attack(char, opponent, mw, state)
        # Nick mastery on action surge attacks too
        if opponent.is_alive:
            _try_nick_extra_attack(char, opponent, mw, state)
    else:
        rw = char.best_ranged_weapon()
        if rw and state.distance <= rw.effective_range:
            resolve_attack(char, opponent, rw, state, is_thrown=rw.is_thrown)
    char.action_used = True


def _do_second_wind_action(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    do_second_wind(char, state)


def _do_patient_defense(char: Character, state: CombatState) -> None:
    """Patient Defense — spend 1 Focus Point for Dodge as bonus action."""
    if char.bonus_action_used:
        return
    res = char.resources.get("focus_points")
    if not res or not res.available:
        return
    res.spend()
    char.bonus_action_used = True
    do_dodge(char, state)
    state.log(f"  {char.name} uses Patient Defense!")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _try_nick_extra_attack(
    char: Character, opponent: Character,
    main_weapon: "Weapon", state: CombatState,
) -> None:
    """If main_weapon has Nick mastery and char can use it, make an extra attack
    with a different light weapon. This is part of the Attack action, not bonus action."""
    if not main_weapon.mastery or main_weapon.mastery != MasteryProperty.NICK:
        return
    if not char.can_use_mastery(main_weapon):
        return
    # Find a different light melee weapon
    from sim.models import WeaponProperty
    offhand = None
    for w in char.weapons:
        if w is not main_weapon and w.name != main_weapon.name and w.is_light and w.is_melee:
            offhand = w
            break
    if offhand is None:
        return
    state.log(f"  Nick mastery: extra attack with {offhand.name}!")
    resolve_attack(char, opponent, offhand, state, is_nick_attack=True)


def _find_weapon(char: Character, name: str | None) -> Weapon | None:
    if name is None:
        return None
    for w in char.weapons:
        if w.name.lower() == name.lower():
            return w
    return None


def _unarmed_weapon(char: Character) -> "Weapon":
    """Create a pseudo-weapon for unarmed strikes."""
    from sim.models import Weapon, DamageType, WeaponProperty
    return Weapon(
        name="Unarmed Strike",
        damage_dice=char.martial_arts_die or "1",
        damage_type=DamageType.BLUDGEONING,
        properties=[],
        category="simple",
        range_normal=5,
    )
