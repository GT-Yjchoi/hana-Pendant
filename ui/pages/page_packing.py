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

        self.txt_z_level = "Z-Lev"
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
            self.txt_z_level = t if t != "z_level" else "Z-Lev"
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
        z_area_h = h - 2 * margin
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(50, 55, 65))
        painter.drawRoundedRect(z_area_x, margin, z_bar_width, z_area_h, 5, 5)
        
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
            painter.drawRoundedRect(z_area_x, margin + z_area_h - fill_h, z_bar_width, fill_h, 5, 5)
            
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 9))
        painter.drawText(z_area_x, margin - 2, z_bar_width, 15, Qt.AlignCenter, self.txt_z_level)
        
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

    def __init__(self, axis_name, color_theme, is_z_axis=False):
        super().__init__()
        self.axis_name = axis_name 
        self.is_z_axis = is_z_axis
        
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
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 타이틀
        self.lbl_title = QLabel(f"{axis_name} 축 설정")
        self.lbl_title.setStyleSheet(f"color: {color_theme}; font-size: 18px; font-weight: 900; background: transparent; border: none;")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_title)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background: rgba(255,255,255,0.2); border: none; max-height: 1px;")
        layout.addWidget(line)

        # 1. 현재 위치
        row1 = QHBoxLayout()
        self.lbl_cur = QLabel("현재위치(No.)")
        self.lbl_cur.setStyleSheet("color: #AAA; font-size: 14px; background: transparent; border: none;")
        self.disp_current = QLabel("0")
        self.disp_current.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.disp_current.setStyleSheet(f"color: white; font-size: 22px; font-weight: bold; background: rgba(0,0,0,0.3); border-radius: 4px; padding-right: 10px; border: 1px solid {color_theme};")
        self.disp_current.setFixedHeight(38)
        row1.addWidget(self.lbl_cur)
        row1.addWidget(self.disp_current)
        layout.addLayout(row1)

        # 2. 설정 횟수
        row2 = QHBoxLayout()
        self.lbl_set = QLabel("설정횟수(EA)")
        self.lbl_set.setStyleSheet("color: #AAA; font-size: 14px; background: transparent; border: none;")
        
        self.btn_count = QPushButton(str(self.val_count))
        self.btn_count.setCursor(Qt.PointingHandCursor)
        self.btn_count.setFixedHeight(42)
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
        self.btn_pitch.setFixedHeight(42)
        self.btn_pitch.setStyleSheet(self._input_btn_style())
        self.btn_pitch.clicked.connect(self._on_pitch_clicked)
        
        row3.addWidget(self.lbl_pitch)
        row3.addWidget(self.btn_pitch)
        layout.addLayout(row3)

        # 4. 방향 설정
        if not is_z_axis:
            self.lbl_dir = QLabel("진행 방향")
            self.lbl_dir.setStyleSheet("color: #AAA; font-size: 14px; background: transparent; border: none; margin-top: 5px;")
            layout.addWidget(self.lbl_dir)
            
            self.btn_dir = QPushButton("+ 방향 (정방향)")
            self.btn_dir.setCheckable(True)
            self.btn_dir.setChecked(True)
            self.btn_dir.setFixedHeight(45)
            self.btn_dir.setCursor(Qt.PointingHandCursor)
            self.btn_dir.clicked.connect(self._on_dir_toggle)
            self._update_dir_style()
            layout.addWidget(self.btn_dir)
        else:
            self.lbl_dir = None
            self.btn_dir = None

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
            
            if not self.is_z_axis:
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


# =========================================================
# [메인 페이지] PagePacking
# =========================================================
class PagePacking(GlassCard):
    def __init__(self):
        super().__init__("")
        
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
        
        self.panel_x = AxisControlPanel("X", "#00E5FF")
        self.panel_y = AxisControlPanel("Y", "#FFD280")
        self.panel_z = AxisControlPanel("Z", "#64FFDA", is_z_axis=True)
        
        self.panel_x.config_changed.connect(self._reset_and_play)
        self.panel_y.config_changed.connect(self._reset_and_play)
        self.panel_z.config_changed.connect(self._reset_and_play)
        
        settings_layout.addWidget(self.panel_x)
        settings_layout.addWidget(self.panel_y)
        settings_layout.addWidget(self.panel_z)
        
        main_layout.addWidget(right_widget, 6)
        
        self.body.addLayout(main_layout)
        
        self.plc_x = 0; self.plc_y = 0; self.plc_z = 0
        self.plc_timer = QTimer(self)
        self.plc_timer.timeout.connect(self._update_plc_data)
        self.plc_timer.start(1000)

        self.anim_x = 0; self.anim_y = 0; self.anim_z = 0
        self.sim_timer = QTimer(self)
        self.sim_timer.setInterval(300) 
        self.sim_timer.timeout.connect(self._update_animation)
        
        self.stack_order = 0 
        self.update_language()

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
        self._reset_and_play()
        super().showEvent(event)

    def _on_order_toggle(self):
        self.stack_order = (self.stack_order + 1) % 4
        self._update_order_btn_text()
        self._reset_and_play()

    def _update_order_btn_text(self):
        if not LanguageManager: return
        lm = LanguageManager.instance()
        
        if self.stack_order == 0: 
            key = "btn_x_first"
            style = "border: 2px solid #468CFF; color: #468CFF;"
            bg = "rgba(70, 140, 255, 0.2)"
        elif self.stack_order == 1: 
            key = "btn_y_first"
            style = "border: 2px solid #FFD280; color: #FFD280;"
            bg = "rgba(255, 210, 128, 0.2)"
        elif self.stack_order == 2: 
            key = "btn_z_first_x"
            style = "border: 2px solid #64FFDA; color: #64FFDA;"
            bg = "rgba(100, 255, 218, 0.2)"
        else: 
            key = "btn_z_first_y"
            style = "border: 2px solid #E040FB; color: #E040FB;" 
            bg = "rgba(224, 64, 251, 0.2)"
            
        self.btn_order.setText(lm.get_text(key))
        self.btn_order.setStyleSheet(f"""
            QPushButton {{ background: {bg}; {style} border-radius: 8px; font-weight: bold; font-size: 14px; }}
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

    def _update_plc_data(self):
        self.panel_x.set_current_display(self.plc_x)
        self.panel_y.set_current_display(self.plc_y)
        self.panel_z.set_current_display(self.plc_z)

    def _update_animation(self):
        xc, _, _ = self.panel_x.get_values()
        yc, _, _ = self.panel_y.get_values()
        zc, _, _ = self.panel_z.get_values()
        
        if self.stack_order == 0: 
            self.anim_x += 1
            if self.anim_x >= xc:
                self.anim_x = 0
                self.anim_y += 1
                if self.anim_y >= yc:
                    self.anim_y = 0
                    self.anim_z += 1
                    
        elif self.stack_order == 1: 
            self.anim_y += 1
            if self.anim_y >= yc:
                self.anim_y = 0
                self.anim_x += 1
                if self.anim_x >= xc:
                    self.anim_x = 0
                    self.anim_z += 1
                    
        elif self.stack_order == 2: 
            self.anim_z += 1
            if self.anim_z >= zc:
                self.anim_z = 0
                self.anim_x += 1
                if self.anim_x >= xc:
                    self.anim_x = 0
                    self.anim_y += 1
                    
        else: 
            self.anim_z += 1
            if self.anim_z >= zc:
                self.anim_z = 0
                self.anim_y += 1
                if self.anim_y >= yc:
                    self.anim_y = 0
                    self.anim_x += 1

        finished = False
        if self.stack_order in [0, 1]:
            if self.anim_z >= zc: finished = True
        elif self.stack_order == 2:
            if self.anim_y >= yc: finished = True
        else: 
            if self.anim_x >= xc: finished = True
            
        if finished:
            if self.stack_order in [0, 1]: self.anim_z = zc
            elif self.stack_order == 2: self.anim_y = yc
            else: self.anim_x = xc
            self._stop_simulation(finished=True)
            return
        
        self._update_visualizer(state=1)

    def _update_visualizer(self, state):
        xc, _, xd = self.panel_x.get_values()
        yc, _, yd = self.panel_y.get_values()
        zc, _, _ = self.panel_z.get_values()
        self.visualizer.update_status(xc, yc, zc, self.anim_x, self.anim_y, self.anim_z, xd, yd, state)