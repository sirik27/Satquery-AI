#!/usr/bin/env python3
"""
DrishtiAI Cross-Platform Development Runner
Detects OS, sets up virtualenv, installs deps, and launches backend + frontend concurrently.
Works on both Windows and macOS without modification.
"""

import os
import sys
import subprocess
import signal
import time
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / "venv"
FRONTEND_DIR = ROOT / "frontend"
REQUIREMENTS = ROOT / "requirements.txt"


def get_venv_python() -> Path:
    """Return the virtualenv Python binary path based on OS."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def get_venv_pip() -> Path:
    """Return the virtualenv pip binary path based on OS."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def create_venv():
    """Create a virtual environment if it doesn't already exist."""
    if not VENV_DIR.exists():
        print("📦 Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
        print("✅ Virtual environment created.")
    else:
        print("✅ Virtual environment already exists.")


def install_python_deps():
    """Install/upgrade Python dependencies from requirements.txt."""
    pip = get_venv_pip()
    python = get_venv_python()

    print("⬆️  Upgrading pip...")
    subprocess.check_call([str(python), "-m", "pip", "install", "--upgrade", "pip"],
                          stdout=subprocess.DEVNULL)

    print("📥 Installing Python dependencies...")
    subprocess.check_call([str(pip), "install", "-r", str(REQUIREMENTS)])
    print("✅ Python dependencies installed.")


def install_frontend_deps():
    """Install npm dependencies for the frontend."""
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print("📥 Installing frontend dependencies...")
        subprocess.check_call(["npm", "install"], cwd=str(FRONTEND_DIR))
        print("✅ Frontend dependencies installed.")
    else:
        print("✅ Frontend dependencies already installed.")


def copy_env_if_missing():
    """Copy .env.example to .env if .env doesn't exist."""
    env_file = ROOT / ".env"
    env_example = ROOT / ".env.example"
    if not env_file.exists() and env_example.exists():
        import shutil
        shutil.copy(str(env_example), str(env_file))
        print("📋 Copied .env.example → .env (edit with your values)")

    frontend_env = FRONTEND_DIR / ".env"
    frontend_env_example = FRONTEND_DIR / ".env.example"
    if not frontend_env.exists() and frontend_env_example.exists():
        import shutil
        shutil.copy(str(frontend_env_example), str(frontend_env))
        print("📋 Copied frontend/.env.example → frontend/.env")


def create_data_dirs():
    """Ensure data directories exist."""
    (ROOT / "data" / "tile_cache").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "uploads").mkdir(parents=True, exist_ok=True)
    print("📁 Data directories ready.")


def main():
    print("=" * 60)
    print("  🛰️  DrishtiAI Development Server Launcher")
    print(f"  OS: {sys.platform} | Python: {sys.version.split()[0]}")
    print("=" * 60)
    print()

    # Setup
    create_venv()
    install_python_deps()
    install_frontend_deps()
    copy_env_if_missing()
    create_data_dirs()

    print()
    print("🚀 Starting DrishtiAI servers...")
    print("   Backend:  http://localhost:8000")
    print("   Frontend: http://localhost:5173")
    print("   Press Ctrl+C to stop both servers.")
    print()

    python = get_venv_python()

    # Launch backend
    backend_proc = subprocess.Popen(
        [str(python), "-m", "uvicorn", "backend.main:app",
         "--reload", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(ROOT),
    )

    # Launch frontend
    npm_cmd = shutil.which("npm") or "/usr/local/bin/npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Handle graceful shutdown
    processes = [backend_proc, frontend_proc]

    def shutdown(signum, frame):
        print("\n🛑 Shutting down servers...")
        for proc in processes:
            try:
                proc.terminate()
            except Exception:
                pass
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        print("👋 DrishtiAI servers stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for either process to exit
    try:
        while True:
            for proc in processes:
                retcode = proc.poll()
                if retcode is not None:
                    print(f"⚠️  A process exited with code {retcode}. Shutting down...")
                    shutdown(None, None)
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
