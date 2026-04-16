import sys
import os

# Qt ibus 한글 입력 - QApplication 생성 전에 설정해야 적용됨
os.environ.setdefault("QT_IM_MODULE", "ibus")
os.environ.setdefault("GTK_IM_MODULE", "ibus")
os.environ.setdefault("XMODIFIERS", "@im=ibus")

# 빌드 환경에서 DPI 자동 스케일링으로 인해 하단이 잘리는 것을 방지
os.environ.setdefault("QT_SCALE_FACTOR", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from ui.main_window import MainWindow
from ui.theme import APP_STYLESHEET
from utils.plc_client import PLCClient

def main():
    # 1. 앱 생성
    app = QApplication(sys.argv)
    
    # 2. 기본 스타일 'Fusion'으로 설정
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    app.setOverrideCursor(Qt.BlankCursor)

    # 4. [NEW] PLC 통신 모듈 생성
    # 프로그램 전체에서 하나만 만들어 공유합니다.
    plc_client = PLCClient()

    # 5. [MODIFIED] 윈도우 생성 시 PLC 클라이언트 전달
    # (ui/main_window.py의 __init__도 이에 맞춰 수정되어 있어야 합니다)
    window = MainWindow(plc_client)

    # 시스템 패널/태스크바가 앱 위를 가리지 않도록 항상 최상단 유지
    window.setWindowFlag(Qt.WindowStaysOnTopHint, True)

    # 빌드 환경에서 화면 geometry를 명시적으로 지정해 하단 잘림 방지
    screen = app.primaryScreen()
    window.setGeometry(screen.geometry())
    window.showFullScreen()

    # 부팅 시 데스크톱 패널이 늦게 로드될 때 하단 잘림 방지:
    # 이벤트 루프 시작 후 1초 뒤에 geometry를 재적용
    def reapply_geometry():
        s = app.primaryScreen()
        window.setGeometry(s.geometry())
        window.showFullScreen()
    QTimer.singleShot(1000, reapply_geometry)
    
    # 6. [NEW] 프로그램 종료 시 연결 해제
    app.aboutToQuit.connect(plc_client.disconnect_plc)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()