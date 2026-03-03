from PySide6.QtCore import Qt, QEventLoop, QRect, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QScrollArea, QGridLayout, QFrame, QSizePolicy, 
    QScroller, QScrollerProperties, QApplication, QInputDialog
)

from widgets.glass_card import GlassCard

# [키패드 임포트]
try:
    from widgets.touch_number_keyboard import TouchNumberKeyboard
except ImportError:
    TouchNumberKeyboard = None


# ==========================================================
# [팝업] 타이머 시간 수정 다이얼로그 (오버레이 방식)
# ==========================================================
# QDialog가 아니라 QWidget을 상속받아 "새 창"이 아닌 "덮어씌우는 화면"으로 만듦
class TimerEditDialog(QWidget):
    # QDialog의 응답 코드 흉내
    Accepted = 1
    Rejected = 0

    def __init__(self, timer_name, current_val_ms, parent=None):
        super().__init__(parent)
        
        # [핵심] 부모 화면 전체를 덮도록 크기 설정
        if parent:
            self.resize(parent.size())
        
        # 반투명 배경 (모달 효과)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        
        # 이 위젯 자체가 터치를 먹어서 뒷배경 클릭 방지
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)

        self.current_ms = int(current_val_ms)
        self.result_code = self.Rejected
        self._event_loop = None

        # --- 내부 컨텐츠 박스 (화면 중앙에 배치) ---
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
        
        # 컨텐츠 레이아웃
        box_layout = QVBoxLayout(self.container)
        box_layout.setSpacing(15)
        box_layout.setContentsMargins(20, 20, 20, 20)

        # 1. 타이머 이름
        lbl_name_display = QLabel(timer_name)
        lbl_name_display.setAlignment(Qt.AlignCenter)
        lbl_name_display.setStyleSheet("color: #FFD700; font-size: 22px; font-weight: 900; margin-bottom: 5px;")
        box_layout.addWidget(lbl_name_display)

        # 1-2. 안내 라벨
        lbl_title = QLabel("설정 시간 변경 (초)")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color: #AAA; font-size: 14px;")
        box_layout.addWidget(lbl_title)

        # 2. 값 입력 영역
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

        box_layout.addLayout(val_layout)

        # 3. 버튼
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
        
        # 오버레이에 컨테이너 추가
        main_layout.addWidget(self.container)
        
        self._update_display()

    # [핵심] QDialog의 exec()를 흉내내는 함수
    def exec(self):
        self.show()
        self.raise_()
        self._event_loop = QEventLoop()
        self._event_loop.exec() # 여기서 코드 실행이 멈추고 대기함
        self.hide()
        self.deleteLater() # 사용 후 자동 삭제
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
        # 키패드는 QDialog여도 상관없음 (닫히면 다시 이 Overlay로 포커스가 돌아오는데, Overlay는 메인창의 일부라 포커스 문제 없음)
        formatted_val = f"{self.current_ms / 100.0:.1f}"

        if TouchNumberKeyboard:
            # self를 부모로 지정
            dlg = TouchNumberKeyboard(formatted_val, 1, parent=self)

            # 키패드 실행 (QDialog.exec() 사용)
            # 여기서는 키패드가 '새 창'으로 뜨지만,
            # 닫힐 때 돌아오는 곳이 '메인 윈도우'이므로 문제 없음
            if dlg.exec() == 1: # Accepted
                try:
                    input_float = float(dlg.get_value())
                    self.current_ms = int(round(input_float * 100))
                    self._update_display()
                except ValueError: pass
        else:
            current_sec = self.current_ms / 100.0
            val, ok = QInputDialog.getDouble(self, "입력", "시간(초):", current_sec, 0, 999, 1)
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
# [페이지] 타이머 목록
# ==========================================================
class PageTimer(GlassCard):
    def __init__(self, sequence_data=None, plc_client=None):
        super().__init__("")
        
        if hasattr(self, 'title_label'):
            self.title_label.hide()
            if self.title_label.parentWidget() and self.title_label.parentWidget() != self:
                self.title_label.parentWidget().hide()

        if self.layout():
            self.layout().setContentsMargins(10, 5, 10, 10)

        self.plc_client = plc_client

        self.sequence_data = sequence_data if sequence_data is not None else {}
        if isinstance(self.sequence_data, dict) and "Main" not in self.sequence_data:
            self.sequence_data["Main"] = []

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        # [QScroller 설정]
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

        self.body.addWidget(scroll, 1)
        self._last_width = 0
        # 위젯 배치 완료 후 첫 그리드 그리기
        QTimer.singleShot(0, self.refresh_grid)

    def refresh_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        timers = []

        if isinstance(self.sequence_data, dict):
            for seq_name, steps in self.sequence_data.items():
                for i, step in enumerate(steps):
                    if step.get("type") == "TMR":
                        timers.append((seq_name, i, step))
        elif isinstance(self.sequence_data, list):
            for i, step in enumerate(self.sequence_data):
                if step.get("type") == "TMR":
                    timers.append(("Main", i, step))

        # 열 수 고정 8, viewport 폭으로 카드 폭 계산
        COLS = 8
        spacing = 10
        vp_w = self.scroll.viewport().width()
        if vp_w < 200:
            vp_w = self.width()
        if vp_w < 200:
            vp_w = 1000  # 초기 레이아웃 미결정 시 기본값
        card_w = max(100, (vp_w - spacing * (COLS - 1)) // COLS)
        card_h = max(100, int(card_w * 0.92))
        cols = COLS

        for i, (seq_name, step_idx, step) in enumerate(timers):
            r = i // cols
            c = i % cols
            card = self._create_timer_card(seq_name, step, card_w, card_h)
            card.clicked.connect(lambda checked, s=step, sn=seq_name, idx=step_idx, w=card: self._on_card_clicked(s, sn, idx, w))
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

    def _create_timer_card(self, seq_name, step, card_w=130, card_h=110):
        btn = QPushButton()
        btn.setFixedSize(card_w, card_h)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1A222C;
                border: 1px solid #3E4A59;
                border-radius: 12px;
            }
            QPushButton:pressed {
                background-color: #2C3E50;
                border: 1px solid #468CFF;
            }
        """)
        
        layout = QVBoxLayout(btn)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(5)
        
        lbl_seq = QLabel(f"[{seq_name}]")
        lbl_seq.setAlignment(Qt.AlignCenter)
        lbl_seq.setStyleSheet("color: #AAA; font-size: 12px;")
        
        lbl_name = QLabel(step.get("name", "Timer"))
        lbl_name.setAlignment(Qt.AlignCenter)
        lbl_name.setStyleSheet("color: #EEE; font-size: 14px; font-weight: bold;")
        lbl_name.setWordWrap(True)
        
        if "time" in step:
            raw_val_sec = float(step["time"])
        elif "value" in step:
            raw_val_sec = float(step["value"]) / 100.0
            step["time"] = raw_val_sec
        else:
            raw_val_sec = 1.0
        
        lbl_val = QLabel(f"{raw_val_sec:.1f}")
        lbl_val.setAlignment(Qt.AlignCenter)
        lbl_val.setStyleSheet("color: #FFFF00; font-size: 28px; font-weight: 900;")
        
        lbl_unit = QLabel("SEC")
        lbl_unit.setAlignment(Qt.AlignCenter)
        lbl_unit.setStyleSheet("color: #888; font-size: 11px;")
        
        layout.addWidget(lbl_seq)
        layout.addWidget(lbl_name)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_unit)
        
        btn.lbl_val_ref = lbl_val
        return btn

    def _on_card_clicked(self, step, seq_name, step_idx, card_widget):
        if "time" in step:
            current_sec = float(step["time"])
        elif "value" in step:
            current_sec = float(step["value"]) / 100.0
        else:
            current_sec = 1.0

        current_ms = int(current_sec * 100)
        timer_name = step.get("name", "Timer")
        
        # [수정] 오버레이 방식 다이얼로그 생성 (부모는 self = PageTimer)
        # 이렇게 하면 PageTimer 위에 '그려지는' 것이라 새 창 취급을 안 받아 터치 문제가 없습니다.
        dlg = TimerEditDialog(timer_name, current_ms, self)
        
        # exec()를 호출하지만 실제로는 QDialog가 아닌 커스텀 이벤트 루프가 돕니다.
        if dlg.exec() == TimerEditDialog.Accepted:
            new_ms = dlg.get_value_ms()
            new_sec = new_ms / 100.0
            
            step["time"] = new_sec
            
            if hasattr(card_widget, 'lbl_val_ref'):
                card_widget.lbl_val_ref.setText(f"{new_sec:.1f}")
            
            print(f"[Timer Page] Updated: {new_sec} sec (RAM)")

            # PLC 전송
            if self.plc_client and self.plc_client.is_connected:
                try:
                    seq_map = {"Main": 0}
                    sub_keys = sorted([k for k in self.sequence_data.keys() if k != "Main"])
                    for i, k in enumerate(sub_keys):
                        if i + 1 >= 40: break
                        seq_map[k] = i + 1
                    
                    slot_id = seq_map.get(seq_name, 0)
                    target_addr = 10000 + (slot_id * 500) + (step_idx * 10) + 2
                    
                    self.plc_client.write_dint(0x09, target_addr, new_ms)
                    print(f"[Timer Page] Sent to PLC: Slot={slot_id}, Step={step_idx}, Addr={target_addr}, Val={new_ms}ms")
                    
                except Exception as e:
                    print(f"[Timer Page] PLC Send Error: {e}")
            else:
                print("[Timer Page] PLC not connected.")