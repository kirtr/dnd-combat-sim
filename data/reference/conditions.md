# Conditions Reference (2024 PHB)

## FRIGHTENED
While you have the Frightened condition, you experience the following effects:
- **Ability Checks and Attacks Affected.** You have Disadvantage on ability checks and attack rolls while the source of fear is within line of sight.
- **Can't Approach.** You can't willingly move closer to the source of fear.

*Sim note: "Within line of sight" is always true in 1v1. "Can't approach" is not yet enforced (future work).*

## PRONE
While you have the Prone condition:
- Your only movement option is to crawl (costs 2 ft per ft moved) or stand up (costs half your speed).
- You have Disadvantage on attack rolls.
- Attack rolls against you have Advantage if the attacker is within 5 ft, otherwise Disadvantage.

*Sim note: Standing up costs half speed. Opportunity attacks on leave not yet implemented.*

## INCAPACITATED
While Incapacitated you can't take actions or reactions.

## EXHAUSTION
Levels 1–6, each with cumulative penalties. Level 1: Disadvantage on ability checks. (Full table not yet needed for sim.)

---

## Sim-Internal Conditions
These are tracked in `Condition` enum in `sim/models.py` but are not formal PHB conditions.

## RAGING
*(Barbarian-specific sim state, not a PHB condition)*

While Raging, the barbarian:
- Adds rage damage bonus to melee STR attacks.
- Has resistance to Bludgeoning, Piercing, and Slashing damage.
- Ends if the barbarian doesn't attack or take damage before the start of their next turn (not yet enforced in sim).

*Sim note: Rage is tracked as a `Condition` for convenience. Rage-ending logic is simplified.*

## DODGING
*(Sim state representing the Dodge action, not a standalone PHB condition)*

While Dodging, the character:
- Attack rolls against them have Disadvantage (if the attacker can see them).
- They have Advantage on DEX saving throws.

*Sim note: Dodge condition is cleared at the start of the character's next turn.*

---

## Defined but Not Yet Implemented in Sim

The following appear in the `Condition` enum but are not yet applied or checked in combat:

- **GRAPPLED** – Speed becomes 0. Can't benefit from bonuses to speed. Ends when grappler is incapacitated or target moves out of reach.
- **POISONED** – Disadvantage on attack rolls and ability checks.
- **STUNNED** – Incapacitated, can't move, can only speak falteringly. Attack rolls against have Advantage. Fails STR and DEX saving throws.
