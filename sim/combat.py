"""Combat loop: initiative, turn phases, death, distance tracking."""

from __future__ import annotations

from sim.dice import d20, eval_dice, roll
from sim.models import Character, CombatState, CombatPhase, Condition, ActiveEffect, DamageType, MasteryProperty
from sim.actions import resolve_attack, do_second_wind, do_dash, do_dodge
from sim.effects import apply_rage, apply_bear_totem_rage, apply_reckless_attack
from sim.tactics import TacticsEngine, TurnAction


def _pad_label(label: str) -> str:
    return f"{label:<9}"


def roll_initiative(char: Character) -> int:
    """Roll initiative for a character."""
    return d20() + char.dex_mod + char.initiative_bonus


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
        if a.dex_mod >= b.dex_mod:
            state.turn_order = [a, b]
        else:
            state.turn_order = [b, a]

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

            if hasattr(char, "_savage_used_this_turn"):
                char._savage_used_this_turn = False

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

    char.end_turn()


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

    for i in range(num_attacks):
        if not opponent.is_alive:
            break
        result = resolve_attack(char, opponent, weapon, state, attack_label="ACTION")
        if result.hit and char.is_concentrating("Hex"):
            _apply_hex(char, opponent, state)

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
    save_roll = d20() + opponent.dex_mod
    result = eval_dice("1d10")
    damage_roll = result.total
    dmg_type = getattr(char, "breath_weapon_damage_type", DamageType.FIRE)
    label = _pad_label("ACTION")
    if save_roll >= dc:
        damage_roll = damage_roll // 2
        actual = opponent.take_damage(damage_roll, dmg_type, state)
        state.log(f"{label}Breath Weapon: {opponent.name} saves ({save_roll}/DC {dc}) · {actual} dmg [{opponent.current_hp}/{opponent.max_hp} HP]")
    else:
        actual = opponent.take_damage(damage_roll, dmg_type, state)
        state.log(f"{label}Breath Weapon: {opponent.name} fails ({save_roll}/DC {dc}) · {actual} dmg [{opponent.current_hp}/{opponent.max_hp} HP]")


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
            actual = opponent.take_damage(dmg, DamageType.FORCE, state)
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
    if not char.has_spell_slot(2):
        return
    if any(e.name == "Armor of Agathys" for e in char.active_effects):
        return
    char.spend_spell_slot(2)
    char.action_used = True
    temp_hp = 10
    char.gain_temp_hp(temp_hp)
    char.active_effects.append(ActiveEffect(
        name="Armor of Agathys",
        source="armor_of_agathys",
        duration=99,
    ))
    char.aoa_cold_damage = 10
    label = _pad_label("ACTION")
    state.log(f"{label}Armor of Agathys → +{temp_hp} temp HP, {temp_hp} cold retaliation")


def _do_hex(char: Character, state: CombatState) -> None:
    if char.bonus_action_used:
        return
    if char.is_concentrating():
        return
    if not char.has_spell_slot(2):
        return
    char.spend_spell_slot(2)
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
