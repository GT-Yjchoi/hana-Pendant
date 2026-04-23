import json
import os
from PySide6.QtCore import Qt, Signal
from utils.paths import get_settings_path
from utils.json_utils import load_json, save_json
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect

# ============================================================
# 축 에러 코드 설명 테이블
# ============================================================
AXIS_ERROR_DESCRIPTIONS = {
    0x3001: "과부하 발생",
}

# ============================================================
# 사용자 알람 테이블 (IN 스텝 P3=1/2 에서 발동, w_UserAlarm → DT159)
# 시퀀스 작성자가 정의한 알람 번호 ↔ 메시지 매핑
# ============================================================
USER_ALARMS = {}

# ============================================================
# 스텝 알람 설명 (new_plc_fb.st i_StepAlarmID → DT160)
# 스텝 진행 실패 시 FB 엔진이 세팅하는 에러 코드
# ============================================================
STEP_ALARM_DESCRIPTIONS = {
    21: "POS 축 이동 확인 실패 — BUSY 상승을 감지하지 못함 (RTEX 트리거 거부 또는 전파 실패)",
    22: "패킹 베이스 인덱스 범위 오류 — pack_base 스텝의 point_index 가 0~59 범위를 벗어남",
    50: "서브 시퀀스 에러 (예약)",
    93: "동기 CALL 스택 오버플로 — 4레벨 초과",
    94: "CALL 사용 불가 — 이 인스턴스는 b_NoSubCall=TRUE (Monitor 등 최하위 FB)",
    95: "JMP 타겟 스텝 번호 범위 초과 (0~99)",
    96: "CALL 슬롯 번호 범위 초과 (0~39)",
    97: "실행 슬롯 번호 범위 초과 (0~39)",
    98: "OUT 지연 타이머 슬롯 없음 — 5개 모두 사용중",
    99: "알 수 없는 커맨드",
}

_SETTINGS_PATH = get_settings_path()


def load_user_alarms(settings_path=None):
    path = settings_path or _SETTINGS_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 기존 settings.json 호환: "sequence_alarms" 키 유지
        saved = data.get("sequence_alarms")
        if saved:
            USER_ALARMS.clear()
            USER_ALARMS.update({int(k): v for k, v in saved.items()})
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass


def save_user_alarms(settings_path=None):
    path = settings_path or _SETTINGS_PATH
    try:
        settings = load_json(path) or {}
        settings["sequence_alarms"] = {str(k): v for k, v in sorted(USER_ALARMS.items())}
        save_json(path, settings)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[알람] 저장 실패: {e}")


load_user_alarms()


# 알람 스타일 정의
_STYLE_ALARM = {
    'title_color': '#FF4646',
    'box_bg': '#2D1A1A',
    'box_border': '#FF4646',
}
_STYLE_COMM = {
    'title_color': '#F39C12',
    'box_bg': '#1A1500',
    'box_border': '#F39C12',
}


class AlarmOverlay(QWidget):
    sig_reset_pressed = Signal()
    sig_reset_released = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 활성 알람 관리
        self._alarms = {}       # id → {title, message, style_name, show_reset}
        self._order = []        # 삽입 순서 보존
        self._current_idx = 0

        # 배경
        self.setStyleSheet("background-color: rgba(0, 0, 0, 200);")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.setCursor(Qt.ArrowCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # 알람 박스
        self.box = QFrame()
        self.box.setFixedSize(500, 340)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 10)
        self.box.setGraphicsEffect(shadow)

        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(30, 20, 30, 20)
        box_layout.setSpacing(14)

        # 닫기(X) 버튼 — 박스 우상단에 고정 위치. comm 스타일 알람에만 노출.
        self.btn_close = QPushButton("✕", self.box)
        self.btn_close.setFixedSize(36, 36)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #DDD;
                font-size: 20px;
                font-weight: bold;
                border: 2px solid #888;
                border-radius: 18px;
            }
            QPushButton:hover { color: white; border-color: #CCC; }
            QPushButton:pressed { color: #AAA; border-color: #666; }
        """)
        self.btn_close.move(500 - 36 - 10, 10)
        self.btn_close.clicked.connect(self._on_close_current)
        self.btn_close.hide()

        # 제목
        self.lbl_title = QLabel("[!] SYSTEM ALARM [!]")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        box_layout.addWidget(self.lbl_title)

        # 메시지
        self.lbl_msg = QLabel("")
        self.lbl_msg.setAlignment(Qt.AlignCenter)
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        box_layout.addWidget(self.lbl_msg, 1)

        # 페이지 내비게이션 (여러 알람 때만 보임)
        self.nav_frame = QFrame()
        self.nav_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        nav_layout = QHBoxLayout(self.nav_frame)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(18)
        nav_layout.setAlignment(Qt.AlignCenter)

        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedSize(60, 40)
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setStyleSheet(self._nav_btn_qss())
        self.btn_prev.clicked.connect(self._on_prev)

        self.lbl_page = QLabel("1/1")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.lbl_page.setStyleSheet("color: #EEE; font-size: 18px; font-weight: bold; min-width: 60px;")

        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedSize(60, 40)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet(self._nav_btn_qss())
        self.btn_next.clicked.connect(self._on_next)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_page)
        nav_layout.addWidget(self.btn_next)
        box_layout.addWidget(self.nav_frame)

        # 리셋 버튼
        self.btn_reset = QPushButton("ALARM RESET")
        self.btn_reset.setFixedSize(250, 56)
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #C0392B;
                color: white;
                font-size: 22px;
                font-weight: bold;
                border: 2px solid #E74C3C;
                border-radius: 10px;
            }
            QPushButton:pressed { background-color: #E74C3C; }
        """)
        self.btn_reset.pressed.connect(self.sig_reset_pressed.emit)
        self.btn_reset.released.connect(self.sig_reset_released.emit)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        btn_row.addWidget(self.btn_reset)
        box_layout.addLayout(btn_row)

        layout.addWidget(self.box)

        self.hide()

    def _nav_btn_qss(self):
        return """
            QPushButton {
                background: transparent;
                color: white;
                font-size: 22px;
                font-weight: bold;
                border: 2px solid #888;
                border-radius: 8px;
            }
            QPushButton:hover { color: #FFD; border-color: #CCC; }
            QPushButton:pressed { color: #AAA; border-color: #666; }
            QPushButton:disabled { color: #555; border-color: #444; }
        """

    # ================================================================
    # 공개 API - 알람 추가/제거
    # ================================================================

    def add_alarm(self, alarm_id, title, message, style='alarm', show_reset=True, show_close=False):
        """알람 추가 또는 업데이트. 새 알람이면 해당 페이지로 자동 이동."""
        is_new = alarm_id not in self._alarms
        self._alarms[alarm_id] = {
            'title': title,
            'message': message,
            'style': style,
            'show_reset': show_reset,
            'show_close': show_close,
        }
        if is_new:
            self._order.append(alarm_id)
            self._current_idx = len(self._order) - 1
        self._refresh()

    def remove_alarm(self, alarm_id):
        """알람 제거. 활성 알람 없으면 오버레이 자동 숨김."""
        if alarm_id in self._alarms:
            del self._alarms[alarm_id]
            self._order.remove(alarm_id)
            if self._current_idx >= len(self._order):
                self._current_idx = max(0, len(self._order) - 1)
            self._refresh()

    def has_alarm(self, alarm_id):
        return alarm_id in self._alarms

    def has_any_alarm(self):
        return bool(self._order)

    # ================================================================
    # 하위 호환 API
    # ================================================================

    def show_error(self, axis_list, error_codes=None):
        """축 알람 + E-STOP 분리 등록."""
        axis_names = {1: "X축", 2: "Y축", 3: "Z축", 4: "Y2축", 5: "Z2축",
                      6: "θ축", 7: "R1축", 8: "R2축"}
        estop_present = 9 in axis_list
        axis_only = [a for a in axis_list if a != 9]

        if axis_only:
            lines = []
            for a in axis_only:
                name = axis_names.get(a, f"{a}축")
                if error_codes and len(error_codes) >= a and error_codes[a - 1] > 0:
                    code = error_codes[a - 1]
                    desc = AXIS_ERROR_DESCRIPTIONS.get(code, "")
                    if desc:
                        lines.append(f"{name}: E-{code:04X} ({desc})")
                    else:
                        lines.append(f"{name}: E-{code:04X}")
                else:
                    lines.append(name)
            msg = "축 알람 발생\n" + "\n".join(lines)
            self.add_alarm('axis', '[!] AXIS ALARM [!]', msg, 'alarm')
        else:
            self.remove_alarm('axis')

        if estop_present:
            self.add_alarm('estop', '[!] E-STOP [!]',
                           '비상정지가 활성화되었습니다.', 'alarm')
        # estop 해제는 호출자가 명시적으로 hide_estop()으로 처리

    def hide_axis_alarm(self):
        self.remove_alarm('axis')

    def show_estop(self):
        self.add_alarm('estop', '[!] E-STOP [!]',
                       '비상정지가 활성화되었습니다.', 'alarm')

    def hide_estop(self):
        self.remove_alarm('estop')

    def show_user_alarm(self, alarm_no):
        """사용자 알람 (IN 스텝 P3=1/2, w_UserAlarm/DT159) 표시."""
        msg = USER_ALARMS.get(alarm_no, f"사용자 알람 #{alarm_no}")
        self.add_alarm('user_alarm', '[!] USER ALARM [!]',
                       f"A-{alarm_no:03d}: {msg}", 'alarm')

    def hide_user_alarm(self):
        self.remove_alarm('user_alarm')

    def show_step_alarm(self, alarm_id):
        """스텝 알람 (i_StepAlarmID/DT160) 표시."""
        desc = STEP_ALARM_DESCRIPTIONS.get(alarm_id, f"정의되지 않은 에러 (ID={alarm_id})")
        self.add_alarm('step_alarm', '[!] STEP ALARM [!]',
                       f"E-{alarm_id:02d}: {desc}", 'alarm')

    def hide_step_alarm(self):
        self.remove_alarm('step_alarm')

    def show_comm_error(self):
        self.add_alarm('comm', '[!] COMM ERROR [!]',
                       'PLC와의 통신이 끊어졌습니다.\n자동으로 재연결을 시도합니다.',
                       'comm', show_reset=False, show_close=True)

    def hide_comm_error(self):
        self.remove_alarm('comm')

    # ================================================================
    # 내부: 표시 갱신
    # ================================================================

    def _refresh(self):
        if not self._order:
            if not self.isHidden():
                self.hide()
            return

        aid = self._order[self._current_idx]
        a = self._alarms[aid]
        self.lbl_title.setText(a['title'])
        self.lbl_msg.setText(a['message'])
        self._apply_style(a['style'])
        self.btn_reset.setVisible(a['show_reset'])
        self.btn_close.setVisible(a.get('show_close', False))
        if self.btn_close.isVisible():
            self.btn_close.raise_()

        total = len(self._order)
        self.lbl_page.setText(f"{self._current_idx + 1}/{total}")
        self.nav_frame.setVisible(total > 1)
        self.btn_prev.setEnabled(self._current_idx > 0)
        self.btn_next.setEnabled(self._current_idx < total - 1)

        if self.isHidden():
            self.show()
        self.raise_()

    def _apply_style(self, style_name):
        s = _STYLE_COMM if style_name == 'comm' else _STYLE_ALARM
        self.lbl_title.setStyleSheet(
            f"color: {s['title_color']}; font-size: 30px; font-weight: 900;"
        )
        self.box.setStyleSheet(f"""
            QFrame {{
                background-color: {s['box_bg']};
                border: 4px solid {s['box_border']};
                border-radius: 20px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)

    def _on_close_current(self):
        if not self._order:
            return
        aid = self._order[self._current_idx]
        self.remove_alarm(aid)

    def _on_prev(self):
        if self._current_idx > 0:
            self._current_idx -= 1
            self._refresh()

    def _on_next(self):
        if self._current_idx < len(self._order) - 1:
            self._current_idx += 1
            self._refresh()
