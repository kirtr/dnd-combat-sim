"""Tests for attack roll resolution and damage calculation."""

import random
from sim.models import (
    AbilityScores,
    Character,
    CombatState,
    DamageType,
    MasteryProperty,
    Weapon,
    WeaponProperty,
)
from sim.actions import resolve_attack


def _make_fighter(name="Fighter", str_score=16, ac=16, hp=20):
    return Character(
        name=name,
        level=2,
        class_name="fighter",
        ability_scores=AbilityScores(strength=str_score, dexterity=10, constitution=14),
        max_hp=hp,
        ac=ac,
        proficiency_bonus=2,
        speed=30,
        weapons=[],
        features=[],
    )


def _make_greatsword():
    return Weapon(
        name="Greatsword",
        damage_dice="2d6",
        damage_type=DamageType.SLASHING,
        properties=[WeaponProperty.HEAVY, WeaponProperty.TWO_HANDED],
        mastery=MasteryProperty.GRAZE,
        category="martial",
    )


def test_attack_hit():
    """A high roll should hit."""
    random.seed(0)
    attacker = _make_fighter("Attacker")
    defender = _make_fighter("Defender", ac=10)
    weapon = _make_greatsword()
    state = CombatState(combatant_a=attacker, combatant_b=defender)

    # Run many attacks, at least some should hit with AC 10
    hits = 0
    for _ in range(100):
        defender.current_hp = defender.max_hp
        result = resolve_attack(attacker, defender, weapon, state)
        if result.hit:
            hits += 1
    assert hits > 50, f"Expected most attacks to hit AC 10, got {hits}/100"


def test_attack_miss():
    """Attacks against very high AC should mostly miss."""
    random.seed(42)
    attacker = _make_fighter("Attacker")
    defender = _make_fighter("Defender", ac=25)
    weapon = _make_greatsword()
    state = CombatState(combatant_a=attacker, combatant_b=defender)

    misses = 0
    for _ in range(100):
        result = resolve_attack(attacker, defender, weapon, state)
        if not result.hit:
            misses += 1
    assert misses > 80, f"Expected most attacks to miss AC 25, got {misses}/100 misses"


def test_critical_hit():
    """Natural 20 always hits and deals extra damage."""
    attacker = _make_fighter("Attacker")
    defender = _make_fighter("Defender", ac=30, hp=200)
    weapon = _make_greatsword()
    state = CombatState(combatant_a=attacker, combatant_b=defender)

    crits = 0
    for seed in range(10000):
        random.seed(seed)
        defender.current_hp = defender.max_hp
        result = resolve_attack(attacker, defender, weapon, state)
        if result.critical:
            crits += 1
            assert result.hit
    # ~5% crit rate (nat 20)
    assert 300 < crits < 700, f"Crit count {crits} out of 10000 (expected ~500)"


def test_damage_with_modifier():
    """Damage includes STR modifier."""
    random.seed(42)
    attacker = _make_fighter("Attacker", str_score=16)  # +3 mod
    defender = _make_fighter("Defender", ac=5, hp=200)
    weapon = _make_greatsword()
    state = CombatState(combatant_a=attacker, combatant_b=defender)

    # Attack should hit most of the time vs AC 5
    result = None
    for _ in range(20):
        defender.current_hp = defender.max_hp
        result = resolve_attack(attacker, defender, weapon, state)
        if result.hit and not result.critical:
            break
    assert result is not None and result.hit
    # 2d6 + 3 (STR mod) = min 5, max 15
    assert 5 <= result.damage <= 15, f"Damage {result.damage} not in expected range [5, 15]"


def test_dueling_damage_bonus():
    """Dueling style adds +2 to damage with one-handed melee."""
    random.seed(42)
    attacker = _make_fighter("Duelist", str_score=16)
    attacker.fighting_style = "dueling"
    defender = _make_fighter("Target", ac=5, hp=200)
    longsword = Weapon(
        name="Longsword",
        damage_dice="1d8",
        damage_type=DamageType.SLASHING,
        properties=[WeaponProperty.VERSATILE],
        category="martial",
    )
    state = CombatState(combatant_a=attacker, combatant_b=defender)

    result = None
    for _ in range(20):
        defender.current_hp = defender.max_hp
        result = resolve_attack(attacker, defender, longsword, state)
        if result.hit and not result.critical:
            break
    assert result is not None and result.hit
    # 1d8 + 3 (STR) + 2 (dueling) = min 6, max 13
    assert 6 <= result.damage <= 13, f"Damage {result.damage} not in [6, 13]"


def test_graze_on_miss():
    """Graze mastery deals ability mod damage on miss."""
    random.seed(42)
    attacker = _make_fighter("Attacker", str_score=16)
    attacker.weapon_masteries = ["Greatsword"]
    defender = _make_fighter("Defender", ac=30, hp=200)
    weapon = _make_greatsword()
    state = CombatState(combatant_a=attacker, combatant_b=defender)

    # Force a miss (but not nat 20)
    graze_damage_seen = False
    for seed in range(1000):
        random.seed(seed)
        defender.current_hp = defender.max_hp
        result = resolve_attack(attacker, defender, weapon, state)
        if not result.hit and result.damage > 0:
            graze_damage_seen = True
            assert result.damage == 3  # STR mod = +3
            break
    assert graze_damage_seen, "Expected to see Graze damage on at least one miss"
