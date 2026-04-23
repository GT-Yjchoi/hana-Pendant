from PySide6.QtCore import Qt, Signal, QSize, QTimer, QEventLoop
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QGridLayout, QPushButton, QSizePolicy, QDialog, QApplication, QInputDialog
)

from widgets.glass_card import GlassCard

# [키패드 임포트]
try:
    from widgets.touch_number_keyboard import TouchNumberKeyboard
except ImportError:
    from PySide6.QtWidgets import QInputDialog
    TouchNumberKeyboard = None

# 언어 관리자 임포트
try:
    from utils.languages import LanguageManager
except ImportError:
    LanguageManager = None


# ==========================================================
# [핵심] 입력 오버레이 (Dialog 대신 화면 덮어씌우기)
# ==========================================================
class PackingInputOverlay(QWidget):
    Accepted = 1
    Rejected = 0

    def __init__(self, title, current_val, is_float=False, parent=None):
        super().__init__(parent)
        self.is_float = is_float
        
        # 부모 크기만큼 덮어씌우기
        if parent:
            self.resize(parent.size())
            
        # 반투명 배경
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)

        self.current_val = float(current_val) if is_float else int(current_val)
        self.result_code = self.Rejected
        self._event_loop = None

        # --- UI 구성 ---
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

        # 1. 타이틀
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color: #FFD700; font-size: 22px; font-weight: 900; margin-bottom: 5px;")
        box_layout.addWidget(lbl_title)

        # 1-2. 안내 문구
        desc = "설정값 변경 (소수점 가능)" if is_float else "설정값 변경 (정수)"
        lbl_desc = QLabel(desc)
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet("color: #AAA; font-size: 14px;")
        box_layout.addWidget(lbl_desc)

        # 2. 값 입력 버튼
        val_layout = QHBoxLayout()
        val_layout.setSpacing(10)

        self.btn_val = QPushButton()
        self.btn_val.setFixedHeight(80)
        self.btn_val.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_val.setAttribute(Qt.WA_AcceptTouchEvents, True)
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
        self.btn_up.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.btn_up.setStyleSheet("background-color: #34495E; color: #2ECC71; font-size: 20px;")
        self.btn_up.clicked.connect(self._increase)
        
        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedSize(60, 38)
        self.btn_down.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.btn_down.setStyleSheet("background-color: #34495E; color: #E74C3C; font-size: 20px;")
        self.btn_down.clicked.connect(self._decrease)
        
        ud_layout.addWidget(self.btn_up)
        ud_layout.addWidget(self.btn_down)
        val_layout.addLayout(ud_layout)
        box_layout.addLayout(val_layout)

        # 3. 저장/취소
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.btn_cancel = QPushButton("취소")
        self.btn_cancel.setFixedHeight(50)
        self.btn_cancel.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.btn_cancel.setStyleSheet("background-color: #582F2F; color: white; border: 1px solid #C0392B;")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("저장")
        self.btn_save.setFixedHeight(50)
        self.btn_save.setAttribute(Qt.WA_AcceptTouchEvents, True)
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
        if self._event_loop: self._event_loop.quit()

    def reject(self):
        self.result_code = self.Rejected
        if self._event_loop: self._event_loop.quit()

    def _update_display(self):
        if self.is_float:
            self.btn_val.setText(f"{self.current_val:.2f}")
        else:
            self.btn_val.setText(f"{int(self.current_val)}")

    def _open_keypad(self):
        # [핵심] 소수점 문제 해결
        # 정수면 0, 실수면 2 (소수점 2자리)
        precision = 2 if self.is_float else 0
        
        str_val = f"{self.current_val:.2f}" if self.is_float else str(int(self.current_val))
        
        if TouchNumberKeyboard:
            # self를 부모로 하여 포커스 유지
            dlg = TouchNumberKeyboard(str_val, precision, parent=self)
            
            # 키패드도 띄우는 방식 통일 (Overlay 위라 크게 상관없음)
            dlg.show()
            dlg.activateWindow()
            dlg.raise_()
            QApplication.processEvents()
            
            if dlg.exec() == 1:
                try:
                    val = float(dlg.get_value())
                    if not self.is_float:
                        self.current_val = int(val)
                    else:
                        self.current_val = round(val, 2)
                    self._update_display()
                except ValueError: pass
        else:
            if self.is_float:
                val, ok = QInputDialog.getDouble(self, "입력", "값:", self.current_val, 0, 9999, 2)
            else:
                val, ok = QInputDialog.getInt(self, "입력", "값:", int(self.current_val), 1, 9999, 1)
            
            if ok:
                self.current_val = val
                self._update_display()

    def _increase(self):
        if self.is_float:
            self.current_val += 0.1
        else:
            self.current_val += 1
        self._update_display()

    def _decrease(self):
        if self.is_float:
            if self.current_val >= 0.1: self.current_val -= 0.1
        else:
            if self.current_val > 1: self.current_val -= 1
        self._update_display()

    def get_value(self):
        return self.current_val


# =========================================================
# [위젯] 팔레트 시각화
# =========================================================
class PalletVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(300) 
        
        self.x_count = 5
        self.y_count = 4
        self.z_count = 3
        
        self.cur_step_x = 0
        self.cur_step_y = 0
        self.cur_z = 0
        
        self.x_dir = 1 
        self.y_dir = 1 
        
        self.sim_state = 0 

        self.txt_z_level = "Z"
        self.txt_mc = " Injection MC (사출기)"
        self.update_language()

    def update_status(self, xc, yc, zc, cx, cy, cz, xd, yd, state=0):
        self.x_count = max(1, xc)
        self.y_count = max(1, yc)
        self.z_count = max(1, zc)
        self.cur_step_x = cx
        self.cur_step_y = cy
        self.cur_z = cz
        self.x_dir = xd
        self.y_dir = yd
        self.sim_state = state
        self.update() 

    def update_language(self):
        if LanguageManager:
            lm = LanguageManager.instance()
            t = lm.get_text("z_level")
            self.txt_z_level = t if t != "z_level" else "Z"
            t = lm.get_text("sim_mc")
            self.txt_mc = t if t != "sim_mc" else " Injection MC (사출기)"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        w = rect.width()
        h = rect.height()
        
        bg_color = QColor(30, 35, 45)
        painter.fillRect(rect, bg_color)
        
        margin = 15 
        
        # --- Z축 ---
        z_bar_width = 30
        z_area_x = w - margin - z_bar_width
        z_label_h = 20                              # "높이" 라벨 영역
        z_bar_y = margin + z_label_h                # Z바는 라벨 아래부터 시작
        z_area_h = h - z_bar_y - margin

        # "높이" 라벨 (Z바 위쪽 — 겹침 없음)
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.drawText(z_area_x - 4, margin, z_bar_width + 8, z_label_h,
                         Qt.AlignCenter, self.txt_z_level)

        # Z바 배경
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(50, 55, 65))
        painter.drawRoundedRect(z_area_x, z_bar_y, z_bar_width, z_area_h, 5, 5)

        # 현재 Z레벨 채움
        if self.z_count > 0:
            current_display_z = self.cur_z
            if self.sim_state == 2:
                current_display_z = self.z_count
            else:
                current_display_z += 1

            fill_h = (z_area_h / self.z_count) * current_display_z
            fill_h = min(fill_h, z_area_h)

            color = "#64FF64" if self.sim_state == 2 else "#FFD280"
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(z_area_x, z_bar_y + z_area_h - fill_h, z_bar_width, fill_h, 5, 5)
        
        # --- 사출기 ---
        grid_area_w = z_area_x - 2 * margin 
        mc_height = 40 
        mc_gap = 10    
        
        painter.setPen(QPen(QColor(100, 100, 100), 2, Qt.DashLine))
        painter.setBrush(QColor(60, 70, 80)) 
        painter.drawRoundedRect(margin, margin, grid_area_w, mc_height, 8, 8)
        
        painter.setPen(QColor("#FFD280")) 
        painter.setFont(QFont("Arial", 13, QFont.Bold))
        painter.drawText(margin, margin, grid_area_w, mc_height, Qt.AlignCenter, self.txt_mc)

        # --- 그리드 ---
        grid_start_y = margin + mc_height + mc_gap
        grid_area_h = h - grid_start_y - margin 
        
        cell_w = grid_area_w / self.y_count
        cell_h = grid_area_h / self.x_count
        
        start_x = margin
        start_y = grid_start_y
        
        if self.x_dir > 0: target_row = self.cur_step_x 
        else: target_row = (self.x_count - 1) - self.cur_step_x

        if self.y_dir > 0: target_col = (self.y_count - 1) - self.cur_step_y
        else: target_col = self.cur_step_y

        for row in range(self.x_count):
            for col in range(self.y_count):
                dx = start_x + col * cell_w
                dy = start_y + row * cell_h
                
                painter.setPen(QPen(QColor(80, 90, 110), 2))
                painter.setBrush(QColor(40, 45, 55))
                
                is_head = (row == target_row and col == target_col) and (self.sim_state != 2)
                
                if is_head:
                    painter.setBrush(QColor("#00E5FF"))
                    painter.setPen(Qt.NoPen)
                elif self.sim_state == 2:
                    painter.setBrush(QColor(60, 65, 75))

                painter.drawRoundedRect(dx + 2, dy + 2, cell_w - 4, cell_h - 4, 4, 4)
                
                if is_head:
                    painter.setPen(Qt.black)
                    painter.setFont(QFont("Arial", 10, QFont.Bold))
                    painter.drawText(dx, dy, cell_w, cell_h, Qt.AlignCenter, "HEAD")
                else:
                    painter.setPen(QColor(100, 100, 100))
                    painter.setFont(QFont("Arial", 9))
                    painter.drawText(dx, dy, cell_w, cell_h, Qt.AlignCenter, f"{row+1},{col+1}")


# =========================================================
# [위젯] 축 제어 패널 (수정: 오버레이 적용)
# =========================================================
class AxisControlPanel(QFrame):
    config_changed = Signal()
    current_clicked = Signal(str)   # 사용자가 "현재위치(No.)" 클릭 → 축 이름 emit
    enable_changed = Signal(bool)   # 패킹 사용 토글 (is_enable_host=True 인 패널만 발화)

    def __init__(self, axis_name, color_theme, is_z_axis=False, is_enable_host=False):
        super().__init__()
        self.axis_name = axis_name
        self.is_z_axis = is_z_axis
        self.is_enable_host = is_enable_host

        self.val_count = 1
        self.val_pitch = 10.0
        
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 8, 10, 8)

        # 패킹 사용 토글 (X축 패널에만 표시).
        # Y/Z 패널은 같은 높이의 투명 스페이서를 넣어 타이틀 수직 위치 정렬.
        if is_enable_host:
            self.btn_pack_enable = QPushButton()
            self.btn_pack_enable.setCheckable(True)
            self.btn_pack_enable.setChecked(False)
            self.btn_pack_enable.setFixedHeight(68)
            self.btn_pack_enable.setCursor(Qt.PointingHandCursor)
            self.btn_pack_enable.clicked.connect(self._on_pack_enable_toggled)
            self._update_pack_enable_style()
            layout.addWidget(self.btn_pack_enable)
        else:
            self.btn_pack_enable = None
            spacer = QWidget()
            spacer.setFixedHeight(68)
            spacer.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            layout.addWidget(spacer)

        # 타이틀
        self.lbl_title = QLabel(f"{axis_name} 축 설정")
        self.lbl_title.setStyleSheet(f"color: {color_theme}; font-size: 16px; font-weight: 900; background: transparent; border: none;")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_title)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background: rgba(255,255,255,0.2); border: none; max-height: 1px;")
        layout.addWidget(line)

        # 1. 현재 위치 (클릭 시 사용자 임의 변경 가능)
        row1 = QHBoxLayout()
        self.lbl_cur = QLabel("현재위치(No.)")
        self.lbl_cur.setStyleSheet("color: #AAA; font-size: 14px; background: transparent; border: none;")
        self.disp_current = QPushButton("0")
        self.disp_current.setCursor(Qt.PointingHandCursor)
        self.disp_current.setStyleSheet(
            f"QPushButton {{ color: white; font-size: 22px; font-weight: bold; "
            f"background: rgba(0,0,0,0.3); border-radius: 4px; padding-right: 10px; "
            f"border: 1px solid {color_theme}; text-align: right; }} "
            f"QPushButton:pressed {{ background: rgba(70,140,255,0.3); border: 1px solid #468CFF; }}"
        )
        self.disp_current.setFixedHeight(34)
        self.disp_current.clicked.connect(
            lambda: self.current_clicked.emit(self.axis_name.lower())
        )
        row1.addWidget(self.lbl_cur)
        row1.addWidget(self.disp_current)
        layout.addLayout(row1)

        # 2. 설정 횟수
        row2 = QHBoxLayout()
        self.lbl_set = QLabel("설정횟수(EA)")
        self.lbl_set.setStyleSheet("color: #AAA; font-size: 14px; background: transparent; border: none;")

        self.btn_count = QPushButton(str(self.val_count))
        self.btn_count.setCursor(Qt.PointingHandCursor)
        self.btn_count.setFixedHeight(34)
        self.btn_count.setStyleSheet(self._input_btn_style())
        self.btn_count.clicked.connect(self._on_count_clicked)

        row2.addWidget(self.lbl_set)
        row2.addWidget(self.btn_count)
        layout.addLayout(row2)

        # 3. 설정 피치
        row3 = QHBoxLayout()
        self.lbl_pitch = QLabel("설정피치(mm)")
        self.lbl_pitch.setStyleSheet("color: #AAA; font-size: 14px; background: transparent; border: none;")

        self.btn_pitch = QPushButton(f"{self.val_pitch:.2f}")
        self.btn_pitch.setCursor(Qt.PointingHandCursor)
        self.btn_pitch.setFixedHeight(34)
        self.btn_pitch.setStyleSheet(self._input_btn_style())
        self.btn_pitch.clicked.connect(self._on_pitch_clicked)

        row3.addWidget(self.lbl_pitch)
        row3.addWidget(self.btn_pitch)
        layout.addLayout(row3)

        # 4. 방향 설정 (Z축 포함 모든 축에 표시)
        #    X/Y 기본: + 방향 (검사 ON)
        #    Z    기본: - 방향 (위로 쌓기: 로봇 좌표계에서 Z- 가 위쪽)
        self.lbl_dir = QLabel("진행 방향")
        self.lbl_dir.setStyleSheet("color: #AAA; font-size: 13px; background: transparent; border: none; margin-top: 3px;")
        layout.addWidget(self.lbl_dir)

        self.btn_dir = QPushButton("+ 방향 (정방향)")
        self.btn_dir.setCheckable(True)
        self.btn_dir.setChecked(not is_z_axis)   # Z 는 기본 -방향
        self.btn_dir.setFixedHeight(38)
        self.btn_dir.setCursor(Qt.PointingHandCursor)
        self.btn_dir.clicked.connect(self._on_dir_toggle)
        self._update_dir_style()
        layout.addWidget(self.btn_dir)

        layout.addStretch(1)
        self.update_language()

    def update_language(self):
        if LanguageManager:
            lm = LanguageManager.instance()
            
            t = lm.get_text("axis_set")
            suffix = t if t != "axis_set" else " 축 설정"
            self.lbl_title.setText(f"{self.axis_name}{suffix}")
            
            self.lbl_cur.setText(lm.get_text("curr_pos"))
            self.lbl_set.setText(lm.get_text("set_cnt"))
            self.lbl_pitch.setText(lm.get_text("set_pitch"))

            if self.btn_dir:
                self.lbl_dir.setText(lm.get_text("dir_label"))
                self._update_dir_text()

    def _update_dir_text(self):
        if not self.btn_dir: return
        if LanguageManager:
            lm = LanguageManager.instance()
            if self.btn_dir.isChecked():
                self.btn_dir.setText(lm.get_text("dir_pos"))
            else:
                self.btn_dir.setText(lm.get_text("dir_neg"))

    def _input_btn_style(self):
        return """
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                color: white;
                font-size: 20px;
                font-weight: bold;
                text-align: right;
                padding-right: 10px;
            }
            QPushButton:pressed {
                background: rgba(70, 140, 255, 0.3);
                border: 1px solid #468CFF;
            }
        """

    def _on_dir_toggle(self):
        self._update_dir_text()
        self._update_dir_style()
        self.config_changed.emit()

    def _update_dir_style(self):
        if self.btn_dir.isChecked():
            self.btn_dir.setStyleSheet("""
                QPushButton { background: rgba(0, 229, 255, 0.2); border: 2px solid #00E5FF; color: #00E5FF; border-radius: 8px; font-size: 15px; font-weight: bold; }
            """)
        else:
            self.btn_dir.setStyleSheet("""
                QPushButton { background: rgba(255, 80, 80, 0.2); border: 2px solid #FF5050; color: #FF5050; border-radius: 8px; font-size: 15px; font-weight: bold; }
            """)

    def _on_count_clicked(self):
        # [수정] 오버레이 호출 (정수 모드)
        # self.window()를 부모로 주어 전체 화면을 덮음
        dlg = PackingInputOverlay("설정 횟수", self.val_count, is_float=False, parent=self.window())
        if dlg.exec() == PackingInputOverlay.Accepted:
            self.val_count = int(dlg.get_value())
            self.val_count = max(1, self.val_count)
            self.btn_count.setText(str(self.val_count))
            self.config_changed.emit()

    def _on_pitch_clicked(self):
        # [수정] 오버레이 호출 (실수 모드) -> 소수점 문제 해결
        dlg = PackingInputOverlay("설정 피치", self.val_pitch, is_float=True, parent=self.window())
        if dlg.exec() == PackingInputOverlay.Accepted:
            self.val_pitch = float(dlg.get_value())
            self.val_pitch = max(0.0, self.val_pitch)
            self.btn_pitch.setText(f"{self.val_pitch:.2f}")
            self.config_changed.emit()

    def get_values(self):
        direction = 1
        if self.btn_dir and not self.btn_dir.isChecked():
            direction = -1
        return self.val_count, self.val_pitch, direction

    def set_current_display(self, val):
        self.disp_current.setText(str(val))

    # ───── 패킹 사용 토글 (is_enable_host=True 인 패널에만 존재) ─────
    def _on_pack_enable_toggled(self):
        self._update_pack_enable_style()
        # 스타일 적용을 스캔 큐에 예약만 하면 이후 느린 PLC 송신이 끝날 때까지 리페인트가 미뤄짐.
        # repaint() 로 강제 동기 그리기 → 버튼 상태 전환이 즉각 보이도록.
        self.btn_pack_enable.repaint()
        self.enable_changed.emit(bool(self.btn_pack_enable.isChecked()))

    def set_pack_enabled(self, enabled):
        """외부에서 초기 상태 세팅 (레시피 로드 후). signal 발화 안 함."""
        if self.btn_pack_enable is None:
            return
        self.btn_pack_enable.blockSignals(True)
        self.btn_pack_enable.setChecked(bool(enabled))
        self.btn_pack_enable.blockSignals(False)
        self._update_pack_enable_style()

    def _update_pack_enable_style(self):
        if self.btn_pack_enable is None:
            return
        if self.btn_pack_enable.isChecked():
            self.btn_pack_enable.setText("● 패킹 사용")
            self.btn_pack_enable.setStyleSheet(
                "QPushButton { background: rgba(0,255,127,0.2); border: 2px solid #00FF7F; "
                "color: #00FF7F; border-radius: 8px; font-size: 24px; font-weight: bold; }"
            )
        else:
            self.btn_pack_enable.setText("○ 패킹 미사용")
            self.btn_pack_enable.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2); "
                "color: #888; border-radius: 8px; font-size: 24px; font-weight: bold; } "
                "QPushButton:hover { background: rgba(255,255,255,0.1); border: 1px solid #00FF7F; color: #AAA; }"
            )


# =========================================================
# [메인 페이지] PagePacking
# =========================================================
class PagePacking(GlassCard):
    sig_packing_changed = Signal()

    def __init__(self, position_points=None, sequence_data=None, plc_client=None, packing_config=None):
        super().__init__("")

        self.position_points = position_points if position_points is not None else {}
        self.sequence_data = sequence_data if sequence_data is not None else {}
        self.plc_client = plc_client
        self.packing_config = packing_config if packing_config is not None else {}

        if hasattr(self, 'title_label'):
            self.title_label.hide()
            if self.title_label.parentWidget() and self.title_label.parentWidget() != self:
                self.title_label.parentWidget().hide()

        if self.layout():
            self.layout().setContentsMargins(10, 5, 10, 10)

        main_layout = QHBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 왼쪽 시각화 영역
        vis_container = QFrame()
        vis_container.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        vis_container.setStyleSheet("background: rgba(0,0,0,0.2); border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);")
        vis_layout = QVBoxLayout(vis_container)
        vis_layout.setContentsMargins(10, 10, 10, 10)
        
        self.vis_title = QLabel()
        self.vis_title.setAlignment(Qt.AlignCenter)
        self.vis_title.setStyleSheet("color: #DDD; font-size: 16px; font-weight: bold; border:none; background: transparent; margin-bottom: 5px;")
        vis_layout.addWidget(self.vis_title)

        self.lbl_base_points = QLabel()
        self.lbl_base_points.setAlignment(Qt.AlignCenter)
        self.lbl_base_points.setWordWrap(True)
        self.lbl_base_points.setStyleSheet(
            "color: #64FFDA; font-size: 13px; font-weight: bold; border:none; background: transparent;"
        )
        vis_layout.addWidget(self.lbl_base_points)
        
        sim_ctrl_layout = QHBoxLayout()
        sim_ctrl_layout.setSpacing(10)
        
        self.btn_order = QPushButton()
        self.btn_order.setFixedHeight(45)
        self.btn_order.setCursor(Qt.PointingHandCursor)
        self.btn_order.clicked.connect(self._on_order_toggle)
        sim_ctrl_layout.addWidget(self.btn_order, 1)
        
        self.btn_play = QPushButton()
        self.btn_play.setFixedHeight(45)
        self.btn_play.setCheckable(True)
        self.btn_play.setCursor(Qt.PointingHandCursor)
        self.btn_play.clicked.connect(self._on_sim_play_clicked)
        self.btn_play.setStyleSheet("""
            QPushButton { background: rgba(0, 255, 127, 0.2); border: 2px solid #00FF7F; color: #00FF7F; border-radius: 8px; font-weight: bold; font-size: 14px; }
            QPushButton:checked { background: rgba(255, 70, 70, 0.2); border: 2px solid #FF4646; color: #FF4646; }
            QPushButton:hover { background: rgba(255, 255, 255, 0.1); }
        """)
        sim_ctrl_layout.addWidget(self.btn_play, 1)
        vis_layout.addLayout(sim_ctrl_layout)
        
        self.visualizer = PalletVisualizer()
        vis_layout.addWidget(self.visualizer, 1)
        
        main_layout.addWidget(vis_container, 4)
        
        # 오른쪽 설정 영역
        right_widget = QWidget()
        right_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        
        settings_layout = QHBoxLayout(right_widget)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(10)
        
        self.panel_x = AxisControlPanel("X", "#00E5FF", is_enable_host=True)
        self.panel_y = AxisControlPanel("Y", "#FFD280")
        self.panel_z = AxisControlPanel("Z", "#64FFDA", is_z_axis=True)

        self.panel_x.config_changed.connect(self._on_config_changed_internal)
        self.panel_y.config_changed.connect(self._on_config_changed_internal)
        self.panel_z.config_changed.connect(self._on_config_changed_internal)

        self.panel_x.current_clicked.connect(self._on_current_idx_clicked)
        self.panel_y.current_clicked.connect(self._on_current_idx_clicked)
        self.panel_z.current_clicked.connect(self._on_current_idx_clicked)

        self.panel_x.enable_changed.connect(self._on_pack_enable_toggled)

        settings_layout.addWidget(self.panel_x)
        settings_layout.addWidget(self.panel_y)
        settings_layout.addWidget(self.panel_z)

        main_layout.addWidget(right_widget, 6)

        self.body.addLayout(main_layout)

        self.anim_x = 0; self.anim_y = 0; self.anim_z = 0
        self.sim_timer = QTimer(self)
        self.sim_timer.setInterval(300)
        self.sim_timer.timeout.connect(self._update_animation)

        self.stack_order = 0
        self.update_language()
        self._refresh_base_points_label()

        # PLC 모니터링 시그널 구독 (pack_idx 수신 시 베이스 포인트 좌표 갱신)
        if self.plc_client:
            self.plc_client.sig_monitor_data.connect(self._on_monitor_data)

        # 초기 config 반영 (packing_config dict에 값이 있으면 UI에 로드)
        if self.packing_config:
            self.refresh_ui()

    def update_language(self, lang_code=None):
        if not LanguageManager: return
        lm = LanguageManager.instance()
        
        self.vis_title.setText(lm.get_text("sim_title"))
        
        self._update_order_btn_text()
        self._update_play_btn_text()
        
        self.visualizer.update_language()
        self.panel_x.update_language()
        self.panel_y.update_language()
        self.panel_z.update_language()

    def showEvent(self, event):
        self._refresh_base_points_label()
        self._reset_and_play()   # sim_timer 시작
        super().showEvent(event)

    def hideEvent(self, event):
        # [S-4] 페이지 숨김 시 시뮬레이션 타이머 중단 — 백그라운드 300ms 주기 paint 방지
        if hasattr(self, 'sim_timer') and self.sim_timer.isActive():
            self.sim_timer.stop()
        super().hideEvent(event)

    # 6가지 적층 순서: 첫 축이 가장 내부 루프 (가장 빨리 증가)
    STACK_ORDERS = [
        ("x", "y", "z"),  # 0: X → Y → Z
        ("x", "z", "y"),  # 1: X → Z → Y
        ("y", "x", "z"),  # 2: Y → X → Z
        ("y", "z", "x"),  # 3: Y → Z → X
        ("z", "x", "y"),  # 4: Z → X → Y
        ("z", "y", "x"),  # 5: Z → Y → X
    ]
    STACK_ORDER_STYLES = [
        ("#468CFF", "rgba(70, 140, 255, 0.2)"),
        ("#FF9F80", "rgba(255, 159, 128, 0.2)"),
        ("#FFD280", "rgba(255, 210, 128, 0.2)"),
        ("#C9FF80", "rgba(201, 255, 128, 0.2)"),
        ("#64FFDA", "rgba(100, 255, 218, 0.2)"),
        ("#E040FB", "rgba(224, 64, 251, 0.2)"),
    ]

    def _on_order_toggle(self):
        self.stack_order = (self.stack_order + 1) % len(self.STACK_ORDERS)
        self._update_order_btn_text()
        self._on_config_changed_internal()

    def _update_order_btn_text(self):
        order = self.STACK_ORDERS[self.stack_order % len(self.STACK_ORDERS)]
        color, bg = self.STACK_ORDER_STYLES[self.stack_order % len(self.STACK_ORDER_STYLES)]
        label = "→".join(ax.upper() for ax in order)
        self.btn_order.setText(label)
        self.btn_order.setStyleSheet(f"""
            QPushButton {{ background: {bg}; border: 2px solid {color}; color: {color};
                           border-radius: 8px; font-weight: bold; font-size: 14px; }}
            QPushButton:hover {{ background: rgba(255, 255, 255, 0.1); }}
        """)

    def _on_sim_play_clicked(self):
        if self.btn_play.isChecked():
            zc, _, _ = self.panel_z.get_values()
            if self.anim_z >= zc:
                self.anim_x = 0; self.anim_y = 0; self.anim_z = 0
            
            self._update_play_btn_text()
            self.sim_timer.start()
            self._update_visualizer(state=1)
        else:
            self._stop_simulation()

    def _update_play_btn_text(self):
        if not LanguageManager: return
        lm = LanguageManager.instance()
        if self.btn_play.isChecked():
            self.btn_play.setText(lm.get_text("btn_stop"))
        else:
            self.btn_play.setText(lm.get_text("btn_play"))

    def _stop_simulation(self, finished=False):
        self.sim_timer.stop()
        self.btn_play.setChecked(False)
        self._update_play_btn_text()
        if finished:
            self._update_visualizer(state=2)

    def _reset_and_play(self):
        self.sim_timer.stop()
        self.anim_x = 0; self.anim_y = 0; self.anim_z = 0
        self.btn_play.setChecked(True)
        self._update_play_btn_text()
        self.sim_timer.start()
        self._update_visualizer(state=1)

    def _on_config_changed_internal(self):
        """설정값 변경 시 config dict 동기화 + 자동저장 트리거 + 시뮬 재시작
        + PLC 로 패킹 설정 즉시 전송"""
        self._sync_to_packing_config()
        self.sig_packing_changed.emit()
        self._reset_and_play()
        if self.plc_client and self.plc_client.is_connected:
            self.plc_client.send_packing_config(self.packing_config)

    def _on_pack_enable_toggled(self, enabled):
        """패킹 사용 토글 (X축 패널 버튼) → packing_config['enabled'] 갱신.
        PLC 송신·자동저장은 sig_packing_changed 로 main_window 가 일괄 처리 (중복 송신 방지)."""
        self.packing_config["enabled"] = bool(enabled)
        self.sig_packing_changed.emit()

    def _sync_to_packing_config(self):
        """AxisControlPanel 현재값 → self.packing_config dict"""
        cfg = self.get_packing_config()
        self.packing_config.clear()
        self.packing_config.update(cfg)

    def get_packing_config(self):
        xc, xp, xd = self.panel_x.get_values()
        yc, yp, yd = self.panel_y.get_values()
        zc, zp, zd = self.panel_z.get_values()
        cfg = {
            "x_count": int(xc), "x_pitch": float(xp), "x_dir": int(xd),
            "y_count": int(yc), "y_pitch": float(yp), "y_dir": int(yd),
            "z_count": int(zc), "z_pitch": float(zp), "z_dir": int(zd),
            "stack_order": int(self.stack_order),
        }
        if self.panel_x.btn_pack_enable is not None:
            cfg["enabled"] = bool(self.panel_x.btn_pack_enable.isChecked())
        else:
            cfg["enabled"] = bool(self.packing_config.get("enabled", False))
        return cfg

    def refresh_ui(self):
        """packing_config dict → UI 복원 (레시피 로드 후 호출)"""
        cfg = self.packing_config or {}

        def _apply(panel, count, pitch, direction=None):
            panel.val_count = max(1, int(count))
            panel.val_pitch = float(pitch)
            panel.btn_count.setText(str(panel.val_count))
            panel.btn_pitch.setText(f"{panel.val_pitch:.2f}")
            if direction is not None and panel.btn_dir is not None:
                panel.btn_dir.setChecked(int(direction) > 0)
                panel._update_dir_text()
                panel._update_dir_style()

        _apply(self.panel_x, cfg.get("x_count", 5), cfg.get("x_pitch", 10.0), cfg.get("x_dir", 1))
        _apply(self.panel_y, cfg.get("y_count", 4), cfg.get("y_pitch", 10.0), cfg.get("y_dir", 1))
        _apply(self.panel_z, cfg.get("z_count", 3), cfg.get("z_pitch", 10.0), cfg.get("z_dir", -1))

        # 패킹 사용 토글 상태 복원 (default False — 명시 플래그 없으면 미사용)
        self.panel_x.set_pack_enabled(bool(cfg.get("enabled", False)))

        self.stack_order = int(cfg.get("stack_order", 0)) % len(self.STACK_ORDERS)
        self._update_order_btn_text()
        self._refresh_base_points_label()
        self._reset_and_play()

    def _collect_pack_base_point_names(self):
        """모든 시퀀스의 POS 스텝 중 pack_base=True인 스텝의 point_name 집합 반환"""
        names = []
        seen = set()
        sequences = self.sequence_data
        if isinstance(sequences, list):
            sequences = {"Main": sequences}
        if not isinstance(sequences, dict):
            return names
        for steps in sequences.values():
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if step.get("type") != "POS":
                    continue
                if not step.get("pack_base"):
                    continue
                p_name = step.get("point_name")
                if not p_name or p_name in seen:
                    continue
                seen.add(p_name)
                names.append(p_name)
        return names

    def _refresh_base_points_label(self):
        """시퀀스 POS 스텝 중 pack_base=True인 스텝의 포인트들을 표시"""
        if not hasattr(self, 'lbl_base_points'):
            return
        bases = self._collect_pack_base_point_names()
        if bases:
            self.lbl_base_points.setText("베이스: " + ", ".join(bases))
        else:
            self.lbl_base_points.setText(
                "⚠ 시퀀스 편집기의 POS 스텝에서 '파렛타이징 베이스'를 체크하세요"
            )

    def _on_monitor_data(self, data):
        """PLC monitor_data 수신 → 현재 pack_idx 표시만 (좌표 덮어쓰기는 PLC 내부 fb_Packing 담당)"""
        pack_idx = list(data.get('pack_idx', [0, 0, 0]))
        self.panel_x.set_current_display(pack_idx[0] + 1)
        self.panel_y.set_current_display(pack_idx[1] + 1)
        self.panel_z.set_current_display(pack_idx[2] + 1)

    def _on_current_idx_clicked(self, axis):
        """사용자가 현재위치(No.)를 클릭 → 임의 인덱스로 변경"""
        if not self.plc_client or not self.plc_client.is_connected:
            return
        counts = {
            "x": self.panel_x.get_values()[0],
            "y": self.panel_y.get_values()[0],
            "z": self.panel_z.get_values()[0],
        }
        max_idx = max(1, int(counts.get(axis, 1)))
        # 현재 표시값 (1-based) → 편집 후 0-based 로 PLC 에 기록
        cur_disp = {
            "x": self.panel_x.disp_current.text(),
            "y": self.panel_y.disp_current.text(),
            "z": self.panel_z.disp_current.text(),
        }.get(axis, "1")
        try:
            cur_val = max(1, int(cur_disp))
        except ValueError:
            cur_val = 1

        dlg = PackingInputOverlay(
            f"{axis.upper()} 축 현재위치 (1 ~ {max_idx})",
            cur_val,
            is_float=False,
            parent=self.window(),
        )
        if dlg.exec() == PackingInputOverlay.Accepted:
            new_val = int(dlg.get_value())
            new_val = max(1, min(max_idx, new_val))
            # PLC 에는 0-based 로 기록
            self.plc_client.write_pack_idx(axis, new_val - 1)

    def _update_animation(self):
        counts = {
            "x": self.panel_x.get_values()[0],
            "y": self.panel_y.get_values()[0],
            "z": self.panel_z.get_values()[0],
        }
        anim = {"x": self.anim_x, "y": self.anim_y, "z": self.anim_z}
        order = self.STACK_ORDERS[self.stack_order % len(self.STACK_ORDERS)]

        # 첫 축부터 증가, 카운트 도달하면 리셋 + 다음 축 증가, ...
        finished = False
        for i, ax in enumerate(order):
            anim[ax] += 1
            if anim[ax] >= counts[ax]:
                if i == len(order) - 1:
                    # 마지막 축까지 오버플로 → 전체 완료
                    finished = True
                    break
                anim[ax] = 0
            else:
                break

        self.anim_x, self.anim_y, self.anim_z = anim["x"], anim["y"], anim["z"]

        if finished:
            last_ax = order[-1]
            if last_ax == "x": self.anim_x = counts["x"]
            elif last_ax == "y": self.anim_y = counts["y"]
            else: self.anim_z = counts["z"]
            self._stop_simulation(finished=True)
            return

        self._update_visualizer(state=1)

    def _update_visualizer(self, state):
        xc, _, xd = self.panel_x.get_values()
        yc, _, yd = self.panel_y.get_values()
        zc, _, _ = self.panel_z.get_values()
        self.visualizer.update_status(xc, yc, zc, self.anim_x, self.anim_y, self.anim_z, xd, yd, state)