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

---

# Phase 4: Level 3 Subclasses

**Sim Parameters:** 500 combats per matchup, 1v1, start at 60ft, aggressive tactics, level 3 builds only.
**Level 3 builds archived:** 26 level 2 builds moved to `data/builds/archive/level2/` — level 3 is the active focus.

## New Subclasses Implemented

### Barbarian
- **Berserker** — Frenzy: bonus action weapon attack each turn while raging (costs Exhaustion 1 after rage, ignored in sim)
- **Bear Totem Warrior** — Resistance to ALL damage except Psychic while raging (upgraded from base B/P/S only)

### Monk
- **Warrior of the Open Hand** — Open Hand Technique: after Flurry of Blows hit, impose Push/Prone/Deny Reaction (no save). Tactic: Knock Prone for advantage on follow-up attacks.
- **Warrior of Shadow** — Shadow Arts: spend 2 ki → "obscured" for 1 minute (attacks against you have disadvantage)

### Rogue
- **Thief** — Fast Hands: bonus action Help to grant yourself advantage on next attack (1/combat)
- **Arcane Trickster** — Booming Blade cantrip: on hit, weapon damage + 1d8 thunder; extra 1d8 if target moves before your next turn

## Bug Fix: Nick Mastery "Once Per Turn"

**Rule:** Nick's extra Light weapon attack happens as part of the Attack action (not bonus action) and can only fire **once per turn**.

**Bug:** `_try_nick_extra_attack()` was triggering on both the Attack action and Action Surge attacks — two Nick attacks per turn, violating the rule.

**Fix:** Added `nick_used_this_turn` flag on `Character`, reset in `start_turn()`. Gates `_try_nick_extra_attack()` so it fires at most once per turn regardless of Action Surge.

**Impact on Berserker:** Confirmed Nick does NOT consume the bonus action, so Berserker TWF builds correctly get Nick extra attack (Attack action) + Frenzy (bonus action) on the same turn.

## Level 3 Rankings (n=500, 21 builds)

| Rank | Build | Avg Win% |
|------|-------|----------|
| 1 | Berserker GWF Orc | 90.3% |
| 2 | Berserker TWF Orc | 85.9% |
| 3 | Battle Master Dueling Orc | 76.9% |
| 4 | Bear Totem GWF Orc | 75.5% |
| 5 | Battle Master GWF Orc | 75.3% |
| 6 | Bear Totem TWF Orc | 74.8% |
| 7 | Battle Master TWF Orc | 72.9% |
| 8 | Hunter Ranger TWF | 59.1% |
| 9 | Champion TWF Fire Goliath | 51.8% |
| 10 | Champion GWF Orc | 48.8% |
| 11 | Fighter GWF Orc | 45.9% |
| 12 | Hunter Ranger GWF | 45.8% |
| 13 | Fighter TWF Orc | 43.4% |
| 14 | Open Hand Orc | 33.9% |
| 15 | Arcane Trickster Human | 31.8% |
| 16 | Arcane Trickster Halfling | 31.7% |
| 17 | Shadow Monk Orc | 29.8% |
| 18 | Open Hand Human | 28.1% |
| 19 | Hunter Ranger Archery | 21.0% |
| 20 | Thief Halfling | 13.4% |
| 21 | Thief Human | 13.3% |

## Level 3 Tier List (1v1)

**S Tier:**
- **Berserker Barbarian** (85-90%) — Frenzy gives a third attack per turn while raging. Combined with Rage resistance, it's overwhelming. Frenzy + Nick on TWF frees bonus action for the Frenzy attack. Dominant.

**A Tier:**
- **Battle Master Fighter** (73-77%) — 4d8 Superiority Dice with Precision/Trip/Riposte/Menacing is a massive burst of controlled damage. Trip → prone → advantage for follow-up attacks compounds nicely.
- **Bear Totem Barbarian** (75%) — Resistance to all non-psychic damage is a huge defensive upgrade. Survives long enough to win attrition fights even without Frenzy's extra attack.

**B Tier:**
- **Hunter Ranger TWF** (59%) — Hunter's Mark (+1d6/hit, no concentration in 2024) adds sustained damage. Two attacks per turn with HM is solid. Bonus action goes to HM first turn, then free.
- **Champion Fighter** (49-52%) — Crit on 19-20 is good burst but not enough to compete with Battle Master's reliability.
- **Base Fighter** (43-46%) — Action Surge is powerful but no subclass punch at level 3.

**C Tier:**
- **Hunter Ranger GWF** (46%) — HM helps but fewer attacks limits procs. GWF reroll rarely triggers.
- **Open Hand Monk** (28-34%) — Flurry + prone is clever but d8 hit die and 3 ki points runs dry fast. Low survivability.
- **Arcane Trickster Rogue** (32%) — Booming Blade + Sneak Attack is decent burst but needs advantage and still has squishiness problem.
- **Shadow Monk** (30%) — Disadvantage on incoming attacks helps survival but ki drain and low damage makes it a slow fight that often ends badly.

**D Tier:**
- **Hunter Ranger Archery** (21%) — Ranged kiting doesn't exist in the sim; opponent closes and the Archery ranger becomes a worse melee fighter.
- **Thief Rogue** (13%) — Fast Hands is a weak combat ability. Rogue needs party support for consistent Sneak Attack. Terrible 1v1.

## Key Findings

### Berserker is Broken at Level 3
Three effective attacks per turn (main + Nick offhand + Frenzy bonus action) while also having Rage resistance is too much. Berserker GWF at 90.3% beats everything — including the Barbarian's already-dominant level 2 showing. This tracks with how Berserker plays at the table: it's strong but costs Exhaustion, which the sim ignores (multi-fight context).

### Barbarians Own the Top 6
All 4 Barbarian builds land in the top 6. Rage resistance alone is worth 20-30 win percentage points vs. non-Barbarian builds. At level 3 the subclasses differentiate: Berserker adds offense, Bear Totem adds defense — both are top tier.

### Monks and Rogues Need Party Play
Both classes land at the bottom of 1v1 rankings, which matches their design intent. Rogues need advantage from an ally (Sneak Attack) and monks need time to chip with ki. Neither has the raw durability to survive extended 1v1 combat at level 3. Worth noting for arena matchmaking — these classes would need handicaps or team contexts to be viable.

### Hunter's Mark is a Real DPS Upgrade (Ranger)
+1d6 per hit with no concentration cost (2024 rules) makes Hunter Ranger punching significantly above base fighter in sustained fights. TWF Ranger at 59% is competitive with Champions and base fighters. The bonus action investment on turn 1 pays off over 3-4 round fights.

### Ranged Builds Need Kiting Logic
Archery Ranger at 21% is a modeling artifact — the sim doesn't implement retreat/kiting tactics, so ranged builds just get closed on and fight at a disadvantage. Before treating Archery as weak, implement proper ranged tactics (move-and-shoot, disengage-and-fire).

### Next Priority: Spellcasters or Level 5
Two clear paths forward:
1. **Level 5** — Extra Attack is the biggest power spike in the game. Every martial class doubles attacks. Hill Giant becomes strong (prone + 2 attacks with advantage). This is where most balance shakeup happens.
2. **Spellcasters** — Warlock (Eldritch Blast + Hex), Paladin (Divine Smite burst), Cleric (Spirit Guardians) need a spell system architecture first.

---

*Generated by dnd-combat-sim v0.4.0 — Phase 4, Level 3 Subclasses*
