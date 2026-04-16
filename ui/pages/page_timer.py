from PySide6.QtCore import Qt, QEventLoop, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QGridLayout, QFrame, QSizePolicy,
    QScroller, QScrollerProperties, QApplication, QInputDialog, QDialog
)

from widgets.glass_card import GlassCard

try:
    from widgets.touch_keyboard import TouchKeyboard
except ImportError:
    TouchKeyboard = None

try:
    from ui.dialogs.sequence_utils import NumericKeypad, DarkConfirmDialog, TimerReorderDialog
except ImportError:
    NumericKeypad = None
    DarkConfirmDialog = None
    TimerReorderDialog = None


# ==========================================================
# [팝업] 타이머 시간 수정 다이얼로그 (오버레이 방식)
# ==========================================================
class TimerEditDialog(QWidget):
    Accepted = 1
    Rejected = 0

    def __init__(self, timer_name, current_val_ms, parent=None):
        super().__init__(parent)
        if parent:
            self.resize(parent.size())
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)

        self.current_ms = int(current_val_ms)
        self.result_code = self.Rejected
        self._event_loop = None

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        self.container = QFrame()
        self.container.setFixedSize(350, 320)
        self.container.setStyleSheet("""
            QFrame {
                background-color: #1A1F2B;
                border: 2px solid #468CFF;
                border-radius: 12px;
            }
            QLabel {
                background-color: transparent;
                border: none;
                color: #EEE;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton {
                border-radius: 8px;
                font-weight: bold;
                font-size: 16px;
                background-color: #34495E;
                color: white;
                border: none;
            }
        """)

        box_layout = QVBoxLayout(self.container)
        box_layout.setSpacing(15)
        box_layout.setContentsMargins(20, 20, 20, 20)

        lbl_name_display = QLabel(timer_name)
        lbl_name_display.setAlignment(Qt.AlignCenter)
        lbl_name_display.setStyleSheet("color: #FFD700; font-size: 22px; font-weight: 900; margin-bottom: 5px;")
        box_layout.addWidget(lbl_name_display)

        lbl_title = QLabel("설정 시간 변경 (초)")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color: #AAA; font-size: 14px;")
        box_layout.addWidget(lbl_title)

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

        box_layout.addLayout(val_layout)

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
        box_layout.addLayout(btn_layout)

        main_layout.addWidget(self.container)
        self._update_display()

    def exec(self):
        self.show()
        self.raise_()
        self._event_loop = QEventLoop()
        self._event_loop.exec()
        self.hide()
        self.deleteLater()
        return self.result_code

    def accept(self):
        self.result_code = self.Accepted
        if self._event_loop:
            self._event_loop.quit()

    def reject(self):
        self.result_code = self.Rejected
        if self._event_loop:
            self._event_loop.quit()

    def _update_display(self):
        sec_val = self.current_ms / 100.0
        self.btn_val.setText(f"{sec_val:.1f}")

    def _open_keypad(self):
        if NumericKeypad:
            cur_sec = self.current_ms / 100.0
            dlg = NumericKeypad(f"{self.container.findChild(QLabel).text()} 시간(초)", cur_sec, 1, parent=self)
            if dlg.exec() == 1:
                try:
                    val = float(dlg.get_value())
                    self.current_ms = int(round(val * 100))
                    self._update_display()
                except (ValueError, TypeError):
                    pass
        else:
            cur_sec = self.current_ms / 100.0
            val, ok = QInputDialog.getDouble(self, "입력", "시간(초):", cur_sec, 0, 999, 1)
            if ok:
                self.current_ms = int(round(val * 100))
                self._update_display()

    def _increase(self):
        self.current_ms += 10
        self._update_display()

    def _decrease(self):
        if self.current_ms >= 10:
            self.current_ms -= 10
            self._update_display()

    def get_value_ms(self):
        return self.current_ms


# ==========================================================
# [페이지] 타이머 라이브러리 관리
# ==========================================================
class PageTimer(GlassCard):
    def __init__(self, sequence_data=None, timer_library=None, plc_client=None):
        super().__init__("")

        if hasattr(self, 'title_label'):
            self.title_label.hide()
            if self.title_label.parentWidget() and self.title_label.parentWidget() != self:
                self.title_label.parentWidget().hide()

        if self.layout():
            self.layout().setContentsMargins(10, 5, 10, 10)

        self.plc_client = plc_client
        self.sequence_data = sequence_data if sequence_data is not None else {}
        self.timer_library = timer_library if timer_library is not None else {}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        scroller = QScroller.scroller(scroll.viewport())
        props = scroller.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.MousePressEventDelay, 0)
        props.setScrollMetric(QScrollerProperties.DragStartDistance, 20)
        scroller.setScrollerProperties(props)

        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll = scroll

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        scroll.setWidget(self.container)

        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(0, 10, 0, 10)
        self.grid.setSpacing(10)
        self.grid.setAlignment(Qt.AlignTop)

        # 상단 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 4)
        btn_row.addStretch(1)

        self.btn_reorder = QPushButton("⇄ 순서 변경")
        self.btn_reorder.setFixedHeight(36)
        self.btn_reorder.setStyleSheet("""
            QPushButton {
                background: rgba(70,140,255,0.15);
                border: 1px solid rgba(70,140,255,0.5);
                border-radius: 8px;
                color: #7EB8FF;
                font-size: 14px;
                font-weight: bold;
                padding: 0 16px;
            }
            QPushButton:pressed { background: rgba(70,140,255,0.35); }
        """)
        self.btn_reorder.clicked.connect(self._on_reorder_clicked)
        btn_row.addWidget(self.btn_reorder)

        self.body.addLayout(btn_row)
        self.body.addWidget(scroll, 1)
        self._last_width = 0
        QTimer.singleShot(0, self.refresh_grid)

    def refresh_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        COLS = 6
        spacing = 10
        vp_w = self.scroll.viewport().width()
        if vp_w < 200:
            vp_w = self.width()
        if vp_w < 200:
            vp_w = 1000
        card_w = max(120, (vp_w - spacing * (COLS - 1)) // COLS)
        card_h = 100

        if not self.timer_library:
            lbl = QLabel("타이머가 없습니다.\n시퀀스 편집기 TMR 스텝에서 타이머를 추가하세요.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 16px;")
            self.grid.addWidget(lbl, 0, 0, 1, COLS)
            return

        for i, (name, time_sec) in enumerate(self.timer_library.items()):
            r = i // COLS
            c = i % COLS
            card = self._create_timer_card(name, float(time_sec), card_w, card_h)
            self.grid.addWidget(card, r, c)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.refresh_grid)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_w = event.size().width()
        if abs(new_w - self._last_width) > 10:
            self._last_width = new_w
            self.refresh_grid()

    def _create_timer_card(self, name, time_sec, card_w=130, card_h=110):
        frame = QFrame()
        frame.setFixedSize(card_w, card_h)
        frame.setStyleSheet("""
            QFrame {
                background-color: #1A222C;
                border: 1px solid #3E4A59;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # 상단 행: 이름
        lbl_name = QLabel(name)
        lbl_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl_name.setStyleSheet("color: #DDD; font-size: 17px; font-weight: bold; border: none; background: transparent;")
        lbl_name.setWordWrap(True)
        layout.addWidget(lbl_name)

        # 시간 값 (버튼 - 클릭 시 편집)
        btn_time = QPushButton(f"{time_sec:.1f}")
        btn_time.setFixedHeight(50)
        btn_time.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_time.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50;
                color: #FFFF00;
                font-size: 22px;
                font-weight: 900;
                border: 1px solid #3E4A59;
                border-radius: 6px;
                padding: 0 4px;
            }
            QPushButton:pressed {
                background-color: #34495E;
                border: 1px solid #468CFF;
            }
        """)
        btn_time.clicked.connect(lambda _, n=name, t=time_sec, b=btn_time: self._on_card_clicked(n, t, b))
        layout.addWidget(btn_time)

        lbl_unit = QLabel("SEC")
        lbl_unit.setFixedHeight(16)
        lbl_unit.setAlignment(Qt.AlignCenter)
        lbl_unit.setStyleSheet("color: #888; font-size: 11px; border: none; background: transparent;")
        layout.addWidget(lbl_unit)

        # 시간 버튼 참조 저장
        frame._btn_time_ref = btn_time
        frame._name_ref = name

        return frame

    def _on_card_clicked(self, name, time_sec, btn_widget):
        current_ms = int(time_sec * 100)
        dlg = TimerEditDialog(name, current_ms, self)
        if dlg.exec() == TimerEditDialog.Accepted:
            new_ms = dlg.get_value_ms()
            new_sec = new_ms / 100.0
            self.timer_library[name] = new_sec
            btn_widget.setText(f"{new_sec:.1f}")
            self._sync_steps_time(name, new_sec)
            print(f"[Timer Library] Updated '{name}': {new_sec} sec")

    def _sync_steps_time(self, timer_name, new_sec):
        """타이머 값 변경 시 해당 타이머를 참조하는 모든 시퀀스 스텝의 time 동기화 + PLC 패치"""
        # seq_map 빌드 (시퀀스편집기와 동일한 규칙)
        MONITOR_KEY = "Monitor"
        seq_map = {"Main": 0, MONITOR_KEY: 39}
        reserved = set(seq_map.keys())
        subs = sorted([k for k in self.sequence_data.keys() if k not in reserved])
        for i, k in enumerate(subs):
            seq_map[k] = i + 1

        plc = self.plc_client
        patch_count = 0

        for seq_name, steps in self.sequence_data.items():
            if not isinstance(steps, list):
                continue
            slot_id = seq_map.get(seq_name)
            for step_idx, step in enumerate(steps):
                if step.get("type") == "TMR" and step.get("timer_ref") == timer_name:
                    step["time"] = new_sec
                    if plc and getattr(plc, 'is_connected', False) and slot_id is not None:
                        plc.patch_tmr_step_time(slot_id, step_idx, new_sec)
                    patch_count += 1

        if patch_count:
            print(f"[Timer Library] Synced+Patched {patch_count} step(s) referencing '{timer_name}'")

    def _on_delete_timer(self, name):
        if DarkConfirmDialog:
            from PySide6.QtWidgets import QDialog as _QDialog
            dlg = DarkConfirmDialog(f"'{name}' 삭제", "타이머 라이브러리에서 삭제합니다.", self)
            if dlg.exec() != _QDialog.Accepted:
                return
        if name in self.timer_library:
            del self.timer_library[name]
            self.refresh_grid()
            print(f"[Timer Library] Deleted '{name}'")

    def _on_add_timer_clicked(self):
        # 1. 타이머 이름 입력
        timer_name = self._ask_timer_name()
        if not timer_name:
            return
        if timer_name in self.timer_library:
            # 이미 있으면 기존 항목 편집
            self._on_card_clicked(timer_name, self.timer_library[timer_name], None)
            return

        # 2. 시간 입력
        timer_sec = self._ask_timer_time(timer_name)
        if timer_sec is None:
            return

        self.timer_library[timer_name] = timer_sec
        self.refresh_grid()
        print(f"[Timer Library] Added '{timer_name}': {timer_sec} sec")

    def _ask_timer_name(self):
        """타이머 이름 입력 (텍스트 키보드 또는 폴백)"""
        if TouchKeyboard:
            dlg = TouchKeyboard("타이머 이름 입력", parent=self)
            if hasattr(dlg, 'set_language'):
                dlg.set_language("KO")
            from PySide6.QtWidgets import QDialog as _QDialog
            if dlg.exec() == _QDialog.Accepted:
                name = dlg.get_text().strip()
                return name if name else None
            return None
        else:
            name, ok = QInputDialog.getText(self, "타이머 추가", "타이머 이름:")
            return name.strip() if ok and name.strip() else None

    def _ask_timer_time(self, name):
        """타이머 시간 입력"""
        if NumericKeypad:
            dlg = NumericKeypad(f"'{name}' 시간 설정 (초)", 1.0, 1, parent=self)
            if dlg.exec() == 1:
                try:
                    return float(dlg.get_value())
                except (ValueError, TypeError):
                    return None
            return None
        else:
            val, ok = QInputDialog.getDouble(self, "시간 입력", "시간(초):", 1.0, 0, 999, 1)
            return val if ok else None

    def _on_reorder_clicked(self):
        """타이머 순서 변경 다이얼로그 열기"""
        if not self.timer_library:
            return
        if not TimerReorderDialog:
            return

        dlg = TimerReorderDialog(list(self.timer_library.keys()), parent=self)
        from PySide6.QtWidgets import QDialog as _QDialog
        if dlg.exec() != _QDialog.Accepted:
            return

        new_order = dlg.get_ordered_names()
        # timer_library in-place 재정렬 (main_window 참조 공유 유지)
        reordered = {name: self.timer_library[name] for name in new_order if name in self.timer_library}
        self.timer_library.clear()
        self.timer_library.update(reordered)
        self.refresh_grid()
