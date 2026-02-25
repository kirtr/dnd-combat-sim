"""Monte Carlo runner: N combats, collect stats."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field

from sim.combat import run_combat
from sim.loader import load_build
from sim.tactics import load_tactics


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
    }
    return results


def print_results(results: dict) -> None:
    n = results["n"]
    a = results["combatant_a"]
    b = results["combatant_b"]

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
