import json
import os


def load_json(filepath):
    """JSON 파일을 읽어 dict로 반환. 실패 시 None 반환."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[JSONLoad] {filepath}: {e}")
        return None


def save_json(filepath, data):
    """JSON 파일을 임시파일 경유 원자적으로 저장. 성공 시 True 반환."""
    try:
        tmp_path = filepath + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)
        return True
    except Exception as e:
        print(f"[JSONSave] {filepath}: {e}")
        return False
