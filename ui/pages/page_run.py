from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class PageRun(QFrame):
    def __init__(self):
        super().__init__()
        self.setProperty("class", "GlassCard")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        title = QLabel("동작")
        title.setProperty("class", "PageTitle")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        hint = QLabel("START/STOP, 원점복귀, 스텝 실행, JOG 등")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: rgba(233, 238, 243, 180);")

        lay.addWidget(title)
        lay.addWidget(hint)
        lay.addStretch(1)
