import sys
import os

# Qt ibus 한글 입력 - QApplication 생성 전에 설정해야 적용됨
os.environ.setdefault("QT_IM_MODULE", "ibus")
os.environ.setdefault("GTK_IM_MODULE", "ibus")
os.environ.setdefault("XMODIFIERS", "@im=ibus")

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.theme import APP_STYLESHEET
from utils.plc_client import PLCClient

def main():
    # 1. 앱 생성
    app = QApplication(sys.argv)
    
    # 2. 기본 스타일 'Fusion'으로 설정
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    # 4. [NEW] PLC 통신 모듈 생성
    # 프로그램 전체에서 하나만 만들어 공유합니다.
    plc_client = PLCClient()

    # 5. [MODIFIED] 윈도우 생성 시 PLC 클라이언트 전달
    # (ui/main_window.py의 __init__도 이에 맞춰 수정되어 있어야 합니다)
    window = MainWindow(plc_client)
    window.show()
    
    # 6. [NEW] 프로그램 종료 시 연결 해제
    app.aboutToQuit.connect(plc_client.disconnect_plc)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()