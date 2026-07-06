#!/bin/bash
# Pendant 초기 설치 스크립트 (ODROID-M1S, Ubuntu 24.04 server)
#
# 전제: scripts/m1s-bootstrap.sh 가 먼저 실행돼서
#       libmali g24p0 + DSI overlay + weston + ~/pyside-env (PySide6) 가 준비된 상태.
#
# 사용: bash setup.sh   (sudo 비번 한 번 물어봄)
# Idempotent — 다시 돌려도 안전.

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
HOME_DIR=$(getent passwd "$USER_NAME" | cut -d: -f6)
cd "$PROJECT_DIR"

echo "=== [1/6] 사전 점검 (m1s-bootstrap 결과) ==="
if [ ! -x "$HOME_DIR/pyside-env/bin/python" ]; then
    echo "FATAL: $HOME_DIR/pyside-env 없음."
    echo "       먼저 bash scripts/m1s-bootstrap.sh 실행."
    exit 1
fi
PYSIDE_VER=$("$HOME_DIR/pyside-env/bin/python" -c 'import PySide6; print(PySide6.__version__)' 2>/dev/null) \
    || { echo "FATAL: PySide6 import 실패"; exit 1; }
echo "  PySide6 ${PYSIDE_VER} 확인"

if ! command -v weston >/dev/null; then
    echo "FATAL: weston 없음 — m1s-bootstrap.sh 다시 실행"
    exit 1
fi
echo "  weston $(weston --version 2>&1 | head -1 | awk '{print $2}') 확인"

if ! grep -qE '^overlays=.*\bdisplay_vu8s\b' /boot/config.ini 2>/dev/null; then
    echo "WARN: /boot/config.ini 에 display_vu8s overlay 없음. DSI 안 뜰 수 있음."
fi

echo
echo "=== [2/6] 사용자 그룹 ==="
# i2c/spi 그룹은 디바이스 등장 후에만 생김 — 있을 때만 추가
for g in video render input dialout gpio netdev i2c spi; do
    if getent group "$g" >/dev/null; then
        if ! id -nG "$USER_NAME" | tr ' ' '\n' | grep -qx "$g"; then
            sudo usermod -aG "$g" "$USER_NAME"
            echo "  +$g"
        fi
    fi
done

echo
echo "=== [3/6] apt 패키지 (NetworkManager + lgpio) ==="
APT_NEED=()
dpkg -s network-manager >/dev/null 2>&1 || APT_NEED+=(network-manager)
dpkg -s python3-lgpio    >/dev/null 2>&1 || APT_NEED+=(python3-lgpio)
if [ ${#APT_NEED[@]} -gt 0 ]; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${APT_NEED[@]}" 2>&1 | tail -3
else
    echo "  이미 모두 설치됨"
fi
# python3-lgpio 는 /usr/lib/python3/dist-packages 에 들어감 — pyside-env 가 sys.path 에 추가하도록 utils/gpio_estop.py 가 처리

sudo tee /etc/polkit-1/rules.d/50-netdev-wifi.rules > /dev/null <<'RULE'
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.NetworkManager.") == 0 &&
        subject.isInGroup("netdev")) {
        return polkit.Result.YES;
    }
});
RULE
sudo systemctl restart polkit 2>/dev/null || true
echo "  polkit netdev 규칙 적용"

# NetworkManager 자체는 유지하되, 부팅 때 네트워크가 online 될 때까지 기다리는 서비스만 끈다.
# SSH/LAN/WiFi 연결은 NetworkManager.service 가 계속 처리한다.
sudo systemctl disable --now NetworkManager-wait-online.service 2>/dev/null || true
echo "  NetworkManager-wait-online 비활성화 (부팅 대기 제거)"

echo
echo "=== [4/6] 이더넷 never-default (PLC 전용 LAN 가정) ==="
if systemctl is-active --quiet NetworkManager; then
    ETH_CONN=$(nmcli -t -f NAME,TYPE connection show 2>/dev/null \
               | awk -F: '$2=="802-3-ethernet"{print $1; exit}')
    if [ -n "$ETH_CONN" ]; then
        sudo nmcli connection modify "$ETH_CONN" \
            ipv4.never-default yes ipv6.never-default yes || true
        echo "  '$ETH_CONN' → never-default"
    else
        echo "  이더넷 NM 프로파일 없음 — 랜선 연결 후 수동:"
        echo "    sudo nmcli connection modify \"<프로파일명>\" ipv4.never-default yes ipv6.never-default yes"
    fi
else
    echo "  NetworkManager inactive — 부팅 후 자동 시작될 예정"
fi

echo
echo "=== [5/6] 백라이트 밝기 조절 권한 (udev: video 그룹 쓰기) ==="
BL_RULE_SRC="$PROJECT_DIR/99-pendant-backlight.rules"
BL_RULE_DST=/etc/udev/rules.d/99-pendant-backlight.rules
if [ -f "$BL_RULE_SRC" ]; then
    sudo cp "$BL_RULE_SRC" "$BL_RULE_DST"
    sudo udevadm control --reload-rules
    # 재부팅 없이 현재 세션에도 즉시 권한 적용(다음 부팅부터는 udev 가 자동).
    # 밝기 자체는 앱이 settings.json("screen_brightness") 값으로 설정하므로
    # 여기서 강제로 max 를 쓰지 않는다(기존 하드코딩 제거).
    for bl in /sys/class/backlight/*/; do
        [ -e "$bl/brightness" ] || continue
        sudo chgrp video "$bl/brightness" 2>/dev/null || true
        sudo chmod g+w "$bl/brightness" 2>/dev/null || true
        echo "  $(basename "$bl"): $(ls -l "$bl/brightness" | awk '{print $1, $3":"$4}')"
    done
else
    echo "  $BL_RULE_SRC 없음 — 건너뜀"
fi

echo
echo "=== [6/6] systemd 서비스 등록 ==="
SERVICE_SRC="$PROJECT_DIR/pendant.service"
SERVICE_DST=/etc/systemd/system/pendant.service
if [ -f "$SERVICE_SRC" ]; then
    sudo cp "$SERVICE_SRC" "$SERVICE_DST"
    sudo systemctl daemon-reload
    sudo systemctl enable pendant.service
    echo "  pendant.service 등록 + enable"
else
    echo "FATAL: $SERVICE_SRC 없음"; exit 1
fi

echo
echo "=== 완료 ==="
echo
echo "수동 시작 (지금):"
echo "  sudo systemctl start pendant"
echo
echo "부팅 자동 시작:"
echo "  이미 enable 됨. sudo reboot 하면 tty1 점유하고 풀스크린으로 떠야 함."
echo
echo "로그:"
echo "  journalctl -u pendant -f"
echo "  tail -f /tmp/pendant-weston.log"
echo
echo "디버그 (서비스 정지하고 콘솔로 돌아가기):"
echo "  sudo systemctl stop pendant"
echo "  sudo systemctl start getty@tty1"
