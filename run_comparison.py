#!/usr/bin/env python3
"""Run all build comparisons and output findings."""

from __future__ import annotations
import sys
import os
from pathlib import Path
from sim.runner import run_simulations
from sim.loader import load_build

BUILDS_DIR = Path(__file__).parent / "data" / "builds"

ALL_BUILDS = [
    "fighter_gwf_greatsword_2",
    "fighter_dueling_longsword_2",
    "fighter_defense_greatsword_2",
    "fighter_archery_longbow_2",
    "barbarian_greatsword_2",
    "monk_2",
    "rogue_rapier_2",
]

N = 10000


def main():
    # Load all builds for stats
    builds = {}
    for name in ALL_BUILDS:
        path = BUILDS_DIR / f"{name}.yaml"
        if path.exists():
            builds[name] = load_build(path)

    # Print build summary
    print("=" * 70)
    print("  BUILD SUMMARY")
    print("=" * 70)
    for name, char in builds.items():
        fs = char.fighting_style or "N/A"
        weapons = ", ".join(w.name for w in char.weapons)
        print(f"  {char.name:<35} HP:{char.max_hp:>3}  AC:{char.ac:>2}  STR:{char.ability_scores.modifier('strength'):>+2}  DEX:{char.ability_scores.modifier('dexterity'):>+2}  Style:{fs}")
        print(f"    Weapons: {weapons}")

    # Round-robin: every build vs every other build
    print("\n" + "=" * 70)
    print("  ROUND-ROBIN RESULTS (10,000 combats each)")
    print("=" * 70)

    results = {}  # (name_a, name_b) -> (win_rate_a, win_rate_b, avg_rounds)

    for i, name_a in enumerate(ALL_BUILDS):
        path_a = BUILDS_DIR / f"{name_a}.yaml"
        if not path_a.exists():
            continue
        for name_b in ALL_BUILDS[i+1:]:
            path_b = BUILDS_DIR / f"{name_b}.yaml"
            if not path_b.exists():
                continue

            stats = run_simulations(str(path_a), str(path_b), n=N)
            a_pct = stats["combatant_a"]["win_rate"]
            b_pct = stats["combatant_b"]["win_rate"]

            char_a = builds[name_a]
            char_b = builds[name_b]
            results[(name_a, name_b)] = (a_pct, b_pct, stats["avg_rounds"])

            print(f"\n  {char_a.name} vs {char_b.name}")
            print(f"    {char_a.name}: {a_pct:.1f}%  |  {char_b.name}: {b_pct:.1f}%  |  Avg Rounds: {stats['avg_rounds']:.1f}")

    # Win totals for ranking
    print("\n" + "=" * 70)
    print("  OVERALL RANKING (by avg win rate across all matchups)")
    print("=" * 70)

    win_rates = {name: [] for name in ALL_BUILDS}
    for (a, b), (a_pct, b_pct, _) in results.items():
        win_rates[a].append(a_pct)
        win_rates[b].append(b_pct)

    ranking = []
    for name in ALL_BUILDS:
        if win_rates[name]:
            avg = sum(win_rates[name]) / len(win_rates[name])
            ranking.append((name, avg, builds[name]))

    ranking.sort(key=lambda x: x[1], reverse=True)

    for rank, (name, avg_wr, char) in enumerate(ranking, 1):
        matchups = " | ".join(f"{wr:.0f}%" for wr in win_rates[name])
        print(f"  {rank}. {char.name:<35} Avg Win Rate: {avg_wr:.1f}%")

    # Fighter style comparison
    fighter_builds = [n for n in ALL_BUILDS if n.startswith("fighter_")]
    if len(fighter_builds) > 1:
        print("\n" + "=" * 70)
        print("  FIGHTER STYLE COMPARISON (head-to-head)")
        print("=" * 70)
        for i, fa in enumerate(fighter_builds):
            for fb in fighter_builds[i+1:]:
                key = (fa, fb) if (fa, fb) in results else (fb, fa)
                if key in results:
                    a_pct, b_pct, avg_r = results[key]
                    ca = builds[key[0]]
                    cb = builds[key[1]]
                    print(f"  {ca.name} ({a_pct:.1f}%) vs {cb.name} ({b_pct:.1f}%) — {avg_r:.1f} rounds")


if __name__ == "__main__":
    main()
