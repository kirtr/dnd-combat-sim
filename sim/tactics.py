"""Pluggable decision engine for combat AI.

The interface is an abstract base class ``TacticsEngine`` with a single
method ``decide_turn`` that returns an ordered list of actions to take.
The default implementation is a priority-list engine loaded from YAML.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from sim.models import Character, CombatState, Condition, MasteryProperty


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
        in_melee = distance <= 5
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
        actions: list[TurnAction] = []

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

        # --- Goliath: Large Form on first turn if not in melee ---
        if ("large_form" in char.species_traits
                and not any(e.name == "Large Form" for e in char.active_effects)
                and not char.bonus_action_used):
            # Use if not in melee (speed boost helps close) or round 1
            if not in_melee:
                actions.append(TurnAction(kind="large_form"))

        # --- Orc: Adrenaline Rush when not in melee (close distance) or when hurt ---
        if "adrenaline_rush" in char.species_traits and not char.bonus_action_used:
            res = char.resources.get("adrenaline_rush")
            if res and res.available:
                hp_pct = char.current_hp / char.max_hp
                if not in_melee or hp_pct < 0.5:
                    actions.append(TurnAction(kind="adrenaline_rush"))

        # --- Dragonborn: Breath Weapon at range (only if in range and not in melee) ---
        if "breath_weapon" in char.species_traits:
            res = char.resources.get("breath_weapon")
            shape = getattr(char, "breath_weapon_shape", "cone")
            bw_range = 15 if shape == "cone" else 30
            if res and res.available and not in_melee and distance <= bw_range:
                actions.append(TurnAction(kind="breath_weapon"))

        # --- Ranged attack if not in melee and have ranged weapon ---
        if not in_melee and has_ranged:
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

        # --- Melee attack ---
        # Prefer Nick weapon as main attack to trigger extra offhand attack
        mw = _pick_melee_weapon(char)
        if mw:
            actions.append(TurnAction(kind="attack", weapon=mw.name))
        else:
            actions.append(TurnAction(kind="attack"))  # unarmed

        # --- Bonus action: Monk Flurry of Blows ---
        if "flurry_of_blows" in char.features and in_melee:
            res = char.resources.get("focus_points")
            if res and res.available:
                actions.append(TurnAction(kind="flurry"))

        # --- Bonus action: Monk Martial Arts free unarmed strike ---
        if "martial_arts" in char.features and "flurry_of_blows" not in char.features:
            actions.append(TurnAction(kind="martial_arts_strike"))
        elif "martial_arts" in char.features:
            # Fallback if no focus points
            actions.append(TurnAction(kind="martial_arts_strike"))

        # --- Rogue: Cunning Action Hide for Sneak Attack advantage ---
        if "cunning_action" in char.features and in_melee:
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
