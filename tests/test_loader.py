"""Tests for YAML loading."""

from pathlib import Path

from sim.loader import load_build, load_weapon

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_load_weapon_greatsword():
    w = load_weapon("greatsword")
    assert w.name == "Greatsword"
    assert w.damage_dice == "2d6"
    assert w.is_heavy
    assert w.is_two_handed
    assert w.mastery is not None
    assert w.mastery.value == "graze"


def test_load_weapon_rapier():
    w = load_weapon("rapier")
    assert w.name == "Rapier"
    assert w.is_finesse
    assert not w.is_heavy


def test_load_weapon_longbow():
    w = load_weapon("longbow")
    assert w.name == "Longbow"
    assert w.is_ranged
    assert w.range_normal == 150
    assert w.range_long == 600


def test_load_fighter_gwf():
    path = _DATA_DIR / "builds" / "archive" / "level2" / "fighter_gwf_greatsword_2.yaml"
    char = load_build(path)
    assert char.name == "Fighter (GWF Greatsword)"
    assert char.level == 2
    assert char.class_name == "fighter"
    assert char.ac == 16  # chain mail
    assert char.max_hp == 20  # 10+2 + 6+2
    assert char.proficiency_bonus == 2
    assert char.fighting_style == "great_weapon_fighting"
    assert char.has_savage_attacker
    assert len(char.weapons) == 2
    assert any(w.name == "Greatsword" for w in char.weapons)


def test_load_fighter_dueling():
    path = _DATA_DIR / "builds" / "archive" / "level2" / "fighter_dueling_longsword_2.yaml"
    char = load_build(path)
    assert char.ac == 18  # chain mail 16 + shield 2
    assert char.fighting_style == "dueling"
    assert "shield" in char.features


def test_load_barbarian():
    path = _DATA_DIR / "builds" / "archive" / "level2" / "barbarian_greatsword_2.yaml"
    char = load_build(path)
    assert char.name == "Barbarian (Greatsword)"
    assert char.ac == 15  # 10 + DEX(2) + CON(3)
    assert char.max_hp == 25  # 12+3 + 7+3
    assert "rage" in char.features
    assert "reckless_attack" in char.features
    assert char.resources["rage"].maximum == 2


def test_load_monk():
    path = _DATA_DIR / "builds" / "archive" / "level2" / "monk_2.yaml"
    char = load_build(path)
    assert char.ac == 16  # 10 + DEX(3) + WIS(3)
    assert char.max_hp == 17  # 8+2 + 5+2
    assert char.speed == 40  # 30 + 10 unarmored movement
    assert char.martial_arts_die == "1d6"
    assert "focus_points" in char.resources
    assert char.resources["focus_points"].maximum == 2


def test_load_rogue():
    path = _DATA_DIR / "builds" / "archive" / "level2" / "rogue_rapier_2.yaml"
    char = load_build(path)
    assert char.ac == 14  # leather 11 + DEX(3)
    assert char.max_hp == 17  # 8+2 + 5+2
    assert char.sneak_attack_dice == "1d6"
    assert "cunning_action" in char.features


def test_load_rogue_level5_sneak_attack_scaling(tmp_path):
    path = tmp_path / "rogue_level5.yaml"
    path.write_text(
        """
name: Rogue (Level 5)
class: rogue
subclass: thief
level: 5
species: human
ability_scores:
  str: 10
  dex: 16
  con: 14
  int: 10
  wis: 10
  cha: 10
armor: leather
weapons: [rapier]
powers: [sneak_attack, cunning_action]
""".strip()
    )
    char = load_build(path)
    assert char.sneak_attack_dice == "3d6"


def test_load_rogue_level7_features_and_sneak_attack_scaling(tmp_path):
    path = tmp_path / "rogue_level7.yaml"
    path.write_text(
        """
name: Rogue (Level 7)
class: rogue
subclass: thief
level: 7
species: human
ability_scores:
  str: 10
  dex: 18
  con: 14
  int: 10
  wis: 10
  cha: 10
armor: leather
weapons: [rapier]
powers: [sneak_attack, cunning_action]
""".strip()
    )
    char = load_build(path)
    assert char.sneak_attack_dice == "4d6"
    assert "evasion" in char.features


def test_load_paladin_level6_gets_aura_of_protection(tmp_path):
    path = tmp_path / "paladin_level6.yaml"
    path.write_text(
        """
name: Paladin (Level 6)
class: paladin
subclass: vengeance
level: 6
species: human
ability_scores:
  str: 16
  dex: 10
  con: 14
  wis: 10
  cha: 16
armor: chain_mail
shield: true
weapons: [longsword]
powers: [divine_smite, vow_of_enmity]
""".strip()
    )
    char = load_build(path)
    assert "aura_of_protection" in char.features
    assert char.saving_throw_bonus == 3


def test_load_barbarian_level6_gets_mindless_rage(tmp_path):
    path = tmp_path / "barbarian_level6.yaml"
    path.write_text(
        """
name: Barbarian (Level 6)
class: barbarian
subclass: berserker
level: 6
species: orc
ability_scores:
  str: 18
  dex: 14
  con: 16
  wis: 10
  cha: 10
armor: unarmored
weapons: [greatsword]
powers: [rage, reckless_attack]
""".strip()
    )
    char = load_build(path)
    assert "mindless_rage" in char.features


def test_load_archery_fighter():
    path = _DATA_DIR / "builds" / "archive" / "level2" / "fighter_archery_longbow_2.yaml"
    char = load_build(path)
    assert char.fighting_style == "archery"
    assert char.ac == 15  # chain shirt 13 + DEX(2 capped)
    longbow = next(w for w in char.weapons if w.name == "Longbow")
    assert char.attack_modifier(longbow) == 2 + 3 + 2  # prof + DEX + archery
