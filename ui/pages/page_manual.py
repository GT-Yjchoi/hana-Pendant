from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QHBoxLayout, QVBoxLayout,
    QWidget, QPushButton, QButtonGroup, QSizePolicy,
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

        arm_layout = QVBoxLayout()
        arm_layout.setSpacing(8)
        
        self.btn_product_arm = QPushButton()
        self.btn_runner_arm = QPushButton()

        for b in (self.btn_product_arm, self.btn_runner_arm):
            b.setCheckable(True)
            b.setProperty("class", "ArmSelectBtn")
            b.setMinimumHeight(60)

        arm_group = QButtonGroup(self)
        arm_group.setExclusive(True)
        arm_group.addButton(self.btn_product_arm)
        arm_group.addButton(self.btn_runner_arm)

        self.btn_product_arm.setChecked(True)

        arm_layout.addWidget(self.btn_product_arm)
        arm_layout.addWidget(self.btn_runner_arm)
        
        left.addLayout(arm_layout)

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
            self.plc_client.sig_connected.connect(self._on_plc_connected)

        self.update_language()
        # 시작 시 settings.json으로 초기 가시성 설정 (PLC 연결 전 기본값)
        self._init_runner_arm_visibility()

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

    def _init_runner_arm_visibility(self):
        """settings.json에서 축 사용 설정을 읽어 초기 가시성 결정 (PLC 연결 전 대비)"""
        try:
            import os, json
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding="utf-8") as f:
                    s = json.load(f)
                axis_uses = s.get("axis_uses", [True] * 8)
                use_y2 = axis_uses[3] if len(axis_uses) > 3 else True
                use_z2 = axis_uses[4] if len(axis_uses) > 4 else True
                is_runner_used = bool(use_y2 or use_z2)
                self.btn_runner_arm.setVisible(is_runner_used)
                if not is_runner_used and self.btn_runner_arm.isChecked():
                    self.btn_product_arm.click()
        except Exception as e:
            print(f"[PageManual] Runner arm init error: {e}")

    def _on_plc_connected(self, connected: bool):
        """PLC 연결 완료 시 가시성 재확인"""
        if connected:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(300, self._check_runner_arm_visibility)

    def showEvent(self, event):
        super().showEvent(event)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._check_runner_arm_visibility)

    def _check_runner_arm_visibility(self):
        if not self.plc_client or not self.plc_client.is_connected:
            return
        try:
            data = self.plc_client.read_words(0x09, 50000, 1)
            if data:
                use_mask = data[0]
                use_y2 = (use_mask >> 3) & 1
                use_z2 = (use_mask >> 4) & 1
                is_runner_used = bool(use_y2 or use_z2)
                
                if self.btn_runner_arm.isVisible() != is_runner_used:
                    self.btn_runner_arm.setVisible(is_runner_used)
                
                if not is_runner_used and self.btn_runner_arm.isChecked():
                    self.btn_product_arm.click()
        except Exception as e:
            print(f"Runner Arm Check Error: {e}")

    def update_language(self, lang_code=None):
        lm = LanguageManager.instance()
        self.btn_product_arm.setText(lm.get_text("btn_prod_arm"))
        self.btn_runner_arm.setText(lm.get_text("btn_runner_arm"))