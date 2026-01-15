# chat.py
import typing_extensions, typing
import sys

# Define a function to handle the stream output by just printing it to the console
def console_callback(chunk: str):
    """Prints the output chunk directly to the console buffer."""
    # Use sys.stdout.write and flush=True for immediate visibility (like streaming)
    sys.stdout.write(chunk)
    sys.stdout.flush()


# --- Main Logic ---
try:
    from src.orchestrator.main import run_pipeline
except ImportError as e:
    print(f"Error loading pipeline: {e}")
    sys.exit(1)


def chat_loop():
    print("🔬 MatAgent-Forge ready")
    while True:
        material_name = input("\nEnter material name (or 'exit'): ").strip()
        if material_name.lower() == "exit":
            break

        print("\n--- Running Pipeline ---")
        # Run pipeline with the required stream_callback argument
        # Note: Since the command-line interface doesn't need to return a dict,
        # we let the pipeline execute entirely using the console_callback.
        run_pipeline(material_name, console_callback)

        # Print final status message
        print("\n--- Pipeline Complete ---")


if __name__ == "__main__":
    # Ensure the typing extensions are set up before running the main loop
    # (This assumes the original intent of the typing_extensions lines)
    typing.NotRequired = typing_extensions.NotRequired
    
    chat_loop()