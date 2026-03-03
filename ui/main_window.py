import json
import os
import sys
from datetime import datetime
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


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


# ============================================================
# 시퀀스 팝업 메시지 테이블 (w_SeqPopup 코드 → 제목, 메시지)
# PLC에서 w_SeqPopup에 아래 코드를 넣으면 해당 팝업이 표시됩니다.
# 키: 팝업 코드 (WORD, 1~65535)
# 값: (제목, 메시지) 튜플
# ============================================================
SEQ_POPUP_MESSAGES = {
    1: ("입력 대기 타임아웃",  "입력 신호를 받지 못했습니다.\n계속 대기하시겠습니까?"),
    2: ("도어 열림 경고",      "도어가 열려 있습니다.\n확인 후 계속하시겠습니까?"),
    3: ("공압 이상",           "공압이 낮습니다.\n계속하시겠습니까?"),
    # 여기에 코드와 메시지를 계속 추가하세요.
    # 예시: 4: ("온도 이상", "온도가 허용 범위를 초과했습니다.\n계속하시겠습니까?"),
}
# 딕셔너리에 없는 코드가 오면 표시될 기본 메시지
SEQ_POPUP_DEFAULT = ("시퀀스 팝업", "작업자 확인이 필요합니다.\n계속하시겠습니까?")


class MainWindow(QWidget):
    def __init__(self, plc_client=None):
        super().__init__()
        self.setObjectName("Root")
        self.setWindowTitle("HMI Program - Servo Control System")
        
        self.setFixedSize(1024, 600)
        
        # 전체 화면 모드
        self.showFullScreen() 

        # [PLC 클라이언트 설정]
        if plc_client:
            self.plc_client = plc_client
        else:
            self.plc_client = PLCClient() 

        self.base_path = get_base_path()
        if os.path.basename(self.base_path) == 'ui':
            self.base_path = os.path.dirname(self.base_path)
            
        self.settings_file = os.path.join(self.base_path, "settings.json")
        self.recipes_dir = os.path.join(self.base_path, "recipes")

        # 메인 레이아웃
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
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
                                    
                                    self.master_position_points.update(pp)
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

        if not self.master_sequence_data["Main"]:
             self.master_sequence_data["Main"].append(
                 {"type": "POS", "name": "원점 복귀 (Default)", "point_name": "Home", "coords": [0.0]*8, "speeds": [100]*8, "axes": [True]*8}
             )
             if "Home" not in self.master_position_points:
                 self.master_position_points["Home"] = {"coords": [0.0]*8}

        self.top_bar.set_mold_data(loaded_name)

        # ===== 3. Pages =====
        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        self.pages = {}
        self.page_keys = ["manual", "auto", "mode", "position", "timer", "packing", "data", "settings"]

        self.pages["manual"] = PageManual(plc_client=self.plc_client)
        self.pages["auto"] = PageAuto(plc_client=self.plc_client)
        
        self.pages["mode"] = PageMode(mode_data=self.master_mode_data, plc_client=self.plc_client)
        
        self.pages["position"] = PagePosition(
            sequence_data=self.master_sequence_data,
            view_order_data=self.master_view_order,
            position_points=self.master_position_points,
            plc_client=self.plc_client
        )
        
        self.pages["timer"] = PageTimer(
            sequence_data=self.master_sequence_data,
            plc_client=self.plc_client 
        )
        
        self.pages["data"] = PageData(
            sequence_data=self.master_sequence_data,
            position_points=self.master_position_points, 
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
        b_lay.setContentsMargins(14, 4, 14, 16)
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
        self.alarm_overlay = AlarmOverlay(self) # MainWindow(self)가 부모
        self.alarm_overlay.resize(self.size()) # 초기 크기 맞춤

        # 리셋 버튼 신호 연결 (모멘터리: 누를때 1, 뗄때 0)
        self.alarm_overlay.sig_reset_pressed.connect(self._on_alarm_reset_pressed)
        self.alarm_overlay.sig_reset_released.connect(self._on_alarm_reset_released)
        
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

        QTimer.singleShot(500, self._try_auto_connect)

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
        """PLC 연결 시 DT206~208에서 모드 설정 읽어 동기화"""
        if not connected:
            return
        QTimer.singleShot(200, self._sync_mode_from_plc)

    def _sync_mode_from_plc(self):
        """DT206~208 읽어 master_mode_data 및 모드 페이지 갱신"""
        if not self.plc_client or not self.plc_client.is_connected:
            return
        data = self.plc_client.read_mode_settings()
        if data and len(data) >= 44:
            self.master_mode_data[:44] = data[:44]
            page = self.pages.get("mode")
            if page:
                page.refresh_ui()
            print(f"[Mode] DT206~208 동기화 완료")

    # 조그 오버레이 실행 함수
    def _open_jog_overlay(self):
        dlg = JogControlDialog(plc_client=self.plc_client, parent=self)
        dlg.exec()

    def goto_page(self, key: str, index: int):
        self.stack.setCurrentIndex(index)
        for k, btn in self.nav_buttons.items():
            btn.set_active(k == key)

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
            data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data["last_recipe"] = filename
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[Main] Save settings error: {e}")

    def _on_sequence_updated(self):
        if "timer" in self.pages:
            self.pages["timer"].refresh_grid()
        self._auto_save_data()

    def _auto_save_data(self):
        if "data" in self.pages:
            self.pages["data"].auto_save()

    def _save_io_names_to_settings(self):
        try:
            data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            data["io_names"] = IOManager.instance().to_dict() if IOManager else {}
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
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
        self.plc_client.write_words(0x09, 212, [1])

    def _on_alarm_reset_released(self):
        self.plc_client.write_words(0x09, 212, [0])
        QTimer.singleShot(500, self._clear_alarm_reset_flag)

    def _clear_alarm_reset_flag(self):
        self._alarm_resetting = False

    # ★ [추가] 알람 상태 감시 함수
    def _check_alarm_status(self, data):
        # DT141: 축 알람 상태 워드 (비트별 축 알람)
        axis_alarms = data.get('axis_alarms', [])
        axis_error_codes = data.get('axis_error_codes', [0] * 8)
        if axis_alarms:
            key = tuple(axis_alarms) + tuple(axis_error_codes)
            if self.current_error_code != key:  # 알람 내용이 바뀔 때만 재표시
                self.current_error_code = key
                self.alarm_overlay.show_error(axis_alarms, axis_error_codes)
        else:
            if not self.alarm_overlay.isHidden() and not self._alarm_resetting:
                self.alarm_overlay.hide()
                self.current_error_code = None

        # DT159: 시퀀스 팝업 요청
        seq_popup = data.get('seq_popup', 0)
        if seq_popup > 0 and not getattr(self, '_seq_popup_showing', False):
            print(f"[Main] 시퀀스 팝업 요청 감지 (코드={seq_popup})")
            self._seq_popup_showing = True
            self._pending_seq_popup = seq_popup
            QTimer.singleShot(0, self._show_seq_popup)

    def _show_seq_popup(self):
        try:
            from ui.pages.page_auto import AutoConfirmOverlay
            code = getattr(self, '_pending_seq_popup', 1)
            title, message = SEQ_POPUP_MESSAGES.get(code, SEQ_POPUP_DEFAULT)
            dlg = AutoConfirmOverlay(title, message, self)
            result = dlg.exec()
            response = 1 if result else 2  # 1=계속, 2=정지
            print(f"[Main] 팝업 응답: {'계속' if response == 1 else '정지'} (코드={code}, DT160={response})")
            if self.plc_client:
                self.plc_client.write_words(0x09, 160, [response])
        except Exception as e:
            print(f"[Main] 시퀀스 팝업 오류: {e}")
        finally:
            self._seq_popup_showing = False
            self._pending_seq_popup = 0

