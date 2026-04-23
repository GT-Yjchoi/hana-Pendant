import time
from PySide6.QtCore import Qt, QEventLoop, QTimer, Signal
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
    sig_timer_changed = Signal()   # 타이머 값 변경 시 발행 → main_window에서 auto_save 트리거

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
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(10)
        self.grid.setAlignment(Qt.AlignTop)

        # 하단 버튼 행 (우측 정렬)
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 8, 0, 0)
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

        self.body.addWidget(scroll, 1)
        self.body.addLayout(btn_row)
        self._last_width = 0

        # 기동 중 카드 하이라이트
        self._timer_cards = {}
        self._active_timer_name = None
        self._blink_state = False
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(500)
        self._blink_timer.timeout.connect(self._on_blink)

        # [NEW] 최소 하이라이트 유지 시간 (0초 타이머도 사용자가 인지하도록 보장)
        # 깜빡임 주기(500ms)와 맞춰 최소 1회 on→off→on 이 보이도록 설정
        self._highlight_min_sec = 0.5
        self._active_min_end = 0.0    # 이 시점까지는 현재 하이라이트 유지
        self._active_queue = []       # 대기 큐: 짧은 타이머 연속 발동 시 순차 표시
        self._pending_clear = QTimer(self)
        self._pending_clear.setSingleShot(True)
        self._pending_clear.timeout.connect(self._on_hold_expired)

        if self.plc_client:
            self.plc_client.sig_monitor_data.connect(self._on_monitor_data)

        QTimer.singleShot(0, self.refresh_grid)

    def refresh_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._timer_cards = {}

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
            self._timer_cards[name] = card
            self.grid.addWidget(card, r, c)

        self._update_card_styles()

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

        # 상단 행: 이름 + 기동중 인디케이터 (우측 정렬)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)

        lbl_name = QLabel(name)
        lbl_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl_name.setStyleSheet("color: #DDD; font-size: 17px; font-weight: bold; border: none; background: transparent;")
        lbl_name.setWordWrap(False)
        top_row.addWidget(lbl_name, 1)

        # 기동중 인디케이터 — 카드 폭 확보를 위해 아이콘만(▶) 표시. 고정폭 유지(레이아웃 들썩임 방지).
        lbl_run = QLabel("")
        lbl_run.setFixedSize(20, 16)
        lbl_run.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_run.setStyleSheet("color: #00FF7F; font-size: 14px; font-weight: bold; border: none; background: transparent;")
        top_row.addWidget(lbl_run, 0)

        layout.addLayout(top_row)

        # 시간 값 (버튼 - 클릭 시 편집) — 시간 + SEC을 한 버튼에 표시
        btn_time = QPushButton(f"{time_sec:.1f} SEC")
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

        # 참조 저장
        frame._btn_time_ref = btn_time
        frame._name_ref = name
        frame._lbl_run = lbl_run

        return frame

    def _on_card_clicked(self, name, time_sec, btn_widget):
        current_ms = int(self.timer_library.get(name, time_sec) * 100)
        dlg = TimerEditDialog(name, current_ms, self)
        if dlg.exec() == TimerEditDialog.Accepted:
            new_ms = dlg.get_value_ms()
            new_sec = new_ms / 100.0
            old_sec = self.timer_library.get(name, time_sec)
            self.timer_library[name] = new_sec
            btn_widget.setText(f"{new_sec:.1f} SEC")
            self._sync_steps_time(name, new_sec)
            print(f"[Timer Library] Updated '{name}': {new_sec} sec")
            try:
                from utils.op_history import record as op_record
                op_record("TIMER", f"타이머 '{name}' {old_sec:.2f}s → {new_sec:.2f}s")
            except Exception: pass

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
            plc_idx = 0
            for step in steps:
                if step.get("type") == "COMMENT":
                    continue
                # TMR 스텝 (단순 대기 / 신호 유지)
                if step.get("type") == "TMR" and step.get("timer_ref") == timer_name:
                    step["time"] = new_sec
                    if plc and getattr(plc, 'is_connected', False) and slot_id is not None:
                        plc.patch_tmr_step_time(slot_id, plc_idx, new_sec)
                    patch_count += 1
                # OUT 스텝의 타이머 기동후출력 (delay_timer_ref)
                elif step.get("type") == "OUT" and step.get("delay_timer_ref") == timer_name:
                    step["delay_time"] = new_sec
                    if plc and getattr(plc, 'is_connected', False) and slot_id is not None:
                        plc.patch_out_delay_step_time(slot_id, plc_idx, new_sec)
                    patch_count += 1
                plc_idx += 1

        if patch_count:
            print(f"[Timer Library] Synced+Patched {patch_count} step(s) referencing '{timer_name}'")

        # 변경 사항이 있든 없든 타이머 라이브러리 자체는 변했으므로 저장 트리거
        self.sig_timer_changed.emit()

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
            self.sig_timer_changed.emit()

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
        self.sig_timer_changed.emit()

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

    def _on_monitor_data(self, data):
        if not isinstance(data, dict):
            return
        op_status    = data.get('op_status', 0)
        current_slot = data.get('sub_seq_idx', 0)   # DT132 = FB.i_CurrentSlot (Main=0, 서브=1~N, Monitor=39)
        current_step = data.get('current_step', 0)  # DT131 = FB.i_CurrentStep (스택 top 기준)

        if op_status in (1, 2):
            active = self._find_active_timer(current_slot, current_step)
        else:
            active = None

        # [변경] 최소 유지 시간 + 큐잉 - 짧은 타이머 연속 발동도 각각 확실히 보임
        self._handle_active_change(active)

    def _handle_active_change(self, active):
        """현재 스캔의 active 타이머 반영. 최소 유지 시간 내엔 큐에 쌓고,
        시간이 지나면 순차적으로 표시."""
        now = time.monotonic()
        holding = now < self._active_min_end

        if active == self._active_timer_name:
            # 동일 active 유지 - 큐에 쌓였던 과거 active 는 무시
            return

        if holding:
            # 현재 하이라이트 최소 유지 시간 내 → 큐에 담기 (중복/None 은 스킵)
            if active is None:
                return
            if not self._active_queue or self._active_queue[-1] != active:
                self._active_queue.append(active)
            return

        # 최소 유지 시간 지남 또는 아직 아무것도 표시 안함 → 즉시 반영
        self._show_active(active)

    def _show_active(self, active):
        """active 타이머를 즉시 표시 (None 이면 해제)."""
        self._pending_clear.stop()
        self._active_timer_name = active
        if active is not None:
            self._active_min_end = time.monotonic() + self._highlight_min_sec
            self._blink_state = True
            self._blink_timer.start()
            # 최소 유지 시간 후에 큐 소진 또는 클리어 결정
            self._pending_clear.start(int(self._highlight_min_sec * 1000))
        else:
            self._active_min_end = 0.0
            self._blink_timer.stop()
            self._blink_state = False
        self._update_card_styles()

    def _on_hold_expired(self):
        """최소 유지 시간 만료. 큐에 대기 중이면 다음 항목 표시, 없으면 클리어."""
        if self._active_queue:
            next_active = self._active_queue.pop(0)
            self._show_active(next_active)
        else:
            self._show_active(None)

    def _find_active_timer(self, current_slot, step_idx):
        """현재 슬롯 + 스텝 번호로 실행 중인 TMR의 timer_ref 반환. Main/Monitor 포함."""
        # 슬롯 번호 → 시퀀스 이름 매핑
        if current_slot == 0:
            seq_name = "Main"
        elif current_slot == 39:
            seq_name = "Monitor"
        else:
            reserved = {"Main", "Monitor"}
            subs = sorted([k for k in self.sequence_data.keys() if k not in reserved])
            idx = current_slot - 1
            if idx < 0 or idx >= len(subs):
                return None
            seq_name = subs[idx]

        steps = self.sequence_data.get(seq_name, [])
        n = 0
        for step in steps:
            if step.get("type") == "COMMENT":
                continue
            if n == step_idx:
                if step.get("type") == "TMR":
                    return step.get("timer_ref")
                return None
            n += 1
        return None

    def _on_blink(self):
        self._blink_state = not self._blink_state
        self._update_card_styles()

    def _update_card_styles(self):
        for name, frame in self._timer_cards.items():
            is_active = (name == self._active_timer_name)
            if is_active:
                border_color = "#00FF7F" if self._blink_state else "#007A40"
                bg_color     = "#162A1E" if self._blink_state else "#111E16"
                frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {bg_color};
                        border: 2px solid {border_color};
                        border-radius: 12px;
                    }}
                """)
                if hasattr(frame, '_lbl_run'):
                    frame._lbl_run.setText("▶")
            else:
                frame.setStyleSheet("""
                    QFrame {
                        background-color: #1A222C;
                        border: 1px solid #3E4A59;
                        border-radius: 12px;
                    }
                """)
                if hasattr(frame, '_lbl_run'):
                    frame._lbl_run.setText("")

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
