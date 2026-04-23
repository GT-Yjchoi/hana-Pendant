from PySide6.QtCore import Qt, Signal, QEventLoop
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import (
    QLabel, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QWidget, QFrame, QSizePolicy, QApplication
)


class StaircaseBar(QWidget):
    """10단계 속도를 오르막 막대 그래프로 시각화."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 10
        self.setMinimumSize(180, 70)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set_level(self, level):
        self._level = max(1, min(10, level))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        bar_count = 10
        gap = 3
        bar_w = (w - gap * (bar_count - 1)) / bar_count

        if self._level <= 3:
            active_color = QColor("#E74C3C")
        elif self._level <= 6:
            active_color = QColor("#F1C40F")
        else:
            active_color = QColor("#2ECC71")

        for i in range(bar_count):
            bar_h = h * (i + 1) / bar_count
            x = i * (bar_w + gap)
            y = h - bar_h
            if i < self._level:
                painter.setBrush(QBrush(active_color))
                painter.setPen(Qt.NoPen)
            else:
                painter.setBrush(QBrush(QColor(40, 48, 60)))
                painter.setPen(QPen(QColor(80, 90, 100), 1))
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(bar_h), 3, 3)

from widgets.glass_card import GlassCard
from widgets.io_panel import IOPanel
from utils.languages import LanguageManager
from ui.widgets.axis_position_panel import AxisPositionPanel

# [스타일 상수]
STYLE_GRAY_OFF  = "background-color: #3E4A59; color: #95A5A6; border: 2px solid #2C3E50; border-radius: 14px; font-weight: bold; font-size: 18px;"
STYLE_GREEN_ON  = "background-color: #2ECC71; color: white; border: 3px solid #27AE60; border-radius: 14px; font-weight: 900; font-size: 20px;"
STYLE_YELLOW_ON = "background-color: #F1C40F; color: black; border: 3px solid #D4AC0D; border-radius: 14px; font-weight: 900; font-size: 20px;"
STYLE_RED_ON    = "background-color: #E74C3C; color: white; border: 3px solid #C0392B; border-radius: 14px; font-weight: 900; font-size: 20px;"

# =========================================================
# [기존 유지] 자동/확인운전 전용 오버레이 확인창
# =========================================================
class AutoConfirmOverlay(QWidget):
    def __init__(self, title, message, parent=None):
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
        container.setFixedSize(400, 220)
        container.setStyleSheet("""
            QFrame {
                background-color: #1A1F2B;
                border: 2px solid #468CFF;
                border-radius: 15px;
            }
            QLabel { background: transparent; border: none; color: white; font-weight: bold; }
            QPushButton { border-radius: 8px; font-size: 16px; font-weight: bold; }
        """)
        
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(25, 25, 25, 25)
        vbox.setSpacing(20)
        
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color: #468CFF; font-size: 22px;")
        vbox.addWidget(lbl_title)
        
        lbl_msg = QLabel(message)
        lbl_msg.setAlignment(Qt.AlignCenter)
        lbl_msg.setStyleSheet("font-size: 16px;")
        vbox.addWidget(lbl_msg)
        
        btn_layout = QHBoxLayout()
        self.btn_no = QPushButton("아니오")
        self.btn_no.setFixedSize(120, 45)
        self.btn_no.setStyleSheet("background: #34495E; color: white;")
        self.btn_no.clicked.connect(self.reject)
        
        self.btn_yes = QPushButton("예")
        self.btn_yes.setFixedSize(120, 45)
        self.btn_yes.setStyleSheet("background: #2980B9; color: white;")
        self.btn_yes.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_no)
        btn_layout.addWidget(self.btn_yes)
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

# [정보 패널] 생산 정보 표시
class InfoPanel(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5) 
        
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("color: #DDD; font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        main_layout.addWidget(self.lbl_title, 0, Qt.AlignTop | Qt.AlignLeft)
        
        self.bg_frame = QFrame()
        self.bg_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            QLabel {
                border: none;
            }
        """)
        main_layout.addWidget(self.bg_frame)
        
        box_layout = QVBoxLayout(self.bg_frame)
        box_layout.setContentsMargins(20, 20, 20, 20)
        box_layout.setSpacing(10) 
        
        self.info_labels = {}
        self.name_labels = {}
        
        # 항목: 취출횟수, 예약알람, 성형시간, 취출시간
        items = [
            ("lbl_extract_cnt", "cnt", "0"),
            ("lbl_reserve_cnt", "rsv", "0"), # 예약알람 추가
            ("lbl_mold_time", "mold", "0.0"),
            ("lbl_extract_time", "ext", "0.0")
        ]
        
        for lang_key, data_key, def_val in items:
            row = QHBoxLayout()
            lbl_n = QLabel(); lbl_n.setStyleSheet("color: #CCC; font-size: 16px; font-weight: bold;")
            lbl_v = QLabel(def_val); lbl_v.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: 900;")
            self.name_labels[lang_key] = lbl_n
            self.info_labels[data_key] = lbl_v
            row.addWidget(lbl_n); row.addStretch(1); row.addWidget(lbl_v)
            box_layout.addLayout(row)
        
        box_layout.addStretch(1)
        self.update_language()
    
    def update_data(self, count, rsv_count, mold_t, ext_t):
        self.info_labels["cnt"].setText(f"{count} 회")
        self.info_labels["rsv"].setText(f"{rsv_count} 회")
        self.info_labels["mold"].setText(f"{mold_t:.1f} 초")
        self.info_labels["ext"].setText(f"{ext_t:.1f} 초")

    def update_language(self):
        lm = LanguageManager.instance()
        self.lbl_title.setText(lm.get_text("info_title"))
        
        for k, lbl in self.name_labels.items():
            text = lm.get_text(k)
            # 언어팩에 키가 없을 경우 기본값 처리
            if k == "lbl_reserve_cnt" and (text == k or text == ""):
                text = "예약알람" 
            lbl.setText(text)

# [메인 페이지] PageAuto
class PageAuto(GlassCard):
    sig_speed_changed = Signal(int)  # 전체속도 변경 → main_window 자동저장 트리거

    def __init__(self, plc_client=None, speed_state=None):
        super().__init__("")
        if hasattr(self, 'title_label'): self.title_label.hide()
        if self.layout(): self.layout().setContentsMargins(10, 5, 10, 10)

        self.plc_client = plc_client
        self.current_mode = 0  # 현재 운전 모드 (0:정지, 1:자동, 2:확인)
        self._prev_op_status = 0
        # 레시피 공유 state (main_window에서 주입). 키: "speed_level" (1~10)
        self.speed_state = speed_state if speed_state is not None else {"speed_level": 10}
        self.speed_level = int(self.speed_state.get("speed_level", 10))
        
        # UI 레이아웃 구성
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        
        # 1. 위치 패널 (Left)
        self.pos_panel = AxisPositionPanel(plc_client=plc_client)
        
        # ★ [수정] 위치 패널 내부 콘텐츠를 상단(Top)으로 정렬
        # GlassCard의 body(QVBoxLayout) 정렬을 변경하여 내용이 위로 올라가게 함
        if hasattr(self.pos_panel, 'body'):
            self.pos_panel.body.setAlignment(Qt.AlignTop)
            # 필요하다면 상단 여백을 조금 주어 너무 딱 붙지 않게 조정 (선택사항)
            # self.pos_panel.body.setContentsMargins(0, 20, 0, 0)

        # 2. IO 패널 (Middle)
        self.io_panel = IOPanel()
        
        # 3. 우측 제어 영역 (Right)
        right_layout = QVBoxLayout()
        
        # 제어 버튼 패널
        ctrl_widget = QWidget()
        ctrl_lay = QHBoxLayout(ctrl_widget)
        ctrl_lay.setContentsMargins(0, 0, 0, 0)
        ctrl_lay.setSpacing(15) 
        
        self.btn_auto = QPushButton("AUTO RUN")
        self.btn_check = QPushButton("CHECK RUN")
        self.btn_stop = QPushButton("STOP")
        
        for b in [self.btn_auto, self.btn_check, self.btn_stop]:
            b.setMinimumHeight(90)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setStyleSheet(STYLE_GRAY_OFF)
            ctrl_lay.addWidget(b)
            
        # 전체 속도 조절 (1~10단계, 계단형 그래프)
        self.speed_box = QFrame()
        self.speed_box.setStyleSheet("""
            QFrame#speedBox {
                background: rgba(255,255,255,0.05);
                border-radius: 10px;
                border: 1px solid #444;
            }
            QLabel { background: transparent; border: none; color: #DDD; }
            QPushButton {
                background: #34495E; color: white;
                border: 1px solid #555; border-radius: 8px;
                font-size: 26px; font-weight: 900;
            }
            QPushButton:pressed { background: #2C3E50; }
        """)
        self.speed_box.setObjectName("speedBox")
        spd_outer = QVBoxLayout(self.speed_box)
        spd_outer.setContentsMargins(15, 10, 15, 10)
        spd_outer.setSpacing(8)

        # 상단: 타이틀 + 현재 단계 숫자
        top_row = QHBoxLayout()
        self.lbl_speed_title = QLabel("전체속도")
        self.lbl_speed_title.setStyleSheet("color: #DDD; font-size: 16px; font-weight: bold;")
        self.lbl_speed_value = QLabel(f"{self.speed_level} / 10")
        self.lbl_speed_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_speed_value.setStyleSheet("color: #2ECC71; font-size: 22px; font-weight: 900;")
        top_row.addWidget(self.lbl_speed_title)
        top_row.addStretch(1)
        top_row.addWidget(self.lbl_speed_value)
        spd_outer.addLayout(top_row)

        # 중단: − 버튼 + 계단 그래프 + + 버튼
        graph_row = QHBoxLayout()
        graph_row.setSpacing(10)
        self.btn_spd_minus = QPushButton("−")
        self.btn_spd_minus.setFixedSize(55, 70)
        self.btn_spd_plus = QPushButton("+")
        self.btn_spd_plus.setFixedSize(55, 70)

        self.speed_bar = StaircaseBar()
        self.speed_bar.set_level(self.speed_level)

        graph_row.addWidget(self.btn_spd_minus)
        graph_row.addWidget(self.speed_bar, 1)
        graph_row.addWidget(self.btn_spd_plus)
        spd_outer.addLayout(graph_row)

        # 확인운전 전용 서브 버튼
        self.sub_box = QFrame()
        self.sub_box.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 10px; border: 1px solid #444;")
        sub_lay = QHBoxLayout(self.sub_box)
        self.btn_sub_start = QPushButton("START")
        self.btn_sub_pause = QPushButton("PAUSE")
        for sb in [self.btn_sub_start, self.btn_sub_pause]:
            sb.setFixedHeight(50)
            sb.setStyleSheet("background: #34495E; color: #BBB; border: 1px solid #555;")
        sub_lay.addWidget(self.btn_sub_start)
        sub_lay.addWidget(self.btn_sub_pause)
        
        right_layout.addWidget(ctrl_widget, 0, Qt.AlignTop)
        right_layout.addWidget(self.sub_box, 0, Qt.AlignTop)
        sp = self.sub_box.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.sub_box.setSizePolicy(sp)
        self.sub_box.hide()

        right_layout.addStretch(1)
        right_layout.addWidget(self.speed_box, 0, Qt.AlignVCenter)
        right_layout.addStretch(1)

        # 정보 패널
        self.info_panel = InfoPanel()
        right_layout.addWidget(self.info_panel, 0, Qt.AlignBottom)
        
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        
        # ★ [수정] 레이아웃 비율 복구 (2 : 4 : 4)
        main_layout.addWidget(self.pos_panel, 2)
        main_layout.addWidget(self.io_panel, 4)
        main_layout.addWidget(right_widget, 4)
        
        self.body.addLayout(main_layout)

        # 이벤트 연결
        self.btn_auto.clicked.connect(self._on_auto_clicked)
        self.btn_check.clicked.connect(self._on_check_clicked)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        self.btn_sub_start.clicked.connect(lambda: self._send_check_state(1))
        self.btn_sub_pause.clicked.connect(lambda: self._send_check_state(0))
        self.btn_spd_minus.clicked.connect(lambda: self._change_speed(-1))
        self.btn_spd_plus.clicked.connect(lambda: self._change_speed(1))

        if self.plc_client:
            self.plc_client.sig_monitor_data.connect(self._on_monitor_data)
        self.update_language()

    def _change_speed(self, delta):
        new_val = max(1, min(10, self.speed_level + delta))
        if new_val == self.speed_level:
            return
        old_val = self.speed_level
        self.speed_level = new_val
        self.speed_state["speed_level"] = new_val
        self._refresh_speed_widgets()
        if self.plc_client:
            self.plc_client.send_speed_override(self.speed_level)
        self.sig_speed_changed.emit(self.speed_level)
        try:
            from utils.op_history import record as op_record
            op_record("SPEED", f"전체속도 {old_val} → {new_val}")
        except Exception: pass

    def _refresh_speed_widgets(self):
        self.lbl_speed_value.setText(f"{self.speed_level} / 10")
        color = "#E74C3C" if self.speed_level <= 3 else "#F1C40F" if self.speed_level <= 6 else "#2ECC71"
        self.lbl_speed_value.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: 900;")
        self.speed_bar.set_level(self.speed_level)

    def refresh_speed_from_state(self):
        """레시피 로드 후 외부 state에서 속도 값을 다시 읽어 UI/PLC 동기화."""
        new_val = max(1, min(10, int(self.speed_state.get("speed_level", 10))))
        self.speed_level = new_val
        self.speed_state["speed_level"] = new_val
        self._refresh_speed_widgets()
        if self.plc_client:
            self.plc_client.send_speed_override(self.speed_level)

    def _send_mode(self, mode):
        if self.plc_client:
            self.plc_client.send_control_command(mode)

    def _on_stop_clicked(self):
        self._send_mode(0)
        self._send_check_state(0)  # DT202 = 0 리셋
        try:
            from utils.op_history import record as op_record
            op_record("RUN", "정지 버튼")
        except Exception: pass

    def _send_check_state(self, state):
        if self.plc_client:
            self.plc_client.send_check_run_command(state)

    def _on_auto_clicked(self):
        # [수정] 이미 운전 중이면 팝업 차단
        if self.current_mode == 1 or self.current_mode == 2:
            return

        if AutoConfirmOverlay("자동 운전", "자동 운전을 시작하시겠습니까?", self.window()).exec():
            self._send_mode(1)
            try:
                from utils.op_history import record as op_record
                op_record("RUN", "자동 운전 시작")
            except Exception: pass

    def _on_check_clicked(self):
        # [수정] 이미 운전 중이면 팝업 차단
        if self.current_mode == 1 or self.current_mode == 2:
            return

        if AutoConfirmOverlay("확인 운전", "확인 운전을 시작하시겠습니까?", self.window()).exec():
            self._send_mode(2)
            try:
                from utils.op_history import record as op_record
                op_record("RUN", "확인 운전 시작")
            except Exception: pass

    def _on_monitor_data(self, data):
        mode = data.get('op_status', 0)

        # 확인운전 종료 감지(2→0): 화면 표시 여부 무관하게 DT202=0 전송
        if self._prev_op_status == 2 and mode == 0:
            self._send_check_state(0)
        self._prev_op_status = mode

        if not self.isVisible(): return
        # 1. IO 업데이트
        if 'inputs' in data: self.io_panel.inputs.update_from_words(data['inputs'])
        if 'outputs' in data: self.io_panel.outputs.update_from_words(data['outputs'])

        # 3. 운전 상태
        self.current_mode = mode
        check_run_state = data.get('check_run_status', 0)
        
        self.btn_auto.setStyleSheet(STYLE_GREEN_ON if mode == 1 else STYLE_GRAY_OFF)
        self.btn_check.setStyleSheet(STYLE_YELLOW_ON if mode == 2 else STYLE_GRAY_OFF)
        self.btn_stop.setStyleSheet(STYLE_RED_ON if mode in [1, 2] else STYLE_GRAY_OFF)

        self.sub_box.setVisible(mode == 2)
        if mode == 2:
            self.btn_sub_start.setStyleSheet("background: #27AE60; color: white; border: 2px solid white;" if check_run_state == 1 else "background: #34495E; color: #BBB;")
            self.btn_sub_pause.setStyleSheet("background: #E67E22; color: white; border: 2px solid white;" if check_run_state == 0 else "background: #34495E; color: #BBB;")
        
        # 4. 생산 정보 (예약알람 포함)
        reserve_cnt = data.get('setting_count', 0) 
        
        self.info_panel.update_data(
            data.get('total_count', 0),
            reserve_cnt,
            data.get('mold_time', 0.0),
            data.get('takeout_time', 0.0)
        )

    def update_language(self, lang_code=None):
        lm = LanguageManager.instance()
        self.btn_auto.setText(lm.get_text("btn_auto_run"))
        self.btn_check.setText(lm.get_text("btn_check_run"))
        self.btn_stop.setText(lm.get_text("btn_stop"))
        self.info_panel.update_language()