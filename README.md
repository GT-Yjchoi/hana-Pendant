# Pendant — 산업용 서보 제어 HMI

라즈베리파이 기반 PySide6 풀스크린 HMI 앱.
파나소닉 PLC(FPWIN Pro)와 TCP(MEWTOCOL-style) 통신으로 8축 서보 시스템을 제어하고 시퀀스·포인트를 관리합니다.

---

## 실행 환경

| 항목 | 값 |
|---|---|
| 플랫폼 | Raspberry Pi (aarch64) |
| OS | Raspberry Pi OS (Debian) |
| Python | 3.x |
| 가상환경 | `/home/yjchoi/Desktop/Pendant/.venv` |
| 해상도 | 1024 × 600 (풀스크린) |

---

## 프로젝트 구조

```
Pendant/
├── main.py                        # 진입점 (QApplication, PLCClient, MainWindow)
├── main.spec                      # PyInstaller 빌드 스펙
├── settings.json                  # 사용자 설정 (PLC IP/Port, 밸브, IO 이름 등)
├── style.qss                      # 전역 스타일시트 (Fusion 기반)
├── plc_fb.st                      # PLC 펑션블록 소스 (파나소닉 FPWIN Pro ST)
│
├── ui/                            # UI 레이어
│   ├── main_window.py             # 메인 윈도우 (페이지 스택, 네비게이션, 알람 오버레이)
│   ├── top_bar.py                 # 상단 바 (PLC 상태, 모드, 카운터, JOG 버튼)
│   ├── overlays/
│   │   └── alarm_overlay.py       # 축 알람 오버레이 (리셋 버튼 포함)
│   ├── pages/
│   │   ├── page_manual.py         # 수동 운전 페이지 (밸브 수동 제어)
│   │   ├── page_auto.py           # 자동 운전 페이지 (시퀀스 실행, 확인운전)
│   │   ├── page_mode.py           # 모드 설정 페이지 (40개 모드 On/Off)
│   │   ├── page_position.py       # 포인트 관리 + 시퀀스 미리보기
│   │   ├── page_timer.py          # 타이머 설정 페이지 (시퀀스 TMR 스텝 편집)
│   │   ├── page_packing.py        # 패킹 페이지 (X/Y/Z축 적재 카운터)
│   │   ├── page_data.py           # 레시피 관리 (저장/로드/새로만들기)
│   │   └── page_settings.py       # 설정 페이지 (PLC IP·Port, 언어, 밸브 이름 등)
│   ├── dialogs/
│   │   ├── jog_control_dialog.py  # 조그 제어 팝업 (축별 수동 이동)
│   │   ├── sequence_editor_dialog.py  # 시퀀스 편집기 (스텝 추가/수정/삭제)
│   │   ├── sequence_step_ui.py    # 스텝 UI 위젯 (POS/OUT/IN/TMR/JMP/CALL/END/COMMENT)
│   │   ├── sequence_utils.py      # 시퀀스 유틸리티 (OverlayDialog 등)
│   │   └── timer_edit_dialog.py   # 타이머 값 편집 팝업
│   └── widgets/
│       ├── axis_position_panel.py # 축 위치 표시 패널
│       ├── valve_tile.py          # 밸브 타일 위젯 (Toggle/Momentary)
│       └── custom_inputs.py       # 커스텀 입력 위젯
│
├── utils/                         # 비즈니스 로직
│   ├── plc_client.py              # 파나소닉 PLC TCP 통신 클라이언트
│   ├── io_manager.py              # IO 이름 관리 (싱글톤)
│   ├── mode_manager.py            # 모드 이름 관리 (싱글톤)
│   ├── languages.py               # 다국어 지원 (한/영)
│   ├── gpio_estop.py              # GPIO 기반 하드 비상정지 입력
│   ├── json_utils.py              # JSON 읽기/쓰기 공통 유틸
│   └── paths.py                   # 리소스 경로 유틸 (PyInstaller 호환)
│
├── widgets/                       # 공용 재사용 위젯
│   ├── nav_button.py              # 하단 네비게이션 버튼
│   ├── glass_card.py              # 글래스 카드 컨테이너
│   ├── io_panel.py                # IO 상태 패널
│   ├── square_toggle_tile.py      # 정사각형 토글 타일
│   ├── touch_keyboard.py          # 터치 소프트 키보드
│   └── touch_number_keyboard.py   # 터치 숫자 키패드
│
└── recipes/                       # 레시피 파일 (런타임 생성)
    └── *.json                     # 시퀀스·포인트·모드 통합 저장
```

---

## 핵심 설계

### PLC 통신 (`utils/plc_client.py`)

- **대상 PLC**: 파나소닉 FP 시리즈 (FPWIN Pro, ST 프로그래밍)
- **프로토콜**: TCP, `DEST_UNIT=0x01`, 12바이트 헤더 프레임
- **모니터링**: DT100~DT160 (61 Words) 를 50ms 주기로 폴링
- **하트비트**: 통신 성공마다 DT214에 0~100 순환값 전송
- **자동 재연결**: 통신 끊김 시 5초 간격으로 재연결 시도

#### PLC 메모리 맵

| 영역 | 주소 | 내용 |
|---|---|---|
| **모니터링 (PLC→HMI)** | DT100~115 | 8축 현재 위치 (DINT×8, 0.001mm 단위) |
| | DT116~119 | 입력(X) 상태 (WORD×4, 64점) |
| | DT120~123 | 출력(Y) 상태 (WORD×4, 64점) |
| | DT124~125 | 밸브 동작 상태 (32개 밸브) |
| | DT126 | R입력 R0~RF (HMI port 200~215 매핑) |
| | DT129 | 운전 상태 (0=정지, 1=수동, 2=자동, 3=일정지) |
| | DT130 | 확인운전 상태 |
| | DT131 | 현재 시퀀스 스텝 번호(코멘트 제외) |
| | DT132~133 | 총 취출 횟수 (DINT) |
| | DT134~135 | 성형 시간 (0.1초 단위) |
| | DT136~137 | 취출 시간 (0.1초 단위) |
| | DT138~140 | 패킹 카운터 X/Y/Z |
| | DT141 | 축 알람 비트맵 (bit0~7=1~8축, bit8=비상정지) |
| | DT143~158 | 축별 에러코드 (DINT×8) |
| | DT159 | 시퀀스 팝업 요청 코드 |
| | DT160 | 작업자 응답 (0=대기, 1=계속, 2=정지) |
| **제어 (HMI→PLC)** | DT200 | 운전 제어 (0=정지, 1=자동, 2=확인운전) |
| | DT201 | 조작압 선택 (0=제품압, 1=티칭압) |
| | DT202 | 확인운전 제어 (상승엣지로 1스텝 진행) |
| | DT204~205 | 밸브 수동 제어 (2 Words, 32비트) |
| | DT205 | 조그 제어 (비트별 축) |
| | DT206~208 | 모드 설정 (40개 모드 비트팩, 3 Words) |
| | DT211 | 조그 속도 |
| | DT212 | 알람 리셋 (1=리셋, 0=해제) |
| | DT213 | 소프트 비상정지 (0=정상, 1=비상정지) |
| | DT214 | 하트비트 (0~100 순환) |
| | DT215 | 수동조작 모드 (0=앱솔루트, 1=JOG) |
| **축 파라미터** | DT15000~15049 | 8축 공통 설정 블록 (50 Words) |
| | DT15033 | 축 데이터셋 전송 트리거 |
| **포인트 데이터** | DT16000~ | 포인트당 32 Words × 최대 100 포인트 (DT16000~DT19199) |
| **시퀀스 데이터** | DT20000~ | 슬롯당 1000 Words (100스텝 × 10Words) × 최대 40슬롯 (DT20000~DT59999) |

> 포인트 인덱스 `i` 의 시작 주소 = `DT16000 + i × 32`
> 슬롯 `s` 의 스텝 `k` 시작 주소 = `DT20000 + s × 1000 + k × 10`

#### 포인트 데이터 레이아웃 (32 Words/포인트)

| 오프셋 | 내용 |
|---|---|
| +0 | 유효 플래그 (0xFF = 사용) |
| +1 | 전체 속도 (%) |
| +2~17 | 8축 좌표 (DINT×8, 0.001mm) |
| +18~25 | 8축 속도 (WORD×8, %) |

#### 시퀀스 스텝 명령 코드 (10 Words/스텝)

스텝 레이아웃: `[iCommand, wOption, P1_L, P1_H, P2_L, P2_H, P3_L, P3_H, P4_L, P4_H]`

| CMD | 타입 | 설명 |
|---|---|---|
| 10 | POS | 포인트 이동 (OPT = 사용축 비트마스크, P1 = 포인트 인덱스) |
| 20 | OUT | 출력/밸브 On/Off (P3>0 → 타이머 기동후출력) |
| 21 | IN | 입력 대기 (P2 = 타임아웃, P3 = 동작, P4 = 알람번호) |
| 30 | TMR | 타이머 대기 또는 신호유지 (0.01초 단위) |
| 40 | JMP | 점프 (OPT=0 무조건, OPT=1 조건부) |
| 50 | CALL | 서브 시퀀스 호출 (OPT=0 대기, OPT=1 동시실행) |
| 99 | END | 시퀀스 종료 |

> **주의**: 코멘트 스텝은 PLC 전송 시 제외되므로, PLC 관점의 스텝 번호와 HMI 리스트 행 번호가 다를 수 있습니다. `page_position._highlight_step` 에서 PLC step 인덱스를 UI 행으로 매핑합니다.

#### OUT 스텝 파라미터 상세

| 파라미터 | 내용 |
|---|---|
| OPT | 출력 상태 (1=ON, 0=OFF) |
| P1 | 비트 인덱스 (포트) |
| P2 | 출력 구분 (0=시스템출력, 1=밸브출력, 2=내부비트) |
| P3 | 딜레이 시간 (0=즉시출력, >0=타이머 기동후출력, 0.01초 단위) |

**타이머 기동후출력 동작:**
- P3 > 0 이면 타이머만 기동하고 즉시 다음 스텝으로 진행
- 타이머 만료 시 지정된 출력(P1, P2, OPT)을 실행
- 최대 **2개** 동시 기동 가능 (슬롯 0~1)
- 2개 초과 시 `i_ErrorID = 98` 에러로 시퀀스 정지

#### IN 스텝 포트 매핑

| 포트 범위 | 의미 |
|---|---|
| 0~63 | 시스템/밸브 입력 X00~X3F |
| 100~131 | 내부 비트 M00~M31 (DT300~301) |
| 200~215 | R입력 R0~RF (DT126 비트 0~15) |

### PLC 펑션블록 (`plc_fb.st`) — 3-tier 인스턴스 구조

시퀀스 실행 FB는 3개 인스턴스로 배선합니다 (Main → Sub → SubSub). CALL 스텝은 최대 2단계 중첩(메인 → 서브 → 서브서브) 까지 지원.

```
FB_Main   (slot 0 고정, b_Run = 외부 운전 명령)
   ↓ b_CallStart / i_CallSlotOut
FB_Sub    (slot 동적, 메인의 CALL에서 기동)
   ↓
FB_SubSub (slot 동적, 서브의 CALL에서 기동, b_NoSubCall=TRUE)
```

**핵심 I/O:**
- `b_SubBusy` : 하위 FB 실행중 플래그 (병렬 CALL 충돌 방지)
- `b_NoSubCall` : 최하위 인스턴스 표시 (SubSub에 TRUE 배선)
- `b_IsBusy` : 이 FB가 실행중 (상위의 `b_SubBusy`에 연결)
- `b_Step_End` : END 도달 펄스 (상위의 `b_SubDone`에 연결)

**에러 ID:**

| ID | 의미 |
|---|---|
| 21 | POS 축 이동 확인 실패 |
| 50 | 서브 시퀀스 에러 |
| 93 | 병렬 CALL 실패 — 서브 FB가 이미 실행중 |
| 94 | CALL 사용 불가 — 최하위 인스턴스(`b_NoSubCall=TRUE`) |
| 95 | JMP 타겟 스텝 번호 범위 초과 (0~99) |
| 96 | CALL 슬롯 번호 범위 초과 (0~39) |
| 97 | 실행 슬롯 번호 범위 초과 (0~39) |
| 98 | OUT 지연 타이머 슬롯 없음 (2개 모두 사용중) |
| 99 | 알 수 없는 커맨드 |

### 레시피 파일 형식 (`recipes/*.json`)

```json
{
    "sequence": {
        "Main": [...],
        "Sub1": [...]
    },
    "position_points": {
        "Home": {"coords": [0,0,0,0,0,0,0,0], "speeds": [100,100,100,100,100,100,100,100]},
        "Point_1": {"coords": [100.5, 200.0, ...], "speeds": [...]}
    },
    "mode": [false, true, false, ...],
    "view_order": ["Home", "Point_1", ...],
    "user_modes": {...}
}
```

### settings.json 주요 구조

```json
{
    "plc_ip": "192.168.0.60",
    "plc_port": "60001",
    "last_recipe": "레시피명",
    "axis_uses": [true, true, true, false, false, false, false, false],
    "valve_config": [
        {"index": 0, "name": "척 1", "mode": "toggle", "enabled": true},
        {"index": 8, "name": "포스쳐 반전", "mode": "momentary", "enabled": true}
    ],
    "io_names": {
        "inputs": ["X00 비상정지", "X01", ...],
        "outputs": ["Y00", ..., "Y0D 서보온", ...]
    }
}
```

---

## 시퀀스 팝업 메시지 (`ui/main_window.py`)

PLC DT159에 코드 값이 들어오면 작업자 확인 팝업을 표시합니다.
응답(계속=1 / 정지=2)은 DT160에 기록됩니다.

| 코드 | 제목 | 메시지 |
|---|---|---|
| 1 | 입력 대기 타임아웃 | 입력 신호를 받지 못했습니다. |
| 2 | 도어 열림 경고 | 도어가 열려 있습니다. |
| 3 | 공압 이상 | 공압이 낮습니다. |

`SEQ_POPUP_MESSAGES` 딕셔너리에 코드를 추가해 확장할 수 있습니다.

---

## 빌드 방법

```bash
cd /home/yjchoi/Desktop/Pendant
source .venv/bin/activate
pyinstaller --clean -y main.spec
```

---

## 개발 실행

```bash
cd /home/yjchoi/Desktop/Pendant
source .venv/bin/activate
python main.py
```

---

## 자주 수정하는 부분

| 목적 | 파일 |
|---|---|
| PLC IP/Port 기본값 | `ui/main_window.py` → `_try_auto_connect` |
| 시퀀스 팝업 메시지 추가 | `ui/main_window.py` → `SEQ_POPUP_MESSAGES` |
| 밸브 이름·모드 설정 | `settings.json` → `valve_config` |
| IO 이름 변경 | `settings.json` → `io_names` |
| 모니터링 주기 변경 | `utils/plc_client.py` → `_mon_loop` (`time.sleep`) |
| PLC 주소 상수 | `utils/plc_client.py` → `__init__` 상단 |
| 시퀀스 FB 로직 | `plc_fb.st` |
| 페이지 추가 | `ui/pages/` 파일 생성 후 `ui/main_window.py`에 등록 |
| 네비게이션 버튼 순서 | `ui/main_window.py` → `add_nav(...)` 호출 순서 |
| 스타일 변경 | `style.qss` |
