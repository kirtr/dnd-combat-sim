"""
Initiative test: Berserker Greatsword Orc L5 vs Battle Master S&B Stone Goliath L5
10,000 trials
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sim.loader import load_build
from sim.combat import roll_initiative

TRIALS = 10_000

berserker_path = "data/builds/berserker_greatsword_orc_5.yaml"
goliath_path   = "data/builds/battlemaster_sb_stone_goliath_5.yaml"

berserk = load_build(berserker_path)
goliath = load_build(goliath_path)

wins = ties = losses = 0

for _ in range(TRIALS):
    b_init = roll_initiative(berserk)
    g_init = roll_initiative(goliath)
    if b_init > g_init:
        wins += 1
    elif b_init == g_init:
        ties += 1
    else:
        losses += 1

print(f"\n{'='*52}")
print(f"  Initiative Test — {TRIALS:,} trials")
print(f"{'='*52}")
print(f"  Berserker  DEX mod: +{berserk.dex_mod}  initiative_bonus: +{berserk.initiative_bonus}")
print(f"  Goliath    DEX mod: +{goliath.dex_mod}  initiative_bonus: +{goliath.initiative_bonus}")
print(f"{'='*52}")
print(f"  Berserker WINS : {wins:>5}  ({wins/TRIALS*100:.1f}%)")
print(f"  TIES           : {ties:>5}  ({ties/TRIALS*100:.1f}%)")
print(f"  Berserker LOSES: {losses:>5}  ({losses/TRIALS*100:.1f}%)")
print(f"{'='*52}\n")
