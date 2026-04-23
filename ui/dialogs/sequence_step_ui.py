# ui/dialogs/sequence_step_ui.py

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QGridLayout, QCheckBox, QScrollArea, QRadioButton, 
    QButtonGroup, QFrame, QStackedWidget, QDoubleSpinBox
)
# ClickableLineEdit는 이제 안 쓰지만, 혹시 몰라 import는 둠
from ui.widgets.custom_inputs import ClickableLineEdit, TouchComboBox

# 매니저 임포트
try:
    from utils.io_manager import IOManager
except ImportError:
    IOManager = None

try:
    from utils.mode_manager import ModeManager
except ImportError:
    ModeManager = None

# 상수 정의
VALVE_LIST = [
    "척 1 (Chuck 1)", "척 2 (Chuck 2)", "척 3 (Chuck 3)", "척 4 (Chuck 4)",
    "흡착 1 (Vac 1)", "흡착 2 (Vac 2)", "흡착 3 (Vac 3)", "흡착 4 (Vac 4)",
    "포스쳐 반전", "포스쳐 복귀", "스위블 회전", "스위블 복귀",
    "니퍼 컷팅 1", "니퍼 컷팅 2", "컨베이어 출력", "공급기 출력"
]

MODE_NAMES = [
    "제품측 취출", "런너측 취출", "주행 대기", "하강 대기",
    "주행도중개방", "복귀도중개방", "안전도어 회피", "안전도어 회피2",
    "낙하측 반전", "주행도중 반전", "취출대기 반전", "고정측 취출",
    "제품 형내개방", "런너 형내개방", "에젝터 연동", "언더컷 취출모드",
    "척1 사용", "척1 감지", "척2 사용", "척2 감지",
    "척3 사용", "척3 감지", "척4 사용", "척4 감지",
    "흡착1 사용", "흡착1 감지", "흡착2 사용", "흡착2 감지",
    "흡착3 사용", "흡착3 감지", "흡착4 사용", "흡착4 감지",
    "2포인트 개방", "공정감시 모드",
]

INTERNAL_BIT_COUNT = 16

class StepUIGenerator:
    """오른쪽 속성 편집 패널들을 생성하여 메인 다이얼로그에 붙여주는 클래스"""

    @staticmethod
    def create_pos_editor(dlg):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        
        # 포인트 선택 그룹
        gb_point = QGroupBox("목표 위치 포인트")
        gb_point.setStyleSheet(StepUIGenerator._groupbox_style())
        point_layout = QHBoxLayout(gb_point)
        point_layout.setContentsMargins(10, 5, 10, 5) 
        
        # 버튼으로 변경됨
        dlg.btn_point_select = QPushButton("선택하세요")
        dlg.btn_point_select.setFixedHeight(45)
        dlg.btn_point_select.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid #888;
                border-radius: 4px;
                color: white;
                font-size: 15px;
                font-weight: bold;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.2); }
        """)
        dlg.btn_point_select.clicked.connect(dlg._open_point_list)
        
        point_layout.addWidget(dlg.btn_point_select, 1)
        
        btn_new = StepUIGenerator._icon_btn("+", "#468CFF", "새 포인트")
        btn_new.clicked.connect(dlg._on_new_point_clicked)
        
        btn_rename = StepUIGenerator._icon_btn("수정", "#FFFFFF", "이름 변경")
        btn_rename.clicked.connect(dlg._on_rename_point_clicked)

        btn_del = StepUIGenerator._icon_btn("삭제", "#FF4646", "삭제")
        btn_del.clicked.connect(dlg._on_delete_point_clicked)

        point_layout.addWidget(btn_new)
        point_layout.addWidget(btn_rename)
        point_layout.addWidget(btn_del)

        # ★ 포인트 그룹 (높이 고정 안함)
        lay.addWidget(gb_point)

        # 파렛타이징 베이스 체크박스 (X/Y/Z를 스택 인덱스에 따라 가감산)
        dlg.chk_pack_base = QCheckBox("파렛타이징 베이스 (X/Y/Z 스택 가감산)")
        dlg.chk_pack_base.setStyleSheet(
            "QCheckBox { color: #64FFDA; font-size: 14px; font-weight: bold; padding: 4px; } "
            "QCheckBox::indicator { width: 22px; height: 22px; border: 2px solid #64FFDA; "
            "border-radius: 4px; background: transparent; } "
            "QCheckBox::indicator:checked { background-color: #64FFDA; border: 2px solid #64FFDA; }"
        )
        lay.addWidget(dlg.chk_pack_base)

        # 축/속도 설정 그룹
        gb_axes = QGroupBox("축 선택 및 속도")
        gb_axes.setStyleSheet(StepUIGenerator._groupbox_style())
        gl = QGridLayout(gb_axes)
        gl.setSpacing(2)  # 간격 좁게
        gl.setContentsMargins(10, 15, 10, 5)  # 상단 여백 더 줄임 (2 → 15, 타이틀 공간만 확보)
        gl.setVerticalSpacing(2)  # 수직 간격 더 좁게 (3 → 2)
        
        headers = ["사용", "축", "목표위치", "속도%"]
        for c, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold;")
            gl.addWidget(lbl, 0, c)
        
        dlg.axis_checkboxes = []
        dlg.pos_labels = []
        dlg.speed_spinboxes = []
        
        axes = ["X", "Y", "Z", "Y2", "Z2", "θ", "R1", "R2"]
        
        # ★ dlg에서 enabled_axes 가져오기
        enabled_axes = getattr(dlg, 'enabled_axes', [True] * 8)
        
        visible_row = 1  # 헤더 다음 행부터
        for i, ax in enumerate(axes):
            # ★ 연결되지 않은 축은 건너뜀
            if not enabled_axes[i]:
                # 빈 위젯이라도 추가해서 인덱스 유지 (데이터 호환성)
                dlg.axis_checkboxes.append(None)
                dlg.pos_labels.append(None)
                dlg.speed_spinboxes.append(None)
                continue
            
            row = visible_row
            
            chk = QCheckBox()
            chk.setStyleSheet("""
                QCheckBox::indicator { 
                    width: 24px; 
                    height: 24px; 
                    border: 2px solid #888888; 
                    border-radius: 4px;
                    background: transparent;
                }
                QCheckBox::indicator:checked { 
                    background-color: #468CFF; 
                    border: 2px solid #468CFF;
                }
            """)
            
            dlg.axis_checkboxes.append(chk)
            gl.addWidget(chk, row, 0, Qt.AlignCenter)
            
            lbl_axis = QLabel(ax)
            lbl_axis.setAlignment(Qt.AlignCenter)
            lbl_axis.setStyleSheet("color: #FFFFFF; font-weight: 900; font-size: 14px;")
            gl.addWidget(lbl_axis, row, 1)
            
            btn_pos = QPushButton("0.00")
            btn_pos.setCursor(Qt.PointingHandCursor)
            btn_pos.setStyleSheet(StepUIGenerator._value_btn_style("#64FFDA"))
            btn_pos.setFixedHeight(28)  # 32 → 28로 줄임 (간격 좁게)
            btn_pos.clicked.connect(lambda checked, idx=i: dlg._on_pos_edit_clicked(idx))
            dlg.pos_labels.append(btn_pos) 
            gl.addWidget(btn_pos, row, 2)
            
            btn_spd = QPushButton("100")
            btn_spd.setCursor(Qt.PointingHandCursor)
            btn_spd.setStyleSheet(StepUIGenerator._value_btn_style("#FFD280"))
            btn_spd.setFixedHeight(28)  # 32 → 28로 줄임 (간격 좁게)
            btn_spd.clicked.connect(lambda checked, idx=i: dlg._on_speed_edit_clicked(idx))
            dlg.speed_spinboxes.append(btn_spd) 
            gl.addWidget(btn_spd, row, 3)
            
            visible_row += 1  # 다음 표시할 행
        
        gl.setColumnStretch(0, 0)
        gl.setColumnStretch(1, 1)
        gl.setColumnStretch(2, 2)
        gl.setColumnStretch(3, 1)
        
        # ★ 축 그룹 추가 (비율 없이 자연스럽게)
        lay.addWidget(gb_axes)
        
        # ★ 마지막에 stretch 추가 (남은 공간 채우기)
        lay.addStretch(1)
        
        # ★ [수정됨] 이름 변경 입력창(name_gb) 삭제됨!
        # 공간 확보 완료
        
        return w

    @staticmethod
    def create_io_editor(dlg):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        
        gb = QGroupBox("입출력 설정")
        gb.setStyleSheet(StepUIGenerator._groupbox_style())
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(7)
        vbox.setContentsMargins(10, 14, 10, 6)
        
        # ★ [수정] OUT 스텝 전용: 출력 구분 (상단으로 이동)
        dlg.out_type_frame = QWidget()
        out_type_layout = QVBoxLayout(dlg.out_type_frame)
        out_type_layout.setContentsMargins(0, 0, 0, 6)
        out_type_layout.setSpacing(6)
        out_type_layout.addWidget(QLabel("출력 구분"))
        rb_otype_row = QWidget()
        rb_otype_layout = QHBoxLayout(rb_otype_row)
        rb_otype_layout.setContentsMargins(0, 0, 0, 0)
        rb_otype_layout.setSpacing(12)
        dlg.rb_out_sys      = QRadioButton("시스템 출력")
        dlg.rb_out_valve    = QRadioButton("밸브 출력")
        dlg.rb_out_internal = QRadioButton("내부 비트")
        dlg.rb_out_sys.setChecked(True)
        dlg.out_type_grp = QButtonGroup(dlg.out_type_frame)
        dlg.out_type_grp.addButton(dlg.rb_out_sys,      0)
        dlg.out_type_grp.addButton(dlg.rb_out_valve,    1)
        dlg.out_type_grp.addButton(dlg.rb_out_internal, 2)
        for rb in [dlg.rb_out_sys, dlg.rb_out_valve, dlg.rb_out_internal]:
            rb_otype_layout.addWidget(rb)
        rb_otype_layout.addStretch()
        out_type_layout.addWidget(rb_otype_row)
        vbox.addWidget(dlg.out_type_frame)
        dlg.out_type_frame.setVisible(False)

        # ★ [신규] IN 스텝 전용: 입력 구분
        dlg.in_type_frame = QWidget()
        in_type_layout = QVBoxLayout(dlg.in_type_frame)
        in_type_layout.setContentsMargins(0, 0, 0, 6)
        in_type_layout.setSpacing(6)
        in_type_layout.addWidget(QLabel("입력 구분"))
        rb_itype_row = QWidget()
        rb_itype_layout = QHBoxLayout(rb_itype_row)
        rb_itype_layout.setContentsMargins(0, 0, 0, 0)
        rb_itype_layout.setSpacing(12)
        dlg.rb_in_sys      = QRadioButton("시스템 입력")
        dlg.rb_in_valve    = QRadioButton("밸브 입력")
        dlg.rb_in_internal = QRadioButton("내부 비트")
        dlg.rb_in_sys.setChecked(True)
        dlg.in_type_grp = QButtonGroup(dlg.in_type_frame)
        dlg.in_type_grp.addButton(dlg.rb_in_sys,      0)
        dlg.in_type_grp.addButton(dlg.rb_in_valve,    1)
        dlg.in_type_grp.addButton(dlg.rb_in_internal, 2)
        for rb in [dlg.rb_in_sys, dlg.rb_in_valve, dlg.rb_in_internal]:
            rb_itype_layout.addWidget(rb)
        rb_itype_layout.addStretch()
        in_type_layout.addWidget(rb_itype_row)
        vbox.addWidget(dlg.in_type_frame)
        dlg.in_type_frame.setVisible(False)

        dlg.lbl_io_target = QLabel("대상 포트")
        vbox.addWidget(dlg.lbl_io_target)

        # ★ 버튼으로 변경 (터치 친화적)
        dlg.io_combo_btn = QPushButton("선택하세요")
        dlg.io_combo_btn.setFixedHeight(45)
        dlg.io_combo_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid #888;
                border-radius: 4px;
                color: white;
                font-size: 15px;
                font-weight: bold;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.2); }
        """)
        dlg.io_combo_btn.clicked.connect(dlg._open_io_selector)
        vbox.addWidget(dlg.io_combo_btn)

        # 기존 콤보박스는 숨김 (데이터 저장용)
        dlg.io_combo = TouchComboBox()
        dlg.io_combo.setFixedHeight(42)
        dlg.io_combo.currentIndexChanged.connect(dlg._on_io_value_changed)
        dlg.io_combo.hide()

        vbox.addWidget(QLabel("상태"))
        bg_widget = QWidget()
        bl = QHBoxLayout(bg_widget)
        bl.setContentsMargins(0, 0, 0, 0)
        dlg.rb_on = QRadioButton("ON")
        dlg.rb_off = QRadioButton("OFF")
        for rb in [dlg.rb_on, dlg.rb_off]:
            rb.toggled.connect(dlg._on_io_value_changed)
        dlg.io_group = QButtonGroup(w)
        dlg.io_group.addButton(dlg.rb_on)
        dlg.io_group.addButton(dlg.rb_off)
        bl.addWidget(dlg.rb_on)
        bl.addSpacing(20)
        bl.addWidget(dlg.rb_off)
        bl.addStretch(1)
        vbox.addWidget(bg_widget)

        # ★ OUT 스텝 전용: 타이머 기동후출력
        dlg.out_delay_frame = QWidget()
        out_delay_layout = QVBoxLayout(dlg.out_delay_frame)
        out_delay_layout.setContentsMargins(0, 4, 0, 0)
        out_delay_layout.setSpacing(5)

        dlg.chk_out_delay = QCheckBox("타이머 기동후출력")
        dlg.chk_out_delay.setStyleSheet(
            "QCheckBox { font-size: 14px; font-weight: bold; color: #FFD700; }"
            "QCheckBox::indicator { width: 22px; height: 22px; border: 2px solid #FFD700; border-radius: 4px; background: transparent; }"
            "QCheckBox::indicator:checked { background: #FFD700; border: 2px solid #FFD700; }"
        )
        out_delay_layout.addWidget(dlg.chk_out_delay)

        dlg.out_delay_timer_btn = QPushButton("타이머 선택하세요")
        dlg.out_delay_timer_btn.setFixedHeight(38)
        dlg.out_delay_timer_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 215, 0, 0.08);
                border: 1px solid #FFD700;
                border-radius: 4px;
                color: #FFD700;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
                padding-left: 12px;
            }
            QPushButton:pressed { background: rgba(255, 215, 0, 0.2); }
            QPushButton:disabled { color: #666; border-color: #555; }
        """)
        dlg.out_delay_timer_btn.clicked.connect(dlg._open_out_delay_timer_selector)
        out_delay_layout.addWidget(dlg.out_delay_timer_btn)

        def _on_delay_chk_toggled(checked):
            dlg.out_delay_timer_btn.setEnabled(checked)
            dlg._on_io_value_changed()

        dlg.chk_out_delay.toggled.connect(_on_delay_chk_toggled)
        dlg.out_delay_timer_btn.setEnabled(False)

        vbox.addWidget(dlg.out_delay_frame)
        dlg.out_delay_frame.setVisible(False)

        # ★ IN 스텝 전용: 타임아웃 설정
        dlg.in_timeout_frame = QWidget()
        timeout_layout = QVBoxLayout(dlg.in_timeout_frame)
        timeout_layout.setContentsMargins(0, 4, 0, 0)
        timeout_layout.setSpacing(5)

        # 타임아웃 사용/미사용 라디오 버튼
        from PySide6.QtWidgets import QHBoxLayout as _QHBox
        rb_row = QWidget()
        rb_row_layout = _QHBox(rb_row)
        rb_row_layout.setContentsMargins(0, 0, 0, 0)
        rb_row_layout.setSpacing(20)
        dlg.rb_timeout_enabled = QRadioButton("사용")
        dlg.rb_timeout_disabled = QRadioButton("미사용")
        dlg.rb_timeout_enabled.setChecked(True)
        dlg.timeout_use_grp = QButtonGroup(rb_row)
        dlg.timeout_use_grp.addButton(dlg.rb_timeout_enabled)
        dlg.timeout_use_grp.addButton(dlg.rb_timeout_disabled)
        rb_row_layout.addWidget(QLabel("타임아웃:"))
        rb_row_layout.addWidget(dlg.rb_timeout_enabled)
        rb_row_layout.addWidget(dlg.rb_timeout_disabled)
        rb_row_layout.addStretch()
        timeout_layout.addWidget(rb_row)
        dlg.rb_timeout_enabled.toggled.connect(dlg._on_io_value_changed)

        # 타임아웃 시간 (항상 표시)
        timeout_layout.addWidget(QLabel("타임아웃 (초)"))

        dlg.timeout_btn = QPushButton("5.0 sec")
        dlg.timeout_btn.setFixedHeight(38)
        dlg.timeout_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid #888;
                border-radius: 4px;
                color: #FFD700;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.2); }
        """)
        dlg.timeout_btn.clicked.connect(dlg._on_timeout_edit_clicked)
        timeout_layout.addWidget(dlg.timeout_btn)

        timeout_layout.addWidget(QLabel("타임아웃 시 동작"))

        action_widget = QWidget()
        action_layout = QVBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(2)

        dlg.rb_timeout_continue = QRadioButton("계속 대기")
        dlg.rb_timeout_ask = QRadioButton("알람 띄우고 정지")
        dlg.rb_timeout_alarm_go = QRadioButton("알람 띄우고 진행")

        dlg.timeout_action_grp = QButtonGroup(w)
        dlg.timeout_action_grp.addButton(dlg.rb_timeout_continue)
        dlg.timeout_action_grp.addButton(dlg.rb_timeout_ask)
        dlg.timeout_action_grp.addButton(dlg.rb_timeout_alarm_go)

        for rb in [dlg.rb_timeout_continue, dlg.rb_timeout_ask, dlg.rb_timeout_alarm_go]:
            rb.toggled.connect(dlg._on_io_value_changed)

        action_layout.addWidget(dlg.rb_timeout_continue)
        action_layout.addWidget(dlg.rb_timeout_ask)
        action_layout.addWidget(dlg.rb_timeout_alarm_go)

        timeout_layout.addWidget(action_widget)

        # 알람 번호 선택 (알람 관련 옵션 선택 시 표시)
        dlg.timeout_alarm_frame = QWidget()
        alarm_layout = QVBoxLayout(dlg.timeout_alarm_frame)
        alarm_layout.setContentsMargins(20, 0, 0, 0)
        alarm_layout.setSpacing(0)

        dlg.timeout_alarm_btn = QPushButton("선택하세요")
        dlg.timeout_alarm_btn.setFixedHeight(35)
        dlg.timeout_alarm_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid #FF4646;
                border-radius: 4px;
                color: #FF4646;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:pressed { background: rgba(255, 70, 70, 0.2); }
        """)
        dlg.timeout_alarm_btn.clicked.connect(dlg._open_timeout_alarm_selector)
        alarm_layout.addWidget(dlg.timeout_alarm_btn)

        timeout_layout.addWidget(dlg.timeout_alarm_frame)
        dlg.timeout_alarm_frame.setVisible(False)

        def _update_alarm_frame(checked):
            show = dlg.rb_timeout_ask.isChecked() or dlg.rb_timeout_alarm_go.isChecked()
            dlg.timeout_alarm_frame.setVisible(show)

        dlg.rb_timeout_ask.toggled.connect(_update_alarm_frame)
        dlg.rb_timeout_alarm_go.toggled.connect(_update_alarm_frame)

        # 기본 선택
        dlg.rb_timeout_continue.setChecked(True)
        
        vbox.addWidget(dlg.in_timeout_frame)
        # IN 스텝이 아닐 때 숨김
        dlg.in_timeout_frame.setVisible(False)
        
        vbox.addStretch(1)
        lay.addWidget(gb)
        return w

    @staticmethod
    def create_tmr_editor(dlg):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        gb = QGroupBox("시간 설정")
        gb.setStyleSheet(StepUIGenerator._groupbox_style())
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(8)
        vbox.setContentsMargins(10, 14, 10, 6)

        # 모드 선택
        mode_row = QWidget()
        mode_lay = QHBoxLayout(mode_row)
        mode_lay.setContentsMargins(0, 0, 0, 0)
        mode_lay.setSpacing(20)
        dlg.rb_tmr_simple = QRadioButton("단순 대기")
        dlg.rb_tmr_hold   = QRadioButton("신호 유지")
        dlg.rb_tmr_simple.setChecked(True)
        dlg.tmr_mode_grp = QButtonGroup(w)
        dlg.tmr_mode_grp.addButton(dlg.rb_tmr_simple, 0)
        dlg.tmr_mode_grp.addButton(dlg.rb_tmr_hold,   1)
        for rb in [dlg.rb_tmr_simple, dlg.rb_tmr_hold]:
            rb.toggled.connect(dlg._on_tmr_mode_changed)
            mode_lay.addWidget(rb)
        mode_lay.addStretch()
        vbox.addWidget(mode_row)

        # 모드별 콘텐츠 스택
        dlg.tmr_mode_stack = QStackedWidget()

        # ── 페이지 0: 단순 대기 ──────────────────────────
        simple_w = QWidget()
        simple_w.setStyleSheet("background: transparent;")
        sl = QVBoxLayout(simple_w)
        sl.setContentsMargins(0, 4, 0, 0)
        sl.setSpacing(8)
        sl.addWidget(QLabel("타이머 선택"))
        dlg.tmr_btn = QPushButton("선택하세요")
        dlg.tmr_btn.setFixedHeight(50)
        dlg.tmr_btn.setStyleSheet(StepUIGenerator._value_btn_style("#FFD700"))
        dlg.tmr_btn.clicked.connect(dlg._open_timer_selector)
        sl.addWidget(dlg.tmr_btn)

        # 선택된 타이머의 시간값 표시/편집 (타이머 선택 후 표시)
        dlg.tmr_simple_time_frame = QWidget()
        dlg.tmr_simple_time_frame.setStyleSheet("background: transparent;")
        dlg.tmr_simple_time_frame.setVisible(False)
        time_row = QVBoxLayout(dlg.tmr_simple_time_frame)
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.setSpacing(4)
        time_row.addWidget(QLabel("설정 시간"))
        dlg.tmr_simple_time_btn = QPushButton("1.0 sec")
        dlg.tmr_simple_time_btn.setFixedHeight(45)
        dlg.tmr_simple_time_btn.setStyleSheet(StepUIGenerator._value_btn_style("#00CFFF"))
        dlg.tmr_simple_time_btn.clicked.connect(dlg._on_tmr_simple_time_clicked)
        time_row.addWidget(dlg.tmr_simple_time_btn)
        sl.addWidget(dlg.tmr_simple_time_frame)

        sl.addStretch(1)
        dlg.tmr_mode_stack.addWidget(simple_w)

        # ── 페이지 1: 신호 유지 ──────────────────────────
        hold_w = QWidget()
        hold_w.setStyleSheet("background: transparent;")
        hl = QVBoxLayout(hold_w)
        hl.setContentsMargins(0, 4, 0, 0)
        hl.setSpacing(7)

        # 입력 구분
        itype_row = QWidget()
        itype_lay = QHBoxLayout(itype_row)
        itype_lay.setContentsMargins(0, 0, 0, 0)
        itype_lay.setSpacing(8)
        itype_lay.addWidget(QLabel("입력 구분"))
        dlg.tmr_hold_rb_sys      = QRadioButton("시스템")
        dlg.tmr_hold_rb_valve    = QRadioButton("밸브")
        dlg.tmr_hold_rb_internal = QRadioButton("내부비트")
        dlg.tmr_hold_rb_sys.setChecked(True)
        dlg.tmr_hold_type_grp = QButtonGroup(hold_w)
        dlg.tmr_hold_type_grp.addButton(dlg.tmr_hold_rb_sys,      0)
        dlg.tmr_hold_type_grp.addButton(dlg.tmr_hold_rb_valve,    1)
        dlg.tmr_hold_type_grp.addButton(dlg.tmr_hold_rb_internal, 2)
        for rb in [dlg.tmr_hold_rb_sys, dlg.tmr_hold_rb_valve, dlg.tmr_hold_rb_internal]:
            rb.toggled.connect(dlg._on_tmr_hold_type_changed)
            itype_lay.addWidget(rb)
        itype_lay.addStretch()
        hl.addWidget(itype_row)

        hl.addWidget(QLabel("감시할 신호"))
        dlg.tmr_hold_io_btn = QPushButton("선택하세요")
        dlg.tmr_hold_io_btn.setFixedHeight(42)
        dlg.tmr_hold_io_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid #888;
                border-radius: 4px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
                padding-left: 12px;
            }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.2); }
        """)
        dlg.tmr_hold_io_btn.clicked.connect(dlg._open_tmr_hold_io_selector)
        hl.addWidget(dlg.tmr_hold_io_btn)

        hl.addWidget(QLabel("유지할 상태"))
        state_row = QWidget()
        state_lay = QHBoxLayout(state_row)
        state_lay.setContentsMargins(0, 0, 0, 0)
        dlg.tmr_hold_rb_on  = QRadioButton("ON")
        dlg.tmr_hold_rb_off = QRadioButton("OFF")
        dlg.tmr_hold_rb_on.setChecked(True)
        dlg.tmr_hold_state_grp = QButtonGroup(hold_w)
        dlg.tmr_hold_state_grp.addButton(dlg.tmr_hold_rb_on)
        dlg.tmr_hold_state_grp.addButton(dlg.tmr_hold_rb_off)
        for rb in [dlg.tmr_hold_rb_on, dlg.tmr_hold_rb_off]:
            rb.toggled.connect(dlg._on_tmr_hold_value_changed)
            state_lay.addWidget(rb)
        state_lay.addStretch()
        hl.addWidget(state_row)

        hl.addWidget(QLabel("유지 시간 (초)"))
        dlg.tmr_hold_time_btn = QPushButton("1.0 sec")
        dlg.tmr_hold_time_btn.setFixedHeight(45)
        dlg.tmr_hold_time_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid #64FFDA;
                border-radius: 4px;
                color: #64FFDA;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:pressed { background: rgba(100, 255, 218, 0.2); }
        """)
        dlg.tmr_hold_time_btn.clicked.connect(dlg._on_tmr_edit_clicked)
        hl.addWidget(dlg.tmr_hold_time_btn)
        hl.addStretch(1)
        dlg.tmr_mode_stack.addWidget(hold_w)

        vbox.addWidget(dlg.tmr_mode_stack)
        vbox.addStretch(1)
        lay.addWidget(gb)
        return w

    @staticmethod
    def create_jmp_editor(dlg):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        
        gb_target = QGroupBox("이동 목표")
        gb_target.setStyleSheet(StepUIGenerator._groupbox_style())
        l1 = QVBoxLayout(gb_target)
        l1.setContentsMargins(10, 20, 10, 10)
        
        # ★ 버튼으로 변경
        dlg.jmp_target_btn = QPushButton("선택하세요")
        dlg.jmp_target_btn.setFixedHeight(45)
        dlg.jmp_target_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid #888;
                border-radius: 4px;
                color: white;
                font-size: 15px;
                font-weight: bold;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.2); }
        """)
        dlg.jmp_target_btn.clicked.connect(dlg._open_jmp_target_selector)
        l1.addWidget(dlg.jmp_target_btn)
        
        # 기존 콤보박스는 숨김 (데이터 저장용)
        dlg.jmp_target_combo = TouchComboBox()
        dlg.jmp_target_combo.setFixedHeight(42)
        dlg.jmp_target_combo.currentIndexChanged.connect(dlg._on_jmp_value_changed)
        dlg.jmp_target_combo.hide()
        
        lay.addWidget(gb_target)
        
        gb_cond = QGroupBox("이동 조건")
        gb_cond.setStyleSheet(StepUIGenerator._groupbox_style())
        l2 = QVBoxLayout(gb_cond)
        l2.setContentsMargins(10, 20, 10, 10)
        l2.setSpacing(8)
        
        bg = QWidget()
        bl = QHBoxLayout(bg)
        bl.setContentsMargins(0, 0, 0, 0)
        dlg.rb_jmp_always = QRadioButton("무조건")
        dlg.rb_jmp_cond = QRadioButton("조건부")

        dlg.jmp_grp = QButtonGroup(w)
        dlg.jmp_grp.addButton(dlg.rb_jmp_always)
        dlg.jmp_grp.addButton(dlg.rb_jmp_cond)

        for rb in [dlg.rb_jmp_always, dlg.rb_jmp_cond]:
            rb.toggled.connect(dlg._on_jmp_value_changed)

        bl.addWidget(dlg.rb_jmp_always)
        bl.addWidget(dlg.rb_jmp_cond)
        bl.addStretch(1)
        l2.addWidget(bg)

        dlg.jmp_cond_frame = QFrame()
        dlg.jmp_cond_frame.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 4px;")
        fl = QVBoxLayout(dlg.jmp_cond_frame)
        fl.setContentsMargins(8, 8, 8, 8)
        fl.setSpacing(6)
        
        # ★ 조건 타입 선택 (시스템입력, 밸브입력, 내부비트, 모드)
        src_bg = QWidget()
        src_lay = QHBoxLayout(src_bg)
        src_lay.setContentsMargins(0, 0, 0, 0)
        dlg.rb_src_input = QRadioButton("시스템입력")
        dlg.rb_src_valve = QRadioButton("밸브입력")
        dlg.rb_src_bit   = QRadioButton("내부비트")
        dlg.rb_src_mode  = QRadioButton("모드")

        dlg.rb_src_state = QRadioButton("운전상태")

        dlg.src_grp = QButtonGroup(w)
        dlg.src_grp.addButton(dlg.rb_src_input)
        dlg.src_grp.addButton(dlg.rb_src_valve)
        dlg.src_grp.addButton(dlg.rb_src_bit)
        dlg.src_grp.addButton(dlg.rb_src_mode)
        dlg.src_grp.addButton(dlg.rb_src_state)

        for rb in [dlg.rb_src_input, dlg.rb_src_valve, dlg.rb_src_bit, dlg.rb_src_mode, dlg.rb_src_state]:
            rb.toggled.connect(dlg._on_jmp_value_changed)

        src_lay.addWidget(dlg.rb_src_input)
        src_lay.addWidget(dlg.rb_src_valve)
        src_lay.addWidget(dlg.rb_src_bit)
        src_lay.addWidget(dlg.rb_src_mode)
        src_lay.addWidget(dlg.rb_src_state)
        src_lay.addStretch(1)
        fl.addWidget(src_bg)

        dlg.stack_cond_source = QStackedWidget()

        _btn_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid #888;
                border-radius: 4px;
                color: white;
                font-size: 15px;
                font-weight: bold;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.2); }
        """

        # ★ 0. 시스템입력 (X)
        dlg.jmp_input_btn = QPushButton("선택하세요")
        dlg.jmp_input_btn.setFixedHeight(45)
        dlg.jmp_input_btn.setStyleSheet(_btn_style)
        dlg.jmp_input_btn.clicked.connect(dlg._open_jmp_input_selector)
        dlg.jmp_input_combo = TouchComboBox()
        dlg.jmp_input_combo.hide()
        dlg.jmp_input_combo.currentIndexChanged.connect(dlg._on_jmp_value_changed)
        input_widget = QWidget()
        input_lay = QVBoxLayout(input_widget)
        input_lay.setContentsMargins(0, 0, 0, 0)
        input_lay.addWidget(dlg.jmp_input_btn)
        input_lay.addWidget(dlg.jmp_input_combo)
        dlg.stack_cond_source.addWidget(input_widget)

        # ★ 1. 밸브입력 (Y)
        dlg.jmp_valve_btn = QPushButton("선택하세요")
        dlg.jmp_valve_btn.setFixedHeight(45)
        dlg.jmp_valve_btn.setStyleSheet(_btn_style)
        dlg.jmp_valve_btn.clicked.connect(dlg._open_jmp_valve_selector)
        dlg.jmp_valve_combo = TouchComboBox()
        dlg.jmp_valve_combo.hide()
        dlg.jmp_valve_combo.currentIndexChanged.connect(dlg._on_jmp_value_changed)
        valve_widget = QWidget()
        valve_lay = QVBoxLayout(valve_widget)
        valve_lay.setContentsMargins(0, 0, 0, 0)
        valve_lay.addWidget(dlg.jmp_valve_btn)
        valve_lay.addWidget(dlg.jmp_valve_combo)
        dlg.stack_cond_source.addWidget(valve_widget)

        # ★ 2. 내부비트 (M)
        dlg.jmp_bit_btn = QPushButton("선택하세요")
        dlg.jmp_bit_btn.setFixedHeight(45)
        dlg.jmp_bit_btn.setStyleSheet(_btn_style)
        dlg.jmp_bit_btn.clicked.connect(dlg._open_jmp_bit_selector)
        dlg.jmp_bit_combo = TouchComboBox()
        dlg.jmp_bit_combo.hide()
        dlg.jmp_bit_combo.currentIndexChanged.connect(dlg._on_jmp_value_changed)
        bit_widget = QWidget()
        bit_lay = QVBoxLayout(bit_widget)
        bit_lay.setContentsMargins(0, 0, 0, 0)
        bit_lay.addWidget(dlg.jmp_bit_btn)
        bit_lay.addWidget(dlg.jmp_bit_combo)
        dlg.stack_cond_source.addWidget(bit_widget)

        # ★ 3. 모드
        dlg.jmp_mode_btn = QPushButton("선택하세요")
        dlg.jmp_mode_btn.setFixedHeight(45)
        dlg.jmp_mode_btn.setStyleSheet(_btn_style)
        dlg.jmp_mode_btn.clicked.connect(dlg._open_jmp_mode_selector)
        dlg.jmp_mode_combo = TouchComboBox()
        dlg.jmp_mode_combo.hide()
        dlg.jmp_mode_combo.currentIndexChanged.connect(dlg._on_jmp_value_changed)
        mode_widget = QWidget()
        mode_lay = QVBoxLayout(mode_widget)
        mode_lay.setContentsMargins(0, 0, 0, 0)
        mode_lay.addWidget(dlg.jmp_mode_btn)
        mode_lay.addWidget(dlg.jmp_mode_combo)
        dlg.stack_cond_source.addWidget(mode_widget)

        # ★ 4. 운전상태 (i_ControlCmd: 0=정지, 1=자동, 2=확인운전)
        state_widget = QWidget()
        state_lay = QVBoxLayout(state_widget)
        state_lay.setContentsMargins(0, 4, 0, 0)
        state_lay.setSpacing(4)
        dlg.jmp_run_state_grp = QButtonGroup(state_widget)
        dlg.jmp_run_state_rbs = {}
        rb_run_row = QWidget()
        rb_run_row_lay = QHBoxLayout(rb_run_row)
        rb_run_row_lay.setContentsMargins(0, 0, 0, 0)
        rb_run_row_lay.setSpacing(14)
        for label, val in [("정지", 0), ("자동", 1), ("확인운전", 2)]:
            rb = QRadioButton(label)
            rb.toggled.connect(dlg._on_jmp_value_changed)
            dlg.jmp_run_state_grp.addButton(rb, val)
            dlg.jmp_run_state_rbs[val] = rb
            rb_run_row_lay.addWidget(rb)
        rb_run_row_lay.addStretch()
        state_lay.addWidget(rb_run_row)
        dlg.jmp_run_state_rbs[2].setChecked(True)  # 기본: 확인운전
        dlg.stack_cond_source.addWidget(state_widget)

        fl.addWidget(dlg.stack_cond_source)
        
        bg2 = QWidget()
        bl2 = QHBoxLayout(bg2)
        bl2.setContentsMargins(0, 0, 0, 0)
        dlg.rb_jmp_on = QRadioButton("ON")
        dlg.rb_jmp_off = QRadioButton("OFF")
        
        dlg.jmp_state_grp = QButtonGroup(w)
        dlg.jmp_state_grp.addButton(dlg.rb_jmp_on)
        dlg.jmp_state_grp.addButton(dlg.rb_jmp_off)
        
        for rb in [dlg.rb_jmp_on, dlg.rb_jmp_off]:
            rb.toggled.connect(dlg._on_jmp_value_changed)
            
        bl2.addWidget(dlg.rb_jmp_on)
        bl2.addWidget(dlg.rb_jmp_off)
        bl2.addStretch(1)
        fl.addWidget(bg2)
        
        l2.addWidget(dlg.jmp_cond_frame)
        lay.addWidget(gb_cond)
        
        lay.addStretch(1)
        return w

    @staticmethod
    def create_call_editor(dlg):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        
        gb = QGroupBox("시퀀스 호출")
        gb.setStyleSheet(StepUIGenerator._groupbox_style())
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(12)
        vbox.setContentsMargins(10, 20, 10, 10)
        
        vbox.addWidget(QLabel("호출할 시퀀스 선택"))
        
        # ★ 버튼으로 변경
        dlg.call_btn = QPushButton("선택하세요")
        dlg.call_btn.setFixedHeight(45)
        dlg.call_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid #888;
                border-radius: 4px;
                color: white;
                font-size: 15px;
                font-weight: bold;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.2); }
        """)
        dlg.call_btn.clicked.connect(dlg._open_call_selector)
        vbox.addWidget(dlg.call_btn)
        
        # 기존 콤보박스는 숨김 (데이터 저장용)
        dlg.call_combo = TouchComboBox()
        dlg.call_combo.setFixedHeight(45)
        dlg.call_combo.currentIndexChanged.connect(dlg._on_call_value_changed)
        dlg.call_combo.hide()
        
        # ★ 실행 모드 선택 추가
        vbox.addSpacing(10)
        vbox.addWidget(QLabel("실행 모드"))
        
        mode_bg = QWidget()
        mode_lay = QHBoxLayout(mode_bg)
        mode_lay.setContentsMargins(0, 0, 0, 0)
        
        dlg.rb_call_wait = QRadioButton("대기 후 실행")
        dlg.rb_call_parallel = QRadioButton("동시 실행")
        
        dlg.call_mode_grp = QButtonGroup(w)
        dlg.call_mode_grp.addButton(dlg.rb_call_wait)
        dlg.call_mode_grp.addButton(dlg.rb_call_parallel)
        
        for rb in [dlg.rb_call_wait, dlg.rb_call_parallel]:
            rb.toggled.connect(dlg._on_call_value_changed)
        
        mode_lay.addWidget(dlg.rb_call_wait)
        mode_lay.addWidget(dlg.rb_call_parallel)
        mode_lay.addStretch(1)
        vbox.addWidget(mode_bg)
        
        # 기본 선택: 대기 후 실행
        dlg.rb_call_wait.setChecked(True)
        
        vbox.addStretch(1)
        lay.addWidget(gb)
        return w

    # --- 스타일 헬퍼 ---
    @staticmethod
    def _groupbox_style():
        return """
            QGroupBox { 
                font-size: 14px; 
                font-weight: bold; 
                color: #FFFFFF; 
                border: 1px solid rgba(255, 255, 255, 0.8); 
                border-radius: 6px; 
                margin-top: 22px; 
                padding-top: 10px; 
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """

    @staticmethod
    def _icon_btn(text, color, tooltip):
        btn = QPushButton(text)
        btn.setFixedSize(46, 45)
        btn.setToolTip(tooltip)
        btn.setStyleSheet(f"""
            QPushButton {{ background: rgba(255, 255, 255, 10); border: 1px solid {color}; border-radius: 6px; font-size: 14px; font-weight: bold; color: {color}; }}
            QPushButton:pressed {{ background: rgba(255, 255, 255, 30); }}
        """)
        return btn

    @staticmethod
    def _value_btn_style(color):
        return f"""
            QPushButton {{
                background: rgba(255,255,255,0.15); 
                border: 1px solid rgba(255,255,255,0.2); 
                border-radius: 4px; 
                color: {color}; 
                font-size: 14px; 
                font-weight: bold; 
                padding: 6px;
            }}
            QPushButton:pressed {{ background: rgba(255,255,255,0.3); }}
        """