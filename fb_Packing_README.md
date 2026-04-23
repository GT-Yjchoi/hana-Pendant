# 파렛타이징 PLC 통합 가이드

POS 스텝에 `pack_base` 플래그가 켜지면 **베이스 포인트 좌표 + (pack_idx × pitch × dir)** 결과를 RTEX 스크래치 테이블(10089, idx=63) 에 기록하고 그 테이블로 이동합니다. 원본 포인트 데이터는 절대 변경되지 않으므로 HMI 의 기억 좌표는 그대로 유지됩니다.

## 아키텍처 (병합 설계)

파렛타이징 로직은 **`new_plc_fb.st` 내부 (FB_Main)** 에 인라인 통합되어 있습니다. 별도 FB (`fb_Packing`) 는 **더 이상 사용하지 않음** — state 11 에서 직접 계산·F151_WRT 수행, state 10 CMD=99 (사이클 END) 에서 pack_idx 증가.

| 역할 | 위치 |
|---|---|
| pack_base 감지 + 좌표 계산 + 테이블 63 쓰기 | FB_Main state 11 (POS 처리) |
| pack_idx 증가 (사이클 완료 시) | FB_Main state 10 CMD=99 END 처리 |
| Monitor 인스턴스 중복 방지 | `IF NOT b_NoSubCall` 가드 |
| HMI ↔ PLC 통신 | 글로벌 변수 (DT 매핑, AT 주소) |

PROGRAM 와이어링은 **기존 그대로** — 추가 인스턴스 없음.

---

## 0. GLOBAL_VAR 리팩토링 (선결 작업)

`fb_WriteMotionTable` 와 `fb_Packing` 이 공통으로 참조하는 아래 변수들은 **Global Variables 로 승격** 되어야 합니다. 이전 버전에서 `fb_WriteMotionTable` 의 `VAR_INPUT` 으로 선언돼 있었다면 FPWIN 에서 다음 마이그레이션을 수행:

### 마이그레이션 절차 (FPWIN Pro)

1. **Global Variables 탭에 추가**:
   ```pascal
   VAR_GLOBAL
       g_Dut_Point      : ARRAY[0..59] OF POINT_DATA_DUT;
       gi_SpeedOverride : INT;   (* DT216 매핑 *)
       gi_1축AccDec : INT;   gi_2축AccDec : INT;   gi_3축AccDec : INT;
       gi_4축AccDec : INT;   gi_5축AccDec : INT;
       gdi_1축PPR   : DINT;  gdi_2축PPR   : DINT;  gdi_3축PPR   : DINT;
       gdi_4축PPR   : DINT;  gdi_5축PPR   : DINT;
   END_VAR
   ```
   (초기값은 기존 PROGRAM 의 세팅 순간에 대입되던 값들, `gi_SpeedOverride` 는 스캔마다 DT216 복사)

2. **fb_WriteMotionTable 의 VAR_INPUT 에서 이 변수들 제거**:
   - 남기는 것: `b_Execute`, `i_WriteCount`
   - 제거: `g_Dut_Point`, `gi_SpeedOverride`, `gi_*축AccDec`, `gdi_*축PPR`

3. **PROGRAM 와이어링 간소화**:
   ```pascal
   (* 변경 전 *)
   fb_WriteMotionTable_inst(
       b_Execute       := ...,
       i_WriteCount    := ...,
       i_SpeedOverride := DT216,
       gi_1축AccDec     := <값>,
       ...
       gdi_5축PPR       := <값>,
       g_Dut_Point   := ...
   );

   (* 변경 후 *)
   gi_SpeedOverride := WORD_TO_INT(DT216);   (* 스캔 최상단에서 DT216 → 글로벌 복사 *)
   fb_WriteMotionTable_inst(
       b_Execute    := ...,
       i_WriteCount := ...
   );
   ```

4. **fb_Packing 도 동일 원칙**: 축 파라미터는 와이어링 안 함. PROGRAM 호출은 본 문서 §4 참조.

### 이점

- **인스턴스 코드 복제 비용 감소** — FP0H 는 FB 인스턴스마다 VAR_INPUT 파라미터 포함 본체가 복제됨. VAR_INPUT 제거 = 본체 작아짐
- **fb_Packing 과 일관성** — 두 FB 가 같은 소스의 좌표/축 파라미터를 참조
- **PROGRAM 와이어링 단순화**

---

## 1. DT 메모리 맵 (신규 할당)

### HMI ↔ PLC 공유 (읽기/쓰기 모두 가능)

| DT | 용도 | 타입 | 비고 |
|---|---|---|---|
| DT161 | `i_PackIdxX` 현재 X 스택 인덱스 (0-based) | INT | HMI 임의 수정 → PLC 즉시 반영 |
| DT162 | `i_PackIdxY` | INT | 동상 |
| DT163 | `i_PackIdxZ` | INT | 동상 |

### HMI → PLC (패킹 설정, HMI 가 기록)

| DT | 용도 | 타입 |
|---|---|---|
| DT217 | `w_PackEnable` (1=패킹 활성) | WORD |
| DT218~219 | `di_PitchX` (0.001 mm) | DINT |
| DT220~221 | `di_PitchY` | DINT |
| DT222~223 | `di_PitchZ` | DINT |
| DT224 | `i_DirX` (+1 / -1) | INT |
| DT225 | `i_DirY` | INT |
| DT226 | `i_DirZ` (보통 +1) | INT |
| DT227 | `i_CountX` (총 횟수) | INT |
| DT228 | `i_CountY` | INT |
| DT229 | `i_CountZ` | INT |
| DT230 | `i_StackOrder` (0~5) | INT |

> `plc_client.py` 의 `ADDR_*` 상수에 아래를 추가 필요:
> ```python
> self.ADDR_PACK_CFG        = 217   # DT217~230 (14 Words)
> self.ADDR_PACK_IDX        = 161   # DT161~163 (공유)
> ```

---

## 2. 시퀀스 스텝의 pack_base 플래그

10 Words 스텝 포맷의 `wOption` (Word 1) 에 **bit 8** 을 `pack_base` 플래그로 할당합니다. (bit 0~7 은 HMI 의 8축 사용 마스크가 점유.)

```
wOption bit 구조:
  bit 0 : 1축 (X) 사용
  bit 1 : 2축 (Y) 사용
  bit 2 : 3축 (Z) 사용
  bit 3 : 4축 (Y2) 사용
  bit 4 : 5축 (Z2) 사용
  bit 5 : 6축 (θ) 사용 (현재 모션 FB 미지원 but HMI 예약)
  bit 6 : 7축 (R1)
  bit 7 : 8축 (R2)
  bit 8 : pack_base (1=파렛타이징 베이스 스텝)   ← [NEW]
  bit 9~15 : 예약
```

HMI `plc_client.py` 의 스텝 시리얼라이즈 시 `step.get("pack_base")` 가 True 면 bit 8 OR 처리:

```python
if step.get("pack_base"):
    w_option |= 0x0100  # bit 8
```

---

## 3. new_plc_fb.st 수정

### 3-1. FB_Main 내부 VAR 추가 (FPWIN 변수 탭)

state 11 인라인 계산용 작업 변수. 모두 내부 VAR (외부 노출 없음):

```pascal
VAR
    (* ... 기존 ... *)
    i_PackBaseIdx   : INT;
    w_PackBankSlot  : WORD;
    w_PackTableOff  : WORD;
    di_PackBase     : DINT;
    di_PackOffset   : DINT;
    di_PackTarget   : DINT;
    i_PackTargetSpd : INT;
    i_PackAxisAcc   : INT;
    di_PackAxisPPR  : DINT;
    i_PackOvrd      : INT;
    PackTableData   : TABLE_DATA_DUT;
END_VAR
```

> VAR_OUTPUT 추가 없음 — `b_PackTrig`, `i_PackBasePointIdx` 모두 불필요.
> PROGRAM 은 글로벌 (DT 매핑) 로만 통신.

### 3-2. State 11 (POS) 인라인 패킹 계산

wOption bit 8 (pack_base) 체크 + `gw_PackEnable` 마스터 스위치 확인 후, 둘 다 만족이면 **같은 state 에서** 테이블 63(RTEX 10089) 에 계산·기록하고 `i_WriteTableNo := 10089` 지정. OFF 면 기존 로직 (원본 포인트 테이블로 일반 이동).

```pascal
11:
    w_EffOpt := w_StepOpt AND w_AxisEnable;

    IF (w_StepOpt AND 16#0100) <> 0 AND (gw_PackEnable <> 0) THEN
        (* === 인라인 패킹 === *)
        i_WriteTableNo := 10026 + 63;
        i_PackBaseIdx  := DINT_TO_INT(di_StepP1);

        IF (gi_SpeedOverride < 1) OR (gi_SpeedOverride > 10) THEN
            i_PackOvrd := 10;
        ELSE
            i_PackOvrd := gi_SpeedOverride;
        END_IF;

        PackTableData.ControlCode := 16#0001;
        PackTableData.Pattern     := 16#0000;
        (* ... 공통 필드 ... *)

        w_PackTableOff := INT_TO_WORD(63 * 16);

        FOR i_LoopAxis := 1 TO 5 DO
            w_PackBankSlot := 16#6000 OR SHL(INT_TO_WORD(i_LoopAxis), 8);
            CASE i_LoopAxis OF
                1: (* X: 오프셋 적용 *)
                    di_PackBase   := g_Dut_Point[i_PackBaseIdx].diPosX;
                    (* ... 속도/PPR ... *)
                    di_PackOffset := INT_TO_DINT(gi_PackIdxX) * gdi_PitchX * INT_TO_DINT(gi_DirX);
                    di_PackTarget := di_PackBase + di_PackOffset;
                2: (* Y: 동일 패턴 *) ...
                3: (* Z: 동일 패턴 *) ...
                4,5: (* Y2/Z2: 원본 유지 *) ...
            END_CASE;
            PackTableData.TargetPosition := di_PackTarget;
            (* TargetSpeed / AccTime / DecTime 채우기 *)
            F151_WRT(s1_BankSlot:=w_PackBankSlot,
                     s2_Start:=Adr_Of_Var(PackTableData),
                     n_Number:=16,
                     d_Start:=w_PackTableOff);
        END_FOR;
    ELSE
        i_WriteTableNo := DINT_TO_INT(di_StepP1) + 10026;
    END_IF;

    (* 뱅크슬롯 쓰기 (기존 로직) *)
    FOR i_LoopAxis := 1 TO 5 DO ... END_FOR;

    t_SettleTime := T#50MS;
    b_SettleStart := TRUE;
    i_SeqState := 12;
```

> **전체 상세 코드는 new_plc_fb.st 의 state 11 블록 참조** — 이 README 는 핵심 골격만 표시.

### 3-3. State 10 CMD=99 (최상위 END) 에 pack_idx 증가 추가

사이클 완료 시점(`b_Step_End := TRUE` 직후)에 **FB_Main 인스턴스만** pack_idx 증가. Monitor 인스턴스는 `b_NoSubCall=TRUE` 로 구분되므로 guard 로 차단.

```pascal
99: (* END 명령 — 최상위 종료 *)
    IF i_StackTop > 0 THEN
        (* sub 복귀 ... *)
    ELSE
        i_CurrentStep := 0;
        b_Step_End    := TRUE;
        (* ... *)
        i_SeqState    := 0;

        (* [NEW] pack_idx 증가 — Main 만 수행 *)
        IF (NOT b_NoSubCall) AND (gw_PackEnable <> 0) THEN
            CASE gi_StackOrder OF
                0: (* X→Y→Z *) gi_PackIdxX := gi_PackIdxX + 1;
                               IF gi_PackIdxX >= gi_CountX THEN
                                   gi_PackIdxX := 0;
                                   gi_PackIdxY := gi_PackIdxY + 1;
                                   IF gi_PackIdxY >= gi_CountY THEN
                                       gi_PackIdxY := 0;
                                       gi_PackIdxZ := gi_PackIdxZ + 1;
                                       IF gi_PackIdxZ >= gi_CountZ THEN gi_PackIdxZ := 0; END_IF;
                                   END_IF;
                               END_IF;
                1: (* X→Z→Y *) ...
                2: (* Y→X→Z *) ...
                3: (* Y→Z→X *) ...
                4: (* Z→X→Y *) ...
                5: (* Z→Y→X *) ...
            END_CASE;
        END_IF;
    END_IF;
```

> HMI 가 DT161~163 에 임의 값을 쓰면 다음 사이클은 그 값에서 시작 (PLC 별도 처리 없음, 자연스럽게 따름).

---

## 4. PROGRAM 와이어링

### 4-1. 인스턴스 선언

```pascal
VAR
    FB_Main    : <이FB타입>;
    FB_Monitor : <이FB타입>;
    (* fb_Packing 인스턴스는 없음 — FB_Main 안으로 병합됨 *)
END_VAR
```

### 4-2. 매 스캔 호출

병합 결과 PROGRAM 호출은 **기존과 동일** — pack_base 관련 추가 인자 없음:

```pascal
FB_Main(
    (* 기존 와이어링 그대로 *)
);
FB_Monitor(
    (* 기존 와이어링 그대로 *)
);
```

### 4-3. Global Variables 에 pack 관련 DT 매핑 선언

FPWIN 의 Global Variables 탭에 아래 추가 (AT 문법은 FPWIN Pro 표기법 따름):

```pascal
VAR_GLOBAL
    (* 기존 ... *)
    (* [NEW] 파렛타이징 — HMI↔PLC 공유 *)
    gi_PackIdxX      AT %MW161.0 : INT;     (* DT161 — HMI R/W *)
    gi_PackIdxY      AT %MW162.0 : INT;     (* DT162 *)
    gi_PackIdxZ      AT %MW163.0 : INT;     (* DT163 *)
    gw_PackEnable    AT %MW217.0 : WORD;    (* DT217 — 1=활성 *)
    gdi_PitchX       AT %MD218.0 : DINT;    (* DT218~219 — 0.001mm *)
    gdi_PitchY       AT %MD220.0 : DINT;    (* DT220~221 *)
    gdi_PitchZ       AT %MD222.0 : DINT;    (* DT222~223 *)
    gi_DirX          AT %MW224.0 : INT;     (* DT224 — +1/-1 *)
    gi_DirY          AT %MW225.0 : INT;
    gi_DirZ          AT %MW226.0 : INT;
    gi_CountX        AT %MW227.0 : INT;     (* DT227 *)
    gi_CountY        AT %MW228.0 : INT;
    gi_CountZ        AT %MW229.0 : INT;
    gi_StackOrder    AT %MW230.0 : INT;     (* DT230 — 0~5 *)
END_VAR
```

> `AT` 주소 표기는 FPWIN Pro 프로젝트 설정에 맞게 `DT161` 같은 심볼명으로 바꿔 쓸 수도 있음.

---

## 6. HMI 쪽 필요 변경 (별도 작업)

### 6-1. `utils/plc_client.py`

```python
# __init__ 에 주소 추가
self.ADDR_PACK_IDX = 161   # DT161~163 (pack_idx 공유)
self.ADDR_PACK_CFG = 217   # DT217~230 (pack config HMI→PLC)

# 신규 메서드
def send_packing_config(self, cfg: dict):
    """packing_config dict 을 DT217~230 에 쓰기."""
    if not self.is_connected:
        return
    pc = cfg or {}
    # DT217: enable flag
    enabled = 1 if cfg else 0
    self.write_word(0x09, 217, enabled)
    # DT218~223: pitches (DINT, ×1000)
    for i, key in enumerate(["x_pitch", "y_pitch", "z_pitch"]):
        pitch_int = int(round(float(pc.get(key, 10.0)) * 1000))
        self.write_dint(0x09, 218 + i*2, pitch_int)
    # DT224~226: directions
    self.write_word(0x09, 224, int(pc.get("x_dir", 1)) & 0xFFFF)
    self.write_word(0x09, 225, int(pc.get("y_dir", 1)) & 0xFFFF)
    self.write_word(0x09, 226, 1)  # z_dir 고정
    # DT227~229: counts
    self.write_word(0x09, 227, int(pc.get("x_count", 1)))
    self.write_word(0x09, 228, int(pc.get("y_count", 1)))
    self.write_word(0x09, 229, int(pc.get("z_count", 1)))
    # DT230: stack_order
    self.write_word(0x09, 230, int(pc.get("stack_order", 0)))

def write_pack_idx(self, axis: str, value: int):
    """사용자 수동 변경용: pack_idx 개별 축 쓰기."""
    addr = {"x": 161, "y": 162, "z": 163}.get(axis.lower())
    if addr is None: return
    self.write_word(0x09, addr, int(value))
```

### 6-2. 스텝 시리얼라이즈 시 pack_base → wOption bit 5

`send_sequence_to_slot` 내 `_convert_json_step_to_10words` 또는 유사 함수에서:

```python
if step.get("type") == "POS":
    w_option = 0
    for i, used in enumerate(step.get("active_axes", [False]*8)):
        if used: w_option |= (1 << i)
    if step.get("pack_base"):
        w_option |= 0x0020   # bit 5
    # ...
```

### 6-3. `ui/pages/page_packing.py`

- **`_push_targets_for_idx` 제거** (더 이상 HMI가 포인트 coords 덮어쓰지 않음)
- `AxisControlPanel.disp_current` 를 **QPushButton** 으로 변경 → 클릭 시 `PackingInputOverlay` 띄워 DT161~163 직접 수정 (`plc_client.write_pack_idx`)
- `sig_packing_changed` 발화 시 `plc_client.send_packing_config(packing_config)` 호출 (main_window 또는 PagePacking 내부)
- `_on_monitor_data` 는 `pack_idx` 표시용으로만 유지

### 6-4. `ui/main_window.py`

- PLC 연결 성공 후 (`_send_mode_to_plc` 옆) `plc_client.send_packing_config(master_packing_config)` 추가
- `sig_packing_changed` → `plc_client.send_packing_config(master_packing_config)` 로 추가 연결

---

## 7. 제약 및 주의사항

1. **포인트 개수 제한**: RTEX 64 테이블 할당 정책:
   - `idx 0..59` : 일반 포인트 (총 60개, HMI `MAX_POINTS=60`)
   - `idx 60..62` : 예비 (미래 확장용)
   - `idx 63`    : 파렛타이징 스크래치 (fb_Packing 전용, RTEX 10089)

   `fb_WriteMotionTable.i_WriteCount` 최대 60 으로 클램프, HMI `plc_client.MAX_POINTS = 60`.

2. **pack_base 스텝 실행 시 50ms 지연**: 기존 POS 와 동일 (state 11 → 12 settle). 기존 비-pack_base POS 와 성능 차이 없음.

3. **동시 실행 금지**: 스크래치 테이블이 1 개 뿐이므로 **병렬 CALL 시퀀스(FB_Monitor)에서 pack_base 스텝 사용 금지**. 순차 실행 중인 Main 의 pack_base 와 모니터링 워커의 pack_base 가 겹치면 스크래치가 서로 덮어씀.

4. **알람 ID 22 매핑 완료**: `i_StepAlarmID := 22` 세팅 (state 11 에서 `i_PackBaseIdx` 범위 초과 시).
   - `ui/overlays/alarm_overlay.py` `STEP_ALARM_DESCRIPTIONS` 에 등록됨 → HMI 알람 오버레이 자동 표시
   - `plc_Readme.md` 에러 ID 표에도 반영

5. **오프셋 단위 일관성**: fb_Packing 의 `di_PitchX/Y/Z` 는 0.001mm 단위 DINT (g_Dut_Point.diPos* 와 동일 스케일). HMI 가 float mm × 1000 으로 전송.

---

## 8. 관련 파일

- **패킹 로직 본체**: `/home/yjchoi/Pendant/new_plc_fb.st` (state 11 인라인 + state 10 CMD=99 카운터)
- **참고 구현 (deprecated)**: `/home/yjchoi/Pendant/fb_Packing.st` — 별도 FB 초기 설계안. 현재 병합되어 **미사용**. 참고용으로 남겨둠
- RTEX 테이블 쓰기 패턴 참고: `/home/yjchoi/Pendant/fb_WriteMotionTable.st`
- HMI: `/home/yjchoi/Pendant/utils/plc_client.py`, `/home/yjchoi/Pendant/ui/pages/page_packing.py`
