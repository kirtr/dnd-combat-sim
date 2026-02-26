"""D&D 2024 Combat Simulator CLI.

Usage: ./sim <mode> [options]
Modes: rank, compare, dps, fight, show, list
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from sim.loader import load_build
from sim.runner import run_simulations, print_results
from sim.combat import run_combat
from sim.tactics import load_tactics

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_BUILDS_DIR = _DATA_DIR / "builds"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_build_names() -> list[str]:
    return sorted(p.stem for p in _BUILDS_DIR.glob("*.yaml"))


def _load_tags(path: Path) -> list[str]:
    """Quick YAML tag extraction without full load."""
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("tags", [])


def _filter_by_tags(tags: list[str]) -> list[str]:
    """Return build names matching ALL given tags."""
    if not tags:
        return _all_build_names()
    result = []
    for name in _all_build_names():
        build_tags = _load_tags(_BUILDS_DIR / f"{name}.yaml")
        if all(t in build_tags for t in tags):
            result.append(name)
    return result


def _resolve_builds(args) -> list[str]:
    """Get build list from --builds or --tag flags."""
    if hasattr(args, "builds") and args.builds:
        return [b.strip() for b in args.builds.split(",")]
    tags = getattr(args, "tag", []) or []
    builds = _filter_by_tags(tags)
    if not builds:
        print(f"  No builds found matching tags: {tags}")
        sys.exit(1)
    return builds


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def cmd_list(args):
    """List available builds."""
    tags = args.tag or []
    builds = _filter_by_tags(tags)
    if tags:
        print(f"  Builds matching tags {tags}: ({len(builds)})")
    else:
        print(f"  All builds: ({len(builds)})")
    for name in builds:
        build_tags = _load_tags(_BUILDS_DIR / f"{name}.yaml")
        print(f"    {name:<45} {' '.join(build_tags)}")


def cmd_show(args):
    """Show build details."""
    name = args.build
    path = _BUILDS_DIR / f"{name}.yaml"
    if not path.exists():
        print(f"  Build not found: {name}")
        sys.exit(1)
    char = load_build(str(path))
    print(f"  Name:      {char.name}")
    print(f"  Class:     {char.class_name} (level {char.level})")
    print(f"  HP:        {char.max_hp}")
    print(f"  AC:        {char.ac}")
    print(f"  Speed:     {char.speed} ft")
    print(f"  STR:{char.str_mod:+d}  DEX:{char.dex_mod:+d}  CON:{char.con_mod:+d}")
    print(f"  Style:     {char.fighting_style or 'N/A'}")
    print(f"  Weapons:   {', '.join(w.name for w in char.weapons)}")
    print(f"  Features:  {', '.join(char.features)}")
    print(f"  Resources: {', '.join(f'{r.name}({r.current})' for r in char.resources.values())}")
    if char.giant_ancestry:
        print(f"  Ancestry:  {char.giant_ancestry}")
    tags = _load_tags(path)
    if tags:
        print(f"  Tags:      {' '.join(tags)}")


def cmd_fight(args):
    """Run verbose 1v1 combats."""
    n = args.n or 1
    path_a = _BUILDS_DIR / f"{args.build1}.yaml"
    path_b = _BUILDS_DIR / f"{args.build2}.yaml"
    results = run_simulations(str(path_a), str(path_b), n=n, verbose=True)
    print_results(results)


def cmd_compare(args):
    """Head-to-head between specific builds."""
    builds = _resolve_builds(args)
    if len(builds) < 2:
        print("  Need at least 2 builds to compare.")
        sys.exit(1)

    n = args.n or 3000
    print(f"  Comparing {len(builds)} builds, {n} combats each\n")

    for i, a in enumerate(builds):
        for b in builds[i + 1:]:
            pa = _BUILDS_DIR / f"{a}.yaml"
            pb = _BUILDS_DIR / f"{b}.yaml"
            if not pa.exists() or not pb.exists():
                continue
            stats = run_simulations(str(pa), str(pb), n=n)
            ca = stats["combatant_a"]
            cb = stats["combatant_b"]
            print(f"  {ca['name']} ({ca['win_rate']:.1f}%) vs {cb['name']} ({cb['win_rate']:.1f}%) — {stats['avg_rounds']:.1f}r")


def cmd_rank(args):
    """Round-robin ranking within a filtered set."""
    builds = _resolve_builds(args)
    n = args.n or 3000

    chars = {}
    for name in builds:
        path = _BUILDS_DIR / f"{name}.yaml"
        if path.exists():
            chars[name] = load_build(str(path))

    if len(chars) < 2:
        print("  Need at least 2 builds to rank.")
        sys.exit(1)

    print(f"  Ranking {len(chars)} builds, {n} combats per matchup")
    print(f"  Total matchups: {len(chars) * (len(chars) - 1) // 2}\n")

    # Summary
    for name, c in chars.items():
        fs = c.fighting_style or "—"
        print(f"  {c.name:<40} HP:{c.max_hp:>3} AC:{c.ac:>2} SPD:{c.speed:>2}")

    results = {}
    keys = list(chars.keys())
    start = time.time()
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            stats = run_simulations(
                str(_BUILDS_DIR / f"{a}.yaml"),
                str(_BUILDS_DIR / f"{b}.yaml"),
                n=n,
            )
            results[(a, b)] = (
                stats["combatant_a"]["win_rate"],
                stats["combatant_b"]["win_rate"],
                stats["avg_rounds"],
            )
    elapsed = time.time() - start

    # Compute rankings
    win_rates = {name: [] for name in chars}
    for (a, b), (ap, bp, _) in results.items():
        win_rates[a].append(ap)
        win_rates[b].append(bp)

    ranking = [(n, sum(wr) / len(wr), chars[n]) for n, wr in win_rates.items() if wr]
    ranking.sort(key=lambda x: x[1], reverse=True)

    print(f"\n  {'RANKING':^70}")
    print(f"  {'Rank':<5} {'Build':<40} {'Avg Win%':>10}")
    print("  " + "-" * 57)
    for rank, (name, avg, c) in enumerate(ranking, 1):
        print(f"  {rank:>3}.  {c.name:<40} {avg:>9.1f}%")

    print(f"\n  Completed in {elapsed:.1f}s")


def cmd_dps(args):
    """DPS analysis against static AC targets."""
    from sim.dps import simulate_dpr
    builds = _resolve_builds(args)
    acs = [int(x) for x in (args.ac or "14,16,18").split(",")]
    n = args.n or 5000

    print(f"  DPS Analysis — {n} rounds per measurement\n")

    header = f"  {'Build':<40}"
    for ac in acs:
        header += f" {'AC ' + str(ac):>8}"
    print(header)
    print("  " + "-" * (40 + 9 * len(acs)))

    for name in builds:
        path = _BUILDS_DIR / f"{name}.yaml"
        if not path.exists():
            continue
        char = load_build(str(path))
        row = f"  {char.name:<40}"
        for ac in acs:
            dpr = simulate_dpr(char, ac, n=n, use_surge=args.burst)
            row += f" {dpr:>8.2f}"
        print(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="sim",
        description="D&D 2024 Combat Simulator",
    )
    sub = parser.add_subparsers(dest="mode", help="Simulation mode")

    # list
    p = sub.add_parser("list", help="List available builds")
    p.add_argument("--tag", action="append", help="Filter by tag (repeatable)")

    # show
    p = sub.add_parser("show", help="Show build details")
    p.add_argument("build", help="Build name (without .yaml)")

    # fight
    p = sub.add_parser("fight", help="Run verbose 1v1 combat(s)")
    p.add_argument("--build1", required=True)
    p.add_argument("--build2", required=True)
    p.add_argument("-n", type=int, default=1)

    # compare
    p = sub.add_parser("compare", help="Head-to-head between builds")
    p.add_argument("--builds", help="Comma-separated build names")
    p.add_argument("--tag", action="append", help="Filter by tag")
    p.add_argument("-n", type=int, default=3000)

    # rank
    p = sub.add_parser("rank", help="Round-robin ranking")
    p.add_argument("--builds", help="Comma-separated build names")
    p.add_argument("--tag", action="append", help="Filter by tag")
    p.add_argument("-n", type=int, default=3000)

    # dps
    p = sub.add_parser("dps", help="DPS against static AC")
    p.add_argument("--builds", help="Comma-separated build names")
    p.add_argument("--tag", action="append", help="Filter by tag")
    p.add_argument("--ac", default="14,16,18", help="Comma-separated AC values")
    p.add_argument("-n", type=int, default=5000)
    p.add_argument("--burst", action="store_true", help="First-round burst with Action Surge")

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        return 1

    cmd = {
        "list": cmd_list,
        "show": cmd_show,
        "fight": cmd_fight,
        "compare": cmd_compare,
        "rank": cmd_rank,
        "dps": cmd_dps,
    }
    return cmd[args.mode](args) or 0


if __name__ == "__main__":
    sys.exit(main())
