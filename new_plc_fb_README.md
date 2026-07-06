# new_plc_fb.st 기능 및 사용 설명서

Panasonic FP0H용 시퀀스 실행 FB. 동기 CALL은 **단일 FB 내부 콜 스택**으로 처리하고, 병렬 CALL은 **2개 병렬 워커** 중 빈 워커로 분배.

---

## 1. 개요

| 항목 | 내용 |
|---|---|
| 파일 | `new_plc_fb.st` |
| 대상 PLC | Panasonic FP0H |
| 인스턴스 수 | **3개** (FB_Main + FB_Sub + FB_Worker2) |
| 콜 스택 깊이 | 4 레벨 (Main + 3단계 동기 sub) |
| 병렬 CALL 지원 | 2개 동시 실행 (병렬 워커 2개) |
| 시퀀스 슬롯 | 40개 (DT20000~DT59999) |
| 슬롯당 스텝 | 100 |

---

## 2. 주요 기능

### 시퀀스 실행
- 스텝 데이터(DT20000~)를 읽어 명령어 디스패치
- POS / OUT / IN / TMR / JMP / CALL / END 처리

### 콜 처리
- **동기 CALL** (`parallel: false`): 내부 콜 스택에 캘러 컨텍스트 푸시 → 호출된 슬롯 실행 → END 시 자동 복귀 (최대 4 레벨)
- **병렬 CALL** (`parallel: true`): 빈 병렬 워커(FB_Sub/FB_Worker2)에게 1스캔 펄스 발생 → 캘러는 즉시 다음 스텝 진행
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
FB_Sub     : <FB_Type>;   (* 병렬 CALL 워커 1 *)
FB_Worker2 : <FB_Type>;   (* 병렬 CALL 워커 2 *)
```

### FB_Main 와이어링
```pascal
FB_Main.i_SlotNo     := 0;                  (* Main 슬롯 고정 *)
FB_Main.b_NoSubCall  := FALSE;              (* CALL 허용 *)
FB_Main.b_Run        := <외부 자동운전 명령>;
FB_Main.b_ParallelBusy1 := FB_Sub.b_IsBusy;
FB_Main.b_ParallelBusy2 := FB_Worker2.b_IsBusy;
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

### 병렬 워커 와이어링
```pascal
FB_Sub.i_SlotNo     := FB_Main.i_ParallelSlot1;
FB_Sub.b_Run        := FB_Main.b_ParallelStart1;
FB_Sub.b_NoSubCall  := TRUE;      (* 병렬 워커 내부 CALL 금지 *)
FB_Sub.b_Reset      := <리셋 신호>;
FB_Sub.i_ControlCmd := DT200;

FB_Worker2.i_SlotNo     := FB_Main.i_ParallelSlot2;
FB_Worker2.b_Run        := FB_Main.b_ParallelStart2;
FB_Worker2.b_NoSubCall  := TRUE;  (* 병렬 워커 내부 CALL 금지 *)
FB_Worker2.b_Reset      := <리셋 신호>;
FB_Worker2.i_ControlCmd := DT200;
(* 나머지 외부 변수는 FB_Main과 동일하게 공유 *)
```

### 실행 순서 (중요)
PROGRAM에서 **반드시 FB_Main 먼저, 병렬 워커 나중**에 호출. 동일 스캔에 `b_ParallelStart1/2` 펄스가 각 워커의 `b_Run`으로 전달되도록.

```pascal
(* 매 스캔 *)
FB_Main(...);     (* 1 *)
FB_Sub(...);      (* 2 *)
FB_Worker2(...);  (* 3 *)
```

### HMI 모니터링 출력 매핑
```pascal
DT131 := FB_Main.i_CurrentStep;   (* 현재 스텝 *)
DT132 := FB_Main.i_CurrentSlot;   (* 현재 슬롯 번호 *)
DT133 := FB_Main.i_StackDepth;    (* 스택 깊이 *)
DT134 := FB_Sub.i_CurrentSlot;    (* 병렬 워커1 슬롯 *)
DT135 := FB_Sub.i_CurrentStep;    (* 병렬 워커1 스텝 *)
DT126 := FB_Worker2.i_CurrentSlot;(* 병렬 워커2 슬롯 *)
DT127 := FB_Worker2.i_CurrentStep;(* 병렬 워커2 스텝 *)
```

---

## 4. 시퀀스 명령어

스텝 데이터 1개당 10 Words. `iCommand` 매핑:

| Cmd | 명령 | 의미 | wOption | diParam1 | diParam2 | diParam3 | diParam4 |
|---|---|---|---|---|---|---|---|
| 10 | POS | 위치이동 | 사용축 비트마스크 (+bit8 패킹베이스) | 포인트 인덱스 | 이행 0:완료후 / 1:동시 | - | - |
| 20 | OUT | 출력 | 0=OFF / 1=ON | 포트 번호 | 0:시스템/1:밸브/2:내부 | 지연시간(0=즉시) | - |
| 21 | IN | 입력대기 | 0=OFF대기 / 1=ON대기 | 포트 번호 | 타임아웃(×0.01s) | 0:계속/1:알람정지/2:알람진행 | 알람번호 |
| 30 | TMR | 타이머 | 0=일반 / 1=신호유지(p3=1) | 시간(×0.01s) | 포트(hold용) | 0:단순/1:hold | - |
| 40 | JMP | 점프 | 0=무조건 / 1=조건부 / 2=데이터비교 | 타겟 스텝(0~99) | (opt1)0:포트/1:모드/2:상태 · (opt2)비교 DT주소 | (opt1)조건값/포트 · (opt2)연산자 | (opt1)조건 ON(1)/OFF(0) · (opt2)비교상수 |
| 50 | CALL | 호출 | 0=동기 / 1=병렬 | 슬롯 번호(0~39) | - | - | - |
| 99 | END | 종료 | - | - | - | - | - |

### 포트 번호 영역
| 범위 | 의미 |
|---|---|
| 0~15 | 시스템 입력 X0~X15 |
| 32~47 | 시스템 입력 X20~X2F |
| 100~115 | 내부 비트 M0~M15 |
| 116~131 | 내부 비트 M16~M31 |

### POS 이행 모드 (diParam2)
POS(위치이동) 스텝의 `diParam2` 로 이동 완료 후 다음 스텝 진행 방식을 지정한다.

| diParam2 | 모드 | 동작 |
|---|---|---|
| `0` | 완료 후 이행 (기본) | 기동 확인(BUSY 상승) → **완료 대기(state 30, BUSY 하강)** → 다음 스텝. 기존 동작과 동일 |
| `1` | 동시 이행 | 기동 확인(BUSY 상승)만 하고 **즉시 다음 스텝**으로 진행. 이동은 백그라운드로 계속됨 |

- `diParam2` 미설정(0) 시 기존 레시피와 100% 동일하게 동작 (하위호환).
- 두 모드 모두 "이미 목표 위치(INP=TRUE, BUSY 미상승)" 백업 판정과 기동 실패 에러 21 로직은 동일하게 적용된다.
- 동시 이행한 축의 **완료를 이후 스텝에서 대기하는 표준 명령은 없다.** 타이밍은 후속 TMR/IN 스텝으로 레시피 작성자가 책임진다.
- 동일 축에 대한 후속 POS 가 진행 중 이동을 덮어쓴다. 보통 다른 축 / OUT·타이머 등 비축 작업과 겹칠 때 사용.
- HMI 레시피 키: POS 스텝의 `wait_completion` (bool). 누락/`true`=완료 후 이행, `false`=동시 이행.

### JMP 데이터값 비교 (wOption=2)
JMP 스텝에서 DT 레지스터 값을 상수와 비교해, 참이면 타겟 스텝으로 점프한다. (HMI "이동 조건 → 데이터값")
비교 대상은 미사용 영역 **DT60000~DT60099 (100워드)** 로 한정하며, FB 는 글로벌 `g_DTPool`(VAR_EXTERNAL 직접참조) 로 읽는다. (`g_SeqData` 와 동일 방식 — 복사·배선 없음, 스텝 최소)

| 파라미터 | 의미 |
|---|---|
| `wOption` | `2` (데이터값 비교 모드) |
| `diParam1` | 타겟 스텝 (0~99) |
| `diParam2` | 비교 대상 DT 절대주소 (**60000~60099**) |
| `diParam3` | 연산자 — `0:=` `1:≠` `2:>` `3:≥` `4:<` `5:≤` |
| `diParam4` | 비교 상수 (16비트 부호 INT) |

- 비교식: `DT[diParam2] <연산자> diParam4` 가 참이면 `diParam1` 스텝으로 점프, 거짓이면 다음 스텝.
- `diParam4` 는 **상수**이므로 조건부(opt1)의 ON/OFF 반전 로직을 적용하지 않는다.
- **전역변수 필요** (`g_SeqData` 와 동일하게 VAR_EXTERNAL 직접참조 → 배선 불필요, 복사 없음, 스텝 최소):
  - GVL: `g_DTPool AT DT60000 : ARRAY[0..99] OF INT;` (미사용 DT60000~60099 별칭)
  - FB 변수표: **VAR_EXTERNAL** `g_DTPool : ARRAY[0..99] OF INT;` (AT 절은 GVL 에만, VAR_EXTERNAL 은 이름·타입만 일치)
  - FB 본문은 절대주소를 DINT 로 비교 후 인덱스만 변환해 `g_DTPool[diParam2 - 60000]` 로 직접 참조한다.
  - ⚠ 주소 60000 은 INT(±32767) 초과 → `diParam2`(DINT)를 `DINT#60000`/`DINT#60099` 와 DINT 비교하고, 인덱스(0~99)만 `DINT_TO_INT` 변환. INT 변수로 주소를 받으면 형식 불일치 컴파일 에러.
  - 글로벌이라 FB 가 읽기/쓰기 모두 가능. DT60000~60099 는 HMI/래더 등 외부에서도 자유롭게 기록 가능(실제 DT 메모리).
- 값은 **단일 DT 1워드(16비트 부호 INT)** 로 읽는다. 32비트(DDT) 비교는 미지원.
- DT 주소가 60000~60099 범위를 벗어나면 **알람 23** (DT 비교 주소 범위 초과) 발생, 점프하지 않고 에러 정지.
- HMI 레시피 키: `cond_type:"DTCMP"`, `cmp_dt_addr`(DT 절대주소 60000~60099), `cmp_op`(0~5), `cmp_const`(상수). `cond_on` 은 무시됨.
- ⚠ 이 분기는 PLC FB(`new_plc_fb.st`)를 **빌드 후 PLC 로 다운로드**해야 동작한다. 실장비 검증 전 라이브 레시피 투입 금지.

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
| 50 | 병렬 CALL 실패 | 병렬 워커 2개 모두 실행중 |
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
| 인스턴스 수 | 4 (Main / Sub / SubSub / +1) | **3 (Main / 병렬 워커 2개)** |
| PLC 메모리 | ~13,900 스텝 (4×3,475) | ~10,500 스텝 목표 (3×3,500) |
| CALL 라우팅 | 외부 와이어 (b_CallStart, b_SubDone 등) | **내부 콜 스택** |
| 병렬 CALL 슬롯 | 다중 (3 인스턴스) | **2개 (빈 워커 자동 배정)** |
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
2. 3 인스턴스(Main + 병렬 워커 2개) 통합 후 전체 프로젝트 스텝 수 확인 (목표 ~15,000 이하)

### 단위 동작 테스트 (시뮬레이터/실기)
1. **Main 단순 실행** (CALL 없음): POS/OUT/TMR 정상 동작
2. **1단계 동기 CALL**: Main → Sub → END → Main 복귀
3. **3단계 중첩 CALL**: Main → A → B → C → 정상 복귀
4. **4단계 시도**: 에러 93 발생 확인
5. **병렬 CALL 1개**: parallel=true CALL → FB_Sub 기동, FB_Main 즉시 다음 스텝
6. **병렬 CALL 2개**: 두 번째 parallel=true CALL → FB_Worker2 기동
7. **병렬 CALL 3개 시도**: 두 워커가 모두 Busy이면 에러 50
8. **확인운전 모드**: i_ControlCmd=2일 때 동기 CALL 정상
9. **서브 에러 전파**: 동기 sub의 POS 실패 → state 900 진입
10. **병렬 워커에서 CALL 시도**: 에러 94 발생 확인

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
2개 초과 병렬 시퀀스가 필요하면 `b_ParallelBusyN`, `i_ParallelSlotN`, `b_ParallelStartN` 세트를 같은 패턴으로 추가.

---

## 10. 관련 파일

- 본체: `/home/yjchoi/Pendant/new_plc_fb.st`
- 폐기 예정: `/home/yjchoi/Pendant/fb_call_executor.st` (영구 미사용)
- PLC 일반 노트: `/home/yjchoi/Pendant/plc_Readme.md`
- 설계 계획서: `/home/yjchoi/.claude/plans/elegant-booping-cosmos.md`
- HMI 통신: `/home/yjchoi/Pendant/utils/plc_client.py`
- HMI 하이라이트: `/home/yjchoi/Pendant/ui/pages/page_position.py`
