from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

class GlassCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        # 사용자님의 원본 스타일 속성 유지
        self.setProperty("class", "GlassCard")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        # [수정] 외부(PageManual 등)에서 접근하는 변수명인 self.title_label로 변경
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "PageTitle")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        lay.addWidget(self.title_label)

        # 본문 레이아웃
        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        lay.addLayout(self.body, 1)  # stretch 1 추가하여 body가 남은 공간 차지