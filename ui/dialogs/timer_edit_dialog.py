from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QSizePolicy, QInputDialog
)

# [키패드 임포트]
try:
    from widgets.touch_number_keyboard import TouchNumberKeyboard
except ImportError:
    TouchNumberKeyboard = None

class TimerEditDialog(QDialog):
    def __init__(self, timer_name, current_val_ms, parent=None):
        super().__init__(parent)
        self.setWindowTitle("타이머 시간 설정")
        
        # [핵심] 모달 설정 강화
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        
        self.resize(350, 320)
        self.current_ms = int(current_val_ms)

        self.setStyleSheet("""
            QDialog {
                background-color: #1A1F2B;
                border: 2px solid #468CFF;
                border-radius: 12px;
            }
            QLabel {
                color: #EEE;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton {
                border-radius: 8px;
                font-weight: bold;
                font-size: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 타이머 이름
        lbl_name_display = QLabel(timer_name)
        lbl_name_display.setAlignment(Qt.AlignCenter)
        lbl_name_display.setStyleSheet("color: #FFD700; font-size: 22px; font-weight: 900; margin-bottom: 5px;")
        layout.addWidget(lbl_name_display)

        # 안내 라벨
        lbl_title = QLabel("설정 시간 변경 (초)")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color: #AAA; font-size: 14px;")
        layout.addWidget(lbl_title)

        # 값 입력 영역
        val_layout = QHBoxLayout()
        val_layout.setSpacing(10)

        self.btn_val = QPushButton()
        self.btn_val.setFixedHeight(80)
        self.btn_val.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_val.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50;
                color: #F1C40F;
                font-size: 40px;
                border: 2px solid #3E4A59;
            }
            QPushButton:pressed {
                background-color: #34495E;
                border: 2px solid #468CFF;
            }
        """)
        self.btn_val.clicked.connect(self._open_keypad)
        val_layout.addWidget(self.btn_val)
        
        self._update_display() 

        # 증감 버튼
        ud_layout = QVBoxLayout()
        ud_layout.setSpacing(5)
        
        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedSize(60, 38)
        self.btn_up.setStyleSheet("background-color: #34495E; color: #2ECC71; font-size: 20px;")
        self.btn_up.clicked.connect(self._increase)
        
        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedSize(60, 38)
        self.btn_down.setStyleSheet("background-color: #34495E; color: #E74C3C; font-size: 20px;")
        self.btn_down.clicked.connect(self._decrease)
        
        ud_layout.addWidget(self.btn_up)
        ud_layout.addWidget(self.btn_down)
        val_layout.addLayout(ud_layout)

        layout.addLayout(val_layout)

        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.btn_cancel = QPushButton("취소")
        self.btn_cancel.setFixedHeight(50)
        self.btn_cancel.setStyleSheet("background-color: #582F2F; color: white; border: 1px solid #C0392B;")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("저장")
        self.btn_save.setFixedHeight(50)
        self.btn_save.setStyleSheet("background-color: #2980B9; color: white; border: 1px solid #3498DB;")
        self.btn_save.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    # ★ [핵심] 터치 씹힘 방지
    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.setFocus()
        QTimer.singleShot(100, self._force_focus)

    def _force_focus(self):
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def _update_display(self):
        sec_val = self.current_ms / 1000.0
        self.btn_val.setText(f"{sec_val:.1f}")

    def _open_keypad(self):
        formatted_val = f"{self.current_ms / 1000.0:.1f}"
        
        if TouchNumberKeyboard:
            dlg = TouchNumberKeyboard(formatted_val, 1, parent=self)
            if dlg.exec() == QDialog.Accepted:
                try:
                    input_float = float(dlg.get_value())
                    self.current_ms = int(round(input_float * 1000))
                    self._update_display()
                except ValueError:
                    pass
        else:
            current_sec = self.current_ms / 1000.0
            val, ok = QInputDialog.getDouble(self, "입력", "시간(초):", current_sec, 0, 999, 1)
            if ok:
                self.current_ms = int(round(val * 1000))
                self._update_display()

    def _increase(self):
        self.current_ms += 100
        self._update_display()

    def _decrease(self):
        if self.current_ms >= 100:
            self.current_ms -= 100
            self._update_display()

    def get_value_ms(self):
        return self.current_ms