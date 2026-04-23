"""
축 스트로크 한계 조회 유틸.
settings.json 의 "axis_strokes" 키에서 8축 한계값(mm)을 로드한다.
page_position / sequence_editor 등에서 좌표 입력 범위 클램프에 사용.
"""
from utils.json_utils import load_json
from utils.paths import get_settings_path

DEFAULT_STROKE_MM = 1000.0  # settings.json 에 값이 없으면 사용할 기본값 (보수적으로 1m)


def get_axis_strokes():
    """
    settings.json 에서 8축 스트로크 한계값(mm) 리스트 반환.
    값이 없거나 오류 시 전 축 DEFAULT_STROKE_MM 로 대체.
    """
    try:
        data = load_json(get_settings_path()) or {}
        strokes = data.get("axis_strokes")
        if isinstance(strokes, list) and len(strokes) == 8:
            return [float(s) if s and s > 0 else DEFAULT_STROKE_MM for s in strokes]
    except Exception as e:
        print(f"[axis_limits] 스트로크 로드 실패: {e}")
    return [DEFAULT_STROKE_MM] * 8


def clamp_position(axis_idx, value_mm):
    """
    축 axis_idx (0~7) 에 대해 좌표값을 0 ~ 스트로크 한계 범위로 클램프.
    음수는 0 으로, 한계 초과는 한계값으로 보정.
    """
    strokes = get_axis_strokes()
    if not (0 <= axis_idx < 8):
        return value_mm
    lo, hi = 0.0, strokes[axis_idx]
    return max(lo, min(hi, float(value_mm)))
