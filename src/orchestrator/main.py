# src/orchestrator/main.py

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import asyncio
from typing import Iterator

from src.agents.data_agent import parse_dataset
from src.agents.analysis_agent import analyze_material
from src.agents.hypothesis_agent import generate_hypothesis
from src.agents.simulation_agent import run_simulation_agent
from src.orchestrator.formatter import assemble_markdown # adjust if your path differs

# --- FastAPI Setup ---
app = FastAPI(title="MatAgent-Forge API")


# Add CORS middleware to allow the Next.js frontend (on port 3000) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def assemble_simulation_markdown(sim_result):
    lines = []
    lines.append("## 🔬 Simulation Feasibility")
    lines.append(f"**Verdict:** {sim_result.verdict}")
    if sim_result.details and sim_result.details.get("estimated_formation_energy_ev_per_atom") is not None:
        efe = sim_result.details["estimated_formation_energy_ev_per_atom"]
        lines.append(f"**Estimated formation energy:** {efe:.2f} eV/atom (heuristic)")
    lines.append("\n## ⚙️ Parameter Decisions")
    for r in sim_result.reasoning:
        lines.append(f"- {r}")
    lines.append("\n> Note: Simulation-backed reasoning. This is not authoritative database data.")
    return "\n".join(lines)


def run_pipeline(material_name: str, stream_callback: callable):
    # Use the callback function to send messages to the client

    stream_callback("🔹 Step 1: Parsing dataset...\n\n")
    try:
        parsed = parse_dataset(material_name)
        is_db_hit = isinstance(parsed, dict) and (
            ("material_id" in parsed) or ("formula_pretty" in parsed)
        ) and len(parsed) > 0
    except Exception as e:
        stream_callback(f"Data lookup failed: {e}\n\n")
        parsed = None
        is_db_hit = False

    if is_db_hit:
        stream_callback("🔹 Step 2: Analyzing results...\n")
        analysis = analyze_material(parsed)

        stream_callback("🔹 Step 3: Generating hypothesis...\n")
        hypothesis = generate_hypothesis(parsed)

        markdown_output = assemble_markdown(parsed, analysis, hypothesis)

        # Send final markdown report
        stream_callback(markdown_output)
        return

    # --- Simulation route (no authoritative DB hit) ---
    stream_callback("🔹 Database miss → Routing to simulation agent...\n")
    sim = run_simulation_agent(material_name)

    # Minimal markdown assembly for simulation mode
    sim_markdown = assemble_simulation_markdown(sim)

    # Send final simulation markdown
    stream_callback(sim_markdown)
    return


# --- API Endpoint Definition ---
@app.post("/api/analyze")
async def analyze_material_endpoint(request: Request):
    try:
        data = await request.json()
        material_name = data.get("material_name")
        if not material_name:
            return {"error": "Material name not provided"}, 400
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format"}, 400

    # 1. Create a Queue to pass data from the Thread -> Async Response
    queue = asyncio.Queue()
    
    # 2. Get the running event loop (safe because this endpoint is async)
    loop = asyncio.get_running_loop()

    def sync_pipeline_wrapper():
        """
        This runs in a separate thread. It executes the blocking run_pipeline logic
        and pushes results into the async queue using run_coroutine_threadsafe.
        """
        def callback(chunk: str):
            # Schedule the "put" operation on the main event loop
            asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)

        try:
            # --- EXECUTE YOUR PIPELINE HERE ---
            # Ensure 'run_pipeline' is imported/defined in your file context
            run_pipeline(material_name, callback)
        except Exception as e:
            # If pipeline crashes, send error to UI
            asyncio.run_coroutine_threadsafe(queue.put(f"\n\nError in pipeline: {str(e)}"), loop)
        finally:
            # 3. Send None to signal the end of the stream
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    # 4. Start the pipeline in a background thread executor
    loop.run_in_executor(None, sync_pipeline_wrapper)

    # 5. Define the Async Generator for StreamingResponse
    async def response_generator():
        while True:
            # Await the next chunk (non-blocking)
            chunk = await queue.get()
            
            # If we receive the 'None' sentinel, stop streaming
            if chunk is None:
                break
            
            yield chunk

    return StreamingResponse(
        response_generator(),
        media_type="text/plain"
    )