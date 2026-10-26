"""Upload Lantern firmware and/or open the PlatformIO serial monitor."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent


def find_platformio() -> str:
    for command in ("platformio", "pio"):
        executable = shutil.which(command)
        if executable:
            return executable

    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        windows_path = (
            Path(user_profile)
            / ".platformio"
            / "penv"
            / "Scripts"
            / "platformio.exe"
        )
        if windows_path.exists():
            return str(windows_path)

    raise FileNotFoundError(
        "ไม่พบ PlatformIO CLI หรือ "
        "%USERPROFILE%\\.platformio\\penv\\Scripts\\platformio.exe"
    )


def run_platformio(platformio: str, arguments: list[str], environment: dict[str, str]) -> None:
    completed = subprocess.run(
        [platformio, *arguments],
        cwd=PROJECT_DIR,
        env=environment,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(f"PlatformIO ล้มเหลวด้วย exit code {completed.returncode}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload Lantern firmware and open the PlatformIO Serial Monitor."
    )
    parser.add_argument(
        "--environment",
        choices=("lcd_test", "lcd_state_test", "esp32dev", "relay_test"),
        default="lcd_test",
    )
    parser.add_argument("--port", default="COM7", help="Serial port, for example COM7")
    parser.add_argument(
        "--mode",
        choices=("both", "upload", "monitor"),
        default="both",
    )
    parser.add_argument("--baud", type=int, default=115200)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    platformio = find_platformio()
    environment = os.environ.copy()
    environment["PLATFORMIO_CORE_DIR"] = str(PROJECT_DIR.parent / ".pio-core")

    if args.mode in ("both", "upload"):
        print(f"Uploading {args.environment} to {args.port}...", flush=True)
        run_platformio(
            platformio,
            [
                "run",
                "-e",
                args.environment,
                "-t",
                "upload",
                "--upload-port",
                args.port,
            ],
            environment,
        )

    if args.mode in ("both", "monitor"):
        print(
            f"Opening Serial Monitor on {args.port} at {args.baud} baud. "
            "Press Ctrl+C to exit.",
            flush=True,
        )
        run_platformio(
            platformio,
            [
                "device",
                "monitor",
                "-e",
                args.environment,
                "-b",
                str(args.baud),
                "--port",
                args.port,
            ],
            environment,
        )


if __name__ == "__main__":
    main()
