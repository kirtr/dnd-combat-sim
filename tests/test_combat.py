"""Tests for combat and loading."""
import random
from sim.loader import load_build_by_name
from sim.combat import run_combat
from sim.tactics import load_tactics


def test_load_fighter_gwf():
    char = load_build_by_name("fighter_gwf_greatsword_2")
    assert char.name == "Fighter (GWF Greatsword)"
    assert char.level == 2
    assert char.max_hp > 0
    assert char.ac == 16  # chain mail
    assert char.fighting_style == "great_weapon_fighting"
    assert len(char.weapons) == 1
    assert char.weapons[0].name == "Greatsword"
    assert char.has_savage_attacker


def test_load_barbarian():
    char = load_build_by_name("barbarian_berserker_2")
    assert char.class_name == "barbarian"
    assert char.ac == 14  # 10 + 2(DEX) + 2(CON)
    assert "rage" in char.resources


def test_load_monk():
    char = load_build_by_name("monk_open_hand_2")
    assert char.class_name == "monk"
    assert char.ac == 16  # 10 + 3(DEX) + 3(WIS)
    assert char.martial_arts_die == "1d6"
    assert char.speed == 40


def test_load_rogue():
    char = load_build_by_name("rogue_thief_2")
    assert char.class_name == "rogue"
    assert char.sneak_attack_dice == "1d6"
    assert "cunning_action" in char.features


def test_combat_runs_to_completion():
    random.seed(42)
    a = load_build_by_name("fighter_gwf_greatsword_2")
    b = load_build_by_name("barbarian_berserker_2")
    tactics = load_tactics("aggressive")
    ca, cb = a.deep_copy(), b.deep_copy()
    state = run_combat(ca, cb, tactics, tactics)
    assert not ca.is_alive or not cb.is_alive or state.round_number == 100
    assert state.round_number > 0


def test_combat_all_builds():
    """All builds load and can fight each other."""
    random.seed(42)
    builds = [
        "fighter_gwf_greatsword_2",
        "fighter_dueling_longsword_2",
        "fighter_archery_longbow_2",
        "barbarian_berserker_2",
        "monk_open_hand_2",
        "rogue_thief_2",
    ]
    chars = [load_build_by_name(b) for b in builds]
    tactics = load_tactics("aggressive")
    for i, a in enumerate(chars):
        for j, b in enumerate(chars):
            if i != j:
                state = run_combat(a.deep_copy(), b.deep_copy(), tactics, tactics)
                # Should finish within 100 rounds
                assert state.round_number <= 100
