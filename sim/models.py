"""Core data models for the combat simulator."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DamageType(Enum):
    BLUDGEONING = auto()
    PIERCING = auto()
    SLASHING = auto()
    FIRE = auto()
    COLD = auto()
    LIGHTNING = auto()
    THUNDER = auto()
    ACID = auto()
    POISON = auto()
    NECROTIC = auto()
    RADIANT = auto()
    FORCE = auto()
    PSYCHIC = auto()


class ActionType(Enum):
    ACTION = "action"
    BONUS_ACTION = "bonus_action"
    REACTION = "reaction"
    FREE = "free"


class WeaponProperty(Enum):
    FINESSE = "finesse"
    HEAVY = "heavy"
    LIGHT = "light"
    REACH = "reach"
    TWO_HANDED = "two_handed"
    VERSATILE = "versatile"
    THROWN = "thrown"
    AMMUNITION = "ammunition"
    LOADING = "loading"


class MasteryProperty(Enum):
    """2024 Weapon Mastery properties — separate from weapon physical properties."""
    NICK = "nick"
    TOPPLE = "topple"
    GRAZE = "graze"
    PUSH = "push"
    SAP = "sap"
    SLOW = "slow"
    CLEAVE = "cleave"
    VEX = "vex"


class Condition(Enum):
    PRONE = "prone"
    GRAPPLED = "grappled"
    FRIGHTENED = "frightened"
    POISONED = "poisoned"
    STUNNED = "stunned"
    INCAPACITATED = "incapacitated"
    RAGING = "raging"
    DODGING = "dodging"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Weapon:
    name: str
    damage_dice: str            # e.g. "2d6" or "1d8"
    damage_type: DamageType
    properties: list[WeaponProperty] = field(default_factory=list)
    mastery: MasteryProperty | None = None
    bonus: int = 0              # magic weapon bonus
    category: str = "simple"    # "simple" or "martial"
    versatile_damage: str | None = None  # e.g. "1d10" for longsword
    range_normal: int = 5       # melee = 5
    range_long: int | None = None  # None for melee-only
    thrown_range_normal: int | None = None
    thrown_range_long: int | None = None

    @property
    def is_finesse(self) -> bool:
        return WeaponProperty.FINESSE in self.properties

    @property
    def is_heavy(self) -> bool:
        return WeaponProperty.HEAVY in self.properties

    @property
    def is_light(self) -> bool:
        return WeaponProperty.LIGHT in self.properties

    @property
    def is_two_handed(self) -> bool:
        return WeaponProperty.TWO_HANDED in self.properties

    @property
    def is_versatile(self) -> bool:
        return WeaponProperty.VERSATILE in self.properties

    @property
    def is_thrown(self) -> bool:
        return WeaponProperty.THROWN in self.properties

    @property
    def is_ranged(self) -> bool:
        """True if this is a dedicated ranged weapon (bow/crossbow)."""
        return WeaponProperty.AMMUNITION in self.properties

    @property
    def is_melee(self) -> bool:
        return not self.is_ranged

    @property
    def effective_range(self) -> int:
        """Normal range for ranged/thrown; 5 (or 10 with reach) for melee."""
        if self.is_ranged:
            return self.range_normal
        if self.is_thrown and self.thrown_range_normal:
            return self.thrown_range_normal
        return self.range_normal


@dataclass
class AbilityScores:
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    def modifier(self, ability: str) -> int:
        return (getattr(self, ability) - 10) // 2


@dataclass
class Resource:
    """A trackable resource (spell slots, uses per rest, etc.)."""
    name: str
    current: int
    maximum: int
    recharge: str = "long_rest"  # long_rest, short_rest, turn, round

    @property
    def available(self) -> bool:
        return self.current > 0

    def spend(self, n: int = 1) -> bool:
        if self.current >= n:
            self.current -= n
            return True
        return False

    def restore(self, n: int | None = None) -> None:
        self.current = self.maximum if n is None else min(self.current + n, self.maximum)


@dataclass
class ActiveEffect:
    """An effect currently active on a character."""
    name: str
    source: str                     # what granted it
    duration: int | None = None     # rounds remaining, None = permanent
    end_trigger: str | None = None  # "start_of_turn", "end_of_turn", "on_hit", etc.
    ac_bonus: int = 0
    damage_resistance: list[DamageType] = field(default_factory=list)
    advantage_on_attacks: bool = False
    disadvantage_on_attacks: bool = False
    grants_advantage_to_enemies: bool = False
    rage_damage_bonus: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Character:
    """A combatant with all stats, resources, and state."""
    name: str
    level: int
    class_name: str
    ability_scores: AbilityScores
    max_hp: int
    ac: int
    proficiency_bonus: int
    speed: int = 30                 # base speed in feet
    weapons: list[Weapon] = field(default_factory=list)
    resources: dict[str, Resource] = field(default_factory=dict)
    features: list[str] = field(default_factory=list)      # feature IDs
    conditions: set[Condition] = field(default_factory=set)
    active_effects: list[ActiveEffect] = field(default_factory=list)
    initiative_bonus: int = 0
    extra_attacks: int = 0  # number of *additional* attacks (Extra Attack = 1)
    fighting_style: str | None = None
    weapon_mastery_slots: int = 0
    weapon_masteries: list[str] = field(default_factory=list)  # weapon names unlocked
    has_savage_attacker: bool = False
    sneak_attack_dice: str | None = None  # e.g. "1d6"
    sneak_attack_used: bool = False
    martial_arts_die: str | None = None   # e.g. "1d6"
    species_traits: dict[str, Any] = field(default_factory=dict)
    origin_feat: str = ""
    giant_ancestry: str = ""  # cloud/fire/frost/hill/stone/storm
    breath_weapon_shape: str = "cone"  # cone or line
    breath_weapon_damage_type: DamageType = DamageType.FIRE

    # --- Per-combat state ---
    current_hp: int = 0
    temp_hp: int = 0
    action_used: bool = False
    bonus_action_used: bool = False
    reaction_used: bool = False
    has_moved: bool = False
    movement_remaining: int = 0
    vex_target: str | None = None  # name of creature with Vex advantage

    def __post_init__(self):
        if self.current_hp == 0:
            self.current_hp = self.max_hp

    # --- Convenience properties ---

    @property
    def is_alive(self) -> bool:
        return self.current_hp > 0

    @property
    def effective_ac(self) -> int:
        bonus = sum(e.ac_bonus for e in self.active_effects)
        if Condition.PRONE in self.conditions:
            pass  # Handled via advantage/disadvantage on attacks
        return self.ac + bonus

    @property
    def str_mod(self) -> int:
        return self.ability_scores.modifier("strength")

    @property
    def dex_mod(self) -> int:
        return self.ability_scores.modifier("dexterity")

    @property
    def con_mod(self) -> int:
        return self.ability_scores.modifier("constitution")

    @property
    def wis_mod(self) -> int:
        return self.ability_scores.modifier("wisdom")

    @property
    def is_raging(self) -> bool:
        return Condition.RAGING in self.conditions

    @property
    def is_dodging(self) -> bool:
        return Condition.DODGING in self.conditions

    @property
    def rage_damage(self) -> int:
        for e in self.active_effects:
            if e.rage_damage_bonus:
                return e.rage_damage_bonus
        return 0

    # --- Weapon helpers ---

    def best_melee_weapon(self) -> Weapon | None:
        melee = [w for w in self.weapons if w.is_melee]
        return max(melee, key=lambda w: w.damage_dice, default=None)

    def best_ranged_weapon(self) -> Weapon | None:
        """Best dedicated ranged weapon or thrown weapon."""
        ranged = [w for w in self.weapons if w.is_ranged]
        if ranged:
            return max(ranged, key=lambda w: w.damage_dice)
        thrown = [w for w in self.weapons if w.is_thrown]
        return max(thrown, key=lambda w: w.damage_dice, default=None)

    def attack_modifier(self, weapon: Weapon) -> int:
        """Calculate attack bonus for a weapon."""
        ability_mod = self._attack_ability_mod(weapon)
        bonus = ability_mod + self.proficiency_bonus + weapon.bonus
        if self.fighting_style == "archery" and weapon.is_ranged:
            bonus += 2
        return bonus

    def _attack_ability_mod(self, weapon: Weapon) -> int:
        if weapon.is_finesse:
            return max(self.str_mod, self.dex_mod)
        if weapon.is_ranged:
            return self.dex_mod
        # Monk weapons: use DEX if we have martial_arts_die
        if self.martial_arts_die and not weapon.is_heavy:
            return max(self.str_mod, self.dex_mod)
        return self.str_mod

    def damage_modifier(self, weapon: Weapon, is_thrown: bool = False) -> int:
        """Calculate flat damage bonus for a weapon."""
        ability_mod = self._attack_ability_mod(weapon)
        bonus = ability_mod + weapon.bonus
        if self.fighting_style == "dueling":
            # +2 when holding melee weapon in one hand, no other weapons
            if weapon.is_melee and not weapon.is_two_handed:
                bonus += 2
        if self.fighting_style == "thrown_weapon_fighting" and is_thrown:
            bonus += 2
        # Rage damage
        if self.is_raging and weapon.is_melee and not weapon.is_ranged:
            # Must use STR for rage bonus (not finesse-DEX)
            if not weapon.is_finesse or self.str_mod >= self.dex_mod:
                bonus += self.rage_damage
        return bonus

    def unarmed_damage_mod(self) -> int:
        """Modifier for unarmed strikes."""
        if self.martial_arts_die:
            return max(self.str_mod, self.dex_mod)
        return self.str_mod

    def unarmed_attack_mod(self) -> int:
        if self.martial_arts_die:
            return max(self.str_mod, self.dex_mod) + self.proficiency_bonus
        return self.str_mod + self.proficiency_bonus

    def can_use_mastery(self, weapon: Weapon) -> bool:
        """Check if the character can use this weapon's mastery property."""
        return weapon.name.lower() in [m.lower() for m in self.weapon_masteries]

    # --- Turn management ---

    def start_turn(self) -> None:
        self.action_used = False
        self.bonus_action_used = False
        self.has_moved = False
        self.movement_remaining = self.speed
        self.sneak_attack_used = False
        # Tick down effects
        expired = []
        for e in self.active_effects:
            if e.end_trigger == "start_of_turn":
                expired.append(e)
            elif e.duration is not None:
                e.duration -= 1
                if e.duration <= 0:
                    expired.append(e)
        for e in expired:
            self.active_effects.remove(e)
        # Remove dodging at start of turn (it lasts until start of your next turn)
        self.conditions.discard(Condition.DODGING)
        # Stand up from prone (costs half movement)
        if Condition.PRONE in self.conditions:
            self.conditions.discard(Condition.PRONE)
            self.movement_remaining = max(0, self.movement_remaining - self.speed // 2)

    def end_turn(self) -> None:
        expired = [e for e in self.active_effects if e.end_trigger == "end_of_turn"]
        for e in expired:
            self.active_effects.remove(e)
        self.reaction_used = False

    def take_damage(self, amount: int, damage_type: DamageType, state: Any = None) -> int:
        """Apply damage, respecting resistances, temp HP, and reactions. Returns actual damage."""
        resisted = any(damage_type in e.damage_resistance for e in self.active_effects)
        if resisted:
            amount = amount // 2

        # Stone's Endurance (Goliath Frost Giant) — reaction to reduce damage
        if (not self.reaction_used
                and self.giant_ancestry == "stone"
                and "stones_endurance" in self.resources):
            res = self.resources["stones_endurance"]
            if res.available:
                from sim.dice import eval_dice
                reduction = eval_dice("1d12").total + self.con_mod
                reduction = max(0, reduction)
                amount = max(0, amount - reduction)
                res.spend()
                self.reaction_used = True
                if state:
                    state.log(f"  {self.name} uses Stone's Endurance, reducing damage by {reduction}")

        # Storm's Thunder (Storm Giant): reaction to deal 1d8 thunder to attacker, no save
        if (not self.reaction_used
                and self.giant_ancestry == "storm"
                and "storm_giant" in self.resources):
            res = self.resources["storm_giant"]
            if res.available:
                res.spend()
                self.reaction_used = True
                from sim.dice import eval_dice as _eval
                if state and hasattr(state, 'opponent_of'):
                    attacker = state.opponent_of(self)
                    thunder_dmg = _eval("1d8").total
                    thunder_actual = attacker.take_damage(thunder_dmg, DamageType.THUNDER, None)
                    if state:
                        state.log(f"  {self.name} Storm's Thunder! {attacker.name} takes {thunder_actual} thunder damage")

        # Absorb with temp HP first
        if self.temp_hp > 0:
            absorbed = min(self.temp_hp, amount)
            self.temp_hp -= absorbed
            amount -= absorbed

        self.current_hp = max(0, self.current_hp - amount)

        # Relentless Endurance (Orc) — drop to 1 HP instead of 0
        if self.current_hp == 0 and "relentless_endurance" in self.resources:
            res = self.resources["relentless_endurance"]
            if res.available:
                res.spend()
                self.current_hp = 1
                if state:
                    state.log(f"  {self.name} uses Relentless Endurance! Drops to 1 HP instead of 0!")

        return amount

    def heal(self, amount: int) -> int:
        actual = min(amount, self.max_hp - self.current_hp)
        self.current_hp += actual
        return actual

    def gain_temp_hp(self, amount: int) -> None:
        """Temp HP don't stack — keep higher."""
        self.temp_hp = max(self.temp_hp, amount)

    def reset(self) -> None:
        """Full reset for a new combat."""
        self.current_hp = self.max_hp
        self.temp_hp = 0
        self.conditions.clear()
        self.active_effects.clear()
        self.action_used = False
        self.bonus_action_used = False
        self.reaction_used = False
        self.has_moved = False
        self.movement_remaining = self.speed
        self.sneak_attack_used = False
        self.vex_target = None
        for r in self.resources.values():
            r.restore()

    def deep_copy(self) -> "Character":
        """Return a deep copy for simulation."""
        return copy.deepcopy(self)


@dataclass
class CombatState:
    """Tracks global combat state for a 1v1 fight."""
    combatant_a: Character
    combatant_b: Character
    distance: int = 60           # feet apart
    round_number: int = 0
    turn_order: list[Character] = field(default_factory=list)
    combat_log: list[str] = field(default_factory=list)
    verbose: bool = False

    def opponent_of(self, char: Character) -> Character:
        return self.combatant_b if char is self.combatant_a else self.combatant_a

    def log(self, msg: str) -> None:
        if self.verbose:
            self.combat_log.append(msg)
