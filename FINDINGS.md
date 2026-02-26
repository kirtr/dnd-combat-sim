# D&D 2024 Combat Simulator — Findings (Phase 3)

**Sim Parameters:** 10,000 combats per matchup, 1v1, start at 60ft, aggressive tactics, level 2 builds.

## Bug Fixes (Phase 3)

1. **Action Surge at range**: Fixed `_do_action_surge()` to move toward the opponent before attempting melee attacks. Previously it would try to swing a greatsword at 60ft range. Now it moves first, then melees if in range, or uses ranged weapon otherwise. Ranged surge also gets full extra attacks now.

2. **Javelin at 5ft in melee**: Fixed the combat loop to skip `ranged_attack` actions when already in melee range (distance ≤ 5ft). Previously the tactics engine would queue a ranged attack before moving, then after closing distance, throw a javelin at 5ft instead of using the greatsword.

## Overall Rankings (Level 2, by avg win rate across all 21 builds)

| Rank | Build | Avg Win Rate | HP | AC | Key Feature |
|------|-------|-------------|----|----|-------------|
| 1 | **Barbarian (Greatsword)** | **87.8%** | 25 | 15 | Rage (half damage), Reckless Attack |
| 2 | Fighter (TWF Scimitar+SS) | 67.2% | 20 | 16 | Nick mastery = 2 attacks/turn + Vex |
| 3 | **Fighter (TWF Goliath Fire)** | **66.3%** | 20 | 16 | Fire's Burn: +1d10 fire on hit (2/LR) + TWF |
| 4 | Fighter (Defense Greatsword) | 65.2% | 20 | 17 | +1 AC from style, greatsword damage |
| 5 | Fighter (GWF Greatsword) | 64.9% | 20 | 16 | Reroll low damage dice |
| 6 | Fighter (GWF Greatsword Orc) | 64.7% | 20 | 16 | Relentless Endurance + Adrenaline Rush |
| 7 | Fighter (GWF Greatsword Goliath Frost) | 63.4% | 20 | 16 | Stone's Endurance (1d12+CON reduction) |
| 8 | **Fighter (GWF Goliath Fire)** | **62.4%** | 20 | 16 | Fire's Burn: +1d10 fire on hit (2/LR) |
| 9 | Fighter (TWF Human SA+Tough) | 58.3% | 24 | 16 | Savage Attacker + Tough + Heroic Inspiration |
| 10 | Fighter (GWF Human SA+Tough) | 57.1% | 24 | 16 | Savage Attacker + Tough + Heroic Inspiration |
| 11 | Fighter (GWF Goliath Storm) | 55.2% | 20 | 16 | Storm's Thunder: 1d8 reaction damage (2/LR) |
| 12 | Fighter (GWF Tough) | 52.3% | 24 | 16 | +4 HP but no Savage Attacker |
| 13 | Fighter (Dueling Longsword) | 48.0% | 20 | 18 | Highest AC (shield), +2 flat damage |
| 14 | Fighter (TWF Goliath Hill) | 47.7% | 20 | 16 | Hill's Tumble: free prone on hit (2/LR) |
| 15 | Fighter (GWF Goliath Hill) | 42.5% | 20 | 16 | Hill's Tumble on GWF (less value than TWF) |
| 16 | Fighter (GWF Greatsword Dragonborn) | 41.7% | 20 | 16 | Breath Weapon wastes action |
| 17 | Monk (Shortsword) | 31.0% | 17 | 16 | Flurry of Blows, low HP |
| 18 | Fighter (Archery Longbow) | 31.0% | 20 | 15 | +2 to hit at range, bad in 1v1 |
| 19 | Rogue (Dual Wield) | 13.0% | 17 | 14 | Nick = 2 SA chances |
| 20 | Rogue (Dual Wield Halfling) | 12.9% | 17 | 14 | Luck rerolls, low HP |
| 21 | Rogue (Rapier) | 11.0% | 17 | 14 | SA needs advantage |

---

## Phase 3: Goliath Ancestry Comparison

### Giant Ancestry Traits Implemented

| Ancestry | Trait | Effect | Uses |
|----------|-------|--------|------|
| **Frost** | Stone's Endurance | Reaction: reduce damage by 1d12+CON | PB/LR |
| **Fire** | Fire's Burn | On hit: +1d10 fire damage | PB/LR |
| **Hill** | Hill's Tumble | On hit: target goes Prone (no save) | PB/LR |
| **Storm** | Storm's Thunder | Reaction when hit: 1d8 thunder to attacker (no save) | PB/LR |

### Ancestry Rankings (GWF Greatsword mirror, head-to-head)

| Matchup | Fire | Frost | Hill | Storm |
|---------|------|-------|------|-------|
| Fire vs Frost | **52.7%** | 47.3% | — | — |
| Fire vs Hill | **69.6%** | — | 30.4% | — |
| Fire vs Storm | **49.2%** | — | — | 40.7% |
| Frost vs Hill | **71.0%** | — | 28.9% | — |
| Frost vs Storm | **53.1%** | — | — | 44.6% |
| Hill vs Storm | — | — | 30.5% | **61.9%** |

**Ancestry tier (GWF):** Fire > Frost > Storm > Hill

### Ancestry Rankings (TWF mirror, where applicable)

| Matchup | Result |
|---------|--------|
| TWF Fire vs TWF Hill | **70.2%** vs 29.8% |
| TWF Fire vs GWF Frost | **53.0%** vs 47.0% |
| TWF Hill vs GWF Hill | **55.5%** vs 44.5% |

### Key Ancestry Findings

1. **Fire Giant is the best offensive ancestry.** Fire's Burn adds +1d10 (avg 5.5) per hit, 2 uses at level 2. Unlike Stone's Endurance (reactive/defensive), this is pure offense that accelerates kills. TWF Fire Giant is especially nasty because more attacks = more chances to burn fire charges.

2. **Frost Giant drops from #1 species to #2 ancestry.** Stone's Endurance is still excellent defense (~8.5 damage reduced per use) but Fire's Burn edges it out by **ending fights faster** (avg 2.7 rounds for Fire mirror vs 3.7 for Frost mirror). In a race, offense beats defense.

3. **Storm Giant is mid-tier.** Storm's Thunder deals 1d8 (avg 4.5) per hit taken, no save. It's reactive damage that punishes attackers but only fires PB times. At level 2 that's 9 total thunder damage across a fight — decent but less impactful than Fire's 11 bonus damage since Storm doesn't choose when to use it (it triggers on enemy attacks, not your hits).

4. **Hill Giant is the weakest 1v1 ancestry.** Hill's Tumble proning the target is great for TWF (first hit → prone → Nick attack with advantage) but mediocre for GWF (prone doesn't help your remaining attacks that turn since you already rolled). In 1v1, the positional advantage of prone is limited — the enemy just stands up on their turn (costs half movement). Hill Giant's value skyrockets in party play where multiple allies can benefit from the prone target.

5. **TWF is the best fighting style for Fire Giant.** TWF Fire (66.3% avg) beats GWF Fire (62.4% avg). More attacks = more chances to land the 1d10 fire bonus. TWF also pairs well with Hill Giant for the prone → advantage combo.

### DPS Analysis: Burst vs Sustained vs Depleted (AC 16)

| Build | Burst (R1+Surge) | Sustained | Depleted |
|-------|-------------------|-----------|----------|
| TWF Goliath Fire | **24.13** | **13.41** | 7.54 |
| GWF Goliath Fire | 21.27 | 10.75 | 7.84 |
| GWF Human SA+Tough | 18.35 | 10.34 | 7.83 |
| TWF Human SA+Tough | 17.06 | 9.44 | 7.64 |
| TWF Goliath Hill | 16.57 | 8.41 | 7.52 |
| GWF Greatsword (base) | 15.76 | 7.78 | 7.82 |
| GWF Goliath Frost | 15.91 | 7.83 | 7.78 |
| GWF Goliath Storm | 15.81 | 7.89 | 7.77 |
| GWF Goliath Hill | 15.56 | 7.85 | 7.90 |

**Key insight:** Fire Giant TWF has the highest burst DPR (24.13) in the entire sim — that's ~50% more damage than a base GWF Fighter on round 1. The depleted numbers converge because all Goliath fighters are identical once ancestry charges are spent.

---

## Phase 3: Human (2024) with Heroic Inspiration

### Human Traits
- **Resourceful:** Heroic Inspiration (1/LR) — advantage on one d20 roll
- **Skillful:** Extra skill proficiency (not combat-relevant)
- **Versatile:** Bonus Origin feat — Human effectively gets TWO feats at level 1

### Human Build Analysis

The 2024 Human is a feat machine: Soldier background gives Savage Attacker, Versatile gives a second feat (Tough). Combined with Heroic Inspiration, Humans get:
- Savage Attacker (reroll damage dice)
- Tough (+2 HP/level = 24 HP at level 2)
- Heroic Inspiration (advantage on one attack per fight)

| Build | Avg Win Rate | vs Barbarian | vs GWF base | vs Frost Goliath |
|-------|-------------|-------------|-------------|-----------------|
| TWF Human SA+Tough | 58.3% | 12.7% | 46.7% | 43.7% |
| GWF Human SA+Tough | 57.1% | 8.4% | 42.1% | 41.9% |

### Human vs Goliath (Same Style)

| Matchup | Human | Goliath |
|---------|-------|---------|
| GWF Human vs GWF Frost | 41.9% | **58.1%** |
| GWF Human vs GWF Fire | 42.8% | **57.2%** |
| TWF Human vs TWF Fire | 37.6% | **62.4%** |
| GWF Human vs GWF Storm | 45.2% | **48.6%** |

**Humans lose to Goliaths head-to-head.** The +4 HP from Tough and Heroic Inspiration can't match the raw power of Fire's Burn or the defensive value of Stone's Endurance. Humans do better against Storm and Hill ancestries where the gap is smaller.

### When Human Is Best
- **Versatile feat flexibility**: Tough + Savage Attacker is a strong combo, but you could also pick Alert (add PB to initiative), Lucky, or others
- **Sustained fights**: 24 HP gives staying power; Savage Attacker adds ~1 DPR consistently
- **No ancestry to waste**: Humans don't have charges that go unused in short fights
- In the rankings, Human SA+Tough is solidly mid-tier (#9-10) — strong but not dominant

---

## Updated Key Takeaways

### Tier List (Level 2, 1v1)

**S Tier:**
- Barbarian (87.8%) — Rage is still broken

**A Tier:**
- TWF Scimitar+SS (67.2%) — Nick mastery + Vex is consistently excellent
- TWF Goliath Fire (66.3%) — Best burst damage in the game
- Defense Greatsword (65.2%) — AC 17 + greatsword is quietly very strong
- GWF Greatsword (64.9%) — Reliable baseline
- GWF Orc (64.7%) — Relentless saves fights
- GWF Goliath Frost (63.4%) — Stone's Endurance = tank

**B Tier:**
- GWF Goliath Fire (62.4%) — Great burst, fewer attacks to trigger
- TWF Human SA+Tough (58.3%) — Two feats + 24 HP
- GWF Human SA+Tough (57.1%) — Same but greatsword
- GWF Goliath Storm (55.2%) — Decent reactive damage
- GWF Tough (52.3%) — HP without Savage Attacker

**C Tier:**
- Dueling Longsword (48.0%) — AC 18 doesn't save you anymore
- TWF Goliath Hill (47.7%) — Prone is better in parties
- GWF Goliath Hill (42.5%) — Prone on GWF is underwhelming
- GWF Dragonborn (41.7%) — Breath Weapon wastes turns

**D Tier:**
- Monk (31.0%), Archery (31.0%) — Squishy / bad 1v1
- Rogues (11-13%) — Need party support

### The Offense > Defense Shift

Phase 2 showed Frost Goliath (defensive) as the best species. Phase 3 reveals that Fire Giant (offensive) actually wins more fights overall because **ending fights faster reduces the opponent's opportunities to deal damage**. The best defense is killing them before they kill you — especially in short 2-3 round fights at level 2.

### TWF + Fire Giant = Nova King

TWF Goliath Fire Giant is the deadliest burst build at level 2:
- Round 1: Scimitar (Nick) → Shortsword (Vex) + Fire's Burn on both hits → Action Surge → 4 more attacks with fire
- Theoretical max round 1 damage: 4×(1d6+3) + 2×(1d10 fire) + Action Surge = absurd

### Prone Mechanics Need Party Context

Hill's Tumble (free prone) is weak in 1v1 because the enemy stands up for free on their turn (costs half movement, which rarely matters in melee). In party play, prone would give advantage to ALL melee allies attacking that target before its next turn — potentially devastating.

---

*Generated by dnd-combat-sim v0.3.0 — Phase 3, Goliath Ancestries + Human 2024*
