#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./upload-monitor.sh [environment] [port] [mode] [baud]

Examples:
  ./upload-monitor.sh lcd_test COM7 both
  ./upload-monitor.sh esp32dev COM7 upload
  ./upload-monitor.sh lcd_test COM7 monitor

Arguments:
  environment  PlatformIO environment: lcd_test, lcd_state_test, esp32dev, or relay_test
  port         Serial port, for example COM7
  mode         both, upload, or monitor (default: both)
  baud         Serial baud rate (default: 115200)
EOF
}

ENVIRONMENT="${1:-lcd_test}"
PORT="${2:-COM7}"
MODE="${3:-both}"
BAUD="${4:-115200}"

case "$ENVIRONMENT" in
  lcd_test|lcd_state_test|esp32dev|relay_test) ;;
  -h|--help) usage; exit 0 ;;
  *) echo "Unsupported environment: $ENVIRONMENT" >&2; usage >&2; exit 2 ;;
esac

case "$MODE" in
  both|upload|monitor) ;;
  *) echo "Unsupported mode: $MODE" >&2; usage >&2; exit 2 ;;
esac

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if command -v platformio >/dev/null 2>&1; then
  PLATFORMIO="$(command -v platformio)"
elif command -v pio >/dev/null 2>&1; then
  PLATFORMIO="$(command -v pio)"
elif command -v cygpath >/dev/null 2>&1 && [[ -n "${USERPROFILE:-}" ]]; then
  PLATFORMIO="$(cygpath -u "$USERPROFILE")/.platformio/penv/Scripts/platformio.exe"
else
  echo "PlatformIO CLI not found. Install PlatformIO or add it to PATH." >&2
  exit 1
fi

if command -v cygpath >/dev/null 2>&1; then
  export PLATFORMIO_CORE_DIR="$(cygpath -w "$PROJECT_DIR/../.pio-core")"
else
  export PLATFORMIO_CORE_DIR="$PROJECT_DIR/../.pio-core"
fi

if [[ "$MODE" == "both" || "$MODE" == "upload" ]]; then
  echo "Uploading $ENVIRONMENT to $PORT..."
  "$PLATFORMIO" run -e "$ENVIRONMENT" -t upload --upload-port "$PORT"
fi

if [[ "$MODE" == "both" || "$MODE" == "monitor" ]]; then
  echo "Opening Serial Monitor on $PORT at ${BAUD} baud. Press Ctrl+C to exit."
  "$PLATFORMIO" device monitor -e "$ENVIRONMENT" -b "$BAUD" --port "$PORT"
fi
