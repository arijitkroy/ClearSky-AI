import subprocess
import time
import sys
import os
import threading

def start_backend():
    print("--> Starting FastAPI Backend on http://127.0.0.1:8000...")
    # Run uvicorn as a subprocess
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

def start_simulator():
    print("--> Starting Mock IoT Sensor Simulator (Streaming every 5s)...")
    # Run simulator as a subprocess
    return subprocess.Popen(
        [sys.executable, "simulator/simulator.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

def stream_logs(process, prefix):
    for line in iter(process.stdout.readline, ""):
        print(f"[{prefix}] {line.strip()}")
    process.stdout.close()

def main():
    # Make sure we are in the correct directory context
    os.environ["PYTHONPATH"] = os.path.abspath(os.path.dirname(__file__))

    backend_proc = None
    simulator_proc = None

    try:
        # Start backend
        backend_proc = start_backend()
        
        # Start a thread to read and print backend logs
        backend_logger = threading.Thread(target=stream_logs, args=(backend_proc, "BACKEND"), daemon=True)
        backend_logger.start()

        # Wait a moment for the server to bind and start up
        time.sleep(3)

        # Start simulator
        simulator_proc = start_simulator()
        
        # Start a thread to read and print simulator logs
        simulator_logger = threading.Thread(target=stream_logs, args=(simulator_proc, "SIMULATOR"), daemon=True)
        simulator_logger.start()

        print("\n=======================================================")
        print(" ClearSky AI Platform Services Are Online!")
        print(" - FastAPI REST API: http://127.0.0.1:8000/docs")
        print(" - Simulator Stream: Active pushing ~100 sensors")
        print(" - Next.js Frontend: Run 'npm run dev' inside frontend/")
        print(" Press Ctrl+C to terminate all services.")
        print("=======================================================\n")

        # Keep main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nTerminating all services...")
    finally:
        if simulator_proc:
            print("Stopping Simulator...")
            simulator_proc.terminate()
            simulator_proc.wait()
        if backend_proc:
            print("Stopping Backend...")
            backend_proc.terminate()
            backend_proc.wait()
        print("All processes stopped. Exiting.")

if __name__ == "__main__":
    main()
