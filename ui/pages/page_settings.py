import json
import os
import struct
import sys
from utils.paths import get_settings_path as _get_settings_path
from utils.json_utils import load_json, save_json
from PySide6.QtCore import Qt, Signal, QEventLoop
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QScrollArea, QGridLayout, QComboBox, 
    QLineEdit, QTabWidget, QMessageBox, QGroupBox, QDialog, QApplication,
    QScrollBar, QScroller, QScrollerProperties, QCheckBox
)
from widgets.glass_card import GlassCard

# 커스텀 위젯 임포트
try:
    from ui.widgets.custom_inputs import TouchComboBox, ClickableLineEdit
except ImportError:
    TouchComboBox = QComboBox
    ClickableLineEdit = QLineEdit

try:
    from widgets.touch_keyboard import TouchKeyboard
except ImportError:
    TouchKeyboard = None

# 매니저 모듈 임포트
try:
    from utils.io_manager import IOManager
except ImportError:
    IOManager = None

try:
    from utils.languages import LanguageManager
except ImportError:
    LanguageManager = None

# =========================================================
# [NEW] 숫자/IP 입력 전용 오버레이 키패드
# =========================================================
class NumberInputOverlay(QWidget):
    def __init__(self, current_val_str, is_ip=False, parent=None):
        super().__init__(parent)
        
        # 최상위 윈도우 덮기
        if parent:
            main_window = parent.window()
            self.setParent(main_window)
            self.resize(main_window.size())
            
        # 배경 어둡게
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        
        self.is_ip = is_ip
        self.result_val = None
        self._event_loop = None
        self.first_input = True
        
        # 레이아웃
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        container = QFrame()
        container.setFixedSize(340, 480)
        container.setStyleSheet("""
            QFrame {
                background-color: #1A1F2B;
                border: 2px solid #468CFF;
                border-radius: 15px;
            }
            QLabel {
                color: #FFD700;
                font-size: 28px;
                font-weight: bold;
                background: rgba(0,0,0,0.3);
                border: 1px solid #444;
                border-radius: 6px;
                padding: 5px;
            }
            QPushButton {
                background-color: #34495E;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
            }
            QPushButton:pressed { background-color: #468CFF; }
            QPushButton#btnCancel { background-color: #582F2F; border: 1px solid #C0392B; font-size: 18px; }
            QPushButton#btnOk { background-color: #2980B9; border: 1px solid #3498DB; font-size: 18px; }
        """)
        
        vbox = QVBoxLayout(container)
        vbox.setSpacing(10)
        vbox.setContentsMargins(20, 20, 20, 20)
        
        # 타이틀 (IP 모드인지 표시)
        title_str = "IP Address Input" if is_ip else "Number Input"
        lbl_title = QLabel(title_str)
        lbl_title.setStyleSheet("border: none; background: transparent; color: #AAA; font-size: 14px;")
        lbl_title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(lbl_title)

        # 디스플레이
        self.display = QLabel(current_val_str)
        self.display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.display.setFixedHeight(60)
        vbox.addWidget(self.display)
        
        # 그리드 키패드
        grid = QGridLayout()
        grid.setSpacing(10)
        
        keys = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('0', 3, 0), ('.', 3, 1), ('←', 3, 2),
        ]
        
        for text, r, c in keys:
            btn = QPushButton(text)
            btn.setFixedSize(85, 65)
            
            if text == '.':
                btn.clicked.connect(self._on_dot)
            elif text == '←':
                btn.clicked.connect(self._on_backspace)
            else:
                btn.clicked.connect(lambda _, t=text: self._on_digit(t))
                
            grid.addWidget(btn, r, c)
            
        vbox.addLayout(grid)
        
        # 하단 버튼
        hbox = QHBoxLayout()
        btn_cancel = QPushButton("취소")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.setFixedHeight(55)
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("확인")
        btn_ok.setObjectName("btnOk")
        btn_ok.setFixedHeight(55)
        btn_ok.clicked.connect(self.accept)
        
        hbox.addWidget(btn_cancel)
        hbox.addWidget(btn_ok)
        vbox.addLayout(hbox)
        
        layout.addWidget(container)

    def _on_digit(self, digit):
        if self.first_input:
            self.display.setText(digit)
            self.first_input = False
        else:
            current = self.display.text()
            if current == "0": self.display.setText(digit)
            else: self.display.setText(current + digit)

    def _on_dot(self):
        text = self.display.text()
        
        if self.first_input:
            self.display.setText("0.")
            self.first_input = False
            return

        if self.is_ip:
            # IP 모드: 점을 최대 3개까지 허용, 연속된 점 방지
            if not text.endswith(".") and text.count(".") < 3:
                self.display.setText(text + ".")
        else:
            # 일반 숫자 모드: 점은 하나만 허용
            if "." not in text:
                self.display.setText(text + ".")

    def _on_backspace(self):
        current = self.display.text()
        if len(current) > 1:
            self.display.setText(current[:-1])
        else:
            self.display.setText("0")
            self.first_input = True

    def accept(self):
        self.result_val = self.display.text()
        if self._event_loop: self._event_loop.quit()
        self.close()
        self.deleteLater()

    def reject(self):
        self.result_val = None
        if self._event_loop: self._event_loop.quit()
        self.close()
        self.deleteLater()

    def exec(self):
        self.show()
        self.raise_()
        self._event_loop = QEventLoop()
        self._event_loop.exec()
        return self.result_val

# =========================================================
# [기존 유지] 종료 확인 오버레이
# =========================================================
class ConfirmOverlay(QWidget):
    def __init__(self, title, message, btn_yes="예", btn_no="아니오", parent=None):
        super().__init__(parent)
        if parent:
            self.resize(parent.size())
            
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        
        self.result = False
        self._event_loop = None
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        container = QFrame()
        container.setFixedSize(450, 250)
        container.setStyleSheet("""
            QFrame {
                background-color: #1A1F2B;
                border: 2px solid #FF4646;
                border-radius: 15px;
            }
            QLabel {
                background: transparent;
                border: none;
                font-weight: bold;
            }
        """)
        
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(30, 30, 30, 30)
        vbox.setSpacing(20)
        
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color: #FF4646; font-size: 24px; font-weight: 900;")
        vbox.addWidget(lbl_title)
        
        lbl_msg = QLabel(message)
        lbl_msg.setAlignment(Qt.AlignCenter)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("color: #EEE; font-size: 18px;")
        vbox.addWidget(lbl_msg)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_cancel = QPushButton(btn_no)
        self.btn_cancel.setFixedSize(120, 50)
        self.btn_cancel.setStyleSheet("""
            QPushButton { background: #34495E; color: white; border-radius: 8px; font-size: 16px; font-weight: bold; }
            QPushButton:pressed { background: #555; }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton(btn_yes)
        self.btn_ok.setFixedSize(120, 50)
        self.btn_ok.setStyleSheet("""
            QPushButton { background: #C0392B; color: white; border-radius: 8px; font-size: 16px; font-weight: bold; border: 1px solid #E74C3C; }
            QPushButton:pressed { background: #E74C3C; }
        """)
        self.btn_ok.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        vbox.addLayout(btn_layout)
        
        layout.addWidget(container)

    def accept(self):
        self.result = True
        if self._event_loop: self._event_loop.quit()
        self.close()
        self.deleteLater()

    def reject(self):
        self.result = False
        if self._event_loop: self._event_loop.quit()
        self.close()
        self.deleteLater()

    def exec(self):
        self.show()
        self.raise_()
        self._event_loop = QEventLoop()
        self._event_loop.exec()
        return self.result

# 스타일 정의
TAB_STYLE = """
    QTabWidget::pane { border: none; background: transparent; padding-top: 10px; }
    QTabBar::tab {
        background: rgba(255, 255, 255, 0.05); color: #AAA; padding: 8px 20px;
        margin-right: 5px; border-radius: 8px; font-weight: bold; font-size: 14px;
        border: 1px solid transparent;
    }
    QTabBar::tab:selected {
        background: rgba(70, 140, 255, 0.2); color: #468CFF; border: 1px solid #468CFF;
    }
    QTabBar::tab:hover:!selected {
        background: rgba(255, 255, 255, 0.1); color: #DDD;
    }
"""

LINE_EDIT_STYLE = """
    QLineEdit {
        background: rgba(0, 0, 0, 0.2); color: #EEE;
        border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px;
        padding: 5px 8px; font-size: 13px; min-height: 25px;
        selection-background-color: #468CFF;
    }
    QLineEdit:hover { background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.2); }
    QLineEdit:focus { border: 1px solid #468CFF; background: rgba(70, 140, 255, 0.05); }
    QLineEdit::placeholder { color: rgba(255, 255, 255, 0.3); }
"""

SCROLLBAR_STYLE = """
    QScrollBar:vertical { border: none; background: rgba(0, 0, 0, 0.1); width: 10px; margin: 0px; border-radius: 5px; }
    QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.2); min-height: 30px; border-radius: 5px; }
    QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.3); }
    QScrollBar::handle:vertical:pressed { background: rgba(70, 140, 255, 0.5); }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
"""

GROUPBOX_STYLE = """
    QGroupBox {
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        margin-top: 25px; 
        font-size: 14px; 
        font-weight: bold;
        background: rgba(0, 0, 0, 0.1);
    }
    QGroupBox::title { 
        subcontrol-origin: margin; 
        subcontrol-position: top left; 
        left: 15px; 
        top: 5px;
        padding: 0 5px;
        color: #DDD;
    }
"""

AXIS_NAMES = ["X축", "Y축", "Z축", "Y2축", "Z2축", "세타", "R1", "R2"]

class PageSettings(GlassCard):
    # ★ 밸브 설정 변경 시그널
    sig_valve_config_changed = Signal()
    
    def __init__(self):
        super().__init__("") 
        
        if hasattr(self, 'title_label'):
            self.title_label.hide()
            if self.title_label.parentWidget() and self.title_label.parentWidget() != self:
                self.title_label.parentWidget().hide()

        if self.layout():
            self.layout().setContentsMargins(10, 5, 10, 10)

        self.plc_client = None

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)
        
        # 1. 일반 설정 탭
        self.tab_general = QWidget()
        self._init_general_tab()
        self.tabs.addTab(self.tab_general, "일반 설정")

        # 2. I/O 설정 탭
        self.tab_io = QWidget()
        self._init_io_tab()
        self.tabs.addTab(self.tab_io, "IO 이름 변경")

        # 3. 파라미터 설정 탭
        self.tab_param = QWidget()
        self._init_param_tab()
        self.tabs.addTab(self.tab_param, "시스템 파라미터")
        
        # 4. 밸브 설정 탭
        self.tab_valve = QWidget()
        self._init_valve_tab()
        self.tabs.addTab(self.tab_valve, "밸브 설정")

        # 5. 알람 메시지 탭
        self.tab_alarm = QWidget()
        self._init_alarm_tab()
        self.tabs.addTab(self.tab_alarm, "알람 메시지")

        # 6. 인터록 설정 탭
        self.tab_interlock = QWidget()
        self._init_interlock_tab()
        self.tabs.addTab(self.tab_interlock, "인터록 설정")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.body.addWidget(self.tabs)

        if IOManager:
            IOManager.instance().sig_names_changed.connect(self._on_manager_changed)
            
        self._load_plc_settings()
        self.update_language()

    def showEvent(self, event):
        if not self.plc_client:
            main_window = self.window()
            if hasattr(main_window, 'plc_client'):
                self.set_plc_client(main_window.plc_client)

        if self.plc_client:
            self._on_plc_status_changed(self.plc_client.is_connected)

        # 설정 페이지 진입 시 현재 탭이 파라미터 탭이면 자동 로드
        if self.tabs.currentIndex() == 2:
            self._load_params()

        super().showEvent(event)

    def _on_tab_changed(self, index):
        """탭 전환 시 파라미터 탭이면 자동으로 불러오기"""
        if index == 2:
            self._load_params()

    def set_plc_client(self, client):
        self.plc_client = client
        if self.plc_client:
            try:
                self.plc_client.sig_connected.disconnect(self._on_plc_status_changed)
            except RuntimeError:
                pass  # 연결되지 않은 시그널 disconnect는 무시
            self.plc_client.sig_connected.connect(self._on_plc_status_changed)
            self._on_plc_status_changed(self.plc_client.is_connected)

    # ----------------------------------------------------------------------
    # [Tab 4] 밸브 설정
    # ----------------------------------------------------------------------
    def _init_valve_tab(self):
        """
        밸브 설정 탭 초기화
        - V1~V32 이름 설정
        - 동작 모드: Momentary / Toggle
        - 순서 변경
        - 사용 여부
        """
        main_layout = QVBoxLayout(self.tab_valve)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 상단 툴바
        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        
        btn_save = QPushButton(" 저장")
        btn_save.setFixedSize(120, 40)
        btn_save.setStyleSheet("""
            QPushButton {
                background: #27AE60;
                border: 1px solid #2ECC71;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background: #2ECC71; }
            QPushButton:pressed { background: #1E8449; }
        """)
        btn_save.clicked.connect(self._save_valve_config)
        toolbar.addWidget(btn_save)
        main_layout.addLayout(toolbar)
        
        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(content_widget)
        vbox.setSpacing(0)
        vbox.setContentsMargins(10, 10, 10, 20)
        
        # 밸브 설정 그룹박스
        grp_valve = QGroupBox("밸브 설정 (Y00~Y0F / Y20~Y2F)")
        grp_valve.setStyleSheet(GROUPBOX_STYLE)
        grid = QGridLayout(grp_valve)
        grid.setContentsMargins(15, 35, 15, 15)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        
        # 헤더
        headers = ["사용", "번호", "이름", "동작 모드", "순서", "JOG"]
        for c, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #FFD700; font-weight: bold; font-size: 13px;")
            grid.addWidget(lbl, 0, c)

        # 밸브 32개 설정 UI
        self.valve_checks = []      # 사용 여부 체크박스
        self.valve_name_edits = []  # 이름 입력창
        self.valve_mode_combos = [] # 동작 모드 콤보박스
        self.valve_up_btns = []     # 위로 버튼
        self.valve_down_btns = []   # 아래로 버튼
        self.valve_jog_btns = []    # JOG 팝업 표시 여부
        self.valve_jog_up_btns = [] # JOG 순서 위로
        self.valve_jog_down_btns = [] # JOG 순서 아래로
        self._jog_order = []        # JOG 선택 밸브 인덱스 순서 리스트
        self._JOG_MAX = 6           # JOG 팝업 최대 밸브 수
        
        for i in range(32):
            row = i + 1

            # 사용 여부 체크박스
            chk = QCheckBox()
            chk.setChecked(i >= 16)  # 기본값: Y20~Y2F 사용
            chk.setStyleSheet("""
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border: 2px solid #888;
                    border-radius: 4px;
                    background: transparent;
                }
                QCheckBox::indicator:checked {
                    background-color: #468CFF;
                    border: 2px solid #468CFF;
                }
            """)
            self.valve_checks.append(chk)
            grid.addWidget(chk, row, 0, Qt.AlignCenter)
            
            # 번호 (Y00~Y0F, Y20~Y2F)
            y_addr = i if i < 16 else i + 16
            lbl_num = QLabel(f"Y{y_addr:02X}")
            lbl_num.setAlignment(Qt.AlignCenter)
            lbl_num.setStyleSheet("color: #FFD280; font-weight: bold; font-size: 12px; font-family: monospace;")
            grid.addWidget(lbl_num, row, 1)

            # 이름 입력창 → 버튼으로 변경 (클릭하면 터치 키보드)
            named_y0x = [
                "형개허가", "형폐허가", "에젝터 허가", "싸이클스타트",
                "컨베어출력1", "컨베어출력2", "예비1", "예비2",
                f"예비 Y08", f"예비 Y09", f"예비 Y0A", f"예비 Y0B",
                f"예비 Y0C", f"예비 Y0D", f"예비 Y0E", f"예비 Y0F",
            ]
            named_y2x = [
                "척 1 (Chuck 1)", "척 2 (Chuck 2)", "척 3 (Chuck 3)", "척 4 (Chuck 4)",
                "흡착 1 (Vac 1)", "흡착 2 (Vac 2)", "흡착 3 (Vac 3)", "흡착 4 (Vac 4)",
                "포스쳐 반전", "포스쳐 복귀", "스위블 회전", "스위블 복귀",
                "니퍼 컷팅 1", "니퍼 컷팅 2", "컨베이어 출력", "공급기 출력"
            ]
            default_name = named_y2x[i - 16] if i >= 16 else named_y0x[i]
            
            btn_name = QPushButton(default_name)
            btn_name.setFixedHeight(35)
            btn_name.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid #666;
                    border-radius: 4px;
                    color: white;
                    padding: 5px;
                    font-size: 12px;
                    text-align: left;
                    padding-left: 10px;
                }
                QPushButton:hover {
                    border: 1px solid #468CFF;
                    background: rgba(70, 140, 255, 0.15);
                }
                QPushButton:pressed {
                    background: rgba(70, 140, 255, 0.3);
                }
            """)
            btn_name.clicked.connect(lambda checked, idx=i: self._edit_valve_name(idx))
            self.valve_name_edits.append(btn_name)
            grid.addWidget(btn_name, row, 2)
            
            # 동작 모드 → 토글 버튼으로 변경
            btn_mode = QPushButton("Toggle")
            btn_mode.setFixedHeight(35)
            btn_mode.setCheckable(True)
            btn_mode.setChecked(True)  # 기본값: Toggle
            btn_mode.setStyleSheet("""
                QPushButton {
                    background: rgba(70, 140, 255, 0.3);
                    border: 1px solid #468CFF;
                    border-radius: 4px;
                    color: white;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: rgba(70, 140, 255, 0.4);
                }
                QPushButton:checked {
                    background: rgba(46, 204, 113, 0.3);
                    border: 1px solid #2ECC71;
                    color: #2ECC71;
                }
                QPushButton:checked:hover {
                    background: rgba(46, 204, 113, 0.4);
                }
            """)
            btn_mode.toggled.connect(lambda checked, b=btn_mode: b.setText("Toggle" if checked else "Momentary"))
            self.valve_mode_combos.append(btn_mode)
            grid.addWidget(btn_mode, row, 3)
            
            # 순서 변경 버튼
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(5)
            
            btn_up = QPushButton("▲")
            btn_up.setFixedSize(35, 30)
            btn_up.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid #666;
                    border-radius: 4px;
                    color: white;
                    font-size: 10px;
                }
                QPushButton:hover { background: rgba(70, 140, 255, 0.3); }
                QPushButton:pressed { background: rgba(70, 140, 255, 0.5); }
            """)
            btn_up.clicked.connect(lambda checked, idx=i: self._move_valve_up(idx))
            self.valve_up_btns.append(btn_up)
            btn_layout.addWidget(btn_up)
            
            btn_down = QPushButton("▼")
            btn_down.setFixedSize(35, 30)
            btn_down.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid #666;
                    border-radius: 4px;
                    color: white;
                    font-size: 10px;
                }
                QPushButton:hover { background: rgba(70, 140, 255, 0.3); }
                QPushButton:pressed { background: rgba(70, 140, 255, 0.5); }
            """)
            btn_down.clicked.connect(lambda checked, idx=i: self._move_valve_down(idx))
            self.valve_down_btns.append(btn_down)
            btn_layout.addWidget(btn_down)
            
            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            grid.addWidget(btn_widget, row, 4)

            # JOG 열: [JOG 토글] [▲] [▼]
            jog_cell = QWidget()
            jog_h = QHBoxLayout(jog_cell)
            jog_h.setContentsMargins(2, 0, 2, 0)
            jog_h.setSpacing(3)

            btn_jog = QPushButton("JOG")
            btn_jog.setFixedSize(45, 33)
            btn_jog.setCheckable(True)
            btn_jog.setChecked(False)
            btn_jog.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.07);
                    border: 1px solid #555;
                    border-radius: 4px;
                    color: #666;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:checked {
                    background: rgba(0,229,255,0.2);
                    border: 1px solid #00E5FF;
                    color: #00E5FF;
                }
            """)
            _jog_ord_btn_style = """
                QPushButton {
                    background: rgba(255,255,255,0.05);
                    border: 1px solid #444;
                    border-radius: 3px;
                    color: #555;
                    font-size: 9px;
                }
                QPushButton:enabled {
                    color: #00B4D8;
                    border: 1px solid #00B4D8;
                }
                QPushButton:pressed { background: rgba(0,180,216,0.3); }
            """
            btn_ju = QPushButton("▲")
            btn_ju.setFixedSize(22, 15)
            btn_ju.setStyleSheet(_jog_ord_btn_style)
            btn_ju.setEnabled(False)

            btn_jd = QPushButton("▼")
            btn_jd.setFixedSize(22, 15)
            btn_jd.setStyleSheet(_jog_ord_btn_style)
            btn_jd.setEnabled(False)

            ud_col = QVBoxLayout()
            ud_col.setSpacing(1)
            ud_col.setContentsMargins(0, 0, 0, 0)
            ud_col.addWidget(btn_ju)
            ud_col.addWidget(btn_jd)

            jog_h.addWidget(btn_jog)
            jog_h.addLayout(ud_col)

            btn_jog.toggled.connect(lambda checked, b=btn_jog, idx=i: self._on_jog_valve_toggled(b, checked, idx))
            btn_ju.clicked.connect(lambda checked, idx=i: self._move_jog_order(idx, -1))
            btn_jd.clicked.connect(lambda checked, idx=i: self._move_jog_order(idx, +1))

            self.valve_jog_btns.append(btn_jog)
            self.valve_jog_up_btns.append(btn_ju)
            self.valve_jog_down_btns.append(btn_jd)
            grid.addWidget(jog_cell, row, 5)

        vbox.addWidget(grp_valve)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # settings.json에서 밸브 설정 및 IO 입력 이름 로드
        self._load_valve_config()
        self._load_io_input_names()
    
    def _edit_valve_name(self, idx):
        """터치 키보드로 밸브 이름 편집"""
        try:
            current_name = self.valve_name_edits[idx].text()
            
            dlg = TouchKeyboard("밸브 이름 입력", current_name, self)
            if dlg.exec() == QDialog.Accepted:
                new_name = dlg.get_text()
                if new_name:
                    self.valve_name_edits[idx].setText(new_name)
        except ImportError:
            # TouchKeyboard가 없으면 간단한 입력 다이얼로그
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(
                self, 
                "밸브 이름 입력", 
                "이름:", 
                QLineEdit.Normal, 
                self.valve_name_edits[idx].text()
            )
            if ok and text:
                self.valve_name_edits[idx].setText(text)
    
    def _move_valve_up(self, idx):
        """밸브 순서를 위로 이동"""
        if idx == 0:
            return
        
        # 데이터 교환
        self._swap_valve_data(idx, idx - 1)
    
    def _move_valve_down(self, idx):
        """밸브 순서를 아래로 이동"""
        if idx >= 31:
            return
        
        # 데이터 교환
        self._swap_valve_data(idx, idx + 1)
    
    def _swap_valve_data(self, idx1, idx2):
        """두 밸브의 데이터를 교환"""
        # 사용 여부
        c1 = self.valve_checks[idx1].isChecked()
        c2 = self.valve_checks[idx2].isChecked()
        self.valve_checks[idx1].setChecked(c2)
        self.valve_checks[idx2].setChecked(c1)
        
        # 이름 (버튼 텍스트)
        n1 = self.valve_name_edits[idx1].text()
        n2 = self.valve_name_edits[idx2].text()
        self.valve_name_edits[idx1].setText(n2)
        self.valve_name_edits[idx2].setText(n1)
        
        # 동작 모드 (토글 버튼 체크 상태)
        m1 = self.valve_mode_combos[idx1].isChecked()
        m2 = self.valve_mode_combos[idx2].isChecked()
        self.valve_mode_combos[idx1].setChecked(m2)
        self.valve_mode_combos[idx2].setChecked(m1)
    
    def _on_jog_valve_toggled(self, btn, checked, valve_idx):
        """JOG 버튼 토글 — 최대 6개 초과 시 자동 해제, _jog_order 동기화"""
        if checked:
            if len(self._jog_order) >= self._JOG_MAX:
                btn.blockSignals(True)
                btn.setChecked(False)
                btn.blockSignals(False)
                return
            if valve_idx not in self._jog_order:
                self._jog_order.append(valve_idx)
        else:
            if valve_idx in self._jog_order:
                self._jog_order.remove(valve_idx)
        self._refresh_jog_order_btns()

    def _move_jog_order(self, valve_idx, direction):
        """JOG 순서 이동 (direction: -1=위, +1=아래)"""
        if valve_idx not in self._jog_order:
            return
        pos = self._jog_order.index(valve_idx)
        new_pos = pos + direction
        if 0 <= new_pos < len(self._jog_order):
            self._jog_order[pos], self._jog_order[new_pos] = self._jog_order[new_pos], self._jog_order[pos]
        self._refresh_jog_order_btns()

    def _refresh_jog_order_btns(self):
        """JOG ▲/▼ 버튼 활성화 상태 갱신"""
        for i, btn_jog in enumerate(self.valve_jog_btns):
            in_jog = i in self._jog_order
            self.valve_jog_up_btns[i].setEnabled(in_jog)
            self.valve_jog_down_btns[i].setEnabled(in_jog)

    def _build_valve_config(self):
        """현재 UI 상태로 valve_config 리스트 생성"""
        valve_config = []
        for i in range(32):
            mode = "toggle" if self.valve_mode_combos[i].isChecked() else "momentary"
            jog_pos = self._jog_order.index(i) if i in self._jog_order else -1
            valve_config.append({
                "index": i,
                "name": self.valve_name_edits[i].text(),
                "mode": mode,
                "enabled": self.valve_checks[i].isChecked(),
                "jog_valve": i in self._jog_order,
                "jog_order": jog_pos,
                "order": i
            })
        return valve_config

    def _save_valve_config_silent(self):
        """팝업 없이 밸브 설정을 settings.json에 저장"""
        try:
            path = _get_settings_path()
            settings = load_json(path) or {}
            settings["valve_config"] = self._build_valve_config()
            save_json(path, settings)
            self.sig_valve_config_changed.emit()
            print("[Settings] 밸브 설정 자동 저장 완료")
        except Exception as e:
            print(f"[Settings] 밸브 설정 자동 저장 실패: {e}")

    def _save_valve_config(self):
        """밸브 설정을 settings.json에 저장"""
        try:
            path = _get_settings_path()
            settings = load_json(path) or {}
            settings["valve_config"] = self._build_valve_config()
            save_json(path, settings)
            print(f"[Settings] 밸브 설정 저장 완료")

            # ★ 밸브 설정 변경 시그널 발생
            self.sig_valve_config_changed.emit()

            # IO 출력 이름 동기화
            self._sync_valve_names_to_io()

            # 저장 완료 알림 (ConfirmOverlay는 이 파일 내에 정의되어 있음)
            dlg = ConfirmOverlay("저장 완료", "밸브 설정이 저장되었습니다.", btn_yes="확인", parent=self.window())
            dlg.btn_cancel.hide()
            dlg.exec()
            
        except Exception as e:
            print(f"[Settings] 밸브 설정 저장 실패: {e}")
    
    def _load_valve_config(self):
        """settings.json에서 밸브 설정 로드"""
        try:
            path = _get_settings_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    valve_config = settings.get("valve_config", None)

                    if valve_config and len(valve_config) == 32:
                        # jog_order 복원: jog_order >= 0 인 것들을 순서대로 정렬
                        jog_entries = [(cfg.get("jog_order", -1), i)
                                       for i, cfg in enumerate(valve_config)
                                       if cfg.get("jog_valve", False)]
                        jog_entries.sort(key=lambda x: x[0])
                        self._jog_order = [idx for _, idx in jog_entries]

                        for i, cfg in enumerate(valve_config):
                            self.valve_checks[i].setChecked(cfg.get("enabled", True))
                            self.valve_name_edits[i].setText(cfg.get("name", f"밸브 {i+1}"))
                            mode = cfg.get("mode", "toggle")
                            self.valve_mode_combos[i].setChecked(mode == "toggle")
                            self.valve_jog_btns[i].blockSignals(True)
                            self.valve_jog_btns[i].setChecked(cfg.get("jog_valve", False))
                            self.valve_jog_btns[i].blockSignals(False)
                        self._refresh_jog_order_btns()

                        print(f"[Settings] 밸브 설정 로드 완료")
        except Exception as e:
            print(f"[Settings] 밸브 설정 로드 실패: {e}")

        self._sync_valve_names_to_io()

    def _sync_valve_names_to_io(self):
        """밸브 설정 이름을 IOManager 출력 이름과 IO탭 편집창에 동기화"""
        if not IOManager:
            return
        if not hasattr(self, 'valve_name_edits') or not hasattr(self, 'output_edits'):
            return
        mgr = IOManager.instance()
        for i in range(32):
            name = self.valve_name_edits[i].text() if i < len(self.valve_name_edits) else f"Y{i:02X}"
            mgr.outputs[i] = name
            if i < len(self.output_edits):
                self.output_edits[i].setText(name)
        mgr.sig_names_changed.emit()
        print("[Settings] IO 출력 이름을 밸브 설정과 동기화 완료")

    # ----------------------------------------------------------------------
    # [Tab 1] 일반 설정
    # ----------------------------------------------------------------------
    def _init_general_tab(self):
        main_layout = QVBoxLayout(self.tab_general)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(30)
        layout.setContentsMargins(20, 10, 20, 20)
        
        # --- [그룹 1] PLC 연결 설정 ---
        self.grp_plc = QGroupBox("PLC 통신 설정") 
        self.grp_plc.setStyleSheet(GROUPBOX_STYLE.replace("rgba(255, 255, 255, 0.15)", "rgba(0, 229, 255, 0.4)").replace("#DDD", "#00E5FF"))
        
        plc_grid = QGridLayout(self.grp_plc)
        plc_grid.setContentsMargins(20, 35, 20, 20)
        plc_grid.setHorizontalSpacing(15)
        plc_grid.setVerticalSpacing(15)
        
        self.edit_ip = ClickableLineEdit("192.168.0.10")
        self.edit_ip.setPlaceholderText("IP Address")
        self.edit_ip.setStyleSheet(LINE_EDIT_STYLE)
        # [수정] IP 입력용 키패드 호출 (is_ip=True)
        self.edit_ip.clicked.connect(lambda: self._open_keypad(self.edit_ip, is_ip=True))
        
        self.edit_port = ClickableLineEdit("9094")
        self.edit_port.setPlaceholderText("Port")
        self.edit_port.setFixedWidth(100)
        self.edit_port.setStyleSheet(LINE_EDIT_STYLE)
        # [수정] 포트 입력용 키패드 호출 (is_ip=False)
        self.edit_port.clicked.connect(lambda: self._open_keypad(self.edit_port, is_ip=False))

        self.btn_connect = QPushButton("연결")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.setFixedSize(100, 40)
        self.btn_connect.setStyleSheet("""
            QPushButton { 
                background: rgba(0, 255, 0, 0.15); border: 1px solid #00FF00; color: #00FF00; 
                border-radius: 6px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background: rgba(0, 255, 0, 0.25); }
        """)
        self.btn_connect.clicked.connect(self._on_connect_clicked)

        self.lbl_status = QLabel("● Disconnected")
        self.lbl_status.setStyleSheet("color: #FF4646; font-size: 14px; font-weight: bold; margin-left: 5px;")

        plc_grid.addWidget(QLabel("IP 주소:"), 0, 0)
        plc_grid.addWidget(self.edit_ip, 0, 1)
        plc_grid.addWidget(QLabel("포트:"), 0, 2)
        plc_grid.addWidget(self.edit_port, 0, 3)
        plc_grid.addWidget(self.btn_connect, 0, 4)
        plc_grid.addWidget(self.lbl_status, 0, 5)
        
        layout.addWidget(self.grp_plc)

        # --- [그룹 2] 환경 설정 ---
        self.grp_env = QGroupBox("환경 설정") 
        self.grp_env.setStyleSheet(GROUPBOX_STYLE)
        
        env_layout = QHBoxLayout(self.grp_env)
        env_layout.setContentsMargins(20, 35, 20, 20)
        env_layout.setSpacing(20)
        
        self.lbl_lang = QLabel("언어 (Language)")
        self.lbl_lang.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        
        self.btn_lang_kr = QPushButton("🇰🇷 한국어")
        self.btn_lang_en = QPushButton("🇺🇸 English")
        
        btn_style_base = """
            QPushButton {
                border-radius: 20px; font-size: 13px; font-weight: bold;
                border: 2px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05); color: #AAA;
                padding: 8px 15px;
            }
        """
        self.btn_lang_kr.setStyleSheet(btn_style_base)
        self.btn_lang_en.setStyleSheet(btn_style_base)
        self.btn_lang_kr.setFixedSize(110, 40)
        self.btn_lang_en.setFixedSize(110, 40)
        
        self.btn_lang_kr.clicked.connect(lambda: self._set_language("KR"))
        self.btn_lang_en.clicked.connect(lambda: self._set_language("EN"))
        
        env_layout.addWidget(self.lbl_lang)
        env_layout.addWidget(self.btn_lang_kr)
        env_layout.addWidget(self.btn_lang_en)
        env_layout.addStretch(1)
        
        layout.addWidget(self.grp_env)
        
        # --- [그룹 3] 시스템 제어 ---
        self.grp_sys = QGroupBox("시스템") 
        self.grp_sys.setStyleSheet(GROUPBOX_STYLE.replace("#DDD", "#FF8080").replace("rgba(255, 255, 255, 0.15)", "rgba(255, 70, 70, 0.3)"))
        
        sys_layout = QHBoxLayout(self.grp_sys)
        sys_layout.setContentsMargins(20, 35, 20, 20)
        
        self.lbl_sys_info = QLabel("프로그램 종료")
        self.lbl_sys_info.setStyleSheet("color: #FF8080; font-size: 14px; font-weight: bold;")
        
        self.btn_exit = QPushButton("종료")
        self.btn_exit.setFixedSize(150, 45)
        self.btn_exit.setStyleSheet("""
            QPushButton {
                background: rgba(255, 70, 70, 0.15); border: 2px solid #FF4646; color: #FF4646;
                border-radius: 8px; font-size: 15px; font-weight: 900;
            }
            QPushButton:hover { background: rgba(255, 70, 70, 0.3); color: white; }
            QPushButton:pressed { background: rgba(200, 50, 50, 1.0); }
        """)
        self.btn_exit.clicked.connect(self._on_exit_clicked)
        
        sys_layout.addWidget(self.lbl_sys_info)
        sys_layout.addStretch(1)
        sys_layout.addWidget(self.btn_exit)
        
        layout.addWidget(self.grp_sys)
        
        layout.addSpacing(20)
        info = QLabel("HMI System v1.3.2 | Build 2026.02.05")
        info.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 12px;")
        info.setAlignment(Qt.AlignRight)
        layout.addWidget(info)
        
        layout.addStretch(1) 

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    # ----------------------------------------------------------------------
    # [Tab 2] I/O 설정
    # ----------------------------------------------------------------------
    def _init_io_tab(self):
        layout = QVBoxLayout(self.tab_io)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        top_layout = QHBoxLayout()
        top_layout.addStretch(1)
        self.io_info_lbl = QLabel("※ 변경 후 [이름 적용] 버튼을 눌러야 저장됩니다.")
        self.io_info_lbl.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 13px; margin-right: 5px;")
        top_layout.addWidget(self.io_info_lbl)
        layout.addLayout(top_layout)
        
        scroll_container = QFrame()
        scroll_container.setStyleSheet("background: rgba(0, 0, 0, 0.15); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05);")
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(5, 5, 5, 5)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        
        grid = QGridLayout(container)
        grid.setSpacing(12)
        grid.setContentsMargins(15, 15, 15, 15)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(4, 1)
        
        self.lbl_table_header_in = QLabel("입력 (Input) 이름")
        self.lbl_table_header_in.setStyleSheet("color: #AAA; font-weight: bold; font-size: 13px; margin-bottom: 8px;")
        grid.addWidget(self.lbl_table_header_in, 0, 1)
        
        self.lbl_table_header_out = QLabel("출력 (Output) 이름")
        self.lbl_table_header_out.setStyleSheet("color: #AAA; font-weight: bold; font-size: 13px; margin-bottom: 8px;")
        grid.addWidget(self.lbl_table_header_out, 0, 4)
            
        self.input_edits = []
        self.output_edits = []
        
        mgr = IOManager.instance() if IOManager else None
        count = 32
        
        for i in range(count):
            row_idx = i + 1
            # X00~X0F, X20~X2F (X10~X1F 건너뜀)
            x_addr = i if i < 16 else i + 16
            lbl_in = QLabel(f"X{x_addr:02X}")
            lbl_in.setStyleSheet("color: #64FFDA; font-weight: 600; font-family: 'Roboto Mono', monospace; font-size: 15px;")
            lbl_in.setAlignment(Qt.AlignCenter)
            curr_in_name = mgr.get_input_name(i) if mgr else ""

            edit_in = ClickableLineEdit(curr_in_name)
            edit_in.setPlaceholderText(f"X{x_addr:02X}")
            edit_in.setStyleSheet(LINE_EDIT_STYLE)
            edit_in.clicked.connect(lambda e=edit_in, t=f"X{x_addr:02X}": self._open_keyboard(e, t))
            self.input_edits.append(edit_in)

            grid.addWidget(lbl_in, row_idx, 0)
            grid.addWidget(edit_in, row_idx, 1)
            grid.setColumnMinimumWidth(2, 40)

            # Y00~Y0F, Y20~Y2F (Y10~Y1F 건너뜀)
            y_addr = i if i < 16 else i + 16
            lbl_out = QLabel(f"Y{y_addr:02X}")
            lbl_out.setStyleSheet("color: #FFD280; font-weight: 600; font-family: 'Roboto Mono', monospace; font-size: 15px;")
            lbl_out.setAlignment(Qt.AlignCenter)
            curr_out_name = mgr.get_output_name(i) if mgr else ""

            edit_out = ClickableLineEdit(curr_out_name)
            edit_out.setPlaceholderText(f"Y{y_addr:02X}")
            edit_out.setStyleSheet(LINE_EDIT_STYLE)
            edit_out.clicked.connect(lambda e=edit_out, t=f"Y{y_addr:02X}": self._open_keyboard(e, t))
            self.output_edits.append(edit_out)
            
            grid.addWidget(lbl_out, row_idx, 3)
            grid.addWidget(edit_out, row_idx, 4)

        container.setLayout(grid)
        scroll.setWidget(container)
        scroll_layout.addWidget(scroll)
        layout.addWidget(scroll_container, 1)
        
        layout.addSpacing(5)
        self.btn_io_save = QPushButton("이름 적용")
        self.btn_io_save.setMinimumHeight(50)
        self.btn_io_save.setCursor(Qt.PointingHandCursor)
        self.btn_io_save.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #468CFF, stop:1 #357AE8);
                color: white; font-size: 16px; font-weight: bold; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5A9CFF, stop:1 #468CFF); border: 1px solid rgba(255,255,255,0.3); }
            QPushButton:pressed { background: #2A65C7; border: none; }
        """)
        self.btn_io_save.clicked.connect(self._apply_io_names)
        layout.addWidget(self.btn_io_save)

    # ----------------------------------------------------------------------
    # [Tab 5] 알람 메시지
    # ----------------------------------------------------------------------
    def _init_alarm_tab(self):
        from ui.overlays.alarm_overlay import SEQUENCE_ALARMS, save_sequence_alarms

        main_layout = QVBoxLayout(self.tab_alarm)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 상단 툴바
        toolbar = QHBoxLayout()
        toolbar.addStretch(1)

        btn_add = QPushButton("＋ 알람 추가")
        btn_add.setFixedSize(140, 40)
        btn_add.setStyleSheet("""
            QPushButton { background: rgba(70,140,255,0.2); border: 1px solid #468CFF;
                color: #468CFF; border-radius: 6px; font-weight: bold; font-size: 13px; }
            QPushButton:pressed { background: rgba(70,140,255,0.4); }
        """)
        btn_add.clicked.connect(self._add_alarm)

        btn_save = QPushButton("저장")
        btn_save.setFixedSize(100, 40)
        btn_save.setStyleSheet("""
            QPushButton { background: #2A65C7; border: 1px solid #468CFF;
                color: white; border-radius: 6px; font-weight: bold; font-size: 13px; }
            QPushButton:pressed { background: #1A4FA0; }
        """)
        btn_save.clicked.connect(self._save_alarms)

        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_save)
        main_layout.addLayout(toolbar)

        # 헤더
        header = QWidget()
        header.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 4px;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 6, 10, 6)
        for text, stretch in [("번호", 1), ("알람 메시지", 5), ("", 2)]:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #AAA; font-weight: bold; font-size: 13px;")
            lbl.setAlignment(Qt.AlignCenter)
            hl.addWidget(lbl, stretch)
        main_layout.addWidget(header)

        # 스크롤 목록
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        self._alarm_list_widget = QWidget()
        self._alarm_list_widget.setStyleSheet("background: transparent;")
        self._alarm_list_layout = QVBoxLayout(self._alarm_list_widget)
        self._alarm_list_layout.setContentsMargins(0, 0, 0, 0)
        self._alarm_list_layout.setSpacing(4)
        self._alarm_list_layout.addStretch(1)

        scroll.setWidget(self._alarm_list_widget)
        main_layout.addWidget(scroll)

        self._refresh_alarm_list()

    def _refresh_alarm_list(self):
        from ui.overlays.alarm_overlay import SEQUENCE_ALARMS

        layout = self._alarm_list_layout
        # 기존 행 제거 (stretch 제외)
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row_style = """
            QWidget#AlarmRow { background: rgba(255,255,255,0.04); border-radius: 6px; }
            QWidget#AlarmRow:hover { background: rgba(255,255,255,0.08); }
        """
        for no in sorted(SEQUENCE_ALARMS.keys()):
            msg = SEQUENCE_ALARMS[no]
            row = QWidget()
            row.setObjectName("AlarmRow")
            row.setFixedHeight(48)
            row.setStyleSheet(row_style)

            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 0, 10, 0)
            rl.setSpacing(8)

            lbl_no = QLabel(f"A-{no:03d}")
            lbl_no.setFixedWidth(60)
            lbl_no.setAlignment(Qt.AlignCenter)
            lbl_no.setStyleSheet("color: #FF6B6B; font-weight: bold; font-size: 14px;")

            lbl_msg = QLabel(msg)
            lbl_msg.setStyleSheet("color: white; font-size: 14px;")
            lbl_msg.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            btn_edit = QPushButton("수정")
            btn_edit.setFixedSize(70, 34)
            btn_edit.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.1); border: 1px solid #888;
                    color: white; border-radius: 4px; font-size: 13px; font-weight: bold; }
                QPushButton:pressed { background: rgba(255,255,255,0.2); }
            """)
            btn_edit.clicked.connect(lambda _, n=no: self._edit_alarm(n))

            btn_del = QPushButton("삭제")
            btn_del.setFixedSize(70, 34)
            btn_del.setStyleSheet("""
                QPushButton { background: rgba(255,70,70,0.15); border: 1px solid #FF4646;
                    color: #FF4646; border-radius: 4px; font-size: 13px; font-weight: bold; }
                QPushButton:pressed { background: rgba(255,70,70,0.3); }
            """)
            btn_del.clicked.connect(lambda _, n=no: self._delete_alarm(n))

            rl.addWidget(lbl_no, 1)
            rl.addWidget(lbl_msg, 5)
            rl.addWidget(btn_edit)
            rl.addWidget(btn_del)

            layout.insertWidget(layout.count() - 1, row)

    def _alarm_next_no(self):
        from ui.overlays.alarm_overlay import SEQUENCE_ALARMS
        return max(SEQUENCE_ALARMS.keys(), default=0) + 1

    def _alarm_input(self, title, current=""):
        """알람 메시지 입력: 터치키보드 → QInputDialog 순으로 시도"""
        if TouchKeyboard:
            kb = TouchKeyboard(title, current, self)
            if kb.exec() != QDialog.Accepted:
                return None
            return kb.get_text().strip() or None
        from PySide6.QtWidgets import QInputDialog
        msg, ok = QInputDialog.getText(self, title, "메시지:", text=current)
        return msg.strip() if ok and msg.strip() else None

    def _add_alarm(self):
        from ui.overlays.alarm_overlay import SEQUENCE_ALARMS
        no = self._alarm_next_no()
        msg = self._alarm_input(f"A-{no:03d} 알람 메시지 입력")
        if msg is None:
            return
        SEQUENCE_ALARMS[no] = msg
        self._refresh_alarm_list()

    def _edit_alarm(self, no):
        from ui.overlays.alarm_overlay import SEQUENCE_ALARMS
        current = SEQUENCE_ALARMS.get(no, "")
        msg = self._alarm_input(f"A-{no:03d} 알람 메시지 수정", current)
        if msg is None:
            return
        SEQUENCE_ALARMS[no] = msg
        self._refresh_alarm_list()

    def _delete_alarm(self, no):
        from ui.overlays.alarm_overlay import SEQUENCE_ALARMS
        from ui.dialogs.sequence_utils import DarkConfirmDialog
        dlg = DarkConfirmDialog("알람 삭제", f"A-{no:03d} 알람을 삭제하시겠습니까?", self)
        if dlg.exec() == QDialog.Accepted:
            SEQUENCE_ALARMS.pop(no, None)
            self._refresh_alarm_list()

    def _save_alarms(self):
        from ui.overlays.alarm_overlay import save_sequence_alarms
        from ui.dialogs.sequence_utils import DarkMessageDialog
        save_sequence_alarms()
        DarkMessageDialog("저장 완료", "알람 메시지가 저장되었습니다.", parent=self).exec()

    # ----------------------------------------------------------------------
    # [Tab 3] 시스템 파라미터
    # ----------------------------------------------------------------------
    def _init_param_tab(self):
        main_layout = QVBoxLayout(self.tab_param)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 상단 툴바
        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        
        self.btn_apply_param = QPushButton("파라미터 적용")
        self.btn_apply_param.setFixedSize(140, 40)
        self.btn_apply_param.setStyleSheet("QPushButton { background: #C0392B; border: 1px solid #E74C3C; color: white; border-radius: 6px; font-weight: bold; font-size: 13px; } QPushButton:hover { background: #E74C3C; }")
        self.btn_apply_param.clicked.connect(self._save_params)

        toolbar.addWidget(self.btn_apply_param)
        main_layout.addLayout(toolbar)
        
        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(content_widget)
        vbox.setSpacing(25)
        vbox.setContentsMargins(10, 10, 10, 20)
        
        # -- [1] 축 구성 및 모션 파라미터 --
        grp_axis = QGroupBox("축 구성 및 모션 설정 (DT15000 ~)")
        grp_axis.setStyleSheet(GROUPBOX_STYLE)
        grid_axis = QGridLayout(grp_axis)
        grid_axis.setContentsMargins(15, 35, 15, 15)
        grid_axis.setHorizontalSpacing(10)
        grid_axis.setVerticalSpacing(10)
        
        headers = ["축 이름", "사용 여부", "운전 방향", "스트로크 한계", "가감속 시간"]
        for c, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setStyleSheet("color: #BBB; font-weight: bold; font-size: 13px;")
            lbl.setAlignment(Qt.AlignCenter)
            grid_axis.addWidget(lbl, 0, c)
            
        self.chk_axis_uses = []
        self.btn_axis_dirs = []
        self.edt_axis_strokes = []
        self.edt_axis_accels = []
        
        for i, name in enumerate(AXIS_NAMES):
            row = i + 1
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
            lbl_name.setAlignment(Qt.AlignCenter)
            grid_axis.addWidget(lbl_name, row, 0)
            
            # 사용여부
            chk = QCheckBox()
            chk.setStyleSheet("QCheckBox::indicator { width: 20px; height: 20px; }")
            hbox_chk = QHBoxLayout(); hbox_chk.setAlignment(Qt.AlignCenter); hbox_chk.addWidget(chk)
            w_chk = QWidget(); w_chk.setLayout(hbox_chk)
            grid_axis.addWidget(w_chk, row, 1)
            self.chk_axis_uses.append(chk)
            
            # 방향 (토글 버튼)
            btn_dir = QPushButton("정방향")
            btn_dir.setFixedSize(90, 30)
            btn_dir.setProperty("dir_value", 0) # 0: 정방향, 1: 역방향
            btn_dir.setStyleSheet("""
                QPushButton { background: rgba(0, 200, 0, 0.3); border: 1px solid #00FF00; color: #00FF00; border-radius: 4px; font-weight: bold; font-size: 12px; }
            """)
            btn_dir.clicked.connect(lambda _, b=btn_dir: self._toggle_dir_btn(b))
            grid_axis.addWidget(btn_dir, row, 2)
            self.btn_axis_dirs.append(btn_dir)
            
            # 스트로크 (mm 단위, 숫자 키패드)
            edt_str = ClickableLineEdit("0.000 mm")
            edt_str.setAlignment(Qt.AlignCenter)
            edt_str.setStyleSheet(LINE_EDIT_STYLE)
            # [수정] mm 단위 전용 키패드 호출
            edt_str.clicked.connect(lambda e=edt_str, t=f"{name} 스트로크": self._open_stroke_keypad(e, t))
            grid_axis.addWidget(edt_str, row, 3)
            self.edt_axis_strokes.append(edt_str)
            
            # 가감속 (일반 숫자 키패드)
            edt_acc = ClickableLineEdit("100")
            edt_acc.setAlignment(Qt.AlignCenter)
            edt_acc.setStyleSheet(LINE_EDIT_STYLE)
            # [수정] 일반 숫자 키패드 호출
            edt_acc.clicked.connect(lambda e=edt_acc, t=f"{name} 가감속": self._open_keypad(e, is_ip=False))
            grid_axis.addWidget(edt_acc, row, 4)
            self.edt_axis_accels.append(edt_acc)
            
        vbox.addWidget(grp_axis)
        
        # -- [2] 기타 설정 (데이터셋) --
        grp_etc = QGroupBox("기타 시스템 설정")
        grp_etc.setStyleSheet(GROUPBOX_STYLE)
        
        vbox_etc = QVBoxLayout(grp_etc)
        vbox_etc.setContentsMargins(15, 35, 15, 15)

        hbox_home_btn = QHBoxLayout()
        hbox_home_btn.addStretch(1)
        self.btn_home_toggle = QPushButton("OFF")
        self.btn_home_toggle.setFixedSize(100, 40)
        self.btn_home_toggle.setCheckable(True)
        self.btn_home_toggle.setChecked(False)
        self.btn_home_toggle.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.08); border: 1px solid #666; color: #AAA; border-radius: 8px; font-weight: bold; font-size: 15px; }
        """)
        self.btn_home_toggle.clicked.connect(self._on_home_toggle_clicked)
        hbox_home_btn.addWidget(self.btn_home_toggle)
        vbox_etc.addLayout(hbox_home_btn)

        lbl_preset = QLabel("데이터셋 (Zero Preset) - 버튼을 누르면 해당 축 원점 설정 (DT50033)")
        lbl_preset.setStyleSheet("color: #DDD; font-size: 13px; margin-bottom: 5px;")
        vbox_etc.addWidget(lbl_preset)
        
        grid_preset = QGridLayout()
        grid_preset.setSpacing(8)
        
        for i, name in enumerate(AXIS_NAMES):
            btn = QPushButton(f"{name}\nSET")
            btn.setFixedSize(70, 50)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #444; color: #AAA; border: 1px solid #666; 
                    border-radius: 6px; font-weight: bold; font-size: 12px;
                }
                QPushButton:pressed {
                    background-color: #E67E22; color: white; border: 1px solid #D35400;
                }
            """)
            btn.pressed.connect(lambda idx=i: self._on_dataset_pressed(idx))
            btn.released.connect(lambda idx=i: self._on_dataset_released(idx))
            
            row = i // 4
            col = i % 4
            grid_preset.addWidget(btn, row, col)
            
        vbox_etc.addLayout(grid_preset)
        vbox.addWidget(grp_etc)
        vbox.addStretch(1)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    # [수정] 방향 토글 버튼 핸들러
    def _toggle_dir_btn(self, btn):
        curr = btn.property("dir_value")
        new_val = 1 - curr
        self._update_dir_btn_style(btn, new_val)
        
    def _update_dir_btn_style(self, btn, val):
        btn.setProperty("dir_value", val)
        if val == 0:
            btn.setText("정방향")
            btn.setStyleSheet("""
                QPushButton { background: rgba(0, 200, 0, 0.3); border: 1px solid #00FF00; color: #00FF00; border-radius: 4px; font-weight: bold; font-size: 12px; }
            """)
        else:
            btn.setText("역방향")
            btn.setStyleSheet("""
                QPushButton { background: rgba(255, 100, 0, 0.3); border: 1px solid #FF8000; color: #FF8000; border-radius: 4px; font-weight: bold; font-size: 12px; }
            """)

    # [수정] 스트로크 전용 키패드 (mm 단위 처리)
    def _open_stroke_keypad(self, line_edit, title):
        text = line_edit.text().replace(" mm", "").strip()
        dlg = NumberInputOverlay(text, is_ip=False, parent=self)
        if dlg.exec():
            # 입력값 뒤에 mm 붙이기
            try:
                val = float(dlg.result_val)
                line_edit.setText(f"{val:.3f} mm")
            except ValueError:
                pass  # 숫자 변환 실패 시 무시

    # [수정] 일반 숫자 키패드 (포트, 가감속 등)
    def _open_keypad(self, line_edit, is_ip=False):
        dlg = NumberInputOverlay(line_edit.text(), is_ip=is_ip, parent=self)
        if dlg.exec():
            line_edit.setText(dlg.result_val)

    # [수정] 텍스트 키보드 (IO 이름용)
    def _open_keyboard(self, line_edit, title):
        if not TouchKeyboard:
            return
        dlg = TouchKeyboard(title, parent=self)
        if dlg.exec() == QDialog.Accepted:
            line_edit.setText(dlg.get_text())

    def _on_home_toggle_clicked(self):
        is_on = self.btn_home_toggle.isChecked()
        if is_on:
            self.btn_home_toggle.setText("ON")
            self.btn_home_toggle.setStyleSheet("""
                QPushButton { background: rgba(0, 200, 100, 0.3); border: 1px solid #00CC66; color: #00CC66; border-radius: 8px; font-weight: bold; font-size: 15px; }
            """)
        else:
            self.btn_home_toggle.setText("OFF")
            self.btn_home_toggle.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.08); border: 1px solid #666; color: #AAA; border-radius: 8px; font-weight: bold; font-size: 15px; }
            """)
        if self.plc_client and self.plc_client.is_connected:
            self.plc_client.send_jog_mode(1 if is_on else 0)

    def _on_dataset_pressed(self, axis_index):
        if not self.plc_client or not self.plc_client.is_connected: return
        val = (1 << axis_index)
        self.plc_client.write_words(0x09, self.plc_client.ADDR_AXIS_DATASET, [val])

    def _on_dataset_released(self, axis_index):
        if not self.plc_client or not self.plc_client.is_connected: return
        self.plc_client.write_words(0x09, self.plc_client.ADDR_AXIS_DATASET, [0])

    def _load_params(self):
        # ★ settings.json에서 축 설정 먼저 로드
        axis_uses_from_file = self._load_axis_settings()
        
        if not self.plc_client or not self.plc_client.is_connected:
            # PLC 연결 안됐을 때는 파일에서만 로드
            if axis_uses_from_file:
                for i in range(8):
                    if i < len(axis_uses_from_file):
                        self.chk_axis_uses[i].setChecked(axis_uses_from_file[i])
            return
            
        try:
            data = self.plc_client.read_words(0x09, self.plc_client.AXIS_PARAM_ADDR, 50)
            if not data or len(data) < 50: return
            
            use_bits = data[0]
            for i in range(8):
                is_use = (use_bits >> i) & 1
                self.chk_axis_uses[i].setChecked(bool(is_use))
                
            for i in range(8):
                direction = data[1 + i]
                self._update_dir_btn_style(self.btn_axis_dirs[i], direction)
                
            for i in range(8):
                idx = 9 + (i * 2)
                low, high = data[idx], data[idx+1]
                val = (high << 16) | low
                if val > 0x7FFFFFFF: val -= 0x100000000
                real_val = val / 1000.0
                self.edt_axis_strokes[i].setText(f"{real_val:.3f} mm")
                
            for i in range(8):
                val = data[25 + i]
                self.edt_axis_accels[i].setText(str(val))
        except Exception as e:
            print(f"Param Load Error: {e}")

    def _save_params(self):
        if not self.plc_client or not self.plc_client.is_connected:
            dlg = ConfirmOverlay("전송 실패", "PLC가 연결되어 있지 않습니다.", btn_yes="확인", parent=self.window())
            dlg.btn_cancel.hide(); dlg.exec(); return

        try:
            send_data = [0] * 50
            use_mask = 0
            
            # ★ 축 사용 여부 리스트 (settings.json 저장용)
            axis_uses_list = []
            
            for i in range(8):
                is_checked = self.chk_axis_uses[i].isChecked()
                axis_uses_list.append(is_checked)
                if is_checked: 
                    use_mask |= (1 << i)
            send_data[0] = use_mask
            
            for i in range(8):
                send_data[1 + i] = self.btn_axis_dirs[i].property("dir_value")
                
            for i in range(8):
                text = self.edt_axis_strokes[i].text().replace(" mm", "").strip()
                try: val_float = float(text)
                except: val_float = 0.0
                val = int(val_float * 1000)
                low, high = val & 0xFFFF, (val >> 16) & 0xFFFF
                idx = 9 + (i * 2)
                send_data[idx] = low; send_data[idx+1] = high
                
            for i in range(8):
                try: val = int(self.edt_axis_accels[i].text())
                except: val = 100
                send_data[25 + i] = val
                
            # PLC에 전송
            self.plc_client.write_words(0x09, self.plc_client.AXIS_PARAM_ADDR, send_data)
            
            # ★ settings.json에 축 설정 저장
            self._save_axis_settings(axis_uses_list)
            
            dlg = ConfirmOverlay("적용 완료", "시스템 파라미터가 PLC와 파일에 저장되었습니다.", btn_yes="확인", parent=self.window())
            dlg.btn_cancel.hide(); dlg.exec()
            
        except Exception as e:
            dlg = ConfirmOverlay("오류", f"데이터 전송 중 오류가 발생했습니다.\n{e}", btn_yes="확인", parent=self.window())
            dlg.btn_cancel.hide(); dlg.exec()

    def _apply_io_names(self):
        if not IOManager: return
        new_inputs = [e.text() for e in self.input_edits]
        new_outputs = [e.text() for e in self.output_edits]
        IOManager.instance().update_names(new_inputs, new_outputs)

        # IO 출력 이름 → 밸브 이름 역방향 동기화 후 settings.json 자동 저장
        for i in range(min(len(new_outputs), len(self.valve_name_edits))):
            self.valve_name_edits[i].setText(new_outputs[i])
        self._save_valve_config_silent()

        # 입력 이름을 settings.json에 저장
        try:
            path = _get_settings_path()
            settings = load_json(path) or {}
            settings["io_input_names"] = new_inputs
            save_json(path, settings)
            print("[Settings] IO 입력 이름 저장 완료")
        except Exception as e:
            print(f"[Settings] IO 입력 이름 저장 실패: {e}")

        dlg = ConfirmOverlay("적용 완료", "I/O 이름이 적용되었습니다.", btn_yes="확인", parent=self.window())
        dlg.btn_cancel.hide(); dlg.exec()

    def _load_io_input_names(self):
        """settings.json에서 입력 이름 로드 후 IOManager 및 편집창에 반영.
        저장값 없으면 DEFAULT_INPUTS를 그대로 적용."""
        from utils.io_manager import DEFAULT_INPUTS
        try:
            saved = []
            path = _get_settings_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                saved = settings.get("io_input_names", [])

            names = list(DEFAULT_INPUTS)  # 기본값으로 시작
            for i in range(min(len(saved), 32)):
                names[i] = saved[i]       # 저장된 값으로 덮어쓰기

            if IOManager:
                mgr = IOManager.instance()
                for i in range(32):
                    mgr.inputs[i] = names[i]
                    if i < len(self.input_edits):
                        self.input_edits[i].setText(names[i])
                mgr.sig_names_changed.emit()
            print("[Settings] IO 입력 이름 로드 완료")
        except Exception as e:
            print(f"[Settings] IO 입력 이름 로드 실패: {e}")

    def _on_manager_changed(self):
        if not IOManager: return
        mgr = IOManager.instance()
        for i, edit in enumerate(self.input_edits): edit.setText(mgr.get_input_name(i))
        for i, edit in enumerate(self.output_edits): edit.setText(mgr.get_output_name(i))

    def update_language(self, lang_code=None):
        if not LanguageManager: return
        lm = LanguageManager.instance()
        self.tabs.setTabText(0, "일반 설정")
        self.tabs.setTabText(1, "IO 이름 변경")
        self.tabs.setTabText(2, "시스템 파라미터")
        self.grp_plc.setTitle("PLC 통신 설정") 
        self.grp_env.setTitle("환경 설정")
        self.lbl_lang.setText("언어 (Language)")
        self.lbl_sys_info.setText("시스템")
        self.btn_exit.setText("종료")
        self.io_info_lbl.setText("※ 변경 후 [이름 적용] 버튼을 눌러야 저장됩니다.")
        self.lbl_table_header_in.setText("입력 (Input) 이름")
        self.lbl_table_header_out.setText("출력 (Output) 이름")
        self.btn_io_save.setText("이름 적용")
        self._update_lang_buttons(lm.current_lang)

    def _set_language(self, code):
        if not LanguageManager: return
        LanguageManager.instance().set_language(code)
        self._update_lang_buttons(code); self.update_language()

    def _update_lang_buttons(self, code):
        active = "QPushButton { border-radius: 20px; font-size: 13px; font-weight: bold; border: 2px solid #468CFF; background: rgba(70, 140, 255, 0.2); color: #468CFF; }"
        inactive = "QPushButton { border-radius: 20px; font-size: 13px; font-weight: bold; border: 2px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05); color: #AAA; }"
        if code == "KR": self.btn_lang_kr.setStyleSheet(active); self.btn_lang_en.setStyleSheet(inactive)
        else: self.btn_lang_kr.setStyleSheet(inactive); self.btn_lang_en.setStyleSheet(active)

    def _on_exit_clicked(self):
        dlg = ConfirmOverlay("프로그램 종료", "정말로 프로그램을 종료하시겠습니까?", btn_yes="종료", btn_no="취소", parent=self.window())
        if dlg.exec(): QApplication.instance().quit()

    def _on_connect_clicked(self):
        if not self.plc_client: return
        if self.plc_client.is_connected: self.plc_client.disconnect_plc()
        else:
            ip = self.edit_ip.text().strip(); port = self.edit_port.text().strip()
            if not ip or not port: return
            self._save_plc_settings(ip, port)
            self.lbl_status.setText("● Connecting..."); self.lbl_status.setStyleSheet("color: orange; font-size: 14px; font-weight: bold; margin-left: 5px;")
            QApplication.instance().processEvents()
            ok, msg = self.plc_client.connect_to_plc(ip, port)
            if not ok:
                dlg = ConfirmOverlay("접속 실패", f"PLC에 접속할 수 없습니다.\n({msg})", btn_yes="확인", parent=self.window())
                dlg.btn_cancel.hide(); dlg.exec()

    def _on_plc_status_changed(self, connected):
        if connected:
            self.btn_connect.setText("해제"); self.btn_connect.setStyleSheet("QPushButton { background: rgba(255, 70, 70, 0.15); border: 1px solid #FF4646; color: #FF4646; border-radius: 6px; font-weight: bold; font-size: 14px;} QPushButton:hover { background: rgba(255, 70, 70, 0.25); }")
            self.lbl_status.setText("● Connected"); self.lbl_status.setStyleSheet("color: #00FF00; font-size: 14px; font-weight: bold; margin-left: 5px;")
            self.edit_ip.setEnabled(False); self.edit_port.setEnabled(False)
            if self.tabs.currentWidget() == self.tab_param: self._load_params()
        else:
            self.btn_connect.setText("연결"); self.btn_connect.setStyleSheet("QPushButton { background: rgba(0, 255, 0, 0.15); border: 1px solid #00FF00; color: #00FF00; border-radius: 6px; font-weight: bold; font-size: 14px;} QPushButton:hover { background: rgba(0, 255, 0, 0.25); }")
            self.lbl_status.setText("● Disconnected"); self.lbl_status.setStyleSheet("color: #FF4646; font-size: 14px; font-weight: bold; margin-left: 5px;")
            self.edit_ip.setEnabled(True); self.edit_port.setEnabled(True)

    def _save_plc_settings(self, ip, port):
        try:
            path = _get_settings_path()
            settings = load_json(path) or {}
            settings["plc_ip"] = ip
            settings["plc_port"] = port
            save_json(path, settings)
        except Exception as e:
            print(f"Settings Save Error: {e}")

    def _load_plc_settings(self):
        try:
            settings = load_json(_get_settings_path()) or {}
            self.edit_ip.setText(settings.get("plc_ip", "192.168.0.10"))
            self.edit_port.setText(settings.get("plc_port", "9094"))
        except Exception as e:
            print(f"[Settings] PLC 설정 로드 실패: {e}")
    
    # =========================================================
    # ★ [신규] 축 설정 저장/로드 (settings.json)
    # =========================================================
    
    def _save_axis_settings(self, axis_uses_list):
        """
        축 사용 여부를 settings.json에 저장
        axis_uses_list: [True, True, True, False, False, ...] (8개)
        """
        try:
            path = _get_settings_path()
            settings = load_json(path) or {}
            settings["axis_uses"] = axis_uses_list
            save_json(path, settings)
            print(f"[Settings] 축 설정 저장 완료: {axis_uses_list}")
            
        except Exception as e:
            print(f"[Settings] 축 설정 저장 실패: {e}")
    
    def _load_axis_settings(self):
        """
        settings.json에서 축 사용 여부 로드
        반환: [True, True, True, False, ...] 또는 None
        """
        try:
            path = _get_settings_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    axis_uses = settings.get("axis_uses", None)
                    
                    if axis_uses and len(axis_uses) == 8:
                        print(f"[Settings] 축 설정 로드 완료: {axis_uses}")
                        return axis_uses
        except Exception as e:
            print(f"[Settings] 축 설정 로드 실패: {e}")
        
        # 기본값: 전축 활성화
        return [True] * 8
    def _init_interlock_tab(self):
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
        layout = QVBoxLayout(self.tab_interlock)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        lbl = QLabel("모드 인터록 설정")
        lbl.setStyleSheet("color: #00E5FF; font-size: 18px; font-weight: bold;")
        layout.addWidget(lbl)

        desc = QLabel(
            "• 배타(⊗): 같은 그룹에서 하나를 켜면 나머지가 자동으로 꺼집니다.\n"
            "• 필수(★): 같은 그룹에서 마지막 하나는 끌 수 없습니다.\n"
            "• 두 옵션은 독립적으로 설정할 수 있습니다."
        )
        desc.setStyleSheet("color: #9CA3AF; font-size: 14px; line-height: 1.6;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #374151;")
        layout.addWidget(sep)

        btn = QPushButton("인터록 그룹 설정 열기")
        btn.setFixedHeight(55)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(0,229,255,0.1); border: 2px solid #00E5FF;
                border-radius: 10px; color: #00E5FF; font-size: 17px; font-weight: bold;
            }
            QPushButton:pressed { background: rgba(0,229,255,0.3); }
        """)
        btn.clicked.connect(self._open_interlock_dialog)
        layout.addWidget(btn)
        layout.addStretch(1)

    def _open_interlock_dialog(self):
        try:
            from ui.pages.page_mode import InterlockDialog, TOTAL_SLOTS
        except ImportError:
            return

        _GROUP_COLORS = [
            None, "#E74C3C", "#3498DB", "#2ECC71", "#F39C12",
            "#9B59B6", "#1ABC9C", "#E67E22", "#E91E63",
        ]

        def _load():
            try:
                with open(_get_settings_path(), "r", encoding="utf-8") as f:
                    d = json.load(f)
                g = d.get("interlock_groups", [0]*TOTAL_SLOTS)
                m = d.get("interlock_mandatory", [False]*9)
                e = d.get("interlock_exclusive", [True]*9)
                if len(g) < TOTAL_SLOTS: g += [0]*(TOTAL_SLOTS-len(g))
                if len(m) < 9: m += [False]*(9-len(m))
                if len(e) < 9: e += [True]*(9-len(e))
                return g[:TOTAL_SLOTS], m[:9], e[:9]
            except Exception:
                return [0]*TOTAL_SLOTS, [False]*9, [True]*9

        def _get_mode_name(idx):
            default = [
                "제품측 취출","런너측 취출","주행 대기","하강 대기","주행도중개방","복귀도중개방",
                "안전도어 회피","안전도어 회피2","낙하측 반전","주행도중 반전","취출대기 반전",
                "고정측 취출","제품 형내개방","런너 형내개방","에젝터 연동","언더컷 취출모드",
                "척1 사용","척1 감지","척2 사용","척2 감지","척3 사용","척3 감지",
                "척4 사용","척4 감지","흡착1 사용","흡착1 감지","흡착2 사용","흡착2 감지",
                "흡착3 사용","흡착3 감지","흡착4 사용","흡착4 감지","2포인트 개방","공정감시 모드",
            ]
            try:
                from utils.mode_manager import ModeManager
                mgr = ModeManager.instance()
                if mgr: return mgr.get_name(idx)
            except Exception:
                pass
            return default[idx] if idx < len(default) else f"User Mode {idx-33}"

        groups, mandatory, exclusive = _load()
        dlg = InterlockDialog(groups, mandatory, exclusive, _get_mode_name, _GROUP_COLORS, parent=self)
        if dlg.exec() == QDialog.Accepted:
            path = _get_settings_path()
            data = load_json(path) or {}
            data["interlock_groups"] = dlg.get_groups()
            data["interlock_mandatory"] = dlg.get_mandatory()
            data["interlock_exclusive"] = dlg.get_exclusive()
            save_json(path, data)
