"""Tests for attack roll resolution and damage calculation."""

import random
from types import SimpleNamespace

from sim.models import (
    AbilityScores,
    Character,
    CombatState,
    Condition,
    DamageType,
    MasteryProperty,
    Resource,
    Weapon,
    WeaponProperty,
)
from sim.actions import resolve_attack, resolve_spell_save


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


def test_divine_smite_prefers_level2_slot_when_available():
    """Divine Smite should consume a level 2 slot first (level-5 scaling)."""
    attacker = _make_fighter("Paladin", str_score=16)
    attacker.level = 5
    attacker.features = ["divine_smite"]
    attacker.resources["spell_slot_1"] = Resource("Spell Slot 1", 2, 2, "long_rest")
    attacker.resources["spell_slot_2"] = Resource("Spell Slot 2", 1, 1, "long_rest")

    defender = _make_fighter("Target", ac=5, hp=200)
    weapon = _make_greatsword()
    state = CombatState(combatant_a=attacker, combatant_b=defender)

    random.seed(1)
    for _ in range(30):
        result = resolve_attack(attacker, defender, weapon, state)
        if result.hit:
            break
    assert result.hit
    assert attacker.resources["spell_slot_2"].current == 0
    assert attacker.resources["spell_slot_1"].current == 2


def test_resolve_spell_save_applies_aura_of_protection(monkeypatch):
    caster = Character(
        name="Wizard",
        level=5,
        class_name="wizard",
        ability_scores=AbilityScores(intelligence=16),
        max_hp=30,
        ac=12,
        proficiency_bonus=3,
        spellcasting_ability="intelligence",
    )
    target = Character(
        name="Paladin",
        level=6,
        class_name="paladin",
        ability_scores=AbilityScores(dexterity=10, charisma=16),
        max_hp=40,
        ac=18,
        proficiency_bonus=3,
        features=["aura_of_protection"],
        aura_of_protection=True,
    )
    state = CombatState(combatant_a=caster, combatant_b=target, verbose=True)

    monkeypatch.setattr("sim.actions.d20", lambda: 11)
    monkeypatch.setattr("sim.actions.eval_dice", lambda _: SimpleNamespace(total=12, rolls=(6, 6)))

    actual = resolve_spell_save(caster, target, "2d6", DamageType.FIRE, "Fireball", "dex", state)

    assert actual == 6
    assert "saves (14/DC 14)" in state.combat_log[-1]


def test_resolve_spell_save_evasion_zero_on_success(monkeypatch):
    caster = Character(
        name="Wizard",
        level=5,
        class_name="wizard",
        ability_scores=AbilityScores(intelligence=16),
        max_hp=30,
        ac=12,
        proficiency_bonus=3,
        spellcasting_ability="intelligence",
    )
    target = Character(
        name="Rogue",
        level=7,
        class_name="rogue",
        ability_scores=AbilityScores(dexterity=18),
        max_hp=35,
        ac=15,
        proficiency_bonus=3,
        features=["evasion"],
    )
    state = CombatState(combatant_a=caster, combatant_b=target, verbose=True)

    monkeypatch.setattr("sim.actions.d20", lambda: 10)
    monkeypatch.setattr("sim.actions.eval_dice", lambda _: SimpleNamespace(total=12, rolls=(6, 6)))

    actual = resolve_spell_save(caster, target, "2d6", DamageType.FIRE, "Fireball", "dexterity", state)

    assert actual == 0
    assert "Evasion → 0 dmg" in state.combat_log[-1]


def test_resolve_spell_save_evasion_half_on_failure(monkeypatch):
    caster = Character(
        name="Wizard",
        level=5,
        class_name="wizard",
        ability_scores=AbilityScores(intelligence=16),
        max_hp=30,
        ac=12,
        proficiency_bonus=3,
        spellcasting_ability="intelligence",
    )
    target = Character(
        name="Rogue",
        level=7,
        class_name="rogue",
        ability_scores=AbilityScores(dexterity=18),
        max_hp=35,
        ac=15,
        proficiency_bonus=3,
        features=["evasion"],
    )
    state = CombatState(combatant_a=caster, combatant_b=target, verbose=True)

    monkeypatch.setattr("sim.actions.d20", lambda: 1)
    monkeypatch.setattr("sim.actions.eval_dice", lambda _: SimpleNamespace(total=12, rolls=(6, 6)))

    actual = resolve_spell_save(caster, target, "2d6", DamageType.FIRE, "Fireball", "dex", state)

    assert actual == 6
    assert "Evasion → 6 dmg" in state.combat_log[-1]


def test_mindless_rage_blocks_frightened_and_charmed_while_raging():
    barbarian = Character(
        name="Barbarian",
        level=6,
        class_name="barbarian",
        ability_scores=AbilityScores(strength=18, constitution=16),
        max_hp=55,
        ac=15,
        proficiency_bonus=3,
        features=["rage", "mindless_rage"],
        conditions={Condition.RAGING},
    )

    assert barbarian.apply_condition(Condition.FRIGHTENED) is False
    assert barbarian.apply_condition(Condition.CHARMED) is False
    assert Condition.FRIGHTENED not in barbarian.conditions
    assert Condition.CHARMED not in barbarian.conditions
