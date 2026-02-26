#!/usr/bin/env python3
"""Focused comparison: best fighter variants + rogue, no barbarian."""

from __future__ import annotations
from pathlib import Path
from sim.runner import run_simulations
from sim.loader import load_build

BUILDS_DIR = Path(__file__).parent / "data" / "builds"

# Core fighter styles + species variants + rogues (no barbarian, no monk)
ALL_BUILDS = [
    # Core fighter styles (orc baseline)
    "fighter_gwf_greatsword_2",          # GWF Orc
    "fighter_dueling_longsword_2",       # Dueling Human
    "fighter_defense_greatsword_2",      # Defense Orc
    "fighter_twf_scimitar_shortsword_2", # TWF Orc
    # Goliath variants
    "goliath_fire_fighter_gwf_2",        # Fire GWF
    "goliath_fire_fighter_twf_2",        # Fire TWF
    "goliath_hill_fighter_gwf_2",        # Hill GWF
    "goliath_hill_fighter_twf_2",        # Hill TWF
    "goliath_storm_fighter_gwf_2",       # Storm GWF
    "fighter_gwf_greatsword_goliath_2",  # Frost GWF
    # Human variants
    "human_fighter_gwf_2",              # Human GWF (SA+Tough+HI)
    "human_fighter_twf_2",              # Human TWF (SA+Tough+HI)
    # Rogues
    "rogue_dual_wield_2",               # DW Rogue
]

N = 3000

def main():
    builds = {}
    for name in ALL_BUILDS:
        path = BUILDS_DIR / f"{name}.yaml"
        if not path.exists():
            print(f"  SKIP: {name} (not found)")
            continue
        builds[name] = load_build(path)

    # Print build summary
    print("=" * 80)
    print("  BUILD SUMMARY (Fighters + Rogue, Level 2)")
    print("=" * 80)
    for name, char in builds.items():
        fs = char.fighting_style or "N/A"
        anc = f" ({char.giant_ancestry})" if char.giant_ancestry else ""
        print(f"  {char.name:<40} HP:{char.max_hp:>3}  AC:{char.ac:>2}  SPD:{char.speed:>2}")

    # Round-robin
    results = {}
    for i, name_a in enumerate(list(builds.keys())):
        for name_b in list(builds.keys())[i+1:]:
            stats = run_simulations(
                str(BUILDS_DIR / f"{name_a}.yaml"),
                str(BUILDS_DIR / f"{name_b}.yaml"),
                n=N,
            )
            a_pct = stats["combatant_a"]["win_rate"]
            b_pct = stats["combatant_b"]["win_rate"]
            results[(name_a, name_b)] = (a_pct, b_pct, stats["avg_rounds"])

    # Ranking
    win_rates = {name: [] for name in builds}
    for (a, b), (a_pct, b_pct, _) in results.items():
        win_rates[a].append(a_pct)
        win_rates[b].append(b_pct)

    ranking = []
    for name in builds:
        if win_rates[name]:
            avg = sum(win_rates[name]) / len(win_rates[name])
            ranking.append((name, avg, builds[name]))
    ranking.sort(key=lambda x: x[1], reverse=True)

    print("\n" + "=" * 80)
    print("  OVERALL RANKING (avg win rate, no barbarian)")
    print("=" * 80)
    for rank, (name, avg_wr, char) in enumerate(ranking, 1):
        print(f"  {rank:>2}. {char.name:<40} Avg Win Rate: {avg_wr:.1f}%")

    # Species comparison: same style, different species
    print("\n" + "=" * 80)
    print("  SPECIES COMPARISON — GWF Greatsword")
    print("=" * 80)
    gwf_builds = [n for n in builds if "gwf" in n]
    for i, a in enumerate(gwf_builds):
        for b in gwf_builds[i+1:]:
            key = (a, b) if (a, b) in results else (b, a)
            if key in results:
                ap, bp, ar = results[key]
                print(f"  {builds[key[0]].name} ({ap:.1f}%) vs {builds[key[1]].name} ({bp:.1f}%) — {ar:.1f}r")

    print("\n" + "=" * 80)
    print("  SPECIES COMPARISON — TWF Scimitar+SS")
    print("=" * 80)
    twf_builds = [n for n in builds if "twf" in n]
    for i, a in enumerate(twf_builds):
        for b in twf_builds[i+1:]:
            key = (a, b) if (a, b) in results else (b, a)
            if key in results:
                ap, bp, ar = results[key]
                print(f"  {builds[key[0]].name} ({ap:.1f}%) vs {builds[key[1]].name} ({bp:.1f}%) — {ar:.1f}r")

if __name__ == "__main__":
    main()
