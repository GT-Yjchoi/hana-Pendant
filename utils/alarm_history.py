"""
알람 발생 이력 관리. 알람 오버레이에 뜨는 모든 알람을 JSON 에 누적 저장하고,
TopBar 알람 텍스트 클릭 시 히스토리 팝업에 표시한다.
보존 기간: 30 일. 저장/로드 시 자동 정리.
"""
from datetime import datetime, timedelta
from utils.json_utils import load_json, save_json
from utils.paths import get_alarm_history_path

RETENTION_DAYS = 30
MAX_ENTRIES    = 5000   # 하드캡: 시스템 시계 오류 등으로 시간 prune 이 제대로 안 되어도 이 개수 넘지 않음


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_ts(ts_str):
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def _prune(entries):
    """30일 이내 항목만 남기고, 그래도 MAX_ENTRIES 초과면 오래된 것부터 버림.
    입력이 시간순(append 결과) 이라는 전제."""
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    result = []
    for e in entries:
        ts = _parse_ts(e.get("ts", ""))
        if ts is not None and ts >= cutoff:
            result.append(e)
    # 하드캡: 뒤쪽(최근)을 우선 보존
    if len(result) > MAX_ENTRIES:
        result = result[-MAX_ENTRIES:]
    return result


def load_history():
    """저장된 알람 이력 로드. 로드 시점에 자동 정리."""
    try:
        data = load_json(get_alarm_history_path()) or {}
        entries = data.get("entries", [])
        if not isinstance(entries, list):
            return []
        return _prune(entries)
    except Exception as e:
        print(f"[AlarmHistory] 로드 실패: {e}")
        return []


def save_history(entries):
    try:
        save_json(get_alarm_history_path(), {"entries": entries})
    except Exception as e:
        print(f"[AlarmHistory] 저장 실패: {e}")


def record(category, code, message):
    """
    알람 발생 기록.
    category: "AXIS" | "ESTOP" | "STEP" | "USER" | "COMM" | 기타 태그
    code    : 에러 코드 (int). E-STOP/COMM 은 0.
    message : 한 줄 설명
    """
    entries = load_history()
    entries.append({
        "ts": _now_str(),
        "category": str(category),
        "code": int(code) if isinstance(code, (int, float)) else 0,
        "message": str(message),
    })
    save_history(entries)
