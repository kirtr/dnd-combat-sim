# D&D 2024 Combat Simulator — Phase 1 Findings (Updated)

**Sim Parameters:** 10,000 combats per matchup, 1v1, start at 60ft, aggressive tactics, level 2 builds.

**Update (Phase 1.5):** Added Two-Weapon Fighting with Nick mastery, Vex mastery fix, and dual-wield builds.

## Overall Rankings (Level 2, by avg win rate across all matchups)

| Rank | Build | Avg Win Rate | HP | AC | Key Feature |
|------|-------|-------------|----|----|-------------|
| 1 | **Barbarian (Greatsword)** | **88.8%** | 25 | 15 | Rage (half damage), Reckless Attack |
| 2 | Fighter (Dueling Longsword) | 59.7% | 20 | 18 | Highest AC (shield), +2 flat damage |
| 3 | Fighter (Defense Greatsword) | 59.7% | 20 | 17 | +1 AC from style, greatsword damage |
| 4 | **Fighter (TWF Scimitar+SS)** | **58.2%** | 20 | 16 | Nick mastery = 2 attacks/turn + Vex |
| 5 | Fighter (GWF Greatsword) | 57.4% | 20 | 16 | Reroll low damage dice |
| 6 | Fighter (Archery Longbow) | 45.2% | 20 | 15 | +2 to hit at range |
| 7 | Monk (Shortsword) | 42.8% | 17 | 16 | Flurry of Blows, extra attacks |
| 8 | **Rogue (Dual Wield)** | **20.1%** | 17 | 14 | Nick = 2 SA chances per turn |
| 9 | Rogue (Rapier) | 18.0% | 17 | 14 | Sneak Attack (needs advantage) |

## What Changed: TWF & Nick Mastery Implementation

### How Nick Mastery Works (2024 PHB)
- Attack with a **Nick weapon** (Scimitar, Dagger, Light Hammer, Sickle) → get an **extra attack** with a different **Light weapon** as part of the same Attack action
- The extra attack does **NOT** add ability modifier to damage unless you have **Two-Weapon Fighting style**
- This is NOT a bonus action — it's part of the Attack action, leaving bonus action free

### Key Implementation Details
- Vex mastery now properly consumed after one attack (was persisting incorrectly before)
- Tactics engine prefers Nick weapons as main attack to trigger the extra offhand attack
- Action Surge also triggers Nick extra attacks on the surge action

## New Build Analysis

### Fighter TWF (Scimitar + Shortsword) — 58.2% avg win rate

**Setup:** Scimitar (Nick) + Shortsword (Vex), TWF style, chain mail AC 16

The TWF Fighter is **competitive with other melee fighter styles**, ranking 4th overall:
- Beats GWF head-to-head: **52.7% vs 47.3%** — Nick's extra attack compensates for lower per-hit damage
- Loses to Dueling: **46.3% vs 53.7%** — AC 18 shield is hard to overcome with d6 weapons
- Loses to Defense: **48.3% vs 51.7%** — same issue, greatsword damage + AC 17 edge
- Crushes Archery: **66.9% vs 33.1%**

**Why TWF works now:** With Nick mastery, the TWF Fighter effectively gets 2 attacks per turn (3 on Action Surge turns) at level 2, while other fighters get 1 (2 on surge). Each attack is 1d6+3 (6.5 avg) with TWF style adding ability mod. Scimitar hit → Nick extra Shortsword attack → Vex on hit gives advantage on next turn's first attack.

**The attack chain:**
1. Attack with Scimitar (Nick) — 1d6+3
2. Nick triggers extra Shortsword (Vex) attack — 1d6+3 (TWF style adds STR mod)
3. If Shortsword hits: Vex gives advantage on next turn's first attack
4. On Action Surge turns: another Scimitar attack + another Nick Shortsword attack = 4 attacks total

### Rogue (Dual Wield) vs Rogue (Rapier) — 53.6% vs 46.4%

**Dual Wield Rogue (Scimitar + Shortsword):** 20.1% avg win rate
**Single Rapier Rogue:** 18.0% avg win rate

The dual-wield Rogue is **modestly better** than the rapier Rogue:
- Head-to-head: Dual Wield wins **53.6%** of the time
- Better average win rate across all matchups: **20.1% vs 18.0%** (+2.1%)

**Why it helps but doesn't transform:** The Rogue's core problem in 1v1 is needing advantage for Sneak Attack. Nick gives a second attack (two chances to trigger SA via Cunning Action: Hide), but each individual attack deals less damage (1d6 vs 1d8 rapier) and the Nick attack doesn't add DEX to damage (no TWF style). The improvement is real but modest — an extra ~2% win rate.

**The math:**
- Rapier Rogue: 1 attack at 1d8+3, one chance for SA
- Dual Wield Rogue: Scimitar 1d6+3 + Nick Shortsword 1d6 (no DEX), two chances for SA
- Extra SA chance matters more than the lower per-hit damage

### TWF vs Other Fighter Styles — Head-to-Head

| Matchup | TWF Win% | Opponent Win% |
|---------|----------|---------------|
| TWF vs GWF | **52.7%** | 47.3% |
| TWF vs Dueling | 46.3% | **53.7%** |
| TWF vs Defense | 48.3% | **51.7%** |
| TWF vs Archery | **66.9%** | 33.1% |

TWF beats GWF and Archery, loses to Dueling and Defense. The shield builds (Dueling AC 18) and higher-AC greatsword builds (Defense AC 17) punish TWF's lower per-hit damage — more attacks mean more chances to miss against high AC.

## Key Takeaways

### Barbarian is Still King at Level 2
88.8% average win rate, dominant across the board. Rage resistance + Reckless Attack + high HP pool remains unbeatable in 1v1.

### Fighter Styles Are All Viable
All four melee fighter styles (Defense, Dueling, TWF, GWF) cluster between **57-60%** average win rate. The differences are small enough that player preference, subclass features (level 3), and party composition should drive the choice.

**Style Tier List (1v1 at level 2):**
1. Defense / Dueling (tied at 59.7%)
2. TWF (58.2%)
3. GWF (57.4%)
4. Archery (45.2% — bad in 1v1, great in parties)

### Nick Mastery Is Legit
Nick mastery makes TWF competitive without requiring a bonus action for the offhand attack. This is a huge improvement over 2014's TWF, which consumed your bonus action. Now TWF fighters can use Second Wind or other bonus actions while still getting two attacks per turn.

### Dual-Wield Rogue: Marginal Improvement
Going from rapier to scimitar + shortsword gives the Rogue +2% win rate. The extra attack helps land Sneak Attack more reliably, but the Rogue's fundamental problem (needing advantage in 1v1, low HP/AC) remains. In party play with an adjacent ally guaranteeing SA, the dual-wield Rogue would benefit more from two chances to land the hit.

### Vex Mastery Fix
Vex now properly consumed after one attack instead of persisting indefinitely. This slightly reduced win rates for Vex-using builds compared to Phase 1 (where the bug inflated them).

## Sim Limitations & Next Steps

### Known Limitations
- **No opportunity attacks** — closing distance is free
- **Simplified hiding** — Rogue's Cunning Action: Hide uses contested roll but ignores cover/obscurement
- **No subclasses** — Level 3 subclass features will dramatically change the landscape
- **1v1 bias** — heavily favors tanky builds; Rogue and Archery would perform much better with allies

### Phase 2 Priorities
1. Level 3 subclass features (Champion, Battlemaster, Berserker, Open Hand, Thief)
2. Level 5 (Extra Attack is a massive power spike — TWF gets 3 attacks/turn!)
3. Casters: Warlock (simple spell slots), then Paladin (smites)
4. Party vs party framework

---

## Phase 2: Species & Origin Feat Impact (Level 2 Fighter Mirror Match)

### Species Traits Implemented
- **Orc:** Relentless Endurance (drop to 1 HP instead of 0, 1/LR), Adrenaline Rush (BA Dash + temp HP)
- **Goliath (Frost Giant):** Stone's Endurance (reaction: reduce damage by 1d12+CON, PB/LR), Large Form (BA: +10 speed for PB turns)
- **Dragonborn:** Breath Weapon (action: 15ft cone, DEX save, 1d10 damage, PB/LR)
- **Halfling:** Luck (reroll nat 1s on d20 attacks/saves)
- **Tough feat:** +2 HP per level
- **Lucky feat:** PB luck points/LR, reroll failed attack rolls

### Species Ranking (GWF Greatsword Fighter, same stats, head-to-head)

| Species | Avg Win Rate | Key Advantage |
|---------|-------------|---------------|
| **Goliath (Frost)** | **69.5%** | Stone's Endurance is king — 2 uses of 1d12+2 damage reduction per fight (~8.5 HP saved per use) |
| **Orc** | **65.2%** | Relentless Endurance gives a "free round" at 1 HP; Adrenaline Rush helps close distance |
| **Human (base)** | **65.1%** | Savage Attacker alone is strong; no defensive traits |
| **Human (Tough)** | **55.6%** | +4 HP (24 vs 20) helps but loses Savage Attacker |
| **Dragonborn** | **49.0%** | Breath Weapon is a trap in 1v1 — 1d10 (5.5) < 2d6+3 GWF (10.3) |

### Key Findings

1. **Goliath (Frost Giant) is the best combat species at level 2.** Stone's Endurance effectively adds ~17 HP worth of damage reduction across a fight. It beat every other species variant head-to-head:
   - Goliath 54.9% vs Human, 54.8% vs Orc, 70.2% vs Dragonborn, 65.1% vs Tough

2. **Orc is barely better than base Human (~0.1% difference).** Relentless Endurance sounds great but only matters when you'd die — and you still die on the next hit at 1 HP. Adrenaline Rush helps with distance-closing but the 60ft starting distance means most builds close within 2 rounds anyway.

3. **Dragonborn Breath Weapon is a DPS downgrade in 1v1.** At level 2, using your action on 1d10 (avg 5.5) instead of a greatsword attack (2d6+3 GWF, avg 10.3) is terrible. It only makes sense in AoE situations (multiple targets). The Dragonborn actually performs *worse* than base Human (33.3% vs 66.7%).

4. **Tough feat (+4 HP) is worse than Savage Attacker.** The Tough fighter has 24 HP vs 20 but loses the reroll-damage-dice benefit. Base Human with Savage Attacker beats Tough 61% to 39%. Offense > Defense at this level.

5. **Halfling Luck is nearly invisible in simulation.** Rerolling nat 1s (5% chance) only matters on ~1 in 20 attacks. The Halfling rogue performed identically to the base rogue (51.4% vs 48.6% in mirror match — within noise).

6. **Lucky feat didn't show significant impact** in the DPS calculator because it only fires on misses and costs a limited resource. In full combat, it provides marginal improvement.

### Defensive Traits > Offensive Traits

The overall lesson: **damage mitigation scales better than small offensive bonuses** in 1v1 duels at level 2. Stone's Endurance (Goliath) providing ~17 effective HP is worth more than Savage Attacker's ~1 extra DPR. This may invert at higher levels where burst damage increases.

---
*Generated by dnd-combat-sim v0.2.0 — Phase 2, Species & Origin Feats*
