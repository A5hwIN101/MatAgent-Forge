# src/agents/simulation_agent.py
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import re
from pymatgen.core import Lattice, Structure

# --- pymatgen + m3gnet ---
from pymatgen.core import Structure, Composition
from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDEntry
from m3gnet.models import M3GNet
# Load M3GNet once globally
m3gnet_model = M3GNet.load()

# --- Domain data (minimal; extend as needed) ---
ELECTRONEGATIVITY = {
    "H": 2.20, "Li": 0.98, "Be": 1.57, "B": 2.04, "C": 2.55, "N": 3.04, "O": 3.44, "F": 3.98,
    "Na": 0.93, "Mg": 1.31, "Al": 1.61, "Si": 1.90, "P": 2.19, "S": 2.58, "Cl": 3.16,
    "K": 0.82, "Ca": 1.00, "Fe": 1.83, "Cu": 1.90, "Zn": 1.65,
    # Extend as needed
}

OXIDATION_STATES = {
    "H": [+1, -1], "O": [-2], "F": [-1],
    "Cl": [-1, +1, +3, +5, +7],
    "N": [-3, +3, +5], "C": [-4, +2, +4],
    "Na": [+1], "K": [+1], "Mg": [+2], "Ca": [+2],
    "Fe": [+2, +3], "Cu": [+1, +2], "Zn": [+2],
    "Al": [+3], "Si": [+4], "P": [+5, -3],
}

IONIC_RADII_PM = {
    "Na": 102, "K": 138, "Ca": 100, "Mg": 72, "Al": 53, "Si": 40,
    "Fe": 78, "Cu": 73, "Zn": 74, "Cl": 181, "O": 140,
}

# --- Data structures ---
@dataclass
class ParameterDecision:
    name: str
    ok: bool
    justification: str

@dataclass
class SimulationResult:
    mode: str
    verdict: str
    reasoning: List[str]
    details: Dict[str, Optional[float]]

# --- Basic competing phase library for Ehull ---
# Each entry: system key (tuple of elements) → list of (Composition, energy_per_atom)
# Energies here are placeholders; replace with M3GNet predictions or database values for accuracy.

COMPETING_PHASES_LIBRARY: Dict[Tuple[str, ...], List[Tuple[Composition, float]]] = {
    # Cu–Cl system
    ("Cu", "Cl"): [
        (Composition("Cu"), 0.0),          # elemental Cu
        (Composition("Cl2"), 0.0),         # elemental Cl2
        (Composition("CuCl"), -0.8),       # stable binary
        (Composition("CuCl2"), -0.6),      # another binary
    ],
    # Na–Al–Si–O system
    ("Na", "Al", "Si", "O"): [
        (Composition("Na"), 0.0),
        (Composition("Al"), 0.0),
        (Composition("Si"), 0.0),
        (Composition("O2"), 0.0),
        (Composition("Na2O"), -1.2),
        (Composition("Al2O3"), -1.5),
        (Composition("SiO2"), -1.6),
    ],
    # Fe–O system
    ("Fe", "O"): [
        (Composition("Fe"), 0.0),
        (Composition("O2"), 0.0),
        (Composition("FeO"), -1.0),
        (Composition("Fe2O3"), -1.2),
    ],
    # Mg–O system
    ("Mg", "O"): [
        (Composition("Mg"), 0.0),
        (Composition("O2"), 0.0),
        (Composition("MgO"), -1.1),
    ],
    # Si–O system
    ("Si", "O"): [
        (Composition("Si"), 0.0),
        (Composition("O2"), 0.0),
        (Composition("SiO2"), -1.6),
    ],
    # Generic halides (Na–Cl)
    ("Na", "Cl"): [
        (Composition("Na"), 0.0),
        (Composition("Cl2"), 0.0),
        (Composition("NaCl"), -0.9),
    ],
}

def safe_predict_energy(structure: Structure) -> Optional[float]:
    """
    Wrapper around M3GNet.predict_structure to avoid crashes from dtype mismatches.
    Returns a float formation energy if successful, or None if prediction fails.
    """
    try:
        from m3gnet.models import M3GNet
        model = M3GNet.load()
        return float(model.predict_structure(structure))
    except Exception as e:
        print(f"[Warning] M3GNet prediction failed: {e}")
        return None

def generate_prototype_structure(formula: str) -> Optional[Structure]:
    """
    Build a candidate crystal Structure for the given formula using simple prototypes:
      - NaCl-type (rock-salt, AB) for binary halides/oxides or general 1:1 systems
      - Perovskite ABO3 (common oxide family) if stoichiometry and O are present
      - Spinel AB2O4 (oxide family) if stoichiometry and O are present

    Approach:
      1) Parse stoichiometry and split roles (cations/anions) via electronegativity.
      2) Use SubstitutionProbabilityModel to refine role assignments.
      3) Choose a template by stoichiometry heuristic.
      4) Estimate lattice parameter(s) from ionic radii (crude), then build Structure.

    Returns a Structure or None if a suitable prototype cannot be built.
    """
    try:
        comp = Composition(formula)
        parsed = parse_formula(formula)
        elements = sorted([str(e) for e in comp.elements], key=lambda e: ELECTRONEGATIVITY.get(e, 2.0))
        mid = max(1, len(elements) // 2)
        cation_pool = elements[:mid]
        anion_pool = elements[mid:]

        # Role selection: pick dominant species by count within each pool
        cation_base = max(cation_pool, key=lambda e: parsed.get(e, 0)) if cation_pool else None
        anion_base = max(anion_pool, key=lambda e: parsed.get(e, 0)) if anion_pool else None
        if not cation_base or not anion_base:
            return None

        spm = SubstitutionProbabilityModel()

        def refine_element(el: str, prob_thresh: float = 0.2) -> str:
            subs = spm.get_substitutions(el)
            filtered = {k: v for k, v in subs.items() if v >= prob_thresh}
            return max(filtered, key=filtered.get) if filtered else el

        # Refine cation/anion representatives
        A = refine_element(cation_base)
        X = refine_element(anion_base)

        # Helpers: lattice/structure builders
        from pymatgen.core import Lattice

        def pm_to_angstrom(pm: float) -> float:
            # crude conversion; keep a sensible lower bound
            return max(4.5, pm * 0.01)

        def rs_lattice_param(a_el: str, x_el: str) -> float:
            rc = IONIC_RADII_PM.get(a_el, 100)  # pm
            ra = IONIC_RADII_PM.get(x_el, 100)  # pm
            return pm_to_angstrom(rc + ra)

        def build_rocksalt(a: float, cation: str, anion: str) -> Structure:
            lattice = Lattice.cubic(a)
            species = [cation, anion]
            frac_coords = [[0, 0, 0], [0.5, 0.5, 0.5]]
            return Structure(lattice, species, frac_coords)

        def build_perovskite(a: float, A_site: str, B_site: str, O_site: str = "O") -> Structure:
            # Simple cubic perovskite (Pm-3m) with 5 atoms:
            # A at (0,0,0); B at (0.5,0.5,0.5); O at face centers
            lattice = Lattice.cubic(a)
            species = [A_site, B_site, O_site, O_site, O_site]
            frac_coords = [
                [0, 0, 0],          # A
                [0.5, 0.5, 0.5],    # B
                [0.5, 0.5, 0.0],    # O1
                [0.5, 0.0, 0.5],    # O2
                [0.0, 0.5, 0.5],    # O3
            ]
            return Structure(lattice, species, frac_coords)

        def build_spinel(a: float, A_site: str, B_site: str, O_site: str = "O") -> Structure:
            # Minimal conventional spinel-like motif (not full Fd-3m multiplicities),
            # kept small for quick surrogate predictions. It's a schematic prototype.
            lattice = Lattice.cubic(a)
            species = [A_site, B_site, B_site, O_site, O_site, O_site, O_site]
            frac_coords = [
                [0.125, 0.125, 0.125],  # A (tetra-like)
                [0.5,   0.5,   0.5],    # B1 (octa-like)
                [0.0,   0.5,   0.5],    # B2
                [0.25,  0.25,  0.25],   # O1
                [0.75,  0.75,  0.25],   # O2
                [0.75,  0.25,  0.75],   # O3
                [0.25,  0.75,  0.75],   # O4
            ]
            return Structure(lattice, species, frac_coords)

        # Decide template based on stoichiometry and presence of oxygen
        has_O = "O" in parsed
        n_A = parsed.get(A, 0)
        n_X = parsed.get(X, 0)
        total_atoms = sum(parsed.values())

        # Try Perovskite ABO3 if oxygen present and stoichiometry roughly matches
        # Heuristic: 2 or 3 distinct elements, counts compatible with A:B:O ~ 1:1:3
        if has_O and len(parsed) >= 3:
            # pick B as the strongest cation distinct from A
            cation_candidates = [e for e in cation_pool if e != A]
            B_base = cation_candidates[0] if cation_candidates else A
            B = refine_element(B_base)

            # lattice parameter from B–O radii (crude)
            a_perov = pm_to_angstrom(IONIC_RADII_PM.get(B, 80) + IONIC_RADII_PM.get("O", 140))
            try:
                return build_perovskite(a_perov, A_site=A, B_site=B, O_site="O")
            except Exception:
                pass  # fall through

        # Try Spinel AB2O4 if oxygen present and stoichiometry hints at A:B:O ~ 1:2:4
        if has_O and len(parsed) >= 3:
            cation_candidates = [e for e in cation_pool if e != A]
            B_base = cation_candidates[0] if cation_candidates else A
            B = refine_element(B_base)
            a_spinel = pm_to_angstrom(IONIC_RADII_PM.get(B, 80) + IONIC_RADII_PM.get("O", 140))
            try:
                return build_spinel(a_spinel, A_site=A, B_site=B, O_site="O")
            except Exception:
                pass  # fall through

        # Default: Rock-salt (NaCl-type) for binary systems or general fallback
        a_rs = rs_lattice_param(A, X)
        try:
            return build_rocksalt(a_rs, cation=A, anion=X)
        except Exception:
            return None

    except Exception as e:
        print(f"Structure generation failed: {e}")
        return None

def get_competing_phases(formula: str) -> List[Tuple[Composition, float]]:
    """
    Look up competing phases for the chemical system of the given formula.
    Returns a list of (Composition, energy_per_atom).
    """
    comp = Composition(formula)
    system_key = tuple(sorted([el.symbol for el in comp.elements]))
    return COMPETING_PHASES_LIBRARY.get(system_key, [])
    
# --- Helpers ---
def parse_formula(formula: str) -> Dict[str, int]:
    tokens = re.findall(r'([A-Z][a-z]?)(\d*)', formula)
    composition = {}
    for el, count in tokens:
        n = int(count) if count else 1
        composition[el] = composition.get(el, 0) + n
    return composition

def check_stoichiometry_veto(composition: Dict[str, int]) -> Tuple[bool, str]:
    if not composition or len(composition) < 2:
        return False, "Invalid or unary composition."
    sorted_els = sorted(composition.keys(), key=lambda e: ELECTRONEGATIVITY.get(e, 2.0))
    cation_cands = sorted_els[:max(1, len(sorted_els)//2)]
    anion_cands = sorted_els[max(1, len(sorted_els)//2):]
    total = 0
    assignments = []
    for e in cation_cands:
        mult = composition[e]
        pos_states = [s for s in OXIDATION_STATES.get(e, []) if s > 0]
        if pos_states:
            ox = pos_states[0]
            total += ox * mult
            assignments.append((e, ox, mult))
    for e in anion_cands:
        mult = composition[e]
        neg_states = [s for s in OXIDATION_STATES.get(e, []) if s < 0]
        if neg_states:
            ox = neg_states[0]
            total += ox * mult
            assignments.append((e, ox, mult))
    steps = ", ".join([f"{e}({ox})×{m}" for e, ox, m in assignments]) or "no assignments"
    if total == 0:
        return True, f"Charge neutrality achievable via assignments: {steps}."
    return False, f"Net charge {total} with common oxidation states ({steps}); unlikely."

def electronegativity_trend(composition: Dict[str, int]) -> Tuple[bool, str]:
    els = list(composition.keys())
    en_values = [ELECTRONEGATIVITY.get(e, None) for e in els]
    if any(v is None for v in en_values):
        return False, "Missing EN data."
    delta = max(en_values) - min(en_values)
    if delta >= 1.0:
        return True, f"ΔEN ≈ {delta:.2f} suggests plausible bonding."
    elif delta >= 0.5:
        return True, f"ΔEN ≈ {delta:.2f} indicates moderate polarity."
    else:
        return False, f"ΔEN ≈ {delta:.2f} is low; metallic clustering likely."

def crystal_rules_feasibility(composition: Dict[str, int]) -> Tuple[bool, str]:
    els = sorted(composition.keys(), key=lambda e: ELECTRONEGATIVITY.get(e, 2.0))
    cations = [e for e in els[:max(1, len(els)//2)] if IONIC_RADII_PM.get(e)]
    anions = [e for e in els[max(1, len(els)//2):] if IONIC_RADII_PM.get(e)]
    if not cations or not anions:
        return False, "Insufficient radii data."
    rc = IONIC_RADII_PM[cations[0]]
    ra = IONIC_RADII_PM[anions[0]]
    ratio = rc / ra
    if 0.3 <= ratio <= 0.7:
        return True, f"Radius ratio ≈ {ratio:.2f} within stable window."
    return False, f"Radius ratio ≈ {ratio:.2f} outside stable window."

def analogue_comparison_hint(formula: str) -> Tuple[bool, str]:
    if re.search(r'Cl|Br|I', formula):
        return True, "Halide family detected; analogues exist."
    if re.search(r'O', formula):
        return True, "Oxide family detected; analogues exist."
    return False, "No clear analogue family detected."

def generate_prototype_structure(formula: str) -> Optional[Structure]:
    comp = Composition(formula)
    parsed = parse_formula(formula)
    elements = sorted([str(e) for e in comp.elements],
                      key=lambda e: ELECTRONEGATIVITY.get(e, 2.0))
    mid = max(1, len(elements)//2)
    cation = elements[0]
    anion = elements[-1]

    # crude lattice parameter from ionic radii
    rc = IONIC_RADII_PM.get(cation, 100)
    ra = IONIC_RADII_PM.get(anion, 100)
    a_ang = max(4.5, (rc + ra) * 0.01)

    # fallback: NaCl-type
    lattice = Lattice.cubic(a_ang)
    species = [cation, anion]
    frac_coords = [[0,0,0],[0.5,0.5,0.5]]
    return Structure(lattice, species, frac_coords)

def predict_formation_energy(structure: Structure) -> Tuple[Optional[float], str]:
    energy = safe_predict_energy(structure)
    if energy is not None:
        return energy, f"M3GNet predicted formation energy ≈ {energy:.3f} eV/atom."
    else:
        return None, "M3GNet prediction failed: dtype mismatch or other error."

def compute_ehull(formula: str, candidate_energy: float, competing_phases: List[Tuple[Composition, float]]) -> Tuple[Optional[float], str]:
    try:
        entries = [PDEntry(comp, en) for comp, en in competing_phases]
        candidate_entry = PDEntry(Composition(formula), candidate_energy)
        pd = PhaseDiagram(entries + [candidate_entry])
        ehull = pd.get_e_above_hull(candidate_entry)
        return float(ehull), f"Ehull ≈ {ehull:.3f} eV/atom."
    except Exception as e:
        return None, f"Ehull computation failed: {e}"

# --- Main API ---
def run_simulation_agent(formula: str) -> SimulationResult:
    composition = parse_formula(formula)

    # Step 1: Veto
    v_ok, v_just = check_stoichiometry_veto(composition)
    decisions: List[ParameterDecision] = [ParameterDecision("Stoichiometry Veto", v_ok, v_just)]
    if not v_ok:
        return SimulationResult(
            "simulation",
            "Not feasible",
            [f"{decisions[0].name}: No — {v_just}"],
            {"formation_energy_ev_per_atom": None, "ehull_ev_per_atom": None}
        )

    # Step 2: Filters
    ok_en, just_en = electronegativity_trend(composition)
    decisions.append(ParameterDecision("Electronegativity", ok_en, just_en))

    ok_analog, just_analog = analogue_comparison_hint(formula)
    decisions.append(ParameterDecision("Analogues", ok_analog, just_analog))

    ok_crystal, just_crystal = crystal_rules_feasibility(composition)
    decisions.append(ParameterDecision("Crystal Chemistry Rules", ok_crystal, just_crystal))

    filters_pass = sum(1 for d in decisions[1:] if d.ok)
    filters_fail = len(decisions[1:]) - filters_pass
    if filters_fail >= 2:
        return SimulationResult(
            "simulation",
            "Not feasible",
            [f"{d.name}: {'Yes' if d.ok else 'No'} — {d.justification}" for d in decisions],
            {"formation_energy_ev_per_atom": None, "ehull_ev_per_atom": None}
        )

    # Step 3: Structure → M3GNet → Ehull
    est_fe: Optional[float] = None
    ehull: Optional[float] = None

    try:
        structure = None
        if "parsed" in locals() and isinstance(parsed, dict) and "structure" in parsed:
            structure = Structure.from_dict(parsed["structure"])
        else:
            structure = generate_prototype_structure(formula)

        if structure:
            est_fe, fe_msg = predict_formation_energy(structure)
            decisions.append(ParameterDecision("Formation Energy (M3GNet)", est_fe is not None and est_fe < 0.0, fe_msg))

            competing_phases = get_competing_phases(formula)
            if competing_phases and est_fe is not None:
                ehull, ehull_msg = compute_ehull(formula, est_fe, competing_phases)
                decisions.append(ParameterDecision("Convex Hull Stability (Ehull)", ehull is not None and ehull <= 0.2, ehull_msg))
            else:
                decisions.append(ParameterDecision("Convex Hull Stability (Ehull)", False, "No competing phases available for this system."))
        else:
            decisions.append(ParameterDecision("Formation Energy (M3GNet)", False, "No structure available; cannot run M3GNet."))
    except Exception as e:
        decisions.append(ParameterDecision("Formation Energy (M3GNet)", False, f"M3GNet prediction failed: {e}"))

    # Verdict assembly
    if ehull is not None:
        if ehull <= 0.1:
            verdict = "Feasible"
        elif ehull <= 0.2:
            verdict = "Metastable"
        else:
            verdict = "Not feasible"
    else:
        if est_fe is not None and est_fe < 0.0:
            verdict = "Feasible"
        else:
            verdict = "Metastable" if filters_pass >= 2 else "Uncertain"

    reasoning = [f"{d.name}: {'Yes' if d.ok else 'No'} — {d.justification}" for d in decisions]
    details = {"formation_energy_ev_per_atom": est_fe, "ehull_ev_per_atom": ehull}

    return SimulationResult("simulation", verdict, reasoning, details)


    # --- Optional: quick CLI test ---
if __name__ == "__main__":
    test_formulas = ["CuCl", "NaCl", "Fe2O3", "MgO", "SiO2", "Cu2N5"]
    for formula in test_formulas:
        res = run_simulation_agent(formula)
        print(f"\n== {formula} ==")
        print("Verdict:", res.verdict)
        for r in res.reasoning:
            print("-", r)
        print("Details:", res.details)