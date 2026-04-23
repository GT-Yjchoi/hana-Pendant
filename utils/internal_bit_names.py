"""
내부비트 M00~M31 사용자 정의 이름 관리.
settings.json 의 "internal_bit_names": {"M00": "감지비트", ...} 에 저장.
"""
from utils.json_utils import load_json, save_json
from utils.paths import get_settings_path


def load_all():
    """{"M00": "감지비트", ...} 형식으로 반환. 없으면 빈 dict."""
    try:
        data = load_json(get_settings_path()) or {}
        names = data.get("internal_bit_names", {})
        return {str(k): str(v) for k, v in names.items() if isinstance(v, str) and v.strip()}
    except Exception as e:
        print(f"[InternalBitNames] 로드 실패: {e}")
        return {}


def get_name(key):
    """key='M00' 에 대한 사용자 정의 이름. 없으면 빈 문자열."""
    return load_all().get(key, "")


def set_name(key, name):
    """이름 저장. name 이 빈 문자열/None 이면 해당 키 삭제."""
    try:
        path = get_settings_path()
        data = load_json(path) or {}
        names = dict(data.get("internal_bit_names", {}))
        if name and name.strip():
            names[key] = name.strip()
        else:
            names.pop(key, None)
        data["internal_bit_names"] = names
        save_json(path, data)
    except Exception as e:
        print(f"[InternalBitNames] 저장 실패: {e}")


def format_card(bit_idx):
    """bit_idx(0~31) → 카드 표시 문자열.
    이름 있으면 "M00\\n감지비트", 없으면 "M00" 반환.
    """
    key = f"M{bit_idx:02d}"
    nm = get_name(key)
    return f"{key}\n{nm}" if nm else key


def parse_key(card_text):
    """카드 문자열에서 M키 추출 ('M00\\n감지비트' → 'M00')."""
    if not card_text:
        return ""
    return card_text.split("\n", 1)[0].strip()
