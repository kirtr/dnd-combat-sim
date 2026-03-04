"""Pluggable decision engine for combat AI.

The interface is an abstract base class ``TacticsEngine`` with a single
method ``decide_turn`` that returns an ordered list of actions to take.
The default implementation is a priority-list engine loaded from YAML.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from sim.models import Character, CombatState, CombatPhase, Condition, MasteryProperty


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class TacticsEngine(abc.ABC):
    """Base class for all decision engines."""

    @abc.abstractmethod
    def decide_turn(self, char: Character, state: CombatState) -> list[TurnAction]:
        """Return an ordered list of actions for this turn."""
        ...


@dataclass
class TurnAction:
    """A single decision for the turn."""
    kind: str          # "move", "attack", "rage", "reckless", "second_wind",
                       # "dodge", "dash", "flurry", "cunning_hide",
                       # "patient_defense", "action_surge", "ranged_attack"
    weapon: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Priority-based engine
# ---------------------------------------------------------------------------

@dataclass
class PriorityTactics(TacticsEngine):
    """Priority-list tactics loaded from YAML.

    Rules are evaluated top-down; the first matching rule fires.
    """
    name: str = "aggressive"
    rules: list[dict[str, Any]] = field(default_factory=list)

    def decide_turn(self, char: Character, state: CombatState) -> list[TurnAction]:
        opponent = state.opponent_of(char)
        actions: list[TurnAction] = []
        distance = state.distance
        in_melee = distance <= 5 and state.phase == CombatPhase.MELEE
        has_ranged = char.best_ranged_weapon() is not None

        if self.name == "aggressive":
            actions = self._aggressive(char, opponent, state, distance, in_melee, has_ranged)
        elif self.name == "defensive":
            actions = self._defensive(char, opponent, state, distance, in_melee, has_ranged)
        else:
            actions = self._aggressive(char, opponent, state, distance, in_melee, has_ranged)
        return actions

    def _aggressive(
        self, char: Character, opponent: Character,
        state: CombatState, distance: int, in_melee: bool, has_ranged: bool,
    ) -> list[TurnAction]:
        prefix_actions: list[TurnAction] = []
        actions: list[TurnAction] = []
        is_blade_pact = "pact_of_the_blade" in char.features

        # ===== NEW SUBCLASS TACTICS =====

        # --- Bladesinger Wizard ---
        if char.subclass == "bladesinger" or "bladesong" in char.features:
            return self._bladesinger_tactics(char, opponent, state, in_melee)

        # --- Eldritch Knight ---
        if char.subclass == "eldritch_knight" or "war_magic" in char.features:
            return self._eldritch_knight_tactics(char, opponent, state, in_melee)

        # --- Hexblade Warlock ---
        if char.subclass == "hexblade" or "hexblade_curse" in char.features:
            return self._hexblade_tactics(char, opponent, state, in_melee)

        # --- Assassin Rogue ---
        if char.subclass == "assassin" or "assassinate" in char.features:
            return self._assassin_tactics(char, opponent, state, in_melee)

        # --- Gloom Stalker Ranger ---
        if char.subclass == "gloom_stalker" or "dread_ambusher" in char.features:
            return self._gloom_stalker_tactics(char, opponent, state, in_melee, has_ranged)

        # --- Swords Bard ---
        if char.subclass == "swords_bard" or ("blade_flourish" in char.features and char.class_name == "bard"):
            return self._swords_bard_tactics(char, opponent, state, in_melee)

        # --- Devotion Paladin ---
        if char.subclass == "devotion" or "sacred_weapon" in char.features:
            return self._devotion_paladin_tactics(char, opponent, state, in_melee)

        # --- Forge Cleric ---
        if char.subclass == "forge" or "blessing_of_the_forge" in char.features:
            return self._forge_cleric_tactics(char, opponent, state, in_melee)

        # --- Full caster logic ---
        if char.spells_known and "eldritch_blast" not in char.features and not is_blade_pact:
            if any(e.name == "SpiritualWeapon" for e in char.active_effects):
                prefix_actions.append(TurnAction(kind="spiritual_weapon_attack"))
            if (
                char.class_name == "druid"
                and in_melee
                and "shillelagh" in char.spells_known
                and not any(e.name == "Shillelagh" for e in char.active_effects)
                and not char.bonus_action_used
            ):
                prefix_actions.append(TurnAction(kind="cast_spell", extra={"spell": "shillelagh", "slot_level": 0}))
            spell_action = _pick_spell_action(char, opponent)
            if spell_action:
                prefix_actions.append(spell_action)
                spell_name = spell_action.extra.get("spell")
                if spell_name == "spiritual_weapon":
                    cantrip_action = _pick_cantrip_action(char)
                    if cantrip_action:
                        prefix_actions.append(cantrip_action)
                elif spell_name == "healing_word" and char.class_name == "druid":
                    follow_up_action = _pick_druid_primary_spell_action(char)
                    if follow_up_action:
                        prefix_actions.append(follow_up_action)
                return prefix_actions
            if prefix_actions:
                actions.extend(prefix_actions)

        # --- Barbarian: Rage on first turn ---
        if (
            "rage" in char.features
            and not char.is_raging
            and not char.bonus_action_used
        ):
            res = char.resources.get("rage")
            if res and res.available:
                actions.append(TurnAction(kind="rage"))

        # --- Barbarian: Reckless Attack ---
        if "reckless_attack" in char.features and in_melee:
            actions.append(TurnAction(kind="reckless"))

        # --- Goliath: Large Form on first turn if not in melee (level 5+) ---
        if ("large_form" in char.species_traits
                and char.level >= 5
                and not any(e.name == "Large Form" for e in char.active_effects)
                and not char.bonus_action_used):
            # Use if not in melee (speed boost helps close) or round 1
            if not in_melee:
                actions.append(TurnAction(kind="large_form"))

        # --- Paladin: Vow of Enmity on first turn (before Hunter's Mark — lasts all combat) ---
        if (
            "vow_of_enmity" in char.features
            and not char.vow_of_enmity_active
            and not char.bonus_action_used
        ):
            res = char.resources.get("channel_divinity")
            if res and res.available:
                actions.append(TurnAction(kind="vow_of_enmity"))

        # --- Ranger/Paladin: Hunter's Mark on first turn ---
        # (prioritized before Adrenaline Rush since it boosts all hits)
        # Note: _do_hunters_mark checks bonus_action_used, so if Vow fired, this skips safely
        if "hunters_mark" in char.features and not char.hunters_mark_active and not char.bonus_action_used:
            hm_res = char.resources.get("hunters_mark")
            if hm_res and hm_res.available:
                actions.append(TurnAction(kind="hunters_mark"))

        # --- Dragonborn: Breath Weapon at range (only if in range and not in melee) ---
        if "breath_weapon" in char.species_traits:
            res = char.resources.get("breath_weapon")
            shape = getattr(char, "breath_weapon_shape", "cone")
            bw_range = 15 if shape == "cone" else 30
            if res and res.available and not in_melee and distance <= bw_range:
                actions.append(TurnAction(kind="breath_weapon"))

        # --- Warlock: Hex as bonus action when not concentrating and have a slot ---
        if "hex" in char.features and not char.is_concentrating():
            if char.highest_available_spell_slot():
                actions.append(TurnAction(kind="hex"))

        # --- Orc: Adrenaline Rush when not in melee (close distance) or when hurt ---
        if "adrenaline_rush" in char.species_traits and not char.bonus_action_used:
            res = char.resources.get("adrenaline_rush")
            if res and res.available:
                hp_pct = char.current_hp / char.max_hp
                if not in_melee or hp_pct < 0.5:
                    actions.append(TurnAction(kind="adrenaline_rush"))

        # --- Warlock: Eldritch Blast as primary action every turn ---
        if "eldritch_blast" in char.features and not is_blade_pact:
            actions.append(TurnAction(kind="eldritch_blast"))

        # --- Warlock: Armor of Agathys when already in melee and exposed ---
        if "armor_of_agathys" in char.features and in_melee and not is_blade_pact:
            if not any(e.name == "Armor of Agathys" for e in char.active_effects):
                if char.highest_available_spell_slot():
                    actions.append(TurnAction(kind="armor_of_agathys"))

        # --- Ranged attack if not in melee and have ranged weapon (non-Warlock) ---
        if not in_melee and has_ranged and "eldritch_blast" not in char.features:
            rw = char.best_ranged_weapon()
            if rw:
                actions.append(TurnAction(kind="ranged_attack", weapon=rw.name))

        # --- Move toward opponent ---
        if not in_melee:
            actions.append(TurnAction(kind="move"))

        # --- Heroic Inspiration: use on first melee attack if we don't have advantage ---
        if "heroic_inspiration" in char.species_traits or char.resources.get("heroic_inspiration"):
            hi_res = char.resources.get("heroic_inspiration")
            if hi_res and hi_res.available:
                # Use it when we're about to melee and don't already have advantage
                has_reckless = any(a.kind == "reckless" for a in actions)
                if not has_reckless:
                    actions.append(TurnAction(kind="heroic_inspiration"))

        # --- Thief: Fast Hands for advantage (before attack) ---
        if "fast_hands" in char.features and in_melee:
            actions.append(TurnAction(kind="fast_hands"))

        # --- Rogue: Steady Aim for advantage (when in melee already) ---
        if "steady_aim" in char.features and in_melee and "fast_hands" not in char.features:
            actions.append(TurnAction(kind="steady_aim"))

        # --- Melee attack ---
        # Arcane Trickster: use Booming Blade instead of normal attack
        if "booming_blade" in char.features and in_melee:
            actions.append(TurnAction(kind="booming_blade"))
        else:
            # Prefer Nick weapon as main attack to trigger extra offhand attack
            mw = _pick_melee_weapon(char)
            if mw:
                actions.append(TurnAction(kind="attack", weapon=mw.name))
            else:
                actions.append(TurnAction(kind="attack"))  # unarmed

        # --- Berserker: Frenzy attack as bonus action while raging ---
        if "frenzy" in char.features and char.is_raging and in_melee:
            actions.append(TurnAction(kind="frenzy_attack"))

        # --- Bonus action: Monk Flurry of Blows ---
        if "open_hand_technique" in char.features and in_melee:
            res = char.resources.get("focus_points")
            if res and res.available:
                actions.append(TurnAction(kind="open_hand_flurry"))
        elif "flurry_of_blows" in char.features and in_melee:
            res = char.resources.get("focus_points")
            if res and res.available:
                actions.append(TurnAction(kind="flurry"))

        # --- Shadow Monk: Shadow Step (L6) for advantage before attacking ---
        if "shadow_step" in char.features and in_melee and not char._shadow_step_used:
            actions.append(TurnAction(kind="shadow_step"))

        # --- Open Hand Monk: Wholeness of Body (L6) when below 50% HP ---
        if "wholeness_of_body" in char.features:
            res = char.resources.get("wholeness_of_body")
            if res and res.available and char.current_hp / char.max_hp < 0.5:
                actions.append(TurnAction(kind="wholeness_of_body"))

        # --- Shadow Monk: Shadow Arts (cast Darkness for defense) ---
        if "shadow_arts" in char.features and not any(e.name == "Shadow Darkness" for e in char.active_effects):
            res = char.resources.get("focus_points")
            if res and res.current >= 2:
                # Use shadow arts on first turn for defense
                actions.append(TurnAction(kind="shadow_arts"))

        # --- Bonus action: Monk Martial Arts free unarmed strike ---
        if "martial_arts" in char.features and "flurry_of_blows" not in char.features:
            actions.append(TurnAction(kind="martial_arts_strike"))
        elif "martial_arts" in char.features:
            # Fallback if no focus points
            actions.append(TurnAction(kind="martial_arts_strike"))

        # --- Rogue: Cunning Action Hide for Sneak Attack advantage ---
        if "cunning_action" in char.features and in_melee and "fast_hands" not in char.features and "steady_aim" not in char.features:
            # In aggressive mode, prefer hiding for sneak attack advantage
            actions.append(TurnAction(kind="cunning_hide"))

        # --- Action Surge ---
        if "action_surge" in char.features:
            res = char.resources.get("action_surge")
            if res and res.available:
                actions.append(TurnAction(kind="action_surge"))

        # --- Second Wind when hurt ---
        if "second_wind" in char.features:
            res = char.resources.get("second_wind")
            if res and res.available:
                hp_pct = char.current_hp / char.max_hp
                if hp_pct < 0.5:
                    actions.append(TurnAction(kind="second_wind"))

        return actions

    def _defensive(
        self, char: Character, opponent: Character,
        state: CombatState, distance: int, in_melee: bool, has_ranged: bool,
    ) -> list[TurnAction]:
        actions: list[TurnAction] = []

        # --- Barbarian: Rage on first turn (still defensive to get resistance) ---
        if (
            "rage" in char.features
            and not char.is_raging
            and not char.bonus_action_used
        ):
            res = char.resources.get("rage")
            if res and res.available:
                actions.append(TurnAction(kind="rage"))

        # --- Second Wind when hurt (priority in defensive) ---
        if "second_wind" in char.features:
            res = char.resources.get("second_wind")
            if res and res.available:
                hp_pct = char.current_hp / char.max_hp
                if hp_pct < 0.6:
                    actions.append(TurnAction(kind="second_wind"))

        # --- Monk: Patient Defense when hurt ---
        if "patient_defense" in char.features:
            res = char.resources.get("focus_points")
            hp_pct = char.current_hp / char.max_hp
            if res and res.available and hp_pct < 0.5:
                actions.append(TurnAction(kind="patient_defense"))

        # --- Ranged attack if not in melee ---
        if not in_melee and has_ranged:
            rw = char.best_ranged_weapon()
            if rw:
                actions.append(TurnAction(kind="ranged_attack", weapon=rw.name))

        # --- Move toward opponent ---
        if not in_melee:
            actions.append(TurnAction(kind="move"))

        # --- Melee attack ---
        mw = char.best_melee_weapon()
        if mw:
            actions.append(TurnAction(kind="attack", weapon=mw.name))
        else:
            actions.append(TurnAction(kind="attack"))

        # --- Reckless Attack (only in defensive if no other option) ---
        if "reckless_attack" in char.features and in_melee:
            actions.append(TurnAction(kind="reckless"))

        # --- Action Surge ---
        if "action_surge" in char.features:
            res = char.resources.get("action_surge")
            if res and res.available:
                actions.append(TurnAction(kind="action_surge"))

        return actions


    # ===== SUBCLASS TACTICS METHODS =====

    def _bladesinger_tactics(
        self, char: Character, opponent: Character,
        state: CombatState, in_melee: bool,
    ) -> list[TurnAction]:
        actions: list[TurnAction] = []
        spells = char.spells_known

        # BA: activate Bladesong if not active
        if not any(e.name == "Bladesong" for e in char.active_effects):
            actions.append(TurnAction(kind="bladesong"))

        # Spiritual Weapon attack if active
        if any(e.name == "SpiritualWeapon" for e in char.active_effects):
            actions.append(TurnAction(kind="spiritual_weapon_attack"))

        # Move if needed
        if not in_melee:
            actions.append(TurnAction(kind="move"))

        # Spell priority: L7+ high slots first
        if char.level >= 7:
            if char.has_spell_slot(7) and "finger_of_death" in spells:
                actions.append(TurnAction(kind="cast_spell", extra={"spell": "finger_of_death", "slot_level": 7}))
                return actions
            if char.has_spell_slot(6) and "disintegrate" in spells:
                actions.append(TurnAction(kind="cast_spell", extra={"spell": "disintegrate", "slot_level": 6}))
                return actions

        if char.has_spell_slot(5) and "hold_monster" in spells and not char.is_concentrating():
            actions.append(TurnAction(kind="cast_spell", extra={"spell": "hold_monster", "slot_level": 5}))
            return actions
        if char.has_spell_slot(4) and "polymorph" in spells and not char.is_concentrating():
            actions.append(TurnAction(kind="cast_spell", extra={"spell": "polymorph", "slot_level": 4}))
            return actions
        if char.has_spell_slot(3) and "fireball" in spells:
            actions.append(TurnAction(kind="cast_spell", extra={"spell": "fireball", "slot_level": 3}))
            return actions

        # Cantrip fallback
        cantrip = _pick_cantrip_action(char)
        if cantrip:
            actions.append(cantrip)
        elif in_melee:
            mw = _pick_melee_weapon(char)
            if mw:
                actions.append(TurnAction(kind="attack", weapon=mw.name))

        return actions

    def _eldritch_knight_tactics(
        self, char: Character, opponent: Character,
        state: CombatState, in_melee: bool,
    ) -> list[TurnAction]:
        actions: list[TurnAction] = []

        # Move if needed
        if not in_melee:
            actions.append(TurnAction(kind="move"))

        # L7+: cantrip then War Magic bonus attack
        if char.level >= 7 and "war_magic" in char.features:
            # Cast cantrip as action (enables War Magic)
            cantrip = _pick_cantrip_action(char)
            if cantrip:
                actions.append(cantrip)
                # War Magic bonus attack will fire via war_magic_attack handler
                actions.append(TurnAction(kind="war_magic_attack"))
                return actions

        # Fallback: use available spell slot
        if char.has_spell_slot(1) and "shield_spell" not in char.features:
            # Save slots for Shield reaction
            pass

        # Normal melee attack
        mw = _pick_melee_weapon(char)
        if in_melee and mw:
            actions.append(TurnAction(kind="attack", weapon=mw.name))
        elif in_melee:
            actions.append(TurnAction(kind="attack"))

        # Action Surge
        if "action_surge" in char.features:
            res = char.resources.get("action_surge")
            if res and res.available:
                actions.append(TurnAction(kind="action_surge"))

        return actions

    def _hexblade_tactics(
        self, char: Character, opponent: Character,
        state: CombatState, in_melee: bool,
    ) -> list[TurnAction]:
        actions: list[TurnAction] = []
        spells = char.spells_known

        # BA: apply hexblade curse if not yet applied
        if char.hexblade_curse_target is None and "hexblade_curse" in char.features:
            actions.append(TurnAction(kind="hexblade_curse"))

        # Move if needed
        if not in_melee:
            actions.append(TurnAction(kind="move"))

        # Power Word Kill if target ≤ 100 HP and have L9 slot
        if char.has_spell_slot(9) and "power_word_kill" in spells and opponent.current_hp <= 100:
            actions.append(TurnAction(kind="cast_spell", extra={"spell": "power_word_kill", "slot_level": 9}))
            return actions

        # Hold Monster / Finger of Death
        if char.has_spell_slot(5) and "hold_monster" in spells and not char.is_concentrating():
            actions.append(TurnAction(kind="cast_spell", extra={"spell": "hold_monster", "slot_level": 5}))
            return actions
        if char.has_spell_slot(7) and "finger_of_death" in spells:
            actions.append(TurnAction(kind="cast_spell", extra={"spell": "finger_of_death", "slot_level": 7}))
            return actions

        # Hex bonus action
        if "hex" in char.features and not char.is_concentrating():
            slot = char.highest_available_spell_slot()
            if slot:
                actions.append(TurnAction(kind="hex"))

        # Melee weapon attack (CHA-based via hexblade_armor)
        if in_melee:
            mw = _pick_melee_weapon(char)
            if mw:
                actions.append(TurnAction(kind="attack", weapon=mw.name))
            else:
                actions.append(TurnAction(kind="attack"))
        else:
            # Eldritch Blast at range
            if "eldritch_blast" in char.features:
                actions.append(TurnAction(kind="eldritch_blast"))

        return actions

    def _assassin_tactics(
        self, char: Character, opponent: Character,
        state: CombatState, in_melee: bool,
    ) -> list[TurnAction]:
        actions: list[TurnAction] = []

        # Round 1: Steady Aim for advantage (assassinate auto-crit is set by engine)
        if state.round_number == 1 and not char.assassin_surprised_this_combat:
            if "steady_aim" in char.features:
                actions.append(TurnAction(kind="steady_aim"))

        # Move if needed
        if not in_melee:
            actions.append(TurnAction(kind="move"))

        if in_melee or state.distance <= 5:
            mw = _pick_melee_weapon(char)
            if mw:
                actions.append(TurnAction(kind="attack", weapon=mw.name))
            else:
                actions.append(TurnAction(kind="attack"))
        else:
            # Ranged sneak attack
            rw = char.best_ranged_weapon()
            if rw:
                actions.append(TurnAction(kind="ranged_attack", weapon=rw.name))

        # Cunning Action Hide for Sneak Attack advantage next turn
        if "cunning_action" in char.features:
            actions.append(TurnAction(kind="cunning_hide"))

        return actions

    def _gloom_stalker_tactics(
        self, char: Character, opponent: Character,
        state: CombatState, in_melee: bool, has_ranged: bool,
    ) -> list[TurnAction]:
        actions: list[TurnAction] = []

        # Hunter's Mark
        if "hunters_mark" in char.features and not char.hunters_mark_active:
            res = char.resources.get("hunters_mark")
            if res and res.available:
                actions.append(TurnAction(kind="hunters_mark"))

        # Move if needed
        if not in_melee:
            actions.append(TurnAction(kind="move"))

        # Main attack (Dread Ambusher handled in _do_melee_attack)
        if in_melee:
            mw = _pick_melee_weapon(char)
            if mw:
                actions.append(TurnAction(kind="attack", weapon=mw.name))
            else:
                actions.append(TurnAction(kind="attack"))
        elif has_ranged:
            rw = char.best_ranged_weapon()
            if rw:
                actions.append(TurnAction(kind="ranged_attack", weapon=rw.name))

        return actions

    def _swords_bard_tactics(
        self, char: Character, opponent: Character,
        state: CombatState, in_melee: bool,
    ) -> list[TurnAction]:
        actions: list[TurnAction] = []
        spells = char.spells_known

        # Hypnotic Pattern if available and not yet cast
        if (
            char.has_spell_slot(3)
            and "hypnotic_pattern" in spells
            and not char.is_concentrating()
            and Condition.INCAPACITATED not in opponent.conditions
        ):
            actions.append(TurnAction(kind="cast_spell", extra={"spell": "hypnotic_pattern", "slot_level": 3}))
            return actions

        # Move if needed
        if not in_melee:
            actions.append(TurnAction(kind="move"))

        # Blade Flourish before attacking (defensive)
        if (
            "blade_flourish" in char.features
            and not char._blade_flourish_used_this_turn
        ):
            actions.append(TurnAction(kind="blade_flourish"))

        # Melee attack
        if in_melee:
            mw = _pick_melee_weapon(char)
            if mw:
                actions.append(TurnAction(kind="attack", weapon=mw.name))
            else:
                actions.append(TurnAction(kind="attack"))

        return actions

    def _devotion_paladin_tactics(
        self, char: Character, opponent: Character,
        state: CombatState, in_melee: bool,
    ) -> list[TurnAction]:
        actions: list[TurnAction] = []

        # BA round 1: Sacred Weapon
        if "sacred_weapon" in char.features and not any(e.name == "SacredWeapon" for e in char.active_effects):
            actions.append(TurnAction(kind="sacred_weapon"))

        # Vow of Enmity if available
        if "vow_of_enmity" in char.features and not char.vow_of_enmity_active:
            res = char.resources.get("channel_divinity")
            if res and res.available and not char.bonus_action_used:
                actions.append(TurnAction(kind="vow_of_enmity"))

        # Move if needed
        if not in_melee:
            actions.append(TurnAction(kind="move"))

        # Melee attack
        if in_melee:
            mw = _pick_melee_weapon(char)
            if mw:
                actions.append(TurnAction(kind="attack", weapon=mw.name))
            else:
                actions.append(TurnAction(kind="attack"))

        # Action Surge
        if "action_surge" in char.features:
            res = char.resources.get("action_surge")
            if res and res.available:
                actions.append(TurnAction(kind="action_surge"))

        # Second Wind if hurt
        if "second_wind" in char.features:
            res = char.resources.get("second_wind")
            if res and res.available and char.current_hp / char.max_hp < 0.5:
                actions.append(TurnAction(kind="second_wind"))

        return actions

    def _forge_cleric_tactics(
        self, char: Character, opponent: Character,
        state: CombatState, in_melee: bool,
    ) -> list[TurnAction]:
        actions: list[TurnAction] = []
        spells = char.spells_known

        # Spiritual Weapon attack if active
        if any(e.name == "SpiritualWeapon" for e in char.active_effects):
            actions.append(TurnAction(kind="spiritual_weapon_attack"))

        # Spirit Guardians if available
        if (
            char.has_spell_slot(3)
            and "spirit_guardians" in spells
            and not char.is_concentrating("spirit_guardians")
        ):
            actions.append(TurnAction(kind="cast_spell", extra={"spell": "spirit_guardians", "slot_level": 3}))
            return actions

        # Spiritual Weapon as bonus action if not active
        if (
            char.has_spell_slot(2)
            and "spiritual_weapon" in spells
            and not any(e.name == "SpiritualWeapon" for e in char.active_effects)
        ):
            actions.append(TurnAction(kind="cast_spell", extra={"spell": "spiritual_weapon", "slot_level": 2}))

        # Move if needed
        if not in_melee:
            actions.append(TurnAction(kind="move"))

        # Weapon attack (+1 from Blessing of the Forge)
        if in_melee:
            mw = _pick_melee_weapon(char)
            if mw:
                actions.append(TurnAction(kind="attack", weapon=mw.name))
            else:
                actions.append(TurnAction(kind="attack"))
        else:
            cantrip = _pick_cantrip_action(char)
            if cantrip:
                actions.append(cantrip)

        # Healing Word if hurt
        if (
            char.has_spell_slot(1)
            and "healing_word" in spells
            and char.current_hp < char.max_hp * 0.5
            and not char.bonus_action_used
        ):
            actions.append(TurnAction(kind="cast_spell", extra={"spell": "healing_word", "slot_level": 1}))

        return actions


def _pick_spell_action(char: Character, opponent: Character | None = None) -> TurnAction | None:
    """Pick the best spell to cast. Returns TurnAction or None if no spells available."""
    spells = char.spells_known

    if (
        "healing_word" in spells
        and char.current_hp < char.max_hp * 0.5
        and char.has_spell_slot(1)
        and not char.bonus_action_used
    ):
        return TurnAction(kind="cast_spell", extra={"spell": "healing_word", "slot_level": 1})

    if char.class_name == "druid":
        return _pick_druid_primary_spell_action(char)

    if char.class_name == "cleric":
        if char.has_spell_slot(3) and "spirit_guardians" in spells and not char.is_concentrating("spirit_guardians"):
            return TurnAction(kind="cast_spell", extra={"spell": "spirit_guardians", "slot_level": 3})

        spiritual_weapon_active = any(e.name == "SpiritualWeapon" for e in char.active_effects)
        if char.has_spell_slot(2) and "spiritual_weapon" in spells and not spiritual_weapon_active:
            return TurnAction(kind="cast_spell", extra={"spell": "spiritual_weapon", "slot_level": 2})

        if char.has_spell_slot(2) and "scorching_ray" in spells:
            return TurnAction(kind="cast_spell", extra={"spell": "scorching_ray", "slot_level": 2})

        if char.has_spell_slot(1):
            if "guiding_bolt" in spells:
                return TurnAction(kind="cast_spell", extra={"spell": "guiding_bolt", "slot_level": 1})
            if "chromatic_orb" in spells:
                return TurnAction(kind="cast_spell", extra={"spell": "chromatic_orb", "slot_level": 1})
            if "magic_missile" in spells:
                return TurnAction(kind="cast_spell", extra={"spell": "magic_missile", "slot_level": 1})

        return _pick_cantrip_action(char)

    if char.class_name == "bard":
        if (
            char.has_spell_slot(3)
            and "hypnotic_pattern" in spells
            and not char.is_concentrating()
            and not (opponent and Condition.INCAPACITATED in opponent.conditions)
        ):
            return TurnAction(kind="cast_spell", extra={"spell": "hypnotic_pattern", "slot_level": 3})

        if char.has_spell_slot(2):
            if "scorching_ray" in spells:
                return TurnAction(kind="cast_spell", extra={"spell": "scorching_ray", "slot_level": 2})
            if "dissonant_whispers" in spells:
                return TurnAction(kind="cast_spell", extra={"spell": "dissonant_whispers", "slot_level": 2})

        if char.has_spell_slot(1):
            if "dissonant_whispers" in spells:
                return TurnAction(kind="cast_spell", extra={"spell": "dissonant_whispers", "slot_level": 1})
            if "chromatic_orb" in spells:
                return TurnAction(kind="cast_spell", extra={"spell": "chromatic_orb", "slot_level": 1})

        return _pick_cantrip_action(char)

    # L9 spells
    if char.has_spell_slot(9) and "power_word_kill" in spells and opponent and opponent.current_hp <= 100:
        return TurnAction(kind="cast_spell", extra={"spell": "power_word_kill", "slot_level": 9})
    if char.has_spell_slot(9) and "time_stop" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "time_stop", "slot_level": 9})
    if char.has_spell_slot(9) and "wish" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "wish", "slot_level": 9})
    if char.has_spell_slot(9) and "meteor_swarm" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "meteor_swarm", "slot_level": 9})

    # L8 spells
    if char.has_spell_slot(8) and "power_word_stun" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "power_word_stun", "slot_level": 8})
    if char.has_spell_slot(8) and "abi_dalzims_horrid_wilting" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "abi_dalzims_horrid_wilting", "slot_level": 8})

    # L7 spells
    if char.has_spell_slot(7) and "power_word_pain" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "power_word_pain", "slot_level": 7})
    if char.has_spell_slot(7) and "finger_of_death" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "finger_of_death", "slot_level": 7})

    # L6 spells
    if char.has_spell_slot(6) and "disintegrate" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "disintegrate", "slot_level": 6})
    if char.has_spell_slot(6) and "harm" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "harm", "slot_level": 6})
    if char.has_spell_slot(6) and "chain_lightning" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "chain_lightning", "slot_level": 6})
    if char.has_spell_slot(6) and "sunbeam" in spells and not char.is_concentrating():
        return TurnAction(kind="cast_spell", extra={"spell": "sunbeam", "slot_level": 6})

    # L5 spells
    if char.has_spell_slot(5) and "hold_monster" in spells and not char.is_concentrating():
        return TurnAction(kind="cast_spell", extra={"spell": "hold_monster", "slot_level": 5})
    if char.has_spell_slot(5) and "cone_of_cold" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "cone_of_cold", "slot_level": 5})
    if char.has_spell_slot(5) and "synaptic_static" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "synaptic_static", "slot_level": 5})

    # L4 spells
    if char.has_spell_slot(4) and "banishment" in spells and not char.is_concentrating():
        return TurnAction(kind="cast_spell", extra={"spell": "banishment", "slot_level": 4})
    if char.has_spell_slot(4) and "greater_invisibility" in spells and Condition.GREATER_INVISIBLE not in char.conditions:
        return TurnAction(kind="cast_spell", extra={"spell": "greater_invisibility", "slot_level": 4})
    if char.has_spell_slot(4) and "polymorph" in spells and not char.is_concentrating():
        return TurnAction(kind="cast_spell", extra={"spell": "polymorph", "slot_level": 4})
    if char.has_spell_slot(4) and "blight" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "blight", "slot_level": 4})

    if char.has_spell_slot(3) and "fireball" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "fireball", "slot_level": 3})

    if char.has_spell_slot(2) and "scorching_ray" in spells:
        return TurnAction(kind="cast_spell", extra={"spell": "scorching_ray", "slot_level": 2})

    if char.has_spell_slot(1):
        if "chromatic_orb" in spells:
            return TurnAction(kind="cast_spell", extra={"spell": "chromatic_orb", "slot_level": 1})
        if "magic_missile" in spells:
            return TurnAction(kind="cast_spell", extra={"spell": "magic_missile", "slot_level": 1})

    return _pick_cantrip_action(char)


def _pick_cantrip_action(char: Character) -> TurnAction | None:
    cantrip_order = ["toll_the_dead", "sacred_flame", "fire_bolt"]
    if char.class_name == "bard":
        cantrip_order = ["vicious_mockery", "fire_bolt"]
    for cantrip in cantrip_order:
        if cantrip in char.spells_known:
            return TurnAction(kind="cast_spell", extra={"spell": cantrip, "slot_level": 0})
    return None


def _pick_druid_primary_spell_action(char: Character) -> TurnAction | None:
    spells = char.spells_known

    if char.is_concentrating("call_lightning"):
        return TurnAction(kind="call_lightning_bolt")

    if char.has_spell_slot(3) and "call_lightning" in spells and not char.is_concentrating():
        return TurnAction(kind="cast_spell", extra={"spell": "call_lightning", "slot_level": 3})

    if "thunderwave" in spells:
        if char.has_spell_slot(2):
            return TurnAction(kind="cast_spell", extra={"spell": "thunderwave", "slot_level": 2})
        if char.has_spell_slot(1):
            return TurnAction(kind="cast_spell", extra={"spell": "thunderwave", "slot_level": 1})

    return _pick_cantrip_action(char)


def _pick_melee_weapon(char: Character):
    """Pick the best melee weapon. Prefer Nick weapon if dual-wielding to trigger extra attack."""
    melee = [w for w in char.weapons if w.is_melee]
    if not melee:
        return None
    # If we have a Nick weapon and another light weapon, prefer the Nick weapon
    nick_weapons = [w for w in melee if w.mastery == MasteryProperty.NICK and char.can_use_mastery(w)]
    if nick_weapons:
        # Check there's a different light weapon for the offhand
        for nw in nick_weapons:
            others = [w for w in melee if w is not nw and w.name != nw.name and w.is_light]
            if others:
                return nw
    # Fall back to best melee weapon
    return max(melee, key=lambda w: w.damage_dice, default=None)


def load_tactics(name: str) -> TacticsEngine:
    """Load a tactics engine by name."""
    return PriorityTactics(name=name)
