def assemble_markdown(parsed: dict, analysis: dict, hypothesis: dict) -> str:
    # Material Summary
    formula = parsed.get("formula_pretty", "Unknown")
    symmetry = parsed.get("symmetry", {})
    space_group = symmetry.get("symbol", "Unknown")
    crystal_system = symmetry.get("crystal_system", "Unknown")

    lattice = parsed.get("structure", {}).get("lattice", {})
    a = lattice.get("a", "—")
    b = lattice.get("b", "—")
    c = lattice.get("c", "—")

    summary = f"""## 🧪 Material Summary
| Property    | Value        |
|-------------|--------------|
| Formula     | {formula}    |
| Structure   | {crystal_system} |
| Space Group | {space_group} |
| a           | {a} |
| b           | {b} |
| c           | {c} |
"""

    # ✅ Change 1: Computed Properties (only simple scalars, skip nested dicts/lists)
    props_table = "## 📊 Computed / Parsed Properties\n"
    props_table += "| Property | Value |\n|----------|-------|\n"
    for k, v in parsed.items():
        if isinstance(v, (int, float, str)):   # only include simple values
            props_table += f"| {k} | {v} |\n"

    # Analysis
    analysis_md = "## 🧩 Analysis\n"
    for k, v in analysis.items():
        analysis_md += f"- **{k}**: {v}\n"

    # ✅ Change 3: Hypotheses (always clean bullet points)
    hypothesis_md = "## 🔭 Hypotheses\n"
    if isinstance(hypothesis, dict):
        for k, v in hypothesis.items():
            hypothesis_md += f"- **{k}**: {v}\n"
    elif isinstance(hypothesis, list):
        for h in hypothesis:
            hypothesis_md += f"- {h}\n"
    elif isinstance(hypothesis, str):
        # split into lines and bullets
        lines = [l.strip("-• ").strip() for l in hypothesis.splitlines() if l.strip()]
        for l in lines:
            hypothesis_md += f"- {l}\n"
    else:
        hypothesis_md += "- No hypotheses generated.\n"

    return "\n".join([summary, props_table, analysis_md, hypothesis_md])