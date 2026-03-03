from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLineEdit, QWidget, QGridLayout
)

class TouchNumberKeyboard(QDialog):
    def __init__(self, initial_value="", precision=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("숫자 입력")
        
        # 모달 설정 (뒷배경 차단)
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal) 
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        
        self.resize(350, 450)
        self.precision = precision
        
        # [NEW] 첫 입력 감지 플래그 (True면 첫 입력 시 기존 값 클리어)
        self.first_input = True

        self.setStyleSheet("""
            QDialog { background-color: #222; border: 2px solid #555; border-radius: 10px; }
            QLineEdit { font-size: 32px; padding: 10px; color: white; background: #333; border: 1px solid #666; border-radius: 5px; }
            QPushButton { font-size: 24px; font-weight: bold; background-color: #444; color: white; border: 1px solid #555; border-radius: 5px; }
            QPushButton:pressed { background-color: #666; }
            QPushButton#EnterBtn { background-color: #468CFF; border: 1px solid #468CFF; }
            QPushButton#CloseBtn { background-color: #FF5555; border: 1px solid #FF5555; }
            QPushButton:disabled { color: #555; background-color: #333; border: 1px solid #333; }
        """)

        layout = QVBoxLayout(self)
        
        self.display = QLineEdit(str(initial_value))
        self.display.setAlignment(Qt.AlignRight)
        self.display.setReadOnly(True) 
        layout.addWidget(self.display)

        grid = QGridLayout()
        grid.setSpacing(5)
        
        keys = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('0', 3, 0), ('.', 3, 1), ('Del', 3, 2),
            ('Clear', 4, 0), ('-', 4, 1)
        ]

        for text, r, c in keys:
            btn = QPushButton(text)
            btn.setMinimumHeight(60)
            if text == 'Del':
                btn.clicked.connect(self._on_backspace)
            elif text == 'Clear':
                btn.clicked.connect(self.display.clear)
            elif text == '.':
                if self.precision == 0: 
                    btn.setEnabled(False) # 정수 모드면 비활성화
                btn.clicked.connect(lambda _, t=text: self._on_input(t))
            else:
                btn.clicked.connect(lambda _, t=text: self._on_input(t))
            grid.addWidget(btn, r, c)

        btn_close = QPushButton("취소")
        btn_close.setObjectName("CloseBtn")
        btn_close.setMinimumHeight(60)
        btn_close.clicked.connect(self.reject)
        grid.addWidget(btn_close, 4, 2) 

        btn_enter = QPushButton("확인 (Enter)")
        btn_enter.setObjectName("EnterBtn")
        btn_enter.setMinimumHeight(60)
        btn_enter.clicked.connect(self.accept)
        layout.addLayout(grid)
        layout.addWidget(btn_enter)

    # 창이 뜨면 포커스 강제 (터치 씹힘 방지)
    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.display.setFocus()
        QTimer.singleShot(100, self._force_focus)

    def _force_focus(self):
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def _on_input(self, text):
        # 1. 마이너스(-) 키는 부호 반전 기능이므로 '덮어쓰기' 하지 않음 (기존 값 유지하며 부호만 변경)
        if text == '-':
            current_text = self.display.text()
            if current_text:
                if current_text.startswith('-'): 
                    self.display.setText(current_text[1:])
                else: 
                    self.display.setText('-' + current_text)
            # 첫 입력 상태 해제 (부호 바꿨으면 입력 시작한 것으로 간주)
            self.first_input = False
            return

        # 2. 숫자나 점(.) 입력 시: 첫 입력이면 기존 값 지우기
        if self.first_input:
            self.display.clear()
            self.first_input = False
            # 만약 처음 누른 게 점(.)이면 "0."으로 시작하도록 편의성 제공
            if text == '.':
                self.display.setText("0.")
                return

        # 3. 기존 입력 방식 (이어붙이기)
        current_text = self.display.text()
        if text == '.' and '.' in current_text: return
        self.display.setText(current_text + text)

    def _on_backspace(self):
        # 백스페이스를 누르면 "수정" 의도이므로 첫 입력 모드 해제
        self.first_input = False
        self.display.setText(self.display.text()[:-1])

    def get_value(self):
        txt = self.display.text()
        if not txt or txt == '-': return 0.0 if self.precision > 0 else 0
        try:
            val = float(txt)
            if self.precision == 0: return int(val)
            return round(val, self.precision)
        except:
            return 0