from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QGridLayout, QPushButton, QSizePolicy,
    QScrollArea, QWidget, QVBoxLayout, QScroller, QLabel,
    QDialog, QLineEdit, QHBoxLayout
)
from widgets.glass_card import GlassCard

# 모듈 임포트
try:
    from widgets.touch_keyboard import TouchKeyboard
except ImportError:
    TouchKeyboard = None

try:
    from utils.languages import LanguageManager
except ImportError:
    LanguageManager = None

try:
    from utils.mode_manager import ModeManager
except ImportError:
    ModeManager = None

# [상수] 기본 모드 키값 목록 (0~33번)
DEFAULT_MODE_KEYS = [
    "mode_prod_takeout", "mode_runner_takeout", "mode_wait_move", "mode_wait_down",
    "mode_open_move", "mode_open_ret", "mode_safety_1", "mode_safety_2",
    "mode_inv_drop", "mode_inv_move", "mode_inv_wait", "mode_fix_side",
    "mode_open_prod", "mode_open_run", "mode_eject_link", "mode_undercut",
    "mode_chuck1_use", "mode_chuck1_sens", "mode_chuck2_use", "mode_chuck2_sens",
    "mode_chuck3_use", "mode_chuck3_sens", "mode_chuck4_use", "mode_chuck4_sens",
    "mode_vac1_use", "mode_vac1_sens", "mode_vac2_use", "mode_vac2_sens",
    "mode_vac3_use", "mode_vac3_sens", "mode_vac4_use", "mode_vac4_sens",
    "mode_2point_open", "mode_process_mon"
]

# [백업용] 기본 한글 이름
DEFAULT_KOREAN_NAMES = [
    "제품측 취출", "런너측 취출", "주행 대기", "하강 대기",
    "주행도중개방", "복귀도중개방", "안전도어 회피", "안전도어 회피2",
    "낙하측 반전", "주행도중 반전", "취출대기 반전", "고정측 취출",
    "제품 형내개방", "런너 형내개방", "에젝터 연동", "언더컷 취출모드",
    "척1 사용", "척1 감지", "척2 사용", "척2 감지",
    "척3 사용", "척3 감지", "척4 사용", "척4 감지",
    "흡착1 사용", "흡착1 감지", "흡착2 사용", "흡착2 감지",
    "흡착3 사용", "흡착3 감지", "흡착4 사용", "흡착4 감지",
    "2포인트 개방", "공정감시 모드",
]

# 전체 슬롯 개수 (기본 34개 + 사용자 모드 10개 = 44개)
TOTAL_SLOTS = 44
USER_MODE_START_IDX = 34

# =========================================================
# [커스텀 위젯] 롱 프레스(꾹 누르기) 감지 버튼
# =========================================================
class LongPressButton(QPushButton):
    sig_long_press = Signal(int)

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self._timer = QTimer(self)
        self._timer.setInterval(800)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_long_press)
        self._is_long_pressed = False

    def mousePressEvent(self, e):
        self._is_long_pressed = False
        self._timer.start()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._timer.stop()
        if not self._is_long_pressed:
            super().mouseReleaseEvent(e)

    def _on_long_press(self):
        self._is_long_pressed = True
        self.sig_long_press.emit(self.index)


# =========================================================
# [페이지] 동작 모드
# =========================================================
class PageMode(GlassCard):
    def __init__(self, mode_data=None, plc_client=None):
        # [수정] 타이틀 제거 (빈 문자열 전달)
        super().__init__("")
        self.plc_client = plc_client

        # [수정] GlassCard 헤더 숨기기 및 여백 최소화
        if hasattr(self, 'title_label'):
            self.title_label.hide()
            if self.title_label.parentWidget() and self.title_label.parentWidget() != self:
                self.title_label.parentWidget().hide()

        if self.layout():
            self.layout().setContentsMargins(10, 5, 10, 10)

        # 1. 데이터 연동
        if mode_data is not None:
            self.mode_data = mode_data
        else:
            self.mode_data = []

        current_len = len(self.mode_data)
        if current_len < TOTAL_SLOTS:
            self.mode_data.extend([False] * (TOTAL_SLOTS - current_len))

        # ===== Scroll Area =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        scroll.setWidget(container)

        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setContentsMargins(10, 5, 10, 10) # 상단 여백 줄임

        outer.addLayout(grid)
        outer.addStretch(1)

        self.buttons = []
        cols = 4
        
        for i in range(TOTAL_SLOTS):
            r = i // cols
            c = i % cols

            if i >= USER_MODE_START_IDX:
                btn = LongPressButton(index=i)
                btn.sig_long_press.connect(self._on_btn_long_pressed)
            else:
                btn = QPushButton()

            btn.setCheckable(True)
            btn.setProperty("class", "ModeTileBtn")
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(80) 

            btn_layout = QVBoxLayout(btn)
            btn_layout.setContentsMargins(0,0,0,0)
            btn_layout.setSpacing(0)
            
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setTextFormat(Qt.RichText)
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            lbl.setStyleSheet("background: transparent; border: none;")
            
            btn.inner_label = lbl 
            btn_layout.addWidget(lbl)

            btn.setStyleSheet(self._get_btn_stylesheet(i >= USER_MODE_START_IDX))

            is_on = self.mode_data[i]
            btn.setChecked(is_on)
            
            name = self._get_mode_name(i)
            lbl.setText(self._format_text(name, is_on))
            
            btn.toggled.connect(lambda checked, idx=i, b=btn: self._on_toggled(idx, b, checked))
            
            self.buttons.append(btn)
            grid.addWidget(btn, r, c)

        for c in range(cols):
            grid.setColumnStretch(c, 1)

        self.body.addWidget(scroll, 1)

        if ModeManager:
            ModeManager.instance().sig_names_changed.connect(self.refresh_ui)
        
        self.refresh_ui()

    def _get_btn_stylesheet(self, is_user_mode):
        border_color = "rgba(255, 215, 0, 0.3)" if is_user_mode else "rgba(255, 255, 255, 0.1)"
        return f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QPushButton:checked {{
                background: rgba(70, 140, 255, 0.15);
                border: 1px solid #468CFF;
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 0.1);
            }}
        """

    def _get_mode_name(self, idx):
        # 1. 사용자 모드
        if idx >= USER_MODE_START_IDX:
            if ModeManager:
                return ModeManager.instance().get_name(idx)
            return f"User Mode {idx - USER_MODE_START_IDX + 1}"
        
        # 2. 기본 모드
        if idx < len(DEFAULT_MODE_KEYS):
            key = DEFAULT_MODE_KEYS[idx]
            default_kr = DEFAULT_KOREAN_NAMES[idx] if idx < len(DEFAULT_KOREAN_NAMES) else key
            
            if LanguageManager:
                val = LanguageManager.instance().get_text(key)
                if val and val != key:
                    return val
            return default_kr
            
        return "Unknown"

    def _format_text(self, name: str, checked: bool) -> str:
        state_text = "ON" if checked else "OFF"
        color = "#00FF00" if checked else "#999999"
        name_color = "#E0E0E0" if checked else "#CCCCCC"
        
        return (f"<html><head/><body><p align='center'>"
                f"<span style='font-size:16px; font-weight:bold; color:{name_color};'>{name}</span><br>"
                f"<span style='font-size:20px; font-weight:bold; color:{color};'>{state_text}</span>"
                f"</p></body></html>")

    def _on_toggled(self, idx: int, button: QPushButton, checked: bool):
        self.mode_data[idx] = checked
        name = self._get_mode_name(idx)
        button.inner_label.setText(self._format_text(name, checked))
        if self.plc_client and self.plc_client.is_connected:
            self.plc_client.send_mode_settings(self.mode_data)

    def _on_btn_long_pressed(self, idx):
        if not ModeManager: return
        if not TouchKeyboard: return
        
        current_name = ModeManager.instance().get_name(idx)
        
        dlg = TouchKeyboard("사용자 모드 이름 변경", parent=self)
        
        # 키보드 언어 설정
        if hasattr(dlg, "set_language"):
            dlg.set_language("EN")
        elif hasattr(dlg, "set_layout"):
            dlg.set_layout("EN")
        
        # 초기 텍스트 설정
        if hasattr(dlg, "set_text"):
            dlg.set_text(current_name)
        elif hasattr(dlg, "set_initial_text"):
            dlg.set_initial_text(current_name)
        elif hasattr(dlg, "input_field"):
            dlg.input_field.setText(current_name)
            
        if dlg.exec() == QDialog.Accepted:
            new_name = dlg.get_text()
            ModeManager.instance().set_name(idx, new_name)

    def update_language(self, lang_code=None):
        # [수정] 타이틀 업데이트 로직 제거 (타이틀이 없으므로)
        self.refresh_ui()

    def refresh_ui(self):
        for i, btn in enumerate(self.buttons):
            if i < len(self.mode_data):
                is_on = self.mode_data[i]
                btn.blockSignals(True)
                btn.setChecked(is_on)
                btn.blockSignals(False)
                
                name = self._get_mode_name(i)
                btn.inner_label.setText(self._format_text(name, is_on))