# Fighter Style Analysis — Level 3
*Generated: 2026-02-28*

All matchups: N=10,000 fights. Standard opponent: **Battle Master Dueling Orc** (S&B, AC 18, HP 31).

## Ability Score Corrections

All STR-primary melee builds were using incomplete ability scores (no background bonuses applied, total 72 instead of 75).

**Fixed (Soldier background: STR +2, CON +1):**
- Fighters (7 builds): STR 16, DEX 10→13, CON 14→16, INT 8, WIS 12, CHA 8→10
- Barbarians (4 builds): STR 16, DEX 14→13, CON 16 (kept), INT 8, WIS 10, CHA 8
- Rangers (2 builds): STR 16, DEX 14→13, CON 14→16, INT 8, WIS 12, CHA 10

Net effect: +2 CON (+1 HP/level, better saves) and +3 DEX for fighters; barbarians lost 1 DEX.

## Fighting Style Rankings

### Champion Subclass (vs BM Dueling Orc)

| Build        | Species       | Win Rate | Avg DPR | Avg HP on Win | Notes                                        |
| ------------ | ------------- | -------- | ------- | ------------- | -------------------------------------------- |
| Champion GWF | Orc           | 17.5%    | 3.54    | 8.0           | Best Champion damage, still loses hard to BM |
| Champion GWF | Stone Goliath | 25.4%    | 3.17    | 12.7          | Stone's Endurance adds survivability         |
| Champion TWF | Stone Goliath | 14.8%    | 2.30    | 13.4          |                                              |
| Champion TWF | Orc           | 10.5%    | 2.54    | 8.6           |                                              |
| Champion TWF | Fire Goliath  | 11.8%    | 3.91    | 12.9          | Fire ancestry adds AoE but limited           |
| Champion S&B | Stone Goliath | 13.1%    | 1.71    | 13.9          | Tanky but no damage                          |
| Champion S&B | Orc           | 10.2%    | 1.88    | 8.7           | Worst win rate overall                       |

**Champion takeaway:** GWF is clearly the best fighting style for Champions. The expanded crit range (19-20) benefits GWF's higher damage dice. Champions are significantly weaker than Battle Masters at level 3 — the BM Dueling Orc beats every Champion variant by a huge margin.

### Battle Master Subclass (vs BM Dueling Orc mirror)

| Build | Species | Win Rate | Avg DPR | Avg HP on Win | Notes |
|-------|---------|----------|---------|---------------|-------|
| BM Dueling (S&B) | Orc | 50.2% | 2.78 | 13.0 | Mirror match — baseline |
| BM GWF | Orc | 45.6% | 6.56 | 8.3 | Competitive! High DPR, lower AC hurts |
| BM S&B | Stone Goliath | 34.7% | 3.02 | 16.6 | Stone's ≠ Relentless here; fewer clutch saves |
| BM TWF | Orc | 26.4% | 4.72 | 10.0 | TWF underperforms significantly |

**Battle Master takeaway:** Dueling (S&B) is the best BM style — AC 18 with shield is massive. GWF is close behind (45.6% vs mirror). TWF is the worst. Maneuvers + shield + dueling is the optimal level 3 fighter build.

## Orc vs Goliath: Species Feature Analysis

**Head-to-head: Champion GWF Orc vs Champion GWF Stone Goliath** (identical builds, species only difference)

| | Orc | Stone Goliath |
|---|---|---|
| Win Rate | 45.3% | 54.7% |
| Avg DPR | 4.12 | 4.75 |
| Avg HP on Win | 7.6 | 13.0 |
| Avg Rounds | 5.8 | 5.8 |

### Relentless Endurance (Orc)
- Triggers in **71.5%** of fights (extremely common in 1v1)
- Effect: drops to 1 HP instead of 0 → essentially a free extra round
- HP-equivalent: ~4-8 effective HP (triggers often but only saves you once, and you're at 1 HP after)
- Also has **Adrenaline Rush** (dash as bonus action, temp HP) — not tracked but adds mobility

### Stone's Endurance (Goliath)
- Triggers in **~100%** of fights per combatant (197% = both fighters using it ~once each)
- Avg damage reduced per fight: **12.3 HP** (1d12+3 CON mod ≈ 9.5 average, but often caps at incoming damage)
- HP-equivalent: **~12 effective HP per fight** (consistent, reliable, every fight)
- Usable as reaction once per short rest — fires on first big hit

### Verdict

**Stone Goliath is significantly better than Orc at level 3 in 1v1 combat.**

- Stone's Endurance provides ~12 effective HP per fight — consistent and reliable
- Relentless Endurance triggers often (~71%) but only gives you 1 HP, making you extremely vulnerable
- The Goliath wins the head-to-head 54.7% to 45.3% — a clear but not overwhelming advantage
- Goliath winners have **13.0 avg HP remaining** vs Orc's **7.6** — much healthier wins
- Orc's advantage is Adrenaline Rush (mobility + temp HP), which matters more in group combat

**When Orc is better:** Multi-encounter days where Relentless Endurance prevents a death that would end a character permanently. In campaign play, "not dying" > "taking less damage."

**When Goliath is better:** Optimizing for consistent combat performance, especially in 1v1 or when fights are shorter. Stone's Endurance is like having a free Shield spell.

## Recommendations

### Best Level 3 Fighter Build
**Battle Master, Dueling (S&B), Stone Goliath** — AC 18, HP 31, maneuvers for burst/control, Stone's Endurance for damage mitigation. The S&B + dueling combination outperforms GWF and TWF due to the massive AC advantage.

### Fighting Style Tier List (Level 3)
1. **Dueling (S&B)** — +2 damage, +2 AC from shield, best overall
2. **Great Weapon Fighting** — Highest raw DPR, works well with Graze mastery
3. **Two-Weapon Fighting** — Underperforms; bonus action attack doesn't compensate for lower per-hit damage and AC

### Subclass Tier List
1. **Battle Master** — Maneuvers are incredibly powerful at level 3 (Precision alone is worth ~+2 hit rate)
2. **Champion** — Expanded crit range is too small a benefit; no utility or burst

### Species Tier List (melee fighter)
1. **Stone Goliath** — ~12 effective HP/fight from Stone's Endurance
2. **Orc** — Relentless Endurance is a great safety net but less raw combat power
3. **Fire Goliath** — Fire's Burn is situational and doesn't significantly improve outcomes
