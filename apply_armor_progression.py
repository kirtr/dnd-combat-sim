#!/usr/bin/env python3
"""Apply armor progression rule to all build YAMLs.

Heavy (fighter/paladin/cleric w/ heavy prof): L3/L5 → splint, L7 → plate
Medium (ranger/hexblade warlock): L3 → scale_mail, L5 → breastplate, L7 → half_plate
Light (rogue/bard/warlock/bladesinger): L3+ → studded_leather
Unarmored (monk/barbarian): no change
Special (draconic_resilience, null): no change
Druid: no change (metal armor restriction)
"""

import re
import sys
from pathlib import Path

BUILDS_DIR = Path("data/builds")

# Map: filename → (old_armor, new_armor, comment)
# comment=None means strip trailing comment; comment=str means replace/keep
CHANGES = {
    # ── LIGHT ARMOR: leather → studded_leather ───────────────────────────────
    "arcane_trickster_halfling_3.yaml":    ("leather", "studded_leather", None),
    "arcane_trickster_halfling_5.yaml":    ("leather", "studded_leather", None),
    "arcane_trickster_human_3.yaml":       ("leather", "studded_leather", None),
    "arcane_trickster_human_5.yaml":       ("leather", "studded_leather", None),
    "assassin_rogue_halfling_3.yaml":      ("leather", "studded_leather", None),
    "assassin_rogue_halfling_5.yaml":      ("leather", "studded_leather", None),
    "assassin_rogue_halfling_7.yaml":      ("leather", "studded_leather", None),
    # Bladesinger stays light armor (Bladesong requires it), but upgrade to studded
    "bladesinger_wizard_elf_3.yaml":       ("leather", "studded_leather", "# light armor required for Bladesong"),
    "bladesinger_wizard_elf_5.yaml":       ("leather", "studded_leather", "# light armor required for Bladesong"),
    "bladesinger_wizard_elf_7.yaml":       ("leather", "studded_leather", "# light armor required for Bladesong"),
    "lore_bard_human_3.yaml":             ("leather", "studded_leather", None),
    "lore_bard_human_5.yaml":             ("leather", "studded_leather", None),
    "swords_bard_human_3.yaml":           ("leather", "studded_leather", None),
    "swords_bard_human_5.yaml":           ("leather", "studded_leather", None),
    "swords_bard_human_7.yaml":           ("leather", "studded_leather", None),
    "thief_halfling_3.yaml":              ("leather", "studded_leather", None),
    "thief_halfling_5.yaml":              ("leather", "studded_leather", None),
    "thief_halfling_7.yaml":              ("leather", "studded_leather", None),
    "thief_human_3.yaml":                 ("leather", "studded_leather", None),
    "thief_human_5.yaml":                 ("leather", "studded_leather", None),
    "thief_human_7.yaml":                 ("leather", "studded_leather", None),

    # ── MEDIUM ARMOR: rangers ─────────────────────────────────────────────────
    "gloom_stalker_ranger_human_3.yaml":  ("leather", "scale_mail", None),
    "gloom_stalker_ranger_human_5.yaml":  ("studded_leather", "breastplate", None),
    "gloom_stalker_ranger_human_7.yaml":  ("studded_leather", "half_plate", None),
    "hunter_ranger_archery_3.yaml":       ("studded_leather", "scale_mail", None),
    "hunter_ranger_archery_5.yaml":       ("studded_leather", "breastplate", None),
    "hunter_ranger_gwf_3.yaml":           ("half_plate", "scale_mail", None),
    "hunter_ranger_gwf_5.yaml":           ("half_plate", "breastplate", None),
    "hunter_ranger_twf_3.yaml":           ("half_plate", "scale_mail", None),
    "hunter_ranger_twf_5.yaml":           ("half_plate", "breastplate", None),

    # ── MEDIUM ARMOR: hexblade warlock (medium via Hex Warrior) ──────────────
    "hexblade_warlock_orc_3.yaml":        ("chain_shirt", "scale_mail",  "# medium armor via Hex Warrior proficiency"),
    "hexblade_warlock_orc_5.yaml":        ("chain_shirt", "breastplate", "# medium armor via Hex Warrior proficiency"),
    "hexblade_warlock_orc_7.yaml":        ("chain_shirt", "half_plate",  "# medium armor via Hex Warrior proficiency"),

    # ── HEAVY ARMOR: battlemaster fighters ────────────────────────────────────
    "battlemaster_dueling_orc_3.yaml":         ("chain_mail", "splint", None),
    "battlemaster_dueling_orc_5.yaml":         ("chain_mail", "splint", None),
    "battlemaster_gwf_fire_goliath_5.yaml":    ("chain_mail", "splint", None),
    "battlemaster_gwf_orc_3.yaml":             ("chain_mail", "splint", None),
    "battlemaster_gwf_orc_5.yaml":             ("chain_mail", "splint", None),
    "battlemaster_gwf_stone_goliath_5.yaml":   ("chain_mail", "splint", None),
    "battlemaster_sb_fire_goliath_3.yaml":     ("chain_mail", "splint", None),
    "battlemaster_sb_fire_goliath_5.yaml":     ("chain_mail", "splint", None),
    "battlemaster_sb_orc_5.yaml":              ("chain_mail", "splint", None),
    "battlemaster_sb_stone_goliath_3.yaml":    ("chain_mail", "splint", None),
    "battlemaster_sb_stone_goliath_5.yaml":    ("chain_mail", "splint", None),
    "battlemaster_twf_orc_3.yaml":             ("chain_mail", "splint", None),
    "battlemaster_twf_orc_5.yaml":             ("chain_mail", "splint", None),

    # ── HEAVY ARMOR: champion fighters ────────────────────────────────────────
    "champion_gwf_fire_goliath_5.yaml":    ("chain_mail", "splint", None),
    "champion_gwf_orc_3.yaml":             ("chain_mail", "splint", None),
    "champion_gwf_orc_5.yaml":             ("chain_mail", "splint", None),
    "champion_gwf_orc_6.yaml":             ("chain_mail", "splint", None),  # L6: between L5/L7 → splint
    "champion_gwf_stone_goliath_3.yaml":   ("chain_mail", "splint", None),
    "champion_gwf_stone_goliath_5.yaml":   ("chain_mail", "splint", None),
    "champion_sb_fire_goliath_3.yaml":     ("chain_mail", "splint", None),
    "champion_sb_fire_goliath_5.yaml":     ("chain_mail", "splint", None),
    "champion_sb_orc_3.yaml":             ("chain_mail", "splint", None),
    "champion_sb_orc_5.yaml":             ("chain_mail", "splint", None),
    "champion_sb_stone_goliath_3.yaml":    ("chain_mail", "splint", None),
    "champion_sb_stone_goliath_5.yaml":    ("chain_mail", "splint", None),
    "champion_twf_fire_goliath_3.yaml":    ("chain_mail", "splint", None),
    "champion_twf_orc_3.yaml":             ("chain_mail", "splint", None),
    "champion_twf_orc_5.yaml":             ("chain_mail", "splint", None),
    "champion_twf_stone_goliath_3.yaml":   ("chain_mail", "splint", None),

    # ── HEAVY ARMOR: base fighters ────────────────────────────────────────────
    "fighter_gwf_orc_3.yaml":             ("chain_mail", "splint", None),
    "fighter_twf_orc_3.yaml":             ("chain_mail", "splint", None),

    # ── HEAVY ARMOR: eldritch knight ──────────────────────────────────────────
    "eldritch_knight_human_3.yaml":       ("chain_mail", "splint", None),
    "eldritch_knight_human_5.yaml":       ("chain_mail", "splint", None),
    "eldritch_knight_human_7.yaml":       ("chain_mail", "plate",  None),

    # ── HEAVY ARMOR: paladins ─────────────────────────────────────────────────
    "devotion_paladin_human_3.yaml":      ("chain_mail", "splint", None),
    "devotion_paladin_human_5.yaml":      ("chain_mail", "splint", None),
    "devotion_paladin_human_7.yaml":      ("chain_mail", "plate",  None),
    "vengeance_paladin_orc_3.yaml":       ("chain_mail", "splint", None),
    "vengeance_paladin_orc_5.yaml":       ("chain_mail", "splint", None),
    "vengeance_paladin_orc_6.yaml":       ("chain_mail", "splint", None),  # L6: splint

    # ── HEAVY ARMOR: clerics ──────────────────────────────────────────────────
    "war_cleric_human_3.yaml":            ("chain_mail", "splint", None),
    "war_cleric_human_5.yaml":            ("chain_mail", "splint", None),
    # Forge cleric: class YAML confirms heavy armor proficiency
    "forge_cleric_dwarf_3.yaml":          ("scale_mail", "splint", "# heavy armor — forge cleric proficiency"),
    "forge_cleric_dwarf_5.yaml":          ("scale_mail", "splint", "# heavy armor — forge cleric proficiency"),
    "forge_cleric_dwarf_7.yaml":          ("scale_mail", "plate",  "# heavy armor — forge cleric proficiency (L7 plate)"),
}

# Regex: match the armor line, capturing optional trailing whitespace+comment
ARMOR_LINE_RE = re.compile(
    r'^(armor:\s*)(\S+)(.*?)$',
    re.MULTILINE
)


def apply_change(path: Path, old_armor: str, new_armor: str, new_comment):
    text = path.read_text()

    def replace_armor(m):
        key_part = m.group(1)          # "armor: "
        val = m.group(2)               # current armor value
        rest = m.group(3)              # trailing whitespace + comment

        if val != old_armor:
            return m.group(0)          # no match → leave unchanged

        if new_comment is not None:
            suffix = "   " + new_comment
        else:
            suffix = ""                # strip old comment

        return f"{key_part}{new_armor}{suffix}"

    new_text = ARMOR_LINE_RE.sub(replace_armor, text)

    if new_text == text:
        # Check if it was already correct
        if f"armor: {new_armor}" in text:
            print(f"  SKIP {path.name} — already {new_armor}")
        else:
            print(f"  WARN {path.name} — expected '{old_armor}', not found!", file=sys.stderr)
        return False

    path.write_text(new_text)
    print(f"  OK   {path.name}: {old_armor} → {new_armor}")
    return True


def main():
    changed = 0
    skipped = 0
    errors = 0

    for fname, (old_a, new_a, cmt) in sorted(CHANGES.items()):
        p = BUILDS_DIR / fname
        if not p.exists():
            print(f"  MISS {fname} — file not found", file=sys.stderr)
            errors += 1
            continue
        result = apply_change(p, old_a, new_a, cmt)
        if result:
            changed += 1
        else:
            skipped += 1

    print(f"\nDone: {changed} changed, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()
