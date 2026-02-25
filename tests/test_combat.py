"""Tests for combat loop running to completion."""

import random
from sim.models import (
    AbilityScores,
    Character,
    DamageType,
    MasteryProperty,
    Resource,
    Weapon,
    WeaponProperty,
)
from sim.combat import run_combat
from sim.tactics import PriorityTactics


def _make_combatant(
    name="Fighter",
    str_score=16,
    dex_score=10,
    con_score=14,
    ac=16,
    hp=20,
    class_name="fighter",
    features=None,
    weapons=None,
    fighting_style=None,
    resources=None,
):
    if weapons is None:
        weapons = [
            Weapon(
                name="Greatsword",
                damage_dice="2d6",
                damage_type=DamageType.SLASHING,
                properties=[WeaponProperty.HEAVY, WeaponProperty.TWO_HANDED],
                mastery=MasteryProperty.GRAZE,
                category="martial",
            ),
            Weapon(
                name="Javelin",
                damage_dice="1d6",
                damage_type=DamageType.PIERCING,
                properties=[WeaponProperty.THROWN],
                mastery=MasteryProperty.SLOW,
                category="simple",
                thrown_range_normal=30,
                thrown_range_long=120,
            ),
        ]
    return Character(
        name=name,
        level=2,
        class_name=class_name,
        ability_scores=AbilityScores(
            strength=str_score, dexterity=dex_score, constitution=con_score,
        ),
        max_hp=hp,
        ac=ac,
        proficiency_bonus=2,
        speed=30,
        weapons=weapons,
        features=features or ["second_wind", "action_surge"],
        fighting_style=fighting_style,
        weapon_masteries=[w.name for w in (weapons or [])],
        resources=resources or {
            "second_wind": Resource("Second Wind", 2, 2, "long_rest"),
            "action_surge": Resource("Action Surge", 1, 1, "short_rest"),
        },
    )


def test_combat_runs_to_completion():
    """A combat between two fighters should always end with one dead."""
    random.seed(42)
    a = _make_combatant("Fighter A")
    b = _make_combatant("Fighter B")
    tactics = PriorityTactics(name="aggressive")

    state = run_combat(a, b, tactics, tactics, verbose=True)
    # One should be dead
    assert not (a.is_alive and b.is_alive), "Both alive — combat didn't finish"
    assert a.is_alive or b.is_alive, "Both dead — shouldn't happen"
    assert state.round_number > 0
    assert state.round_number < 100


def test_combat_multiple_seeds():
    """Run 100 combats to make sure none hang or crash."""
    tactics = PriorityTactics(name="aggressive")
    wins_a = 0
    wins_b = 0
    for seed in range(100):
        random.seed(seed)
        a = _make_combatant("A")
        b = _make_combatant("B")
        state = run_combat(a, b, tactics, tactics)
        if a.is_alive:
            wins_a += 1
        elif b.is_alive:
            wins_b += 1
    total = wins_a + wins_b
    assert total == 100, f"Expected 100 decisive combats, got {total}"
    # Both should win sometimes (roughly 50/50 for identical builds)
    assert wins_a > 20, f"A won only {wins_a}/100 — too low for mirror match"
    assert wins_b > 20, f"B won only {wins_b}/100 — too low for mirror match"


def test_barbarian_vs_fighter():
    """Barbarian with rage should be competitive against fighter."""
    random.seed(42)
    tactics = PriorityTactics(name="aggressive")

    barbarian = _make_combatant(
        name="Barbarian",
        str_score=16,
        dex_score=14,
        con_score=16,
        ac=15,  # 10 + 2 + 3
        hp=25,  # 12 + 3 + 7 + 3
        class_name="barbarian",
        features=["rage", "reckless_attack"],
        resources={"rage": Resource("Rage", 2, 2, "long_rest")},
    )

    fighter = _make_combatant(
        name="Fighter",
        hp=20,
        ac=16,
    )

    wins_barb = 0
    wins_fight = 0
    for seed in range(200):
        random.seed(seed)
        a = barbarian.deep_copy()
        b = fighter.deep_copy()
        state = run_combat(a, b, tactics, tactics)
        if a.is_alive:
            wins_barb += 1
        elif b.is_alive:
            wins_fight += 1

    # Barbarian should win more often (rage resistance + reckless + more HP)
    # but fighter should still win sometimes
    assert wins_barb > 50, f"Barbarian won only {wins_barb}/200"
    assert wins_fight > 10, f"Fighter won only {wins_fight}/200"


def test_distance_tracking():
    """Combatants start 60ft apart and close distance."""
    random.seed(42)
    a = _make_combatant("A")
    b = _make_combatant("B")
    tactics = PriorityTactics(name="aggressive")

    state = run_combat(a, b, tactics, tactics, starting_distance=60, verbose=True)
    # By end of combat, they should be in melee range
    assert state.distance <= 5 or not (a.is_alive and b.is_alive)
