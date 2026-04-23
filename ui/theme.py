APP_STYLESHEET = """
/* ========================================================
   [Global] 기본 폰트 및 배경 설정
   ======================================================== */
QWidget {
    color: #E9EEF3;
    font-family: "Pretendard", "Segoe UI";
    font-size: 20px;
}

#Root {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #1A2733, stop:0.45 #1B2430, stop:1 #0F161E
    );
}

/* ========================================================
   [Main Window] 상단/하단 바
   ======================================================== */
#TopBar, #BottomBar {
    background: rgba(10, 16, 22, 170);
    border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 14px;
}

#TopBar QLabel {
    font-size: 16px;
    font-weight: 700;
    color: rgba(233, 238, 243, 210);
}

/* ========================================================
   [Common] 공통 위젯 스타일
   ======================================================== */
/* 글래스 카드 (반투명 패널) */
.GlassCard {
    background: rgba(15, 22, 30, 150);
    border: 1px solid rgba(255, 255, 255, 35);
    border-radius: 16px;
}

.PageTitle {
    font-size: 20px;
    font-weight: 800;
    color: rgba(233, 238, 243, 230);
}

.HintText {
    color: rgba(233, 238, 243, 180);
    font-size: 14px;
}

/* 하단 네비게이션 버튼 */
.NavBtn {
    background: transparent;
    border: none;
    color: rgba(233, 238, 243, 170);
    padding: 8px 10px;
    border-radius: 10px;
    min-height: 44px;
}
.NavBtn[active="true"] {
    background: rgba(90, 160, 255, 22);
    color: rgba(233, 238, 243, 240);
    border: 1px solid rgba(90, 160, 255, 60);
}

/* 스크롤바 커스텀 */
QScrollBar:vertical {
    background: rgba(255, 255, 255, 6);
    width: 12px;
    margin: 6px 4px 6px 4px;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 28);
    min-height: 40px;
    border-radius: 6px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    width: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

/* ========================================================
   [Page] Mode (동작모드)
   ======================================================== */
.ModeTileBtn {
    background: rgba(255, 255, 255, 12);
    border: 1px solid rgba(255, 255, 255, 28);
    border-radius: 14px;
    padding: 10px;
    text-align: center;
    font-weight: 800;
    color: rgba(233, 238, 243, 210);
}
.ModeTileBtn:pressed {
    background: rgba(90, 160, 255, 18);
    border: 1px solid rgba(90, 160, 255, 70);
}
.ModeTileBtn:checked {
    background: rgba(90, 160, 255, 24);
    border: 2px solid rgba(90, 160, 255, 140);
    color: rgba(233, 238, 243, 245);
}

/* ========================================================
   [Page] Manual (수동운전) - 밸브 조작 버튼
   ======================================================== */
.ValveTileBtn {
    background: rgba(255, 255, 255, 10);
    border: 1px solid rgba(255, 255, 255, 25);
    border-radius: 14px;
    padding: 8px;
    color: rgba(233, 238, 243, 210);
    font-weight: 900;
    font-size: 14px;
}
.ValveTileBtn:pressed {
    background: rgba(90, 160, 255, 18);
    border: 1px solid rgba(90, 160, 255, 70);
}
.ValveTileBtn:checked {
    background: rgba(90, 160, 255, 24);
    border: 2px solid rgba(90, 160, 255, 140);
    color: rgba(233, 238, 243, 245);
}

/* 암 선택 버튼 */
.ArmSelectBtn {
    background: rgba(255, 255, 255, 10);
    border: 1px solid rgba(255, 255, 255, 25);
    border-radius: 14px;
    padding: 10px 12px;
    font-weight: 900;
    color: rgba(233, 238, 243, 210);
}
.ArmSelectBtn:checked {
    background: rgba(90, 160, 255, 24);
    border: 2px solid rgba(90, 160, 255, 140);
    color: rgba(233, 238, 243, 245);
}

/* IO 램프 */
QFrame#IOLampIn, QFrame#IOLampOut {
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,35);
    background-color: rgba(0,0,0,230);
}
QFrame#IOLampIn[on="true"] {
    background-color: rgba(70, 140, 255, 245);
    border: 1px solid rgba(140, 200, 255, 220);
}
QFrame#IOLampOut[on="true"] {
    background-color: rgba(255, 105, 35, 245);
    border: 1px solid rgba(255, 170, 120, 220);
}

/* ========================================================
   [Page] Auto (자동운전)
   ======================================================== */
.AutoControlBtn {
    background: rgba(70, 140, 255, 18);
    border: 2px solid rgba(70, 140, 255, 80);
    border-radius: 14px;
    padding: 14px 18px;
    font-weight: 900;
    font-size: 18px;
    color: rgba(233, 238, 243, 245);
}
.AutoControlBtn:pressed {
    background: rgba(70, 140, 255, 38);
    border: 2px solid rgba(70, 140, 255, 150);
}
.AutoControlBtn[variant="stop"] {
    background: rgba(255, 70, 70, 18);
    border: 2px solid rgba(255, 70, 70, 80);
}
.AutoControlBtn[variant="stop"]:pressed {
    background: rgba(255, 70, 70, 38);
    border: 2px solid rgba(255, 70, 70, 150);
}

/* 자동운전 타일 버튼들 */
.AutoControlTile {
    background: rgba(50, 80, 120, 15);
    border: 2px solid rgba(70, 100, 140, 50);
    border-radius: 14px;
    padding: 14px;
    font-weight: 900;
    font-size: 18px;
    color: rgba(180, 200, 220, 180);
}
.AutoControlTile:checked {
    background: rgba(70, 140, 255, 40);
    border: 3px solid rgba(70, 140, 255, 200);
    color: rgba(255, 255, 255, 255);
}
.AutoControlTile[variant="stop"] {
    background: rgba(255, 70, 70, 18);
    border: 2px solid rgba(255, 70, 70, 80);
    color: rgba(255, 200, 200, 220);
}
.AutoControlTile[variant="start"] {
    background: rgba(70, 200, 100, 18);
    border: 2px solid rgba(70, 200, 100, 80);
    color: rgba(200, 255, 220, 220);
}
.AutoControlTile[variant="pause"] {
    background: rgba(255, 180, 70, 18);
    border: 2px solid rgba(255, 180, 70, 80);
    color: rgba(255, 230, 200, 220);
}

/* ========================================================
   [Page] Data (금형데이터)
   ======================================================== */
.DataButton {
    background: rgba(70, 140, 255, 22);
    border: 2px solid rgba(70, 140, 255, 90);
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 900;
    font-size: 16px;
    color: rgba(233, 238, 243, 245);
}
.DataList {
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 12px;
    padding: 8px;
    font-size: 16px;
    font-weight: 700;
    color: rgba(233, 238, 243, 230);
}
.DataList::item:selected {
    background: rgba(70, 140, 255, 30);
    border: 2px solid rgba(70, 140, 255, 140);
    color: rgba(233, 238, 243, 250);
}

/* ========================================================
   [Page] Position (위치설정)
   ======================================================== */
.PointNavButton {
    background: rgba(70, 140, 255, 25);
    border: 2px solid rgba(70, 140, 255, 90);
    border-radius: 8px;
    color: rgba(233, 238, 243, 240);
    font-size: 20px;
    font-weight: 900;
}
.PosTableAxisLabel {
    background: rgba(255, 255, 255, 12);
    border: 1px solid rgba(255, 255, 255, 35);
    border-radius: 6px;
    color: rgba(233, 238, 243, 230);
    font-size: 15px;
    font-weight: 900;
}
.PosTableValueBox {
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(255, 255, 255, 25);
    border-radius: 6px;
}
.PosTableValue {
    color: rgba(233, 238, 243, 240);
    font-size: 15px;
    font-weight: 700;
}

/* ========================================================
   [Dialog] 시퀀스 편집기 (Sequence Editor)
   ======================================================== */
QDialog#SequenceEditor {
    background-color: #141E28;
    border: 2px solid #468CFF;
    border-radius: 16px;
}

QDialog#SequenceEditor QGroupBox {
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 6px;
    margin-top: 25px;
    color: white;
    font-weight: bold;
    font-size: 18px;
}
QDialog#SequenceEditor QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 10px;
    background-color: transparent;
}

QDialog#SequenceEditor QComboBox {
    background-color: #252525;
    border: 1px solid #666;
    border-radius: 6px;
    padding: 5px 10px;
    color: #E0E0E0;
    font-size: 20px;
    font-weight: bold;
}
QDialog#SequenceEditor QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 35px;
    border-left-width: 1px;
    border-left-color: #555;
    border-left-style: solid;
    background: #333;
}
QDialog#SequenceEditor QComboBox::down-arrow {
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 8px solid #DDD;
    margin-top: 2px;
}

QComboBox QAbstractItemView {
    background-color: #252525;
    border: 1px solid #468CFF;
    selection-background-color: #468CFF;
    color: #E0E0E0;
    font-size: 18px;
    outline: none;
    padding: 5px;
}

QDialog#SequenceEditor QRadioButton {
    color: #E0E0E0;
    font-size: 20px;
    spacing: 10px;
}
QDialog#SequenceEditor QRadioButton::indicator {
    width: 24px;
    height: 24px;
    border-radius: 13px;
    border: 2px solid #999;
    background: #111;
}
QDialog#SequenceEditor QRadioButton::indicator:checked {
    background-color: #00FF00;
    border: 2px solid #00FF00;
}

QDialog#SequenceEditor QDoubleSpinBox,
QDialog#SequenceEditor QSpinBox {
    background-color: #252525;
    border: 1px solid #666;
    border-radius: 4px;
    color: #FFD280;
    font-size: 20px;
    font-weight: bold;
    padding-left: 10px;
}
"""
