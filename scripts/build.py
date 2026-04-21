"""Build script for creating application distributions."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: str | None = None) -> None:
    """Run a command and handle errors.

    Args:
        cmd: Command to run as list of strings
        cwd: Working directory for the command
    """
    try:
        result = subprocess.run(
            cmd, check=True, cwd=cwd, capture_output=True, text=True
        )
        print(f"Command {' '.join(cmd)} succeeded")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Command {' '.join(cmd)} failed with error:")
        print(e.stderr)
        sys.exit(1)


def build_app() -> None:
    """Build the application for distribution."""
    project_root = Path(__file__).parent.parent

    print("Building application...")

    # Install dependencies
    print("Installing dependencies...")
    run_command([sys.executable, "-m", "uv", "sync", "--all-extras"])

    # Build with pyinstaller
    print("Building with pyinstaller...")
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=tkinter-app",
        "--add-data=src/app;src/app",
        "src/app/main.py",
    ]
    run_command(pyinstaller_cmd, cwd=str(project_root))

    print("Build completed successfully!")
    print("Check the 'dist' directory for the built application.")


if __name__ == "__main__":
    build_app()
