"""
Convenience entrypoint – starts the backend from the project root.

    python main.py
    # or from backend/:  uvicorn app.main:app --reload
"""

import subprocess
import sys


if __name__ == "__main__":
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0"],
        cwd="backend",
    )