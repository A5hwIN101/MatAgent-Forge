from groq import Groq
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Now fetch the key
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# List available models
models = client.models.list()

for m in models.data:
    print(m.id)