import json
import os
from PySide6.QtCore import Qt, Signal
from utils.paths import get_settings_path
from utils.json_utils import load_json, save_json
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect

# ============================================================
# 축 에러 코드 설명 테이블
# 에러코드와 설명을 여기에 추가하세요.
# 키: 에러코드 (int, 16진수로 입력 가능)
# 값: 설명 문자열 (str)
# ============================================================
AXIS_ERROR_DESCRIPTIONS = {
    0x3001: "과부하 발생",

    # 여기에 에러코드와 설명을 계속 추가하세요.
    # 예시: 0x0050: "인코더 이상",
}

# ============================================================
# 시퀀스 알람 테이블
# 입력대기(IN) 스텝 타임아웃 시 띄울 알람 메시지
# 키: 알람 번호 (int, 1부터 시작)
# 값: 알람 메시지 (str)
# ============================================================
SEQUENCE_ALARMS = {}

_SETTINGS_PATH = get_settings_path()


def load_sequence_alarms(settings_path=None):
    """settings.json의 sequence_alarms를 읽어 SEQUENCE_ALARMS 딕셔너리를 갱신합니다."""
    path = settings_path or _SETTINGS_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        saved = data.get("sequence_alarms")
        if saved:
            SEQUENCE_ALARMS.clear()
            SEQUENCE_ALARMS.update({int(k): v for k, v in saved.items()})
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass  # 저장된 데이터 없으면 기본값 유지


def save_sequence_alarms(settings_path=None):
    """SEQUENCE_ALARMS를 settings.json에 저장합니다."""
    path = settings_path or _SETTINGS_PATH
    try:
        settings = load_json(path) or {}
        settings["sequence_alarms"] = {str(k): v for k, v in sorted(SEQUENCE_ALARMS.items())}
        save_json(path, settings)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[알람] 저장 실패: {e}")


# 앱 시작 시 settings.json에서 자동 로드
load_sequence_alarms()

class AlarmOverlay(QWidget):
    sig_reset_pressed = Signal()
    sig_reset_released = Signal()
    sig_dismissed = Signal()  # X버튼으로 닫을 때

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. 배경 설정 (반투명 검정)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 200);")
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # 터치 이벤트가 뒤로 넘어가지 않도록 막음 (알람 중 조작 금지)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.setCursor(Qt.ArrowCursor)

        # 2. 메인 레이아웃 (중앙 정렬)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # 3. 알람 박스 디자인
        self.box = QFrame()
        self.box.setFixedSize(500, 320)
        self.box.setStyleSheet("""
            QFrame {
                background-color: #2D1A1A; 
                border: 4px solid #FF4646; 
                border-radius: 20px;
            }
            QLabel { background: transparent; border: none; }
        """)
        
        # 그림자 효과 (입체감)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 10)
        self.box.setGraphicsEffect(shadow)

        # 박스 내부 레이아웃
        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(30, 14, 30, 30)
        box_layout.setSpacing(20)

        # [닫기 버튼 (X)] - 오른쪽 상단
        close_row = QHBoxLayout()
        close_row.setContentsMargins(0, 0, 0, 0)
        close_row.addStretch()
        self.btn_close = QPushButton("X")
        self.btn_close.setFixedSize(48, 48)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #FF4646;
                font-size: 27px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { color: white; }
            QPushButton:pressed { color: #aaa; }
        """)
        self.btn_close.clicked.connect(self._on_close_clicked)
        close_row.addWidget(self.btn_close)
        box_layout.addLayout(close_row)

        # [아이콘/제목]
        self.lbl_title = QLabel("[!] SYSTEM ALARM [!]")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("color: #FF4646; font-size: 32px; font-weight: 900;")
        box_layout.addWidget(self.lbl_title)

        # [에러 코드 및 메시지]
        self.lbl_msg = QLabel("E-001: 비상정지가 눌렸습니다.")
        self.lbl_msg.setAlignment(Qt.AlignCenter)
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        box_layout.addWidget(self.lbl_msg)

        # [리셋 버튼]
        self.btn_reset = QPushButton("ALARM RESET")
        self.btn_reset.setFixedSize(250, 60)
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #C0392B;
                color: white;
                font-size: 22px;
                font-weight: bold;
                border: 2px solid #E74C3C;
                border-radius: 10px;
            }
            QPushButton:pressed {
                background-color: #E74C3C;
            }
        """)
        self.btn_reset.pressed.connect(self.sig_reset_pressed.emit)
        self.btn_reset.released.connect(self.sig_reset_released.emit)

        # 버튼 중앙 정렬을 위한 레이아웃
        btn_layout = QVBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.addWidget(self.btn_reset)
        box_layout.addLayout(btn_layout)

        layout.addWidget(self.box)

        # 초기엔 숨김
        self.hide()

    def _on_close_clicked(self):
        self.hide()
        self.sig_dismissed.emit()

    def _set_alarm_style(self):
        """기본 알람 스타일(빨강)으로 복구"""
        self.lbl_title.setText("[!] SYSTEM ALARM [!]")
        self.lbl_title.setStyleSheet("color: #FF4646; font-size: 32px; font-weight: 900;")
        self.box.setStyleSheet("""
            QFrame {
                background-color: #2D1A1A;
                border: 4px solid #FF4646;
                border-radius: 20px;
            }
            QLabel { background: transparent; border: none; }
        """)
        self.btn_reset.show()

    def show_comm_error(self):
        """PLC 통신 에러 팝업"""
        self.lbl_title.setText("[!] COMM ERROR [!]")
        self.lbl_title.setStyleSheet("color: #F39C12; font-size: 32px; font-weight: 900;")
        self.box.setStyleSheet("""
            QFrame {
                background-color: #1A1500;
                border: 4px solid #F39C12;
                border-radius: 20px;
            }
            QLabel { background: transparent; border: none; }
        """)
        self.lbl_msg.setText("PLC와의 통신이 끊어졌습니다.\n자동으로 재연결을 시도합니다.")
        self.btn_reset.hide()
        self._comm_error = True
        self.show()
        self.raise_()

    def hide_comm_error(self):
        """통신 복구 시 COMM ERROR 팝업 닫기"""
        if getattr(self, '_comm_error', False):
            self._comm_error = False
            self._set_alarm_style()
            self.hide()

    def show_sequence_alarm(self, alarm_no):
        """시퀀스 알람 (IN 스텝 타임아웃 등)을 화면에 띄움"""
        self._set_alarm_style()
        msg = SEQUENCE_ALARMS.get(alarm_no, f"시퀀스 알람 #{alarm_no}")
        self.lbl_msg.setText(f"A-{alarm_no:03d}: {msg}")
        self.show()
        self.raise_()

    def show_error(self, axis_list, error_codes=None):
        """축 알람 메시지를 설정하고 화면에 띄움"""
        self._set_alarm_style()
        axis_names = {1: "X축", 2: "Y축", 3: "Z축", 4: "Y2축", 5: "Z2축", 6: "θ축", 7: "R1축", 8: "R2축", 9: "비상정지"}
        lines = []
        for a in axis_list:
            name = axis_names.get(a, f"{a}축")
            if error_codes and len(error_codes) >= a and error_codes[a - 1] > 0:
                code = error_codes[a - 1]
                desc = AXIS_ERROR_DESCRIPTIONS.get(code, "")
                if desc:
                    lines.append(f"{name}: E-{code:04X} ({desc})")
                else:
                    lines.append(f"{name}: E-{code:04X}")
            else:
                lines.append(name)
        self.lbl_msg.setText("축 알람 발생\n" + "\n".join(lines))
        self.show()
        self.raise_()