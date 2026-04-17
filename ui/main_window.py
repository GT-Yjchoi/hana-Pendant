import json
import os
import sys
from datetime import datetime
from utils.paths import get_settings_path, get_recipes_dir
from utils.json_utils import load_json, save_json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QSizePolicy
)

from widgets.nav_button import NavButton
from ui.top_bar import TopBar

# 페이지들 임포트
from ui.pages.page_mode import PageMode
from ui.pages.page_position import PagePosition
from ui.pages.page_timer import PageTimer
from ui.pages.page_packing import PagePacking
from ui.pages.page_data import PageData
from ui.pages.page_manual import PageManual
from ui.pages.page_auto import PageAuto
from ui.pages.page_settings import PageSettings

# [조그 오버레이 임포트]
from ui.dialogs.jog_control_dialog import JogControlDialog

# ★ [추가] 알람 오버레이 임포트
from ui.overlays.alarm_overlay import AlarmOverlay

# 유틸리티 임포트
from utils.plc_client import PLCClient

try:
    from utils.gpio_estop import GpioEstop
except ImportError:
    GpioEstop = None 

try:
    from utils.languages import LanguageManager
except ImportError:
    LanguageManager = None

try:
    from utils.io_manager import IOManager
except ImportError:
    IOManager = None

try:
    from utils.mode_manager import ModeManager
except ImportError:
    ModeManager = None


# ============================================================
# 시퀀스 팝업 메시지 테이블 (w_SeqPopup 코드 → 제목, 메시지)
# PLC에서 w_SeqPopup에 아래 코드를 넣으면 해당 팝업이 표시됩니다.
# 키: 팝업 코드 (WORD, 1~65535)
# 값: (제목, 메시지) 튜플
# ============================================================


class MainWindow(QWidget):
    def __init__(self, plc_client=None):
        super().__init__()
        self.setObjectName("Root")
        self.setWindowTitle("HMI Program - Servo Control System")
        
        # 전체 화면 모드 (main.py에서 showFullScreen() 호출)


        # [PLC 클라이언트 설정]
        if plc_client:
            self.plc_client = plc_client
        else:
            self.plc_client = PLCClient() 

        self.settings_file = get_settings_path()
        self.recipes_dir = get_recipes_dir()

        # 메인 레이아웃
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 10)
        root.setSpacing(12)

        # ===== 1. Top Bar =====
        self.top_bar = TopBar()
        root.addWidget(self.top_bar)

        # PLC 통신 상태를 TopBar와 연결
        self.plc_client.sig_connected.connect(self.top_bar.set_comm_status)
        self.plc_client.sig_connected.connect(self._on_plc_connected)
        self.top_bar.set_comm_status(self.plc_client.is_connected)
        
        # PLC 모니터링 데이터 연결 (TopBar 갱신용)
        self.plc_client.sig_monitor_data.connect(self.top_bar._on_monitor_data)
        
        # TopBar의 JOG 버튼 클릭 시 오버레이 실행 연결
        self.top_bar.sig_jog_clicked.connect(self._open_jog_overlay)

        # TopBar의 알람 텍스트 클릭 시 오버레이 재표시
        self.top_bar.sig_alarm_clicked.connect(self._show_alarm_overlay)

        # ===== 2. Shared Data =====
        self.master_sequence_data = {"Main": []}
        self.master_position_points = {}
        self.master_timer_library = {}
        self.master_mode_data = [False] * 40
        self.master_view_order = []

        self.current_recipe_name = None

        # [자동 로드]
        loaded_name = "No Data"
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    last_recipe = settings.get("last_recipe")

                    # IO 이름은 settings.json에서 로드 (레시피 무관)
                    io_data = settings.get("io_names")
                    if io_data and IOManager:
                        IOManager.instance().load_from_dict(io_data)

                    if last_recipe:
                        recipe_path = os.path.join(self.recipes_dir, f"{last_recipe}.json")
                        if os.path.exists(recipe_path):
                            with open(recipe_path, 'r', encoding='utf-8') as rf:
                                data = json.load(rf)
                                
                                seq_raw = {}
                                if isinstance(data, list):
                                    seq_raw = {"Main": data}
                                elif isinstance(data, dict):
                                    temp_seq = data.get("sequence", [])
                                    if isinstance(temp_seq, list):
                                        seq_raw = {"Main": temp_seq}
                                    elif isinstance(temp_seq, dict):
                                        seq_raw = temp_seq
                                
                                self.master_sequence_data.clear()
                                self.master_sequence_data.update(seq_raw)
                                if "Main" not in self.master_sequence_data:
                                    self.master_sequence_data["Main"] = []

                                if isinstance(data, dict):
                                    pp = data.get("position_points", {})
                                    mod = data.get("mode", [])
                                    vo = data.get("view_order", [])
                                    tl = data.get("timer_library", {})

                                    self.master_position_points.update(pp)
                                    self.master_timer_library.update(tl)
                                    self.master_mode_data[:len(mod)] = mod
                                    self.master_view_order.extend(vo)

                                    user_modes = data.get("user_modes")
                                    if user_modes and ModeManager:
                                        ModeManager.instance().load_from_dict(user_modes)
                                            
                                    loaded_name = last_recipe
                                    self.current_recipe_name = last_recipe
                                    print(f"[Init] Auto-loaded recipe: {last_recipe}")
            except Exception as e:
                print(f"[Init] Load error: {e}")

        # settings.json의 point_visibility로 레시피 visible_mode 오버라이드
        self._apply_point_visibility_from_settings()

        if not self.master_sequence_data["Main"]:
             self.master_sequence_data["Main"].append(
                 {"type": "POS", "name": "원점 복귀 (Default)", "point_name": "Home", "coords": [0.0]*8, "speeds": [100]*8, "axes": [True]*8}
             )
             if "Home" not in self.master_position_points:
                 self.master_position_points["Home"] = {"coords": [0.0]*8}

        self.top_bar.set_mold_data(loaded_name)

        # ===== 3. Pages =====
        self.stack = QStackedWidget()
        self.stack.setMinimumHeight(0)
        root.addWidget(self.stack, 1)

        self.pages = {}
        self.page_keys = ["manual", "auto", "mode", "position", "timer", "packing", "data", "settings"]

        self.pages["manual"] = PageManual(plc_client=self.plc_client)
        self.pages["auto"] = PageAuto(plc_client=self.plc_client)
        
        self.pages["mode"] = PageMode(mode_data=self.master_mode_data, plc_client=self.plc_client)
        
        self.pages["position"] = PagePosition(
            sequence_data=self.master_sequence_data,
            view_order_data=self.master_view_order,
            position_points=self.master_position_points,
            mode_data=self.master_mode_data,
            timer_library=self.master_timer_library,
            plc_client=self.plc_client
        )

        self.pages["timer"] = PageTimer(
            sequence_data=self.master_sequence_data,
            timer_library=self.master_timer_library,
            plc_client=self.plc_client
        )

        self.pages["data"] = PageData(
            sequence_data=self.master_sequence_data,
            position_points=self.master_position_points,
            timer_library=self.master_timer_library,
            mode_data=self.master_mode_data,
            view_order_data=self.master_view_order
        )
        
        self.pages["packing"] = PagePacking()
        self.pages["settings"] = PageSettings() 

        self.pages["data"].sig_file_loaded.connect(self._on_recipe_loaded)
        self.pages["position"].sig_sequence_changed.connect(self._on_sequence_updated)

        for key in self.page_keys:
            self.stack.addWidget(self.pages[key])

        if loaded_name != "No Data":
            self.pages["data"].set_current_filename(loaded_name)

        # ===== 4. Bottom Bar =====
        bottom = QFrame()
        bottom.setObjectName("BottomBar")
        bottom.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom.setMinimumHeight(70)
        
        b_lay = QHBoxLayout(bottom)
        b_lay.setContentsMargins(14, 4, 14, 4)
        b_lay.setSpacing(10)

        self.nav_buttons = {}

        def add_nav(page_key: str, text_key: str, index: int):
            initial_text = text_key
            if LanguageManager:
                initial_text = LanguageManager.instance().get_text(text_key)
                
            btn = NavButton(initial_text)
            btn.clicked.connect(lambda: self.goto_page(page_key, index))
            btn.setProperty("text_key", text_key)
            
            self.nav_buttons[page_key] = btn
            b_lay.addWidget(btn)

        add_nav("manual",   "nav_manual", 0)
        add_nav("auto",     "nav_auto",   1)
        add_nav("mode",     "nav_mode",   2)
        add_nav("position", "nav_pos",    3)
        add_nav("timer",    "nav_timer",  4)
        add_nav("packing",  "nav_packing",5)
        add_nav("data",     "nav_data",   6)
        add_nav("settings", "nav_setting",7)

        root.addWidget(bottom)
        self.goto_page("manual", 0)

        # =========================================================
        # ★ [추가] 5. Alarm Overlay (항상 최상단)
        # =========================================================
        self.current_error_code = None
        self._alarm_resetting = False
        self._seq_alarm_showing = False
        self._jog_dialog = None
        self._prev_op_status = 0
        self._seq_alarm_no = 0
        self.alarm_overlay = AlarmOverlay(self) # MainWindow(self)가 부모
        self.alarm_overlay.resize(self.size()) # 초기 크기 맞춤

        # 리셋 버튼 신호 연결 (모멘터리: 누를때 1, 뗄때 0)
        self.alarm_overlay.sig_reset_pressed.connect(self._on_alarm_reset_pressed)
        self.alarm_overlay.sig_reset_released.connect(self._on_alarm_reset_released)
        self.alarm_overlay.sig_dismissed.connect(self._on_alarm_dismissed)
        
        # PLC 데이터 감시 연결 (알람 체크용)
        if self.plc_client:
            self.plc_client.sig_monitor_data.connect(self._check_alarm_status)
        # =========================================================

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self._auto_save_data)
        self.auto_save_timer.start(60000) 

        if LanguageManager:
            LanguageManager.instance().sig_lang_changed.connect(self.update_language)

        if IOManager:
            IOManager.instance().sig_names_changed.connect(self._save_io_names_to_settings)
        if ModeManager:
            ModeManager.instance().sig_names_changed.connect(self._auto_save_data)

        # GPIO 비상정지 모니터
        self._gpio_estop = None
        if GpioEstop:
            self._gpio_estop = GpioEstop(self)
            self._gpio_estop.sig_estop.connect(self._on_gpio_estop)
            self._gpio_estop.start()

        QTimer.singleShot(500, self._try_auto_connect)

    def _on_gpio_estop(self, active):
        """GPIO22 비상정지 신호 → DT213 전송 + 알람 팝업"""
        self._gpio_estop_active = active
        if self.plc_client and self.plc_client.is_connected:
            self.plc_client.send_soft_estop(active)
        if active:
            # X0 비상정지와 동일한 팝업 표시 (axis_alarm 9 = 비상정지)
            self.alarm_overlay.show_error([9], [0] * 8)
        else:
            # 해제 시 팝업 닫기 (알람 리셋 중이 아닐 때)
            if not self._alarm_resetting and not self._seq_alarm_showing:
                self.alarm_overlay.hide()
                self.current_error_code = None

    def closeEvent(self, event):
        """앱 종료 시 GPIO 정리"""
        if self._gpio_estop:
            self._gpio_estop.stop()
        super().closeEvent(event)

    def _try_auto_connect(self):
        """설정 파일에서 IP/Port를 읽어와 자동 연결 시도"""
        if self.plc_client.is_connected:
            return

        target_ip = "192.168.0.10"
        target_port = 8501

        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    target_ip = settings.get("plc_ip", target_ip)
                    target_port = int(settings.get("plc_port", target_port))
            except Exception as e:
                print(f"[AutoConnect] Settings read error: {e}")

        print(f"[Auto Connect] Connecting to {target_ip}:{target_port}...")
        self.plc_client.connect_to_plc(target_ip, target_port)

    def _on_plc_connected(self, connected: bool):
        """PLC 연결/해제 시 처리"""
        if connected:
            self.alarm_overlay.hide_comm_error()
            QTimer.singleShot(200, self._send_mode_to_plc)
        else:
            if not self._alarm_resetting and not self._seq_alarm_showing:
                self.alarm_overlay.show_comm_error()

    def _send_mode_to_plc(self):
        """master_mode_data → DT206~208 전송 (재부팅 후 PLC 동기화)"""
        if not self.plc_client or not self.plc_client.is_connected:
            return
        self.plc_client.send_mode_settings(self.master_mode_data)
        print(f"[Mode] PLC 연결 후 모드 설정 전송 완료")

    # 조그 오버레이 실행 함수
    def _open_jog_overlay(self):
        if self.top_bar.op_status in (1, 2):
            return  # 자동운전 / 확인운전 중에는 JOG 차단
        page_manual = self.pages.get("manual")
        self._jog_dialog = JogControlDialog(plc_client=self.plc_client, page_manual=page_manual, parent=self)
        self._jog_dialog.exec()
        self._jog_dialog = None

    def goto_page(self, key: str, index: int):
        if key == "settings":
            if self.stack.currentIndex() == index:
                return
            self._request_settings_password(index)
            return
        self.stack.setCurrentIndex(index)
        for k, btn in self.nav_buttons.items():
            btn.set_active(k == key)

    def _request_settings_password(self, index: int):
        try:
            from ui.dialogs.sequence_utils import NumericKeypad, DarkMessageDialog
            dlg = NumericKeypad("설정 비밀번호를 입력하세요", decimals=0, parent=self, password_mode=True)
            if dlg.exec() == 1:
                val = int(dlg.get_value())
                if val == 2026:
                    self.stack.setCurrentIndex(index)
                    for k, btn in self.nav_buttons.items():
                        btn.set_active(k == "settings")
                else:
                    err_dlg = DarkMessageDialog("비밀번호 오류", "비밀번호가 올바르지 않습니다.", is_error=True, parent=self)
                    err_dlg.exec()
        except Exception as e:
            print(f"[Settings] Password dialog error: {e}")

    def update_language(self, lang_code):
        if not LanguageManager: return
        lm = LanguageManager.instance()
        for key, btn in self.nav_buttons.items():
            text_key = btn.property("text_key")
            if text_key:
                btn.setText(lm.get_text(text_key))
                
        for page in self.pages.values():
            if hasattr(page, "update_language"):
                page.update_language(lang_code)

    def _on_recipe_loaded(self, filename):
        self.current_recipe_name = filename
        self.top_bar.set_mold_data(filename)

        # 새 레시피 로드 후 settings.json의 point_visibility 오버라이드 적용
        self._apply_point_visibility_from_settings()

        if "mode" in self.pages:
            self.pages["mode"].refresh_ui()
        if "position" in self.pages:
            self.pages["position"]._refresh_ui()
        if "timer" in self.pages:
            self.pages["timer"].refresh_grid()

        if self.plc_client and self.plc_client.is_connected:
            self.plc_client.send_mode_settings(self.master_mode_data)
            print(f"[Mode] 레시피 '{filename}' 모드 → DT206~208 전송")
        
        try:
            data = load_json(self.settings_file) or {}
            data["last_recipe"] = filename
            save_json(self.settings_file, data)
        except Exception as e:
            print(f"[Main] Save settings error: {e}")

    def _on_sequence_updated(self):
        if "timer" in self.pages:
            self.pages["timer"].refresh_grid()
        self._save_point_visibility_to_settings()
        self._auto_save_data()

    def _auto_save_data(self):
        if "data" in self.pages:
            self.pages["data"].auto_save()

    def _apply_point_visibility_from_settings(self):
        """settings.json의 point_visibility를 master_position_points에 적용 (settings 우선)"""
        try:
            data = load_json(self.settings_file) or {}
            pv = data.get("point_visibility", {})
            for pt_name, vm in pv.items():
                if pt_name in self.master_position_points:
                    self.master_position_points[pt_name]["visible_mode"] = vm
        except Exception as e:
            print(f"[Main] point_visibility load error: {e}")

    def _save_point_visibility_to_settings(self):
        """master_position_points의 visible_mode를 settings.json에 저장"""
        try:
            data = load_json(self.settings_file) or {}
            data["point_visibility"] = {
                name: pt["visible_mode"]
                for name, pt in self.master_position_points.items()
                if "visible_mode" in pt
            }
            save_json(self.settings_file, data)
        except Exception as e:
            print(f"[Main] point_visibility save error: {e}")

    def _save_io_names_to_settings(self):
        try:
            data = load_json(self.settings_file) or {}
            data["io_names"] = IOManager.instance().to_dict() if IOManager else {}
            save_json(self.settings_file, data)
        except Exception as e:
            print(f"[Main] IO names save error: {e}")

    # ★ [추가] 창 크기 변경 이벤트 (오버레이 크기 동기화)
    def resizeEvent(self, event):
        if hasattr(self, 'alarm_overlay'):
            self.alarm_overlay.resize(self.size())
        super().resizeEvent(event)

    def _show_alarm_overlay(self):
        """TopBar 알람 텍스트 클릭 시 오버레이 재표시"""
        if self.current_error_code:
            self.alarm_overlay.show()
            self.alarm_overlay.raise_()

    def _on_alarm_reset_pressed(self):
        self._alarm_resetting = True
        self.plc_client.write_words(0x09, self.plc_client.ADDR_ALARM_RESET, [1])

    def _on_alarm_reset_released(self):
        self.plc_client.write_words(0x09, self.plc_client.ADDR_ALARM_RESET, [0])
        # 시퀀스 알람(DT159) 클리어 및 즉시 숨김
        if getattr(self, '_seq_alarm_showing', False):
            self.plc_client.write_words(0x09, self.plc_client.ADDR_SEQ_POPUP, [0])
            self._seq_alarm_showing = False
            self._seq_alarm_no = 0
            self.alarm_overlay.hide()
        QTimer.singleShot(500, self._clear_alarm_reset_flag)

    def _clear_alarm_reset_flag(self):
        self._alarm_resetting = False

    def _on_alarm_dismissed(self):
        """X버튼으로 알람 닫을 때 플래그 리셋 → 다음 알람 수신 가능"""
        self._seq_alarm_showing = False
        self._seq_alarm_no = 0

    # ★ [추가] 알람 상태 감시 함수
    def _check_alarm_status(self, data):
        op_status = data.get('op_status', 0)

        # 자동/확인운전 시작 시 JOG 팝업 강제 종료
        if op_status in (1, 2):
            if getattr(self, '_jog_dialog', None) is not None:
                self._jog_dialog.close_overlay()

        self._prev_op_status = op_status

        # DT141: 축 알람 상태 워드 (비트별 축 알람)
        axis_alarms = data.get('axis_alarms', [])
        axis_error_codes = data.get('axis_error_codes', [0] * 8)
        if axis_alarms:
            key = tuple(axis_alarms) + tuple(axis_error_codes)
            if self.current_error_code != key:  # 알람 내용이 바뀔 때만 재표시
                self.current_error_code = key
                self.alarm_overlay.show_error(axis_alarms, axis_error_codes)
        else:
            if not self.alarm_overlay.isHidden() and not self._alarm_resetting and not self._seq_alarm_showing and not getattr(self, '_gpio_estop_active', False):
                self.alarm_overlay.hide()
                self.current_error_code = None

        # DT159: 시퀀스 알람 요청 (alarm_no, bit15=알람+진행 플래그)
        seq_popup = data.get('seq_popup', 0)
        if seq_popup > 0 and not self._seq_alarm_showing:
            alarm_go = seq_popup >= 1000               # 1000 이상 → 알람+진행
            alarm_no = seq_popup - 1000 if alarm_go else seq_popup  # 실제 알람 번호
            print(f"[Main] 시퀀스 알람 요청 (alarm_no={alarm_no}, alarm_go={alarm_go})")
            self._seq_alarm_showing = True
            self._seq_alarm_no = alarm_no
            # 즉시 DT159 클리어 (핸드셰이크) → 재트리거 방지
            self.plc_client.write_words(0x09, self.plc_client.ADDR_SEQ_POPUP, [0])
            # DT200/DT202는 PLC FB(VAR_IN_OUT)가 직접 처리 → HMI는 팝업 표시만
            self.alarm_overlay.show_sequence_alarm(alarm_no)

