from pathlib import Path

Import("env")


DEFAULT_MAX_RECORDING_MS = 4000
MIN_MAX_RECORDING_MS = 1000
MAX_MAX_RECORDING_MS = 60000


def read_max_recording_ms() -> int:
    env_path = Path(env.subst("$PROJECT_DIR")) / ".env"
    if not env_path.exists():
        return DEFAULT_MAX_RECORDING_MS

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key != "MAX_RECORDING_MS":
            continue
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError("MAX_RECORDING_MS must be an integer") from exc
        if not MIN_MAX_RECORDING_MS <= parsed <= MAX_MAX_RECORDING_MS:
            raise ValueError(
                "MAX_RECORDING_MS must be between "
                f"{MIN_MAX_RECORDING_MS} and {MAX_MAX_RECORDING_MS}"
            )
        return parsed
    return DEFAULT_MAX_RECORDING_MS


max_recording_ms = read_max_recording_ms()
env.Append(CPPDEFINES=[f"LANTERN_MAX_RECORDING_MS={max_recording_ms}"])
print(f"Lantern max recording: {max_recording_ms} ms")
