from PySide6.QtCore import Qt, Signal, QEventLoop
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QFrame, QGridLayout, QLabel, QButtonGroup
)

class JogControlDialog(QWidget):
    sig_jog_event = Signal(str, bool)
    _last_speed = 1  # 마지막 선택 속도 기억 (클래스 변수)

    def __init__(self, plc_client=None, parent=None):
        super().__init__(parent)
        self.plc_client = plc_client

        _W, _H = 280, 630  # 패널 크기

        if parent:
            main_window = parent.window()
            self.setParent(main_window)
            # 전체화면 대신 패널 크기만큼만 → 나머지 영역 터치 통과
            self.setFixedSize(_W, _H)
            # 오른쪽 상단에 배치
            x = main_window.width() - _W - 5
            y = (main_window.height() - _H) // 2
            self.move(x, y)

        self.setAttribute(Qt.WA_AcceptTouchEvents, True)

        self._event_loop = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setFixedSize(_W, _H)
        self.container.setStyleSheet("""
            QFrame { background-color: #080c15; border: 2px solid #00E5FF; border-radius: 15px; }
            QPushButton { background-color: rgba(255, 255, 255, 0.05); border: 2px solid #005f73; border-radius: 8px; color: white; font-size: 14px; font-weight: bold; font-family: 'Malgun Gothic', sans-serif; }
            QPushButton:pressed { background-color: rgba(0, 229, 255, 0.3); border: 2px solid #00E5FF; color: #00E5FF; }
            QLabel { color: #00E5FF; font-weight: bold; font-size: 18px; background-color: transparent; border: none; }
            QPushButton#btnClose { background-color: transparent; border: none; color: #888; font-size: 20px; font-weight: 900; }
            QPushButton#btnClose:pressed { color: #FF4646; border: none; background-color: transparent; }
        """)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(15, 10, 15, 15)
        layout.setSpacing(5) 

        # 1. 헤더
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(QLabel("JOG CONTROL"))
        header_layout.addStretch(1)
        btn_close = QPushButton("X")
        btn_close.setObjectName("btnClose")
        btn_close.setFixedSize(35, 35)
        btn_close.clicked.connect(self.close_overlay)
        header_layout.addWidget(btn_close)
        layout.addLayout(header_layout)
        
        line = QLabel(); line.setFixedHeight(2); line.setStyleSheet("background-color: #00E5FF;"); layout.addWidget(line)
        layout.addSpacing(10)

        # 2. 주행 버튼
        top_layout = QHBoxLayout(); top_layout.setSpacing(8)
        self.btn_trav_neg = self._create_btn("주행 -", h=55)
        self.btn_trav_pos = self._create_btn("주행 +", h=55)
        top_layout.addWidget(self.btn_trav_neg); top_layout.addWidget(self.btn_trav_pos)
        layout.addLayout(top_layout)
        layout.addSpacing(15)

        # 3. 십자키
        cross_frame = QFrame()
        cross_frame.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 12px; border: none;")
        cross_layout = QGridLayout(cross_frame)
        cross_layout.setSpacing(6); cross_layout.setContentsMargins(6, 6, 6, 6)
        
        btn_size = (60, 60) 
        self.btn_up = self._create_btn("상 (Z-)", btn_size)
        self.btn_down = self._create_btn("하 (Z+)", btn_size)
        self.btn_front = self._create_btn("전 (Y+)", btn_size)
        self.btn_back = self._create_btn("후 (Y-)", btn_size)

        cross_layout.addWidget(self.btn_up, 0, 1)       
        cross_layout.addWidget(self.btn_front, 1, 0)   
        cross_layout.addWidget(self.btn_back, 1, 2)    
        cross_layout.addWidget(self.btn_down, 2, 1)    
        
        center_lbl = QLabel("MOVE")
        center_lbl.setAlignment(Qt.AlignCenter)
        center_lbl.setStyleSheet("color: #666; font-size: 11px;")
        cross_layout.addWidget(center_lbl, 1, 1)
        layout.addWidget(cross_frame, 0, Qt.AlignCenter)
        
        # ---------------------------------------------------------
        # 속도 조절 섹션 (1~5단)
        # ---------------------------------------------------------
        layout.addSpacing(15)
        lbl_speed = QLabel("JOG SPEED (DT211)")
        lbl_speed.setStyleSheet("color: #AAA; font-size: 12px; margin-bottom: 5px;")
        lbl_speed.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_speed)

        speed_layout = QHBoxLayout()
        speed_layout.setSpacing(5)
        
        self.speed_group = QButtonGroup(self)
        self.speed_group.setExclusive(True)
        self.speed_btns = []

        for i in range(1, 6):
            btn = QPushButton(str(i))
            btn.setCheckable(True)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet(self._get_speed_btn_style(False))
            btn.clicked.connect(lambda checked, val=i: self._set_speed(val))
            
            self.speed_group.addButton(btn, i)
            speed_layout.addWidget(btn)
            self.speed_btns.append(btn)

        layout.addLayout(speed_layout)
        layout.addSpacing(15) 
        # ---------------------------------------------------------

        # 4. 하단 보조 버튼
        aux_grid = QGridLayout(); aux_grid.setSpacing(8)
        h_aux = 45 
        
        aux_grid.addWidget(self._create_btn("반전", h=h_aux), 0, 0)
        aux_grid.addWidget(self._create_btn("반전 복귀", h=h_aux), 0, 1)
        aux_grid.addWidget(self._create_btn("회전", h=h_aux), 1, 0)
        aux_grid.addWidget(self._create_btn("회전 복귀", h=h_aux), 1, 1)
        # [수정] 버튼 이름 변경 (글자수 줄임)
        aux_grid.addWidget(self._create_btn("척 개", h=h_aux), 2, 0)
        aux_grid.addWidget(self._create_btn("척 폐", h=h_aux), 2, 1)

        layout.addLayout(aux_grid)
        layout.addStretch(1)
        main_layout.addWidget(self.container)

        self._set_speed(JogControlDialog._last_speed)

    def _create_btn(self, text, size=None, h=55):
        btn = QPushButton(text)
        if size: btn.setFixedSize(size[0], size[1])
        else: btn.setMinimumHeight(h)
        btn.setAttribute(Qt.WA_AcceptTouchEvents, True)
        btn.pressed.connect(lambda t=text: self._on_jog(t, True))
        btn.released.connect(lambda t=text: self._on_jog(t, False))
        return btn

    def _get_speed_btn_style(self, active):
        if active:
            return """
                QPushButton { 
                    background-color: rgba(0, 229, 255, 0.2); 
                    border: 2px solid #00E5FF; 
                    color: #00E5FF; 
                    border-radius: 5px; 
                    font-weight: bold; font-size: 16px;
                }
            """
        else:
            return """
                QPushButton { 
                    background-color: rgba(255, 255, 255, 0.05); 
                    border: 1px solid #444; 
                    color: #888; 
                    border-radius: 5px; 
                    font-weight: bold; font-size: 16px;
                }
                QPushButton:hover { border: 1px solid #666; color: #AAA; }
            """

    def _set_speed(self, val):
        JogControlDialog._last_speed = val
        for btn in self.speed_btns:
            if btn.text() == str(val):
                btn.setChecked(True)
                btn.setStyleSheet(self._get_speed_btn_style(True))
            else:
                btn.setChecked(False)
                btn.setStyleSheet(self._get_speed_btn_style(False))
        
        if self.plc_client and self.plc_client.is_connected:
            try:
                self.plc_client.write_words(0x09, 211, [val])
            except Exception as e:
                print(f"[JOG] Speed Error: {e}")

    def _on_jog(self, name, is_on):
        self.sig_jog_event.emit(name, is_on)
        if not self.plc_client or not self.plc_client.is_connected: return

        target_addr = 205
        area_code = 0x09
        
        bit_pos = -1
        
        if name == "주행 +": bit_pos = 0
        elif name == "주행 -": bit_pos = 1
        elif name == "상 (Z-)": bit_pos = 2
        elif name == "하 (Z+)": bit_pos = 3
        elif name == "전 (Y+)": bit_pos = 4
        elif name == "후 (Y-)": bit_pos = 5
        
        elif name == "반전": bit_pos = 6
        elif name == "회전": bit_pos = 7
        
        # [수정] 변경된 버튼 이름에 맞춰 조건문 수정
        elif name == "척 개": bit_pos = 8
        elif name == "척 폐": bit_pos = 9
        
        elif name == "반전 복귀": bit_pos = 10 
        elif name == "회전 복귀": bit_pos = 11

        if bit_pos >= 0:
            try:
                self.plc_client.write_bit(area_code, target_addr, bit_pos, is_on)
            except Exception as e:
                print(f"[JOG] Error: {e}")

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def close_overlay(self):
        if self._event_loop: self._event_loop.quit()
        self.close(); self.deleteLater()

    def exec(self):
        self.show(); self.raise_(); self._event_loop = QEventLoop(); self._event_loop.exec()