from PySide6.QtCore import Qt, Signal
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

class AlarmOverlay(QWidget):
    sig_reset_pressed = Signal()
    sig_reset_released = Signal()

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
        self.btn_close.setFixedSize(32, 32)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #FF4646;
                font-size: 18px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { color: white; }
            QPushButton:pressed { color: #aaa; }
        """)
        self.btn_close.clicked.connect(self.hide)
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

    def show_error(self, axis_list, error_codes=None):
        """축 알람 메시지를 설정하고 화면에 띄움"""
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