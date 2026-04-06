from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QHBoxLayout, QFrame, QSizePolicy

class AxisPositionPanel(QWidget):
    """
    8축 현재 위치 표시 패널 (1280x800 해상도 최적화)
    - 축 이름(왼쪽) <-> 값(오른쪽) 간격 최대 확보 (1000단위 숫자 대응)
    - 폰트 크기 확대, 미사용 축 자동 숨김
    """
    def __init__(self, plc_client=None):
        super().__init__()

        self.plc_client = plc_client
        if self.plc_client:
            self.plc_client.sig_monitor_data.connect(self._update_realtime_values)
            self.plc_client.sig_connected.connect(self._refresh_visibility)

        grid = QGridLayout(self)
        # ★ [수정] 좌우 여백을 25px로 늘려 전체적으로 넓게 쓰도록 함
        grid.setContentsMargins(25, 15, 25, 5) 
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        title = QLabel("현재 위치")
        title.setProperty("class", "PosPanelTitle")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #DDD; margin-bottom: 10px;")
        grid.addWidget(title, 0, 0, 1, 2)

        self._value_labels = [] 
        self._row_items = []    

        axes = ["X", "Y", "Z", "Y2", "Z2", "θ", "R1", "R2"]
        
        for i, axis in enumerate(axes, start=1):
            # 1. 축 이름 (왼쪽으로 이동)
            lbl_axis = QLabel(axis)
            # ★ [수정] 왼쪽 정렬로 변경
            lbl_axis.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lbl_axis.setFixedWidth(60) 
            # 왼쪽 패딩을 주어 벽에서 살짝 띄움
            lbl_axis.setStyleSheet("color: #CCCCCC; font-size: 20px; font-weight: bold; padding-left: 5px;")

            # 2. 값 표시 영역
            box = QFrame()
            box.setProperty("class", "PosValueBox")
            box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            box.setMinimumHeight(40) 
            
            h = QHBoxLayout(box)
            # 내부 여백을 없애서 오른쪽 끝까지 공간 활용
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(10) 

            # 3. 값 (Value - 오른쪽 정렬 유지)
            val = QLabel("0.000")
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val.setMinimumWidth(120)  # "-1000.000" 9자 기준 고정폭 → 자릿수 변화 시 레이아웃 흔들림 방지
            val.setStyleSheet("color: white; font-size: 26px; font-weight: bold; font-family: 'Roboto Mono', monospace;")

            # 4. 단위 (Unit)
            unit = QLabel("mm")
            unit.setStyleSheet("color: rgba(233,238,243,160); font-weight: bold; font-size: 16px;")

            h.addWidget(val, 1) # 늘어나는 공간을 숫자가 차지
            h.addWidget(unit, 0)

            self._value_labels.append(val)
            self._row_items.append((lbl_axis, box))

            grid.addWidget(lbl_axis, i, 0)
            grid.addWidget(box, i, 1)
        
        # 값 컬럼(1번)이 남는 공간을 모두 가져가도록 설정
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(grid.rowCount(), 1)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._refresh_visibility)

    def _refresh_visibility(self):
        if not self.plc_client or not self.plc_client.is_connected:
            return

        try:
            data = self.plc_client.read_words(0x09, self.plc_client.AXIS_PARAM_ADDR, 1)
            if data:
                use_mask = data[0]
                for i, (lbl, box) in enumerate(self._row_items):
                    is_visible = bool((use_mask >> i) & 1)
                    if lbl.isVisible() != is_visible:
                        lbl.setVisible(is_visible)
                        box.setVisible(is_visible)
        except Exception as e:
            print(f"Axis Config Load Error: {e}")

    def _update_realtime_values(self, data):
        if not self.isVisible(): return
        if isinstance(data, dict):
            axis_data = data.get('axis_pos', [])
        else:
            axis_data = data
            
        for i, val in enumerate(axis_data):
            if i < len(self._value_labels):
                self._value_labels[i].setText(f"{val:.3f}")

    def set_positions(self, values):
        if len(values) < 8: return
        for i, v in enumerate(values):
            if i < len(self._value_labels):
                self._value_labels[i].setText(f"{v:,.3f}")