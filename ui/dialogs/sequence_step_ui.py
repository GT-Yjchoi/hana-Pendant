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
        vbox.setSpacing(12)
        vbox.setContentsMargins(10, 20, 10, 10)
        
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
        
        # ★ IN 스텝 전용: 타임아웃 설정
        dlg.in_timeout_frame = QWidget()
        timeout_layout = QVBoxLayout(dlg.in_timeout_frame)
        timeout_layout.setContentsMargins(0, 10, 0, 0)
        timeout_layout.setSpacing(8)

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
        dlg.timeout_btn.setFixedHeight(45)
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
        action_layout.setSpacing(4)
        
        dlg.rb_timeout_ask = QRadioButton("팝업 띄우기 (작업자 선택)")
        dlg.rb_timeout_continue = QRadioButton("계속 대기")
        dlg.rb_timeout_stop = QRadioButton("시퀀스 정지")
        dlg.rb_timeout_jump = QRadioButton("특정 스텝으로 점프")
        
        dlg.timeout_action_grp = QButtonGroup(w)
        dlg.timeout_action_grp.addButton(dlg.rb_timeout_ask)
        dlg.timeout_action_grp.addButton(dlg.rb_timeout_continue)
        dlg.timeout_action_grp.addButton(dlg.rb_timeout_stop)
        dlg.timeout_action_grp.addButton(dlg.rb_timeout_jump)
        
        for rb in [dlg.rb_timeout_ask, dlg.rb_timeout_continue, dlg.rb_timeout_stop, dlg.rb_timeout_jump]:
            rb.toggled.connect(dlg._on_io_value_changed)
        
        action_layout.addWidget(dlg.rb_timeout_ask)
        action_layout.addWidget(dlg.rb_timeout_continue)
        action_layout.addWidget(dlg.rb_timeout_stop)
        action_layout.addWidget(dlg.rb_timeout_jump)
        
        timeout_layout.addWidget(action_widget)
        
        # ★ 점프 타겟 선택 (rb_timeout_jump 선택 시만 표시)
        dlg.timeout_jump_frame = QWidget()
        jump_layout = QVBoxLayout(dlg.timeout_jump_frame)
        jump_layout.setContentsMargins(20, 0, 0, 0)  # ★ 위 여백 제거
        jump_layout.setSpacing(0)
        
        # ★ "점프할 스텝" 라벨 제거
        
        dlg.timeout_jump_btn = QPushButton("선택하세요")
        dlg.timeout_jump_btn.setFixedHeight(35)  # ★ 높이 줄임 (40 → 35)
        dlg.timeout_jump_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid #888;
                border-radius: 4px;
                color: white;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:pressed { background: rgba(255, 255, 255, 0.2); }
        """)
        dlg.timeout_jump_btn.clicked.connect(dlg._open_timeout_jump_selector)
        jump_layout.addWidget(dlg.timeout_jump_btn)
        
        # 숨겨진 콤보박스 (데이터 저장용)
        dlg.timeout_jump_combo = TouchComboBox()
        dlg.timeout_jump_combo.hide()
        dlg.timeout_jump_combo.currentIndexChanged.connect(dlg._on_io_value_changed)
        
        timeout_layout.addWidget(dlg.timeout_jump_frame)
        dlg.timeout_jump_frame.setVisible(False)  # 기본 숨김
        
        # ★ 점프 라디오 버튼 토글 시 프레임 표시/숨김
        dlg.rb_timeout_jump.toggled.connect(
            lambda checked: dlg.timeout_jump_frame.setVisible(checked)
        )
        
        # 기본 선택
        dlg.rb_timeout_ask.setChecked(True)
        
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
        vbox.setSpacing(12)
        vbox.setContentsMargins(10, 20, 10, 10)
        vbox.addWidget(QLabel("대기 시간 (초)"))
        
        dlg.tmr_btn = QPushButton("1.0 sec")
        dlg.tmr_btn.setFixedHeight(50)
        dlg.tmr_btn.setStyleSheet(StepUIGenerator._value_btn_style("#FFFFFF"))
        dlg.tmr_btn.clicked.connect(dlg._on_tmr_edit_clicked)
        
        vbox.addWidget(dlg.tmr_btn)
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
        
        # ★ 조건 타입 선택 (입력/내부비트, 모드만 남김)
        src_bg = QWidget()
        src_lay = QHBoxLayout(src_bg)
        src_lay.setContentsMargins(0, 0, 0, 0)
        dlg.rb_src_port = QRadioButton("입력/내부비트")
        dlg.rb_src_mode = QRadioButton("모드")
        
        dlg.src_grp = QButtonGroup(w)
        dlg.src_grp.addButton(dlg.rb_src_port)
        dlg.src_grp.addButton(dlg.rb_src_mode)
        
        for rb in [dlg.rb_src_port, dlg.rb_src_mode]:
            rb.toggled.connect(dlg._on_jmp_value_changed)
            
        src_lay.addWidget(dlg.rb_src_port)
        src_lay.addWidget(dlg.rb_src_mode)
        src_lay.addStretch(1)
        fl.addWidget(src_bg)
        
        dlg.stack_cond_source = QStackedWidget()
        
        # ★ 1. 입력/내부비트 - 버튼으로 변경
        dlg.jmp_port_btn = QPushButton("선택하세요")
        dlg.jmp_port_btn.setFixedHeight(45)
        dlg.jmp_port_btn.setStyleSheet("""
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
        dlg.jmp_port_btn.clicked.connect(dlg._open_jmp_port_selector)
        
        # 숨겨진 콤보박스 (데이터 저장용)
        dlg.jmp_port_combo = TouchComboBox()
        dlg.jmp_port_combo.hide()
        dlg.jmp_port_combo.currentIndexChanged.connect(dlg._on_jmp_value_changed)
        
        port_widget = QWidget()
        port_lay = QVBoxLayout(port_widget)
        port_lay.setContentsMargins(0, 0, 0, 0)
        port_lay.addWidget(dlg.jmp_port_btn)
        port_lay.addWidget(dlg.jmp_port_combo)
        
        dlg.stack_cond_source.addWidget(port_widget)
        
        # ★ 2. 모드 - 버튼으로 변경
        dlg.jmp_mode_btn = QPushButton("선택하세요")
        dlg.jmp_mode_btn.setFixedHeight(45)
        dlg.jmp_mode_btn.setStyleSheet("""
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
        dlg.jmp_mode_btn.clicked.connect(dlg._open_jmp_mode_selector)
        
        # 숨겨진 콤보박스 (데이터 저장용)
        dlg.jmp_mode_combo = TouchComboBox()
        dlg.jmp_mode_combo.hide()
        dlg.jmp_mode_combo.currentIndexChanged.connect(dlg._on_jmp_value_changed)
        
        mode_widget = QWidget()
        mode_lay = QVBoxLayout(mode_widget)
        mode_lay.setContentsMargins(0, 0, 0, 0)
        mode_lay.addWidget(dlg.jmp_mode_btn)
        mode_lay.addWidget(dlg.jmp_mode_combo)
        
        dlg.stack_cond_source.addWidget(mode_widget)
        
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