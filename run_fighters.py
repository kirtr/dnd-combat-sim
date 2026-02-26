#!/usr/bin/env python3
"""Fighter-only comparison: find the best level 2 fighter."""

from __future__ import annotations
from pathlib import Path
from sim.runner import run_simulations
from sim.loader import load_build

BUILDS_DIR = Path(__file__).parent / "data" / "builds"

# Fighters only — organized by style × species
FIGHTERS = [
    # GWF variants
    "fighter_gwf_greatsword_2",          # GWF Orc
    "goliath_fire_fighter_gwf_2",        # GWF Fire Goliath
    "goliath_hill_fighter_gwf_2",        # GWF Hill Goliath
    "goliath_storm_fighter_gwf_2",       # GWF Storm Goliath
    "fighter_gwf_greatsword_goliath_2",  # GWF Frost Goliath
    "human_fighter_gwf_2",              # GWF Human (SA+Tough)
    # TWF variants
    "fighter_twf_scimitar_shortsword_2", # TWF Orc
    "goliath_fire_fighter_twf_2",        # TWF Fire Goliath
    "goliath_hill_fighter_twf_2",        # TWF Hill Goliath
    "human_fighter_twf_2",              # TWF Human (SA+Tough)
    # Dueling variants
    "fighter_dueling_longsword_orc_2",   # Dueling Orc
    "goliath_fire_fighter_dueling_2",    # Dueling Fire Goliath
    # Defense
    "fighter_defense_greatsword_2",      # Defense Orc
    # Archery
    "fighter_archery_longbow_2",         # Archery Elf
]

N = 3000

def main():
    builds = {}
    for name in FIGHTERS:
        path = BUILDS_DIR / f"{name}.yaml"
        if not path.exists():
            print(f"  SKIP: {name}")
            continue
        builds[name] = load_build(path)

    print("=" * 85)
    print("  FIGHTER BUILDS — Level 2 Summary")
    print("=" * 85)
    for name, c in builds.items():
        fs = c.fighting_style or "N/A"
        anc = c.giant_ancestry or ""
        spec = "Goliath" if anc else ("Orc" if "orc" in str(c.species_traits) else "Human" if "resourceful" in str(c.species_traits) else "Elf")
        print(f"  {c.name:<40} HP:{c.max_hp:>3}  AC:{c.ac:>2}  SPD:{c.speed:>2}  Style:{fs:<6} Species:{spec} {anc}")

    # Round-robin
    results = {}
    keys = list(builds.keys())
    total = len(keys) * (len(keys) - 1) // 2
    done = 0
    for i, a in enumerate(keys):
        for b in keys[i+1:]:
            done += 1
            stats = run_simulations(
                str(BUILDS_DIR / f"{a}.yaml"),
                str(BUILDS_DIR / f"{b}.yaml"),
                n=N,
            )
            results[(a, b)] = (
                stats["combatant_a"]["win_rate"],
                stats["combatant_b"]["win_rate"],
                stats["avg_rounds"],
            )

    # Ranking
    win_rates = {name: [] for name in builds}
    for (a, b), (ap, bp, _) in results.items():
        win_rates[a].append(ap)
        win_rates[b].append(bp)

    ranking = []
    for name in builds:
        rates = win_rates[name]
        if rates:
            ranking.append((name, sum(rates)/len(rates), builds[name]))
    ranking.sort(key=lambda x: x[1], reverse=True)

    print("\n" + "=" * 85)
    print("  OVERALL RANKING")
    print("=" * 85)
    for rank, (name, avg, c) in enumerate(ranking, 1):
        print(f"  {rank:>2}. {c.name:<40} Avg Win Rate: {avg:.1f}%")

    # Style comparison (same species: Orc)
    print("\n" + "=" * 85)
    print("  STYLE COMPARISON (Orc, head-to-head)")
    print("=" * 85)
    orc_styles = [n for n in builds if n in [
        "fighter_gwf_greatsword_2", "fighter_twf_scimitar_shortsword_2",
        "fighter_dueling_longsword_orc_2", "fighter_defense_greatsword_2",
    ]]
    for i, a in enumerate(orc_styles):
        for b in orc_styles[i+1:]:
            key = (a, b) if (a, b) in results else (b, a)
            if key in results:
                ap, bp, ar = results[key]
                print(f"  {builds[key[0]].name} ({ap:.1f}%) vs {builds[key[1]].name} ({bp:.1f}%) — {ar:.1f}r")

    # Species comparison (same style: GWF)
    print("\n" + "=" * 85)
    print("  SPECIES COMPARISON (GWF, head-to-head)")
    print("=" * 85)
    gwf = [n for n in builds if "gwf" in n]
    for i, a in enumerate(gwf):
        for b in gwf[i+1:]:
            key = (a, b) if (a, b) in results else (b, a)
            if key in results:
                ap, bp, ar = results[key]
                print(f"  {builds[key[0]].name} ({ap:.1f}%) vs {builds[key[1]].name} ({bp:.1f}%) — {ar:.1f}r")

    # Species comparison (same style: TWF)
    print("\n" + "=" * 85)
    print("  SPECIES COMPARISON (TWF, head-to-head)")
    print("=" * 85)
    twf = [n for n in builds if "twf" in n]
    for i, a in enumerate(twf):
        for b in twf[i+1:]:
            key = (a, b) if (a, b) in results else (b, a)
            if key in results:
                ap, bp, ar = results[key]
                print(f"  {builds[key[0]].name} ({ap:.1f}%) vs {builds[key[1]].name} ({bp:.1f}%) — {ar:.1f}r")

    # Top 5 head-to-head
    top5 = [name for name, _, _ in ranking[:5]]
    print("\n" + "=" * 85)
    print("  TOP 5 HEAD-TO-HEAD")
    print("=" * 85)
    for i, a in enumerate(top5):
        for b in top5[i+1:]:
            key = (a, b) if (a, b) in results else (b, a)
            if key in results:
                ap, bp, ar = results[key]
                print(f"  {builds[key[0]].name} ({ap:.1f}%) vs {builds[key[1]].name} ({bp:.1f}%) — {ar:.1f}r")

if __name__ == "__main__":
    main()
