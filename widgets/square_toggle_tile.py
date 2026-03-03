from PySide6.QtWidgets import QPushButton


class SquareToggleTile(QPushButton):
    """
    레이아웃에서 가로폭이 정해지면, 높이를 가로와 같게 맞춰 정사각형처럼 보이게 하는 토글 버튼
    """
    def __init__(self, text: str = ""):
        super().__init__(text)
        self.setCheckable(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 가로폭에 맞춰 높이를 맞춤(너무 작아지지 않게는 page에서 minimumSize로 제한)
        side = self.width()
        if self.height() != side:
            self.setMinimumHeight(side)
            self.setMaximumHeight(side)
