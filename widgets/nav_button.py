from PySide6.QtWidgets import QPushButton

class NavButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setProperty("class", "NavBtn")
        self.set_active(False)

    def set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        # property 기반 QSS 갱신
        self.style().unpolish(self)
        self.style().polish(self)
