#!/usr/bin/env python3
"""Compare all Goliath ancestries head-to-head, both GWF and TWF."""

from pathlib import Path
from sim.runner import run_simulations
from sim.loader import load_build

BUILDS_DIR = Path(__file__).parent / "data" / "builds"
N = 3000

def run_group(label, builds):
    chars = {}
    for name in builds:
        path = BUILDS_DIR / f"{name}.yaml"
        if path.exists():
            chars[name] = load_build(path)
        else:
            print(f"  SKIP: {name}")

    results = {}
    keys = list(chars.keys())
    for i, a in enumerate(keys):
        for b in keys[i+1:]:
            stats = run_simulations(str(BUILDS_DIR / f"{a}.yaml"), str(BUILDS_DIR / f"{b}.yaml"), n=N)
            results[(a, b)] = (stats["combatant_a"]["win_rate"], stats["combatant_b"]["win_rate"], stats["avg_rounds"])

    win_rates = {n: [] for n in chars}
    for (a, b), (ap, bp, _) in results.items():
        win_rates[a].append(ap)
        win_rates[b].append(bp)

    ranking = [(n, sum(wr)/len(wr), chars[n]) for n, wr in win_rates.items() if wr]
    ranking.sort(key=lambda x: x[1], reverse=True)

    print(f"\n  {label} RANKING:")
    for rank, (name, avg, c) in enumerate(ranking, 1):
        print(f"  {rank}. {c.name:<35} {avg:.1f}%")

    print(f"\n  {label} HEAD-TO-HEAD:")
    for (a, b), (ap, bp, ar) in results.items():
        print(f"  {chars[a].name} ({ap:.1f}%) vs {chars[b].name} ({bp:.1f}%) — {ar:.1f}r")

def main():
    print("=" * 75)
    print("  GOLIATH ANCESTRY COMPARISON + ORC BASELINE")
    print("=" * 75)

    gwf_builds = [
        "fighter_gwf_greatsword_2",           # Orc baseline
        "goliath_fire_fighter_gwf_2",         # Fire
        "goliath_frost_fighter_gwf_2",        # Frost (NEW)
        "fighter_gwf_greatsword_goliath_2",   # Stone
        "goliath_hill_fighter_gwf_2",         # Hill
        "goliath_storm_fighter_gwf_2",        # Storm
    ]
    run_group("GWF", gwf_builds)

    twf_builds = [
        "fighter_twf_scimitar_shortsword_2",  # Orc baseline
        "goliath_fire_fighter_twf_2",         # Fire
        "goliath_frost_fighter_twf_2",        # Frost (NEW)
        "goliath_hill_fighter_twf_2",         # Hill
    ]
    run_group("TWF", twf_builds)

if __name__ == "__main__":
    main()
