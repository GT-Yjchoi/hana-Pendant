import os
import json
from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QListWidget, QListWidgetItem, QFrame, QDialog, QSizePolicy,
    QAbstractItemView, QMessageBox
)

from widgets.glass_card import GlassCard
from widgets.touch_keyboard import TouchKeyboard

# 매니저 모듈 임포트
try:
    from utils.io_manager import IOManager
except ImportError:
    IOManager = None
    print("X [PageData] IOManager Not Found!")

try:
    from utils.mode_manager import ModeManager
except ImportError:
    ModeManager = None
    print("X [PageData] ModeManager Not Found!")

try:
    from utils.languages import LanguageManager
except ImportError:
    LanguageManager = None


class GlassConfirmDialog(QDialog):
    def __init__(self, title, message, btn_yes=None, btn_no=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.resize(450, 250)
        
        lm = LanguageManager.instance() if LanguageManager else None
        
        txt_yes = btn_yes if btn_yes else (lm.get_text("btn_yes") if lm else "Yes")
        txt_no = btn_no if btn_no else (lm.get_text("btn_no") if lm else "No")
        
        if btn_yes == "확인" or btn_yes == "OK": 
             txt_yes = lm.get_text("btn_confirm") if lm else "OK"

        self.setStyleSheet("""
            QDialog { background: rgba(30, 35, 45, 250); border: 2px solid rgba(70, 140, 255, 120); border-radius: 14px; }
            QLabel#Title { color: #468CFF; font-size: 20px; font-weight: 900; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }
            QLabel#Message { color: white; font-size: 18px; font-weight: bold; line-height: 1.4; }
            QPushButton { border-radius: 8px; font-size: 16px; font-weight: bold; height: 50px; }
            QPushButton#Yes { background: rgba(70, 140, 255, 40); border: 1px solid rgba(70, 140, 255, 100); color: white; }
            QPushButton#Yes:pressed { background: rgba(70, 140, 255, 80); }
            QPushButton#No { background: rgba(255, 70, 70, 40); border: 1px solid rgba(255, 70, 70, 100); color: white; }
            QPushButton#No:pressed { background: rgba(255, 70, 70, 80); }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("Title")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_msg = QLabel(message)
        lbl_msg.setObjectName("Message")
        lbl_msg.setAlignment(Qt.AlignCenter)
        lbl_msg.setWordWrap(True)
        layout.addWidget(lbl_msg, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_no = QPushButton(txt_no)
        self.btn_no.setObjectName("No")
        self.btn_no.setCursor(Qt.PointingHandCursor)
        self.btn_no.clicked.connect(self.reject)
        
        self.btn_yes = QPushButton(txt_yes)
        self.btn_yes.setObjectName("Yes")
        self.btn_yes.setCursor(Qt.PointingHandCursor)
        self.btn_yes.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_no)
        btn_layout.addWidget(self.btn_yes)
        layout.addLayout(btn_layout)


class PageData(GlassCard):
    sig_file_loaded = Signal(str)

    def __init__(self, sequence_data=None, position_points=None, mode_data=None, view_order_data=None):
        # [수정] 타이틀 제거
        super().__init__("")
        
        # [수정] GlassCard 헤더 숨김
        if hasattr(self, 'title_label'):
            self.title_label.hide()
            if self.title_label.parentWidget() and self.title_label.parentWidget() != self:
                self.title_label.parentWidget().hide()

        if self.layout():
            # [수정] 상단 여백 최소화
            self.layout().setContentsMargins(10, 5, 10, 10)
        
        self.sequence_data = sequence_data if sequence_data is not None else {}
        if "Main" not in self.sequence_data:
            self.sequence_data["Main"] = []

        self.position_points = position_points if position_points is not None else {}
        self.mode_data = mode_data if mode_data is not None else []
        self.view_order_data = view_order_data if view_order_data is not None else []
        
        self.save_dir = "recipes"
        self.current_filename = None
        
        if not os.path.exists(self.save_dir):
            try:
                os.makedirs(self.save_dir)
            except OSError as e:
                print(f"[PageData] 디렉토리 생성 실패: {e}")

        self._init_ui()
        self._refresh_file_list()
        self.update_language()

    def _init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # [LEFT] 파일 목록
        left_layout = QVBoxLayout()
        self.left_header = QLabel(" 저장된 파일 목록")
        self.left_header.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        left_layout.addWidget(self.left_header)
        
        self.file_list = QListWidget()
        # [수정] 아이템 높이(65->45), 폰트(20->16) 줄여서 더 많이 보이게 함
        self.file_list.setStyleSheet("""
            QListWidget { background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; font-size: 16px; color: #EEE; outline: none; }
            QListWidget::item { height: 45px; padding-left: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); }
            QListWidget::item:selected { background: rgba(70, 140, 255, 0.25); border: 1px solid rgba(70, 140, 255, 0.6); border-radius: 6px; color: white; font-weight: bold; }
            QListWidget::item:hover { background: rgba(255, 255, 255, 0.05); }
        """)
        self.file_list.itemClicked.connect(self._on_file_selected)
        # 스크롤바 스타일링 (얇게)
        self.file_list.verticalScrollBar().setStyleSheet("QScrollBar:vertical { width: 12px; background: transparent; } QScrollBar::handle:vertical { background: rgba(255,255,255,0.2); border-radius: 6px; min-height: 40px; }")
        left_layout.addWidget(self.file_list)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # [RIGHT] 상세 정보 및 미리보기
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        
        self.lbl_info = QLabel("파일을 선택하면 상세 정보가 표시됩니다.")
        self.lbl_info.setStyleSheet("background: rgba(0,0,0,0.2); border-radius: 8px; color: #FFD280; font-size: 16px; font-weight: bold; padding: 10px;")
        self.lbl_info.setAlignment(Qt.AlignCenter)
        self.lbl_info.setFixedHeight(45)
        right_layout.addWidget(self.lbl_info)

        self.preview_header = QLabel("[X] 데이터 미리보기 (Step Preview)")
        self.preview_header.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 15px; margin-top: 5px;")
        right_layout.addWidget(self.preview_header)
        
        self.preview_list = QListWidget()
        # [수정] 미리보기 높이(45->32), 폰트(16->14) 줄여서 더 많은 내용 표시
        self.preview_list.setStyleSheet("""
            QListWidget { background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; font-size: 14px; color: #CCC; outline: none; }
            QListWidget::item { height: 32px; padding-left: 10px; border-bottom: 1px solid rgba(255,255,255,0.03); }
        """)
        self.preview_list.setSelectionMode(QListWidget.NoSelection)
        self.preview_list.verticalScrollBar().setStyleSheet("QScrollBar:vertical { width: 12px; background: transparent; } QScrollBar::handle:vertical { background: rgba(255,255,255,0.2); border-radius: 6px; }")
        right_layout.addWidget(self.preview_list, 1)

        # [버튼]
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        def mk_btn(text, color, icon_emoji):
            b = QPushButton(f"{icon_emoji}  {text}")
            b.setMinimumHeight(65) # 버튼 높이 약간 축소 (공간 확보)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{ background: rgba(255,255,255,0.05); border: 2px solid {color}; color: {color}; border-radius: 12px; font-weight: bold; font-size: 16px; }} 
                QPushButton:hover {{ background: {color}; color: black; }}
                QPushButton:pressed {{ background: rgba(255,255,255,0.3); }}
            """)
            return b
        
        self.btn_load = mk_btn("불러오기\n(LOAD)", "#64FF64", "")
        self.btn_new = mk_btn("새로만들기\n(NEW)", "#468CFF", "")
        self.btn_save = mk_btn("저장\n(SAVE)", "#FFD280", "")
        self.btn_del  = mk_btn("파일 삭제\n(DELETE)", "#FF4646", "")
        
        self.btn_load.clicked.connect(self._on_load_clicked)
        self.btn_new.clicked.connect(self._on_new_clicked)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_del.clicked.connect(self._on_del_clicked)
        
        btn_layout.addWidget(self.btn_load, 1)
        btn_layout.addWidget(self.btn_new, 1)
        btn_layout.addWidget(self.btn_save, 1)
        btn_layout.addWidget(self.btn_del, 1)
        
        right_layout.addLayout(btn_layout)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        main_layout.addWidget(left_widget, 4)
        main_layout.addWidget(right_widget, 6)
        self.body.addLayout(main_layout)

    def showEvent(self, event):
        self._refresh_file_list()
        super().showEvent(event)

    def set_current_filename(self, filename):
        if filename and filename != "No Data":
            self.current_filename = filename

    def auto_save(self):
        if not self.current_filename or self.current_filename == "No Data":
            return
        filepath = os.path.join(self.save_dir, f"{self.current_filename}.json")
        self._perform_save(filepath, self.current_filename, is_auto=True)

    def update_language(self, lang_code=None):
        if not LanguageManager: return
        lm = LanguageManager.instance()
        
        # [수정] 타이틀 업데이트 제거 (숨김 처리됨)
        # self.title_label.setText(...)
        
        self.left_header.setText(lm.get_text("data_list_header"))
        self.preview_header.setText(lm.get_text("data_preview_header"))
        if self.file_list.currentItem() is None:
            self.lbl_info.setText(lm.get_text("data_info_default"))
        self.btn_load.setText("  " + lm.get_text("btn_load_file"))
        self.btn_new.setText("  " + lm.get_text("btn_new_file"))
        self.btn_save.setText("  " + lm.get_text("btn_save_file"))
        self.btn_del.setText("  " + lm.get_text("btn_del_file"))

    def _refresh_file_list(self):
        self.file_list.clear()
        self.preview_list.clear()
        lm = LanguageManager.instance() if LanguageManager else None
        txt = lm.get_text("data_info_default") if lm else "파일을 선택하세요."
        self.lbl_info.setText(txt)
        
        if not os.path.exists(self.save_dir): return
        try:
            files = [f for f in os.listdir(self.save_dir) if f.endswith(".json")]
            files.sort()
            for f in files:
                item = QListWidgetItem(f[:-5])
                item.setData(Qt.UserRole, f)
                self.file_list.addItem(item)
        except OSError: pass

    def _on_file_selected(self, item):
        filename = item.data(Qt.UserRole)
        filepath = os.path.join(self.save_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            steps = []
            info_extra = ""
            
            seq_raw = []
            if isinstance(data, list):
                seq_raw = data
                info_extra = "(List Type)"
                steps = seq_raw
            elif isinstance(data, dict):
                seq_raw = data.get("sequence", [])
                if isinstance(seq_raw, list):
                    steps = seq_raw
                    info_extra = "(Single Seq)"
                elif isinstance(seq_raw, dict):
                    steps = seq_raw.get("Main", [])
                    seq_count = len(seq_raw.keys())
                    info_extra = f"(Multi Seq: {seq_count}개)"
                
            dt = datetime.fromtimestamp(os.path.getmtime(filepath))
            date_str = dt.strftime('%Y-%m-%d %H:%M')
            self.lbl_info.setText(f" {filename[:-5]}   |   {info_extra}   |   🕒 {date_str}")
            
            self.preview_list.clear()
            icons = {"POS": "[P]", "OUT": "[Y]", "IN": "[X]", "TMR": "[T]", "JMP": "[J]", "CALL": "[C]"}
            if steps:
                for i, step in enumerate(steps):
                    stype = step.get("type", "")
                    icon = icons.get(stype, "?")
                    name = step.get("name", "Unknown")
                    self.preview_list.addItem(f"[{i+1:02d}]  {icon}  {name}")
            else:
                self.preview_list.addItem("i (Empty or No Main Sequence)")
        except Exception as e:
            self.lbl_info.setText(f"X 오류: {e}")

    def _on_new_clicked(self):
        if "Main" not in self.sequence_data:
            self.sequence_data["Main"] = []
        if not isinstance(self.sequence_data["Main"], list):
            self.sequence_data["Main"] = []
            
        lm = LanguageManager.instance() if LanguageManager else None
        t_title = lm.get_text("title_new") if lm else "새로 만들기"
        t_msg = lm.get_text("msg_new_confirm") if lm else "데이터를 새로 만듭니다."
        
        confirm = GlassConfirmDialog(t_title, t_msg, parent=self)
        
        if confirm.exec() == QDialog.Accepted:
            dlg = TouchKeyboard("새 파일 이름 입력", parent=self)
            if hasattr(dlg, "set_language"): dlg.set_language("EN")
            elif hasattr(dlg, "set_layout"): dlg.set_layout("EN")
                
            if dlg.exec() == QDialog.Accepted:
                name = dlg.get_text()
                if not name: return
                safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-', '.')).strip()
                if not safe_name: return
                filename = f"{safe_name}.json"
                filepath = os.path.join(self.save_dir, filename)
                
                if os.path.exists(filepath):
                    t_dup = lm.get_text("title_dup") if lm else "중복 확인"
                    msg_dup = lm.get_text("msg_dup_confirm").format(safe_name) if lm else f"'{safe_name}' 중복. 덮어쓸까요?"
                    confirm_dup = GlassConfirmDialog(t_dup, msg_dup, parent=self)
                    if confirm_dup.exec() != QDialog.Accepted: return

                # ★ 기존 스텝 유지 (clear 제거)
                # self.sequence_data.clear()
                # self.sequence_data["Main"] = [{"type": "POS", "name": "원점 복귀", "coords": [0.0]*8, "speeds": [100]*8}]
                
                # ★ 현재 데이터를 그대로 새 파일로 저장
                # 만약 Main이 비어있으면 기본 스텝 추가
                if "Main" not in self.sequence_data or not self.sequence_data["Main"]:
                    self.sequence_data["Main"] = [{"type": "POS", "name": "원점 복귀", "point_name": "원점", "active_axes": [True]*8, "speeds": [100]*8}]
                
                self._perform_save(filepath, safe_name)

    def _on_save_clicked(self):
        lm = LanguageManager.instance() if LanguageManager else None
        
        if not self.current_filename or self.current_filename == "No Data":
            t_not = lm.get_text("title_notice") if lm else "알림"
            m_not = lm.get_text("msg_no_save_target") if lm else "저장할 대상이 없습니다."
            msg = GlassConfirmDialog(t_not, m_not, btn_yes=lm.get_text("btn_confirm") if lm else "확인", parent=self)
            msg.btn_no.hide()
            msg.exec()
            return

        t_sav = lm.get_text("title_save") if lm else "저장 확인"
        m_sav = lm.get_text("msg_save_confirm").format(self.current_filename) if lm else f"[{self.current_filename}] 에 저장?"
        confirm = GlassConfirmDialog(t_sav, m_sav, parent=self)
        
        if confirm.exec() == QDialog.Accepted:
            filename = f"{self.current_filename}.json"
            filepath = os.path.join(self.save_dir, filename)
            self._perform_save(filepath, self.current_filename)

    def _perform_save(self, filepath, display_name, is_auto=False):
        # POS 스텝에서 중복 필드(speeds, coords) 제거 후 저장
        clean_sequence = {}
        for seq_name, steps in self.sequence_data.items():
            clean_steps = []
            for step in steps:
                s = dict(step)
                if s.get("type") == "POS":
                    s.pop("speeds", None)
                    s.pop("coords", None)
                clean_steps.append(s)
            clean_sequence[seq_name] = clean_steps

        save_data = {
            "version": 1.4,
            "saved_at": str(datetime.now()),
            "sequence": clean_sequence,
            "position_points": self.position_points,
            "mode": self.mode_data,
            "view_order": self.view_order_data,
            "user_modes": ModeManager.instance().to_dict() if ModeManager else {}
        }

        lm = LanguageManager.instance() if LanguageManager else None

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4, ensure_ascii=False)
            
            if not is_auto:
                self._refresh_file_list()
                items = self.file_list.findItems(display_name, Qt.MatchExactly)
                if items:
                    self.file_list.setCurrentItem(items[0])
                    self._on_file_selected(items[0])

                self.current_filename = display_name
                self.sig_file_loaded.emit(display_name)

                t_done = lm.get_text("title_done") if lm else "완료"
                m_done = lm.get_text("msg_save_done") if lm else "저장되었습니다."
                msg = GlassConfirmDialog(t_done, m_done, btn_yes=lm.get_text("btn_confirm") if lm else "확인", parent=self)
                msg.btn_no.hide() 
                msg.exec()
            else:
                print(f"[AutoSave] Saved {display_name}.json")
            
        except Exception as e:
            if not is_auto:
                err = GlassConfirmDialog("Error", f"Save Failed:\n{e}", btn_yes="OK", parent=self)
                err.btn_no.hide()
                err.exec()
            else:
                print(f"[AutoSave] Error: {e}")

    def _on_load_clicked(self):
        item = self.file_list.currentItem()
        lm = LanguageManager.instance() if LanguageManager else None
        
        if not item:
            t_not = lm.get_text("title_notice") if lm else "알림"
            m_not = lm.get_text("msg_no_sel_load") if lm else "파일을 선택해주세요."
            msg = GlassConfirmDialog(t_not, m_not, btn_yes=lm.get_text("btn_confirm") if lm else "확인", parent=self)
            msg.btn_no.hide()
            msg.exec()
            return

        filename = item.data(Qt.UserRole)
        filepath = os.path.join(self.save_dir, filename)
        
        t_load = lm.get_text("title_load") if lm else "불러오기 확인"
        m_load = lm.get_text("msg_load_confirm").format(item.text()) if lm else f"'{item.text()}' 로드?"
        confirm = GlassConfirmDialog(t_load, m_load, parent=self)
        
        if confirm.exec() != QDialog.Accepted: return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                new_data = json.load(f)
            
            self.sequence_data.clear()
            
            if isinstance(new_data, list):
                self.sequence_data["Main"] = new_data
            elif isinstance(new_data, dict):
                seq_raw = new_data.get("sequence", [])
                if isinstance(seq_raw, list):
                    self.sequence_data["Main"] = seq_raw
                elif isinstance(seq_raw, dict):
                    self.sequence_data.update(seq_raw)
            
            if "Main" not in self.sequence_data:
                self.sequence_data["Main"] = []

            self.position_points.clear()
            pp = new_data.get("position_points", {})
            self.position_points.update(pp)
            
            self.view_order_data.clear()
            vo = new_data.get("view_order", [])
            self.view_order_data.extend(vo)
            
            mod = new_data.get("mode", [])
            for i, val in enumerate(mod):
                if i < len(self.mode_data):
                    self.mode_data[i] = val

            self.current_filename = item.text()
            self.sig_file_loaded.emit(item.text())

            if isinstance(new_data, dict):
                user_modes = new_data.get("user_modes")
                if user_modes and ModeManager:
                    ModeManager.instance().load_from_dict(user_modes)

            t_done = lm.get_text("title_done") if lm else "완료"
            m_done = lm.get_text("msg_load_done") if lm else "로드 완료."
            msg = GlassConfirmDialog(t_done, m_done, btn_yes=lm.get_text("btn_confirm") if lm else "확인", parent=self)
            msg.btn_no.hide()
            msg.exec()
        except Exception as e:
            err = GlassConfirmDialog("Error", f"Load Failed:\n{e}", btn_yes="OK", parent=self)
            err.btn_no.hide()
            err.exec()

    def _on_del_clicked(self):
        item = self.file_list.currentItem()
        lm = LanguageManager.instance() if LanguageManager else None
        
        if not item:
            t_not = lm.get_text("title_notice") if lm else "알림"
            m_not = lm.get_text("msg_no_sel_del") if lm else "선택해주세요."
            msg = GlassConfirmDialog(t_not, m_not, btn_yes=lm.get_text("btn_confirm") if lm else "확인", parent=self)
            msg.btn_no.hide()
            msg.exec()
            return 
        
        deleted_name = item.text()
        filename = item.data(Qt.UserRole)
        filepath = os.path.join(self.save_dir, filename)
        
        t_del = lm.get_text("title_del") if lm else "삭제 확인"
        m_del = lm.get_text("msg_del_confirm").format(deleted_name) if lm else f"'{deleted_name}' 삭제?"
        confirm = GlassConfirmDialog(t_del, m_del, parent=self)
        
        if confirm.exec() == QDialog.Accepted:
            try:
                os.remove(filepath)
                self._refresh_file_list() 
                self.preview_list.clear()
                self.lbl_info.setText(lm.get_text("msg_del_done") if lm else "삭제됨.")
                
                if self.current_filename == deleted_name:
                    self.current_filename = None
            except Exception as e:
                err = GlassConfirmDialog("Error", f"Delete Failed:\n{e}", btn_yes="OK", parent=self)
                err.btn_no.hide()
                err.exec()