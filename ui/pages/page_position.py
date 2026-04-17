import random
from PySide6.QtCore import Qt, Signal, QEventLoop, QTimer
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QDialog, QFrame,
    QSizePolicy, QScrollArea, QScroller, QGridLayout,
    QScrollerProperties, QStyledItemDelegate, QInputDialog, QMessageBox
)

from widgets.glass_card import GlassCard
from ui.widgets.valve_tile import ValvePanel
from ui.dialogs.sequence_editor_dialog import SequenceEditorDialog
from ui.widgets.custom_inputs import TouchComboBox
from utils.languages import LanguageManager

# =========================================================================
# [기존 유지] 오버레이 방식 숫자 키패드
# =========================================================================
class NumberInputOverlay(QWidget):
    def __init__(self, current_val_str, precision=0, parent=None):
        super().__init__(parent)
        if parent:
            main_window = parent.window()
            self.setParent(main_window)
            self.resize(main_window.size())
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        
        self.precision = precision
        self.result_val = None
        self._event_loop = None
        
        layout = QVBoxLayout(self); layout.setAlignment(Qt.AlignCenter)
        container = QFrame(); container.setFixedSize(320, 450)
        container.setStyleSheet("QFrame { background-color: #1A1F2B; border: 2px solid #468CFF; border-radius: 12px; } QLabel { color: #FFD700; font-size: 28px; font-weight: bold; background: rgba(0,0,0,0.3); border: 1px solid #444; border-radius: 6px; padding: 5px; } QPushButton { background-color: #34495E; color: white; font-size: 22px; font-weight: bold; border: none; border-radius: 6px; } QPushButton:pressed { background-color: #468CFF; } QPushButton#btnCancel { background-color: #582F2F; border: 1px solid #C0392B; } QPushButton#btnOk { background-color: #2980B9; border: 1px solid #3498DB; }")
        
        vbox = QVBoxLayout(container); vbox.setSpacing(10); vbox.setContentsMargins(20, 20, 20, 20)
        self.display = QLabel(current_val_str); self.display.setAlignment(Qt.AlignRight | Qt.AlignVCenter); self.display.setFixedHeight(60); vbox.addWidget(self.display)
        
        grid = QGridLayout(); grid.setSpacing(8)
        keys = [('7',0,0),('8',0,1),('9',0,2),('4',1,0),('5',1,1),('6',1,2),('1',2,0),('2',2,1),('3',2,2),('0',3,0),('.',3,1),('←',3,2)]
        for text, r, c in keys:
            btn = QPushButton(text); btn.setFixedSize(80, 60); btn.setAttribute(Qt.WA_AcceptTouchEvents, True)
            if text == '.':
                if self.precision == 0: btn.setEnabled(False)
                btn.clicked.connect(self._on_dot)
            elif text == '←': btn.clicked.connect(self._on_backspace)
            else: btn.clicked.connect(lambda _, t=text: self._on_digit(t))
            grid.addWidget(btn, r, c)
        vbox.addLayout(grid)
        
        hbox = QHBoxLayout()
        btn_cancel = QPushButton("취소"); btn_cancel.setObjectName("btnCancel"); btn_cancel.setFixedHeight(50); btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("확인"); btn_ok.setObjectName("btnOk"); btn_ok.setFixedHeight(50); btn_ok.clicked.connect(self.accept)
        hbox.addWidget(btn_cancel); hbox.addWidget(btn_ok); vbox.addLayout(hbox)
        layout.addWidget(container); self.first_input = True

    def _on_digit(self, digit):
        if self.first_input: self.display.setText(digit); self.first_input = False
        else: self.display.setText(self.display.text() + digit) if self.display.text() != "0" else self.display.setText(digit)
    def _on_dot(self):
        if self.first_input: self.display.setText("0."); self.first_input = False
        elif "." not in self.display.text(): self.display.setText(self.display.text() + ".")
    def _on_backspace(self):
        cur = self.display.text()
        self.display.setText(cur[:-1] if len(cur) > 1 else "0"); self.first_input = (len(cur) <= 1)
    def accept(self): self.result_val = self.display.text(); self._quit()
    def reject(self): self.result_val = None; self._quit()
    def _quit(self):
        if self._event_loop: self._event_loop.quit()
        self.close(); self.deleteLater()
    def exec(self): self.show(); self.raise_(); self._event_loop = QEventLoop(); self._event_loop.exec(); return self.result_val

# -------------------------------------------------------------------------
# [Helper Classes]
# -------------------------------------------------------------------------
class ClickableLabel(QLabel):
    clicked = Signal(int, str) 
    def __init__(self, row_idx, col_type, text="", parent=None):
        super().__init__(text, parent); self.row_idx = row_idx; self.col_type = col_type; self.setCursor(Qt.PointingHandCursor)
    def mousePressEvent(self, event): self.clicked.emit(self.row_idx, self.col_type); super().mousePressEvent(event)

class PositionOrderDialog(QDialog):
    def __init__(self, current_names, parent=None):
        super().__init__(parent); self.name_list = list(current_names) 
        self.setWindowTitle("위치 목록 순서 변경"); self.setModal(True); self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint); self.resize(500, 600)
        self.setStyleSheet("QDialog { background: rgba(20, 30, 40, 250); border: 2px solid rgba(70, 140, 255, 120); border-radius: 12px; } QLabel { color: white; font-size: 18px; font-weight: bold; } QListWidget { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; font-size: 18px; color: #EEE; } QListWidget::item { height: 50px; padding-left: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); } QListWidget::item:selected { background: rgba(70, 140, 255, 0.4); border: 1px solid #468CFF; color: white; } QPushButton { background: rgba(255,255,255,0.1); border: 1px solid gray; border-radius: 6px; color: white; height: 50px; font-size: 16px; font-weight: bold; } QPushButton:pressed { background: rgba(255,255,255,0.3); }")
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QLabel("위치 명칭 보기 순서 변경")); layout.addWidget(QLabel("※ 실제 동작 순서는 변경되지 않습니다. (화면 표시용)"))
        self.list_widget = QListWidget(); layout.addWidget(self.list_widget); self._load_list()
        btn_layout = QHBoxLayout(); btn_up = QPushButton("▲ 위로"); btn_down = QPushButton("▼ 아래로"); btn_ok = QPushButton("적용 (Apply)"); btn_ok.setStyleSheet("background: rgba(70,140,255,0.4); border: 1px solid #468CFF;"); btn_cancel = QPushButton("취소")
        btn_up.clicked.connect(self._move_up); btn_down.clicked.connect(self._move_down); btn_ok.clicked.connect(self.accept); btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_up); btn_layout.addWidget(btn_down); btn_layout.addWidget(btn_cancel); btn_layout.addWidget(btn_ok); layout.addLayout(btn_layout)
    def showEvent(self, e): super().showEvent(e); self.activateWindow(); self.raise_(); self.setFocus()
    def _load_list(self):
        self.list_widget.clear()
        for name in self.name_list: self.list_widget.addItem(QListWidgetItem(f"[P] {name}"))
    def _move_up(self):
        r = self.list_widget.currentRow(); 
        if r <= 0: return
        self.name_list[r], self.name_list[r-1] = self.name_list[r-1], self.name_list[r]; self._load_list(); self.list_widget.setCurrentRow(r - 1)
    def _move_down(self):
        r = self.list_widget.currentRow(); 
        if r < 0 or r >= self.list_widget.count() - 1: return
        self.name_list[r], self.name_list[r+1] = self.name_list[r+1], self.name_list[r]; self._load_list(); self.list_widget.setCurrentRow(r + 1)
    def get_ordered_names(self): return self.name_list

# -------------------------------------------------------------------------
# [PointNameCardOverlay] 위치 포인트 선택 네임카드 오버레이
# -------------------------------------------------------------------------
class PointNameCardOverlay(QWidget):
    point_selected = Signal(str)

    def __init__(self, ordered_points, current_point, parent=None):
        super().__init__(parent)
        if parent:
            mw = parent.window()
            self.setParent(mw)
            self.resize(mw.size())
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        popup = QFrame()
        popup.setFixedSize(520, 440)
        popup.setStyleSheet("QFrame { background-color: #1A1F2B; border: 2px solid #468CFF; border-radius: 14px; } QLabel { background: transparent; border: none; }")

        vbox = QVBoxLayout(popup)
        vbox.setContentsMargins(20, 16, 20, 20)
        vbox.setSpacing(12)

        # 제목 + 닫기
        title_row = QHBoxLayout()
        title_lbl = QLabel("[P] 위치 포인트 선택")
        title_lbl.setStyleSheet("color: #64FFDA; font-size: 20px; font-weight: bold;")
        btn_close = QPushButton("X")
        btn_close.setFixedSize(32, 32)
        btn_close.setStyleSheet("QPushButton { background: transparent; color: #FF4646; font-size: 16px; font-weight: bold; border: none; } QPushButton:hover { color: white; }")
        btn_close.clicked.connect(self.close)
        title_row.addWidget(title_lbl, 1)
        title_row.addWidget(btn_close)
        vbox.addLayout(title_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.2); border: none; max-height: 1px;")
        vbox.addWidget(sep)

        # 카드 그리드 (스크롤 가능)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setSpacing(10)
        grid.setContentsMargins(4, 4, 4, 4)

        COLS = 2
        for i, name in enumerate(ordered_points):
            is_cur = (name == current_point)
            card = QPushButton(name)
            card.setFixedHeight(56)
            card.setCursor(Qt.PointingHandCursor)
            if is_cur:
                card.setStyleSheet("QPushButton { background-color: rgba(70,140,255,0.5); border: 2px solid #468CFF; border-radius: 8px; color: white; font-size: 18px; font-weight: bold; } QPushButton:pressed { background-color: rgba(70,140,255,0.8); }")
            else:
                card.setStyleSheet("QPushButton { background-color: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: #EEE; font-size: 18px; } QPushButton:hover { background-color: rgba(255,255,255,0.15); border: 1px solid #468CFF; } QPushButton:pressed { background-color: rgba(70,140,255,0.3); }")
            card.clicked.connect(lambda _, n=name: self._on_card(n))
            grid.addWidget(card, i // COLS, i % COLS)

        scroll.setWidget(grid_widget)
        vbox.addWidget(scroll, 1)
        layout.addWidget(popup)

    def _on_card(self, name):
        self.point_selected.emit(name)
        self.close()

    def mousePressEvent(self, event):
        # 팝업 밖 클릭 시 닫기
        self.close()
        event.accept()

class ClickableListWidget(QListWidget):
    empty_clicked = Signal() 
    def __init__(self, parent=None):
        super().__init__(parent); self.setVerticalScrollMode(QListWidget.ScrollPerPixel); self.setFocusPolicy(Qt.NoFocus); self.setCursor(Qt.PointingHandCursor)
    def mousePressEvent(self, event):
        if self.count() == 0: self.empty_clicked.emit()
        super().mousePressEvent(event)

class CenterDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index): super().initStyleOption(option, index); option.displayAlignment = Qt.AlignCenter

class StepHighlightDelegate(QStyledItemDelegate):
    """현재 실행 중인 시퀀스 스텝을 하이라이트하는 delegate"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighted_row = -1

    def paint(self, painter, option, index):
        if index.row() == self.highlighted_row:
            painter.save()
            painter.fillRect(option.rect, QColor(0, 229, 255, 70))
            painter.restore()
        super().paint(painter, option, index)

# -------------------------------------------------------------------------
# [PagePosition Class]
# -------------------------------------------------------------------------
class PagePosition(GlassCard):
    sig_sequence_changed = Signal()

    def __init__(self, sequence_data=None, position_points=None, view_order_data=None, mode_data=None, timer_library=None, plc_client=None):
        super().__init__("")
        if hasattr(self, 'title_label'): self.title_label.hide()
        if self.layout(): self.layout().setContentsMargins(10, 5, 10, 10)

        self.plc_client = plc_client
        if self.plc_client:
            self.plc_client.sig_monitor_data.connect(self._update_realtime_values)

        self.raw_sequence_ref = sequence_data if sequence_data is not None else []
        self.position_points = position_points if position_points is not None else {}
        self.view_order_data = view_order_data if view_order_data is not None else []
        self.mode_data = mode_data if mode_data is not None else []
        self.timer_library = timer_library if timer_library is not None else {}
        
        self.sequences = {}
        if isinstance(self.raw_sequence_ref, list): self.sequences["Main"] = self.raw_sequence_ref
        elif isinstance(self.raw_sequence_ref, dict): self.sequences = self.raw_sequence_ref
        else: self.sequences["Main"] = []
            
        if "Main" not in self.sequences: self.sequences["Main"] = []
        self.current_seq_key = "Main" 

        self._init_points_from_sequence()
        self.lbl_saved_vals = []
        self.lbl_speed_vals = []
        self.lbl_curr_vals = []

        # [NEW] 축 행(Row) 숨김 제어를 위한 리스트
        self.axis_rows = []

        self._init_ui()
        self._refresh_ui()

    def _init_points_from_sequence(self):
        for seq_list in self.sequences.values():
            for step in seq_list:
                if step.get("type") == "POS":
                    p_name = step.get("point_name", step.get("name", "Point"))
                    if not p_name: p_name = "Point_1"
                    if p_name not in self.position_points:
                        coords = step.get("coords", [0.0]*8)
                        speeds = step.get("speeds", [100.0]*8)
                        self.position_points[p_name] = {"coords": list(coords), "speeds": list(speeds)}

    def _init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # [LEFT Panel]
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8) 
        
        nav_layout = QHBoxLayout(); nav_layout.setSpacing(10)
        _nav_btn_style = ("QPushButton { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.3); "
                          "border-radius: 6px; color: white; font-size: 18px; font-weight: bold; } "
                          "QPushButton:hover { background: rgba(255,255,255,0.18); border: 1px solid #468CFF; } "
                          "QPushButton:pressed { background: rgba(70,140,255,0.3); } "
                          "QPushButton:disabled { background: rgba(255,255,255,0.03); "
                          "border: 1px solid rgba(255,255,255,0.08); color: rgba(255,255,255,0.2); }")
        self.btn_prev = QPushButton("◀"); self.btn_prev.setFixedSize(45, 42); self.btn_prev.setStyleSheet(_nav_btn_style); self.btn_prev.clicked.connect(self._on_prev_point)
        # 내부 상태 관리용 (숨김)
        self.point_combo = TouchComboBox(); self.point_combo.setVisible(False); self.point_combo.setItemDelegate(CenterDelegate()); self.point_combo.currentIndexChanged.connect(self._on_combo_changed)
        # 표시용 버튼 - 클릭하면 네임카드 오버레이 팝업
        self.point_name_btn = QPushButton("위치 없음"); self.point_name_btn.setFixedHeight(42); self.point_name_btn.setCursor(Qt.PointingHandCursor)
        self.point_name_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.1); border: 1px solid rgba(100,200,255,0.4); border-radius: 6px; color: white; font-size: 18px; font-weight: bold; } QPushButton:hover { background: rgba(70,140,255,0.2); border: 1px solid #468CFF; } QPushButton:pressed { background: rgba(70,140,255,0.3); } QPushButton:disabled { color: rgba(255,255,255,0.3); border: 1px solid rgba(255,255,255,0.1); }")
        self.point_name_btn.clicked.connect(self._show_name_card_overlay)
        self.btn_next = QPushButton("▶"); self.btn_next.setFixedSize(45, 42); self.btn_next.setStyleSheet(_nav_btn_style); self.btn_next.clicked.connect(self._on_next_point)
        self.btn_reorder = QPushButton("☰"); self.btn_reorder.setFixedSize(45, 42); self.btn_reorder.setStyleSheet("background: rgba(255,255,255,0.1); border: 1px solid gray; border-radius: 6px; font-size: 22px; color: white;"); self.btn_reorder.clicked.connect(self._on_reorder_clicked)

        nav_layout.addWidget(self.btn_prev); nav_layout.addWidget(self.point_name_btn, 1); nav_layout.addWidget(self.btn_reorder); nav_layout.addWidget(self.btn_next)
        left_layout.addLayout(nav_layout)
        
        data_frame = QFrame(); data_frame.setStyleSheet("background: rgba(0,0,0,0.15); border-radius: 10px;")
        grid = QGridLayout(data_frame); grid.setContentsMargins(10, 10, 10, 10); grid.setHorizontalSpacing(10); grid.setVerticalSpacing(10) 
        
        # [수정] 헤더 폰트 확대 (16px)
        headers = ["축", "현재위치", "기억위치", "속도%"]
        for c, h in enumerate(headers):
            lbl = QLabel(h); lbl.setAlignment(Qt.AlignCenter); lbl.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 16px; font-weight: bold;")
            grid.addWidget(lbl, 0, c)
        grid.setColumnStretch(0, 0); grid.setColumnStretch(1, 5); grid.setColumnStretch(2, 5); grid.setColumnStretch(3, 2)

        axis_names = ["X", "Y", "Z", "Y2", "Z2", "θ", "R1", "R2"]
        
        def create_val_label(color, default_text, is_current=False, row_idx=0, val_type=None):
            box = QFrame(); bg_color = "rgba(255,255,255,0.12)" if is_current else "rgba(255,255,255,0.05)"; border_color = "rgba(100,255,218,0.5)" if is_current else "rgba(255,255,255,0.15)"
            # [수정] 박스 높이 확대 (45px)
            box.setStyleSheet(f"background: {bg_color}; border: 1px solid {border_color}; border-radius: 6px;"); box.setMinimumHeight(45); box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            h = QHBoxLayout(box); h.setContentsMargins(4, 2, 4, 2)
            if val_type: lbl = ClickableLabel(row_idx, val_type, default_text); lbl.clicked.connect(self._on_value_clicked) 
            else: lbl = QLabel(default_text)
            # [수정] 값 폰트 확대 (22px)
            lbl.setAlignment(Qt.AlignCenter); lbl.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold; border: none; background: transparent;")
            h.addWidget(lbl); return box, lbl

        for r, axis in enumerate(axis_names, start=1):
            row_idx = r - 1
            # [수정] 축 이름 폰트 확대 (20px) 및 높이 조정
            lbl_axis = QLabel(axis); lbl_axis.setAlignment(Qt.AlignCenter); 
            lbl_axis.setStyleSheet("background: rgba(255,255,255,0.1); border-radius: 4px; color: #DDD; font-weight: bold; font-size: 20px;")
            lbl_axis.setMinimumHeight(45)
            
            grid.addWidget(lbl_axis, r, 0)
            
            box_cur, lbl_cur = create_val_label("#FFFFFF", "0.00", is_current=True); grid.addWidget(box_cur, r, 1); self.lbl_curr_vals.append(lbl_cur)
            box_sav, lbl_sav = create_val_label("#64FFDA", "0.00", row_idx=row_idx, val_type="coords"); grid.addWidget(box_sav, r, 2); self.lbl_saved_vals.append(lbl_sav)
            box_spd, lbl_spd = create_val_label("#FFD280", "100", row_idx=row_idx, val_type="speed"); grid.addWidget(box_spd, r, 3); self.lbl_speed_vals.append(lbl_spd); grid.setRowStretch(r, 1)
            
            # [NEW] 숨김 제어를 위해 행별 위젯 저장
            self.axis_rows.append([lbl_axis, box_cur, box_sav, box_spd])

        data_scroll = QScrollArea()
        data_scroll.setWidget(data_frame)
        data_scroll.setWidgetResizable(True)
        data_scroll.setFrameShape(QFrame.NoFrame)
        data_scroll.setStyleSheet("background: transparent;")
        data_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        data_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        QScroller.grabGesture(data_scroll.viewport(), QScroller.TouchGesture)
        left_layout.addWidget(data_scroll, 1)
        self.btn_teach = QPushButton("현재 위치 기억 (TEACH)"); self.btn_teach.setProperty("class", "AutoControlBtn"); self.btn_teach.setProperty("variant", "start"); self.btn_teach.setMinimumHeight(55); self.btn_teach.setCursor(Qt.PointingHandCursor); self.btn_teach.clicked.connect(self._on_teach_clicked)
        left_layout.addWidget(self.btn_teach)

        left_widget = QWidget(); left_widget.setLayout(left_layout)
        
        # [MIDDLE Panel]
        mid_layout = QVBoxLayout(); mid_layout.setSpacing(10)
        seq_select_layout = QHBoxLayout(); mid_title = QLabel("동작 순서"); mid_title.setProperty("class", "PosPanelTitle"); seq_select_layout.addWidget(mid_title)
        self.seq_selector = TouchComboBox(); self.seq_selector.setMinimumWidth(120); self.seq_selector.setFixedHeight(40); self.seq_selector.setStyleSheet("QComboBox { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.3); border-radius: 4px; color: white; font-weight: bold; padding-left: 10px; font-size: 16px; }"); self.seq_selector.currentIndexChanged.connect(self._on_seq_selector_changed)
        seq_select_layout.addWidget(self.seq_selector); mid_layout.addLayout(seq_select_layout)
        
        self.preview_list = ClickableListWidget(); self.preview_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.preview_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview_list.setStyleSheet("QListWidget { background: rgba(0,0,0,0.2); border: 2px solid rgba(255,255,255,0.1); border-radius: 8px; outline: none; } QListWidget::item { height: 40px; padding-left: 8px; color: #BBB; font-size: 14px; border-bottom: 1px solid rgba(255,255,255,0.05); }")
        self._step_delegate = StepHighlightDelegate(self.preview_list)
        self.preview_list.setItemDelegate(self._step_delegate)
        QScroller.grabGesture(self.preview_list.viewport(), QScroller.TouchGesture); QScroller.grabGesture(self.preview_list.viewport(), QScroller.LeftMouseButtonGesture)
        self.preview_list.itemClicked.connect(self._open_sequence_editor); self.preview_list.empty_clicked.connect(self._open_sequence_editor)
        mid_layout.addWidget(self.preview_list, 1); mid_widget = QWidget(); mid_widget.setLayout(mid_layout)
        
        # [RIGHT Panel]
        self.valve_panel = ValvePanel(self.plc_client)
        
        # [LAYOUT]
        main_layout.addWidget(left_widget, 4)
        main_layout.addWidget(mid_widget, 4)
        main_layout.addWidget(self.valve_panel, 2)
        self.body.addLayout(main_layout)

    def showEvent(self, event):
        self._refresh_ui()
        # 페이지 진입 시 항상 첫 번째 포인트로 이동
        if self.point_combo.isEnabled() and self.point_combo.count() > 0:
            self.point_combo.setCurrentIndex(0)
        super().showEvent(event)
        # 화면 보일 때마다 사용 축 / 런너암 버튼 확인
        QTimer.singleShot(0, self._check_axis_visibility)

    def _check_axis_visibility(self):
        """PLC에서 축 사용 설정을 읽어 미사용 축 숨김"""
        if not self.plc_client or not self.plc_client.is_connected: return
        try:
            data = self.plc_client.read_words(0x09, self.plc_client.AXIS_PARAM_ADDR, 1)
            if data:
                use_mask = data[0]
                for i, widgets in enumerate(self.axis_rows):
                    is_used = bool((use_mask >> i) & 1)
                    for w in widgets:
                        w.setVisible(is_used)
        except Exception as e:
            print(f"[Position] 축 표시 갱신 실패: {e}")

    def _refresh_ui(self):
        self.seq_selector.blockSignals(True)
        self.seq_selector.clear()
        
        keys = sorted([k for k in self.sequences.keys() if k != "Main"])
        all_keys = ["Main"] + keys
        self.seq_selector.addItems(all_keys)
        
        idx = self.seq_selector.findText(self.current_seq_key)
        if idx >= 0: self.seq_selector.setCurrentIndex(idx)
        else: self.seq_selector.setCurrentIndex(0)
        self.seq_selector.blockSignals(False)

        self._sync_points_combobox()
        self._update_preview_list()
        self._on_combo_changed(self.point_combo.currentIndex())

    def _on_seq_selector_changed(self, idx):
        key = self.seq_selector.currentText()
        if key in self.sequences:
            self.current_seq_key = key
            self._update_preview_list()

    def _open_sequence_editor(self):
        dlg = SequenceEditorDialog(
            sequence_data=self.sequences,
            position_points=self.position_points,
            timer_library=self.timer_library,
            plc_client=self.plc_client,
            parent=self
        )
        if dlg.exec() == QDialog.Accepted:
            new_seqs = dlg.get_sequence_data()
            new_points = dlg.get_position_points()
            
            self.sequences.clear()
            self.sequences.update(new_seqs)
            
            if isinstance(self.raw_sequence_ref, list):
                self.raw_sequence_ref.clear()
                if "Main" in self.sequences:
                    self.raw_sequence_ref.extend(self.sequences["Main"])
            
            self.position_points.clear()
            self.position_points.update(new_points)
            
            self._refresh_ui()
            self.sig_sequence_changed.emit()

    def _update_realtime_values(self, data):
        if not self.isVisible(): return
        if isinstance(data, dict):
            axis_data = data.get('axis_pos', [])
        else:
            axis_data = data

        for i, val in enumerate(axis_data):
            if i < len(self.lbl_curr_vals):
                self.lbl_curr_vals[i].setText(f"{val:.3f}")

        # 현재 실행 중인 스텝 하이라이트 (자동운전 중일 때만)
        op_status = data.get('op_status', 0) if isinstance(data, dict) else 0
        current_step = data.get('current_step', -1) if isinstance(data, dict) else -1

        # op_status: 1=자동, 2=확인운전 → 시퀀스 실행 중
        if op_status in (1, 2):
            self._highlight_step(current_step)
        else:
            self._highlight_step(-1)

    def _highlight_step(self, step_idx):
        """preview_list에서 현재 실행 중인 스텝을 하이라이트.
        step_idx는 PLC 기준(COMMENT 제외) 인덱스이므로 리스트 행으로 변환한다."""
        list_row = -1
        if step_idx >= 0:
            n = 0
            for i, s in enumerate(self.sequences.get(self.current_seq_key, [])):
                if s.get("type") == "COMMENT":
                    continue
                if n == step_idx:
                    list_row = i
                    break
                n += 1

        if getattr(self, '_last_highlighted_step', None) == list_row:
            return
        self._last_highlighted_step = list_row

        self._step_delegate.highlighted_row = list_row
        self.preview_list.viewport().update()

        # 자동 스크롤: 현재 스텝이 보이도록
        if 0 <= list_row < self.preview_list.count():
            self.preview_list.scrollToItem(
                self.preview_list.item(list_row),
                QListWidget.PositionAtCenter
            )

    def _show_name_card_overlay(self):
        if not self.point_combo.isEnabled() or self.point_combo.count() == 0:
            return
        ordered = [self.point_combo.itemText(i) for i in range(self.point_combo.count())]
        current = self.point_combo.currentText()
        overlay = PointNameCardOverlay(ordered, current, parent=self)
        overlay.point_selected.connect(self._on_point_selected_from_card)
        overlay.show()
        overlay.raise_()

    def _on_point_selected_from_card(self, name):
        idx = self.point_combo.findText(name)
        if idx >= 0:
            self.point_combo.setCurrentIndex(idx)

    def _on_reorder_clicked(self):
        dlg = PositionOrderDialog(self.view_order_data, self)
        if dlg.exec() == QDialog.Accepted:
            new_order = dlg.get_ordered_names()
            self.view_order_data.clear()
            self.view_order_data.extend(new_order)
            self._sync_points_combobox()
            self._on_combo_changed(0)
            self.sig_sequence_changed.emit()

    def _get_mode_name(self, idx):
        default_names = [
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
        try:
            from utils.mode_manager import ModeManager
            mgr = ModeManager.instance()
            if mgr:
                return mgr.get_name(idx)
        except Exception:
            pass
        return default_names[idx] if idx < len(default_names) else f"User Mode {idx - 33}"

    def _is_point_visible(self, name):
        """포인트의 visible_mode 조건에 따라 현재 표시 여부 반환"""
        vm = self.position_points.get(name, {}).get("visible_mode", -1)
        # 구버전 int 형식 하위 호환
        if isinstance(vm, int):
            if vm < 0:
                return True
            return bool(self.mode_data[vm]) if self.mode_data and vm < len(self.mode_data) else False
        # 신규 list 형식: 빈 리스트 = 항상 표시, 아니면 OR 조건
        if not vm:
            return True
        return any(bool(self.mode_data[i]) for i in vm if self.mode_data and i < len(self.mode_data))

    def _sync_points_combobox(self):
        current_text = self.point_combo.currentText()
        self.point_combo.blockSignals(True)
        self.point_combo.clear()
        all_points = sorted(list(self.position_points.keys()))
        # view_order 동기화 (실제 표시 목록 업데이트)
        valid_custom = [n for n in self.view_order_data if n in all_points]
        new_names = [n for n in all_points if n not in valid_custom]
        self.view_order_data.clear(); self.view_order_data.extend(valid_custom + new_names)
        # 모드 조건 필터링
        visible_points = [n for n in self.view_order_data if self._is_point_visible(n)]
        if not visible_points:
            self.point_combo.addItem("위치 없음"); self.point_combo.setEnabled(False)
            self.point_name_btn.setText("위치 없음"); self.point_name_btn.setEnabled(False)
        else:
            self.point_name_btn.setEnabled(True)
            self.point_combo.setEnabled(True); self.point_combo.addItems(visible_points)
            idx = self.point_combo.findText(current_text)
            self.point_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.point_combo.blockSignals(False)

    def _update_preview_list(self):
        self._last_highlighted_step = None  # 리스트 갱신 시 하이라이트 초기화
        self.preview_list.clear()
        current_steps = self.sequences.get(self.current_seq_key, [])
        step_num = 0
        for step in current_steps:
            stype = step.get("type", "")
            if stype == "COMMENT":
                item = QListWidgetItem(f"// {step.get('text', '')}")
                item.setForeground(QBrush(QColor("#FFD700")))
                self.preview_list.addItem(item)
                continue
            step_num += 1
            name = step.get("name", "Unknown")
            if stype == "POS":
                p_name = step.get("point_name", "")
                if p_name and p_name != name: name = f"{name} ({p_name})"
            elif stype == "CALL":
                tgt = step.get("target_seq", "")
                name = f"{name} -> {tgt}"
            self.preview_list.addItem(f"[{step_num:02d}] {name}")

    def _on_prev_point(self):
        idx = self.point_combo.currentIndex()
        if idx > 0: self.point_combo.setCurrentIndex(idx - 1)

    def _on_next_point(self):
        idx = self.point_combo.currentIndex()
        if idx < self.point_combo.count() - 1: self.point_combo.setCurrentIndex(idx + 1)

    def _on_combo_changed(self, idx):
        count = self.point_combo.count()
        self.btn_prev.setEnabled(idx > 0); self.btn_next.setEnabled(idx < count - 1)
        selected_point = self.point_combo.currentText()
        if not self.point_combo.isEnabled() or not selected_point or selected_point == "위치 없음":
            self.point_name_btn.setText("위치 없음")
            self._clear_display(); return
        self.point_name_btn.setText(selected_point)
        
        if selected_point in self.position_points:
            data = self.position_points[selected_point]
            coords = data.get("coords", [0.0]*8)
            speeds = data.get("speeds", [100.0]*8)
            for i in range(8):
                val = coords[i] if i < len(coords) else 0.0
                spd = speeds[i] if i < len(speeds) else 100.0
                self.lbl_saved_vals[i].setText(f"{val:.3f}")
                self.lbl_speed_vals[i].setText(f"{spd:.0f}")
        else: self._clear_display()

    def _on_value_clicked(self, row_idx, col_type):
        if not self.point_combo.isEnabled(): return
        selected_point = self.point_combo.currentText()
        if selected_point not in self.position_points: return

        current_val_str = ""
        if col_type == "coords": current_val_str = self.lbl_saved_vals[row_idx].text()
        elif col_type == "speed": current_val_str = self.lbl_speed_vals[row_idx].text()
            
        prec = 3 if col_type == "coords" else 0
        dlg = NumberInputOverlay(current_val_str, prec, parent=self.window())
        new_val_str = dlg.exec()
        if new_val_str is None: return

        try: new_val = float(new_val_str)
        except ValueError: return 

        if col_type == "coords":
            self.position_points[selected_point]["coords"][row_idx] = new_val
            for seq in self.sequences.values():
                for step in seq:
                    if step.get("type") == "POS":
                        p_name = step.get("point_name", step.get("name"))
                        if p_name == selected_point:
                            if "coords" in step: step["coords"][row_idx] = new_val
                                
        elif col_type == "speed":
            if "speeds" not in self.position_points[selected_point]:
                self.position_points[selected_point]["speeds"] = [100]*8
            self.position_points[selected_point]["speeds"][row_idx] = int(new_val)

        if self.plc_client and self.plc_client.is_connected:
            try:
                sorted_names = sorted(list(self.position_points.keys()))
                point_idx = sorted_names.index(selected_point)
                base_addr = self.plc_client.POINT_BASE_ADDR + (point_idx * self.plc_client.POINT_SIZE)
                if col_type == "coords":
                    target_addr = base_addr + 2 + (row_idx * 2)
                    send_val = int(new_val * 1000)
                    self.plc_client.write_dint(0x09, target_addr, send_val)
                elif col_type == "speed":
                    target_addr = base_addr + 18 + row_idx
                    send_val = int(new_val)
                    self.plc_client.write_words(0x09, target_addr, [send_val])
            except Exception as e:
                print(f"[Position] PLC 시퀀스 값 전송 실패: {e}")

        self._on_combo_changed(self.point_combo.currentIndex())
        self.sig_sequence_changed.emit()

    def _clear_display(self):
        for i in range(8):
            self.lbl_saved_vals[i].setText("---"); self.lbl_speed_vals[i].setText("-")

    def _on_teach_clicked(self):
        if not self.point_combo.isEnabled(): return
        target_point_name = self.point_combo.currentText()
        if target_point_name not in self.position_points: return

        new_coords = []
        for lbl in self.lbl_curr_vals:
            try: val = float(lbl.text())
            except ValueError: val = 0.0
            new_coords.append(val)
        
        self.position_points[target_point_name]["coords"] = list(new_coords)
        
        for seq in self.sequences.values():
            for step in seq:
                if step.get("type") == "POS":
                    p_name = step.get("point_name", step.get("name"))
                    if p_name == target_point_name: step["coords"] = list(new_coords)
        
        if self.plc_client and self.plc_client.is_connected:
            try:
                sorted_names = sorted(list(self.position_points.keys()))
                point_idx = sorted_names.index(target_point_name)
                base_addr = self.plc_client.POINT_BASE_ADDR + (point_idx * self.plc_client.POINT_SIZE)
                for i, val in enumerate(new_coords):
                    target_addr = base_addr + 2 + (i * 2)
                    send_val = int(val * 1000)
                    self.plc_client.write_dint(0x09, target_addr, send_val)
            except Exception as e:
                print(f"[Position] PLC 포지션 값 전송 실패: {e}")

        self._on_combo_changed(self.point_combo.currentIndex())
        self.sig_sequence_changed.emit()

        # 티칭 후 자동으로 다음 포인트로 이동
        next_idx = self.point_combo.currentIndex() + 1
        if next_idx < self.point_combo.count():
            self.point_combo.setCurrentIndex(next_idx)

