from PySide6.QtCore import QObject, Signal

# 기본값
DEFAULT_INPUTS = [
    "비상정지",       # X00
    "안전문",         # X01
    "사출기 전자동",  # X02
    "형개완료",       # X03
    "형폐완료",       # X04
    "에젝터 전진완료",# X05
    "에젝터 후퇴완료",# X06
    "예비1",          # X07
] + [f"X{i:02X}" for i in range(8, 32)]

DEFAULT_OUTPUTS = [
    "형개허가",       # Y00
    "형폐허가",       # Y01
    "에젝터 허가",    # Y02
    "싸이클스타트",   # Y03
    "컨베어출력1",    # Y04
    "컨베어출력2",    # Y05
    "예비1",          # Y06
    "예비2",          # Y07
] + [f"Y{i:02X}" for i in range(8, 32)]

class IOManager(QObject):
    # 이름이 바뀌면 발생하는 신호
    sig_names_changed = Signal()

    _instance = None

    def __init__(self):
        super().__init__()
        # 초기값은 기본값으로 설정
        self.inputs = list(DEFAULT_INPUTS)
        self.outputs = list(DEFAULT_OUTPUTS)

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_from_dict(self, data):
        """ 레시피 파일에서 읽은 딕셔너리를 적용 """
        saved_in = data.get("inputs", [])
        saved_out = data.get("outputs", [])
        
        # 개수 맞춰서 업데이트 (기본 32개 유지)
        for i in range(min(len(saved_in), 32)):
            self.inputs[i] = saved_in[i]
        
        for i in range(min(len(saved_out), 32)):
            self.outputs[i] = saved_out[i]
            
        # UI 업데이트 신호 발송
        self.sig_names_changed.emit()

    def to_dict(self):
        """ 현재 설정된 이름을 딕셔너리로 반환 (저장용) """
        return {
            "inputs": self.inputs,
            "outputs": self.outputs
        }

    def update_names(self, new_inputs, new_outputs):
        """ 설정 화면에서 수정했을 때 메모리 상의 데이터 갱신 """
        self.inputs = new_inputs
        self.outputs = new_outputs
        self.sig_names_changed.emit()

    def get_input_name(self, idx):
        if 0 <= idx < len(self.inputs):
            return self.inputs[idx]
        return f"X{idx:02X}"

    def get_output_name(self, idx):
        if 0 <= idx < len(self.outputs):
            return self.outputs[idx]
        return f"Y{idx:02X}"