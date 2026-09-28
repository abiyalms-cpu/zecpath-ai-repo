"""
Runs the whole test suite and saves a readable result log.

Usage (from the project root):  python run_tests.py
Results are saved to logs/test_results.txt, overwritten on every run.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
RESULT_FILE = LOG_DIR / "test_results.txt"


def main() -> int:
    LOG_DIR.mkdir(exist_ok=True)

    completed = subprocess.run(
        [sys.executable, "-m", "pytest"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = completed.stdout + completed.stderr

    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    RESULT_FILE.write_text(f"Test run: {started}\n\n{output}", encoding="utf-8")

    print(output)
    print(f"Results saved to {RESULT_FILE}")
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())