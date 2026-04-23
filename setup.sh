#!/bin/bash
#
# Pendant 초기 설치 스크립트
# 새 라즈베리파이(Lite, Trixie+)에서 git clone 후 한 번 실행.
#
#   ./setup.sh
#
# 여러 번 실행해도 안전 (idempotent).
# 필요한 경우 sudo 비밀번호를 물어봅니다.

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
cd "$PROJECT_DIR"

echo "=== [1/6] apt 시스템 패키지 ==="
sudo apt-get update
sudo apt-get install -y \
    python3 python3-venv \
    python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtwidgets \
    python3-pyside6.qtqml python3-pyside6.qtquick \
    libegl1 libgl1 libfontconfig1 libdbus-1-3 libxkbcommon0 \
    network-manager
# 위 pyside6 의존성으로 libQt6EglFsKmsGbmSupport 등 KMS/GBM 라이브러리 자동 설치됨.

echo ""
echo "=== [2/6] Python venv (--system-site-packages) ==="
# 시스템 apt PySide6 를 공유하는 venv. pip 패키지 설치는 하지 않음.
if [ -d "$PROJECT_DIR/.venv" ] && \
   ! grep -q '^include-system-site-packages = true' "$PROJECT_DIR/.venv/pyvenv.cfg" 2>/dev/null; then
    echo "  → 기존 .venv 가 system-site-packages 모드가 아님. 재생성합니다."
    rm -rf "$PROJECT_DIR/.venv"
fi
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    python3 -m venv --system-site-packages "$PROJECT_DIR/.venv"
fi

echo ""
echo "=== [3/6] 부트 커맨드라인 (콘솔/로고 정리 + DSI 회전) ==="
CMDLINE=/boot/firmware/cmdline.txt
if [ -f "$CMDLINE" ]; then
    # vt.global_cursor_default=0  : 콘솔 커서 깜빡임 끔
    # consoleblank=0              : 콘솔 블랭크(꺼짐) 끔
    # fbcon=map:2                 : fbcon 을 존재하지 않는 FB 로 매핑 → 콘솔 텍스트 비표시
    # logo.nologo                 : 부팅 로고 제거
    # video=DSI-1:800x1280e,rotate=270 : Waveshare 10.1" DSI 패널 270° 회전
    FLAGS="vt.global_cursor_default=0 consoleblank=0 fbcon=map:2 logo.nologo video=DSI-1:800x1280e,rotate=270"
    CURRENT=$(cat "$CMDLINE")
    NEW="$CURRENT"
    for flag in $FLAGS; do
        key="${flag%%=*}"
        if echo "$NEW" | grep -qE "(^| )${key}="; then
            NEW=$(echo "$NEW" | sed -E "s|(^| )${key}=[^ ]*|\1${flag}|")
        else
            NEW="$NEW $flag"
        fi
    done
    NEW=$(echo "$NEW" | tr -s ' ' | sed 's/^ //; s/ $//')
    if [ "$NEW" != "$CURRENT" ]; then
        sudo cp "$CMDLINE" "${CMDLINE}.bak.$(date +%Y%m%d%H%M%S)"
        echo "$NEW" | sudo tee "$CMDLINE" > /dev/null
        echo "  → cmdline.txt 업데이트. 재부팅 후 반영됩니다."
    else
        echo "  → 이미 적용됨. 건너뜀."
    fi
else
    echo "  → $CMDLINE 없음. 이 단계 건너뜀 (비-라즈파 환경?)."
fi

echo ""
echo "=== [4/6] WiFi 관리 권한(polkit) + netdev 그룹 ==="
sudo tee /etc/polkit-1/rules.d/50-netdev-wifi.rules > /dev/null <<'RULE'
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.NetworkManager.") == 0 &&
        subject.isInGroup("netdev")) {
        return polkit.Result.YES;
    }
});
RULE
sudo systemctl restart polkit
if ! groups "$USER_NAME" | grep -qw netdev; then
    sudo usermod -aG netdev "$USER_NAME"
    echo "  → $USER_NAME 를 netdev 그룹에 추가. 재로그인 필요."
fi

echo ""
echo "=== [5/6] 유선 이더넷 never-default ==="
# LAN 전용(인터넷 없는 PLC 네트워크)인 경우 유선이 디폴트 라우트로 승격되는 것을 차단.
ETH_CONN=$(nmcli -t -f NAME,TYPE connection show 2>/dev/null | awk -F: '$2=="802-3-ethernet"{print $1; exit}')
if [ -n "$ETH_CONN" ]; then
    sudo nmcli connection modify "$ETH_CONN" ipv4.never-default yes ipv6.never-default yes || true
    echo "  → '$ETH_CONN' 프로파일에 never-default 적용."
else
    echo "  → 이더넷 프로파일 없음. 랜선 연결 후 수동 적용 필요:"
    echo "    sudo nmcli connection modify \"<프로파일명>\" ipv4.never-default yes ipv6.never-default yes"
fi

echo ""
echo "=== [6/6] systemd 서비스 등록 ==="
SERVICE_SRC="$PROJECT_DIR/pendant.service"
SERVICE_DST=/etc/systemd/system/pendant.service
if [ -f "$SERVICE_SRC" ]; then
    sudo cp "$SERVICE_SRC" "$SERVICE_DST"
    sudo systemctl daemon-reload
    sudo systemctl enable pendant.service
    echo "  → pendant.service 등록·enable. 재부팅 시 자동 실행."
    echo ""
    echo "  ⚠ 터치 장치 경로 확인 필요:"
    echo "    pendant.service 의 QT_QPA_EVDEV_TOUCHSCREEN_PARAMETERS 에 /dev/input/event1 이 하드코딩됨."
    echo "    다른 번호라면 아래로 확인 후 서비스 파일 수정:"
    echo "      for d in /dev/input/event*; do udevadm info --query=property --name=\"\$d\" | grep -q TOUCHSCREEN && echo \"\$d\"; done"
else
    echo "  → $SERVICE_SRC 없음. 건너뜀."
fi

echo ""
echo "=== 완료 ==="
echo ""
echo "재부팅으로 자동 실행:"
echo "  sudo reboot"
echo ""
echo "수동 제어:"
echo "  sudo systemctl start pendant.service"
echo "  sudo systemctl stop pendant.service"
echo "  journalctl -u pendant -f"
