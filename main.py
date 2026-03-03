import sys
import os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.plc_client import PLCClient  # [NEW] PLC 클라이언트 임포트

def main():
    # 1. 앱 생성
    app = QApplication(sys.argv)
    
    # 2. 기본 스타일 'Fusion'으로 설정
    app.setStyle("Fusion") 

    # 3. [전역 스타일시트 로드] (기존 코드 유지)
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    qss_path = os.path.join(base_path, "style.qss")

    if os.path.exists(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read()) 
            print(f"✅ 스타일 로드 성공: {qss_path}")
        except Exception as e:
            print(f"❌ 스타일 로드 에러: {e}")
    else:
        print(f"⚠️ 경고: 스타일 파일을 찾을 수 없습니다: {qss_path}")

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