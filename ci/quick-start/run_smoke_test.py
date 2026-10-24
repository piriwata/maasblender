"""CI smoke test; run from examples/quick-start on a disposable hosted runner."""

import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
SERVICES = {
    "broker": ("src/simulation_broker", 3000),
    "scheduled": ("src/base_simulators/scheduled", 3001),
    "walking": ("src/base_simulators/walking", 3002),
    "user_model": ("src/user_model/simple", 3003),
    "scenario_commuter": ("src/scenario/commuter", 3004),
    "planner": ("src/planner/opentripplanner", 3010),
}
OTP_VERSION = "2.9.0"  # Keep in sync with the planner Dockerfile.


def main():
    work = Path.cwd()
    settings_path = work / "broker_setup.json"
    original_settings = settings_path.read_text(encoding="utf-8")
    settings = original_settings
    for name, (_, port) in SERVICES.items():
        settings = settings.replace(f"http://{name}", f"http://localhost:{port}")

    jar = work / "otp-shaded.jar"
    url = (
        "https://repo.maven.apache.org/maven2/org/opentripplanner/otp-shaded/"
        f"{OTP_VERSION}/otp-shaded-{OTP_VERSION}.jar"
    )
    with httpx.stream("GET", url, timeout=180, follow_redirects=True) as response:
        response.raise_for_status()
        with jar.open("wb") as file:
            for chunk in response.iter_bytes():
                file.write(chunk)

    volume = work / "otp-volume"
    volume.mkdir(exist_ok=True)
    env = {
        **os.environ,
        "OPENTRIPPLANNER_EXECUTABLE": str(jar),
        "OPENTRIPPLANNER_VOLUME_DIR": str(volume),
        "OPENTRIPPLANNER_STARTUP_TIMEOUT": "600",
    }
    processes = []
    for project, port in SERVICES.values():
        subprocess.run(
            ["uv", "sync", "--frozen", "--project", str(ROOT / project)], check=True
        )
        processes.append(
            subprocess.Popen(
                [
                    "uv",
                    "run",
                    "--no-sync",
                    "python",
                    "-m",
                    "uvicorn",
                    "controller:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--loop",
                    "asyncio",
                ],
                cwd=ROOT / project,
                env=env,
            )
        )

    deadline = time.monotonic() + 120
    with httpx.Client(timeout=2) as client:
        for _, port in SERVICES.values():
            while True:
                if any(process.poll() is not None for process in processes):
                    raise RuntimeError("A service exited during startup")
                if time.monotonic() > deadline:
                    raise TimeoutError(f"Service on port {port} did not start")
                try:
                    client.get(
                        f"http://localhost:{port}/openapi.json"
                    ).raise_for_status()
                    break
                except httpx.HTTPError:
                    time.sleep(1)

    settings_path.write_text(settings, encoding="utf-8")
    try:
        (work / "events.txt").unlink(missing_ok=True)
        subprocess.run(
            [sys.executable, "execute_simulation.py"],
            check=True,
            timeout=1200,
        )
        if (work / "events.txt").stat().st_size == 0:
            raise RuntimeError("Quick Start produced no events")
    finally:
        settings_path.write_text(original_settings, encoding="utf-8")
    # GitHub Actions cleans up the service processes when the job ends.


if __name__ == "__main__":
    main()
