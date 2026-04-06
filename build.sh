#!/bin/bash
set -e

DIST_DIR="dist/main"
BACKUP_DIR="/tmp/pendant_build_backup"

# 기존 실행 데이터 백업 (빌드 시 dist/main/ 폴더가 초기화되므로)
echo "[1/3] 기존 데이터 백업..."
rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

if [ -f "$DIST_DIR/settings.json" ]; then
    cp "$DIST_DIR/settings.json" "$BACKUP_DIR/settings.json"
    echo "  settings.json 백업 완료"
elif [ -f "settings.json" ]; then
    cp "settings.json" "$BACKUP_DIR/settings.json"
    echo "  settings.json (프로젝트 루트) 백업 완료"
fi

if [ -d "$DIST_DIR/recipes" ]; then
    cp -r "$DIST_DIR/recipes" "$BACKUP_DIR/recipes"
    echo "  recipes/ 백업 완료"
elif [ -d "recipes" ]; then
    cp -r "recipes" "$BACKUP_DIR/recipes"
    echo "  recipes/ (프로젝트 루트) 백업 완료"
fi

# 빌드
echo "[2/3] PyInstaller 빌드 시작..."
source .venv/bin/activate
pyinstaller --clean -y main.spec

# 데이터 복원
echo "[3/3] 데이터 복원..."
if [ -f "$BACKUP_DIR/settings.json" ]; then
    cp "$BACKUP_DIR/settings.json" "$DIST_DIR/settings.json"
    echo "  settings.json 복원 완료"
fi

if [ -d "$BACKUP_DIR/recipes" ]; then
    cp -r "$BACKUP_DIR/recipes" "$DIST_DIR/recipes"
    echo "  recipes/ 복원 완료"
fi

rm -rf "$BACKUP_DIR"

echo ""
echo "빌드 완료 → $DIST_DIR/main"
