import os
import sys
import subprocess
import socket
import threading
import time
import webbrowser

# ANSI color codes for premium console styling
COLOR_HEADER = "\033[95m"
COLOR_INFO = "\033[94m"
COLOR_SUCCESS = "\033[92m"
COLOR_WARNING = "\033[93m"
COLOR_ERROR = "\033[91m"
COLOR_RESET = "\033[0m"

# Service prefixes and colors
PREFIX_FRONTEND = f"\033[96m[FRONTEND]\033[0m"
PREFIX_BACKEND = f"\033[94m[BACKEND]\033[0m"
PREFIX_CELERY = f"\033[93m[CELERY]\033[0m"
PREFIX_SYSTEM = f"\033[95m[SYSTEM]\033[0m"

# List of spawned subprocesses
active_processes = []

def check_port(port):
    """Checks if a port is currently in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind(("127.0.0.1", port))
            return True  # Port is free
        except OSError:
            return False  # Port is busy

def check_redis():
    """Checks if Redis is running on standard port 6379."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.connect(("127.0.0.1", 6379))
            return True
        except OSError:
            return False

def print_banner():
    """Prints a premium visual terminal banner."""
    banner = f"""
{COLOR_HEADER}======================================================================
   🎬  CINEREC AI - UNIFIED PRODUCTION STACK ORCHESTRATOR
======================================================================{COLOR_RESET}
[+] OS Platform  : {sys.platform.upper()}
[+] Project Root : {os.getcwd()}
    """
    print(banner)

def stream_logs(process, prefix):
    """Reads stdout/stderr from a subprocess and prints with a prefix."""
    try:
        for line in iter(process.stdout.readline, b''):
            decoded = line.decode('utf-8', errors='replace').rstrip()
            print(f"{prefix} | {decoded}")
    except Exception as e:
        print(f"{PREFIX_SYSTEM} Log streaming error: {e}")
    finally:
        try:
            process.stdout.close()
        except Exception:
            pass

def terminate_services():
    """Gracefully terminates all active subprocesses."""
    if not active_processes:
        return
    print(f"\n{COLOR_WARNING}[!] Gracefully stopping all services...{COLOR_RESET}")
    for proc, name in active_processes:
        if proc.poll() is None:
            print(f"[-] Terminating {name}...")
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print(f"[{COLOR_ERROR}*{COLOR_RESET}] Force killing {name} (timeout)...")
                try:
                    proc.kill()
                except Exception:
                    pass
            except Exception as e:
                print(f"Error terminating {name}: {e}")
    active_processes.clear()
    print(f"{COLOR_SUCCESS}[✓] All services shut down successfully.{COLOR_RESET}")

def run_local_stack():
    """Runs Frontend, Backend, and Celery Worker locally in parallel."""
    print_banner()
    print(f"{COLOR_INFO}[*] Performing diagnostic checks...{COLOR_RESET}")

    # Check Ports
    frontend_free = check_port(3000)
    backend_free = check_port(8000)
    redis_running = check_redis()

    print(f"  - Frontend Port (3000) : {'FREE' if frontend_free else COLOR_ERROR + 'IN USE' + COLOR_RESET}")
    print(f"  - Backend Port (8000)  : {'FREE' if backend_free else COLOR_ERROR + 'IN USE' + COLOR_RESET}")
    print(f"  - Redis Broker (6379)  : {COLOR_SUCCESS + 'RUNNING' + COLOR_RESET if redis_running else COLOR_WARNING + 'NOT CONNECTED' + COLOR_RESET}")

    if not frontend_free:
        print(f"{COLOR_ERROR}[Error] Port 3000 is occupied. Stop any existing frontend processes.{COLOR_RESET}")
        return
    if not backend_free:
        print(f"{COLOR_ERROR}[Error] Port 8000 is occupied. Stop any existing backend/uvicorn processes.{COLOR_RESET}")
        return
    if not redis_running:
        print(f"{COLOR_WARNING}[Warning] Redis is not running on port 6379. Celery and backend operations might fail.{COLOR_RESET}")
        confirm = input("[?] Would you like to proceed anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return

    # Check for backend virtual environment / requirements
    print(f"\n{COLOR_INFO}[*] Initializing subprocesses...{COLOR_RESET}")

    try:
        # 1. Start Frontend Server (port 3000)
        print(f"[{COLOR_SUCCESS}+{COLOR_RESET}] Spawning Frontend Static Server on port 3000...")
        frontend_proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", "3000"],
            cwd="frontend",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        active_processes.append((frontend_proc, "Frontend Server"))
        threading.Thread(target=stream_logs, args=(frontend_proc, PREFIX_FRONTEND), daemon=True).start()

        # 2. Start Backend FastAPI (port 8000)
        print(f"[{COLOR_SUCCESS}+{COLOR_RESET}] Spawning FastAPI Backend Server on port 8000...")
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
            cwd="backend",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        active_processes.append((backend_proc, "Backend Server"))
        threading.Thread(target=stream_logs, args=(backend_proc, PREFIX_BACKEND), daemon=True).start()

        # 3. Start Celery Worker
        # Special Windows check: Celery defaults to prefork which crashes on Windows.
        # We explicitly supply '-P solo' to guarantee standard single-threaded execution on Windows.
        celery_cmd = [sys.executable, "-m", "celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
        if sys.platform == "win32":
            print(f"[{COLOR_SUCCESS}+{COLOR_RESET}] Running on Windows! Injecting '-P solo' for Celery pool support...")
            celery_cmd.append("-P")
            celery_cmd.append("solo")

        print(f"[{COLOR_SUCCESS}+{COLOR_RESET}] Spawning Celery Async Task Worker...")
        celery_proc = subprocess.Popen(
            celery_cmd,
            cwd="backend",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        active_processes.append((celery_proc, "Celery Worker"))
        threading.Thread(target=stream_logs, args=(celery_proc, PREFIX_CELERY), daemon=True).start()

        print(f"\n{COLOR_SUCCESS}[✓] All services spawned successfully!{COLOR_RESET}")
        print(f"{COLOR_INFO}[i] Opening http://localhost:3000 in your browser...{COLOR_RESET}")
        print(f"{COLOR_INFO}[i] Press Ctrl+C at any time to stop all services.{COLOR_RESET}\n")

        # Open the frontend in the default browser automatically
        try:
            webbrowser.open("http://localhost:3000")
        except Exception as e:
            print(f"{COLOR_WARNING}[!] Failed to automatically open browser: {e}{COLOR_RESET}")

        # Keep main thread alive and monitor processes
        while True:
            time.sleep(1.0)
            for proc, name in active_processes:
                if proc.poll() is not None:
                    print(f"\n{COLOR_ERROR}[!] Service '{name}' exited unexpectedly with code {proc.returncode}.{COLOR_RESET}")
                    terminate_services()
                    return

    except KeyboardInterrupt:
        terminate_services()
    except Exception as e:
        print(f"{COLOR_ERROR}[Error] Startup failed: {e}{COLOR_RESET}")
        terminate_services()

def run_docker_compose():
    """Runs the backend stack via Docker Compose."""
    print_banner()
    print(f"{COLOR_INFO}[*] Starting Docker Compose Services...{COLOR_RESET}")
    docker_path = os.path.join("backend", "docker-compose.yml")
    if not os.path.exists(docker_path):
        print(f"{COLOR_ERROR}[Error] backend/docker-compose.yml not found!{COLOR_RESET}")
        return

    try:
        # Attempt to run docker-compose
        cmd = ["docker", "compose", "-f", docker_path, "up", "--build"]
        print(f"[Running Command] {' '.join(cmd)}")
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print(f"\n{COLOR_WARNING}[!] Stopping Docker containers...{COLOR_RESET}")
        subprocess.run(["docker", "compose", "-f", docker_path, "down"])
    except Exception as e:
        print(f"{COLOR_ERROR}[Error] Could not start Docker Compose: {e}{COLOR_RESET}")

def run_individual_service(service_name):
    """Runs a single individual service."""
    print_banner()
    try:
        if service_name == "frontend":
            print(f"{COLOR_INFO}[*] Starting Static Frontend Server...{COLOR_RESET}")
            proc = subprocess.Popen([sys.executable, "-m", "http.server", "3000"], cwd="frontend")
            active_processes.append((proc, "Frontend Server"))
            time.sleep(0.5)
            # Open the frontend in the default browser automatically
            try:
                webbrowser.open("http://localhost:3000")
            except Exception as e:
                print(f"{COLOR_WARNING}[!] Failed to automatically open browser: {e}{COLOR_RESET}")
        elif service_name == "backend":
            print(f"{COLOR_INFO}[*] Starting FastAPI Backend...{COLOR_RESET}")
            proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"], cwd="backend")
            active_processes.append((proc, "Backend Server"))
        elif service_name == "celery":
            print(f"{COLOR_INFO}[*] Starting Celery Worker...{COLOR_RESET}")
            celery_cmd = [sys.executable, "-m", "celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info"]
            if sys.platform == "win32":
                celery_cmd.extend(["-P", "solo"])
            proc = subprocess.Popen(celery_cmd, cwd="backend")
            active_processes.append((proc, "Celery Worker"))
        elif service_name == "pipeline":
            print(f"{COLOR_INFO}[*] Starting Automated Ingestion Pipeline...{COLOR_RESET}")
            proc = subprocess.Popen([sys.executable, "automation/auto_runner.py"])
            active_processes.append((proc, "Automated Ingestion Pipeline"))

        print(f"\n{COLOR_SUCCESS}[✓] Service started.{COLOR_RESET}")
        print(f"{COLOR_INFO}[i] Press Ctrl+C to terminate.{COLOR_RESET}\n")
        
        while True:
            time.sleep(1.0)
            if proc.poll() is not None:
                print(f"\n{COLOR_WARNING}[!] Service exited with code {proc.returncode}{COLOR_RESET}")
                break
    except KeyboardInterrupt:
        terminate_services()
    except Exception as e:
        print(f"{COLOR_ERROR}[Error] Failed to start service: {e}{COLOR_RESET}")
        terminate_services()

def show_interactive_menu():
    """Renders the main interactive selection CLI menu."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"""
{COLOR_HEADER}======================================================================
   🎬  CINEREC AI - COMPREHENSIVE PRODUCTION STACK RUNNER
======================================================================{COLOR_RESET}
Welcome to CineRec AI orchestration manager! Select an option below:

  {COLOR_SUCCESS}1){COLOR_RESET} 🚀  Run Complete Development Stack (Frontend + Backend + Celery)
  {COLOR_SUCCESS}2){COLOR_RESET} 🐳  Run Complete Stack via Docker Compose
  {COLOR_SUCCESS}3){COLOR_RESET} 💻  Run Frontend Static Server Only (Port 3000)
  {COLOR_SUCCESS}4){COLOR_RESET} ⚙️   Run FastAPI Backend API Only (Port 8000)
  {COLOR_SUCCESS}5){COLOR_RESET} 📦  Run Celery Background Task Worker Only
  {COLOR_SUCCESS}6){COLOR_RESET} 🔄  Run Automated Ingestion Pipeline (file watcher)
  {COLOR_SUCCESS}7){COLOR_RESET} ❌  Exit

""")
        choice = input("[?] Choose an option (1-7): ").strip()
        if choice == "1":
            run_local_stack()
            input("\nPress Enter to return to main menu...")
        elif choice == "2":
            run_docker_compose()
            input("\nPress Enter to return to main menu...")
        elif choice == "3":
            run_individual_service("frontend")
            input("\nPress Enter to return to main menu...")
        elif choice == "4":
            run_individual_service("backend")
            input("\nPress Enter to return to main menu...")
        elif choice == "5":
            run_individual_service("celery")
            input("\nPress Enter to return to main menu...")
        elif choice == "6":
            run_individual_service("pipeline")
            input("\nPress Enter to return to main menu...")
        elif choice == "7":
            print(f"\n{COLOR_INFO}Thank you for using CineRec AI. Goodbye!{COLOR_RESET}")
            sys.exit(0)
        else:
            print(f"\n{COLOR_ERROR}Invalid selection. Please choose between 1 and 7.{COLOR_RESET}")
            time.sleep(1.5)

if __name__ == "__main__":
    # If standard CLI arguments are passed, we can route directly
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["--local", "-l", "local"]:
            run_local_stack()
        elif arg in ["--docker", "-d", "docker"]:
            run_docker_compose()
        elif arg == "frontend":
            run_individual_service("frontend")
        elif arg == "backend":
            run_individual_service("backend")
        elif arg == "celery":
            run_individual_service("celery")
        elif arg in ["pipeline", "watcher"]:
            run_individual_service("pipeline")
        else:
            show_interactive_menu()
    else:
        show_interactive_menu()
