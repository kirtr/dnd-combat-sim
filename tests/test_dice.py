"""Tests for dice module."""
import random
from sim.dice import d20, eval_dice, roll, roll_with_minimum, eval_dice_twice_take_best


def test_roll_basic():
    random.seed(42)
    result = roll(3, 6)
    assert len(result) == 3
    assert all(1 <= r <= 6 for r in result)


def test_d20_advantage():
    random.seed(42)
    results = [d20(advantage=True) for _ in range(100)]
    avg = sum(results) / len(results)
    assert avg > 11.5  # ~13.8 expected


def test_d20_disadvantage():
    random.seed(42)
    results = [d20(disadvantage=True) for _ in range(100)]
    avg = sum(results) / len(results)
    assert avg < 9.5  # ~7.2 expected


def test_d20_both_cancel():
    random.seed(42)
    results = [d20(advantage=True, disadvantage=True) for _ in range(100)]
    avg = sum(results) / len(results)
    assert 8.5 < avg < 12.5


def test_eval_dice_simple():
    random.seed(42)
    result = eval_dice("2d6")
    assert result.total > 0
    assert len(result.rolls) == 2


def test_eval_dice_with_modifier():
    random.seed(42)
    result = eval_dice("1d8+5")
    assert result.total >= 6


def test_gwf_minimum():
    """GWF with minimum=3 should average higher."""
    random.seed(42)
    normal = [eval_dice("2d6").total for _ in range(1000)]
    random.seed(42)
    gwf = [eval_dice("2d6", minimum=3).total for _ in range(1000)]
    assert sum(gwf) / len(gwf) >= sum(normal) / len(normal)


def test_savage_attacker():
    """Roll twice take best should average higher."""
    random.seed(42)
    normal = [eval_dice("2d6").total for _ in range(1000)]
    random.seed(42)
    savage = [eval_dice_twice_take_best("2d6").total for _ in range(1000)]
    assert sum(savage) / len(savage) >= sum(normal) / len(normal)
