from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QLineEdit, QComboBox, QListView, QAbstractItemView, QScroller, QScrollerProperties
)

# [터치 지원 입력창] 클릭 시 시그널 발생 (키보드 호출용)
class ClickableLineEdit(QLineEdit):
    clicked = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def mousePressEvent(self, event):
        self.clicked.emit()
        # 필요한 경우 super().mousePressEvent(event) 호출

# [터치 지원 콤보박스] 부드러운 스크롤 적용
class TouchComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setView(QListView())
        self.view().setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        QScroller.grabGesture(self.view().viewport(), QScroller.TouchGesture)
        QScroller.grabGesture(self.view().viewport(), QScroller.LeftMouseButtonGesture)
        
        scroller = QScroller.scroller(self.view().viewport())
        props = scroller.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.DragStartDistance, 0.001)
        scroller.setScrollerProperties(props)

        # 공통 스타일 적용
        self.setStyleSheet("""
            QComboBox {
                background: rgba(255,255,255,10);
                border: 2px solid rgba(70,140,255,90);
                border-radius: 6px;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding-left: 10px;
            }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox QAbstractItemView {
                background: #141E28;
                color: white;
                selection-background-color: #468CFF;
                font-size: 16px;
                padding: 5px;
                outline: none;
            }
        """)
        self._press_inside = False

    def mousePressEvent(self, event):
        # 팝업을 "뗀 순간"에 열기 위해 press 는 흡수만 한다.
        # (press 에서 열면 손가락이 아직 화면에 있어서 팝업의 해당 항목이 hover 로 잡혀 버림)
        if event.button() == Qt.LeftButton:
            self._press_inside = self.rect().contains(event.position().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._press_inside:
            self._press_inside = False
            if self.rect().contains(event.position().toPoint()):
                self.showPopup()
            event.accept()
            return
        self._press_inside = False
        super().mouseReleaseEvent(event)