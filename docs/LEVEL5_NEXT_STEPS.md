# Level 5 Features — Implementation Checklist (Post-Chunk1A)

> Generated 2026-03-03. Read-only audit of `~/src/dnd-combat-sim`.

---

## 1. Sneak Attack Scaling (Rogue 5 → 3d6)

**Current state:** `sim/loader.py:277-281` — hardcoded `"2d6"` (level≥3) or `"1d6"`. No level-5 branch.

**Changes needed:**
| File | Location | Change |
|---|---|---|
| `sim/loader.py` | ~L276-281 | Add `elif level >= 5: sneak_attack_dice = "3d6"` before existing `level >= 3` check |

**Test:** `python -m sim --build rogue_thief_5 --vs fighter_champion_5 -n 1000` (need a level-5 rogue build YAML)

---

## 2. Divine Smite Scaling (Paladin 5 — 2nd-level slots → 3d8)

**Current state:** `sim/actions.py:298-316` `_try_divine_smite()` — always uses `"2d8"` (1st-level slot). No slot-level scaling.  
`sim/loader.py` — spell_slots wired at level 3 only (2× 1st-level for Paladin).

**Changes needed:**
| File | Location | Change |
|---|---|---|
| `sim/loader.py` | spell_slots setup (~L350-380) | Add 2nd-level slots for Paladin level 5: `{1: 4, 2: 2}` |
| `sim/actions.py` | `_try_divine_smite()` L298-316 | Pick highest available slot; dice = `(1 + slot_level)d8`; prefer higher slots for crits |
| `sim/tactics.py` | smite decision | (Optional) Add smite-slot preference logic: save 2nd-level for crits |

**Test:** `python -m sim --build vengeance_paladin_orc_5 --vs berserker_orc_5 -n 1000`

---

## 3. Eldritch Blast Beam Scaling (Warlock 5 → 2 beams)

**Current state:** `sim/combat.py:618-660` `_do_eldritch_blast()` — fires exactly **1 beam**. No level check.

**Changes needed:**
| File | Location | Change |
|---|---|---|
| `sim/combat.py` | `_do_eldritch_blast()` L618 | Compute `num_beams = 1 + (char.level - 1) // 6` (yields 2 at level 5). Loop attack+damage per beam. Apply Hex per beam. |
| `sim/models.py` | Character dataclass | Ensure `level` field exists (currently inferred from loader; verify it's stored) |

**Key detail:** Each beam is a separate attack roll → Hex triggers per beam hit. Agonizing Blast (+CHA) applies per beam.

**Test:** `python -m sim --build fiend_warlock_orc_5 --vs berserker_orc_5 -n 1000`

---

## 4. Stunning Strike (Monk 5)

**Current state:** No implementation exists anywhere. Monk has `focus_points` resource, `flurry_of_blows`, and `open_hand_technique` in `sim/tactics.py:191-197` and `sim/combat.py:133-134`.

**Changes needed:**
| File | Location | Change |
|---|---|---|
| `sim/models.py` | Condition enum | Add `STUNNED` condition (or verify it exists) |
| `sim/models.py` | `effective_ac` / attack resolution | Stunned → attacks have advantage, target auto-fails STR/CON saves |
| `sim/loader.py` | Monk level ≥ 5 block | Add `"stunning_strike"` to features |
| `sim/actions.py` | New function `_try_stunning_strike()` | After unarmed/monk weapon hit: spend 1 Focus Point, target makes CON save vs Monk DC (8+PB+WIS). Failure → Stunned until start of monk's next turn. |
| `sim/tactics.py` | Monk bonus action logic | Decide when to spend FP on Stunning Strike vs Flurry. Heuristic: use SS on first hit, Flurry otherwise. |
| `sim/combat.py` | `_resolve_melee_attack` or flurry handler | Hook `_try_stunning_strike()` after hit confirmation |
| `sim/effects.py` | Stunned effect | Duration 1 round, clears at start of monk's next turn |

**2024 PHB note:** Stunning Strike costs 1 FP and triggers on ANY unarmed strike hit (including Flurry hits). Target: CON save.

**Test:** `python -m sim --build open_hand_monk_5 --vs fighter_champion_5 -n 1000`

---

## 5. Uncanny Dodge (Rogue 5)

**Current state:** No implementation. Reaction framework exists (`reaction_used` field, `sim/models.py:243`, used for Storm's Thunder at L477-520).

**Changes needed:**
| File | Location | Change |
|---|---|---|
| `sim/loader.py` | Rogue level ≥ 5 | Add `"uncanny_dodge"` to features |
| `sim/models.py` | `take_damage()` (~L440-530) | Before applying damage, check if defender has `uncanny_dodge`, `reaction_used == False`, attacker is visible, and attack was a hit (not AoE). Halve damage. Set `reaction_used = True`. |
| `sim/actions.py` | Attack resolution | Pass `is_attack=True` flag to `take_damage()` so Uncanny Dodge knows it applies |

**Key detail:** Only works against attacks you can see (always true in 1v1 unless blinded). Halves the damage of ONE attack. Uses reaction.

**Test:** `python -m sim --build rogue_thief_5 --vs berserker_orc_5 -n 1000`

---

## 6. Shared Prerequisites (All Level-5 builds)

| Item | File | Change |
|---|---|---|
| `extra_attacks = 1` | `sim/loader.py` ~L399 | For Fighter/Paladin/Monk/Ranger at level 5: set `extra_attacks=1` |
| `proficiency_bonus = 3` | `sim/loader.py` L144 | Already handled ✅ |
| `level` field on Character | `sim/models.py` | Verify `level: int` is stored (needed for beam scaling, feature gates) |
| Level-5 build YAMLs | `data/builds/` | Create one per class: fighter, barbarian, monk, rogue, paladin, warlock |
| ASI/Feat at level 4 | `sim/loader.py` | Need to handle +2 to primary stat or feat selection |

---

## Priority Order

1. **Extra Attack + ASI** (shared prereq — everything else depends on it)
2. **Sneak Attack 3d6** (trivial, 2-line change)
3. **Eldritch Blast 2 beams** (moderate, self-contained loop refactor)
4. **Divine Smite scaling** (moderate, slot-level math + tactics)
5. **Uncanny Dodge** (moderate, reaction framework exists)
6. **Stunning Strike** (complex, new condition + save + tactics heuristic)

---

## Top 5 Risks & Pitfalls

1. **`level` field may not be stored on Character** — beam scaling and feature gates need it. If missing, everything breaks. Verify `sim/models.py` has `level: int` and `sim/loader.py` passes it.

2. **Stunning Strike + action economy** — 2024 PHB changed Stunning Strike timing (costs FP on hit, not on attack). Getting the hook point right (after hit confirmation but before damage?) and the FP budget (Flurry vs SS) is the hardest design call.

3. **Divine Smite slot selection** — naive "always burn highest slot" wastes resources. Need a tactics heuristic (e.g., save level-2 for crits, use level-1 otherwise). The current `_try_divine_smite` has no slot-level parameter.

4. **Eldritch Blast multi-beam + Hex interaction** — Hex triggers on each beam hit. Must ensure `_apply_hex` is called per-beam inside the loop, not once after all beams. Current single-beam code calls it inline — just needs to stay inside the loop.

5. **Uncanny Dodge in `take_damage()` coupling** — `take_damage()` is called from many paths (smite, hex, AoA retaliation, breath weapons). Uncanny Dodge only applies to *attacks*, not all damage. Need a flag or separate code path to distinguish attack damage from effect damage, or it'll incorrectly halve non-attack damage.
