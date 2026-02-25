"""Tests for dice rolling and expression evaluation."""

import random
from sim.dice import d20, eval_dice, eval_dice_twice_take_best, roll, roll_with_minimum


def test_roll_basic():
    """Roll produces correct number of dice in valid range."""
    random.seed(42)
    results = roll(4, 6)
    assert len(results) == 4
    assert all(1 <= r <= 6 for r in results)


def test_d20_normal():
    """Normal d20 roll is between 1 and 20."""
    random.seed(42)
    for _ in range(100):
        r = d20()
        assert 1 <= r <= 20


def test_d20_advantage():
    """Advantage takes the higher of two rolls."""
    random.seed(42)
    results = [d20(advantage=True) for _ in range(1000)]
    # Average should be higher than 10.5 (normal average)
    avg = sum(results) / len(results)
    assert avg > 12.0, f"Advantage average {avg} should be > 12"


def test_d20_disadvantage():
    """Disadvantage takes the lower of two rolls."""
    random.seed(42)
    results = [d20(disadvantage=True) for _ in range(1000)]
    avg = sum(results) / len(results)
    assert avg < 9.0, f"Disadvantage average {avg} should be < 9"


def test_d20_both_cancel():
    """Advantage + disadvantage cancel to a normal roll."""
    random.seed(42)
    results = [d20(advantage=True, disadvantage=True) for _ in range(10000)]
    avg = sum(results) / len(results)
    assert 9.5 < avg < 11.5, f"Cancelled avg {avg} should be ~10.5"


def test_eval_dice_simple():
    """Parse and evaluate '2d6+5'."""
    random.seed(42)
    result = eval_dice("2d6+5")
    assert result.expression == "2d6+5"
    assert len(result.rolls) == 2
    assert all(1 <= r <= 6 for r in result.rolls)
    assert result.total == sum(result.rolls) + 5


def test_eval_dice_single():
    """Parse '1d10'."""
    random.seed(42)
    result = eval_dice("1d10")
    assert len(result.rolls) == 1
    assert 1 <= result.rolls[0] <= 10
    assert result.total == result.rolls[0]


def test_eval_dice_gwf_minimum():
    """GWF: minimum of 3 on each die."""
    random.seed(42)
    results = [eval_dice("2d6", minimum=3) for _ in range(1000)]
    for r in results:
        assert all(die >= 3 for die in r.rolls), f"Die below 3: {r.rolls}"
    # Average per die should be (3+3+4+5+6)/5 = 4.2 instead of 3.5
    avg_per_die = sum(sum(r.rolls) for r in results) / (2 * len(results))
    assert avg_per_die > 3.8, f"GWF avg per die {avg_per_die} should be > 3.8"


def test_roll_with_minimum():
    """roll_with_minimum enforces floor."""
    random.seed(42)
    for _ in range(200):
        results = roll_with_minimum(3, 6, minimum=3)
        assert all(r >= 3 for r in results)


def test_eval_dice_twice_take_best():
    """Savage Attacker: roll twice, take best dice."""
    random.seed(42)
    results_best = [eval_dice_twice_take_best("2d6") for _ in range(1000)]
    results_normal = [eval_dice("2d6") for _ in range(1000)]
    avg_best = sum(r.total for r in results_best) / len(results_best)
    avg_normal = sum(r.total for r in results_normal) / len(results_normal)
    # Best-of-two should average higher
    assert avg_best > avg_normal, f"Best {avg_best} should exceed normal {avg_normal}"


def test_distribution_sanity():
    """d20 distribution: each face should appear roughly 5% of the time."""
    random.seed(42)
    counts = [0] * 21
    n = 100000
    for _ in range(n):
        counts[d20()] += 1
    for face in range(1, 21):
        pct = counts[face] / n
        assert 0.03 < pct < 0.07, f"Face {face} at {pct:.3f}, expected ~0.05"
