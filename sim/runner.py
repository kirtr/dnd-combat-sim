"""Monte Carlo runner: N combats, collect stats."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sim.combat import run_combat
from sim.loader import load_build
from sim.tactics import load_tactics

if TYPE_CHECKING:
    from sim.models import Character, Weapon


# ---------------------------------------------------------------------------
# Character sheet formatting helpers
# ---------------------------------------------------------------------------

def _fmt_mod(value: int) -> str:
    """Format a modifier as +X or -X (never ±0)."""
    return f"+{value}" if value >= 0 else str(value)


def _fmt_stat(score: int) -> str:
    """Format score(mod) e.g. 16(+3)."""
    mod = (score - 10) // 2
    return f"{score}({_fmt_mod(mod)})"


_SUBCLASS_NAMES: dict[str, str] = {
    "battle_master": "BattleMaster",
    "champion": "Champion",
    "berserker": "Berserker",
    "bear_totem": "BearTotem",
    "wild_heart_sea": "WildHeartSea",
    "hunter": "Hunter",
    "open_hand": "OpenHand",
    "shadow": "Shadow",
    "thief": "Thief",
    "arcane_trickster": "ArcaneTrickster",
}

_FIGHTING_STYLE_DISPLAY: dict[str, str] = {
    "dueling": "Dueling+2",
    "two_weapon_fighting": "TWF",
    "archery": "Archery+2",
    "defense": "Defense+1",
    "great_weapon_fighting": "GWF",
    "thrown_weapon_fighting": "ThrowFight+2",
    "protection": "Protection",
    "blind_fighting": "BlindFight",
}

_MANEUVER_NAMES: dict[str, str] = {
    "precision": "Precision",
    "menacing": "Menacing",
    "riposte": "Riposte",
    "trip": "Trip",
    "disarming": "Disarming",
    "pushing": "Pushing",
    "commanding": "Commanding",
    "distracting": "Distracting",
    "evasive": "Evasive",
    "feinting": "Feinting",
    "goading": "Goading",
    "lunging": "Lunging",
    "maneuvering": "Maneuvering",
    "parrying": "Parrying",
    "rally": "Rally",
    "sweeping": "Sweeping",
}

_SPECIES_TRAIT_NAMES: dict[str, str | None] = {
    "adrenaline_rush": "Adrenaline Rush",
    "relentless_endurance": "Relentless Endurance",
    "breath_weapon": "Breath Weapon",
    "resourceful": "Heroic Inspiration",
    "giant_ancestry": None,   # handled via char.giant_ancestry
    # Non-combat traits — suppress
    "darkvision": None,
    "fey_ancestry": None,
    "keen_senses": None,
    "skillful": None,
    "trance": None,
    "versatile": None,
}

_GIANT_ANCESTRY_DISPLAY: dict[str, str] = {
    "cloud": "Cloud Giant",
    "fire": "Fire Giant",
    "frost": "Stone's Endurance",
    "stone": "Stone's Endurance",
    "hill": "Hill Giant",
    "storm": "Storm's Thunder",
}

_ORIGIN_FEAT_NAMES: dict[str, str] = {
    "savage_attacker": "Savage Attacker",
    "alert": "Alert",
    "lucky": "Lucky",
    "tough": "Tough",
    "war_caster": "War Caster",
    "charger": "Charger",
    "durable": "Durable",
    "mage_slayer": "Mage Slayer",
    "tavern_brawler": "Tavern Brawler",
}


def _weapon_damage_str(char: "Character", weapon: "Weapon") -> str:
    """Format weapon as Name(dice+mod[,Mastery])."""
    from sim.models import WeaponProperty

    # Determine ability modifier used for this weapon
    if weapon.is_finesse:
        ability_mod = max(char.str_mod, char.dex_mod)
    elif weapon.is_ranged:
        ability_mod = char.dex_mod
    elif char.martial_arts_die and not weapon.is_heavy:
        ability_mod = max(char.str_mod, char.dex_mod)
    else:
        ability_mod = char.str_mod

    bonus = ability_mod + weapon.bonus

    # Dueling: +2 for melee one-handed weapons that are not thrown weapons
    is_thrown_only = (weapon.is_thrown and not weapon.is_ranged
                      and weapon.range_normal == 5)
    if (char.fighting_style == "dueling"
            and weapon.is_melee
            and not weapon.is_two_handed
            and not is_thrown_only):
        bonus += 2

    die = weapon.damage_dice
    dmg = f"{die}{_fmt_mod(bonus)}"

    # Mastery property (capitalize first letter)
    parts = [dmg]
    if char.can_use_mastery(weapon) and weapon.mastery:
        parts.append(weapon.mastery.value.capitalize())

    return f"{weapon.name}({',' .join(parts)})"


def _species_traits_display(char: "Character") -> str:
    """Return a comma-separated string of notable combat species traits."""
    traits = []

    for key in char.species_traits:
        if key in _SPECIES_TRAIT_NAMES:
            name = _SPECIES_TRAIT_NAMES[key]
            if name:
                traits.append(name)
        else:
            # Unknown trait — format nicely
            traits.append(key.replace("_", " ").title())

    # Giant Ancestry (Goliath)
    if char.giant_ancestry:
        traits.append(_GIANT_ANCESTRY_DISPLAY.get(
            char.giant_ancestry,
            f"{char.giant_ancestry.title()} Giant"
        ))

    # Origin feat
    if char.origin_feat in _ORIGIN_FEAT_NAMES:
        traits.append(_ORIGIN_FEAT_NAMES[char.origin_feat])

    return ", ".join(traits)


def format_character_sheet(char: "Character") -> tuple[str, str]:
    """Return (line1, line2) two-line character sheet summary."""
    ab = char.ability_scores

    # Class/Subclass display
    sub = _SUBCLASS_NAMES.get(char.subclass, char.subclass.replace("_", " ").title() if char.subclass else "")
    class_str = char.class_name.title()
    if sub:
        class_str = f"{class_str}/{sub}"

    line1 = (
        f"{char.name} | {class_str} {char.level} | "
        f"HP:{char.max_hp} AC:{char.ac} | "
        f"STR:{_fmt_stat(ab.strength)} "
        f"DEX:{_fmt_stat(ab.dexterity)} "
        f"CON:{_fmt_stat(ab.constitution)} "
        f"INT:{_fmt_stat(ab.intelligence)} "
        f"WIS:{_fmt_stat(ab.wisdom)} "
        f"CHA:{_fmt_stat(ab.charisma)} "
        f"PB:{_fmt_mod(char.proficiency_bonus)}"
    )

    # Weapons
    weapon_parts = [_weapon_damage_str(char, w) for w in char.weapons]
    weapons_str = " ".join(weapon_parts)

    # Fighting style
    fs_label = _FIGHTING_STYLE_DISPLAY.get(char.fighting_style or "", "")
    if fs_label:
        weapons_str += f" [{fs_label}]"

    line2_parts = [weapons_str]

    # Maneuvers (Battle Master only)
    if char.maneuvers:
        mnames = [_MANEUVER_NAMES.get(m, m.replace("_", " ").title()) for m in char.maneuvers]
        line2_parts.append(f"Maneuvers: {'/'.join(mnames)}")

    # Species traits & notable feats
    traits_str = _species_traits_display(char)
    if traits_str:
        line2_parts.append(traits_str)

    line2 = "  " + " | ".join(line2_parts)

    return line1, line2


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

@dataclass
class CombatStats:
    """Accumulated statistics across many combats."""
    name: str
    wins: int = 0
    total_damage_dealt: float = 0.0
    total_rounds: int = 0
    wins_hp_remaining: float = 0.0

    @property
    def avg_dpr(self) -> float:
        return self.total_damage_dealt / max(1, self.total_rounds)

    @property
    def avg_hp_remaining_on_win(self) -> float:
        return self.wins_hp_remaining / max(1, self.wins)


def run_simulations(
    build1_path: str,
    build2_path: str,
    n: int = 10000,
    tactic1: str = "aggressive",
    tactic2: str = "aggressive",
    verbose: bool = False,
) -> dict:
    """Run N combats and return summary statistics."""

    template_a = load_build(build1_path)
    template_b = load_build(build2_path)
    tactics_a = load_tactics(tactic1)
    tactics_b = load_tactics(tactic2)

    stats_a = CombatStats(name=template_a.name)
    stats_b = CombatStats(name=template_b.name)

    total_rounds = 0
    draws = 0
    special_triggers_totals: dict[str, int] = {}

    for i in range(n):
        a = template_a.deep_copy()
        b = template_b.deep_copy()

        state = run_combat(a, b, tactics_a, tactics_b, verbose=verbose and i == 0)

        total_rounds += state.round_number

        # Damage dealt = opponent's lost HP
        a_damage_dealt = template_b.max_hp - b.current_hp
        b_damage_dealt = template_a.max_hp - a.current_hp

        stats_a.total_damage_dealt += a_damage_dealt
        stats_b.total_damage_dealt += b_damage_dealt
        stats_a.total_rounds += state.round_number
        stats_b.total_rounds += state.round_number

        # Aggregate special triggers
        for key, val in state.special_triggers.items():
            special_triggers_totals[key] = special_triggers_totals.get(key, 0) + val

        if a.is_alive and not b.is_alive:
            stats_a.wins += 1
            stats_a.wins_hp_remaining += a.current_hp
        elif b.is_alive and not a.is_alive:
            stats_b.wins += 1
            stats_b.wins_hp_remaining += b.current_hp
        else:
            draws += 1

        if verbose and i == 0:
            print("\n".join(state.combat_log))
            print()

    avg_rounds = total_rounds / n if n else 0
    avg_ttk_a = avg_rounds  # simplified
    avg_ttk_b = avg_rounds

    results = {
        "n": n,
        "template_a": template_a,   # Character object for char sheet display
        "template_b": template_b,
        "combatant_a": {
            "name": template_a.name,
            "class": template_a.class_name,
            "hp": template_a.max_hp,
            "ac": template_a.ac,
            "wins": stats_a.wins,
            "win_rate": stats_a.wins / n * 100,
            "avg_dpr": stats_a.total_damage_dealt / total_rounds if total_rounds else 0,
            "avg_hp_remaining_on_win": stats_a.avg_hp_remaining_on_win,
        },
        "combatant_b": {
            "name": template_b.name,
            "class": template_b.class_name,
            "hp": template_b.max_hp,
            "ac": template_b.ac,
            "wins": stats_b.wins,
            "win_rate": stats_b.wins / n * 100,
            "avg_dpr": stats_b.total_damage_dealt / total_rounds if total_rounds else 0,
            "avg_hp_remaining_on_win": stats_b.avg_hp_remaining_on_win,
        },
        "draws": draws,
        "avg_rounds": avg_rounds,
        "avg_ttk": avg_rounds,
        "special_triggers": special_triggers_totals,
    }
    return results


def print_results(results: dict) -> None:
    n = results["n"]
    a = results["combatant_a"]
    b = results["combatant_b"]

    # --- Character sheets (before stats divider) ---
    template_a = results.get("template_a")
    template_b = results.get("template_b")

    if template_a is not None:
        l1, l2 = format_character_sheet(template_a)
        print(l1)
        print(l2)
        print()
    if template_b is not None:
        l1, l2 = format_character_sheet(template_b)
        print(l1)
        print(l2)
        print()

    # --- Stats table ---
    print("=" * 64)
    print(f"  D&D 2024 Combat Simulator — {n:,} simulations")
    print("=" * 64)
    print()
    print(f"  {'':22s} {'A: ' + a['name']:>19s}  {'B: ' + b['name']:>19s}")
    print(f"  {'Class':22s} {a['class']:>19s}  {b['class']:>19s}")
    print(f"  {'HP':22s} {a['hp']:>19d}  {b['hp']:>19d}")
    print(f"  {'AC':22s} {a['ac']:>19d}  {b['ac']:>19d}")
    print(f"  {'Wins':22s} {a['wins']:>19,d}  {b['wins']:>19,d}")
    print(f"  {'Win Rate':22s} {a['win_rate']:>18.1f}%  {b['win_rate']:>18.1f}%")
    print(f"  {'Avg DPR':22s} {a['avg_dpr']:>19.2f}  {b['avg_dpr']:>19.2f}")
    print(f"  {'Avg HP on Win':22s} {a['avg_hp_remaining_on_win']:>19.1f}  {b['avg_hp_remaining_on_win']:>19.1f}")
    print()
    print(f"  Draws: {results['draws']:,}")
    print(f"  Avg Rounds per Combat: {results['avg_rounds']:.1f}")
    print(f"  Avg Turns to Kill: {results['avg_ttk']:.1f}")

    # Special triggers
    triggers = results.get("special_triggers", {})
    if triggers:
        print()
        print("  Species Features:")
        if "relentless_endurance" in triggers:
            count = triggers["relentless_endurance"]
            print(f"    Relentless Endurance: {count:,} triggers ({count/n*100:.1f}% of fights)")
        if "stones_endurance_triggers" in triggers:
            count = triggers["stones_endurance_triggers"]
            reduced = triggers.get("stones_endurance_reduced", 0)
            print(f"    Stone's Endurance: {count:,} triggers ({count/n*100:.1f}% of fights), {reduced/n:.1f} avg damage reduced/fight")

    print("=" * 64)


def main():
    parser = argparse.ArgumentParser(description="D&D 2024 Combat Simulator")
    parser.add_argument("--build1", required=True, help="Path to build 1 YAML")
    parser.add_argument("--build2", required=True, help="Path to build 2 YAML")
    parser.add_argument("-n", type=int, default=10000, help="Number of simulations")
    parser.add_argument("--tactic1", default="aggressive", help="Tactics for build 1")
    parser.add_argument("--tactic2", default="aggressive", help="Tactics for build 2")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show first combat log")
    args = parser.parse_args()

    start = time.time()
    results = run_simulations(
        args.build1, args.build2, args.n,
        tactic1=args.tactic1, tactic2=args.tactic2,
        verbose=args.verbose,
    )
    elapsed = time.time() - start

    print_results(results)
    print(f"\n  Completed in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
