# new_plc_fb.st 기능 및 사용 설명서

Panasonic FP0H용 시퀀스 실행 FB. 기존 `plc_fb.st`(4 인스턴스 / 3-tier 직접배선)를 **단일 FB + 내부 콜 스택** 구조로 통합. **2 인스턴스만 사용** → PLC 메모리 약 7,000~8,300 스텝 절감 목표.

---

## 1. 개요

| 항목 | 내용 |
|---|---|
| 파일 | `new_plc_fb.st` |
| 대상 PLC | Panasonic FP0H |
| 인스턴스 수 | **2개** (FB_Main + FB_Monitor) |
| 콜 스택 깊이 | 4 레벨 (Main + 3단계 동기 sub) |
| 병렬 CALL 지원 | 1개 슬롯 (FB_Monitor 전담) |
| 시퀀스 슬롯 | 40개 (DT20000~DT59999) |
| 슬롯당 스텝 | 100 |

---

## 2. 주요 기능

### 시퀀스 실행
- 스텝 데이터(DT20000~)를 읽어 명령어 디스패치
- POS / OUT / IN / TMR / JMP / CALL / END 처리

### 콜 처리
- **동기 CALL** (`parallel: false`): 내부 콜 스택에 캘러 컨텍스트 푸시 → 호출된 슬롯 실행 → END 시 자동 복귀 (최대 4 레벨)
- **병렬 CALL** (`parallel: true`): 외부 워커(FB_Monitor)에게 1스캔 펄스 발생 → 캘러는 즉시 다음 스텝 진행
- 자기 호출 / 범위 외 슬롯 / 스택 오버플로 에러 처리

### 출력 제어
- 시스템 출력 / 밸브 출력 / 내부 비트 단위 ON/OFF
- 지연 출력 2슬롯 (백그라운드 타이머, 캘러는 다음 스텝 진행)

### 입력 대기
- 시스템 입력 / 내부 비트 / R 입력(통신) 5개 영역 지원
- 타임아웃 + 작업자 대응 분기 (계속 / 알람정지 / 알람진행)

### 모니터링 출력
- `i_CurrentStep`: 현재 실행 중 스텝
- `i_CurrentSlot`: 현재 실행 중 슬롯 번호
- `i_StackDepth`: 콜 스택 깊이 (0=Main, 3=최대)
- `b_IsBusy`: 실행 중 여부 (i_SeqState ≠ 0 또는 스택 ≠ 0)

---

## 3. 인스턴스 구성 및 PROGRAM 와이어링

### 인스턴스 선언
```pascal
FB_Main    : <FB_Type>;   (* 메인 + 모든 동기 CALL *)
FB_Monitor : <FB_Type>;   (* 병렬 CALL 대상 (모니터링 시퀀스 전담) *)
```

### FB_Main 와이어링
```pascal
FB_Main.i_SlotNo     := 0;                  (* Main 슬롯 고정 *)
FB_Main.b_NoSubCall  := FALSE;              (* CALL 허용 *)
FB_Main.b_Run        := <외부 자동운전 명령>;
FB_Main.b_Reset      := <리셋 신호>;
FB_Main.i_ControlCmd := DT200;              (* 0=정지, 1=자동, 2=확인운전 *)
FB_Main.i_CheckRunState := DT202;
FB_Main.w_ServoBusy  := <서보 Busy 워드>;
FB_Main.w_ServoDone  := <서보 Done 워드>;
FB_Main.w_Input0     := <입력 워드 0>;
FB_Main.w_Input1     := <입력 워드 1>;
FB_Main.w_ModeWord0  := DT206;
FB_Main.w_ModeWord1  := DT207;
FB_Main.w_ModeWord2  := DT208;
FB_Main.t_WaitTime   := t#100ms;             (* POS 기동 확인 대기 *)
(* IN_OUT *)
FB_Main.w_system_Output := <시스템 출력 워드>;
FB_Main.w_Valve_Output  := DT204;
FB_Main.w_internal_Bit0 := DT300;
FB_Main.w_internal_Bit1 := DT301;
```

### FB_Monitor 와이어링
```pascal
FB_Monitor.i_SlotNo    := FB_Main.i_ParallelSlot;     (* 병렬 호출된 슬롯 번호 *)
FB_Monitor.b_Run       := FB_Main.b_ParallelStart;    (* 병렬 호출 펄스로 기동 *)
FB_Monitor.b_NoSubCall := TRUE;                       (* CALL 시도 시 에러 94 *)
FB_Monitor.b_Reset     := <리셋 신호>;                (* 같은 신호 공유 *)
FB_Monitor.i_ControlCmd := DT200;
(* 나머지 외부 변수는 FB_Main과 동일하게 공유 *)
```

### 실행 순서 (중요)
PROGRAM에서 **반드시 FB_Main 먼저, FB_Monitor 나중**에 호출. 동일 스캔에 `b_ParallelStart` 펄스가 FB_Monitor의 `b_Run`으로 전달되도록.

```pascal
(* 매 스캔 *)
FB_Main(...);     (* 1 *)
FB_Monitor(...);  (* 2 *)
```

### HMI 모니터링 출력 매핑
```pascal
DT131 := FB_Main.i_CurrentStep;   (* 현재 스텝 *)
DT132 := FB_Main.i_CurrentSlot;   (* 현재 슬롯 번호 *)
DT133 := FB_Main.i_StackDepth;    (* 스택 깊이 *)
```

---

## 4. 시퀀스 명령어

스텝 데이터 1개당 10 Words. `iCommand` 매핑:

| Cmd | 명령 | 의미 | wOption | diParam1 | diParam2 | diParam3 | diParam4 |
|---|---|---|---|---|---|---|---|
| 10 | POS | 위치이동 | 사용축 비트마스크 | 포인트 인덱스 | - | - | - |
| 20 | OUT | 출력 | 0=OFF / 1=ON | 포트 번호 | 0:시스템/1:밸브/2:내부 | 지연시간(0=즉시) | - |
| 21 | IN | 입력대기 | 0=OFF대기 / 1=ON대기 | 포트 번호 | 타임아웃(×0.01s) | 0:계속/1:알람정지/2:알람진행 | 알람번호 |
| 30 | TMR | 타이머 | 0=일반 / 1=신호유지(p3=1) | 시간(×0.01s) | 포트(hold용) | 0:단순/1:hold | - |
| 40 | JMP | 점프 | 0=무조건 / 1=조건부 | 타겟 스텝(0~99) | 0:포트/1:모드/2:상태 | 조건값/포트 | 조건 ON(1)/OFF(0) |
| 50 | CALL | 호출 | 0=동기 / 1=병렬 | 슬롯 번호(0~39) | - | - | - |
| 99 | END | 종료 | - | - | - | - | - |

### 포트 번호 영역
| 범위 | 의미 |
|---|---|
| 0~15 | 시스템 입력 X0~X15 |
| 32~47 | 시스템 입력 X20~X2F |
| 100~115 | 내부 비트 M0~M15 |
| 116~131 | 내부 비트 M16~M31 |

---

## 5. 콜 스택 동작 상세

### 푸시 (동기 CALL)
```
[직전]  i_StackTop = 0,  ctx[0] = {Main, step=5, state=10}
              ↓ CALL 슬롯 7
[푸시]  i_StackTop = 1,  ctx[0] = {Main, step=6, state=10}  ← 캘러 다음 스텝 보존
                         ctx[1] = {7,    step=0, state=10}  ← 새 컨텍스트
```

### 팝 (END)
```
[직전]  i_StackTop = 1,  ctx[1] = {7, step=15, state=10}, cmd=99
              ↓ END
[팝]    i_StackTop = 0,  ctx[0]에서 캘러 재로드 → step=6부터 실행
```

### 스택 오버플로
- 깊이 3에서 동기 CALL 시도 → 에러 93, state=900 진입
- Main → A → B → C → D 시도 시 D가 거절됨

### 일시정지 후 재개
- `i_ControlCmd = 0` (정지) 시 i_StackTop과 ctx[*] 보존
- 다시 자동 시작 시 보존된 위치에서 재개
- 완전 초기화는 `b_Reset`

---

## 6. 에러 코드

| ID | 의미 | 발생 조건 |
|---|---|---|
| 21 | POS 축 이동 확인 실패 | 기동 후 t_WaitTime 내 Done 신호 미수신 |
| 50 | (예약, 미사용) | - |
| 93 | 콜 스택 오버플로 | i_StackTop=3에서 동기 CALL |
| 94 | CALL 사용 불가 | b_NoSubCall=TRUE 인스턴스에서 CALL 시도 |
| 95 | JMP 타겟 범위 초과 | 0~99 외 |
| 96 | CALL 슬롯 범위 초과 | 0~39 외 |
| 97 | 실행 슬롯 범위 초과 | i_SlotNo가 0~39 외 |
| 98 | OUT 지연 타이머 슬롯 부족 | 2슬롯 모두 사용 중 |
| 99 | 알 수 없는 커맨드 | iCommand가 미정의 값 |

---

## 7. 기존 plc_fb.st와의 차이점

| 항목 | 기존 (plc_fb.st) | 신규 (new_plc_fb.st) |
|---|---|---|
| 인스턴스 수 | 4 (Main / Sub / SubSub / +1) | **2 (Main / Monitor)** |
| PLC 메모리 | ~13,900 스텝 (4×3,475) | ~7,000 스텝 목표 (2×3,500) |
| CALL 라우팅 | 외부 와이어 (b_CallStart, b_SubDone 등) | **내부 콜 스택** |
| 병렬 CALL 슬롯 | 다중 (3 인스턴스) | **1개 (Monitor 전담)** |
| 동기 CALL 깊이 | 3 | **4** |
| 와이어링 복잡도 | FB간 신호 8~10개 | 외부 입출력만 |
| State 81/82 | 서브 완료 대기 | **삭제됨** |
| 서브 에러 전파 | b_SubError 와이어 | 내부 i_StepAlarmID 즉시 반영 |

### 와이어링 변수 변경
| 기존 | 신규 |
|---|---|
| `b_CallStart` | `b_ParallelStart` |
| `i_CallSlotOut` | `i_ParallelSlot` |
| `b_CallParallelOut` | (제거 - b_ParallelStart 발화 = 병렬) |
| `b_SubDone`, `b_SubError`, `b_SubBusy` | (제거) |
| `b_NoSubCall` | (유지 - Monitor 인스턴스용 플래그) |

---

## 8. 검증 절차

### 컴파일 단계
1. FPWIN Pro/GR에서 `new_plc_fb.st`만 단일 인스턴스로 임시 컴파일 → 인스턴스당 스텝 수 측정
2. 2 인스턴스(Main + Monitor) 통합 후 전체 프로젝트 스텝 수 확인 (목표 ~15,000 이하)

### 단위 동작 테스트 (시뮬레이터/실기)
1. **Main 단순 실행** (CALL 없음): POS/OUT/TMR 정상 동작
2. **1단계 동기 CALL**: Main → Sub → END → Main 복귀
3. **3단계 중첩 CALL**: Main → A → B → C → 정상 복귀
4. **4단계 시도**: 에러 93 발생 확인
5. **병렬 CALL**: parallel=true CALL → FB_Monitor 기동, FB_Main 즉시 다음 스텝
6. **모니터링 무한 루프**: FB_Monitor의 JMP 반복 동작
7. **모니터링 정지**: b_Reset 또는 i_ControlCmd=0 시 정지
8. **확인운전 모드**: i_ControlCmd=2일 때 동기 CALL 정상
9. **서브 에러 전파**: 동기 sub의 POS 실패 → state 900 진입
10. **Monitor에서 CALL 시도**: 에러 94 발생 확인

### HMI 통합
1. `utils/plc_client.py` DT132/133 키 명확화 (`sub_seq_idx` → `current_slot`, `sub_step` → `stack_depth`)
2. `ui/pages/page_position.py:_update_realtime_values` 슬롯번호 → 시퀀스명 매핑 추가
3. `_highlight_step` 호출 조건 보강 (현재 보는 시퀀스 = 실행 중 슬롯일 때만)

### 회귀 테스트
- M0665 레시피 다운로드 → 자동운전 1사이클 → `total_count` 증가 확인
- 안전문 강제 개방 시뮬레이션 → 모니터링 알람 정상 동작

---

## 9. 향후 추가 최적화 (TODO)

1차 컴파일 후 메모리가 더 필요하면 적용:

### Option A 8-1: 포트→비트 매핑 헬퍼
state 61, 51, 70 세 곳의 동일 패턴을 별도 FB로 추출. 약 100~150 스텝 추가 절감 예상. 단, FB 추출은 인스턴스화 비용 발생 — 컴파일 결과 확인 필수.

### Option A 8-3: OUT 출력 타입 분기 단순화
state 40의 4-way 분기를 워드 포인터 배열 또는 헬퍼로 통합. ST 표현이 어색할 수 있어 검토 필요.

### 병렬 워커 추가
미래에 모니터링 외 병렬 시퀀스가 필요하면 FB_Monitor 옆에 워커 인스턴스 1개 추가 (각 +3,500 스텝).

---

## 10. 관련 파일

- 본체: `/home/yjchoi/Pendant/new_plc_fb.st`
- 기존 (참고): `/home/yjchoi/Pendant/plc_fb.st`
- 폐기 예정: `/home/yjchoi/Pendant/fb_call_executor.st` (영구 미사용)
- PLC 일반 노트: `/home/yjchoi/Pendant/plc_Readme.md`
- 설계 계획서: `/home/yjchoi/.claude/plans/elegant-booping-cosmos.md`
- HMI 통신: `/home/yjchoi/Pendant/utils/plc_client.py`
- HMI 하이라이트: `/home/yjchoi/Pendant/ui/pages/page_position.py`
