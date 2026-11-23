"""Run the scorer's offline regression checks: python3 check.py."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
CHECKS = ("adversarial.py", "malformed.py")


def main():
    failed = []
    for name in CHECKS:
        print(f"Running {name}", flush=True)
        result = subprocess.run([sys.executable, str(ROOT / "tests" / name)], cwd=ROOT)
        if result.returncode:
            failed.append(name)
            print(f"FAIL: {name} (exit {result.returncode})", flush=True)
    if failed:
        print("FAIL: " + ", ".join(failed), flush=True)
        return 1
    print("PASS: all scorer checks", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
