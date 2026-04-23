"""
이력 오버레이 팝업. TopBar 알람 라벨 클릭 시 표시.
상단 탭으로 [알람 이력 / 조작 이력] 을 전환.
- 알람 이력: utils.alarm_history (30일 보존)
- 조작 이력: utils.op_history    (7일 보존)
"""
from PySide6.QtCore import Qt, QEventLoop
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QScroller, QScrollerProperties, QScrollBar
)

from utils.alarm_history import load_history as load_alarm_history
from utils.op_history import load_history as load_op_history

_ALARM_LABEL = {
    "AXIS": "축 알람",
    "ESTOP": "비상정지",
    "STEP": "스텝 알람",
    "USER": "사용자 알람",
    "COMM": "통신 오류",
}

_OP_LABEL = {
    "RUN":         "운전",
    "VALVE":       "밸브",
    "POS":         "위치",
    "SPEED":       "속도",
    "TIMER":       "타이머",
    "MODE":        "모드",
    "RECIPE":      "레시피",
    "PARAM":       "파라미터",
    "ALARM_RESET": "알람리셋",
    "JOG":         "JOG",
}

# 초기 렌더 및 "더 보기" 1회당 로드 크기
PAGE_SIZE = 100

_SCROLLBAR_STYLE = """
    QScrollBar:vertical { border: none; background: rgba(0,0,0,0.1); width: 8px; margin: 0; border-radius: 4px; }
    QScrollBar::handle:vertical { background: rgba(255,255,255,0.3); min-height: 30px; border-radius: 4px; }
    QScrollBar::handle:vertical:pressed { background: rgba(70,140,255,0.6); }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
"""


class AlarmHistoryOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        if parent:
            main_window = parent.window()
            self.setParent(main_window)
            self.resize(main_window.size())
        self.setStyleSheet("background-color: rgba(0,0,0,180);")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self._event_loop = None
        self._current_tab = "alarm"   # "alarm" | "op"
        self._all_entries = []         # 최신순 정렬된 현재 탭 전체
        self._shown_count = 0          # 화면에 이미 렌더된 행 수

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        container = QFrame()
        container.setObjectName("root")
        container.setFixedSize(880, 600)
        container.setStyleSheet("""
            QFrame#root { background-color: #1A1F2B; border: 2px solid #468CFF; border-radius: 14px; }
            QLabel#title { color: #468CFF; font-size: 24px; font-weight: 900; background: transparent; border: none; }
            QPushButton#close { background: #582F2F; border: 1px solid #C0392B; border-radius: 8px;
                                 color: white; font-size: 18px; font-weight: bold; height: 50px; }
            QPushButton#close:pressed { background: #C0392B; }
            QPushButton#tab { background: rgba(255,255,255,0.05); border: 1px solid #555; border-radius: 6px;
                               color: #AAA; font-size: 16px; font-weight: bold; height: 42px; }
            QPushButton#tab:checked { background: rgba(70,140,255,0.25); border: 2px solid #468CFF; color: white; }

            /* ── 이력 행: objectName/property 기반 선택자로 per-widget setStyleSheet 제거 ── */
            QWidget#histRow { background: rgba(255,255,255,0.04); border-radius: 5px; }
            QWidget#histRow:hover { background: rgba(255,255,255,0.08); }
            QWidget#histRow QLabel { background: transparent; border: none; color: #DDD; font-size: 14px; }
            QLabel[role="cat_alarm"] { color: #FF9999; font-weight: bold; }
            QLabel[role="cat_op"]    { color: #7FD3FF; font-weight: bold; }
        """)

        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(20, 18, 20, 18)
        vbox.setSpacing(10)

        # 타이틀
        self.lbl_title = QLabel("이력")
        self.lbl_title.setObjectName("title")
        vbox.addWidget(self.lbl_title)

        # 탭
        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)
        self.btn_tab_alarm = QPushButton("알람 이력 (30일)")
        self.btn_tab_alarm.setObjectName("tab")
        self.btn_tab_alarm.setCheckable(True)
        self.btn_tab_alarm.setChecked(True)
        self.btn_tab_alarm.setFixedWidth(180)
        self.btn_tab_alarm.clicked.connect(lambda: self._switch_tab("alarm"))

        self.btn_tab_op = QPushButton("조작 이력 (7일)")
        self.btn_tab_op.setObjectName("tab")
        self.btn_tab_op.setCheckable(True)
        self.btn_tab_op.setFixedWidth(180)
        self.btn_tab_op.clicked.connect(lambda: self._switch_tab("op"))

        tab_row.addWidget(self.btn_tab_alarm)
        tab_row.addWidget(self.btn_tab_op)
        tab_row.addStretch(1)
        vbox.addLayout(tab_row)

        # 컬럼 헤더
        self._hdr_bar = QFrame()
        self._hdr_bar.setObjectName("hdrBar")
        self._hdr_bar.setFixedHeight(34)
        self._hdr_bar.setStyleSheet(
            "QFrame#hdrBar { background: rgba(255,255,255,0.06); border-radius: 4px; border: none; }"
        )
        self._hdr_lay = QHBoxLayout(self._hdr_bar)
        self._hdr_lay.setContentsMargins(12, 0, 12, 0)
        self._hdr_lay.setSpacing(8)
        vbox.addWidget(self._hdr_bar)

        # 리스트 스크롤 (멤버로 보관 → _refresh 에서 setWidget 으로 통째 교체)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        sb = QScrollBar(Qt.Vertical); sb.setStyleSheet(_SCROLLBAR_STYLE)
        self._scroll.setVerticalScrollBar(sb)
        QScroller.grabGesture(self._scroll.viewport(), QScroller.TouchGesture)
        QScroller.grabGesture(self._scroll.viewport(), QScroller.LeftMouseButtonGesture)

        self._list_widget = self._build_list_widget()
        self._scroll.setWidget(self._list_widget)
        vbox.addWidget(self._scroll, 1)

        btn_close = QPushButton("닫기")
        btn_close.setObjectName("close")
        btn_close.clicked.connect(self._quit)
        vbox.addWidget(btn_close)

        outer.addWidget(container)
        self._refresh()

    # ------------------------------------------------------------
    def _switch_tab(self, tab):
        if self._current_tab == tab:
            # 이미 선택된 탭은 체크 상태 유지
            if tab == "alarm":
                self.btn_tab_alarm.setChecked(True)
            else:
                self.btn_tab_op.setChecked(True)
            return
        self._current_tab = tab
        self.btn_tab_alarm.setChecked(tab == "alarm")
        self.btn_tab_op.setChecked(tab == "op")
        self._refresh()

    def _build_list_widget(self):
        """빈 리스트 컨테이너 + layout 하나를 새로 만들어 반환 (부모는 아직 없음)."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)
        lay.addStretch(1)
        self._list_layout = lay
        return w

    def _swap_headers(self, headers):
        """헤더 바를 통째로 새 QFrame 으로 교체 — 중간 상태 노출 없음."""
        new_bar = QFrame()
        new_bar.setObjectName("hdrBar")
        new_bar.setFixedHeight(34)
        new_bar.setStyleSheet(
            "QFrame#hdrBar { background: rgba(255,255,255,0.06); border-radius: 4px; border: none; }"
        )
        lay = QHBoxLayout(new_bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)
        for text, stretch in headers:
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color: #AAA; font-size: 14px; font-weight: bold; background: transparent; border: none;"
            )
            lay.addWidget(lbl, stretch)

        # container vbox 에서 기존 _hdr_bar 의 위치에 교체
        container_vbox = self._hdr_bar.parentWidget().layout()
        idx = container_vbox.indexOf(self._hdr_bar)
        container_vbox.removeWidget(self._hdr_bar)
        self._hdr_bar.setParent(None)
        self._hdr_bar.deleteLater()
        container_vbox.insertWidget(idx, new_bar)
        self._hdr_bar = new_bar
        self._hdr_lay = lay

    def _make_row(self):
        """행 컨테이너 1개 생성 — 스타일은 container 의 QSS 가 objectName=histRow 로 적용"""
        row = QWidget()
        row.setObjectName("histRow")
        row.setAttribute(Qt.WA_StyledBackground, True)
        row.setFixedHeight(42)
        return row

    def _build_alarm_row(self, e):
        row = self._make_row()
        h = QHBoxLayout(row); h.setContentsMargins(12, 0, 12, 0); h.setSpacing(8)
        lbl_ts = QLabel(e.get("ts", "")); lbl_ts.setAlignment(Qt.AlignCenter)
        cat_label = _ALARM_LABEL.get(e.get("category", ""), e.get("category", ""))
        lbl_cat = QLabel(cat_label); lbl_cat.setAlignment(Qt.AlignCenter)
        lbl_cat.setProperty("role", "cat_alarm")
        code = e.get("code", 0)
        lbl_code = QLabel(str(code) if code else "-"); lbl_code.setAlignment(Qt.AlignCenter)
        lbl_msg = QLabel(e.get("message", "")); lbl_msg.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        h.addWidget(lbl_ts, 3); h.addWidget(lbl_cat, 2); h.addWidget(lbl_code, 1); h.addWidget(lbl_msg, 6)
        return row

    def _build_op_row(self, e):
        row = self._make_row()
        h = QHBoxLayout(row); h.setContentsMargins(12, 0, 12, 0); h.setSpacing(8)
        lbl_ts = QLabel(e.get("ts", "")); lbl_ts.setAlignment(Qt.AlignCenter)
        cat_label = _OP_LABEL.get(e.get("category", ""), e.get("category", ""))
        lbl_cat = QLabel(cat_label); lbl_cat.setAlignment(Qt.AlignCenter)
        lbl_cat.setProperty("role", "cat_op")
        lbl_msg = QLabel(e.get("message", "")); lbl_msg.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        h.addWidget(lbl_ts, 3); h.addWidget(lbl_cat, 2); h.addWidget(lbl_msg, 8)
        return row

    def _build_more_button(self, remaining):
        btn = QPushButton(f"⤓  더 보기 ({remaining}건 남음)")
        btn.setObjectName("btnMore")
        btn.setFixedHeight(46)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton#btnMore { background: rgba(70,140,255,0.15); border: 1px solid #468CFF; "
            "border-radius: 6px; color: #9BC4FF; font-size: 15px; font-weight: bold; margin-top: 4px; } "
            "QPushButton#btnMore:pressed { background: rgba(70,140,255,0.3); }"
        )
        btn.clicked.connect(self._on_load_more)
        return btn

    def _build_empty_label(self, text):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #888; font-size: 16px; padding: 40px 0; background: transparent; border: none;")
        return lbl

    def _trim_trailing(self, layout):
        """스트레치 + 기존 '더 보기' 버튼을 모두 제거. 이후 새로 추가할 준비."""
        while layout.count() > 0:
            item = layout.itemAt(layout.count() - 1)
            if item is None:
                break
            if item.spacerItem() is not None:
                layout.takeAt(layout.count() - 1)
                continue
            w = item.widget()
            if w is not None and w.objectName() == "btnMore":
                layout.takeAt(layout.count() - 1)
                w.setParent(None)
                w.deleteLater()
                continue
            break

    def _append_page(self, layout):
        """현재 탭의 다음 PAGE_SIZE 건을 layout 에 추가. 남은 게 있으면 '더 보기' 버튼 재배치."""
        self._trim_trailing(layout)

        total = len(self._all_entries)
        if total == 0 and self._shown_count == 0:
            empty_text = "기록된 알람이 없습니다." if self._current_tab == "alarm" else "기록된 조작이 없습니다."
            layout.addWidget(self._build_empty_label(empty_text))
            layout.addStretch(1)
            return

        build_fn = self._build_alarm_row if self._current_tab == "alarm" else self._build_op_row
        end = min(self._shown_count + PAGE_SIZE, total)
        for i in range(self._shown_count, end):
            layout.addWidget(build_fn(self._all_entries[i]))
        self._shown_count = end

        # 남은 게 있으면 더 보기 버튼
        if self._shown_count < total:
            layout.addWidget(self._build_more_button(total - self._shown_count))

        layout.addStretch(1)

    def _on_load_more(self):
        """현재 리스트 위젯 layout 에 다음 PAGE_SIZE 건 이어서 추가."""
        sb = self._scroll.verticalScrollBar()
        prev_pos = sb.value()
        prev_max = sb.maximum()

        self._append_page(self._list_widget.layout())

        # 스크롤 위치 유지 — 기존에 끝까지 내려와서 '더 보기' 눌렀으면
        # 새 항목들이 아래로 추가되었으니 이전 위치 근처에 머무르게.
        # Qt 가 레이아웃 재계산할 때까지 약간 기다린 뒤 조정 필요 → 여기선 단순히
        # 새 최대값으로 스크롤해서 사용자가 이어서 볼 수 있도록 함.
        new_max = sb.maximum()
        if prev_pos >= prev_max - 10:
            # 이전에 바닥이었으면 새 내용 첫 부분이 보이게 살짝 위로
            sb.setValue(prev_max)

    # ------------------------------------------------------------
    def _refresh(self):
        """
        탭 전환 시: 전체 엔트리를 로드 · 정렬 후 첫 페이지만 오프스크린에서 렌더.
        원자적 setWidget 으로 교체 → 중간 상태 깨짐 방지.
        """
        # 1. 데이터 로드 및 최신순 정렬
        if self._current_tab == "alarm":
            self._all_entries = list(reversed(load_alarm_history()))
            new_headers = [("일시", 3), ("종류", 2), ("코드", 1), ("메시지", 6)]
            title_prefix = "알람 발생 이력 (최근 30일)"
        else:
            self._all_entries = list(reversed(load_op_history()))
            new_headers = [("일시", 3), ("분류", 2), ("내용", 8)]
            title_prefix = "조작 이력 (최근 7일)"
        self._shown_count = 0

        # 2. 새 리스트 컨테이너 off-screen 구성 + 첫 페이지 채움
        new_list = self._build_list_widget()
        self._append_page(new_list.layout())

        # 3. 타이틀 (전체 건수 표시)
        total = len(self._all_entries)
        self.lbl_title.setText(f"{title_prefix}   ({total}건)")

        # 4. 헤더/리스트 원자 교체
        self._swap_headers(new_headers)
        self._scroll.setWidget(new_list)
        self._list_widget = new_list
        self._scroll.verticalScrollBar().setValue(0)

    def _quit(self):
        if self._event_loop:
            self._event_loop.quit()
        self.close()
        self.deleteLater()

    def exec(self):
        self.show()
        self.raise_()
        self._event_loop = QEventLoop()
        self._event_loop.exec()
