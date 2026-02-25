#!/usr/bin/env python3
"""Run the combat simulator: Fighter GWF vs all other builds."""

from sim.runner import run_tournament

if __name__ == "__main__":
    champion = "fighter_gwf_greatsword_2"
    challengers = [
        "fighter_dueling_longsword_2",
        "fighter_archery_longbow_2",
        "barbarian_berserker_2",
        "monk_open_hand_2",
        "rogue_thief_2",
    ]

    print("D&D 2024 Combat Simulator - Phase 1")
    print("Fighter (GWF Greatsword) vs All Builds")
    print(f"10,000 combats per matchup\n")

    results = run_tournament(champion, challengers, n=10000)

    # Summary table
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Matchup':<45} {'Win%':>6}")
    print("-" * 52)
    for r in results:
        label = f"vs {r['build_b']}"
        print(f"  {label:<43} {r['a_win_rate']:5.1f}%")
