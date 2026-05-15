#!/bin/bash
# Pendant 런처 (M1S, weston kiosk)
# pendant.service 가 호출 (직접 수동 실행도 가능 — tty 에서)
#
# 흐름:
#   1) weston 백그라운드 시작 (drm-backend + kiosk-shell, 자기 소켓 wayland-pendant)
#   2) main.py 를 그 weston 위에 Qt wayland 클라이언트로 실행
#   3) main.py 종료/오류 → weston 종료 → 서비스도 종료 (systemd 가 restart 처리)

set -u

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PY="${HOME}/pyside-env/bin/python"
WAYLAND_SOCK="wayland-pendant"
WESTON_LOG="/tmp/pendant-weston.log"
APP_LOG="/tmp/pendant-app.log"

# pendant.service 에 PAMName=login 가 있어서 stdout/stderr 가 tty1 로 가버림.
# 직접 파일로 redirect 해서 SSH 에서 tail -f 가능하게.
exec > >(tee -a "$APP_LOG") 2>&1
echo "===== launch.sh start $(date '+%F %T') ====="

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
mkdir -p "$XDG_RUNTIME_DIR" 2>/dev/null || true
chmod 700 "$XDG_RUNTIME_DIR" 2>/dev/null || true

cleanup() {
    if [ -n "${WESTON_PID:-}" ] && kill -0 "$WESTON_PID" 2>/dev/null; then
        kill "$WESTON_PID" 2>/dev/null
        wait "$WESTON_PID" 2>/dev/null
    fi
}
trap cleanup EXIT INT TERM

# -- weston 시작 -------------------------------------------------------------
: > "$WESTON_LOG"
weston \
    --shell=kiosk-shell.so \
    --backend=drm-backend.so \
    --socket="$WAYLAND_SOCK" \
    --idle-time=0 \
    --config="$PROJECT_DIR/weston.ini" \
    --log="$WESTON_LOG" \
    >>"$WESTON_LOG" 2>&1 &
WESTON_PID=$!

# 소켓 생성 대기 (최대 5초)
for i in 1 2 3 4 5 6 7 8 9 10; do
    [ -S "$XDG_RUNTIME_DIR/$WAYLAND_SOCK" ] && break
    if ! kill -0 "$WESTON_PID" 2>/dev/null; then
        echo "FATAL: weston 시작 직후 죽음 — $WESTON_LOG 참고" >&2
        tail -30 "$WESTON_LOG" >&2
        exit 1
    fi
    sleep 0.5
done

# -- main.py 실행 (Qt6 wayland + Mali EGL 1.5) -------------------------------
cd "$PROJECT_DIR"
exec env \
    WAYLAND_DISPLAY="$WAYLAND_SOCK" \
    QT_QPA_PLATFORM=wayland \
    QT_WAYLAND_CLIENT_BUFFER_INTEGRATION=wayland-egl \
    QT_AUTO_SCREEN_SCALE_FACTOR=0 \
    QT_SCALE_FACTOR=1 \
    PYTHONUNBUFFERED=1 \
    "$VENV_PY" main.py
