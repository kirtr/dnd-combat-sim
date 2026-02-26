#!/usr/bin/env python3
"""Calculate raw DPS against a standard AC target (training dummy).

Measures:
- Sustained DPR (average over many rounds, no Action Surge)
- Burst DPR (round 1 with Action Surge if available)
- DPR vs various ACs
"""

from __future__ import annotations
import sys
from pathlib import Path
from sim.loader import load_build
from sim.dice import d20, eval_dice, eval_dice_twice_take_best
from sim.models import Character, Weapon, MasteryProperty
from sim.actions import _calc_damage, _has_advantage, _has_disadvantage

BUILDS_DIR = Path(__file__).parent / "data" / "builds"
N_ROUNDS = 5000  # rounds to simulate for DPR


def simulate_dpr(char_template: Character, target_ac: int, n: int = N_ROUNDS, 
                 use_surge: bool = False, use_hide: bool = False,
                 depleted: bool = False) -> float:
    """Simulate average damage per round against a static AC target.
    
    Simplified: character attacks every round, uses class features optimally.
    No movement, no distance — pure damage output.
    """
    total_damage = 0
    
    for _ in range(n):
        char = char_template.deep_copy()
        # Depleted mode: drain all limited resources
        if depleted:
            for res in char.resources.values():
                res.current = 0
        round_damage = 0
        advantage = False
        
        # Heroic Inspiration: advantage on first attack
        heroic_available = False
        hi_res = char.resources.get("heroic_inspiration")
        if hi_res and hi_res.available:
            heroic_available = True
            hi_res.spend()
        
        # Reckless Attack (Barbarian) — always on in aggressive mode
        if "reckless_attack" in char.features:
            advantage = True
        
        # Pre-round: if Hide allowed and we're a rogue, assume successful hide
        if use_hide and char.sneak_attack_dice:
            advantage = True
        
        # Determine number of attack sequences
        num_sequences = 1
        if use_surge and char.resources.get("action_surge"):
            num_sequences = 2
        
        for seq in range(num_sequences):
            # Reset savage attacker per turn
            char._savage_used_this_turn = False
            
            # Find weapons
            melee_weapons = [w for w in char.weapons if w.is_melee or w.is_finesse]
            nick_weapon = None
            main_weapon = None
            
            for w in melee_weapons:
                if w.mastery == MasteryProperty.NICK:
                    nick_weapon = w
                elif main_weapon is None:
                    main_weapon = w
            
            if nick_weapon and not main_weapon:
                main_weapon = nick_weapon
                nick_weapon = None
            
            # If we have Nick weapon, attack with it first to trigger extra attack
            if nick_weapon and main_weapon:
                # Attack with Nick weapon
                attack_weapon = nick_weapon
                off_weapon = main_weapon
            elif main_weapon:
                attack_weapon = main_weapon
                off_weapon = None
            else:
                attack_weapon = char.weapons[0] if char.weapons else None
                off_weapon = None
            
            if not attack_weapon:
                continue
            
            num_attacks = 1 + char.extra_attacks
            vex_advantage = False
            
            for atk_idx in range(num_attacks):
                atk_adv = advantage or vex_advantage or (heroic_available and atk_idx == 0 and seq == 0)
                if heroic_available and atk_idx == 0 and seq == 0:
                    heroic_available = False  # consumed
                dmg = _resolve_single_attack(char, attack_weapon, target_ac, atk_adv)
                round_damage += dmg
                
                # Fire Giant: +1d10 fire on hit
                if dmg > 0 and char.giant_ancestry == "fire":
                    fire_res = char.resources.get("fire_giant")
                    if fire_res and fire_res.available:
                        fire_res.spend()
                        round_damage += eval_dice("1d10").total
                
                # Hill Giant: free prone on hit → advantage on subsequent attacks
                if dmg > 0 and char.giant_ancestry == "hill":
                    hill_res = char.resources.get("hill_giant")
                    if hill_res and hill_res.available:
                        hill_res.spend()
                        vex_advantage = True  # prone = advantage on melee
                
                # Vex mastery on hit
                if dmg > 0 and attack_weapon.mastery == MasteryProperty.VEX:
                    vex_advantage = True
                
                # Graze on miss
                if dmg == 0 and attack_weapon.mastery == MasteryProperty.GRAZE:
                    graze = max(0, char._attack_ability_mod(attack_weapon))
                    round_damage += graze
            
            # Nick extra attack
            if nick_weapon and off_weapon:
                nick_adv = advantage or vex_advantage
                # Nick attack: no ability mod to damage unless TWF style
                nick_dmg = _resolve_single_attack(
                    char, off_weapon, target_ac, nick_adv, 
                    no_ability_mod=char.fighting_style != "two_weapon_fighting"
                )
                round_damage += nick_dmg
                
                # Fire Giant on nick hit
                if nick_dmg > 0 and char.giant_ancestry == "fire":
                    fire_res = char.resources.get("fire_giant")
                    if fire_res and fire_res.available:
                        fire_res.spend()
                        round_damage += eval_dice("1d10").total
                
                # Hill Giant on nick hit
                if nick_dmg > 0 and char.giant_ancestry == "hill":
                    hill_res = char.resources.get("hill_giant")
                    if hill_res and hill_res.available:
                        hill_res.spend()
                        # already prone, no further effect in DPS sim
                
                if nick_dmg > 0 and off_weapon.mastery == MasteryProperty.VEX:
                    vex_advantage = True
                    
                if nick_dmg == 0 and off_weapon.mastery == MasteryProperty.GRAZE:
                    graze = max(0, char._attack_ability_mod(off_weapon))
                    round_damage += graze
        
        total_damage += round_damage
    
    return total_damage / n


def _resolve_single_attack(char: Character, weapon: Weapon, target_ac: int,
                           has_adv: bool, no_ability_mod: bool = False) -> int:
    """Resolve a single attack, return damage dealt (0 on miss, ignoring graze)."""
    roll = d20(advantage=has_adv)
    
    if roll == 1:
        return 0  # nat 1 always misses (graze handled separately)
    
    is_crit = roll == 20
    attack_bonus = char.attack_modifier(weapon)
    total = roll + attack_bonus
    
    if not is_crit and total < target_ac:
        return 0
    
    # Calculate damage
    gwf_min = None
    if (char.fighting_style == "great_weapon_fighting"
            and (weapon.is_two_handed or weapon.is_versatile)
            and weapon.is_melee):
        gwf_min = 3
    
    if char.has_savage_attacker and not getattr(char, "_savage_used_this_turn", False):
        base = eval_dice_twice_take_best(weapon.damage_dice, minimum=gwf_min)
        char._savage_used_this_turn = True
    else:
        base = eval_dice(weapon.damage_dice, minimum=gwf_min)
    
    damage = base.total
    
    if is_crit:
        crit_extra = eval_dice(weapon.damage_dice, minimum=gwf_min)
        damage += crit_extra.total
    
    if not no_ability_mod:
        damage += char.damage_modifier(weapon)
    
    # Sneak Attack
    if char.sneak_attack_dice and not char.sneak_attack_used and has_adv:
        sa = eval_dice(char.sneak_attack_dice).total
        if is_crit:
            sa += eval_dice(char.sneak_attack_dice).total
        damage += sa
        char.sneak_attack_used = True
    
    # Rage damage
    if char.is_raging and weapon.is_melee:
        damage += char.rage_damage
    
    return max(1, damage)


def main():
    builds = [
        "fighter_gwf_greatsword_2",
        "fighter_gwf_greatsword_orc_2",
        "fighter_gwf_greatsword_goliath_2",
        "fighter_gwf_greatsword_dragonborn_2",
        "fighter_tough_2",
        "fighter_dueling_longsword_2", 
        "fighter_defense_greatsword_2",
        "fighter_twf_shortswords_2",
        "fighter_archery_longbow_2",
        "rogue_rapier_2",
        "rogue_dual_wield_2",
        "rogue_dual_wield_halfling_2",
        "goliath_fire_fighter_gwf_2",
        "goliath_fire_fighter_twf_2",
        "goliath_hill_fighter_gwf_2",
        "goliath_hill_fighter_twf_2",
        "goliath_storm_fighter_gwf_2",
        "human_fighter_twf_2",
        "human_fighter_gwf_2",
    ]
    
    # Standard AC: fighter with no defense bonus = chain mail AC 16
    # Also test against AC 14 (light armor) and AC 18 (dueling+shield)
    test_acs = [14, 16, 18]
    
    print("=" * 90)
    print("  DPS ANALYSIS — Level 2 Builds (20,000 rounds per measurement)")
    print("=" * 90)
    
    # Sustained DPR (no surge, no hide)
    print(f"\n  {'SUSTAINED DPR (per round)':^86}")
    print(f"  {'Build':<35} {'AC 14':>10} {'AC 16':>10} {'AC 18':>10}")
    print("  " + "-" * 65)
    
    sustained = {}
    for name in builds:
        path = BUILDS_DIR / f"{name}.yaml"
        if not path.exists():
            continue
        char = load_build(path)
        dprs = []
        for ac in test_acs:
            dpr = simulate_dpr(char, ac, use_surge=False, use_hide=False)
            dprs.append(dpr)
        sustained[name] = dprs
        print(f"  {char.name:<35} {dprs[0]:>10.2f} {dprs[1]:>10.2f} {dprs[2]:>10.2f}")
    
    # Rogue with successful Hide (advantage)
    print(f"\n  {'ROGUE DPR WITH HIDE (advantage on all attacks)':^86}")
    print(f"  {'Build':<35} {'AC 14':>10} {'AC 16':>10} {'AC 18':>10}")
    print("  " + "-" * 65)
    
    for name in builds:
        if "rogue" not in name:
            continue
        path = BUILDS_DIR / f"{name}.yaml"
        if not path.exists():
            continue
        char = load_build(path)
        dprs = []
        for ac in test_acs:
            dpr = simulate_dpr(char, ac, use_surge=False, use_hide=True)
            dprs.append(dpr)
        print(f"  {char.name + ' (Hidden)':<35} {dprs[0]:>10.2f} {dprs[1]:>10.2f} {dprs[2]:>10.2f}")
    
    # Burst DPR (round 1 with Action Surge)
    print(f"\n  {'BURST DPR (Round 1 w/ Action Surge)':^86}")
    print(f"  {'Build':<35} {'AC 14':>10} {'AC 16':>10} {'AC 18':>10}")
    print("  " + "-" * 65)
    
    for name in builds:
        path = BUILDS_DIR / f"{name}.yaml"
        if not path.exists():
            continue
        char = load_build(path)
        dprs = []
        for ac in test_acs:
            dpr = simulate_dpr(char, ac, use_surge=True, use_hide=False)
            dprs.append(dpr)
        print(f"  {char.name:<35} {dprs[0]:>10.2f} {dprs[1]:>10.2f} {dprs[2]:>10.2f}")
    
    # Rogue burst with hide
    print(f"\n  {'ROGUE BURST (Hidden + both attacks)':^86}")
    print(f"  {'Build':<35} {'AC 14':>10} {'AC 16':>10} {'AC 18':>10}")
    print("  " + "-" * 65)
    
    for name in builds:
        if "rogue" not in name:
            continue
        path = BUILDS_DIR / f"{name}.yaml"
        if not path.exists():
            continue
        char = load_build(path)
        dprs = []
        for ac in test_acs:
            dpr = simulate_dpr(char, ac, use_surge=False, use_hide=True)
            dprs.append(dpr)
        print(f"  {char.name + ' (Hidden)':<35} {dprs[0]:>10.2f} {dprs[1]:>10.2f} {dprs[2]:>10.2f}")

    # Burst vs Depleted comparison at AC 16
    print(f"\n  {'BURST vs DEPLETED DPR (AC 16 only)':^86}")
    print(f"  {'Build':<35} {'Burst':>10} {'Sustained':>10} {'Depleted':>10}")
    print("  " + "-" * 65)

    for name in builds:
        path = BUILDS_DIR / f"{name}.yaml"
        if not path.exists():
            continue
        char = load_build(path)
        burst = simulate_dpr(char, 16, use_surge=True)
        sust = simulate_dpr(char, 16, use_surge=False)
        depl = simulate_dpr(char, 16, depleted=True)
        print(f"  {char.name:<35} {burst:>10.2f} {sust:>10.2f} {depl:>10.2f}")


if __name__ == "__main__":
    main()
