"""Chunk 1 level-5 feature tests: Stunning Strike and Uncanny Dodge."""

import random

from sim.actions import resolve_attack
from sim.models import (
    AbilityScores,
    Character,
    CombatState,
    Condition,
    DamageType,
    Resource,
    Weapon,
    WeaponProperty,
)


def _make_monk5() -> Character:
    return Character(
        name="Monk5",
        level=5,
        class_name="monk",
        ability_scores=AbilityScores(strength=10, dexterity=16, constitution=12, wisdom=20),
        max_hp=38,
        ac=16,
        proficiency_bonus=3,
        speed=40,
        weapons=[
            Weapon(
                name="Quarterstaff",
                damage_dice="1d8",
                damage_type=DamageType.BLUDGEONING,
                properties=[WeaponProperty.VERSATILE],
                category="simple",
            )
        ],
        features=["martial_arts", "stunning_strike"],
        resources={"focus_points": Resource("Focus Points", 5, 5, "short_rest")},
        martial_arts_die="1d6",
    )


def _make_target(name: str = "Target") -> Character:
    return Character(
        name=name,
        level=5,
        class_name="fighter",
        ability_scores=AbilityScores(strength=10, dexterity=10, constitution=8),
        max_hp=60,
        ac=10,
        proficiency_bonus=3,
        speed=30,
        weapons=[],
        features=[],
    )


def test_stunning_strike_applies_on_melee_hit_and_logs():
    monk = _make_monk5()
    target = _make_target()
    weapon = monk.weapons[0]
    state = CombatState(combatant_a=monk, combatant_b=target, verbose=True)

    saw_stun = False
    # Retry across seeds: we need both a hit and failed CON save.
    for seed in range(300):
        random.seed(seed)
        target.conditions.clear()
        target.active_effects.clear()
        monk.resources["focus_points"].current = 5

        result = resolve_attack(monk, target, weapon, state, attack_label="ACTION")
        if result.hit and Condition.STUNNED in target.conditions:
            saw_stun = True
            break

    assert saw_stun, "Expected at least one Stunning Strike stun across sampled seeds"
    assert monk.resources["focus_points"].current == 4
    assert any("Stunning Strike FP-1" in line and "CON save" in line for line in state.combat_log)


def test_uncanny_dodge_halves_attack_damage_once_per_round():
    rogue = _make_target("Rogue5")
    rogue.features = ["uncanny_dodge"]
    state = CombatState(combatant_a=rogue, combatant_b=_make_target("Attacker"), verbose=True)

    dmg1 = rogue.take_attack_damage([(10, DamageType.SLASHING)], state, is_attack=True)
    dmg2 = rogue.take_attack_damage([(10, DamageType.SLASHING)], state, is_attack=True)

    assert dmg1 == 5
    assert dmg2 == 10
    assert any("Uncanny Dodge" in line for line in state.combat_log)


def test_uncanny_dodge_does_not_apply_to_non_attack_damage():
    rogue = _make_target("Rogue5")
    rogue.features = ["uncanny_dodge"]
    state = CombatState(combatant_a=rogue, combatant_b=_make_target("Caster"), verbose=True)

    dmg = rogue.take_damage(10, DamageType.FIRE, state)

    assert dmg == 10
    assert not rogue.reaction_used
    assert not any("Uncanny Dodge" in line for line in state.combat_log)
