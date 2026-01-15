# ============================================================================
# DATA AGENT - Complete Replacement
# File: src/agents/data_agent.py
# Purpose: Retrieve material properties from Materials Project API
# ============================================================================

from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from src.orchestrator.materials_api import get_material_data
from typing import Dict, Any, Optional

# Load environment variables
load_dotenv()

# Initialize LLM
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant"
)


class DataAgent:
    """
    DataAgent retrieves material properties from Materials Project API.
    
    This agent is designed to work with the LangGraph pipeline.
    """
    
    def __init__(self):
        """Initialize the DataAgent."""
        self.llm = llm
    
    async def run(self, material_formula: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve material data from Materials Project API.
        
        Args:
            material_formula: Material formula (e.g., "NaCl", "Fe2O3")
        
        Returns:
            Dictionary of material properties, or None if not found
        """
        try:
            print(f"[DataAgent.run] Querying Materials Project for: {material_formula}")
            
            # Query Materials Project API
            material_data = get_material_data(material_formula)
            
            if material_data:
                print(f"[DataAgent.run] ✓ Found {len(material_data)} properties")
                return material_data
            else:
                print(f"[DataAgent.run] ✗ No data found for {material_formula}")
                return None
        
        except Exception as e:
            print(f"[DataAgent.run] ✗ Error: {e}")
            raise


# ============================================================================
# LEGACY FUNCTION SUPPORT (for backward compatibility)
# ============================================================================

def parse_dataset(material_name: str) -> Dict[str, Any]:
    """
    DEPRECATED: Use DataAgent class instead.
    
    Retrieves material properties from Materials Project.
    Returns them as a dictionary.
    
    This function is kept for backward compatibility.
    """
    props = get_material_data(material_name)
    return props if props else {}