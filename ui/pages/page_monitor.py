from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class PageMonitor(QFrame):
    def __init__(self):
        super().__init__()
        self.setProperty("class", "GlassCard")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        title = QLabel("모니터")
        title.setProperty("class", "PageTitle")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        hint = QLabel("X/Y/Z 현재값, I/O 상태, 로그 표시")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: rgba(233, 238, 243, 180);")

        lay.addWidget(title)
        lay.addWidget(hint)
        lay.addStretch(1)
