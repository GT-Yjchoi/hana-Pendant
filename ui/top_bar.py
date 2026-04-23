import os, sys
from PySide6.QtCore import Qt, QTimer, QTime, QDate, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget
from PySide6.QtGui import QPixmap

try:
    from utils.languages import LanguageManager
except ImportError:
    LanguageManager = None

def _resource_path(rel):
    """PyInstaller 빌드와 일반 실행 모두에서 리소스 절대경로 반환"""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, rel)

class TopBar(QFrame):
    sig_jog_clicked = Signal()
    sig_alarm_clicked = Signal()

    def __init__(self, plc_client=None):
        super().__init__()
        self.plc_client = plc_client
        self.op_status = 0
        
        # 전체 스타일 설정
        self.setFixedHeight(70) 
        self.setStyleSheet("""
            TopBar {
                background-color: #111827; 
                border-bottom: 2px solid #374151;
            }
            QLabel {
                font-family: 'Malgun Gothic', sans-serif;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(25) 

        # -----------------------------------------------------------
        # [LEFT] 로고 & 상태 정보
        # -----------------------------------------------------------
        
        # 1. 회사 로고 (이미지 + AUTOMATION 텍스트)
        import os
        logo_row = QHBoxLayout()
        logo_row.setSpacing(6)
        logo_row.setContentsMargins(0, 0, 0, 0)

        self.lbl_logo_img = QLabel()
        logo_path = _resource_path("gtlogo.png")
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            self.lbl_logo_img.setPixmap(pixmap.scaledToHeight(28, Qt.SmoothTransformation))
        self.lbl_logo_img.setStyleSheet("background: transparent;")
        logo_row.addWidget(self.lbl_logo_img)

        self.lbl_logo = QLabel("AUTOMATION")
        self.lbl_logo.setStyleSheet("color: white; font-size: 24px; font-weight: 900; letter-spacing: 1px;")
        logo_row.addWidget(self.lbl_logo)

        logo_widget = QWidget()
        logo_widget.setLayout(logo_row)
        logo_widget.setStyleSheet("background: transparent;")
        layout.addWidget(logo_widget)
        
        self._add_separator(layout)

        # 2. 통신 상태
        self.lbl_comm = QLabel("통신: --")
        self.lbl_comm.setStyleSheet("color: #95A5A6; font-size: 19px; font-weight: bold;")
        layout.addWidget(self.lbl_comm)

        # 3. 운전 모드
        self.lbl_mode = QLabel("모드: 정지")
        self.lbl_mode.setStyleSheet("color: #95A5A6; font-size: 20px; font-weight: bold;")
        layout.addWidget(self.lbl_mode)

        # 4. 알람 상태 - 클릭 시 오버레이 재표시
        self.lbl_alarm = QLabel("알람: 없음")
        self.lbl_alarm.setStyleSheet("color: #95A5A6; font-size: 19px; font-weight: bold;")
        self.lbl_alarm.setCursor(Qt.PointingHandCursor)
        self.lbl_alarm.mousePressEvent = lambda e: self.sig_alarm_clicked.emit()
        layout.addWidget(self.lbl_alarm)

        self._add_separator(layout)

        # 5. 데이터 (레시피)
        self.lbl_mold = QLabel("데이터: 기본")
        self.lbl_mold.setStyleSheet("color: #FFFFFF; font-size: 22px; font-weight: bold;") 
        layout.addWidget(self.lbl_mold)

        # -----------------------------------------------------------
        # [SPACER]
        # -----------------------------------------------------------
        layout.addStretch(1)

        # -----------------------------------------------------------
        # [RIGHT] 시계 & 버튼
        # -----------------------------------------------------------
        
        # 6. 날짜/시간
        self.lbl_time = QLabel()
        self.lbl_time.setStyleSheet("color: #E5E7EB; font-size: 20px; font-weight: 600;")
        self.lbl_time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.lbl_time)

        # 7. JOG 버튼
        self.btn_jog = QPushButton("JOG")
        self.btn_jog.setFixedSize(80, 40)
        self.btn_jog.setCursor(Qt.PointingHandCursor)
        self.btn_jog.setStyleSheet("""
            QPushButton {
                background-color: #005f73;
                color: #00E5FF;
                border: 1px solid #00E5FF;
                border-radius: 6px;
                font-weight: bold;
                font-size: 18px;
            }
            QPushButton:hover { background-color: #0a9396; color: white; }
            QPushButton:pressed { background-color: #94d2bd; color: black; }
        """)
        self.btn_jog.clicked.connect(self.sig_jog_clicked.emit)
        
        layout.addWidget(self.btn_jog)

        # 타이머
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)
        self._update_time()

        # PLC 연결
        if self.plc_client:
            self.plc_client.sig_connected.connect(self.set_comm_status)
            self.plc_client.sig_monitor_data.connect(self._on_monitor_data)
            self.set_comm_status(self.plc_client.is_connected)

    def _add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #4B5563; max-height: 20px;")
        layout.addWidget(line)

    def _update_time(self):
        now = QDate.currentDate().toString("yyyy/MM/dd") + " " + QTime.currentTime().toString("HH:mm")
        self.lbl_time.setText(now)

    def set_comm_status(self, connected):
        if connected:
            self.lbl_comm.setText("통신: 정상")
            self.lbl_comm.setStyleSheet("color: #00E5FF; font-size: 19px; font-weight: bold;")
        else:
            self.lbl_comm.setText("통신: 오류")
            self.lbl_comm.setStyleSheet("color: #FF4646; font-size: 19px; font-weight: bold;")

    # 레시피 이름 표시 (과거 함수명 유지, 호출부 호환)
    def set_mold_data(self, name):
        lm = LanguageManager.instance() if LanguageManager else None
        prefix = lm.get_text("lbl_mold") if lm else "데이터: "
        self.lbl_mold.setText(f"{prefix}{name}")

    def _on_monitor_data(self, data):
        """PLC 데이터 수신 시 UI 갱신"""
        # 1. 운전 모드 (DT129)
        self.op_status = data.get('op_status', 0)
        mode = self.op_status
        if mode == 1:
            self.lbl_mode.setText("모드: 자동운전")
            self.lbl_mode.setStyleSheet("color: #2ECC71; font-size: 20px; font-weight: 900;")
        elif mode == 2:
            self.lbl_mode.setText("모드: 확인운전")
            self.lbl_mode.setStyleSheet("color: #F1C40F; font-size: 20px; font-weight: 900;")
        else:
            self.lbl_mode.setText("모드: 정지")
            self.lbl_mode.setStyleSheet("color: #95A5A6; font-size: 20px; font-weight: bold;")

        # 2. 알람 상태 (DT142 기반)
        axis_alarms = data.get('axis_alarms', [])
        if axis_alarms:
            if 9 in axis_alarms:
                self.lbl_alarm.setText("[!] 비상정지")
            else:
                self.lbl_alarm.setText(f"[!] 알람 ({len(axis_alarms)}축)")
            self.lbl_alarm.setStyleSheet(
                "color: #FF4646; font-size: 19px; font-weight: 900; text-decoration: underline;"
            )
        else:
            self.lbl_alarm.setText("알람: 없음")
            self.lbl_alarm.setStyleSheet("color: #95A5A6; font-size: 19px; font-weight: bold;")