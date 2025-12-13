import os
import typing # Needed for the patch
from dotenv import load_dotenv

# load_dotenv() is safe to run here
load_dotenv()
API_KEY = os.getenv("MP_API_KEY")

def get_material_data(material_name: str) -> dict:
    """
    Query Materials Project for a given material formula.
    Returns a dictionary of key properties.
    
    IMPORTANT: MPRester import is lazy-loaded inside this function to avoid Pydantic
    schema conflicts during FastAPI startup.
    """
    
    # --- COMPATIBILITY PATCH FOR PYTHON 3.10 ---
    # The mp_api library sometimes incorrectly assumes Python 3.11+
    # We inject 'NotRequired' into 'typing' from 'typing_extensions' to prevent the crash.
    try:
        import typing_extensions
        if not hasattr(typing, "NotRequired"):
            typing.NotRequired = typing_extensions.NotRequired
    except ImportError:
        pass # If typing_extensions isn't here, we can't fix it, so we let it fail naturally.
    # -------------------------------------------

    # --- LAZY IMPORT ---
    try:
        from mp_api.client import MPRester
        from pymatgen.core import Composition
    except ImportError as e:
        raise ImportError(f"Missing scientific library: {e}")


    if not API_KEY:
        raise ValueError("Materials Project API key not set in .env file")

    # Try to convert the material name to a clean formula before search
    try:
        comp = Composition(material_name)
        formula_search = comp.reduced_formula
    except Exception:
        formula_search = material_name

    with MPRester(API_KEY) as mpr:
        results = mpr.summary.search(
            formula=formula_search,
            fields=[
                "material_id",
                "formula_pretty",
                "energy_above_hull",
                "band_gap",
                "density",
                "volume",
                "nsites",
                "symmetry",
                "structure"
            ]
        )

        if results:
            # Convert the Pydantic model to a standard dictionary
            return results[0].as_dict() if hasattr(results[0], 'as_dict') else results[0].dict()
        else:
            return {}