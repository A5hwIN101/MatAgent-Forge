from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from src.orchestrator.materials_api import get_material_data

load_dotenv()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant"
)

from src.orchestrator.materials_api import get_material_data

def parse_dataset(material_name: str) -> dict:
    """
    Retrieves material properties from Materials Project.
    Returns them as a dictionary.
    """
    props = get_material_data(material_name)
    return props if props else {}