from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QWidget, QGridLayout, QSizePolicy, QStackedWidget, QFrame,
    QApplication
)

# =========================================================
# [핵심] 한글 오토마타 클래스
# =========================================================
class HangulComposer:
    BASE_CODE = 0xAC00
    CHOSUNG_BASE = 0x1100
    JUNGSUNG_BASE = 0x1161
    JONGSUNG_BASE = 0x11A7

    CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    JUNGSUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
    JONGSUNG_LIST = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

    DOUBLE_JUNG_MAP = {(8, 0): 9, (8, 1): 10, (8, 20): 11, (13, 4): 14, (13, 5): 15, (13, 20): 16, (18, 20): 19}
    DOUBLE_JONG_MAP = {(1, 19): 3, (4, 22): 5, (4, 27): 6, (8, 1): 9, (8, 16): 10, (8, 17): 11, (8, 19): 12, (8, 25): 13, (8, 26): 14, (8, 27): 15, (17, 19): 18}
    DOUBLE_JONG_SPLIT = {3: (1, 9), 5: (4, 12), 6: (4, 18), 9: (8, 0), 10: (8, 6), 11: (8, 7), 12: (8, 9), 13: (8, 16), 14: (8, 17), 15: (8, 18), 18: (17, 9)}

    def __init__(self):
        self.cho = -1
        self.jung = -1
        self.jong = 0
        self.completed_text = ""

    def _get_char(self, c, j, k):
        if c < 0: return ""
        if j < 0: return self.CHOSUNG_LIST[c]
        return chr(self.BASE_CODE + (c * 21 * 28) + (j * 28) + k)

    def input_char(self, char):
        if char in self.CHOSUNG_LIST:
            idx = self.CHOSUNG_LIST.index(char)
            if self.cho < 0: self.cho = idx
            elif self.jung < 0:
                self.completed_text += self.CHOSUNG_LIST[self.cho]
                self.cho = idx
            elif self.jong == 0:
                try:
                    jong_idx = self.JONGSUNG_LIST.index(char)
                    self.jong = jong_idx
                except:
                    self.completed_text += self._get_char(self.cho, self.jung, 0)
                    self.cho = idx; self.jung = -1; self.jong = 0
            else:
                try:
                    next_jong = self.JONGSUNG_LIST.index(char)
                    if (self.jong, next_jong) in self.DOUBLE_JONG_MAP:
                        self.jong = self.DOUBLE_JONG_MAP[(self.jong, next_jong)]
                    else:
                        self.completed_text += self._get_char(self.cho, self.jung, self.jong)
                        self.cho = idx; self.jung = -1; self.jong = 0
                except:
                    self.completed_text += self._get_char(self.cho, self.jung, self.jong)
                    self.cho = idx; self.jung = -1; self.jong = 0

        elif char in self.JUNGSUNG_LIST:
            idx = self.JUNGSUNG_LIST.index(char)
            if self.cho < 0: self.completed_text += char
            elif self.jung < 0: self.jung = idx
            elif self.jong == 0:
                if (self.jung, idx) in self.DOUBLE_JUNG_MAP:
                    self.jung = self.DOUBLE_JUNG_MAP[(self.jung, idx)]
                else:
                    self.completed_text += self._get_char(self.cho, self.jung, 0)
                    self.cho = -1; self.jung = -1; self.completed_text += char
            else:
                if self.jong in self.DOUBLE_JONG_SPLIT:
                    prev_jong, next_cho_idx = self.DOUBLE_JONG_SPLIT[self.jong]
                    self.completed_text += self._get_char(self.cho, self.jung, prev_jong)
                    self.cho = next_cho_idx; self.jung = idx; self.jong = 0
                else:
                    current_jong_char = self.JONGSUNG_LIST[self.jong]
                    try:
                        next_cho = self.CHOSUNG_LIST.index(current_jong_char)
                        self.completed_text += self._get_char(self.cho, self.jung, 0)
                        self.cho = next_cho; self.jung = idx; self.jong = 0
                    except:
                        self.completed_text += self._get_char(self.cho, self.jung, self.jong)
                        self.cho = -1; self.jung = -1; self.completed_text += char

        return self.get_full_text()

    def backspace(self):
        if self.jong > 0:
            found_double = False
            for k, v in self.DOUBLE_JONG_MAP.items():
                if v == self.jong:
                    self.jong = k[0]; found_double = True; break
            if not found_double: self.jong = 0
        elif self.jung >= 0:
            found_double = False
            for k, v in self.DOUBLE_JUNG_MAP.items():
                if v == self.jung:
                    self.jung = k[0]; found_double = True; break
            if not found_double: self.jung = -1
        elif self.cho >= 0: self.cho = -1
        else:
            if len(self.completed_text) > 0:
                last_char = self.completed_text[-1]
                self.completed_text = self.completed_text[:-1]
                code = ord(last_char)
                if 0xAC00 <= code <= 0xD7A3:
                    code -= 0xAC00
                    last_jong = code % 28; code //= 28
                    last_jung = code % 21; last_cho = code // 21
                    self.cho = last_cho; self.jung = last_jung; self.jong = last_jong
        return self.get_full_text()

    def commit(self):
        self.completed_text = self.get_full_text()
        self.cho = -1; self.jung = -1; self.jong = 0

    def get_full_text(self):
        current = self._get_char(self.cho, self.jung, self.jong)
        return self.completed_text + current


# =========================================================
# [UI] 터치 키보드 다이얼로그
# =========================================================
class TouchKeyboard(QDialog):
    def __init__(self, title="입력", default_text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 배경 캡처 (dim overlay용)
        self._bg_pixmap = parent.window().grab() if parent else None

        self.composer = HangulComposer()
        self.composer.completed_text = ""
        self.is_korean = True

        # 버튼 객체 참조 (상태 변경용)
        self.eng_btns = []
        self.kor_btns = []
        self.btn_shift_kor = None
        self.btn_shift_eng = None

        # 외부 레이아웃 (전체화면, 중앙 정렬)
        outer_layout = QVBoxLayout(self)
        outer_layout.setAlignment(Qt.AlignCenter)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # 내용 프레임
        self.content_frame = QFrame()
        self.content_frame.setObjectName("KBFrame")
        self.content_frame.setFixedSize(*self._content_size(parent))
        self.content_frame.setStyleSheet("""
            QFrame#KBFrame {
                background: #1E232D;
                border: 2px solid #468CFF;
                border-radius: 12px;
            }
            QLabel#Title { color: #468CFF; font-size: 22px; font-weight: bold; background: transparent; margin-bottom: 5px; }
            QLineEdit { background: rgba(255, 255, 255, 20); border: 1px solid rgba(255, 255, 255, 50); border-radius: 6px; color: white; font-size: 32px; padding: 10px; font-weight: bold; }
            QPushButton { background: rgba(255, 255, 255, 10); border: 1px solid rgba(255, 255, 255, 30); border-radius: 6px; color: white; font-size: 22px; font-weight: bold; }
            QPushButton:pressed { background: rgba(70, 140, 255, 100); }
            QPushButton:checked { background: rgba(70, 140, 255, 80); border: 1px solid #468CFF; }
            QPushButton#action { background: rgba(70, 140, 255, 50); border: 1px solid #468CFF; }
            QPushButton#close { background: rgba(255, 70, 70, 50); border: 1px solid #FF4646; }
        """)
        outer_layout.addWidget(self.content_frame)

        layout = QVBoxLayout(self.content_frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 제목
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("Title")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setWordWrap(True)
        layout.addWidget(self.lbl_title)

        # 1. 입력창
        self.input_field = QLineEdit()
        self.input_field.setAlignment(Qt.AlignCenter)
        self.input_field.setReadOnly(True)
        layout.addWidget(self.input_field)

        self.set_text(default_text)

        # 2. 키패드 영역 (스택)
        self.key_stack = QStackedWidget()

        self.page_kor = QWidget()
        self.layout_kor = QGridLayout(self.page_kor)
        self.layout_kor.setSpacing(5)
        self.layout_kor.setContentsMargins(0,0,0,0)
        self._init_kor_keys()

        self.page_eng = QWidget()
        self.layout_eng = QGridLayout(self.page_eng)
        self.layout_eng.setSpacing(5)
        self.layout_eng.setContentsMargins(0,0,0,0)
        self._init_eng_keys()

        self.key_stack.addWidget(self.page_kor)
        self.key_stack.addWidget(self.page_eng)
        layout.addWidget(self.key_stack, 1)

        # 3. 하단 버튼
        bottom_layout = QHBoxLayout()

        btn_close = QPushButton("취소")
        btn_close.setObjectName("close")
        btn_close.setFixedSize(120, 65)
        btn_close.clicked.connect(self.reject)

        btn_clear = QPushButton("← Back")
        btn_clear.setFixedSize(120, 65)
        btn_clear.setAutoRepeat(True)
        btn_clear.clicked.connect(self._on_backspace)

        self.btn_mode = QPushButton("한/영")
        self.btn_mode.setFixedSize(120, 65)
        self.btn_mode.clicked.connect(self._toggle_mode)

        btn_space = QPushButton("Space")
        btn_space.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_space.setFixedHeight(65)
        btn_space.clicked.connect(self._on_space)

        btn_ok = QPushButton("확 인")
        btn_ok.setObjectName("action")
        btn_ok.setFixedSize(150, 65)
        btn_ok.clicked.connect(self.accept)

        bottom_layout.addWidget(self.btn_mode)
        bottom_layout.addWidget(btn_close)
        bottom_layout.addWidget(btn_space)
        bottom_layout.addWidget(btn_clear)
        bottom_layout.addWidget(btn_ok)

        layout.addLayout(bottom_layout)

    def _content_size(self, parent):
        if parent and parent.window():
            screen = parent.window().screen()
        else:
            screen = QApplication.primaryScreen()

        if screen:
            rect = screen.availableGeometry()
            max_w = max(1, rect.width() - 40)
            max_h = max(1, rect.height() - 40)
        else:
            max_w, max_h = 820, 500
        return min(860, max_w), min(540, max_h)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._bg_pixmap:
            painter.drawPixmap(0, 0, self._bg_pixmap)
        else:
            painter.fillRect(self.rect(), QColor(20, 25, 35, 255))
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

    def set_language(self, mode="KO"):
        self.set_layout(mode)

    def set_text(self, text):
        if text is None: text = ""
        self.input_field.setText(text)
        self.composer.completed_text = text
        self.input_field.deselect()
        self.input_field.end(False)

    def set_initial_text(self, text):
        self.set_text(text)

    def set_layout(self, mode="KO"):
        if mode.upper() == "EN":
            self.is_korean = False
            self.key_stack.setCurrentIndex(1)
            self.btn_mode.setText("한/영 (영)")
        else:
            self.is_korean = True
            self.key_stack.setCurrentIndex(0)
            self.btn_mode.setText("한/영 (한)")

    def _init_kor_keys(self):
        row0 = list("1234567890")
        row1 = list("ㅂㅈㄷㄱㅅㅛㅕㅑㅐㅔ")
        row2 = list("ㅁㄴㅇㄹㅎㅗㅓㅏㅣ")
        row3 = list("ㅋㅌㅊㅍㅠㅜㅡ")
        
        # 숫자 행
        for c, char in enumerate(row0):
            btn = QPushButton(char)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(lambda _, ch=char: self._on_number_click(ch))
            self.layout_kor.addWidget(btn, 0, c)

        # 한글 자모 행 1 (ㅂㅈㄷ...)
        for c, char in enumerate(row1):
            btn = QPushButton(char)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(self._on_kor_char_click)
            self.layout_kor.addWidget(btn, 1, c)
            self.kor_btns.append(btn)

        # 한글 자모 행 2 (ㅁㄴㅇ...)
        for c, char in enumerate(row2):
            btn = QPushButton(char)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(self._on_kor_char_click)
            self.layout_kor.addWidget(btn, 2, c)
            self.kor_btns.append(btn)

        # 한글 자모 행 3 (ㅋㅌㅊ... + Shift)
        # Shift 버튼: (3, 0)
        self.btn_shift_kor = QPushButton("⇧")
        self.btn_shift_kor.setCheckable(True)
        self.btn_shift_kor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.btn_shift_kor.setStyleSheet("color: #468CFF; font-size: 26px;")
        self.btn_shift_kor.toggled.connect(self._toggle_kor_shift)
        self.layout_kor.addWidget(self.btn_shift_kor, 3, 0)

        # [NEW] 특수문자: Shift 옆 비는 자리(3,8)(3,9)에 '_' 과 '.' 배치
        btn_under_kor = QPushButton("_")
        btn_under_kor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn_under_kor.clicked.connect(lambda _, ch="_": self._on_number_click(ch))
        self.layout_kor.addWidget(btn_under_kor, 3, 8)

        btn_dot_kor = QPushButton(".")
        btn_dot_kor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn_dot_kor.clicked.connect(lambda _, ch=".": self._on_number_click(ch))
        self.layout_kor.addWidget(btn_dot_kor, 3, 9)

        # 나머지 자음: (3, 1) 부터 시작
        for c, char in enumerate(row3):
            btn = QPushButton(char)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(self._on_kor_char_click)
            # [수정] Shift가 0번에 있으므로 문자키는 c+1
            self.layout_kor.addWidget(btn, 3, c+1)
            self.kor_btns.append(btn)

    def _init_eng_keys(self):
        row0 = list("1234567890")
        row1 = list("qwertyuiop")
        row2 = list("asdfghjkl")
        row3 = list("zxcvbnm")

        for c, char in enumerate(row0):
            btn = QPushButton(char)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(lambda _, ch=char: self._on_number_click(ch))
            self.layout_eng.addWidget(btn, 0, c)

        for c, char in enumerate(row1):
            btn = QPushButton(char)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(self._on_eng_char_click)
            self.layout_eng.addWidget(btn, 1, c)
            self.eng_btns.append(btn)

        for c, char in enumerate(row2):
            btn = QPushButton(char)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(self._on_eng_char_click)
            self.layout_eng.addWidget(btn, 2, c)
            self.eng_btns.append(btn)

        # Shift 버튼
        self.btn_shift_eng = QPushButton("⇧")
        self.btn_shift_eng.setCheckable(True)
        self.btn_shift_eng.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.btn_shift_eng.setStyleSheet("color: #468CFF; font-size: 26px;")
        self.btn_shift_eng.toggled.connect(self._toggle_eng_shift)
        self.layout_eng.addWidget(self.btn_shift_eng, 3, 0)

        for c, char in enumerate(row3):
            btn = QPushButton(char)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(self._on_eng_char_click)
            self.layout_eng.addWidget(btn, 3, c+1)
            self.eng_btns.append(btn)

        # [NEW] 특수문자: '_' 과 '.' 배치 (영어 레이아웃 3행 col 8, 9)
        btn_under_eng = QPushButton("_")
        btn_under_eng.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn_under_eng.clicked.connect(lambda _, ch="_": self._on_number_click(ch))
        self.layout_eng.addWidget(btn_under_eng, 3, 8)

        btn_dot_eng = QPushButton(".")
        btn_dot_eng.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn_dot_eng.clicked.connect(lambda _, ch=".": self._on_number_click(ch))
        self.layout_eng.addWidget(btn_dot_eng, 3, 9)

    def _toggle_eng_shift(self, checked):
        for btn in self.eng_btns:
            text = btn.text()
            btn.setText(text.upper() if checked else text.lower())

    def _toggle_kor_shift(self, checked):
        normal_map = {'ㅃ':'ㅂ', 'ㅉ':'ㅈ', 'ㄸ':'ㄷ', 'ㄲ':'ㄱ', 'ㅆ':'ㅅ', 'ㅒ':'ㅐ', 'ㅖ':'ㅔ'}
        shift_map = {'ㅂ':'ㅃ', 'ㅈ':'ㅉ', 'ㄷ':'ㄸ', 'ㄱ':'ㄲ', 'ㅅ':'ㅆ', 'ㅐ':'ㅒ', 'ㅔ':'ㅖ'}
        target_map = shift_map if checked else normal_map
        
        for btn in self.kor_btns:
            txt = btn.text()
            if txt in target_map:
                btn.setText(target_map[txt])

    def _reset_shift(self):
        """ [수정] 입력 후 Shift 해제 (Single Shot 기능) """
        if self.btn_shift_kor and self.btn_shift_kor.isChecked():
            self.btn_shift_kor.setChecked(False)
        if self.btn_shift_eng and self.btn_shift_eng.isChecked():
            self.btn_shift_eng.setChecked(False)

    def _on_number_click(self, char):
        if self.is_korean:
            self.composer.commit()
            self.composer.completed_text += char
            self.input_field.setText(self.composer.get_full_text())
        else:
            self.input_field.setText(self.input_field.text() + char)
            self.composer.completed_text = self.input_field.text()
        self._reset_shift()

    def _on_kor_char_click(self):
        btn = self.sender()
        if btn:
            char = btn.text()
            full_str = self.composer.input_char(char)
            self.input_field.setText(full_str)
            self._reset_shift() # 글자 입력 후 Shift 해제

    def _on_eng_char_click(self):
        btn = self.sender()
        if btn:
            char = btn.text()
            self.input_field.setText(self.input_field.text() + char)
            self.composer.completed_text = self.input_field.text()
            self._reset_shift() # 글자 입력 후 Shift 해제

    def _on_backspace(self):
        if self.is_korean:
            new_text = self.composer.backspace()
            self.input_field.setText(new_text)
        else:
            txt = self.input_field.text()
            if txt:
                self.input_field.setText(txt[:-1])
                self.composer.completed_text = txt[:-1]

    def _on_space(self):
        self.composer.commit() 
        self.composer.completed_text += " "
        self.input_field.setText(self.composer.get_full_text())
        self._reset_shift()

    def _toggle_mode(self):
        if self.is_korean:
            self.composer.commit()
            
        self.is_korean = not self.is_korean
        if self.is_korean:
            self.key_stack.setCurrentIndex(0)
            self.btn_mode.setText("한/영 (한)")
        else:
            self.key_stack.setCurrentIndex(1)
            self.btn_mode.setText("한/영 (영)")
        
        self._reset_shift()

    def get_text(self):
        return self.composer.get_full_text()
