from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QScrollArea,
    QFrame, QSizePolicy, QScroller, QScrollerProperties
)
from PySide6.QtGui import QPainter, QColor, QPen

# 매니저 임포트
try:
    from utils.io_manager import IOManager
except ImportError:
    IOManager = None

try:
    from utils.languages import LanguageManager
except ImportError:
    LanguageManager = None


class IOLamp(QFrame):
    """ 라운드 사각형 램프 """
    def __init__(self, is_input: bool):
        super().__init__()
        self.setFixedSize(34, 22)
        self.setFrameShape(QFrame.NoFrame)
        
        self.is_input = is_input
        self._is_on = False

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("IOLampIn" if is_input else "IOLampOut")
        self.setProperty("on", "false")

    def set_on(self, on: bool):
        self._is_on = on
        self.setProperty("on", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update() 
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        
        if self._is_on:
            if self.is_input:
                bg_color = QColor(70, 140, 255, 245)
                border_color = QColor(140, 200, 255, 220)
            else:
                bg_color = QColor(255, 105, 35, 245)
                border_color = QColor(255, 170, 120, 220)
        else:
            bg_color = QColor(0, 0, 0, 230)
            border_color = QColor(255, 255, 255, 35)
        
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(rect, 10, 10)
        painter.end()


class IOList(QWidget):
    """ 단일 리스트(입력 또는 출력) """
    def __init__(self, title: str, is_input: bool, addrs: list[str]):
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self.hdr = QLabel(title)
        self.hdr.setProperty("class", "IOHeader")
        root.addWidget(self.hdr, 0, Qt.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        root.addWidget(scroll, 1)

        # [수정] 터치 제스처 + 마우스 드래그 제스처 모두 활성화
        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture) # 마우스 드래그 추가
        
        scroller = QScroller.scroller(scroll.viewport())
        props = scroller.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.MousePressEventDelay, 0)
        scroller.setScrollerProperties(props)

        cont = QWidget()
        cont.setStyleSheet("background: transparent;")
        scroll.setWidget(cont)

        v = QVBoxLayout(cont)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        self.lamps: list[IOLamp] = []
        self.labels: list[QLabel] = []

        for addr in addrs:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(10)

            lamp = IOLamp(is_input=is_input)

            lbl = QLabel(addr)
            lbl.setProperty("class", "IORowLabel")
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            h.addWidget(lamp, 0, Qt.AlignLeft | Qt.AlignVCenter)
            h.addWidget(lbl, 1, Qt.AlignLeft | Qt.AlignVCenter)

            self.lamps.append(lamp)
            self.labels.append(lbl)

            v.addWidget(row)

        v.addStretch(1)

    def set_title(self, text: str):
        self.hdr.setText(text)

    def set_bit(self, index: int, on: bool):
        if 0 <= index < len(self.lamps):
            self.lamps[index].set_on(on)

    def set_label(self, index: int, text: str):
        if 0 <= index < len(self.labels):
            self.labels[index].setText(text)
    
    def update_from_words(self, words: list):
        """
        ★ 새로 추가: PLC에서 읽은 Word 데이터로 비트 업데이트
        words: Word 단위 리스트 (예: [0x0012, 0x0034])
        각 Word의 비트를 lamp로 표시 (변경된 비트만 업데이트)
        """
        for word_idx, word_val in enumerate(words):
            for bit_idx in range(16):  # 각 Word는 16비트
                lamp_idx = word_idx * 16 + bit_idx
                if lamp_idx < len(self.lamps):
                    is_on = bool(word_val & (1 << bit_idx))
                    if self.lamps[lamp_idx]._is_on != is_on:
                        self.lamps[lamp_idx].set_on(is_on)


class IOPanel(QWidget):
    """ 입력/출력을 2칸으로 나눈 패널 """
    def __init__(self):
        super().__init__()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        x_addrs = [f"X{v:02X}" for v in range(0x00, 0x20)]
        y_addrs = [f"Y{v:02X}" for v in range(0x00, 0x20)]

        t_in = "입력"
        t_out = "출력"
        if LanguageManager:
            t_in = LanguageManager.instance().get_text("lbl_io_input")
            t_out = LanguageManager.instance().get_text("lbl_io_output")

        self.inputs = IOList(t_in, is_input=True, addrs=x_addrs)
        self.outputs = IOList(t_out, is_input=False, addrs=y_addrs)

        self.inputs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.outputs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        root.addWidget(self.inputs, 1)
        root.addWidget(self.outputs, 1)

        if IOManager:
            IOManager.instance().sig_names_changed.connect(self.update_names)
            self.update_names()
            
        if LanguageManager:
            LanguageManager.instance().sig_lang_changed.connect(self.update_language)

    def update_language(self, lang_code=None):
        if not LanguageManager: return
        lm = LanguageManager.instance()
        self.inputs.set_title(lm.get_text("lbl_io_input"))
        self.outputs.set_title(lm.get_text("lbl_io_output"))

    def update_names(self):
        if not IOManager: return
        mgr = IOManager.instance()
        
        for i in range(32):
            name = mgr.get_input_name(i)
            if name: 
                self.inputs.set_label(i, name)
            
        for i in range(32):
            name = mgr.get_output_name(i)
            if name:
                self.outputs.set_label(i, name)

    def set_inputs_from_mask(self, mask: int):
        for i in range(32):
            self.inputs.set_bit(i, bool(mask & (1 << i)))

    def set_outputs_from_mask(self, mask: int):
        for i in range(32):
            self.outputs.set_bit(i, bool(mask & (1 << i)))
