# Character Creation Guidelines

## Armor Progression

Characters are assumed to acquire better equipment as they level, reflecting adventuring wealth.

| Level | Light Armor      | Medium Armor        | Heavy Armor  |
|-------|-----------------|---------------------|--------------|
| L1-2  | Leather          | Hide / Scale Mail   | Chain Mail   |
| L3    | Studded Leather  | Scale Mail          | Splint       |
| L5    | Studded Leather  | Breastplate         | Splint       |
| L7    | Studded Leather  | Half Plate          | Full Plate   |
| L9+   | Studded Leather  | Half Plate          | Full Plate   |

**Armor stat reference (2024 PHB):**

| Armor         | Type   | Base AC | DEX Cap | Notes                    |
|---------------|--------|---------|---------|--------------------------|
| studded_leather | light | 12     | —       |                          |
| scale_mail    | medium | 14     | +2      | Stealth disadvantage     |
| breastplate   | medium | 14     | +2      |                          |
| half_plate    | medium | 15     | +2      | Stealth disadvantage     |
| splint        | heavy  | 17     | 0       | STR 15 required          |
| plate         | heavy  | 18     | 0       | STR 15 required          |

**Rules:**

- **Unarmored classes** (Monk, Barbarian) use Unarmored Defense and ignore this table.
- **Bladesinger Wizards** must use light armor for Bladesong to function — `studded_leather` is the correct choice.
- **Shield proficiency** is independent of this table — keep shields as-is.
- **Armor upgrades only apply if the character has proficiency** with that armor tier. Check `data/classes/<class>.yaml` for proficiency lists.
- **Druids** may not wear metal armor by tradition — use `hide` (medium) regardless of level.
- **Draconic Sorcerers** use `draconic_resilience` (class feature, base AC 13 + DEX) instead of worn armor.
- **Hexblade Warlocks** gain medium armor proficiency via Hex Warrior at L1 — apply the medium armor progression.
- **Forge Clerics** have heavy armor proficiency from their subclass — apply the heavy armor progression.

## Armor in Build YAMLs

Armor is specified in the `armor:` field of each build YAML using the registry key from `data/armor/armor.yaml`:

```yaml
armor: splint       # heavy, AC 17
shield: true        # +2 AC bonus, independent of armor
```

Level 6 builds (between L5 and L7 thresholds) use the L5 armor.

## Ability Score Guidelines

### Fighter / Paladin (STR-based)
- STR 16–18 primary; CON 14–16; dump CHA/INT as needed
- Heavy armor removes the DEX requirement — DEX can be low (8–10)

### Ranger / Rogue (DEX-based)
- DEX 16–18 primary; CON 14 recommended
- Medium armor (ranger): DEX modifier capped at +2, so DEX 14+ is sufficient for max AC

### Caster (WIS/INT/CHA primary)
- Spellcasting stat 16–18 primary; CON 14 for concentration saves
- Light armor or mage armor where applicable

## Class Proficiency Reference

| Class           | Armor Proficiency         | Progression Tier |
|-----------------|--------------------------|------------------|
| Barbarian       | Light, Medium, Shield     | Unarmored Defense|
| Bard            | Light                     | Light            |
| Cleric (base)   | Light, Medium, Shield     | Medium           |
| Cleric (War/Forge/Tempest/Nature) | + Heavy  | Heavy            |
| Druid           | Light, Medium, Shield     | Medium (no metal)|
| Fighter         | All                       | Heavy            |
| Monk            | None                      | Unarmored Defense|
| Paladin         | All                       | Heavy            |
| Ranger          | Light, Medium, Shield     | Medium           |
| Rogue           | Light                     | Light            |
| Sorcerer        | None                      | Special (class feature) |
| Warlock (base)  | Light                     | Light            |
| Warlock (Hexblade) | + Medium, Shield       | Medium           |
| Wizard          | None                      | None (Bladesinger: Light) |
