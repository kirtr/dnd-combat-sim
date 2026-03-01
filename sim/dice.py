"""Dice rolling and expression evaluation."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DiceResult:
    total: int
    rolls: tuple[int, ...]
    expression: str


@dataclass(frozen=True)
class D20Result:
    """Result of a d20 roll, with both raw values for adv/disadv display."""
    chosen: int
    other: int | None  # second die if adv/disadv, else None
    advantage: bool
    disadvantage: bool

    @property
    def value(self) -> int:
        return self.chosen


def roll(n: int, sides: int) -> tuple[int, ...]:
    """Roll n dice with given sides, return individual results."""
    return tuple(random.randint(1, sides) for _ in range(n))


def roll_with_minimum(n: int, sides: int, minimum: int = 1) -> tuple[int, ...]:
    """Roll n dice, treating any result below *minimum* as *minimum*."""
    results = []
    for _ in range(n):
        r = random.randint(1, sides)
        results.append(max(r, minimum))
    return tuple(results)


def d20(advantage: bool = False, disadvantage: bool = False) -> int:
    """Roll a d20 with advantage/disadvantage. Returns just the chosen value."""
    return d20_detail(advantage=advantage, disadvantage=disadvantage).chosen


def d20_detail(advantage: bool = False, disadvantage: bool = False) -> D20Result:
    """Roll a d20, returning full detail including both dice for adv/disadv."""
    if advantage and disadvantage:
        result = random.randint(1, 20)
        return D20Result(chosen=result, other=None, advantage=False, disadvantage=False)
    if advantage:
        a, b = random.randint(1, 20), random.randint(1, 20)
        return D20Result(chosen=max(a, b), other=min(a, b), advantage=True, disadvantage=False)
    if disadvantage:
        a, b = random.randint(1, 20), random.randint(1, 20)
        return D20Result(chosen=min(a, b), other=max(a, b), advantage=False, disadvantage=True)
    result = random.randint(1, 20)
    return D20Result(chosen=result, other=None, advantage=False, disadvantage=False)


# Simple dice expression parser: "2d6", "1d10+5", "3d8+2d6+3"
_DICE_RE = re.compile(r"(\d+)d(\d+)")
_MOD_RE = re.compile(r"([+-]\d+)(?!.*d)")


def parse_dice(expr: str) -> list[tuple[int, int]]:
    """Parse dice expression into list of (count, sides) pairs."""
    return [(int(m.group(1)), int(m.group(2))) for m in _DICE_RE.finditer(expr)]


def _calc_flat_mod(expr: str) -> int:
    """Extract the flat modifier from a dice expression."""
    flat = 0
    clean = _DICE_RE.sub("", expr)
    for match in _MOD_RE.finditer(clean):
        flat += int(match.group(1))
    leftover = _DICE_RE.sub("", expr)
    leftover = _MOD_RE.sub("", leftover).strip().lstrip("+")
    if leftover:
        try:
            flat += int(leftover)
        except ValueError:
            pass
    return flat


def eval_dice(expr: str, minimum: int | None = None) -> DiceResult:
    """Evaluate a dice expression like '2d6+5'."""
    all_rolls: list[int] = []
    total = 0

    for match in _DICE_RE.finditer(expr):
        n, sides = int(match.group(1)), int(match.group(2))
        if minimum is not None:
            rolls = roll_with_minimum(n, sides, minimum)
        else:
            rolls = roll(n, sides)
        all_rolls.extend(rolls)
        total += sum(rolls)

    total += _calc_flat_mod(expr)

    return DiceResult(total=total, rolls=tuple(all_rolls), expression=expr)


@dataclass(frozen=True)
class SavageResult:
    """Result of a Savage Attacker double-roll."""
    total: int
    rolls: tuple[int, ...]  # the chosen (best) set
    set1: tuple[int, ...]
    set2: tuple[int, ...]
    expression: str


def eval_dice_twice_take_best(expr: str, minimum: int | None = None) -> SavageResult:
    """Roll the dice portion twice and keep the better set (Savage Attacker)."""
    dice_parts = parse_dice(expr)
    flat = _calc_flat_mod(expr)

    def _roll_dice():
        rolls: list[int] = []
        for n, sides in dice_parts:
            if minimum is not None:
                rolls.extend(roll_with_minimum(n, sides, minimum))
            else:
                rolls.extend(roll(n, sides))
        return tuple(rolls)

    r1 = _roll_dice()
    r2 = _roll_dice()
    best = r1 if sum(r1) >= sum(r2) else r2
    total_val = sum(best) + flat
    return SavageResult(
        total=total_val,
        rolls=best,
        set1=r1,
        set2=r2,
        expression=expr,
    )


# ---------------------------------------------------------------------------
# Legacy roll log — kept for backward compatibility but no longer used for display
# ---------------------------------------------------------------------------
_roll_log: list[str] = []


def push_roll(entry: str) -> None:
    _roll_log.append(entry)


def flush_rolls() -> str:
    global _roll_log
    out = f"[{', '.join(_roll_log)}]" if _roll_log else "[]"
    _roll_log = []
    return out


def clear_rolls() -> None:
    global _roll_log
    _roll_log = []
