# TODO

---

## Caster Classes

### Chunk C1 — Spell Engine + Evocation Wizard

**Engine (Codex):**
- [ ] `sim/spells.py` — SpellData dataclass + registry, load from `data/spells/*.yaml`
- [ ] `sim/loader.py` — parse `spells_known` from build YAMLs, add `spells_known: list[str]` to Character
- [ ] `sim/combat.py` — `cast_spell` action handler (`_do_cast_spell`), dispatch in `_execute_turn`
- [ ] `sim/tactics.py` — caster decision tree (slot priority + cantrip fallback)

**Data (done by Ridge):**
- [x] `data/spells/fire_bolt.yaml`
- [x] `data/spells/toll_the_dead.yaml`
- [x] `data/spells/sacred_flame.yaml`
- [x] `data/spells/magic_missile.yaml`
- [x] `data/spells/chromatic_orb.yaml`
- [x] `data/spells/scorching_ray.yaml`
- [x] `data/spells/fireball.yaml`
- [x] `data/classes/wizard.yaml`
- [x] `data/builds/evocation_wizard_human_3.yaml`
- [x] `data/builds/evocation_wizard_human_5.yaml`

**Validation:**
- [ ] `./dnd-sim show evocation_wizard_human_3` passes
- [ ] `./dnd-sim fight --build1 evocation_wizard_human_5 --build2 berserker_greatsword_orc_5 -n 100`
- [ ] Tests pass

### Chunk C2 — Sorcerer (Draconic)

- [ ] `data/classes/sorcerer.yaml` (sorcery points resource, same spell slot progression as wizard)
- [ ] `sim/loader.py` — sorcery points resource setup
- [ ] `data/builds/draconic_sorcerer_human_3.yaml`
- [ ] `data/builds/draconic_sorcerer_human_5.yaml`
- [ ] Validation

### Chunk C3 — Cleric (Life/War)

- [ ] `data/classes/cleric.yaml`
- [ ] `data/spells/guiding_bolt.yaml`, `data/spells/spirit_guardians.yaml`
- [ ] `data/builds/life_cleric_human_3.yaml`, `data/builds/war_cleric_human_5.yaml`
- [ ] Cleric-specific tactics (melee + spell hybrid)
- [ ] Validation

### Chunk C4 — Caster Rankings

- [ ] Run `./dnd-sim rank --tag caster -n 3000`
- [ ] Update FINDINGS.md with caster tier analysis
- [ ] Git push

---

## Chunk 1B — Class YAML level 4/5 feature declarations

- [x] fighter: level 4 ASI, level 5 extra_attack
- [x] barbarian: level 4 ASI, level 5 extra_attack + fast_movement
- [x] ranger: level 4 ASI, level 5 extra_attack
- [x] monk: level 4 ASI + slow_fall, level 5 extra_attack + stunning_strike
- [x] paladin: level 4 ASI, level 5 extra_attack
- [x] rogue: level 4 ASI, level 5 uncanny_dodge
- [x] warlock: level 4 ASI, level 5 eldritch_blast_upgrade
- [x] notes sections updated for new level 4/5 declarations
- [x] validation commands run (`./dnd-sim list`, `./dnd-sim show champion_gwf_orc_3`)
