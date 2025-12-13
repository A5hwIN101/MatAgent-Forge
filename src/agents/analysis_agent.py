from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

# Heavy model for deep reasoning
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile"
)

def analyze_material(parsed: dict) -> dict:
    analysis = {}

    # Thermal Behavior (no thermal props yet, so placeholder)
    analysis["Thermal Behavior"] = "No thermal data available in this query."

    # Mechanical Behavior (check if bulk/shear modulus exist)
    if "bulk_modulus" in parsed and parsed["bulk_modulus"]:
        analysis["Mechanical Behavior"] = f"Bulk modulus: {parsed['bulk_modulus']} GPa"
    else:
        analysis["Mechanical Behavior"] = "No mechanical signals identified."

    # Electronic Behavior (band gap, metallicity)
    band_gap = parsed.get("band_gap")
    if band_gap is not None:
        if band_gap > 0.1:
            analysis["Electronic Behavior"] = f"Semiconductor with band gap {band_gap:.2f} eV"
        else:
            analysis["Electronic Behavior"] = "Likely metallic (very small band gap)"
    else:
        analysis["Electronic Behavior"] = "No band gap data available."

    # Stability / Limitations (energy above hull)
    e_hull = parsed.get("energy_above_hull")
    if e_hull is not None:
        if e_hull < 0.05:
            analysis["Limitations"] = f"Stable phase (energy above hull {e_hull:.3f} eV/atom)"
        else:
            analysis["Limitations"] = f"Metastable (energy above hull {e_hull:.3f} eV/atom)"
    else:
        analysis["Limitations"] = "No stability data available."

    return analysis
