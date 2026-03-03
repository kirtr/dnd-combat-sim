# D&D 2024 Combat Simulator — Findings

---

# Phase 6: Barbarian Species Showdown *(current)*

**Level 3. Sim Parameters:** n=3000 per matchup, 1v1, aggressive tactics.
**Question:** Orc (Relentless Endurance) vs Fire Goliath (+1d10 fire on hit) on Berserker chassis.

## 🏆 Champion: Berserker Greatsword Fire Goliath (Level 3)

Called on DPS — head-to-head with S&B Longsword Fire Goliath is a coin flip (51.6/48.4),
but Greatsword outputs 25% more damage (13.89 vs 11.08 DPS at AC 16). Simpler build, higher ceiling.

## Results

```
Win%   Species        Weapon         Mastery   AC  DPS/16
──────────────────────────────────────────────────────────
70%    Fire Goliath   Greatsword     Graze     15   13.89
70%    Fire Goliath   S&B Longsword  Sap       17   11.08
55%    Fire Goliath   S&B Battleaxe  Topple    17   11.22
44%    Orc            S&B Longsword  Sap       17    6.87
39%    Orc            Greatsword     Graze     15    9.94
23%    Orc            S&B Battleaxe  Topple    17    7.14
```

## Key Findings

**Fire Goliath dominates.** +1d10 fire on hit (2 uses/LR, avg 5.5 each = ~11 bonus damage/fight)
is enough to flip the entire tier list. All 3 Fire builds beat all 3 Orc builds.

**Relentless Endurance can't keep up with burst.** Orc's survive-at-1-HP is good but Fire Goliath
ends fights before it matters — Fire mirrors average 3-4 rounds vs 6-8 for Orc mirrors.

**Sap fix changed everything for S&B.** After fixing Sap (was expiring before target attacked),
S&B Longsword went from 50/50 vs Battleaxe to 68/32. Sap cancels Reckless Attack's advantage,
forcing straight d20 rolls.

**Greatsword vs S&B Longsword (Fire) is a coin flip** — Graze wins on DPS, Sap wins at high AC.
Call it by playstyle.

## Bug Fixed This Phase

**Sap mastery (all Sap weapons):** `end_trigger="start_of_turn"` was clearing the effect at the
start of the target's own turn, before they attacked. Disadvantage never applied. Fixed to
consume-on-use in `_has_disadvantage()`, same pattern as Vex. Committed: b92abfa.

---

# Phase 5: Barbarian Optimization *(level 3)*

**Sim Parameters:** n=500 per matchup, 1v1, aggressive tactics.
**Goal:** Find best Berserker weapon. Drop Bear Totem (resistances irrelevant in B/P/S melee).

## Build Spec

All builds: Berserker Orc, Level 3, Soldier background.

| Stat | Value | Mod | Notes |
|------|-------|-----|-------|
| STR | 16 | +3 | 14 base +2 bg |
| DEX | 14 | +2 | Medium armor cap |
| CON | 16 | +3 | 15 base +1 bg |
| CHA | 12 | +1 | Saved points — CHA saves vs Banishment/Fear |
| INT | 8  | -1 | |
| WIS | 8  | -1 | |

Point buy: 7+7+9+4+0+0 = 27 ✓  HP: 35

**Armor:** Unarmored Defense = 10+DEX+CON = **AC 15**. S&B adds shield: **AC 17**.
Half plate (750gp) is not starting-gear affordable for a barbarian — unarmored is correct.

## Weapon Mastery Notes

| Weapon | Dice | Mastery | 1v1 Value |
|--------|------|---------|-----------|
| Greatsword | 2d6 | Graze — miss deals STR mod dmg | ✅ Reliable |
| Maul | 2d6 | Topple — hit → CON save or prone | ⚠️ Redundant (Reckless already gives adv) |
| Greataxe | 1d12 | Cleave — attack 2nd adjacent creature | ❌ Useless in 1v1, no 2nd target |
| Battleaxe | 1d8 | Topple | ⚠️ Same caveat as Maul |
| Longsword | 1d8 | Sap — hit → disadv on target's next attack | ✅ Works 1v1 |

## Barbarian Berserker Championship — Level 3

```
Win%   Weapon           Dice   Mastery    AC   DPS/16
──────────────────────────────────────────────────────
71%    Greatsword       2d6    Graze      15    9.91
60%    Maul             2d6    Topple     15    9.40
50%    S&B Longsword    1d8    Sap        17    7.06
49%    S&B Battleaxe    1d8    Topple     17    6.96
20%    Greataxe         1d12   Cleave†    15    9.19
──────────────────────────────────────────────────────
† Cleave = attack a 2nd adjacent creature. Useless in 1v1.
  20% win rate is accurate — not a sim gap.
```

## Key Findings

**Greatsword wins.** Graze converts rare misses to STR mod damage — more reliable than Topple since Reckless Attack already grants advantage (Topple's prone is redundant for your own attacks). Scales better at high AC where misses become more frequent.

**Maul is solid second.** Same 2d6 dice, Topple just adds less value in this context.

**S&B nearly ties Maul.** AC 17 vs 15 almost cancels the damage gap. Longsword (Sap) and Battleaxe (Topple) are statistically identical (50/50 head-to-head).

**Greataxe is genuinely bad in 1v1.** 1d12 (avg 6.5) < 2d6 (avg 7.0) AND Cleave does nothing without a second target. The 20% win rate stands.

**Bear Totem dropped.** Rage already gives B/P/S resistance. Bear Totem's extra coverage adds nothing in physical melee — zero benefit vs Berserker's Frenzy bonus action attack.

**Old builds were badly underbuilt.** DEX 13 → 14 and correcting armor (AC 14 → 15) accounts for most of the gap. New Greatsword beats old GWF 68%.

## TODO — Next Steps

- Level 5: Extra Attack doubles all martial output — biggest power spike in the game
- Goliath Berserker — Stone's Endurance vs Orc's Relentless Endurance
- Spellcasters: Warlock, Paladin, Cleric (needs spell system)

---

# Phase 4: Level 3 Subclasses

**Sim Parameters:** 500 combats per matchup, 1v1, start at 60ft, aggressive tactics.
**Active builds:** 21 level 3 builds (level 2 builds archived to `data/builds/archive/level2/`).

## New Subclasses Implemented

### Barbarian
- **Berserker** — Frenzy: bonus action weapon attack each turn while raging (Exhaustion 1 after rage; ignored in sim — single-fight context)
- **Bear Totem Warrior** — Resistance to ALL damage except Psychic while raging (upgraded from base B/P/S only)

### Monk
- **Warrior of the Open Hand** — Open Hand Technique: after Flurry of Blows hit, impose Push/Prone/Deny Reaction (no save). Tactic: Knock Prone for advantage on follow-up attacks.
- **Warrior of Shadow** — Shadow Arts: spend 2 ki → "obscured" for 1 minute (attacks against you have disadvantage)

### Rogue
- **Thief** — Fast Hands: bonus action Help to grant self advantage on next attack (1/combat)
- **Arcane Trickster** — Booming Blade: on hit, weapon damage + 1d8 thunder; extra 1d8 if target moves before your next turn

## Bug Fix: Nick Mastery "Once Per Turn"

**Rule (PHB p.218):** "When you make the extra attack of the Light property, you can make it as part of the Attack action instead of as a Bonus Action. You can make this extra attack only once per turn."

**Bug:** `_try_nick_extra_attack()` was firing on both the Attack action and Action Surge — two Nick attacks per turn.

**Fix:** Added `nick_used_this_turn` flag on `Character`, reset in `start_turn()`. Nick fires at most once per turn.

**Note on bonus action:** Nick does NOT consume the bonus action. Berserker TWF correctly gets Nick extra attack (Attack action) + Frenzy (bonus action) on the same turn.

## Level 3 Rankings (n=500)

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
- **Berserker Barbarian** (86-90%) — Three effective attacks/turn (main + Nick offhand + Frenzy bonus action) while having Rage resistance. Dominant in 1v1 arena. Note: Exhaustion cost matters in multi-fight context.

**A Tier:**
- **Battle Master Fighter** (73-77%) — 4d8 Superiority Dice with Precision/Trip/Riposte/Menacing. Trip → prone → advantage on follow-up is reliable and strong.
- **Bear Totem Barbarian** (75%) — Resistance to all non-psychic damage is a huge survivability upgrade. Wins attrition even without Frenzy's extra attack.

**B Tier:**
- **Hunter Ranger TWF** (59%) — Hunter's Mark (+1d6/hit, no concentration in 2024) adds meaningful sustained damage. TWF two attacks/turn with HM procs on both.
- **Champion Fighter** (49-52%) — Crit on 19-20 is solid burst but not enough to compete with Battle Master's consistency.
- **Base Fighter / Hunter Ranger GWF** (43-46%) — Action Surge is powerful but no level 3 subclass punch.

**C Tier:**
- **Open Hand Monk** (28-34%) — Flurry + prone is clever but 3 ki runs dry fast, d8 hit die hurts survivability.
- **Arcane Trickster Rogue** (32%) — Booming Blade + Sneak Attack is decent burst but needs advantage setup.
- **Shadow Monk** (30%) — Incoming disadvantage helps survival but slow damage output.

**D Tier:**
- **Hunter Ranger Archery** (21%) — Modeling artifact: sim has no kiting logic, ranged builds get closed on and fight at a disadvantage. Not a fair test.
- **Thief Rogue** (13%) — Fast Hands is weak as a combat tool. Rogue needs party support for consistent Sneak Attack.

## Key Findings

**Berserker is busted at level 3 (in isolation).** Three attacks/turn + Rage resistance at level 3 is overwhelming. Tracks with table experience — Berserker is strong but the Exhaustion cost is real across multiple encounters, which the sim ignores.

**Barbarians own the top 6.** Rage resistance alone is worth 20-30 win points vs. non-Barbarians. Subclasses differentiate: Berserker adds offense, Bear Totem adds defense — both are top tier.

**Monks and Rogues need party play.** Both classes land at the bottom in 1v1, which matches their design intent. Rogues need an ally for consistent Sneak Attack advantage; Monks need time to work ki. Neither has raw durability for extended 1v1. Worth handicapping or team-contextualizing in arena scenarios.

**Hunter's Mark is a real DPS upgrade.** +1d6/hit with no concentration (2024 rules) makes Hunter Ranger competitive with Champions and base fighters in sustained fights.

**Archery needs kiting logic before judging.** The 21% ranking is a sim limitation, not a class judgment.

## Next Priorities

1. **Level 5** — Extra Attack doubles all martial output. Biggest power spike in the game. Hill Giant becomes strong (prone + 2 attacks with advantage). Where most balance shakeup happens.
2. **Spellcasters** — Warlock (Eldritch Blast + Hex), Paladin (Divine Smite burst), Cleric (Spirit Guardians). Needs spell system architecture first.
3. **Ranged kiting logic** — Implement disengage-and-fire tactics so Archery builds get a fair test.

---

# Phase 3: Goliath Ancestries & Human 2024 *(Level 2 reference)*

> Level 2 builds archived. Findings below are mechanically valid and carry forward to level 3+ builds using the same species.

## Goliath Giant Ancestry

| Ancestry | Trait | Effect | Uses |
|----------|-------|--------|------|
| **Fire** | Fire's Burn | On hit: +1d10 fire damage | PB/LR |
| **Frost** | Stone's Endurance | Reaction: reduce incoming damage by 1d12+CON | PB/LR |
| **Hill** | Hill's Tumble | On hit: target goes Prone (no save) | PB/LR |
| **Storm** | Storm's Thunder | Reaction when hit: 1d8 thunder to attacker | PB/LR |

**Ancestry tier (1v1):** Fire > Frost > Storm > Hill

Key insight: **Offense beats defense in short fights.** Fire's Burn ends fights faster, giving the opponent fewer turns to deal damage. Stone's Endurance (Frost) is excellent defense but doesn't accelerate the kill. Hill's Tumble (prone) is weak 1v1 since enemies stand up for free — it's a party-play trait.

## Human 2024

- **Resourceful:** Heroic Inspiration (advantage on one d20/LR)
- **Versatile:** Bonus Origin feat (Humans effectively get two feats at level 1)

Strong feat combo: Savage Attacker + Tough (+4 HP). Solid mid-tier pick — durable and consistent but Goliath ancestries with active traits outperform head-to-head.

---

# Bug Fixes Log

| Fix | Phase | Details |
|-----|-------|---------|
| Nick mastery "once per turn" | 4 | `_try_nick_extra_attack()` was firing on both Attack action and Action Surge. Added `nick_used_this_turn` flag. |
| Damage order per PHB p.28 | 3 | Adjustments (Stone's Endurance) must apply BEFORE Resistance, which applies BEFORE Vulnerability. |
| Action Surge at range | 3 | `_do_action_surge()` now moves toward opponent before attempting melee. Previously tried to melee at 60ft. |
| Javelin at 5ft in melee | 3 | Combat loop now skips `ranged_attack` when already in melee range. |
| Large Form gated to level 5+ | 3 | Goliath Large Form is not available before level 5. |
| Frost vs Stone Giant ancestry | 3 | Stone's Endurance belongs to Stone Giant (Frost Goliath), not Frost Giant. Frost = Frost's Chill (+1d6 cold). |

---

*dnd-combat-sim — updated Phase 4*

---

# Phase 7: Caster Classes — Level 3 & Level 5

**Sim Parameters:** n=3000 per matchup, 1v1 caster vs caster, aggressive tactics.
**Question:** How do Wizard, Sorcerer, and Cleric stack up against each other at L3 and L5?

## 🏆 Champion: Draconic Sorcerer (Level 5) — 83.1% avg win rate

## Rankings

```
Rank  Build                        Avg Win%   HP   AC
------------------------------------------------------
  1.  Draconic Sorcerer Human 5     83.1%     32   15
  2.  Evocation Wizard Human 5      79.3%     32   12
  3.  War Cleric Human 5            71.8%     48   18
  4.  War Cleric Human              33.0%     30   18
  5.  Draconic Sorcerer Human       20.1%     20   15
  6.  Evocation Wizard Human        12.7%     20   12
```

## Key Findings

**L5 dominates L3 across the board.** Fireball (8d6) + spell slot depth creates a massive power cliff.

**Sorcerer edges Wizard at L5** — identical spells, but Draconic Resilience (AC 15 vs 12) buys enough extra survivability to close out fights the wizard would lose. CHA vs INT doesn't matter — both hit spell_save_dc 15 at L5 with +4 ability mod + prof 3.

**War Cleric underperforms despite AC 18 + 48 HP** — high durability but Spirit Guardians takes a turn to set up, and in a fast caster duel that turn is often lethal. Cleric wins the long game but caster duels are short. Cleric shines vs martials (tested separately — see next phase).

**L3 casters are fragile.** With only L1-L2 slots, a single bad fight can drain all resources. Wizard at L3 (AC 12, 20 HP) is glass cannon territory — loses to almost everyone except other squishies.

## Spells Implemented (Phase 7)

| Spell | Level | Type | Notes |
|---|---|---|---|
| fire_bolt | Cantrip | Spell attack | Scales 1d10→2d10 at L5 |
| toll_the_dead | Cantrip | WIS save | 1d8/1d12 if target missing HP |
| sacred_flame | Cantrip | DEX save | Radiant, no half |
| magic_missile | 1 | Auto-hit | 3 darts × 1d4+1 |
| chromatic_orb | 1 | Spell attack | 3d8 fire |
| guiding_bolt | 1 | Spell attack | 4d6 + advantage granted |
| scorching_ray | 2 | Spell attack | 3 rays × 2d6 |
| spiritual_weapon | 2 | Bonus action | 1d8+WIS, no concentration |
| fireball | 3 | DEX save | 8d6 fire, half on save |
| spirit_guardians | 3 | Concentration aura | 3d8/turn to adjacent enemies |

