#!/bin/bash
#
# Pendant 초기 설치 스크립트
# 새 라즈베리파이에서 git clone 후 한 번 실행.
#
#   ./setup.sh
#
# 필요한 경우 sudo 비밀번호를 물어봅니다.

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== [1/5] 시스템 라이브러리 설치 ==="
sudo apt-get update
sudo apt-get install -y \
    python3 python3-venv python3-pip \
    libxkbcommon0 libxkbcommon-x11-0 \
    libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-sync1 \
    libxcb-xfixes0 libxcb-xkb1 \
    libegl1 libgl1 libfontconfig1 libdbus-1-3 \
    network-manager

echo ""
echo "=== [2/5] Python 가상환경 & 패키지 ==="
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    python3 -m venv "$PROJECT_DIR/.venv"
fi
"$PROJECT_DIR/.venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/.venv/bin/pip" install PySide6 pyinstaller

echo ""
echo "=== [3/5] 부트 커맨드라인 플래그 (tty 커서/콘솔 오버레이 제거) ==="
CMDLINE=/boot/firmware/cmdline.txt
if [ -f "$CMDLINE" ]; then
    # linuxfb 앱 뒤로 tty1 커서·콘솔 텍스트가 비치지 않도록 플래그 추가
    #   vt.global_cursor_default=0  : 콘솔 커서 깜빡임 끔
    #   consoleblank=0              : 콘솔 블랭크(화면 꺼짐) 끔
    #   fbcon=map:2                 : fbcon 을 존재하지 않는 FB 로 매핑 → FB0 점유 해제
    #   logo.nologo                 : 부팅 로고 제거
    FLAGS="vt.global_cursor_default=0 consoleblank=0 fbcon=map:2 logo.nologo"
    CURRENT=$(cat "$CMDLINE")
    NEW="$CURRENT"
    for flag in $FLAGS; do
        key="${flag%%=*}"
        # 같은 key 가 이미 있으면 교체, 없으면 뒤에 추가
        if echo "$NEW" | grep -qE "(^| )${key}="; then
            NEW=$(echo "$NEW" | sed -E "s|(^| )${key}=[^ ]*|\1${flag}|")
        else
            NEW="$NEW $flag"
        fi
    done
    # 선행/중간 공백 정리
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
echo "=== [4/5] WiFi 관리 권한(polkit) 설정 ==="
sudo tee /etc/polkit-1/rules.d/50-netdev-wifi.rules > /dev/null <<'RULE'
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.NetworkManager.") == 0 &&
        subject.isInGroup("netdev")) {
        return polkit.Result.YES;
    }
});
RULE
sudo systemctl restart polkit

# 사용자가 netdev 그룹에 없으면 추가
if ! groups | grep -qw netdev; then
    sudo usermod -aG netdev "$USER"
    echo "  → $USER 를 netdev 그룹에 추가. 재로그인 필요합니다."
fi

echo ""
echo "=== [5/5] 완료 ==="
echo ""
echo "실행:"
echo "  cd $PROJECT_DIR"
echo "  QT_QPA_PLATFORM=linuxfb .venv/bin/python main.py"
