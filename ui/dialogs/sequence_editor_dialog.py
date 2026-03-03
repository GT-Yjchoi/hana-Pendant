import copy
import traceback
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QListWidget, QListWidgetItem, QStackedWidget,
    QTabWidget, QApplication, QMessageBox, QScroller, QScrollerProperties
)
from PySide6.QtGui import QScreen

try:
    from ui.widgets.custom_inputs import ClickableLineEdit, TouchComboBox
    from ui.dialogs.sequence_step_ui import StepUIGenerator, VALVE_LIST, INTERNAL_BIT_COUNT
except ImportError as e:
    print(f"!!! [CRITICAL ERROR] StepUIGenerator Import Failed: {e}")
    traceback.print_exc()
    from PySide6.QtWidgets import QLineEdit as ClickableLineEdit, QComboBox as TouchComboBox
    StepUIGenerator = None

try:
    from ui.dialogs.sequence_utils import (
        DarkConfirmDialog, RenameDialog, NumericKeypad, NewPointDialog, 
        DarkMessageDialog, SequenceListDialog, PopupListSelector, PointListDialog
    )
except ImportError:
    print("!!! [CRITICAL] sequence_utils Import Failed")
    DarkConfirmDialog = None
    RenameDialog = None
    NumericKeypad = None
    NewPointDialog = None
    DarkMessageDialog = None
    SequenceListDialog = None
    PopupListSelector = None
    PointListDialog = None

try:
    from utils.io_manager import IOManager
except ImportError:
    IOManager = None

class TouchScrollListWidget(QListWidget):
    """드래그로 스크롤되는 리스트 위젯 (터치스크린 대응)"""
    SCROLL_THRESHOLD = 8  # 이 픽셀 이상 수직 이동 시 스크롤 모드 진입

    def __init__(self, parent=None):
        super().__init__(parent)
        self._press_pos = None
        self._is_scrolling = False
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)

    def mousePressEvent(self, event):
        self._press_pos = event.pos()
        self._is_scrolling = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is not None:
            dy = event.pos().y() - self._press_pos.y()
            if not self._is_scrolling and abs(dy) > self.SCROLL_THRESHOLD:
                self._is_scrolling = True
                self.clearSelection()
            if self._is_scrolling:
                self.verticalScrollBar().setValue(
                    self.verticalScrollBar().value() - dy
                )
                self._press_pos = event.pos()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_scrolling = self._is_scrolling
        self._press_pos = None
        self._is_scrolling = False
        if was_scrolling:
            return  # 스크롤 중이었으면 아이템 선택 이벤트 무시
        super().mouseReleaseEvent(event)


class SequenceEditorDialog(QDialog):
    def __init__(self, sequence_data=None, position_points=None, plc_client=None, parent=None):
        super().__init__(parent)
        self.setObjectName("SequenceEditor") 
        self.setWindowTitle("시퀀스 편집")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(1024, 680)  # 전체화면 → 1024x680으로 변경 (높이 증가)
        
        # ★ 화면 중앙 정렬
        self._center_on_screen()
        
        self.plc_client = plc_client
        self._is_loading = False
        
        # ★ settings.json에서 연결된 축 정보 로드
        self.enabled_axes = self._load_enabled_axes()
        print(f"[시퀀스 편집기] 연결된 축: {self.enabled_axes}")
        
        self.points_library = {}
        if position_points:
            for k, v in position_points.items():
                if k: 
                    self.points_library[k] = {
                        "coords": list(v.get("coords", [0.0]*8)),
                        "speeds": list(v.get("speeds", [100.0]*8))
                    }
        
        self.sequences = {}
        if isinstance(sequence_data, list): self.sequences["Main"] = copy.deepcopy(sequence_data)
        elif isinstance(sequence_data, dict): self.sequences = copy.deepcopy(sequence_data)
        else: self.sequences["Main"] = []
        if "Main" not in self.sequences: self.sequences["Main"] = []
            
        self.current_seq_key = "Main"
        if "Main" in self.sequences: self.current_seq_key = "Main"
        else: self.current_seq_key = list(self.sequences.keys())[0]

        self.active_step_data = None 

        self._apply_dark_theme()
        self._init_ui()
        self._scan_all_points()
        
        self._update_sequence_info() 
        self._load_step_list_from_memory()

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QDialog#SequenceEditor { background-color: #0f161e; border: 2px solid #468CFF; }
            QWidget { color: #ffffff; font-family: 'Malgun Gothic', sans-serif; }
            QLabel { background: transparent; color: #eeeeee; }
            QListWidget { background-color: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 6px; color: #dddddd; font-size: 14px; outline: none; }
            QListWidget::item { height: 42px; padding-left: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
            QListWidget::item:selected { background-color: rgba(70, 140, 255, 0.3); border: 1px solid #468CFF; color: white; font-weight: bold; }
            QPushButton { background-color: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 4px; color: white; font-weight: bold; font-size: 13px; }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 0.2); }
            QLineEdit { background-color: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 4px; color: white; padding: 5px; font-size: 14px; }
        """)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        header = QHBoxLayout()
        lbl_title = QLabel("시퀀스 편집 (Sequence Editor)")
        lbl_title.setStyleSheet("font-size: 22px; font-weight: 900; color: #468CFF;")
        header.addWidget(lbl_title)
        header.addStretch(1)
        
        btn_cancel = QPushButton("취소 (닫기)")
        btn_cancel.setFixedSize(120, 45)
        btn_cancel.clicked.connect(self.reject)
        header.addWidget(btn_cancel)

        btn_apply = QPushButton("적용 (Apply)")
        btn_apply.setFixedSize(120, 45)
        btn_apply.setStyleSheet("border: 1px solid #00FF7F; color: #00FF7F;")
        btn_apply.clicked.connect(self._on_apply_clicked)
        header.addWidget(btn_apply)

        btn_save = QPushButton("저장 후 닫기")
        btn_save.setFixedSize(140, 45)
        btn_save.setStyleSheet("border: 1px solid #468CFF; color: white;")
        btn_save.clicked.connect(self._on_save_clicked)
        header.addWidget(btn_save)
        layout.addLayout(header)

        content = QHBoxLayout()
        left_widget = QWidget()
        left_box = QVBoxLayout(left_widget)
        
        nav_box = QHBoxLayout()
        nav_box.setSpacing(10)
        
        self.lbl_curr_seq = QLabel("Main")
        self.lbl_curr_seq.setFixedHeight(45)
        self.lbl_curr_seq.setStyleSheet("""
            QLabel { 
                background: rgba(70, 140, 255, 0.1); 
                border: 2px solid #468CFF; 
                border-radius: 6px; 
                color: #468CFF; 
                font-size: 18px; 
                font-weight: bold; 
                padding-left: 15px; 
            }
        """)
        nav_box.addWidget(self.lbl_curr_seq, 1)
        
        self.btn_seq_list = QPushButton(" 목록")
        self.btn_seq_list.setFixedSize(90, 45)
        self.btn_seq_list.setStyleSheet("border: 1px solid #FFFFFF; color: white;")
        self.btn_seq_list.clicked.connect(self._open_sequence_list)
        nav_box.addWidget(self.btn_seq_list)
        
        btn_add_seq = QPushButton("+")
        btn_add_seq.setFixedSize(45, 45)
        btn_add_seq.setStyleSheet("border: 1px solid #00E5FF; color: #00E5FF; font-size: 20px;")
        btn_add_seq.clicked.connect(self._on_add_sequence)
        nav_box.addWidget(btn_add_seq)
        
        self.btn_del_seq = QPushButton("삭제")
        self.btn_del_seq.setFixedSize(55, 45)
        self.btn_del_seq.setStyleSheet("border: 1px solid #FF4646; color: #FF4646; font-size: 14px; font-weight: bold;")
        self.btn_del_seq.clicked.connect(self._on_delete_sequence)
        nav_box.addWidget(self.btn_del_seq)
        
        left_box.addLayout(nav_box)
        
        # ★ 스텝 리스트 (터치 드래그 스크롤 지원)
        self.step_list = TouchScrollListWidget()
        self.step_list.itemClicked.connect(self._on_item_clicked)
        self.step_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.step_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 스타일 설정 (큰 스크롤바)
        self.step_list.setStyleSheet("""
            QListWidget {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                color: white;
                font-size: 14px;
                outline: none;
            }
            QListWidget::item {
                padding: 5px 10px;
                height: 30px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
            QListWidget::item:selected {
                background: rgba(70, 140, 255, 0.4);
                border-left: 3px solid #468CFF;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.1);
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0.2);
                width: 20px;
                margin: 0px;
                border-radius: 10px;
            }
            QScrollBar::handle:vertical {
                background: rgba(70, 140, 255, 0.6);
                min-height: 50px;
                border-radius: 10px;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(70, 140, 255, 0.8);
            }
            QScrollBar::handle:vertical:pressed {
                background: rgba(70, 140, 255, 1.0);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        left_box.addWidget(self.step_list)
        
        add_box = QHBoxLayout()
        for cmd, col in [("POS","#468CFF"), ("OUT","#FFA500"), ("IN","#FF69B4"), ("TMR","#FFFF00"), ("JMP","#00E5FF"), ("CALL","#FF00FF")]:
            btn = QPushButton(cmd)
            btn.setMinimumHeight(45)
            btn.setStyleSheet(f"border: 2px solid {col}; color: {col}; font-weight: bold;")
            btn.clicked.connect(lambda _, c=cmd: self._add_new_step(c))
            add_box.addWidget(btn)
        left_box.addLayout(add_box)
        
        edit_box = QHBoxLayout()
        for t, f in [("▲ 위로", self._move_up), ("▼ 아래로", self._move_down), ("[X] 스텝 삭제", self._delete_step)]:
            b = QPushButton(t)
            b.setMinimumHeight(45)
            b.clicked.connect(f)
            edit_box.addWidget(b)
        left_box.addLayout(edit_box)
        
        content.addWidget(left_widget, 4)
        
        right_widget = QWidget()
        right_widget.setStyleSheet("background: rgba(0,0,0,0.2); border-radius: 8px;")
        right_box = QVBoxLayout(right_widget)
        
        lbl_prop = QLabel("속성 설정")
        lbl_prop.setStyleSheet("font-size: 16px; font-weight: bold; color: #AAA;")
        right_box.addWidget(lbl_prop)
        
        self.stack = QStackedWidget()
        self.stack.addWidget(QLabel("스텝을 선택하세요"))
        
        if StepUIGenerator:
            self.stack.addWidget(StepUIGenerator.create_pos_editor(self))
            if hasattr(self, 'axis_checkboxes'):
                for i, chk in enumerate(self.axis_checkboxes):
                    if chk is None:  # ★ None 체크 추가
                        continue
                    try: chk.toggled.disconnect()
                    except: pass
                    chk.toggled.connect(lambda checked, idx=i: self._on_axis_checkbox_changed(idx, checked))

            self.stack.addWidget(StepUIGenerator.create_io_editor(self))
            self.stack.addWidget(StepUIGenerator.create_tmr_editor(self))
            self.stack.addWidget(StepUIGenerator.create_jmp_editor(self))
            self.stack.addWidget(StepUIGenerator.create_call_editor(self))
        else:
            self.stack.addWidget(QLabel("UI 로드 실패 (Import Error)"))

        right_box.addWidget(self.stack)
        content.addWidget(right_widget, 6)
        
        layout.addLayout(content)

    def _scan_all_points(self):
        for seq_name, steps in self.sequences.items():
            for step_data in steps:
                if step_data.get("type") == "POS":
                    p_name = step_data.get("point_name", step_data.get("name", "Point"))
                    if not p_name: p_name = "Point_1"; step_data["point_name"] = p_name
                    if p_name not in self.points_library:
                        self.points_library[p_name] = {
                            "coords": list(step_data.get("coords", [0.0]*8)),
                            "speeds": list(step_data.get("speeds", [100.0]*8))
                        }

    # =========================================================================
    # 로직 (데이터 로딩 & 저장)
    # =========================================================================
    def _on_item_clicked(self, item):
        row = self.step_list.row(item)
        if row < 0: return
        current_list = self.sequences.get(self.current_seq_key, [])
        if row >= len(current_list): return
        self.active_step_data = current_list[row]
        self._is_loading = True
        try: self._load_data_to_ui(self.active_step_data)
        finally: self._is_loading = False 

    def _load_data_to_ui(self, data):
        # ★ [수정] edit_step_name 관련 코드 제거 (위젯이 삭제되었으므로)
        
        type_code = data.get("type", "")
        # self.edit_step_name.setText(data.get("name", "")) # <-- 삭제됨
        
        idx_map = {"POS": 1, "OUT": 2, "IN": 2, "TMR": 3, "JMP": 4, "CALL": 5}
        self.stack.setCurrentIndex(idx_map.get(type_code, 0))

        if type_code == "POS":
            self._refresh_point_selector()
            
            # ★ active_axes로 통일 (PLC 전송과 동일한 키 사용)
            axes = data.get("active_axes", data.get("axes", [False]*8))
            if len(axes) < 8: axes += [False]*(8-len(axes))
            data["active_axes"] = axes  # active_axes로 저장
            
            p_name_key = data.get("point_name", "")
            speeds = self.points_library.get(p_name_key, {}).get("speeds", [100.0]*8)
            coords = self.points_library.get(p_name_key, {}).get("coords", [0.0]*8)
            
            for i in range(8):
                is_checked = axes[i]
                if hasattr(self, 'axis_checkboxes') and i < len(self.axis_checkboxes):
                    if self.axis_checkboxes[i] is not None:  # ★ None 체크
                        self.axis_checkboxes[i].setChecked(is_checked)
                    if self.pos_labels[i] is not None:  # ★ None 체크
                        self.pos_labels[i].setEnabled(is_checked)
                    if self.speed_spinboxes[i] is not None:  # ★ None 체크
                        self.speed_spinboxes[i].setEnabled(is_checked)
                        
                if hasattr(self, 'pos_labels') and i < len(self.pos_labels):
                    if self.pos_labels[i] is not None:  # ★ None 체크
                        self.pos_labels[i].setText(f"{coords[i]:.2f}")
                        
                if hasattr(self, 'speed_spinboxes') and i < len(self.speed_spinboxes):
                    if self.speed_spinboxes[i] is not None:  # ★ None 체크
                        self.speed_spinboxes[i].setText(f"{speeds[i]:.0f}")

        elif type_code in ["OUT", "IN"]:
            self._update_io_combo(type_code == "OUT")
            self.lbl_io_target.setText("제어할 밸브" if type_code=="OUT" else "감시할 센서")
            bit_index = data.get("port", 0)
            self.io_combo.setCurrentIndex(bit_index)
            
            # ★ 버튼 텍스트에 이름 표시
            if hasattr(self, 'io_combo_btn'):
                if type_code == "OUT":
                    # OUT: 밸브 이름
                    valve_name = self._get_valve_name_by_index(bit_index)
                    self.io_combo_btn.setText(valve_name)
                else:
                    # IN: 입력 이름
                    input_name = self._get_input_name_by_index(bit_index)
                    self.io_combo_btn.setText(input_name)
            
            if data.get("on", True): self.rb_on.setChecked(True)
            else: self.rb_off.setChecked(True)
            
            # ★ IN 스텝 전용: 타임아웃 설정
            if hasattr(self, 'in_timeout_frame'):
                if type_code == "IN":
                    self.in_timeout_frame.setVisible(True)

                    # 타임아웃 사용 여부 (기존 데이터 호환: 없으면 True)
                    enabled = data.get("timeout_enabled", True)
                    if hasattr(self, 'rb_timeout_enabled'):
                        self.rb_timeout_enabled.setChecked(enabled)
                        self.rb_timeout_disabled.setChecked(not enabled)

                    # 타임아웃 시간
                    timeout = data.get("timeout", 5.0)
                    if hasattr(self, 'timeout_btn'):
                        self.timeout_btn.setText(f"{timeout:.1f} sec")

                    # 타임아웃 동작
                    action = data.get("timeout_action", "ask")
                    if action == "continue":
                        self.rb_timeout_continue.setChecked(True)
                    elif action == "stop":
                        self.rb_timeout_stop.setChecked(True)
                    elif action == "jump":
                        self.rb_timeout_jump.setChecked(True)

                        # 점프 타겟 표시
                        if hasattr(self, 'timeout_jump_btn'):
                            jump_idx = data.get("timeout_jump", 0)
                            steps = self.sequences.get(self.current_seq_key, [])
                            if jump_idx < len(steps):
                                step_name = steps[jump_idx].get("name", "Unnamed")
                                self.timeout_jump_btn.setText(f"[{jump_idx:02d}] {step_name}")
                            else:
                                self.timeout_jump_btn.setText("선택하세요")
                    else:  # "ask"
                        self.rb_timeout_ask.setChecked(True)
                else:
                    self.in_timeout_frame.setVisible(False)

        elif type_code == "TMR":
            if hasattr(self, 'tmr_btn'): self.tmr_btn.setText(f"{data.get('time', 1.0):.1f} sec")
        
        elif type_code == "JMP":
            self.jmp_target_combo.blockSignals(True)
            self.jmp_target_combo.clear()
            self.jmp_target_combo.addItems([f"[{i+1:02d}] {s['name']}" for i, s in enumerate(self.sequences[self.current_seq_key])])
            target_idx = data.get("target_idx", 0)
            self.jmp_target_combo.setCurrentIndex(target_idx)
            self.jmp_target_combo.blockSignals(False)
            if hasattr(self, 'jmp_target_btn'):
                text = self.jmp_target_combo.currentText()
                self.jmp_target_btn.setText(text if text else "선택하세요")
            
            cond = data.get("condition", False)
            self.rb_jmp_cond.setChecked(cond)
            self.rb_jmp_always.setChecked(not cond)
            self.jmp_cond_frame.setVisible(cond)
            
            ct = data.get("cond_type", "PORT")
            cond_value = data.get("cond_value", 0)
            
            if ct == "MODE":
                self.rb_src_mode.setChecked(True)
                self.stack_cond_source.setCurrentIndex(1)
                self.jmp_mode_combo.setCurrentIndex(cond_value)
                
                # 버튼 텍스트 업데이트
                if hasattr(self, 'jmp_mode_btn'):
                    mode_name = self._get_mode_name_by_index(cond_value)
                    self.jmp_mode_btn.setText(mode_name)
            else:  # PORT (입력/내부비트 통합, BIT 제거)
                self.rb_src_port.setChecked(True)
                self.stack_cond_source.setCurrentIndex(0)
                self.jmp_port_combo.setCurrentIndex(cond_value)
                
                # 버튼 텍스트 업데이트
                if hasattr(self, 'jmp_port_btn'):
                    port_name = self._get_input_name_by_index(cond_value)
                    self.jmp_port_btn.setText(port_name)
            
            if data.get("cond_on", True): self.rb_jmp_on.setChecked(True)
            else: self.rb_jmp_off.setChecked(True)
            
        elif type_code == "CALL":
            self.call_combo.blockSignals(True)
            self.call_combo.clear()
            # ★ 자기 시퀀스 제외
            self.call_combo.addItems([k for k in self.sequences.keys() if k != self.current_seq_key])
            idx = self.call_combo.findText(data.get("target_seq", ""))
            self.call_combo.setCurrentIndex(idx if idx >= 0 else -1)
            self.call_combo.blockSignals(False)
            
            # ★ 버튼 텍스트 업데이트
            if hasattr(self, 'call_btn'):
                target_seq = data.get("target_seq", "")
                if target_seq:
                    self.call_btn.setText(target_seq)
                else:
                    self.call_btn.setText("선택하세요")
            
            # ★ 실행 모드 설정
            if hasattr(self, 'rb_call_wait') and hasattr(self, 'rb_call_parallel'):
                is_parallel = data.get("parallel", False)
                if is_parallel:
                    self.rb_call_parallel.setChecked(True)
                else:
                    self.rb_call_wait.setChecked(True)

    def _on_axis_checkbox_changed(self, idx, checked):
        if self._is_loading: return
        if self.active_step_data is None: return
        # ★ active_axes로 통일
        if "active_axes" not in self.active_step_data:
            self.active_step_data["active_axes"] = [False] * 8
        self.active_step_data["active_axes"][idx] = checked
        
        # ★ None 체크 추가
        if self.pos_labels[idx] is not None:
            self.pos_labels[idx].setEnabled(checked)
        if self.speed_spinboxes[idx] is not None:
            self.speed_spinboxes[idx].setEnabled(checked)

    def _on_step_name_changed(self, text):
        if self._is_loading: return
        if self.active_step_data is None: return
        self.active_step_data["name"] = text
        item = self.step_list.currentItem()
        if item:
            label = text
            if self.active_step_data.get("type") == "POS":
                p_name = self.active_step_data.get("point_name", "")
                if p_name:
                    label = f"{text}  ({p_name})"
            item.setText(f"[{self.step_list.row(item)+1:02d}] {label}")

    def _on_point_combo_changed(self, idx):
        pass 

    def _on_io_value_changed(self):
        if self._is_loading: return
        if self.active_step_data is None: return
        # ★ port는 선택 시(_open_io_selector)에 이미 저장됨
        # io_combo.currentIndex()는 신뢰할 수 없으므로 여기서 업데이트하지 않음
        # self.active_step_data["port"] = self.io_combo.currentIndex()  # 제거!
        self.active_step_data["on"] = self.rb_on.isChecked()
        
        # ★ IN 스텝: 타임아웃 설정 저장
        if self.active_step_data.get("type") == "IN":
            # 타임아웃 사용 여부
            if hasattr(self, 'rb_timeout_enabled'):
                self.active_step_data["timeout_enabled"] = self.rb_timeout_enabled.isChecked()
            # 타임아웃 동작
            if hasattr(self, 'rb_timeout_ask'):
                if self.rb_timeout_continue.isChecked():
                    self.active_step_data["timeout_action"] = "continue"
                elif self.rb_timeout_stop.isChecked():
                    self.active_step_data["timeout_action"] = "stop"
                elif self.rb_timeout_jump.isChecked():
                    self.active_step_data["timeout_action"] = "jump"
                else:
                    self.active_step_data["timeout_action"] = "ask"

    def _on_tmr_edit_clicked(self):
        if self.active_step_data is None: return
        if NumericKeypad:
            cur_val = self.active_step_data.get("time", 1.0)
            dlg = NumericKeypad("시간 설정 (초)", cur_val, 1, self)
            if dlg.exec() == QDialog.Accepted:
                val = dlg.get_value()
                self.active_step_data["time"] = val
                self.tmr_btn.setText(f"{val:.1f} sec")
    
    def _on_timeout_edit_clicked(self):
        """IN 스텝 타임아웃 편집"""
        if self.active_step_data is None: return
        if NumericKeypad:
            cur_val = self.active_step_data.get("timeout", 5.0)
            dlg = NumericKeypad("타임아웃 설정 (초)", cur_val, 1, self)
            if dlg.exec() == QDialog.Accepted:
                val = dlg.get_value()
                self.active_step_data["timeout"] = val
                self.timeout_btn.setText(f"{val:.1f} sec")

    def _on_jmp_value_changed(self):
        if self._is_loading: return
        if self.active_step_data is None: return
        d = self.active_step_data
        d["target_idx"] = self.jmp_target_combo.currentIndex()
        d["condition"] = self.rb_jmp_cond.isChecked()
        self.jmp_cond_frame.setVisible(d["condition"])
        
        # ★ PORT/MODE만 처리 (BIT 제거)
        if self.rb_src_mode.isChecked():
            d["cond_type"] = "MODE"
            # ★ 기존 값이 있으면 유지, 없으면 0
            if "cond_value" not in d or d["cond_value"] < 0:
                d["cond_value"] = 0
            self.stack_cond_source.setCurrentIndex(1)  # ★ 모드 위젯 표시
        else:  # PORT (입력/내부비트 통합)
            d["cond_type"] = "PORT"
            # ★ 기존 값이 있으면 유지, 없으면 0
            if "cond_value" not in d or d["cond_value"] < 0:
                d["cond_value"] = 0
            self.stack_cond_source.setCurrentIndex(0)  # ★ 포트 위젯 표시
        
        d["cond_on"] = self.rb_jmp_on.isChecked()

    def _on_call_value_changed(self):
        if self._is_loading: return
        if self.active_step_data is None: return
        self.active_step_data["target_seq"] = self.call_combo.currentText()
        
        # ★ 실행 모드 저장
        if hasattr(self, 'rb_call_parallel'):
            self.active_step_data["parallel"] = self.rb_call_parallel.isChecked()

    # =========================================================================
    # 팝업 연결 (Overlay)
    # =========================================================================

    def _on_speed_edit_clicked(self, idx):
        if self.active_step_data is None: return
        if NumericKeypad:
            p_name = self.active_step_data.get("point_name", "")
            cur = self.points_library.get(p_name, {}).get("speeds", [100.0]*8)[idx]
            dlg = NumericKeypad("속도 입력 (%)", cur, 0, self)
            if dlg.exec() == QDialog.Accepted:
                val = int(dlg.get_value())
                if p_name in self.points_library:
                    self.points_library[p_name]["speeds"][idx] = val
                if self.speed_spinboxes[idx] is not None:
                    self.speed_spinboxes[idx].setText(str(val))

    def _on_pos_edit_clicked(self, idx):
        if self.active_step_data is None: return
        p_name = self.point_combo.currentText()
        if p_name in self.points_library:
            coords = self.points_library[p_name]["coords"]
            if NumericKeypad:
                dlg = NumericKeypad(f"{idx+1}축 위치 입력", coords[idx], 2, self)
                if dlg.exec() == QDialog.Accepted:
                    coords[idx] = dlg.get_value()
                    if self.pos_labels[idx] is not None:  # ★ None 체크
                        self.pos_labels[idx].setText(f"{coords[idx]:.2f}")

    def _refresh_point_combo(self):
        self.point_combo.blockSignals(True)
        cur = self.point_combo.currentText()
        self.point_combo.clear()
        self.point_combo.addItems(sorted(list(self.points_library.keys())))
        idx = self.point_combo.findText(cur)
        if idx >= 0: self.point_combo.setCurrentIndex(idx)
        self.point_combo.blockSignals(False)

    def _update_io_combo(self, is_out):
        self.io_combo.blockSignals(True)
        self.io_combo.clear()
        mgr = IOManager.instance() if IOManager else None
        items = []
        if is_out:
            for i in range(32): items.append(f"[Y{i:02X}] {VALVE_LIST[i] if i<len(VALVE_LIST) else (mgr.get_output_name(i) if mgr else '예비')}")
        else:
            for i in range(32): items.append(f"[X{i:02X}] {mgr.get_input_name(i) if mgr else '입력'}")
        for i in range(INTERNAL_BIT_COUNT): items.append(f"[M{i:02X}] 내부 비트 {i}")
        self.io_combo.addItems(items)
        self.io_combo.blockSignals(False)

    def _init_tabs(self): pass
    def _on_seq_tab_changed(self, index): pass

    def _load_step_list_from_memory(self):
        self.step_list.clear()
        self.active_step_data = None
        self.stack.setCurrentIndex(0)
        current_list = self.sequences.get(self.current_seq_key, [])
        for i, step in enumerate(current_list):
            label = step.get('name')
            if step.get("type") == "POS":
                p_name = step.get("point_name", "")
                if p_name:
                    label = f"{label}  ({p_name})"
            self.step_list.addItem(f"[{i+1:02d}] {label}")
        if self.step_list.count() > 0:
            self.step_list.setCurrentRow(0)
            self._on_item_clicked(self.step_list.item(0))

    def _next_step_name(self, type_code):
        """해당 타입에서 비어 있는 가장 낮은 번호로 이름 생성"""
        base_name = {"POS":"위치 이동","OUT":"출력 제어","IN":"입력 대기","TMR":"타이머","JMP":"점프","CALL":"호출"}.get(type_code, "Step")
        used = set()
        for seq in self.sequences.values():
            for step in seq:
                if step.get("type") == type_code:
                    name = step.get("name", "")
                    prefix = base_name + "_"
                    if name.startswith(prefix):
                        suffix = name[len(prefix):]
                        if suffix.isdigit():
                            used.add(int(suffix))
        n = 1
        while n in used:
            n += 1
        return f"{base_name}_{n}"

    def _add_new_step(self, type_code):
        final_name = self._next_step_name(type_code)
        data = {"type": type_code, "name": final_name}
        if type_code == "POS":
            p_names = sorted(list(self.points_library.keys()))
            data["point_name"] = p_names[0] if p_names else final_name
            if not p_names: self.points_library[final_name] = {"coords": [0.0]*8, "speeds": [100.0]*8}
            # ★ active_axes로 통일 (기본값: 모든 축 체크 해제)
            data["active_axes"] = [False] * 8
        elif type_code in ["OUT", "IN"]: data["port"]=0; data["on"]=True
        elif type_code == "TMR": data["time"] = 1.0
        elif type_code == "JMP": data.update({"target_idx":0, "condition":False})
        elif type_code == "CALL": data["target_seq"] = ""
        
        # ★ 선택된 스텝 바로 아래에 삽입
        current_row = self.step_list.currentRow()
        if current_row >= 0:
            # 선택된 스텝이 있으면 그 바로 아래에 삽입
            insert_pos = current_row + 1
            self.sequences[self.current_seq_key].insert(insert_pos, data)
            new_row = insert_pos
        else:
            # 선택된 스텝이 없으면 맨 아래 추가
            self.sequences[self.current_seq_key].append(data)
            new_row = self.step_list.count()
        
        self._load_step_list_from_memory()
        self.step_list.setCurrentRow(new_row)
        self._on_item_clicked(self.step_list.item(new_row))

    def _delete_step(self):
        row = self.step_list.currentRow()
        if row >= 0 and DarkConfirmDialog:
            if DarkConfirmDialog("삭제", "정말 삭제하시겠습니까?", self).exec() == QDialog.Accepted:
                del self.sequences[self.current_seq_key][row]
                self._load_step_list_from_memory()
                new_count = self.step_list.count()
                if new_count > 0:
                    new_row = min(row, new_count - 1)
                    self.step_list.setCurrentRow(new_row)
                    self._on_item_clicked(self.step_list.item(new_row))

    def _move_up(self):
        r = self.step_list.currentRow()
        if r > 0:
            lst = self.sequences[self.current_seq_key]
            lst[r], lst[r-1] = lst[r-1], lst[r]
            self._load_step_list_from_memory()
            self.step_list.setCurrentRow(r-1)
            self._on_item_clicked(self.step_list.item(r-1))

    def _move_down(self):
        r = self.step_list.currentRow()
        lst = self.sequences[self.current_seq_key]
        if r < len(lst)-1:
            lst[r], lst[r+1] = lst[r+1], lst[r]
            self._load_step_list_from_memory()
            self.step_list.setCurrentRow(r+1)
            self._on_item_clicked(self.step_list.item(r+1))

    def _on_apply_clicked(self):
        if not self.plc_client: return
        if self._send_all_sequences_to_plc():
            if DarkMessageDialog:
                DarkMessageDialog("전송 완료", "모든 시퀀스가 PLC로 전송되었습니다.", parent=self).exec()
            else:
                QMessageBox.information(self, "전송 완료", "PLC 전송 완료")
        else:
            if DarkMessageDialog:
                DarkMessageDialog("전송 실패", "통신 상태를 확인하세요.", is_error=True, parent=self).exec()
            else:
                QMessageBox.warning(self, "전송 실패", "통신 상태를 확인하세요")

    def _on_save_clicked(self):
        if self.plc_client:
            if not self._send_all_sequences_to_plc():
                if DarkConfirmDialog:
                    if DarkConfirmDialog("전송 실패", "전송 실패. 그래도 저장하고 닫을까요?", self).exec() != QDialog.Accepted:
                        return
                else:
                    if QMessageBox.question(self, "전송 실패", "저장하고 닫을까요?") != QMessageBox.Yes:
                        return
        self.accept()

    def _send_all_sequences_to_plc(self):
        if not self.plc_client or not self.plc_client.is_connected: return False
        
        # ★ 디버그: 전송할 시퀀스 데이터 확인
        print(f"\n[시퀀스 전송] 전송할 시퀀스 데이터:")
        for seq_name, steps in self.sequences.items():
            print(f"  시퀀스: {seq_name}")
            for i, step in enumerate(steps):
                if step.get("type") in ["OUT", "IN"]:
                    print(f"    Step {i}: {step.get('type')} - port={step.get('port', 'NONE')}, on={step.get('on', 'NONE')}, name={step.get('name', 'NONE')}")
        
        sorted_p_names = sorted(list(self.points_library.keys()))
        point_map = {name: i for i, name in enumerate(sorted_p_names)}
        seq_map = {"Main": 0}
        sub = sorted([k for k in self.sequences.keys() if k != "Main"])
        for i, k in enumerate(sub): seq_map[k] = i + 1
        success = True
        for seq_name, slot_id in seq_map.items():
            raw_steps = self.sequences.get(seq_name, [])
            plc_steps = []
            for step in raw_steps:
                s_data = copy.deepcopy(step)
                if s_data.get("type") == "POS":
                    s_data["point_index"] = point_map.get(s_data.get("point_name"), 0)
                elif s_data.get("type") == "CALL":
                    s_data["sequence_id"] = seq_map.get(s_data.get("target_seq"), 0)
                elif s_data.get("type") == "JMP":
                    s_data["target_step"] = s_data.get("target_idx", 0)
                plc_steps.append(s_data)
            if not self.plc_client.send_sequence_to_slot(slot_id, plc_steps): success = False
        if not self.plc_client.send_all_points(self.points_library, sorted_p_names): success = False
        return success

    def get_sequence_data(self):
        for seq in self.sequences.values():
            for s in seq:
                if s.get("type") == "POS" and s.get("point_name") in self.points_library:
                    s["coords"] = list(self.points_library[s["point_name"]]["coords"])
        return self.sequences
    
    def get_position_points(self):
        return self.points_library
    
    def _open_step_name_keyboard(self):
        if self.active_step_data is None: return
        if RenameDialog:
            all_names = [s['name'] for s in self.sequences[self.current_seq_key]]
            dlg = RenameDialog(self.active_step_data["name"], all_names, self)
            if dlg.exec() == QDialog.Accepted:
                self._on_step_name_changed(dlg.get_new_name())
    
    def _on_item_double_clicked(self, item):
        self._open_step_name_keyboard()
    
    def _on_new_point_clicked(self):
        if NewPointDialog:
            dlg = NewPointDialog(list(self.points_library.keys()), self)
            if dlg.exec() == QDialog.Accepted:
                name = dlg.get_name()
                if name:
                    self.points_library[name] = {"coords": [0.0]*8, "speeds": [100.0]*8}
                    self._refresh_point_selector()
                    idx = self.point_combo.findText(name)
                    if idx >= 0: self.point_combo.setCurrentIndex(idx)

    def _on_rename_point_clicked(self):
        if not hasattr(self, 'btn_point_select'): return
        old = self.btn_point_select.text()
        
        if RenameDialog:
            dlg = RenameDialog(old, list(self.points_library.keys()), self)
            if dlg.exec() == QDialog.Accepted:
                new = dlg.get_new_name()
                if new:
                    self.points_library[new] = self.points_library.pop(old)
                    for seq in self.sequences.values():
                        for s in seq:
                            if s.get("point_name") == old: s["point_name"] = new
                    
                    if self.active_step_data.get("point_name") == old:
                        self.active_step_data["point_name"] = new
                    self._refresh_point_selector()
                    self._load_step_list_from_memory()

    def _on_delete_point_clicked(self):
        if not hasattr(self, 'btn_point_select'): return
        cur = self.btn_point_select.text()
        
        if cur and DarkConfirmDialog:
            if DarkConfirmDialog("삭제", "포인트를 삭제하시겠습니까?", self).exec() == QDialog.Accepted:
                del self.points_library[cur]
                if self.points_library:
                    next_point = sorted(list(self.points_library.keys()))[0]
                else:
                    next_point = "Point_1"
                    self.points_library[next_point] = {"coords": [0.0]*8, "speeds": [100.0]*8}
                
                self.active_step_data["point_name"] = next_point
                self._refresh_point_selector()
                self._load_step_list_from_memory()
    
    # ★ 네비게이션 관리
    def _update_sequence_info(self):
        self.lbl_curr_seq.setText(f" {self.current_seq_key}")
        seq_count = len(self.sequences)
        if seq_count > 1:
            self.btn_seq_list.setEnabled(True)
            self.btn_seq_list.setStyleSheet("border: 1px solid #FFFFFF; color: white;")
            self.btn_seq_list.setText(f" 목록 ({seq_count})")
        else:
            self.btn_seq_list.setEnabled(False)
            self.btn_seq_list.setStyleSheet("border: 1px solid #555; color: #777;")
            self.btn_seq_list.setText(" 목록")
        self.btn_del_seq.setEnabled(self.current_seq_key != "Main")

    def _on_add_sequence(self):
        if RenameDialog:
            dlg = RenameDialog("", list(self.sequences.keys()), self, confirm_text="추가")
            dlg.setWindowTitle("새 시퀀스 생성")
            if dlg.exec() == QDialog.Accepted:
                name = dlg.get_new_name()
                if name:
                    self.sequences[name] = []
                    self.current_seq_key = name
                    self._update_sequence_info()
                    self._load_step_list_from_memory()

    def _open_sequence_list(self):
        if SequenceListDialog:
            dlg = SequenceListDialog(self.sequences.keys(), self.current_seq_key, self)
            if dlg.exec() == QDialog.Accepted:
                selected = dlg.get_selected()
                if selected:
                    self.current_seq_key = selected
                    self._update_sequence_info()
                    self._load_step_list_from_memory()

    def _on_delete_sequence(self):
        if self.current_seq_key == "Main": return
        if DarkConfirmDialog:
            if DarkConfirmDialog("삭제", f"'{self.current_seq_key}' 시퀀스를 삭제하시겠습니까?", self).exec() == QDialog.Accepted:
                del self.sequences[self.current_seq_key]
                self.current_seq_key = "Main"
                self._update_sequence_info()
                self._load_step_list_from_memory()
    
    # ★ [수정] 포인트 선택기 팝업 호출
    def _open_point_list(self):
        if self._is_loading: return
        if self.active_step_data is None: return
        
        cur_point = self.active_step_data.get("point_name", "")
        if PointListDialog:
            dlg = PointListDialog(list(self.points_library.keys()), cur_point, self)
            if dlg.exec() == QDialog.Accepted:
                selected = dlg.get_selected()
                if selected:
                    self.active_step_data["point_name"] = selected
                    self._refresh_point_selector()

                    # 리스트 아이템 포인트명 갱신
                    item = self.step_list.currentItem()
                    if item:
                        name = self.active_step_data.get("name", "")
                        row = self.step_list.row(item)
                        item.setText(f"[{row+1:02d}] {name}  ({selected})")

                    coords = self.points_library.get(selected, {}).get("coords", [0.0]*8)
                    for i in range(8):
                        if self.pos_labels[i] is not None:
                            self.pos_labels[i].setText(f"{coords[i]:.2f}")

    # ★ [수정] 버튼 텍스트 갱신 함수
    def _refresh_point_selector(self):
        if self.active_step_data is None: return
        if hasattr(self, 'btn_point_select'):
            p_name = self.active_step_data.get("point_name", "선택하세요")
            self.btn_point_select.setText(p_name)
    
    # =========================================================
    # ★ [신규] 카드형 선택 팝업 함수들
    # =========================================================
    
    def _open_io_selector(self):
        """IO 선택 팝업 (OUT: 밸브 설정, IN: 입력 이름)"""
        if not hasattr(self, 'io_combo'): return
        
        # 현재 스텝 타입 확인
        step_type = self.active_step_data.get("type", "OUT") if self.active_step_data else "OUT"
        
        if step_type == "OUT":
            # ========== OUT 스텝: 밸브 설정 + 내부 제어 비트 ==========
            import os
            import json
            
            items = []
            valve_indices = []  # 실제 비트 인덱스 저장
            
            try:
                path = "settings.json"
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        valve_config = settings.get("valve_config", [])
                        
                        if valve_config:
                            # order 순서대로 정렬
                            valve_config.sort(key=lambda x: x.get("order", 0))
                            
                            # 사용 가능한 밸브만 필터링
                            for cfg in valve_config:
                                if cfg.get("enabled", True):
                                    items.append(cfg.get("name", f"밸브 {cfg.get('index', 0)+1}"))
                                    valve_indices.append(cfg.get("index", 0))
            except Exception as e:
                print(f"[시퀀스 편집기] 밸브 설정 로드 실패: {e}")
            
            # 설정 로드 실패 시 기본값
            if not items:
                try:
                    from ui.dialogs.sequence_step_ui import VALVE_LIST
                    items = VALVE_LIST
                    valve_indices = list(range(len(items)))
                except:
                    items = [f"밸브 {i+1}" for i in range(16)]
                    valve_indices = list(range(16))
            
            # ★ 내부 제어 비트 32개 추가 (비트 100~131)
            for i in range(32):
                items.append(f" M{i:02d} (내부비트)")
                valve_indices.append(100 + i)  # 100~131
            
            from ui.dialogs.sequence_utils import CardListDialog
            
            # 현재 선택된 비트 인덱스로 이름 찾기
            current_bit_index = self.io_combo.currentIndex() if self.io_combo.currentIndex() >= 0 else -1
            current = None
            if current_bit_index >= 0 and current_bit_index < len(items):
                current = items[current_bit_index]
            
            dlg = CardListDialog(items, current, "[Y] 출력 포트를 선택하세요", columns=4, parent=self)
            if dlg.exec() == QDialog.Accepted:
                selected = dlg.get_selected()
                if selected and selected in items:
                    # 선택한 밸브의 실제 비트 인덱스 찾기
                    list_idx = items.index(selected)
                    bit_idx = valve_indices[list_idx]
                    
                    # ★ active_step_data에 직접 저장
                    if self.active_step_data:
                        self.active_step_data["port"] = bit_idx
                    
                    # io_combo에도 저장 (호환성)
                    self.io_combo.setCurrentIndex(bit_idx)
                    
                    # 버튼 텍스트도 업데이트
                    if hasattr(self, 'io_combo_btn'):
                        self.io_combo_btn.setText(selected)
                    
                    print(f"[시퀀스 편집기] OUT 포트 선택: {selected} (bit_idx={bit_idx})")
        
        else:  # step_type == "IN"
            # ========== IN 스텝: 입력 + 내부 제어 비트 ==========
            try:
                from utils.io_manager import IOManager
                mgr = IOManager.instance() if IOManager else None
                
                items = []
                port_indices = []  # 포트 인덱스 저장
                
                # X0~X3F (64개 입력)
                for i in range(64):
                    if mgr:
                        name = mgr.get_input_name(i)
                        if name:
                            items.append(f"X{i:02X}: {name}")
                        else:
                            items.append(f"X{i:02X}")
                    else:
                        items.append(f"X{i:02X}")
                    port_indices.append(i)
                
                # ★ 내부 제어 비트 32개 추가 (100~131)
                for i in range(32):
                    items.append(f" M{i:02d} (내부비트)")
                    port_indices.append(100 + i)  # 100~131
                
            except Exception as e:
                print(f"[시퀀스 편집기] 입력 이름 로드 실패: {e}")
                items = [f"X{i:02X}" for i in range(64)]
                port_indices = list(range(64))
                # 내부 비트 추가
                for i in range(32):
                    items.append(f" M{i:02d} (내부비트)")
                    port_indices.append(100 + i)
            
            from ui.dialogs.sequence_utils import CardListDialog
            
            # 현재 선택된 포트 번호
            current_port = self.io_combo.currentIndex() if self.io_combo.currentIndex() >= 0 else 0
            current = None
            if current_port < len(items):
                # port_indices에서 current_port와 일치하는 항목 찾기
                try:
                    idx = port_indices.index(current_port)
                    current = items[idx]
                except ValueError:
                    current = None
            
            dlg = CardListDialog(items, current, " 입력/내부비트를 선택하세요", columns=4, parent=self)
            if dlg.exec() == QDialog.Accepted:
                selected = dlg.get_selected()
                if selected and selected in items:
                    list_idx = items.index(selected)
                    port_idx = port_indices[list_idx]  # ★ port_indices에서 실제 인덱스 가져오기
                    
                    # ★ active_step_data에 직접 저장
                    if self.active_step_data:
                        self.active_step_data["port"] = port_idx
                    
                    # io_combo에도 저장 (호환성)
                    self.io_combo.setCurrentIndex(port_idx)
                    
                    # 버튼 텍스트도 업데이트
                    if hasattr(self, 'io_combo_btn'):
                        self.io_combo_btn.setText(selected)
                    
                    print(f"[시퀀스 편집기] IN 포트 선택: {selected} (port_idx={port_idx})")
    
    def _open_jmp_port_selector(self):
        """JMP 조건 - 입력/내부비트 선택 팝업"""
        if not hasattr(self, 'jmp_port_combo'): return
        
        # 입력 (X0~X3F) + 내부비트 (M00~M31)
        try:
            from utils.io_manager import IOManager
            mgr = IOManager.instance() if IOManager else None
            
            items = []
            port_indices = []
            
            # X0~X3F (64개 입력)
            for i in range(64):
                if mgr:
                    name = mgr.get_input_name(i)
                    if name:
                        items.append(f"X{i:02X}: {name}")
                    else:
                        items.append(f"X{i:02X}")
                else:
                    items.append(f"X{i:02X}")
                port_indices.append(i)
            
            # M00~M31 (32개 내부비트)
            for i in range(32):
                items.append(f" M{i:02d} (내부비트)")
                port_indices.append(100 + i)
            
        except Exception as e:
            print(f"[시퀀스 편집기] JMP 입력 로드 실패: {e}")
            items = [f"X{i:02X}" for i in range(64)]
            port_indices = list(range(64))
            for i in range(32):
                items.append(f" M{i:02d} (내부비트)")
                port_indices.append(100 + i)
        
        from ui.dialogs.sequence_utils import CardListDialog
        
        # ★ 현재 선택 (active_step_data에서 가져오기)
        current_port = self.active_step_data.get("cond_value", 0) if self.active_step_data else 0
        current = None
        try:
            idx = port_indices.index(current_port)
            current = items[idx]
        except (ValueError, IndexError):
            current = None
        
        print(f"[DEBUG] JMP 포트 선택 팝업 - current_port={current_port}, current={current}")
        
        dlg = CardListDialog(items, current, " 입력/내부비트를 선택하세요", columns=4, parent=self)
        if dlg.exec() == QDialog.Accepted:
            selected = dlg.get_selected()
            if selected and selected in items:
                list_idx = items.index(selected)
                port_idx = port_indices[list_idx]
                
                # active_step_data에 직접 저장
                if self.active_step_data:
                    self.active_step_data["cond_value"] = port_idx
                
                self.jmp_port_combo.setCurrentIndex(port_idx)
                
                if hasattr(self, 'jmp_port_btn'):
                    self.jmp_port_btn.setText(selected)
                
                print(f"[시퀀스 편집기] JMP 포트 선택: {selected} (port_idx={port_idx})")
    
    def _open_jmp_mode_selector(self):
        """JMP 조건 - 모드 선택 팝업"""
        if not hasattr(self, 'jmp_mode_combo'): return
        
        # 모드 0~43 (page_mode.py 참조)
        items = []
        
        # 기본 모드 이름 (page_mode.py에서 복사)
        default_names = [
            "제품측 취출", "런너측 취출", "주행 대기", "하강 대기",
            "주행도중개방", "복귀도중개방", "안전도어 회피", "안전도어 회피2",
            "낙하측 반전", "주행도중 반전", "취출대기 반전", "고정측 취출",
            "제품 형내개방", "런너 형내개방", "에젝터 연동", "언더컷 취출모드",
            "척1 사용", "척1 감지", "척2 사용", "척2 감지",
            "척3 사용", "척3 감지", "척4 사용", "척4 감지",
            "흡착1 사용", "흡착1 감지", "흡착2 사용", "흡착2 감지",
            "흡착3 사용", "흡착3 감지", "흡착4 사용", "흡착4 감지",
            "2포인트 개방", "공정감시 모드"
        ]
        
        # ModeManager에서 이름 가져오기
        try:
            from utils.mode_manager import ModeManager
            mgr = ModeManager.instance() if ModeManager else None
            
            for i in range(44):
                if mgr:
                    name = mgr.get_name(i)
                elif i < len(default_names):
                    name = default_names[i]
                else:
                    name = f"User Mode {i - 34 + 1}"
                
                items.append(f"[{i:02d}] {name}")
        except Exception as e:
            print(f"[시퀀스 편집기] 모드 로드 실패: {e}")
            for i in range(44):
                if i < len(default_names):
                    items.append(f"[{i:02d}] {default_names[i]}")
                else:
                    items.append(f"[{i:02d}] User Mode {i - 34 + 1}")
        
        from ui.dialogs.sequence_utils import CardListDialog
        
        # ★ 현재 선택 (active_step_data에서 가져오기)
        current_mode = self.active_step_data.get("cond_value", 0) if self.active_step_data else 0
        current = items[current_mode] if current_mode < len(items) else None
        
        print(f"[DEBUG] JMP 모드 선택 팝업 - current_mode={current_mode}, current={current}")
        
        dlg = CardListDialog(items, current, " 모드를 선택하세요", columns=4, parent=self)
        if dlg.exec() == QDialog.Accepted:
            selected = dlg.get_selected()
            if selected and selected in items:
                mode_idx = items.index(selected)
                
                # active_step_data에 직접 저장
                if self.active_step_data:
                    self.active_step_data["cond_value"] = mode_idx
                
                self.jmp_mode_combo.setCurrentIndex(mode_idx)
                
                if hasattr(self, 'jmp_mode_btn'):
                    self.jmp_mode_btn.setText(selected)
                
                print(f"[시퀀스 편집기] JMP 모드 선택: {selected} (mode_idx={mode_idx})")
    
    def _open_jmp_target_selector(self):
        """JMP 타겟 스텝 선택 팝업"""
        if not hasattr(self, 'jmp_target_combo'): return
        
        # 현재 시퀀스의 스텝 리스트
        steps = self.sequences.get(self.current_seq_key, [])
        items = [f"Step {i}: {s.get('name', 'Unnamed')}" for i, s in enumerate(steps)]
        
        if not items:
            items = ["(스텝 없음)"]
        
        from ui.dialogs.sequence_utils import CardListDialog
        current = self.jmp_target_combo.currentText() if self.jmp_target_combo.currentIndex() >= 0 else None
        
        dlg = CardListDialog(items, current, " 점프할 스텝을 선택하세요", columns=3, parent=self)
        if dlg.exec() == QDialog.Accepted:
            selected = dlg.get_selected()
            if selected and selected != "(스텝 없음)":
                idx = items.index(selected)
                self.jmp_target_combo.setCurrentIndex(idx)
                # 버튼 텍스트도 업데이트
                if hasattr(self, 'jmp_target_btn'):
                    self.jmp_target_btn.setText(selected)
    
    def _open_timeout_jump_selector(self):
        """IN 타임아웃 점프 타겟 선택 팝업"""
        if not hasattr(self, 'timeout_jump_combo'): return
        
        # 현재 시퀀스의 스텝 리스트
        steps = self.sequences.get(self.current_seq_key, [])
        items = [f"[{i:02d}] {s.get('name', 'Unnamed')}" for i, s in enumerate(steps)]
        
        if not items:
            items = ["(스텝 없음)"]
        
        from ui.dialogs.sequence_utils import CardListDialog
        
        # 현재 선택
        current_idx = self.active_step_data.get("timeout_jump", 0) if self.active_step_data else 0
        current = items[current_idx] if current_idx < len(items) else None
        
        dlg = CardListDialog(items, current, " 타임아웃 시 점프할 스텝", columns=3, parent=self)
        if dlg.exec() == QDialog.Accepted:
            selected = dlg.get_selected()
            if selected and selected != "(스텝 없음)":
                idx = items.index(selected)
                
                # active_step_data에 직접 저장
                if self.active_step_data:
                    self.active_step_data["timeout_jump"] = idx
                
                self.timeout_jump_combo.setCurrentIndex(idx)
                
                # 버튼 텍스트도 업데이트
                if hasattr(self, 'timeout_jump_btn'):
                    self.timeout_jump_btn.setText(selected)
                
                print(f"[시퀀스 편집기] 타임아웃 점프 타겟: {selected} (idx={idx})")
    
    def _open_call_selector(self):
        """CALL 시퀀스 선택 팝업"""
        if not hasattr(self, 'call_combo'): return
        
        # ★ 시퀀스 리스트 (자기 시퀀스 제외)
        items = [k for k in self.sequences.keys() if k != self.current_seq_key]
        
        from ui.dialogs.sequence_utils import CardListDialog
        
        # ★ 현재 선택 (active_step_data에서 가져오기)
        current_seq = self.active_step_data.get("target_seq", "") if self.active_step_data else ""
        current = current_seq if current_seq in items else None
        
        print(f"[DEBUG] CALL 선택 팝업 - current_seq={current_seq}, current={current}, items={items}")
        
        dlg = CardListDialog(items, current, "[C] 호출할 시퀀스를 선택하세요", columns=4, parent=self)
        if dlg.exec() == QDialog.Accepted:
            selected = dlg.get_selected()
            if selected:
                # ★ active_step_data에 직접 저장
                if self.active_step_data:
                    self.active_step_data["target_seq"] = selected
                
                idx = items.index(selected)
                self.call_combo.setCurrentIndex(idx)
                
                # 버튼 텍스트도 업데이트
                if hasattr(self, 'call_btn'):
                    self.call_btn.setText(selected)
                
                print(f"[시퀀스 편집기] CALL 시퀀스 선택: {selected}")
    
    # =========================================================
    # ★ [신규] 밸브 설정 헬퍼 함수
    # =========================================================
    
    def _get_valve_name_by_index(self, bit_index):
        """비트 인덱스로 밸브 이름 가져오기"""
        # ★ 내부 제어 비트 (100~131)
        if 100 <= bit_index <= 131:
            return f" M{bit_index-100:02d} (내부비트)"
        
        try:
            import os
            import json
            
            path = "settings.json"
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    valve_config = settings.get("valve_config", [])
                    
                    # 비트 인덱스로 밸브 찾기
                    for cfg in valve_config:
                        if cfg.get("index", -1) == bit_index and cfg.get("enabled", True):
                            return cfg.get("name", f"밸브 {bit_index+1}")
        except:
            pass
        
        # 기본값
        return f"밸브 {bit_index+1}"
    
    def _get_input_name_by_index(self, port_index):
        """포트 번호로 입력 이름 가져오기 (IOManager 사용)"""
        # ★ 내부 제어 비트 (100~131)
        if 100 <= port_index <= 131:
            return f" M{port_index-100:02d} (내부비트)"
        
        try:
            from utils.io_manager import IOManager
            mgr = IOManager.instance() if IOManager else None
            
            if mgr:
                name = mgr.get_input_name(port_index)
                if name:
                    return f"X{port_index:02X}: {name}"  # ★ 16진수 표기
        except:
            pass
        
        # 기본값
        return f"X{port_index:02X}"  # ★ 16진수 표기
    
    def _get_mode_name_by_index(self, mode_index):
        """모드 번호로 모드 이름 가져오기 (ModeManager 사용)"""
        default_names = [
            "제품측 취출", "런너측 취출", "주행 대기", "하강 대기",
            "주행도중개방", "복귀도중개방", "안전도어 회피", "안전도어 회피2",
            "낙하측 반전", "주행도중 반전", "취출대기 반전", "고정측 취출",
            "제품 형내개방", "런너 형내개방", "에젝터 연동", "언더컷 취출모드",
            "척1 사용", "척1 감지", "척2 사용", "척2 감지",
            "척3 사용", "척3 감지", "척4 사용", "척4 감지",
            "흡착1 사용", "흡착1 감지", "흡착2 사용", "흡착2 감지",
            "흡착3 사용", "흡착3 감지", "흡착4 사용", "흡착4 감지",
            "2포인트 개방", "공정감시 모드"
        ]
        
        try:
            from utils.mode_manager import ModeManager
            mgr = ModeManager.instance() if ModeManager else None
            
            if mgr:
                name = mgr.get_name(mode_index)
                return f"[{mode_index:02d}] {name}"
            elif mode_index < len(default_names):
                return f"[{mode_index:02d}] {default_names[mode_index]}"
            else:
                return f"[{mode_index:02d}] User Mode {mode_index - 34 + 1}"
        except:
            if mode_index < len(default_names):
                return f"[{mode_index:02d}] {default_names[mode_index]}"
            else:
                return f"[{mode_index:02d}] User Mode {mode_index - 34 + 1}"
    
    # =========================================================
    # ★ [신규] 화면 중앙 정렬
    # =========================================================
    
    def _center_on_screen(self):
        """다이얼로그를 화면 중앙에 배치"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)
    
    # =========================================================
    # ★ [신규] 축 설정 로드
    # =========================================================
    
    def _load_enabled_axes(self):
        """
        settings.json에서 연결된 축 정보 로드
        반환: [True, True, True, False, ...] (8개)
        """
        try:
            import os
            path = "settings.json"
            if os.path.exists(path):
                import json
                with open(path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    axis_uses = settings.get("axis_uses", None)
                    
                    if axis_uses and len(axis_uses) == 8:
                        return axis_uses
        except Exception as e:
            print(f"[시퀀스 편집기] 축 설정 로드 실패: {e}")
        
        # 기본값: 전축 활성화
        return [True] * 8