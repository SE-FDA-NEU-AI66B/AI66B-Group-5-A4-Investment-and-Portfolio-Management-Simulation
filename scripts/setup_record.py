"""Print the environment fields for the SETUP independent-verification table (#83).

Run it from the clone being verified, with that clone's venv Python. It reads values
only; it changes no files and never prints .env contents.
"""

import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(*command):
    try:
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fields = {
        "Date": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z (UTC%z)"),
        "OS": platform.platform(),
        "Python": platform.python_version(),
        "Git": _run("git", "--version").replace("git version ", ""),
        "Tested commit": (f"{_run('git', 'rev-parse', '--short', 'HEAD')} "
                          f"({_run('git', 'rev-parse', '--abbrev-ref', 'HEAD')})"),
        "Clone path is ASCII-only": str(str(ROOT).isascii()),
    }
    for name, value in fields.items():
        print(f"| {name} | {value} |")


if __name__ == "__main__":
    main()