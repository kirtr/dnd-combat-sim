# D&D 2024 Combat Simulator — Phase 1 Findings

**Sim Parameters:** 10,000 combats per matchup, 1v1, start at 60ft, aggressive tactics, level 2 builds.

## Overall Rankings (Level 2, by avg win rate across all matchups)

| Rank | Build | Avg Win Rate | HP | AC | Key Feature |
|------|-------|-------------|----|----|-------------|
| 1 | **Barbarian (Greatsword)** | **87.9%** | 25 | 15 | Rage (half damage), Reckless Attack |
| 2 | Fighter (Defense Greatsword) | 54.9% | 20 | 17 | +1 AC from style, greatsword damage |
| 3 | Fighter (Dueling Longsword) | 54.0% | 20 | 18 | Highest AC (shield), +2 flat damage |
| 4 | Fighter (GWF Greatsword) | 52.6% | 20 | 16 | Reroll low damage dice |
| 5 | Monk (Shortsword) | 45.0% | 17 | 16 | Flurry of Blows, extra attacks |
| 6 | Fighter (Archery Longbow) | 41.3% | 20 | 15 | +2 to hit at range |
| 7 | Rogue (Rapier) | 14.4% | 17 | 14 | Sneak Attack (needs advantage) |

## Key Takeaways

### Barbarian is King at Level 2
The Barbarian's **87.9% average win rate** is dominant — not even close. Two factors:
- **Rage resistance** effectively doubles HP vs physical damage (25 HP becomes ~50 effective HP)
- **Reckless Attack** grants reliable advantage, boosting hit rate significantly
- 25 HP base (d12 hit die + 16 CON) is the highest pool

The Barbarian beats every other build by massive margins. The closest fight is vs Dueling Fighter (81.4% barb win rate), where AC 18 provides some mitigation.

### Fighter Styles Are Closer Than Expected
The three melee fighter styles are within ~5% of each other:

| Matchup | Result |
|---------|--------|
| GWF vs Dueling | 48.8% — 51.2% |
| GWF vs Defense | 49.2% — 50.8% |
| Dueling vs Defense | 47.7% — 52.3% |

**Defense wins the fighter mirror.** The +1 AC on greatsword (AC 17) slightly outperforms both GWF's damage rerolls and Dueling's +2 damage with shield (AC 18). This is counterintuitive — Dueling has the highest AC at 18 but Defense edges it out because it keeps the greatsword's 2d6 + Graze mastery.

**Why Defense > Dueling despite lower AC:** The greatsword deals more damage per hit (2d6+3 avg 10 vs 1d8+5 avg 9.5) AND has Graze mastery (deal STR mod damage on miss). That chip damage on misses adds up over 3-4 round fights.

### Archery Is a Trap in 1v1
The Archery fighter (41.3% avg) underperforms badly. At 60ft starting distance, everyone gets roughly one ranged exchange before closing to melee. The +2 to-hit at range doesn't compensate for:
- Lower AC (chain shirt 15 vs chain mail 16-18)
- DEX-based means weaker melee when forced to close
- Longbow can't be used in melee (unlike javelin-wielders who throw and then draw swords)

**Caveat:** Archery would perform dramatically better with longer engagement ranges, multiple rounds of ranged fire, or party support keeping enemies at distance.

### Rogue Struggles Without Allies
Rogue's 14.4% avg win rate is painful but expected. The 1v1 format is worst-case for Rogues because:
- **Sneak Attack requires advantage** (no adjacent ally in 1v1)
- Cunning Action: Hide is their only advantage source, and it's contested (Stealth vs Passive Perception)
- Low HP (17) and AC (14) means they drop fast
- Without reliable Sneak Attack, they're just doing 1d8+3 per turn

**In party play, Rogue would jump significantly** — a nearby ally guarantees Sneak Attack every turn.

### Monk: Lots of Attacks, Not Enough Punch
Monk sits at 45.0%, middle of the pack. Flurry of Blows gives 3 attacks per turn (action + 2 bonus), but:
- 1d6+3 per hit (6.5 avg) × 3 = 19.5 potential, but with ~60% hit rate that's ~11.7 actual
- Only 17 HP — glass cannon without the cannon
- Focus Points run out after 2 rounds of Flurry

Martial Arts bonus strike (free, no resource) keeps them competitive, but they can't sustain the burst.

## Fighter Style Deep Dive

### Head-to-Head Matrix

| Attacker ↓ / Defender → | GWF | Dueling | Defense | Archery |
|--------------------------|-----|---------|---------|---------|
| **GWF Greatsword** | — | 48.8% | 49.2% | 62.7% |
| **Dueling Longsword** | 51.2% | — | 47.7% | 63.8% |
| **Defense Greatsword** | 50.8% | 52.3% | — | 64.5% |
| **Archery Longbow** | 37.3% | 36.2% | 35.5% | — |

### Style Analysis

**Great Weapon Fighting**
- Rerolling 1s and 2s on 2d6 bumps average from 7.0 to ~8.33 (+1.33 per hit)
- Combined with Graze mastery: even misses deal 3 damage
- Best raw DPR among fighters, but no AC benefit

**Dueling**
- Flat +2 damage is reliable (1d8+5 = 9.5 avg per hit)
- Shield brings AC to 18 — highest among all builds
- Trades Graze/Cleave mastery for Sap (disadvantage on enemy attacks)
- Longsword Sap mastery is defensive, complementing the shield playstyle

**Defense**
- +1 AC (17 with chain mail) is modest but constant
- Keeps greatsword access — same damage as GWF minus the rerolls
- Graze mastery still applies
- The "boring but effective" choice

**Archery**
- +2 to hit at range is the best accuracy bonus available
- Falls apart in melee — DEX-based but forced into close quarters
- Would need 3+ rounds of free shooting to overcome the HP/AC deficit
- Best style for party play, worst for dueling

### Recommendation
For a level 2 fighter "control" build: **Defense with Greatsword** is statistically the strongest in 1v1. GWF is within noise. Dueling + Shield is the best if you value survivability (AC 18) over damage. All three melee styles are viable — the differences are small enough that subclass features at level 3 will matter more.

## Armor Progression Guide

### Recommended Armor by Level (2024 PHB)

D&D 2024 doesn't prescribe wealth-by-level, but typical campaign progression:

| Level | Heavy Armor User | Medium Armor User | Light Armor User |
|-------|-----------------|-------------------|------------------|
| 1-2 | Chain Mail (AC 16) | Scale Mail (AC 14+2) | Leather (AC 11+DEX) |
| 3-4 | Chain Mail (AC 16) | Breastplate (AC 14+2) | Studded Leather (AC 12+DEX) |
| 5-8 | Splint (AC 17) | Half Plate (AC 15+2) | Studded Leather (AC 12+DEX) |
| 9-12 | Plate (AC 18) | Half Plate +1 (AC 16+2) | Studded Leather +1 (AC 13+DEX) |
| 13+ | Plate +1 (AC 19) | Half Plate +2 (AC 17+2) | Studded Leather +2 (AC 14+DEX) |

**Unarmored builds (Barbarian, Monk)** scale with ability scores:

| Level | Barbarian (DEX+CON) | Monk (DEX+WIS) |
|-------|-------------------|----------------|
| 1-3 | AC 15 (14 DEX, 16 CON) | AC 16 (16 DEX, 16 WIS) |
| 4 (ASI) | AC 16 (14 DEX, 18 CON) | AC 17 (18 DEX, 16 WIS) |
| 8 (ASI) | AC 17 (16 DEX, 18 CON) | AC 18 (20 DEX, 16 WIS) |
| 12+ | AC 18 (18 DEX, 18 CON) | AC 19 (20 DEX, 18 WIS) |

### Implementation Plan
- Build YAML files specify armor explicitly (override)
- If no armor specified, loader defaults based on class + level using the table above
- Magic armor (+1/+2/+3) modeled as `ac_bonus` field in build YAML

## Sim Limitations & Next Steps

### Known Limitations
- **TWF not implemented** — Two-Weapon Fighting style builds can't use bonus action offhand attack yet
- **No opportunity attacks** — closing distance is free (should provoke when disengaging)
- **Simplified hiding** — Rogue's Cunning Action: Hide uses a contested roll but ignores cover/obscurement
- **No subclasses** — Level 3 subclass features will dramatically change the landscape
- **1v1 bias** — heavily favors tanky builds; Rogue and Archery would perform much better with allies

### Phase 2 Priorities
1. Level 3 subclass features (Champion, Battlemaster, Berserker, Open Hand, Thief)
2. TWF implementation
3. Level 5 (Extra Attack is a massive power spike)
4. Casters: Warlock (simple spell slots), then Paladin (smites)
5. Party vs party framework

---
*Generated by dnd-combat-sim v0.1.0 — Phase 1, Level 2 Martial Builds*
