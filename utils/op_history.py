"""
사용자 조작 이력 관리.
운전 버튼, 밸브 조작, 수치 변경, 레시피 저장/로드 등 사용자의 모든 조작을 기록.
보존 기간: 7 일. 저장/로드 시 자동 정리.
"""
import os
from datetime import datetime, timedelta
from utils.json_utils import load_json, save_json
from utils.paths import get_base_dir

RETENTION_DAYS = 7
MAX_ENTRIES    = 10000   # 하드캡: 조작은 알람보다 훨씬 자주 발생하므로 넉넉히


def get_op_history_path():
    return os.path.join(get_base_dir(), "op_history.json")


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_ts(ts_str):
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def _prune(entries):
    """7일 이내 항목만 남기고, 그래도 MAX_ENTRIES 초과면 오래된 것부터 버림."""
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    result = [e for e in entries if (ts := _parse_ts(e.get("ts", ""))) and ts >= cutoff]
    if len(result) > MAX_ENTRIES:
        result = result[-MAX_ENTRIES:]
    return result


def load_history():
    try:
        data = load_json(get_op_history_path()) or {}
        entries = data.get("entries", [])
        if not isinstance(entries, list):
            return []
        return _prune(entries)
    except Exception as e:
        print(f"[OpHistory] 로드 실패: {e}")
        return []


def save_history(entries):
    try:
        save_json(get_op_history_path(), {"entries": entries})
    except Exception as e:
        print(f"[OpHistory] 저장 실패: {e}")


def record(category, message):
    """
    조작 기록.
    category: "RUN" | "VALVE" | "POS" | "SPEED" | "TIMER" | "MODE" | "RECIPE" | "PARAM" | "ALARM_RESET" | "JOG" | 기타
    message : 한 줄 설명 (예: "자동 운전 시작", "척1 ON", "X축 기억위치 100.000 → 150.000")
    """
    entries = load_history()
    entries.append({
        "ts": _now_str(),
        "category": str(category),
        "message": str(message),
    })
    save_history(entries)
