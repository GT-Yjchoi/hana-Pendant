from PySide6.QtCore import QObject, Signal

# [기본 모드 목록] (0~33번: 이름 고정)
DEFAULT_MODES = [
    "제품측 취출", "런너측 취출", "주행 대기", "하강 대기",
    "주행도중개방", "복귀도중개방", "안전도어 회피", "안전도어 회피2",
    "낙하측 반전", "주행도중 반전", "취출대기 반전", "고정측 취출",
    "제품 형내개방", "런너 형내개방", "에젝터 연동", "언더컷 취출모드",
    "척1 사용", "척1 감지", "척2 사용", "척2 감지",
    "척3 사용", "척3 감지", "척4 사용", "척4 감지",
    "흡착1 사용", "흡착1 감지", "흡착2 사용", "흡착2 감지",
    "흡착3 사용", "흡착3 감지", "흡착4 사용", "흡착4 감지",
    "2포인트 개방", "공정감시 모드"
]

# 사용자 모드 시작 인덱스 (34번부터)
USER_MODE_START_INDEX = len(DEFAULT_MODES)

# [수정] 전체 모드 개수: 40 -> 44 (사용자 모드 10개)
TOTAL_MODE_COUNT = 44

class ModeManager(QObject):
    sig_names_changed = Signal()
    _instance = None

    def __init__(self):
        super().__init__()
        # 사용자 정의 이름 저장소 { index: "이름" }
        self.custom_names = {} 

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_name(self, idx):
        """ 인덱스에 해당하는 모드 이름 반환 """
        if idx in self.custom_names:
            return self.custom_names[idx]
        
        if 0 <= idx < len(DEFAULT_MODES):
            return DEFAULT_MODES[idx]
            
        return f"User Mode {idx - USER_MODE_START_INDEX + 1}"

    def set_name(self, idx, name):
        """ 사용자 모드 이름 설정 """
        if idx < USER_MODE_START_INDEX:
            print(f"[ModeManager] {idx}번은 기본 모드이므로 변경 불가")
            return
        
        if not name: 
            if idx in self.custom_names:
                del self.custom_names[idx]
        else:
            self.custom_names[idx] = name
            
        self.sig_names_changed.emit()

    def is_user_mode(self, idx):
        """ 해당 인덱스가 사용자 변경 가능한 모드인지 확인 """
        return idx >= USER_MODE_START_INDEX and idx < TOTAL_MODE_COUNT

    def to_dict(self):
        return {str(k): v for k, v in self.custom_names.items()}

    def load_from_dict(self, data):
        self.custom_names.clear()
        if not data: return
        for k, v in data.items():
            try:
                idx = int(k)
                self.custom_names[idx] = v
            except:
                pass
        self.sig_names_changed.emit()