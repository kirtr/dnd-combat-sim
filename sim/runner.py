"""Monte Carlo runner: N combats, collect stats."""

from __future__ import annotations
import statistics
from .loader import load_build_by_name
from .combat import run_combat
from .tactics import load_tactics


def run_matchup(
    build_a: str,
    build_b: str,
    n: int = 10000,
    tactic_a: str = "aggressive",
    tactic_b: str = "aggressive",
    verbose_sample: bool = False,
) -> dict:
    """Run N combats between two builds. Returns stats dict."""
    char_a = load_build_by_name(build_a)
    char_b = load_build_by_name(build_b)
    tactics_a = load_tactics(tactic_a)
    tactics_b = load_tactics(tactic_b)

    a_wins = 0
    b_wins = 0
    draws = 0
    rounds_list = []
    a_hp_remaining = []
    b_hp_remaining = []
    sample_log: list[str] = []

    for i in range(n):
        verbose = verbose_sample and i == 0
        # Deep copy chars for each combat
        ca = char_a.deep_copy()
        cb = char_b.deep_copy()
        state = run_combat(ca, cb, tactics_a, tactics_b, verbose=verbose)

        if verbose:
            sample_log = state.combat_log

        if not cb.is_alive and ca.is_alive:
            a_wins += 1
            a_hp_remaining.append(ca.current_hp)
        elif not ca.is_alive and cb.is_alive:
            b_wins += 1
            b_hp_remaining.append(cb.current_hp)
        else:
            draws += 1

        rounds_list.append(state.round_number)

    return {
        "build_a": char_a.name,
        "build_b": char_b.name,
        "n": n,
        "a_wins": a_wins,
        "b_wins": b_wins,
        "draws": draws,
        "a_win_rate": a_wins / n * 100,
        "b_win_rate": b_wins / n * 100,
        "avg_rounds": statistics.mean(rounds_list),
        "median_rounds": statistics.median(rounds_list),
        "a_avg_hp_remaining": statistics.mean(a_hp_remaining) if a_hp_remaining else 0,
        "b_avg_hp_remaining": statistics.mean(b_hp_remaining) if b_hp_remaining else 0,
        "sample_log": sample_log,
    }


def print_matchup(stats: dict) -> None:
    """Pretty print matchup results."""
    print(f"\n{'='*60}")
    print(f"  {stats['build_a']}  vs  {stats['build_b']}")
    print(f"  {stats['n']} combats")
    print(f"{'='*60}")
    print(f"  {stats['build_a']:>35s}: {stats['a_win_rate']:5.1f}% ({stats['a_wins']} wins)")
    print(f"  {stats['build_b']:>35s}: {stats['b_win_rate']:5.1f}% ({stats['b_wins']} wins)")
    if stats['draws']:
        print(f"  {'Draws':>35s}: {stats['draws']}")
    print(f"  {'Avg rounds':>35s}: {stats['avg_rounds']:.1f}")
    if stats['a_avg_hp_remaining']:
        print(f"  {stats['build_a'] + ' avg HP left':>35s}: {stats['a_avg_hp_remaining']:.1f}")
    if stats['b_avg_hp_remaining']:
        print(f"  {stats['build_b'] + ' avg HP left':>35s}: {stats['b_avg_hp_remaining']:.1f}")
    print()


def run_tournament(
    champion: str,
    challengers: list[str],
    n: int = 10000,
) -> list[dict]:
    """Run champion vs each challenger."""
    results = []
    for challenger in challengers:
        stats = run_matchup(champion, challenger, n=n, verbose_sample=True)
        print_matchup(stats)
        results.append(stats)
    return results
