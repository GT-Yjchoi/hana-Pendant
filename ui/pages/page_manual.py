from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QHBoxLayout, QVBoxLayout,
    QWidget, QSizePolicy,
    QScrollArea, QFrame, QScrollBar, QScroller, QScrollerProperties
)

from widgets.glass_card import GlassCard
from widgets.io_panel import IOPanel
from utils.languages import LanguageManager
from ui.widgets.axis_position_panel import AxisPositionPanel
from ui.widgets.valve_tile import ValvePanel

# [스타일] IO 패널용 스크롤바
SCROLLBAR_STYLE = """
    QScrollBar:vertical { border: none; background: rgba(0, 0, 0, 0.1); width: 8px; margin: 0px; border-radius: 4px; }
    QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.3); min-height: 30px; border-radius: 4px; }
    QScrollBar::handle:vertical:pressed { background: rgba(70, 140, 255, 0.6); }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
"""

class PageManual(GlassCard):
    def __init__(self, plc_client=None):
        super().__init__("") 

        if hasattr(self, 'title_label'):
            self.title_label.hide()
            if self.title_label.parentWidget() and self.title_label.parentWidget() != self:
                self.title_label.parentWidget().hide()

        if self.layout():
            self.layout().setContentsMargins(10, 5, 10, 10)

        self.plc_client = plc_client

        main_row = QHBoxLayout()
        main_row.setSpacing(20)

        # ----------------------------------------------------------
        # [LEFT] 위치 표시 (비율 2)
        # ----------------------------------------------------------
        left = QVBoxLayout()
        left.setSpacing(15)

        self.pos_panel = AxisPositionPanel(plc_client=plc_client)
        if hasattr(self.pos_panel, 'body'):
             self.pos_panel.body.setAlignment(Qt.AlignTop)
        left.addWidget(self.pos_panel, 1)

        # ----------------------------------------------------------
        # [MIDDLE] IO Panel (외부에서 스크롤 적용) (비율 5)
        # ----------------------------------------------------------
        self.io_panel = IOPanel()
        # 에러 수정된 함수 호출
        io_scroll = self._create_smooth_scroll_area(self.io_panel)
        
        # ----------------------------------------------------------
        # [RIGHT] 밸브 조작 패널 (자체 스크롤 내장) (비율 3)
        # ----------------------------------------------------------
        # 이제 ValvePanel이 스스로 QScrollArea입니다.
        self.valve_panel = ValvePanel(plc_client)

        # ★ 레이아웃 배치
        main_row.addLayout(left, 2)
        main_row.addWidget(io_scroll, 5)     # IO (여기서 스크롤 감쌈)
        main_row.addWidget(self.valve_panel, 3) # Valve (자체 스크롤)

        self.body.addLayout(main_row)
        
        if self.plc_client:
            self.plc_client.sig_monitor_data.connect(self._on_monitor_data)

        self.update_language()

    # ★ [수정] 에러 라인 삭제 및 튜닝
    def _create_smooth_scroll_area(self, widget):
        scroll = QScrollArea()
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        # [삭제] AttributeError 유발 코드 제거
        # scroll.setVerticalScrollMode(...)  <-- 이거 삭제함!
        
        # 터치 제스처
        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)
        
        scroller = QScroller.scroller(scroll.viewport())
        props = scroller.scrollerProperties()
        
        # [튜닝] IO 패널용 스크롤 감도 설정
        props.setScrollMetric(QScrollerProperties.MousePressEventDelay, 0.05)
        props.setScrollMetric(QScrollerProperties.DragStartDistance, 0.005)
        props.setScrollMetric(QScrollerProperties.DecelerationFactor, 0.9) # 부드럽게 멈춤
        
        scroller.setScrollerProperties(props)
        
        scrollbar = QScrollBar(Qt.Vertical)
        scrollbar.setStyleSheet(SCROLLBAR_STYLE)
        scroll.setVerticalScrollBar(scrollbar)
        
        return scroll

    def _on_monitor_data(self, data):
        if not self.isVisible(): return
        if 'inputs' in data: 
            self.io_panel.inputs.update_from_words(data['inputs'])
        if 'outputs' in data: 
            self.io_panel.outputs.update_from_words(data['outputs'])

    def update_language(self, lang_code=None):
        pass