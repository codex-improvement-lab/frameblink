"""Install the built wheel in a clean local venv and run its included demo."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import venv


ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / ".frameblink"
SCRATCH.mkdir(exist_ok=True)
assert SCRATCH.resolve().is_relative_to(ROOT.resolve())


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/package_smoke.py dist/frameblink-*.whl")
    wheel = Path(sys.argv[1]).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="smoke-", dir=SCRATCH) as name:
        scratch = Path(name).resolve()
        assert scratch.is_relative_to(SCRATCH.resolve())
        env = scratch / "venv"
        venv.EnvBuilder(with_pip=True).create(env)
        python = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        run(str(python), "-m", "pip", "install", "--disable-pip-version-check", str(wheel), cwd=scratch)
        version = run(str(python), "-m", "frameblink", "--version", cwd=scratch).stdout.strip()
        assert version == "0.1.0a1", version
        output = scratch / "demo-output"
        summary = json.loads(run(str(python), "-m", "frameblink", "demo", "--out", str(output), "--json", cwd=scratch).stdout)
        assert summary["firstCandidateFrame"] == 40, summary
        assert (output / "candidate-01.png").is_file()
        assert (output / "review.html").is_file()
        assert (output / "events.json").is_file()
        refused = subprocess.run([str(python), "-m", "frameblink", "demo", "--out", str(output)], cwd=scratch, text=True, capture_output=True)
        assert refused.returncode == 2 and "already exists" in refused.stderr
        print(json.dumps({"cleanWheelInstall": "passed", "version": version, "frames": summary["framesDecoded"], "topFrame": 40, "noOverwrite": True}))


if __name__ == "__main__":
    main()
