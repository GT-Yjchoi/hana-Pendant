# ui/dialogs/sequence_utils.py

from PySide6.QtCore import Qt, Signal, QObject, QEvent, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QWidget, QListWidget, QGridLayout, QFrame, QScrollArea, QScroller, QScrollerProperties
)

# 시퀀스 편집기 팝업 GPU(QML) 이식: 계약 유지, 내부 렌더만 QML.
from ui.dialogs.qml_overlay import QmlMessageDialog


def apply_touch_scroll(scroll_area):
    """QScrollArea에 터치 스크롤 적용 (Raspberry Pi 터치스크린 대응)"""
    QScroller.grabGesture(scroll_area.viewport(), QScroller.TouchGesture)
    QScroller.grabGesture(scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
    scroller = QScroller.scroller(scroll_area.viewport())
    props = scroller.scrollerProperties()
    props.setScrollMetric(QScrollerProperties.MousePressEventDelay, 0.05)
    props.setScrollMetric(QScrollerProperties.DragStartDistance, 0.005)
    props.setScrollMetric(QScrollerProperties.DecelerationFactor, 0.9)
    scroller.setScrollerProperties(props)


class DragScrollFilter(QObject):
    """버튼 위에서도 드래그로 스크롤되는 이벤트 필터.
    임계값(THRESHOLD) 이상 드래그하면 스크롤 모드로 전환되고,
    짧은 탭은 클릭으로 처리한다."""
    THRESHOLD = 12  # 드래그 판정 픽셀

    def __init__(self, scroll_area):
        super().__init__(scroll_area)
        self._scroll = scroll_area
        self._press_pos = None
        self._last_pos = None
        self._is_scrolling = False

    def attach(self, container_widget):
        """컨테이너와 그 하위 버튼 전부에 필터 등록"""
        self._scroll.viewport().installEventFilter(self)
        container_widget.installEventFilter(self)
        for btn in container_widget.findChildren(QPushButton):
            btn.installEventFilter(self)

    def eventFilter(self, obj, event):
        t = event.type()
        if t == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._last_pos = self._press_pos
            self._is_scrolling = False
            return False  # 버튼이 press 이벤트를 받도록 허용

        elif t == QEvent.MouseMove and (event.buttons() & Qt.LeftButton):
            if self._press_pos is not None:
                curr = event.globalPosition().toPoint()
                if not self._is_scrolling:
                    if (curr - self._press_pos).manhattanLength() > self.THRESHOLD:
                        self._is_scrolling = True
                if self._is_scrolling:
                    delta = curr - self._last_pos
                    self._last_pos = curr
                    bar = self._scroll.verticalScrollBar()
                    bar.setValue(bar.value() - delta.y())
                    return True  # 이동 이벤트 소비 (버튼에 전달 안 함)

        elif t == QEvent.MouseButtonRelease:
            scrolled = self._is_scrolling
            self._press_pos = None
            self._last_pos = None
            self._is_scrolling = False
            if scrolled:
                return True  # 스크롤 중이었으면 release 소비 (클릭 방지)

        return False

# 터치 키보드 임포트 (경로 주의)
try:
    from widgets.touch_keyboard import TouchKeyboard
except ImportError:
    TouchKeyboard = None

# =========================================================
# [공통] 오버레이 다이얼로그 부모 클래스
# =========================================================
class OverlayDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 팝업 열기 전 최상위 윈도우를 캡처 → 배경이 검게 날아가는 문제 방지
        self._bg_pixmap = parent.window().grab() if parent else None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.content_frame = QFrame()
        self.content_frame.setObjectName("ContentFrame")
        self.content_frame.setStyleSheet("""
            QFrame#ContentFrame {
                background: #1E232D;
                border: 2px solid #468CFF;
                border-radius: 12px;
            }
        """)

        self.main_layout.addWidget(self.content_frame)
        self.layout = QVBoxLayout(self.content_frame)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

    def setFixedContentSize(self, w, h):
        self.content_frame.setFixedSize(w, h)

    def exec(self):
        result = super().exec()
        # 닫힌 뒤 명시적 삭제 → QScroller TouchGesture 인식기 즉시 해제
        # (parent=self로 생성된 경우 Qt 부모-자식 관계가 C++ 객체를 계속 살려두어
        #  gesture recognizer가 누적되고 터치 응답이 점점 느려지는 것을 방지)
        self.deleteLater()
        return result

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor
        painter = QPainter(self)
        if self._bg_pixmap:
            painter.drawPixmap(0, 0, self._bg_pixmap)  # 1:1 스케일, 스트레칭 없음
        else:
            painter.fillRect(self.rect(), QColor(20, 25, 35, 255))
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

# =========================================================
# [★ 신규] 포인트 선택 팝업 (작은 박스 5열)
# =========================================================
class PointListDialog(OverlayDialog):
    def __init__(self, points, current_point, parent=None):
        super().__init__(parent)
        self.selected_point = None
        self.setFixedContentSize(850, 600) 
        
        self.layout.addWidget(QLabel("[P] 목표 위치 포인트를 선택하세요"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        apply_touch_scroll(scroll)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(10)

        # 박스 스타일
        btn_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid #666;
                border-radius: 6px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                min-width: 110px; 
                min-height: 55px;
            }
            QPushButton:hover {
                border-color: #468CFF;
                background-color: rgba(70, 140, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(70, 140, 255, 0.3);
            }
            QPushButton#Current {
                border: 2px solid #00FF7F;
                color: #00FF7F;
                background-color: rgba(0, 255, 127, 0.15);
            }
        """
        
        row, col = 0, 0
        cols_limit = 5 # 5열
        
        sorted_points = sorted(points)
        
        for name in sorted_points:
            btn = QPushButton(name)
            btn.setStyleSheet(btn_style)
            
            if name == current_point:
                btn.setObjectName("Current")
                
            btn.clicked.connect(lambda checked, n=name: self._on_selected(n))
            grid.addWidget(btn, row, col)
            
            col += 1
            if col >= cols_limit:
                col = 0
                row += 1
                
        if row == 0: grid.setRowStretch(1, 1)
        else: grid.setRowStretch(row + 1, 1)
                
        scroll.setWidget(container)
        self.layout.addWidget(scroll)
        
        btn_close = QPushButton("취소")
        btn_close.setFixedHeight(45)
        btn_close.setStyleSheet("""
            QPushButton { background: rgba(255, 255, 255, 0.1); border: 1px solid #888; color: white; border-radius: 8px; font-size: 15px; }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.2); }
        """)
        btn_close.clicked.connect(self.reject)
        self.layout.addWidget(btn_close)

    def _on_selected(self, name):
        self.selected_point = name
        self.accept()
        
    def get_selected(self):
        return self.selected_point

# =========================================================
# [기존] 시퀀스 목록 팝업 (큰 박스 4열)
# =========================================================
class SequenceListDialog(OverlayDialog):
    def __init__(self, sequences, current_seq, parent=None, seq_map=None):
        super().__init__(parent)
        self.selected_seq = None
        self.rename_requested = None
        self.setFixedContentSize(850, 600)

        self.layout.addWidget(QLabel(" 이동할 시퀀스를 선택하세요"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        apply_touch_scroll(scroll)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(15)

        btn_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 2px solid #555;
                border-radius: 10px;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                min-width: 140px;
                min-height: 80px;
            }
            QPushButton:hover { border-color: #468CFF; background-color: rgba(70, 140, 255, 0.1); }
            QPushButton:pressed { background-color: rgba(70, 140, 255, 0.3); }
            QPushButton#Current { border: 2px solid #00FF7F; color: #00FF7F; background-color: rgba(0, 255, 127, 0.1); }
            QPushButton#Monitor { border: 2px solid #FFB400; color: #FFB400; background-color: rgba(255,180,0,0.08); }
            QPushButton#MonitorCurrent { border: 2px solid #FFB400; color: #FFB400; background-color: rgba(255,180,0,0.25); }
        """

        row, col = 0, 0
        cols_limit = 4

        from ui.dialogs.sequence_editor_dialog import MONITOR_SEQ_KEY
        normal_keys = ["Main"] + sorted([k for k in sequences if k not in ("Main", MONITOR_SEQ_KEY)])
        monitor_keys = [k for k in sequences if k == MONITOR_SEQ_KEY]
        seq_keys = normal_keys + monitor_keys

        for name in seq_keys:
            slot = seq_map.get(name, "?") if seq_map else "?"
            btn = QPushButton(f"[{slot}] {name}")
            btn.setStyleSheet(btn_style)
            if name == MONITOR_SEQ_KEY:
                btn.setObjectName("MonitorCurrent" if name == current_seq else "Monitor")
            elif name == current_seq:
                btn.setObjectName("Current")
            self._setup_btn_actions(btn, name)
            grid.addWidget(btn, row, col)
            col += 1
            if col >= cols_limit: col = 0; row += 1

        if row == 0: grid.setRowStretch(1, 1)
        else: grid.setRowStretch(row + 1, 1)

        scroll.setWidget(container)
        self.layout.addWidget(scroll)

        # 길게 눌러 이름 변경 기능 제거 - 시퀀스 편집기의 [이름변경] 버튼으로 대체

        btn_close = QPushButton("닫기")
        btn_close.setFixedHeight(50)
        btn_close.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.1); border: 1px solid #888; color: white; border-radius: 8px; font-size: 15px; }")
        btn_close.clicked.connect(self.reject)
        self.layout.addWidget(btn_close)

    def _setup_btn_actions(self, btn, name):
        # 단순 클릭으로 선택만 수행. 이름 변경은 편집기의 [이름변경] 버튼에서 처리.
        btn.clicked.connect(lambda _=False, n=name: self._on_selected(n))

    def _on_selected(self, name):
        self.selected_seq = name
        self.accept()
    def get_selected(self): return self.selected_seq

# =========================================================
# [★ 신규] 카드형 선택 팝업 (범용 - IO/JMP/CALL 등)
# =========================================================
class CardListDialog(OverlayDialog):
    """
    카드 형식으로 항목을 선택하는 팝업
    - items     : 표시할 항목 리스트 (문자열)
    - current   : 현재 선택된 항목
    - columns   : 열 개수 (기본 4)
    - on_delete : 삭제 콜백(item) — 제공 시 ✕ 버튼 표시 ("+"로 시작 제외)
    """
    CARD_H = 95  # 모든 카드 공통 높이

    def __init__(self, items, current=None, title="항목을 선택하세요", columns=4,
                 on_delete=None, on_rename=None, rename_handler=None, parent=None):
        super().__init__(parent)
        self.selected_item = None
        self._columns = columns
        self._current = current
        self._on_delete_cb = on_delete
        self._on_rename_cb = on_rename
        # rename_handler: 호출자가 전체 rename 흐름을 직접 처리 (시그니처: (item, parent_dialog) -> new_display_str or None)
        # None 반환 시 취소. RenameDialog 자동 호출을 완전히 대체함.
        self._rename_handler = rename_handler
        self._items = list(items)
        self.setFixedContentSize(850, 600)

        # 타이틀
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #468CFF; font-size: 18px; font-weight: bold;")
        lbl_title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(lbl_title)

        # 스크롤 영역
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("background: transparent; border: none;")
        apply_touch_scroll(self._scroll)

        self._grid_container = QWidget()
        self._grid = QGridLayout(self._grid_container)
        self._grid.setSpacing(10)
        self._grid.setContentsMargins(10, 10, 10, 10)

        self._build_grid()

        self._scroll.setWidget(self._grid_container)
        self.layout.addWidget(self._scroll)

        drag_filter = DragScrollFilter(self._scroll)
        drag_filter.attach(self._grid_container)

        btn_close = QPushButton("X 닫기")
        btn_close.setFixedHeight(45)
        btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid #888;
                color: white;
                border-radius: 8px;
                font-size: 15px;
            }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.2); }
        """)
        btn_close.clicked.connect(self.reject)
        self.layout.addWidget(btn_close)

    def _build_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        is_current = lambda i: self._current and i == self._current

        row, col = 0, 0
        for item in self._items:
            show_actions = (self._on_delete_cb is not None or self._on_rename_cb is not None or self._rename_handler is not None) and not item.startswith("+")

            if show_actions:
                # ── 액션 버튼 포함 카드 ──
                frame = QFrame()
                frame.setFixedHeight(self.CARD_H)
                frame.setCursor(Qt.PointingHandCursor)
                frame.setStyleSheet("""
                    QFrame {
                        background-color: %s;
                        border: %s;
                        border-radius: 8px;
                    }
                """ % (
                    "rgba(0,255,127,0.15)" if is_current(item) else "rgba(255,255,255,0.05)",
                    "2px solid #00FF7F"    if is_current(item) else "1px solid #555",
                ))
                frame.mousePressEvent = lambda e, i=item: self._on_selected(i)

                f_layout = QVBoxLayout(frame)
                f_layout.setContentsMargins(6, 6, 6, 6)
                f_layout.setSpacing(4)

                # 상단 행: 이름(선택 버튼) + ✎ + ✕
                top_row = QHBoxLayout()
                top_row.setContentsMargins(0, 0, 0, 0)
                top_row.setSpacing(4)

                btn_name = QPushButton(item)
                btn_name.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        color: %s;
                        font-size: 13px;
                        font-weight: bold;
                        text-align: center;
                        padding: 0 2px;
                    }
                    QPushButton:pressed { color: #468CFF; }
                """ % ("#00FF7F" if is_current(item) else "#DDD"))
                btn_name.setCursor(Qt.PointingHandCursor)
                btn_name.clicked.connect(lambda checked, i=item: self._on_selected(i))
                top_row.addWidget(btn_name, 1)

                if self._on_rename_cb is not None or self._rename_handler is not None:
                    btn_rename = QPushButton("✎")
                    btn_rename.setFixedSize(28, 28)
                    btn_rename.setStyleSheet("""
                        QPushButton {
                            background: rgba(70,140,255,0.2);
                            border: 1px solid rgba(70,140,255,0.5);
                            border-radius: 6px;
                            color: #7EB8FF;
                            font-size: 14px;
                            font-weight: bold;
                            padding: 0;
                        }
                        QPushButton:pressed {
                            background: rgba(70,140,255,0.5);
                            color: white;
                        }
                    """)
                    btn_rename.clicked.connect(lambda checked, i=item: self._rename_item(i))
                    top_row.addWidget(btn_rename)

                if self._on_delete_cb is not None:
                    btn_del = QPushButton("✕")
                    btn_del.setFixedSize(28, 28)
                    btn_del.setStyleSheet("""
                        QPushButton {
                            background: rgba(200,50,50,0.25);
                            border: 1px solid rgba(255,70,70,0.5);
                            border-radius: 6px;
                            color: #FF6B6B;
                            font-size: 14px;
                            font-weight: bold;
                            padding: 0;
                        }
                        QPushButton:pressed {
                            background: rgba(255,70,70,0.5);
                            color: white;
                        }
                    """)
                    btn_del.clicked.connect(lambda checked, i=item: self._delete_item(i))
                    top_row.addWidget(btn_del)

                f_layout.addLayout(top_row)
                f_layout.addStretch(1)

                self._grid.addWidget(frame, row, col)

            else:
                # ── 일반 버튼 카드 ──
                btn = QPushButton(item)
                btn.setFixedHeight(self.CARD_H)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: %s;
                        border: %s;
                        border-radius: 8px;
                        color: %s;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 10px;
                        min-width: 120px;
                    }
                    QPushButton:pressed {
                        background-color: rgba(70, 140, 255, 0.3);
                    }
                """ % (
                    "rgba(0,255,127,0.15)" if is_current(item) else "rgba(255,255,255,0.05)",
                    "2px solid #00FF7F"    if is_current(item) else "1px solid #666",
                    "#00FF7F"              if is_current(item) else "white",
                ))
                btn.clicked.connect(lambda checked, i=item: self._on_selected(i))
                self._grid.addWidget(btn, row, col)

            col += 1
            if col >= self._columns:
                col = 0
                row += 1

    def _delete_item(self, item):
        if self._on_delete_cb:
            self._on_delete_cb(item)
        if item in self._items:
            self._items.remove(item)
        self._build_grid()

    def _rename_item(self, item):
        # rename_handler 가 있으면 호출자가 모든 처리 담당 (RenameDialog 직접 띄움/초기값 커스터마이즈 가능)
        if self._rename_handler is not None:
            new_display = self._rename_handler(item, self)
            if new_display is None:
                return  # 취소
            idx = self._items.index(item)
            self._items[idx] = new_display
            if self._current == item:
                self._current = new_display
            self._build_grid()
            return

        if not self._on_rename_cb:
            return
        existing = [i for i in self._items if i != item and not i.startswith("+")]
        dlg = RenameDialog(item, existing, parent=self, confirm_text="변경")
        if dlg.exec() == QDialog.Accepted:
            new_name = dlg.get_new_name()
            if new_name and new_name != item:
                # 콜백이 새 display 문자열을 반환하면 그걸 카드에 쓰고,
                # 아니면 사용자가 입력한 new_name 을 그대로 씀.
                result = self._on_rename_cb(item, new_name)
                display = result if isinstance(result, str) and result else new_name
                idx = self._items.index(item)
                self._items[idx] = display
                if self._current == item:
                    self._current = display
                self._build_grid()

    def _on_selected(self, item):
        self.selected_item = item
        self.accept()

    def get_selected(self):
        return self.selected_item

# =========================================================
# [1] 알림 메시지 다이얼로그
# =========================================================
# [QML 이식] 계약(생성자·.exec()→Accepted/Rejected) 동일, 렌더만 GPU.
class DarkMessageDialog(QmlMessageDialog):
    def __init__(self, title, message, is_error=False, parent=None):
        accent = "#FF4646" if is_error else "#468CFF"
        super().__init__(title, message, accent=accent, two_buttons=False,
                         frame_w=520, frame_h=280, parent=parent)

# =========================================================
# [2] 다크 테마 확인 다이얼로그  (QML 이식, 계약 동일)
# =========================================================
class DarkConfirmDialog(QmlMessageDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(title, message, accent="#468CFF", two_buttons=True,
                         frame_w=400, frame_h=220, parent=parent)

# =========================================================
# [3] 팝업 리스트 선택기 (ComboBox 대체)
# =========================================================
class PopupListSelector(QWidget):
    currentIndexChanged = Signal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self._current_index = -1
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.btn = QPushButton("선택하세요")
        self.btn.setStyleSheet("""
            QPushButton {
                background: rgba(40, 45, 55, 250);
                border: 1px solid rgba(70, 140, 255, 100);
                border-radius: 6px;
                color: white;
                font-size: 14px;
                padding: 8px 12px;
                text-align: left;
            }
            QPushButton:hover { border: 1px solid rgba(70, 140, 255, 200); }
        """)
        self.btn.clicked.connect(self._show_popup)
        layout.addWidget(self.btn)
    
    def addItems(self, items):
        self.items = list(items)
        if self.items and self._current_index < 0:
            self._current_index = 0
            self.btn.setText(self.items[0])
    
    def setCurrentIndex(self, index):
        if 0 <= index < len(self.items):
            self._current_index = index
            self.btn.setText(self.items[index])
        elif index == -1:
            self._current_index = -1
            self.btn.setText("선택하세요")
    
    def currentIndex(self): return self._current_index
    def currentText(self): return self.items[self._current_index] if 0 <= self._current_index < len(self.items) else ""
    def count(self): return len(self.items)
    def clear(self): self.items = []; self._current_index = -1; self.btn.setText("선택하세요")
    def addItem(self, text): self.items.append(text); self._current_index = 0 if self._current_index < 0 else self._current_index; self.btn.setText(text) if self._current_index==0 else None
    def setFixedHeight(self, h): self.btn.setFixedHeight(h)
    
    def _show_popup(self):
        if not self.items: return
        dlg = QDialog(self.window()) 
        dlg.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        dlg.setWindowState(Qt.WindowFullScreen)
        dlg.setAttribute(Qt.WA_TranslucentBackground)
        dlg.paintEvent = lambda e: self._paint_dim(dlg)
        
        layout = QVBoxLayout(dlg)
        layout.setAlignment(Qt.AlignCenter)
        content = QFrame()
        content.setStyleSheet("background: #141E28; border: 2px solid #468CFF; border-radius: 8px;")
        item_height = 40
        visible_count = min(len(self.items), 10)
        popup_height = visible_count * item_height + 20
        content.setFixedSize(300, popup_height)
        cl = QVBoxLayout(content)
        cl.setContentsMargins(5, 5, 5, 5)
        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: white; font-size: 16px; outline: none; }
            QListWidget::item { height: 38px; padding-left: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }
            QListWidget::item:selected { background: rgba(70, 140, 255, 150); border-radius: 4px; }
        """)
        list_widget.addItems(self.items)
        if self._current_index >= 0: list_widget.setCurrentRow(self._current_index)
        list_widget.itemClicked.connect(lambda item: self._on_item_selected(item, dlg))
        cl.addWidget(list_widget)
        layout.addWidget(content)
        dlg.exec()
    
    def _paint_dim(self, widget):
        from PySide6.QtGui import QPainter, QColor
        painter = QPainter(widget)
        painter.fillRect(widget.rect(), QColor(0, 0, 0, 100))

    def _on_item_selected(self, item, dlg):
        idx = self.items.index(item.text()) if item.text() in self.items else -1
        if idx >= 0:
            self._current_index = idx
            self.btn.setText(item.text())
            self.currentIndexChanged.emit(idx)
        dlg.accept()

# =========================================================
# [★] 표시 조건 복수 선택 다이얼로그
# =========================================================
def _normalize_vis_mode(vm):
    """int(구버전) → list 변환. 이미 list면 그대로 반환."""
    if isinstance(vm, list):
        return vm
    if isinstance(vm, int):
        return [] if vm < 0 else [vm]
    return []

def _vis_mode_summary(selected_indices, mode_names_fn):
    """선택된 모드 인덱스 목록 → 버튼 표시 텍스트."""
    if not selected_indices:
        return "항상 표시"
    names = [f"[{i:02d}] {mode_names_fn(i)}" for i in sorted(selected_indices)]
    if len(names) == 1:
        return names[0]
    return f"{names[0]} 외 {len(names)-1}개"


class VisModeMultiPickerDialog(OverlayDialog):
    """
    44개 모드 카드를 복수 선택할 수 있는 팝업.
    accept() 후 get_selected_modes() → list[int] (빈 리스트 = 항상 표시)
    """
    _MODE_NAMES = [
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
    COLS = 4

    def __init__(self, current_modes=None, parent=None):
        super().__init__(parent)
        self._selected = set(current_modes or [])
        self.setFixedContentSize(860, 580)

        self.setStyleSheet("""
            QLabel { color: white; font-size: 15px; font-weight: bold;
                     border: none; background: transparent; }
            QPushButton#always {
                background: rgba(255,255,255,0.08); border: 1px solid #555;
                border-radius: 8px; color: #95A5A6;
                font-size: 15px; font-weight: bold; height: 44px;
            }
            QPushButton#always:checked {
                background: rgba(46,204,113,0.20); border: 2px solid #2ECC71;
                color: #2ECC71;
            }
            QPushButton#always:pressed { background: rgba(255,255,255,0.18); }
            QPushButton#ok {
                background: rgba(46,204,113,0.20); border: 1px solid #2ECC71;
                border-radius: 8px; color: #2ECC71;
                font-size: 16px; font-weight: bold; height: 46px;
            }
            QPushButton#ok:pressed { background: rgba(46,204,113,0.45); }
            QPushButton#cancel {
                background: rgba(255,70,70,0.15); border: 1px solid #FF4646;
                border-radius: 8px; color: #FF6B6B;
                font-size: 16px; font-weight: bold; height: 46px;
            }
            QPushButton#cancel:pressed { background: rgba(255,70,70,0.35); }
        """)

        # 타이틀
        lbl = QLabel("표시 조건 선택  (복수 선택 가능)")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #468CFF; font-size: 17px; font-weight: bold;")
        self.layout.addWidget(lbl)

        # 항상 표시 토글
        self.btn_always = QPushButton("★ 항상 표시")
        self.btn_always.setObjectName("always")
        self.btn_always.setCheckable(True)
        self.btn_always.setChecked(not self._selected)
        self.btn_always.clicked.connect(self._on_always_toggled)
        self.layout.addWidget(self.btn_always)

        # 모드 카드 그리드 (스크롤)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("background: transparent; border: none;")
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        apply_touch_scroll(self._scroll)

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(8)
        self._grid.setContentsMargins(4, 4, 4, 4)
        self._scroll.setWidget(self._grid_widget)
        self.layout.addWidget(self._scroll, 1)

        self._mode_btns = {}
        self._build_mode_grid()

        # 하단 버튼
        foot = QHBoxLayout()
        foot.setSpacing(10)
        btn_cancel = QPushButton("취소")
        btn_cancel.setObjectName("cancel")
        btn_cancel.setFixedHeight(46)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("완료")
        btn_ok.setObjectName("ok")
        btn_ok.setFixedHeight(46)
        btn_ok.clicked.connect(self.accept)
        foot.addWidget(btn_cancel)
        foot.addWidget(btn_ok)
        self.layout.addLayout(foot)

    def _mode_name(self, idx):
        try:
            from utils.mode_manager import ModeManager
            mgr = ModeManager.instance() if ModeManager else None
            if mgr:
                return mgr.get_name(idx)
        except Exception:
            pass
        return self._MODE_NAMES[idx] if idx < len(self._MODE_NAMES) else f"User Mode {idx-33}"

    def _build_mode_grid(self):
        for i in range(44):
            row, col = divmod(i, self.COLS)
            name = self._mode_name(i)
            btn = QPushButton(f"[{i:02d}]\n{name}")
            btn.setCheckable(True)
            btn.setChecked(i in self._selected)
            btn.setFixedHeight(60)
            btn.setStyleSheet(self._card_style(i in self._selected))
            btn.clicked.connect(lambda checked, idx=i: self._on_mode_toggled(idx, checked))
            self._grid.addWidget(btn, row, col)
            self._mode_btns[i] = btn

    def _card_style(self, checked):
        if checked:
            return ("QPushButton { background: rgba(46,204,113,0.20); border: 2px solid #2ECC71; "
                    "border-radius: 8px; color: #2ECC71; font-size: 12px; font-weight: bold; }"
                    "QPushButton:pressed { background: rgba(46,204,113,0.40); }")
        return ("QPushButton { background: rgba(255,255,255,0.05); border: 1px solid #444; "
                "border-radius: 8px; color: #AAA; font-size: 12px; font-weight: bold; }"
                "QPushButton:pressed { background: rgba(70,140,255,0.20); }")

    def _on_always_toggled(self, checked):
        if checked:
            self._selected.clear()
            for idx, btn in self._mode_btns.items():
                btn.setChecked(False)
                btn.setStyleSheet(self._card_style(False))

    def _on_mode_toggled(self, idx, checked):
        if checked:
            self._selected.add(idx)
            self.btn_always.setChecked(False)
        else:
            self._selected.discard(idx)
            if not self._selected:
                self.btn_always.setChecked(True)
        self._mode_btns[idx].setStyleSheet(self._card_style(checked))

    def get_selected_modes(self):
        """빈 리스트 = 항상 표시, 나머지 = 선택된 모드 인덱스 리스트."""
        return sorted(self._selected)


# =========================================================
# [4] 이름 변경 다이얼로그 (Rename)
# =========================================================
class RenameDialog(OverlayDialog):
    def __init__(self, current_name, existing_names, parent=None, confirm_text="변경",
                 visible_mode=None, initial_text=None, allow_empty=False):
        super().__init__(parent)
        self.existing_names = [n for n in existing_names if n != current_name]
        self._current_name = current_name
        self._allow_empty = allow_empty
        # visible_mode=None → 표시 조건 UI 숨김
        # visible_mode=int or list → 표시 조건 UI 표시 (int는 하위 호환 변환)
        self._visible_mode = _normalize_vis_mode(visible_mode) if visible_mode is not None else None
        self.setWindowTitle("명칭 변경")
        self.setFixedContentSize(450, 260 if visible_mode is None else 350)
        self.setStyleSheet("""
            QLabel { color: white; font-size: 16px; font-weight: bold; border: none; background: transparent; }
            QLineEdit { background: #2b2b2b; border: 1px solid #555; border-radius: 6px; color: white; font-size: 18px; padding: 8px; }
            QPushButton { background: rgba(70, 140, 255, 40); border: 1px solid rgba(70, 140, 255, 100); border-radius: 6px; color: white; font-size: 14px; height: 40px; }
            QPushButton:pressed { background: rgba(70, 140, 255, 80); }
        """)
        self.layout.addWidget(QLabel("이름을 입력하세요:"))
        input_layout = QHBoxLayout()
        # initial_text 가 주어지면 그걸 씀. None 이면 current_name (기존 동작)
        _init = initial_text if initial_text is not None else current_name
        self.input_field = QLineEdit(_init)
        input_layout.addWidget(self.input_field)
        btn_keyboard = QPushButton("⌨")
        btn_keyboard.setFixedSize(50, 40)
        btn_keyboard.setStyleSheet("font-size: 22px;")
        btn_keyboard.clicked.connect(self._open_keyboard)
        input_layout.addWidget(btn_keyboard)
        self.layout.addLayout(input_layout)
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #FF4646; font-size: 13px;")
        self.layout.addWidget(self.lbl_error)

        # ★ 표시 조건 (visible_mode가 None이 아닐 때만 표시)
        if visible_mode is not None:
            lbl_vis = QLabel("표시 조건")
            lbl_vis.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 14px; font-weight: bold;")
            self.layout.addWidget(lbl_vis)
            self.btn_vis = QPushButton()
            self.btn_vis.clicked.connect(self._open_vis_mode_picker)
            self.layout.addWidget(self.btn_vis)
            self._refresh_vis_btn()

        self.layout.addStretch(1)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton(confirm_text)
        btn_cancel = QPushButton("취소")
        btn_ok.clicked.connect(self.check_and_accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        self.layout.addLayout(btn_layout)

    def _open_keyboard(self):
        if TouchKeyboard:
            kb = TouchKeyboard("이름 입력", self.input_field.text(), self)
            if kb.exec() == QDialog.Accepted:
                self.input_field.setText(kb.get_text())

    def _mode_name(self, idx):
        try:
            from utils.mode_manager import ModeManager
            mgr = ModeManager.instance() if ModeManager else None
            if mgr:
                return mgr.get_name(idx)
        except Exception:
            pass
        return VisModeMultiPickerDialog._MODE_NAMES[idx] if idx < len(VisModeMultiPickerDialog._MODE_NAMES) else f"User Mode {idx-33}"

    def _refresh_vis_btn(self):
        if self._visible_mode is None or not hasattr(self, 'btn_vis'):
            return
        text = _vis_mode_summary(self._visible_mode, self._mode_name)
        is_always = not self._visible_mode
        self.btn_vis.setText(text)
        if is_always:
            self.btn_vis.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.08); border: 1px solid #666; border-radius: 6px; "
                "color: #95A5A6; font-size: 15px; font-weight: bold; height: 45px; text-align: left; padding-left: 15px; }"
                "QPushButton:pressed { background: rgba(255,255,255,0.2); }"
            )
        else:
            self.btn_vis.setStyleSheet(
                "QPushButton { background: rgba(46,204,113,0.15); border: 1px solid #2ECC71; border-radius: 6px; "
                "color: #2ECC71; font-size: 15px; font-weight: bold; height: 45px; text-align: left; padding-left: 15px; }"
                "QPushButton:pressed { background: rgba(46,204,113,0.35); }"
            )

    def _open_vis_mode_picker(self):
        dlg = VisModeMultiPickerDialog(self._visible_mode or [], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._visible_mode = dlg.get_selected_modes()
            self._refresh_vis_btn()

    def check_and_accept(self):
        new_name = self.input_field.text().strip()
        if not new_name and not self._allow_empty:
            self.lbl_error.setText("이름을 입력해주세요.")
            return
        if new_name and new_name in self.existing_names:
            self.lbl_error.setText(f"이미 존재하는 이름입니다: {new_name}")
            return
        self.accept()

    def get_new_name(self):
        return self.input_field.text().strip()

    def get_visible_mode(self):
        return self._visible_mode

# =========================================================
# [5] 숫자 키패드 (Numeric Keypad) - 문법 수정됨
# =========================================================
class NumericKeypad(OverlayDialog):
    def __init__(self, title="숫자 입력", default_value=0.0, decimals=2, parent=None, password_mode=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.decimals = decimals
        self.is_first_input = True
        self._password_mode = password_mode
        self._raw_input = ""

        self.setFixedContentSize(360, 500)
        
        self.setStyleSheet("""
            QLabel { color: white; font-size: 18px; font-weight: bold; border: none; background: transparent;}
            QLineEdit { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; color: white; font-size: 32px; font-weight: bold; padding: 10px; }
            QPushButton { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; font-size: 24px; font-weight: bold; }
            QPushButton:pressed { background: rgba(70, 140, 255, 100); }
            QPushButton#action { background: rgba(70, 140, 255, 50); border: 1px solid #468CFF; }
            QPushButton#cancel { background: rgba(255, 70, 70, 50); border: 1px solid #FF4646; }
        """)
        
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color: #468CFF;")
        self.layout.addWidget(lbl_title)
        
        self.input_field = QLineEdit("" if password_mode else str(default_value))
        self.input_field.setAlignment(Qt.AlignRight)
        self.input_field.setReadOnly(True)
        self.layout.addWidget(self.input_field)
        
        grid = QGridLayout()
        grid.setSpacing(8)
        
        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('±', 3, 0), ('0', 3, 1), ('.', 3, 2),
        ]
        
        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setFixedHeight(65)
            btn.clicked.connect(lambda checked, t=text: self._on_key(t))
            grid.addWidget(btn, row, col)
        
        btn_clear = QPushButton("C")
        btn_clear.setFixedHeight(65)
        btn_clear.clicked.connect(self._on_clear)
        grid.addWidget(btn_clear, 0, 3)
        
        btn_back = QPushButton("←")
        btn_back.setFixedHeight(65)
        btn_back.clicked.connect(self._on_backspace)
        grid.addWidget(btn_back, 1, 3)
        
        btn_ok = QPushButton("확인")
        btn_ok.setObjectName("action")
        btn_ok.setFixedHeight(138)
        btn_ok.clicked.connect(self.accept)
        grid.addWidget(btn_ok, 2, 3, 2, 1)
        
        self.layout.addLayout(grid)
        
        btn_cancel = QPushButton("취소")
        btn_cancel.setObjectName("cancel")
        btn_cancel.setFixedHeight(50)
        btn_cancel.clicked.connect(self.reject)
        self.layout.addWidget(btn_cancel)
    
    def _on_key(self, key):
        if self._password_mode:
            if key.isdigit():
                self._raw_input += key
                self.input_field.setText('*' * len(self._raw_input))
            return

        current = self.input_field.text()
        if self.is_first_input:
            if key == '±':
                self.input_field.setText('-')
            elif key == '.':
                self.input_field.setText('0.')
            else:
                self.input_field.setText(key)
            self.is_first_input = False
            return

        if key == '±':
            if current.startswith('-'):
                self.input_field.setText(current[1:])
            else:
                self.input_field.setText('-' + current)
        elif key == '.':
            if '.' not in current:
                self.input_field.setText(current + '.')
        else:
            if current == '0':
                self.input_field.setText(key)
            else:
                self.input_field.setText(current + key)

    def _on_clear(self):
        if self._password_mode:
            self._raw_input = ""
            self.input_field.setText("")
            return
        self.input_field.setText('0')
        self.is_first_input = True

    def _on_backspace(self):
        if self._password_mode:
            self._raw_input = self._raw_input[:-1]
            self.input_field.setText('*' * len(self._raw_input))
            return
        current = self.input_field.text()
        if len(current) > 1:
            self.input_field.setText(current[:-1])
        else:
            self.input_field.setText('0')
            self.is_first_input = True

    def get_value(self):
        try:
            if self._password_mode:
                return round(float(self._raw_input), self.decimals) if self._raw_input else 0.0
            return round(float(self.input_field.text()), self.decimals)
        except ValueError:
            return 0.0

# =========================================================
# [6] 새 포인트 이름 입력 (New Point) - 문법 수정됨
# =========================================================
class NewPointDialog(OverlayDialog):
    def __init__(self, existing_names, parent=None):
        super().__init__(parent)
        self.existing_names = existing_names
        self._visible_mode = []  # [] = 항상 표시
        self.setWindowTitle("새 위치 포인트")
        self.setFixedContentSize(450, 340)

        self.setStyleSheet("""
            QLabel { color: white; font-size: 16px; font-weight: bold; border: none; background: transparent; }
            QLineEdit { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; color: white; font-size: 20px; font-weight: bold; padding: 10px; }
            QPushButton { background: rgba(70, 140, 255, 40); border: 1px solid rgba(70, 140, 255, 100); border-radius: 8px; color: white; font-size: 16px; font-weight: bold; height: 50px; }
            QPushButton:pressed { background: rgba(70, 140, 255, 80); }
            QPushButton#cancel { background: rgba(255, 70, 70, 40); border: 1px solid rgba(255, 70, 70, 100); }
        """)

        lbl_title = QLabel("[P] 새 위치 포인트 이름")
        lbl_title.setStyleSheet("color: #468CFF; font-size: 18px; margin-bottom: 10px;")
        self.layout.addWidget(lbl_title)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("포인트 이름 입력...")
        input_layout.addWidget(self.input_field)

        btn_keyboard = QPushButton("⌨")
        btn_keyboard.setFixedSize(60, 50)
        btn_keyboard.setStyleSheet("font-size: 26px;")
        btn_keyboard.clicked.connect(self._open_keyboard)
        input_layout.addWidget(btn_keyboard)
        self.layout.addLayout(input_layout)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #FF4646; font-size: 13px;")
        self.layout.addWidget(self.lbl_error)

        # ★ 표시 조건 선택
        lbl_vis = QLabel("표시 조건")
        lbl_vis.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 14px; font-weight: bold;")
        self.layout.addWidget(lbl_vis)

        self.btn_vis = QPushButton("항상 표시")
        self.btn_vis.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.08); border: 1px solid #666; border-radius: 8px; "
            "color: #95A5A6; font-size: 15px; font-weight: bold; height: 50px; text-align: left; padding-left: 15px; }"
            "QPushButton:pressed { background: rgba(255,255,255,0.2); }"
        )
        self.btn_vis.clicked.connect(self._open_vis_mode_picker)
        self.layout.addWidget(self.btn_vis)

        self.layout.addStretch(1)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("취소")
        btn_cancel.setObjectName("cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("생성")
        btn_ok.clicked.connect(self._on_ok)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        self.layout.addLayout(btn_layout)

    def _open_keyboard(self):
        if TouchKeyboard:
            kb = TouchKeyboard("위치 포인트 이름 입력", self.input_field.text(), self)
            if kb.exec() == QDialog.Accepted:
                self.input_field.setText(kb.get_text())

    def _mode_name(self, idx):
        try:
            from utils.mode_manager import ModeManager
            mgr = ModeManager.instance() if ModeManager else None
            if mgr:
                return mgr.get_name(idx)
        except Exception:
            pass
        return VisModeMultiPickerDialog._MODE_NAMES[idx] if idx < len(VisModeMultiPickerDialog._MODE_NAMES) else f"User Mode {idx-33}"

    def _refresh_vis_btn(self):
        text = _vis_mode_summary(self._visible_mode, self._mode_name)
        is_always = not self._visible_mode
        self.btn_vis.setText(text)
        if is_always:
            self.btn_vis.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.08); border: 1px solid #666; border-radius: 8px; "
                "color: #95A5A6; font-size: 15px; font-weight: bold; height: 50px; text-align: left; padding-left: 15px; }"
                "QPushButton:pressed { background: rgba(255,255,255,0.2); }"
            )
        else:
            self.btn_vis.setStyleSheet(
                "QPushButton { background: rgba(46,204,113,0.15); border: 1px solid #2ECC71; border-radius: 8px; "
                "color: #2ECC71; font-size: 15px; font-weight: bold; height: 50px; text-align: left; padding-left: 15px; }"
                "QPushButton:pressed { background: rgba(46,204,113,0.35); }"
            )

    def _open_vis_mode_picker(self):
        dlg = VisModeMultiPickerDialog(self._visible_mode, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._visible_mode = dlg.get_selected_modes()
            self._refresh_vis_btn()

    def _on_ok(self):
        name = self.input_field.text().strip()
        if not name:
            self.lbl_error.setText("이름을 입력해주세요.")
            return
        if name in self.existing_names:
            self.lbl_error.setText(f"이미 존재하는 이름입니다: {name}")
            return
        self.accept()

    def get_name(self):
        return self.input_field.text().strip()

    def get_visible_mode(self):
        return self._visible_mode


# =========================================================
# [★] 타이머 순서 변경 다이얼로그
# =========================================================
class TimerReorderDialog(OverlayDialog):
    """
    타이머 리스트를 보여주고 선택 후 ▲/▼ 버튼으로 순서를 변경하는 팝업.
    accept() 시 get_ordered_names() 로 새 순서를 반환.
    """
    def __init__(self, timer_names, parent=None):
        super().__init__(parent)
        self.setFixedContentSize(420, 560)

        self.setStyleSheet("""
            QLabel   { color: white; font-size: 16px; font-weight: bold;
                       border: none; background: transparent; }
            QListWidget {
                background: #1A222C;
                border: 1px solid #3E4A59;
                border-radius: 8px;
                color: #DDD;
                font-size: 17px;
                font-weight: bold;
                outline: 0;
            }
            QListWidget::item { padding: 10px 14px; border-bottom: 1px solid #2A3040; }
            QListWidget::item:selected {
                background: rgba(70,140,255,0.30);
                color: #7EB8FF;
                border-left: 3px solid #468CFF;
            }
            QPushButton {
                background: rgba(70,140,255,0.15);
                border: 1px solid rgba(70,140,255,0.5);
                border-radius: 8px;
                color: white;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:pressed { background: rgba(70,140,255,0.45); }
            QPushButton:disabled { background: rgba(255,255,255,0.05); color: #555;
                                   border: 1px solid #333; }
            QPushButton#ok     { background: rgba(46,204,113,0.20);
                                 border: 1px solid #2ECC71; color: #2ECC71; font-size: 16px; }
            QPushButton#ok:pressed { background: rgba(46,204,113,0.45); }
            QPushButton#cancel { background: rgba(255,70,70,0.15);
                                 border: 1px solid #FF4646; color: #FF6B6B; font-size: 16px; }
            QPushButton#cancel:pressed { background: rgba(255,70,70,0.35); }
        """)

        # 타이틀
        lbl = QLabel("타이머 순서 변경")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #468CFF; font-size: 18px; font-weight: bold;")
        self.layout.addWidget(lbl)

        # 본문: 리스트 + ▲▼ 버튼
        body = QHBoxLayout()
        body.setSpacing(10)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        # 터치 스크롤 — QScroller + 이벤트 필터 이중 적용 (QListWidget 선택 이벤트 충돌 회피)
        apply_touch_scroll(self.list_widget)
        self._drag_filter = DragScrollFilter(self.list_widget)
        self._drag_filter.attach(self.list_widget)
        for name in timer_names:
            self.list_widget.addItem(name)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        self.list_widget.currentRowChanged.connect(self._update_buttons)
        body.addWidget(self.list_widget, 1)

        # ▲▼ 버튼 영역
        btn_col = QVBoxLayout()
        btn_col.setSpacing(12)
        btn_col.setAlignment(Qt.AlignVCenter)

        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedSize(60, 70)
        self.btn_up.clicked.connect(self._move_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedSize(60, 70)
        self.btn_down.clicked.connect(self._move_down)

        btn_col.addWidget(self.btn_up)
        btn_col.addWidget(self.btn_down)
        body.addLayout(btn_col)

        self.layout.addLayout(body, 1)

        # 하단 확인/취소
        foot = QHBoxLayout()
        foot.setSpacing(10)
        btn_cancel = QPushButton("취소")
        btn_cancel.setObjectName("cancel")
        btn_cancel.setFixedHeight(48)
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("완료")
        btn_ok.setObjectName("ok")
        btn_ok.setFixedHeight(48)
        btn_ok.clicked.connect(self.accept)

        foot.addWidget(btn_cancel)
        foot.addWidget(btn_ok)
        self.layout.addLayout(foot)

        self._update_buttons()

    def _update_buttons(self):
        row = self.list_widget.currentRow()
        total = self.list_widget.count()
        self.btn_up.setEnabled(row > 0)
        self.btn_down.setEnabled(0 <= row < total - 1)

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row <= 0:
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row - 1, item)
        self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= self.list_widget.count() - 1:
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row + 1, item)
        self.list_widget.setCurrentRow(row + 1)

    def get_ordered_names(self):
        return [self.list_widget.item(i).text()
                for i in range(self.list_widget.count())]

    def get_visible_mode(self):
        return self._visible_mode