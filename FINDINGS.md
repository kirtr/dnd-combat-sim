# D&D 2024 Combat Simulator — Findings

---

# Phase 4: Level 3 Subclasses *(current)*

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
