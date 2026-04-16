import json
import os
import sys
from utils.json_utils import load_json, save_json
from PySide6.QtCore import Qt, QTimer, Signal
from utils.paths import get_settings_path as _get_settings_path
from PySide6.QtWidgets import (
    QGridLayout, QPushButton, QSizePolicy,
    QScrollArea, QWidget, QVBoxLayout, QScroller, QLabel,
    QDialog, QLineEdit, QHBoxLayout, QFrame
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

        # 인터록 그룹 로드
        self.interlock_groups, self.interlock_mandatory, self.interlock_exclusive = self._load_interlock_groups()

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

        grp = self.interlock_groups[idx] if idx < len(self.interlock_groups) else 0
        if grp > 0:
            is_mandatory = self.interlock_mandatory[grp] if grp < len(self.interlock_mandatory) else False
            if not checked and is_mandatory:
                # 필수 그룹: 마지막 하나면 끄기 차단
                on_count = sum(1 for i, g in enumerate(self.interlock_groups) if g == grp and self.mode_data[i])
                if on_count == 0:  # 이미 꺼진 상태에서 신호 → 원복
                    button.blockSignals(True)
                    button.setChecked(True)
                    button.blockSignals(False)
                    self.mode_data[idx] = True
                    button.inner_label.setText(self._format_text(self._get_mode_name(idx), True))
                    return
            is_exclusive = self.interlock_exclusive[grp] if grp < len(self.interlock_exclusive) else False
            if checked and is_exclusive:
                # 배타: 같은 그룹 나머지 OFF
                for other_idx, btn in enumerate(self.buttons):
                    if other_idx == idx: continue
                    other_grp = self.interlock_groups[other_idx] if other_idx < len(self.interlock_groups) else 0
                    if other_grp == grp and self.mode_data[other_idx]:
                        btn.blockSignals(True)
                        btn.setChecked(False)
                        btn.blockSignals(False)
                        self.mode_data[other_idx] = False
                        btn.inner_label.setText(self._format_text(self._get_mode_name(other_idx), False))

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

    # =========================================================
    # 인터록 설정
    # =========================================================
    _SETTINGS_PATH = _get_settings_path()
    # 그룹별 색상 (그룹 1~8)
    _GROUP_COLORS = [
        None,               # 0 = 없음
        "#E74C3C",          # 1 = 빨강
        "#3498DB",          # 2 = 파랑
        "#2ECC71",          # 3 = 초록
        "#F39C12",          # 4 = 주황
        "#9B59B6",          # 5 = 보라
        "#1ABC9C",          # 6 = 청록
        "#E67E22",          # 7 = 진주황
        "#E91E63",          # 8 = 핑크
    ]

    def _load_interlock_groups(self):
        try:
            with open(self._SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            groups = data.get("interlock_groups", [0] * TOTAL_SLOTS)
            if len(groups) < TOTAL_SLOTS:
                groups += [0] * (TOTAL_SLOTS - len(groups))
            mandatory = data.get("interlock_mandatory", [False] * 9)
            if len(mandatory) < 9:
                mandatory += [False] * (9 - len(mandatory))
            # exclusive: 하위호환 - 기존 데이터 없으면 모든 그룹을 배타로 간주
            exclusive = data.get("interlock_exclusive", [True] * 9)
            if len(exclusive) < 9:
                exclusive += [True] * (9 - len(exclusive))
            return groups[:TOTAL_SLOTS], mandatory[:9], exclusive[:9]
        except Exception:
            return [0] * TOTAL_SLOTS, [False] * 9, [True] * 9

    def _save_interlock_groups(self):
        try:
            data = load_json(self._SETTINGS_PATH) or {}
            data["interlock_groups"] = self.interlock_groups
            data["interlock_mandatory"] = self.interlock_mandatory
            data["interlock_exclusive"] = self.interlock_exclusive
            save_json(self._SETTINGS_PATH, data)
        except Exception as e:
            print(f"[인터록] 저장 실패: {e}")

    def _open_interlock_dialog(self):
        dlg = InterlockDialog(
            self.interlock_groups[:],
            self.interlock_mandatory[:],
            self.interlock_exclusive[:],
            self._get_mode_name,
            self._GROUP_COLORS,
            parent=self
        )
        if dlg.exec() == QDialog.Accepted:
            self.interlock_groups = dlg.get_groups()
            self.interlock_mandatory = dlg.get_mandatory()
            self.interlock_exclusive = dlg.get_exclusive()
            self._save_interlock_groups()

    def showEvent(self, event):
        # 설정 페이지에서 인터록 변경 시 반영
        self.interlock_groups, self.interlock_mandatory, self.interlock_exclusive = self._load_interlock_groups()
        super().showEvent(event)

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

# =========================================================
# [다이얼로그] 인터록 그룹 설정
# =========================================================
class InterlockDialog(QDialog):
    def __init__(self, groups, mandatory, exclusive, get_name_fn, group_colors, parent=None):
        super().__init__(parent)
        self.setWindowState(Qt.WindowFullScreen)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self._groups = groups[:]
        self._mandatory = mandatory[:]    # [False, bool×8]  index 0 미사용
        self._exclusive = exclusive[:]    # [True,  bool×8]  index 0 미사용
        self._get_name = get_name_fn
        self._colors = group_colors
        self._max_group = len(group_colors) - 1  # 8

        self.setStyleSheet("background: #111827; color: white;")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        # ── 헤더 ──
        hdr = QHBoxLayout()
        title = QLabel("인터록 그룹 설정")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00E5FF;")
        hdr.addWidget(title)
        hdr.addStretch(1)

        hdr.addSpacing(20)
        btn_clear = QPushButton("전체 해제")
        btn_clear.setFixedHeight(34)
        btn_clear.setStyleSheet(
            "QPushButton { background: rgba(255,70,70,0.2); border: 1px solid #FF4646; "
            "border-radius: 6px; color: #FF4646; font-size: 13px; font-weight: bold; padding: 0 12px; }"
            "QPushButton:pressed { background: rgba(255,70,70,0.4); }")
        btn_clear.clicked.connect(self._clear_all)
        hdr.addWidget(btn_clear)
        root.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #374151;"); root.addWidget(sep)

        # ── 그룹 옵션 카드 행 ──
        cards_bar = QHBoxLayout()
        cards_bar.setSpacing(8)
        self._mandatory_btns = [None]
        self._exclusive_btns = [None]
        for g in range(1, self._max_group + 1):
            c = self._colors[g]
            card = QFrame()
            card.setStyleSheet(f"QFrame {{ background: {c}22; border: 1px solid {c}66; border-radius: 8px; }}")
            card.setFixedWidth(108)
            cv = QVBoxLayout(card)
            cv.setContentsMargins(6, 6, 6, 6)
            cv.setSpacing(4)

            lbl = QLabel(f"G{g}")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"background: {c}; color: white; font-size: 15px; font-weight: bold; "
                              f"border-radius: 5px; padding: 2px 0; border: none;")
            cv.addWidget(lbl)

            # 배타 토글
            btn_ex = QPushButton("배타 OFF")
            btn_ex.setFixedHeight(30)
            btn_ex.setCheckable(True)
            btn_ex.setChecked(self._exclusive[g])
            btn_ex.clicked.connect(lambda checked, gi=g: self._toggle_exclusive(gi, checked))
            self._exclusive_btns.append(btn_ex)
            cv.addWidget(btn_ex)

            # 필수 토글
            btn_mn = QPushButton("필수 OFF")
            btn_mn.setFixedHeight(30)
            btn_mn.setCheckable(True)
            btn_mn.setChecked(self._mandatory[g])
            btn_mn.clicked.connect(lambda checked, gi=g: self._toggle_mandatory(gi, checked))
            self._mandatory_btns.append(btn_mn)
            cv.addWidget(btn_mn)

            cards_bar.addWidget(card)
            self._refresh_exclusive_btn(g)
            self._refresh_mandatory_btn(g)

        cards_bar.addStretch(1)
        root.addLayout(cards_bar)

        # ── 안내 ──
        hint = QLabel("모드 버튼을 탭하면 그룹 순환 (없음 → G1 → G2 → … → G8 → 없음).  배타: 하나 ON 시 나머지 자동 OFF.  필수: 마지막 하나는 끌 수 없음.")
        hint.setStyleSheet("color: #9CA3AF; font-size: 13px;")
        root.addWidget(hint)

        # ── 모드 그리드 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)

        grid_w = QWidget(); grid_w.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_w)
        grid.setHorizontalSpacing(10); grid.setVerticalSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)

        self._btns = []
        cols = 4
        for i in range(TOTAL_SLOTS):
            btn = QPushButton()
            btn.setMinimumHeight(68)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _, idx=i: self._cycle_group(idx))
            self._btns.append(btn)
            grid.addWidget(btn, i // cols, i % cols)
        for c in range(cols):
            grid.setColumnStretch(c, 1)

        scroll.setWidget(grid_w)
        root.addWidget(scroll, 1)

        # ── 하단 버튼 ──
        foot = QHBoxLayout()
        btn_cancel = QPushButton("취소")
        btn_cancel.setFixedHeight(46)
        btn_cancel.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.08); border: 1px solid #555; "
            "border-radius: 8px; color: #CCC; font-size: 16px; font-weight: bold; }"
            "QPushButton:pressed { background: rgba(255,255,255,0.2); }")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("저장")
        btn_ok.setFixedHeight(46)
        btn_ok.setStyleSheet(
            "QPushButton { background: rgba(0,229,255,0.15); border: 1px solid #00E5FF; "
            "border-radius: 8px; color: #00E5FF; font-size: 16px; font-weight: bold; }"
            "QPushButton:pressed { background: rgba(0,229,255,0.35); }")
        btn_ok.clicked.connect(self.accept)

        foot.addWidget(btn_cancel); foot.addWidget(btn_ok)
        root.addLayout(foot)

        self._refresh_all()

    def _refresh_mandatory_btn(self, g):
        btn = self._mandatory_btns[g]
        c = self._colors[g]
        is_on = self._mandatory[g]
        if is_on:
            btn.setText("필수 ON ★")
            btn.setStyleSheet(
                f"QPushButton {{ background: {c}; border: none; border-radius: 5px; "
                f"color: white; font-size: 12px; font-weight: bold; }}"
                f"QPushButton:pressed {{ background: {c}CC; }}"
            )
        else:
            btn.setText("필수 OFF")
            btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.08); border: 1px solid #555; border-radius: 5px; "
                "color: #777; font-size: 12px; font-weight: bold; }"
                "QPushButton:pressed { background: rgba(255,255,255,0.18); }"
            )

    def _toggle_mandatory(self, g, checked):
        self._mandatory[g] = checked
        self._refresh_mandatory_btn(g)

    def _refresh_exclusive_btn(self, g):
        btn = self._exclusive_btns[g]
        c = self._colors[g]
        is_on = self._exclusive[g]
        if is_on:
            btn.setText("배타 ON ⊗")
            btn.setStyleSheet(
                f"QPushButton {{ background: {c}; border: none; border-radius: 5px; "
                f"color: white; font-size: 12px; font-weight: bold; }}"
                f"QPushButton:pressed {{ background: {c}CC; }}"
            )
        else:
            btn.setText("배타 OFF")
            btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.08); border: 1px solid #555; border-radius: 5px; "
                "color: #777; font-size: 12px; font-weight: bold; }"
                "QPushButton:pressed { background: rgba(255,255,255,0.18); }"
            )

    def _toggle_exclusive(self, g, checked):
        self._exclusive[g] = checked
        self._refresh_exclusive_btn(g)
        self._refresh_all()  # 모드 버튼 suffix 갱신

    def _refresh_all(self):
        for i, btn in enumerate(self._btns):
            self._refresh_btn(i, btn)

    def _refresh_btn(self, idx, btn):
        grp = self._groups[idx]
        name = self._get_name(idx)
        if grp > 0:
            tags = []
            if self._exclusive[grp]: tags.append("⊗")
            if self._mandatory[grp]: tags.append("★")
            suffix = " " + "".join(tags) if tags else ""
        else:
            suffix = ""
        if grp == 0:
            btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.15); "
                "border-radius: 8px; color: #9CA3AF; font-size: 13px; font-weight: bold; }"
                "QPushButton:pressed { background: rgba(255,255,255,0.15); }"
            )
            btn.setText(f"{name}\n—")
        else:
            c = self._colors[grp]
            btn.setStyleSheet(
                f"QPushButton {{ background: {c}33; border: 2px solid {c}; "
                f"border-radius: 8px; color: {c}; font-size: 13px; font-weight: bold; }}"
                f"QPushButton:pressed {{ background: {c}66; }}"
            )
            btn.setText(f"{name}\nG{grp}{suffix}")

    def _cycle_group(self, idx):
        self._groups[idx] = (self._groups[idx] + 1) % (self._max_group + 1)
        self._refresh_btn(idx, self._btns[idx])

    def _clear_all(self):
        self._groups = [0] * TOTAL_SLOTS
        self._refresh_all()

    def get_groups(self):
        return self._groups[:]

    def get_mandatory(self):
        return self._mandatory[:]

    def get_exclusive(self):
        return self._exclusive[:]
