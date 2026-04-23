"""
경로 유틸리티 - 개발 환경과 PyInstaller 빌드 환경 모두에서 올바른 경로를 반환합니다.

- 빌드된 실행파일: dist/main/ 폴더 기준
- 개발 환경(python main.py): 프로젝트 루트 기준
"""
import sys
import os


def get_base_dir() -> str:
    """실행파일(또는 프로젝트 루트)이 위치한 디렉토리를 반환합니다."""
    if getattr(sys, 'frozen', False):
        # PyInstaller 빌드: sys.executable = dist/main/main
        return os.path.dirname(sys.executable)
    else:
        # 개발 환경: 이 파일은 utils/ 에 있으므로 한 단계 위가 프로젝트 루트
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_settings_path() -> str:
    return os.path.join(get_base_dir(), "settings.json")


def get_recipes_dir() -> str:
    return os.path.join(get_base_dir(), "recipes")


def get_alarm_history_path() -> str:
    return os.path.join(get_base_dir(), "alarm_history.json")
