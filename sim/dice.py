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


def roll(n: int, sides: int) -> tuple[int, ...]:
    """Roll n dice with given sides, return individual results."""
    return tuple(random.randint(1, sides) for _ in range(n))


def roll_with_minimum(n: int, sides: int, minimum: int = 1) -> tuple[int, ...]:
    """Roll n dice, treating any result below *minimum* as *minimum*.

    This implements 2024 Great Weapon Fighting: any 1 or 2 on a damage die
    is treated as a 3 (minimum=3).
    """
    results = []
    for _ in range(n):
        r = random.randint(1, sides)
        results.append(max(r, minimum))
    return tuple(results)


def d20(advantage: bool = False, disadvantage: bool = False) -> int:
    """Roll a d20 with advantage/disadvantage.  They cancel if both true."""
    if advantage and disadvantage:
        return random.randint(1, 20)
    if advantage:
        return max(random.randint(1, 20), random.randint(1, 20))
    if disadvantage:
        return min(random.randint(1, 20), random.randint(1, 20))
    return random.randint(1, 20)


# Simple dice expression parser: "2d6", "1d10+5", "3d8+2d6+3"
_DICE_RE = re.compile(r"(\d+)d(\d+)")
_MOD_RE = re.compile(r"([+-]\d+)(?!.*d)")


def parse_dice(expr: str) -> list[tuple[int, int]]:
    """Parse dice expression into list of (count, sides) pairs."""
    return [(int(m.group(1)), int(m.group(2))) for m in _DICE_RE.finditer(expr)]


def eval_dice(expr: str, minimum: int | None = None) -> DiceResult:
    """Evaluate a dice expression like '2d6+5'.

    If *minimum* is set, every individual die result below that value is
    raised to it (used for 2024 GWF where 1s/2s become 3s).
    """
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

    # Add flat modifiers
    clean = _DICE_RE.sub("", expr)
    for match in _MOD_RE.finditer(clean):
        total += int(match.group(1))

    # Handle leading number without sign (e.g. the "+5" part handled above,
    # but also bare "5" if the expression is just a number)
    leftover = _DICE_RE.sub("", expr)
    leftover = _MOD_RE.sub("", leftover).strip().lstrip("+")
    if leftover:
        try:
            total += int(leftover)
        except ValueError:
            pass

    return DiceResult(total=total, rolls=tuple(all_rolls), expression=expr)


def eval_dice_twice_take_best(expr: str, minimum: int | None = None) -> DiceResult:
    """Roll the dice portion of *expr* twice and keep the better set.

    Implements 2024 Savage Attacker: 'roll the weapon's damage dice twice
    and use either roll'.  Flat modifiers are added once.
    """
    dice_parts = parse_dice(expr)
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
    return DiceResult(
        total=sum(best) + flat,
        rolls=best,
        expression=expr,
    )
