(* ===========================================================================
   [FB 본문]  ── 2개 인스턴스 + 내부 콜 스택 운용 ──
   (구버전 plc_fb.st 의 4-인스턴스 / 3-tier 구조를 단일 FB + 콜 스택으로 통합)

   ─ PROGRAM 인스턴스 선언 ─
       FB_Main    : <이FB타입명>;   (* 슬롯 0 + 모든 동기 CALL 처리 *)
       FB_Monitor : <이FB타입명>;   (* 병렬 CALL 대상 (모니터링) 1개 전담 *)

   ─ PROGRAM 배선 ─
       (* FB_Main *)
       FB_Main.i_SlotNo     := 0;                    (* Main 슬롯 고정 *)
       FB_Main.b_NoSubCall  := FALSE;                (* CALL 허용 *)
       FB_Main.b_Run        := <외부 자동운전 명령>;
       FB_Main.i_ControlCmd := DT200;
       FB_Main.t_WaitTime   := T#500MS;              (* ★ 필수 - state 21 BUSY 감지 타임아웃 *)
       (* 서보/입력/모드 등 외부 변수 연결 *)

       (* FB_Monitor *)
       FB_Monitor.i_SlotNo    := FB_Main.i_ParallelSlot;   (* 병렬 호출된 슬롯 *)
       FB_Monitor.b_Run       := FB_Main.b_ParallelStart;  (* 1스캔 기동 펄스 *)
       FB_Monitor.b_NoSubCall := TRUE;                     (* Monitor에서 CALL 시 에러 94 *)
       FB_Monitor.i_ControlCmd := DT200;                   (* 같은 명령 공유 *)
       FB_Monitor.t_WaitTime   := T#500MS;                 (* ★ 필수 - state 21 BUSY 감지 타임아웃 *)
       (* 동일한 외부 변수 공유 *)

       (* 실행 순서: FB_Main → FB_Monitor (동일 스캔에서 ParallelStart 펄스 전달) *)

       (* HMI 모니터링 (DT131~135) *)
       DT131 := FB_Main.i_CurrentStep;      (* Main 현재 실행 중 스텝 *)
       DT132 := FB_Main.i_CurrentSlot;      (* Main 현재 실행 중 슬롯 번호 *)
       DT133 := FB_Main.i_StackDepth;       (* Main 콜 스택 깊이 0~3 *)
       DT134 := FB_Monitor.i_CurrentSlot;   (* Monitor 병렬 실행 중 슬롯 (0=idle) *)
       DT135 := FB_Monitor.i_CurrentStep;   (* Monitor 병렬 실행 중 스텝 *)

   ─ 스텝 데이터 메모리 레이아웃 (DT20000~, 슬롯당 1000 Words) ─
       Word +0  : iCommand  (WORD)
       Word +1  : wOption   (WORD)
       Word +2~3: diParam1  (DINT, Low/High)
       Word +4~5: diParam2  (DINT, Low/High)
       Word +6~7: diParam3  (DINT, Low/High)
       Word +8~9: diParam4  (DINT, Low/High)

   ─ VAR_INPUT ─
       i_SlotNo        : INT;    (* 시작 슬롯 (Main=0). 시작 시 래치됨 *)
       b_Run           : BOOL;
       b_Reset         : BOOL;   (* 운전정지 상승펄스. 스택/타이머/SystemOutput/InternalBit 초기화 (에러/Valve 유지) *)
       b_AlarmReset    : BOOL;   (* [NEW] 알람 리셋 상승펄스 (DT212). UserAlarm/StepAlarm 모두 클리어 *)
       b_NoSubCall     : BOOL;   (* TRUE면 이 인스턴스는 CALL 불가 (Monitor용). 시도 시 에러 94 *)

       w_ServoBusy     : WORD;
       w_ServoDone     : WORD;
       w_Input0        : WORD;
       w_Input1        : WORD;
       w_ModeWord0     : WORD;
       w_ModeWord1     : WORD;
       w_ModeWord2     : WORD;
       t_WaitTime      : TIME;   (* ★ state 21 BUSY 상승 감지 타임아웃. PROGRAM에서 T#500MS 이상으로 반드시 배선.
                                     미배선(T#0s) 시 BUSY 못 잡고 에러 21 남발됨 *)
       w_AxisEnable    : WORD;   (* [NEW] 실 사용 축 비트마스크 (DT15000, bit0~7 = 1~8축).
                                     POS 스텝의 w_StepOpt 과 AND 마스킹하여 미연결 축 명령 자동 스킵.
                                     → 3축/5축 공용 레시피 지원. *)

   ─ VAR_IN_OUT ─
       i_ControlCmd    : INT;    (* 0=정지, 1=자동, 2=확인운전 *)
       i_CheckRunState : INT;
       w_system_Output : WORD;
       w_Valve_Output  : WORD;
       w_internal_Bit0 : WORD;
       w_internal_Bit1 : WORD;
       w_UserAlarm     : WORD;   (* [구 w_UserAlarm] IN 스텝에서 사용자가 정의한 알람 번호 → DT159.
                                    VAR_IN_OUT - Main/Monitor 공유. 0=알람없음. *)
       b_StepAlarm     : BOOL;   (* [구 b_StepAlarm] 스텝 진행 에러 플래그. PROGRAM에서 자동정지 트리거 조건으로 사용.
                                    VAR_IN_OUT - Main/Monitor 공유. *)
       i_StepAlarmID   : INT;    (* [구 i_StepAlarmID] 스텝 진행 에러 코드 → DT160. 0=정상.
                                    VAR_IN_OUT - Main/Monitor 공유. *)

   ─ VAR_OUTPUT ─
       b_StepDone      : BOOL;
       b_Step_End      : BOOL;
       b_IsBusy        : BOOL;
       i_CurrentStep   : INT;    (* 현재 실행 중 스텝 (스택 top 기준) *)
       i_CurrentSlot   : INT;    (* [NEW] 현재 실행 중 슬롯 번호 *)
       i_StackDepth    : INT;    (* [NEW] 콜 스택 깊이 0~3 *)
       i_ParallelSlot  : INT;    (* [renamed from i_CallSlotOut] 병렬 CALL 대상 슬롯 *)
       b_ParallelStart : BOOL;   (* [renamed from b_CallStart] 병렬 CALL 1스캔 기동 펄스 *)

   ─ 스텝 알람 ID (i_StepAlarmID) ─
       21 : POS 축 이동 확인 실패 (BUSY 상승 미감지 - 트리거 거부 또는 RTEX 전파 실패)
       22 : 패킹 베이스 인덱스 범위 오류 (pack_base 스텝의 point_index 가 0~59 초과)
       50 : (예약, 미사용)
       93 : 동기 CALL 스택 오버플로 (4 레벨 초과)
       94 : CALL 사용 불가 (이 인스턴스는 b_NoSubCall=TRUE)
       95 : JMP 타겟 스텝 번호 범위 초과(0~99)
       96 : CALL 슬롯 번호 범위 초과(0~39)
       97 : 실행 슬롯 번호 범위 초과(0~39)
       98 : OUT 지연 타이머 슬롯 없음(5개 모두 사용중)
       99 : 알 수 없는 커맨드

   ─ VAR (내부) ─
       (* === [NEW] 콜 스택 (4 레벨) === *)
       ctx_SlotNo      : ARRAY[0..3] OF INT;
       ctx_CurrentStep : ARRAY[0..3] OF INT;
       ctx_SeqState    : ARRAY[0..3] OF INT;
       i_StackTop      : INT;    (* 0 = 최상위, 3 = 최대 깊이 *)

       (* 슬롯/스텝 작업 변수 (스캔마다 ctx[i_StackTop]에서 로드 → 끝에 저장) *)
       (* 전역변수 필요: g_SeqData AT DT20000 : ARRAY[0..3999] OF DUT_STEP_DATA *)
       i_ActiveSlotNo  : INT;
       di_StepBase     : DINT;
       i_StepCmd       : INT;
       w_StepOpt       : WORD;
       di_StepP1       : DINT;
       di_StepP2       : DINT;
       di_StepP3       : DINT;
       di_StepP4       : DINT;
       i_SeqState      : INT;

       (* 서보 *)
       arr_bBusy       : ARRAY[1..5] OF BOOL;
       arr_bDone       : ARRAY[1..5] OF BOOL;
       arr_bStart      : ARRAY[1..5] OF BOOL;
       i_LoopAxis      : INT;
       b_AnyBusy       : BOOL;
       b_AllDone       : BOOL;
       i_WriteTableNo  : INT;
       w_WriteAddr     : WORD;
       w_EffOpt        : WORD;   (* [NEW] POS 스텝 실 사용 축 비트 = w_StepOpt AND w_AxisEnable *)

       (* [NEW] 파렛타이징 — state 11 인라인 계산용 작업 변수 *)
       i_PackBaseIdx   : INT;    (* 현재 pack_base 스텝의 포인트 인덱스 *)
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

       (* ─ 사용하는 GLOBAL (PROGRAM Global Variables 에 AT 매핑으로 선언) ─
          gw_PackEnable    AT DT217 : WORD    (1 = 패킹 활성, 0 = 미사용)
          gdi_PitchX  AT DT218~219 : DINT    (X 피치, 0.001mm)
          gdi_PitchY  AT DT220~221 : DINT
          gdi_PitchZ  AT DT222~223 : DINT
          gi_DirX          AT DT224 : INT    (+1 / -1)
          gi_DirY          AT DT225 : INT
          gi_DirZ          AT DT226 : INT    (보통 +1)
          gi_CountX        AT DT227 : INT    (X 스택 횟수)
          gi_CountY        AT DT228 : INT
          gi_CountZ        AT DT229 : INT
          gi_StackOrder    AT DT230 : INT    (0~5)
          gi_PackIdxX      AT DT161 : INT    (현재 X 스택 인덱스, 0-based, HMI 도 R/W)
          gi_PackIdxY      AT DT162 : INT
          gi_PackIdxZ      AT DT163 : INT
          ※ g_Dut_Point / gi_SpeedOverride / gi_*축AccDec / gdi_*축PPR 는 기존 공유 *)

       (* 출력 제어 *)
       i_OutIndex      : INT;
       i_OutType       : INT;
       w_InputMask     : WORD;
       w_BitMask       : WORD;

       (* 입력 대기 *)
       i_WaitPort      : INT;
       t_InputTimeout  : TIME;
       b_InputWaitStart : BOOL;
       b_InputWaitDone  : BOOL;
       b_CurrentInput   : BOOL;
       b_InputCondMet   : BOOL;
       b_TimeoutImmediate : BOOL;

       (* 타이머 (단일 인스턴스로 충분 - 한 시점에 활성 컨텍스트 1개) *)
       tmr_StartWait   : TON;
       b_TimerStart    : BOOL;
       b_WaitDone      : BOOL;
       tmr_StepDelay   : TON;
       b_DelayStart    : BOOL;
       b_DelayDone     : BOOL;
       t_DelaySetting  : TIME;
       tmr_InputWait   : TON;
       tmr_HoldTimer   : TON;
       b_HoldTimerStart : BOOL;
       b_HoldDone      : BOOL;
       b_HoldInput     : BOOL;
       i_HoldPort      : INT;
       t_HoldSetting   : TIME;

       (* [NEW] POS state 12 - 테이블 쓰기 후 RTEX 전파 대기 *)
       tmr_Settle      : TON;
       b_SettleStart   : BOOL;
       b_SettleDone    : BOOL;
       t_SettleTime    : TIME;   (* 내부 고정 T#50MS *)

       (* [NEW] POS state 21 - BUSY 상승 래치 (silent advance 방지) *)
       b_BusySeen      : BOOL;

       (* [MODIFIED] 타이머 기동후출력 (FP0H DUT 패턴, ARRAY 사용) *)
       at_OD             : ARRAY[0..4] OF TON_FUN_INSTANCE_DUT;
       b_OutDelayStart   : ARRAY[0..4] OF BOOL;
       b_OutDelayPending : ARRAY[0..4] OF BOOL;
       t_OutDelaySetting : ARRAY[0..4] OF TIME;
       i_OutDelayPort    : ARRAY[0..4] OF INT;
       i_OutDelayType    : ARRAY[0..4] OF INT;
       w_OutDelayOpt     : ARRAY[0..4] OF WORD;
       i_OutDelaySlot    : INT;
       i_OutDelayFind    : INT;
       b_OutDelayQ       : BOOL;   (* TON_FUN 임시 출력 Q *)
       t_OutDelayET      : TIME;   (* TON_FUN 임시 출력 ET - 사용 안 하지만 바인딩 필수 *)

       (* JMP *)
       i_JmpPort       : INT;
       i_JmpBit        : INT;
       b_JmpCond       : BOOL;
       b_JmpDoJump     : BOOL;

       (* CALL *)
       i_CallSlot      : INT;
       b_CallParallel  : BOOL;

       (* 에지 검출 *)
       b_RunPrev       : BOOL;
       b_RunRising     : BOOL;
       b_CheckRunPrev  : BOOL;
       b_CheckRunRising : BOOL;

       (* 기타 *)
       w_PopupResp     : WORD;
=========================================================================== *)


(* ── 0. 펄스 클리어 + 상승 에지 검출 ── *)
b_ParallelStart  := FALSE;   (* 이전 스캔 발생 펄스 자동 클리어 *)
b_RunRising      := b_Run AND NOT b_RunPrev;
b_RunPrev        := b_Run;
b_CheckRunRising := (i_CheckRunState = 1) AND NOT b_CheckRunPrev;
b_CheckRunPrev   := (i_CheckRunState = 1);


(* ── 1. 서보 상태 입력 매핑 ── *)
FOR i_LoopAxis := 1 TO 5 DO
    arr_bBusy[i_LoopAxis] := (w_ServoBusy AND SHL(WORD#1, INT_TO_WORD(7 + i_LoopAxis))) <> 0;
    arr_bDone[i_LoopAxis] := (w_ServoDone AND SHL(WORD#1, INT_TO_WORD(i_LoopAxis - 1))) <> 0;
END_FOR;


(* ── 리셋 (운전정지 상승펄스) ──
   정지 시 초기화: 콜스택, 시퀀스 상태, 타이머, SystemOutput, 내부비트 (Bit0/Bit1)
   정지 시 보존 : b_StepAlarm/i_StepAlarmID/w_UserAlarm (알람 유지), Valve_Output (척/진공 등 물림 보호)
*)
IF b_Reset THEN
    (* 콜 스택 전체 클리어 *)
    FOR i_LoopAxis := 0 TO 3 DO
        ctx_SlotNo[i_LoopAxis]      := 0;
        ctx_CurrentStep[i_LoopAxis] := 0;
        ctx_SeqState[i_LoopAxis]    := 0;
    END_FOR;
    i_StackTop       := 0;
    i_ActiveSlotNo   := 0;
    i_CurrentStep    := 0;
    i_SeqState       := 0;
    i_CurrentSlot    := 0;
    i_StackDepth     := 0;

    (* [변경] 에러 필드는 Reset에서 클리어하지 않음 → b_AlarmReset 경로에서만 클리어 *)
    b_StepDone       := FALSE;
    b_Step_End       := FALSE;
    b_IsBusy         := FALSE;
    b_TimerStart     := FALSE;
    b_DelayStart     := FALSE;
    b_InputWaitStart := FALSE;
    b_HoldTimerStart := FALSE;
    b_SettleStart    := FALSE;
    b_BusySeen       := FALSE;
    FOR i_OutDelaySlot := 0 TO 4 DO
        b_OutDelayStart[i_OutDelaySlot]   := FALSE;
        b_OutDelayPending[i_OutDelaySlot] := FALSE;
    END_FOR;
    (* [변경] w_UserAlarm 은 정지로 지우지 않음.
       IN 스텝 P3=1 처리에서 i_ControlCmd:=0 이 같은 스캔에 자동정지 DF를 유발하여
       팝업 세팅 즉시 b_Reset 으로 클리어되어 HMI가 감지하지 못하는 문제가 있었음.
       팝업은 b_AlarmReset 경로에서만 지움. *)
    w_PopupResp      := 0;
    b_ParallelStart  := FALSE;
    i_ParallelSlot   := 0;
    i_CallSlot       := 0;
    b_CallParallel   := FALSE;

    (* [변경] 에지 감지 플래그 - 현재 입력 상태 래치 (FALSE 초기화 시 Run/CheckRun 유지 상태에서 즉시 재트리거됨) *)
    b_RunPrev        := b_Run;
    b_CheckRunPrev   := (i_CheckRunState = 1);
    b_RunRising      := FALSE;
    b_CheckRunRising := FALSE;

    FOR i_LoopAxis := 1 TO 5 DO arr_bStart[i_LoopAxis] := FALSE; END_FOR;

    (* [변경] System Output + 내부 비트 클리어. Valve 는 유지 (척·진공 등 안전 물림 상태 보호) *)
    w_system_Output  := 0;
    w_internal_Bit0  := 0;
    w_internal_Bit1  := 0;

    RETURN;
END_IF;


(* ── [NEW] 알람 리셋 (DT212 상승펄스) ──
   운전정지와 분리된 명시적 경로. 작업자가 에러 확인 후 리셋 버튼을 눌렀을 때만 클리어.
*)
IF b_AlarmReset THEN
    b_StepAlarm    := FALSE;
    i_StepAlarmID  := 0;
    w_UserAlarm := 0;   (* 알람과 팝업은 한 세트: 리셋 시 함께 닫힘 *)
    (* state 900 트랩 탈출 - AlarmReset 으로도 에러 상태에서 빠져나올 수 있도록.
       이게 없으면 같은 스캔의 CASE 900 블록이 b_StepAlarm 를 다시 TRUE 로 덮음 *)
    IF i_SeqState = 900 THEN
        i_SeqState := 0;
        ctx_SeqState[i_StackTop] := 0;
    END_IF;
END_IF;


(* ── 2. 타이머 기동후출력 백그라운드 처리 (FOR 루프, TON_FUN+DUT 패턴) ── *)
FOR i_OutDelaySlot := 0 TO 4 DO
    TON_FUN(IN          := b_OutDelayStart[i_OutDelaySlot],
            PT          := t_OutDelaySetting[i_OutDelaySlot],
            dutInstance := at_OD[i_OutDelaySlot],
            Q           => b_OutDelayQ,
            ET          => t_OutDelayET);

    IF b_OutDelayPending[i_OutDelaySlot] AND b_OutDelayQ THEN
        b_OutDelayStart[i_OutDelaySlot]   := FALSE;
        b_OutDelayPending[i_OutDelaySlot] := FALSE;
        w_BitMask := SHL(WORD#1, INT_TO_WORD(i_OutDelayPort[i_OutDelaySlot] MOD 16));

        IF i_OutDelayType[i_OutDelaySlot] = 0 THEN
            IF w_OutDelayOpt[i_OutDelaySlot] = 1 THEN
                w_system_Output := w_system_Output OR w_BitMask;
            ELSE
                w_system_Output := w_system_Output AND (NOT w_BitMask);
            END_IF;
        ELSIF i_OutDelayType[i_OutDelaySlot] = 1 THEN
            IF w_OutDelayOpt[i_OutDelaySlot] = 1 THEN
                w_Valve_Output := w_Valve_Output OR w_BitMask;
            ELSE
                w_Valve_Output := w_Valve_Output AND (NOT w_BitMask);
            END_IF;
        ELSIF i_OutDelayPort[i_OutDelaySlot] < 16 THEN
            IF w_OutDelayOpt[i_OutDelaySlot] = 1 THEN
                w_internal_Bit0 := w_internal_Bit0 OR w_BitMask;
            ELSE
                w_internal_Bit0 := w_internal_Bit0 AND (NOT w_BitMask);
            END_IF;
        ELSE
            IF w_OutDelayOpt[i_OutDelaySlot] = 1 THEN
                w_internal_Bit1 := w_internal_Bit1 OR w_BitMask;
            ELSE
                w_internal_Bit1 := w_internal_Bit1 AND (NOT w_BitMask);
            END_IF;
        END_IF;
    END_IF;
END_FOR;


(* ── [NEW] 컨텍스트 로드: 활성 스택 레벨의 상태를 작업 변수로 ── *)
i_ActiveSlotNo := ctx_SlotNo[i_StackTop];
i_CurrentStep  := ctx_CurrentStep[i_StackTop];
i_SeqState     := ctx_SeqState[i_StackTop];


(* ── 3. 시퀀스 로직 ── *)
CASE i_SeqState OF

    0: (* 대기 (i_StackTop=0 일 때만 의미 있음) *)
        b_StepDone       := FALSE;
        b_TimerStart     := FALSE;
        b_DelayStart     := FALSE;
        b_Step_End       := FALSE;
        IF i_ControlCmd = 1 AND b_Run THEN
            IF i_SlotNo < 0 OR i_SlotNo > 39 THEN
                i_StepAlarmID  := 97;
                i_SeqState := 900;
            ELSE
                i_ActiveSlotNo := i_SlotNo;
                IF i_CurrentStep < 0 OR i_CurrentStep > 99 THEN i_CurrentStep := 0; END_IF;
                i_SeqState := 10;
            END_IF;
        ELSIF i_ControlCmd = 2 AND b_CheckRunRising THEN
            IF i_SlotNo < 0 OR i_SlotNo > 39 THEN
                i_StepAlarmID  := 97;
                i_SeqState := 900;
            ELSE
                i_ActiveSlotNo := i_SlotNo;
                IF i_CurrentStep < 0 OR i_CurrentStep > 99 THEN i_CurrentStep := 0; END_IF;
                i_SeqState := 10;
            END_IF;
        END_IF;

    1: (* 확인운전 - 다음 상승엣지까지 대기 *)
        IF b_CheckRunRising THEN
            i_SeqState := 10;
        END_IF;

    10: (* 스텝 데이터 읽기 + 커맨드 해석 *)
        b_StepDone  := FALSE;
        (* 인덱스 = 슬롯 × 100 + 스텝  (최대 39×100+99 = 3999) *)
        di_StepBase := INT_TO_DINT(i_ActiveSlotNo) * 100 + INT_TO_DINT(i_CurrentStep);
        i_StepCmd  := g_SeqData[di_StepBase].iCommand;
        w_StepOpt  := g_SeqData[di_StepBase].wOption;
        di_StepP1  := g_SeqData[di_StepBase].diParam1;
        di_StepP2  := g_SeqData[di_StepBase].diParam2;
        di_StepP3  := g_SeqData[di_StepBase].diParam3;
        di_StepP4  := g_SeqData[di_StepBase].diParam4;

        CASE i_StepCmd OF
            10: i_SeqState := 11;
            20: i_SeqState := 40;
            21: i_SeqState := 60;
            30: i_SeqState := 50;
            40: i_SeqState := 70;
            50: i_SeqState := 80;
            99: (* END 명령 - [NEW] 스택 팝 또는 최상위 종료 *)
                IF i_StackTop > 0 THEN
                    (* 동기 sub 종료 → caller 복귀 *)
                    ctx_SlotNo[i_StackTop]      := 0;
                    ctx_CurrentStep[i_StackTop] := 0;
                    ctx_SeqState[i_StackTop]    := 0;
                    i_StackTop := i_StackTop - 1;
                    (* 작업 변수에 caller 컨텍스트 즉시 재로드 (이번 스캔 끝의 save가 ctx[caller]를 덮어쓰지 않도록) *)
                    i_ActiveSlotNo := ctx_SlotNo[i_StackTop];
                    i_CurrentStep  := ctx_CurrentStep[i_StackTop];
                    i_SeqState     := 10;   (* caller의 다음 스텝 (CALL 시 미리 +1 해둠) 읽기 *)
                ELSE
                    (* 최상위 종료 — 한 사이클 완료 *)
                    i_CurrentStep := 0;
                    b_Step_End    := TRUE;
                    IF i_ControlCmd = 2 THEN i_CheckRunState := 0; END_IF;
                    i_SeqState := 0;

                    (* [NEW] pack_idx 증가 (사이클 완료 시 1회)
                       - b_NoSubCall=TRUE 인 FB_Monitor 는 증가 금지 (Main 만 증가)
                       - gw_PackEnable=0 이면 패킹 미사용 → 카운터 유지
                       - [C-3] gi_CountX/Y/Z 중 하나라도 <= 0 이면 무의미한 연쇄 증가 방지
                       - stack_order (0~5) 에 따라 6 케이스 오도미터 캐스케이드 *)
                    IF (NOT b_NoSubCall) AND (gw_PackEnable <> 0)
                       AND (gi_CountX > 0) AND (gi_CountY > 0) AND (gi_CountZ > 0) THEN
                        CASE gi_StackOrder OF
                            0:  (* X → Y → Z *)
                                gi_PackIdxX := gi_PackIdxX + 1;
                                IF gi_PackIdxX >= gi_CountX THEN
                                    gi_PackIdxX := 0;
                                    gi_PackIdxY := gi_PackIdxY + 1;
                                    IF gi_PackIdxY >= gi_CountY THEN
                                        gi_PackIdxY := 0;
                                        gi_PackIdxZ := gi_PackIdxZ + 1;
                                        IF gi_PackIdxZ >= gi_CountZ THEN gi_PackIdxZ := 0; END_IF;
                                    END_IF;
                                END_IF;
                            1:  (* X → Z → Y *)
                                gi_PackIdxX := gi_PackIdxX + 1;
                                IF gi_PackIdxX >= gi_CountX THEN
                                    gi_PackIdxX := 0;
                                    gi_PackIdxZ := gi_PackIdxZ + 1;
                                    IF gi_PackIdxZ >= gi_CountZ THEN
                                        gi_PackIdxZ := 0;
                                        gi_PackIdxY := gi_PackIdxY + 1;
                                        IF gi_PackIdxY >= gi_CountY THEN gi_PackIdxY := 0; END_IF;
                                    END_IF;
                                END_IF;
                            2:  (* Y → X → Z *)
                                gi_PackIdxY := gi_PackIdxY + 1;
                                IF gi_PackIdxY >= gi_CountY THEN
                                    gi_PackIdxY := 0;
                                    gi_PackIdxX := gi_PackIdxX + 1;
                                    IF gi_PackIdxX >= gi_CountX THEN
                                        gi_PackIdxX := 0;
                                        gi_PackIdxZ := gi_PackIdxZ + 1;
                                        IF gi_PackIdxZ >= gi_CountZ THEN gi_PackIdxZ := 0; END_IF;
                                    END_IF;
                                END_IF;
                            3:  (* Y → Z → X *)
                                gi_PackIdxY := gi_PackIdxY + 1;
                                IF gi_PackIdxY >= gi_CountY THEN
                                    gi_PackIdxY := 0;
                                    gi_PackIdxZ := gi_PackIdxZ + 1;
                                    IF gi_PackIdxZ >= gi_CountZ THEN
                                        gi_PackIdxZ := 0;
                                        gi_PackIdxX := gi_PackIdxX + 1;
                                        IF gi_PackIdxX >= gi_CountX THEN gi_PackIdxX := 0; END_IF;
                                    END_IF;
                                END_IF;
                            4:  (* Z → X → Y *)
                                gi_PackIdxZ := gi_PackIdxZ + 1;
                                IF gi_PackIdxZ >= gi_CountZ THEN
                                    gi_PackIdxZ := 0;
                                    gi_PackIdxX := gi_PackIdxX + 1;
                                    IF gi_PackIdxX >= gi_CountX THEN
                                        gi_PackIdxX := 0;
                                        gi_PackIdxY := gi_PackIdxY + 1;
                                        IF gi_PackIdxY >= gi_CountY THEN gi_PackIdxY := 0; END_IF;
                                    END_IF;
                                END_IF;
                            5:  (* Z → Y → X *)
                                gi_PackIdxZ := gi_PackIdxZ + 1;
                                IF gi_PackIdxZ >= gi_CountZ THEN
                                    gi_PackIdxZ := 0;
                                    gi_PackIdxY := gi_PackIdxY + 1;
                                    IF gi_PackIdxY >= gi_CountY THEN
                                        gi_PackIdxY := 0;
                                        gi_PackIdxX := gi_PackIdxX + 1;
                                        IF gi_PackIdxX >= gi_CountX THEN gi_PackIdxX := 0; END_IF;
                                    END_IF;
                                END_IF;
                        END_CASE;
                    END_IF;
                END_IF;
            0:  i_SeqState := 0;
            ELSE i_StepAlarmID := 99; i_SeqState := 900;
        END_CASE;


    (* ──── [위치 이동 POS] ──── *)
    11: (* 테이블 번호 쓰기 + RTEX 전파 대기 타이머 기동 *)
        (* [NEW] 축 마스킹: w_StepOpt 중 실 사용 축만 남김 → 미연결 축에 F151_WRT 안 침
                  3축/5축 공용 레시피 지원. w_AxisEnable 에 포함 안 된 축은 자동 스킵됨 *)
        w_EffOpt := w_StepOpt AND w_AxisEnable;

        (* [NEW] 파렛타이징 베이스 플래그 (wOption bit 8) 체크.
           조건 3 가지 모두 충족 시만 스크래치 테이블 사용:
             (a) wOption bit 8 == 1     (이 스텝이 pack_base)
             (b) gw_PackEnable <> 0     (마스터 스위치 ON)
             (c) NOT b_NoSubCall        (FB_Monitor 는 차단 — Main 과 table63 race 방지)
           위 중 하나라도 미충족 → 기존 로직 (point_index + 10026) 로 일반 이동. *)
        IF (w_StepOpt AND 16#0100) <> 0 AND (gw_PackEnable <> 0) AND NOT b_NoSubCall THEN
            i_PackBaseIdx := DINT_TO_INT(di_StepP1);

            (* [C-2] 베이스 포인트 인덱스 범위 검증 (0..59) *)
            IF (i_PackBaseIdx < 0) OR (i_PackBaseIdx > 59) THEN
                i_StepAlarmID := 22;   (* 패킹 베이스 인덱스 범위 오류 *)
                i_SeqState := 900;
                RETURN;
            END_IF;

            i_WriteTableNo := 10026 + 63;

            (* 속도 배율 클램프 (gi_SpeedOverride 1~10) *)
            IF (gi_SpeedOverride < 1) OR (gi_SpeedOverride > 10) THEN
                i_PackOvrd := 10;
            ELSE
                i_PackOvrd := gi_SpeedOverride;
            END_IF;

            (* RTEX 테이블 공통 필드 (fb_WriteMotionTable 와 동일) *)
            PackTableData.ControlCode := 16#0001;
            PackTableData.Pattern     := 16#0000;
            PackTableData.dummy1      := 0;
            PackTableData.dummy2      := 0;
            PackTableData.AuxPoint    := 0;
            PackTableData.DwellTime   := 0;
            PackTableData.AuxOutput   := 0;
            PackTableData.dummy3      := 0;
            PackTableData.dummy4      := 0;

            w_PackTableOff := INT_TO_WORD(63 * 16);   (* 테이블 63 오프셋 *)

            (* 5축 루프: 각 축별 베이스+오프셋 계산 후 테이블 63 에 기록 *)
            FOR i_LoopAxis := 1 TO 5 DO
                w_PackBankSlot := 16#6000 OR SHL(INT_TO_WORD(i_LoopAxis), 8);
                CASE i_LoopAxis OF
                    1: (* X — 오프셋 적용 *)
                        di_PackBase     := g_Dut_Point[i_PackBaseIdx].diPosX;
                        i_PackTargetSpd := g_Dut_Point[i_PackBaseIdx].iSpeedX;
                        i_PackAxisAcc   := gi_1축AccDec;
                        di_PackAxisPPR  := gdi_1축PPR;
                        di_PackOffset   := INT_TO_DINT(gi_PackIdxX) * gdi_PitchX * INT_TO_DINT(gi_DirX);
                        di_PackTarget   := di_PackBase + di_PackOffset;
                    2: (* Y — 오프셋 적용 *)
                        di_PackBase     := g_Dut_Point[i_PackBaseIdx].diPosY;
                        i_PackTargetSpd := g_Dut_Point[i_PackBaseIdx].iSpeedY;
                        i_PackAxisAcc   := gi_2축AccDec;
                        di_PackAxisPPR  := gdi_2축PPR;
                        di_PackOffset   := INT_TO_DINT(gi_PackIdxY) * gdi_PitchY * INT_TO_DINT(gi_DirY);
                        di_PackTarget   := di_PackBase + di_PackOffset;
                    3: (* Z — 오프셋 적용 *)
                        di_PackBase     := g_Dut_Point[i_PackBaseIdx].diPosZ;
                        i_PackTargetSpd := g_Dut_Point[i_PackBaseIdx].iSpeedZ;
                        i_PackAxisAcc   := gi_3축AccDec;
                        di_PackAxisPPR  := gdi_3축PPR;
                        di_PackOffset   := INT_TO_DINT(gi_PackIdxZ) * gdi_PitchZ * INT_TO_DINT(gi_DirZ);
                        di_PackTarget   := di_PackBase + di_PackOffset;
                    4: (* Y2 — 원본 유지 *)
                        di_PackBase     := g_Dut_Point[i_PackBaseIdx].diPosY2;
                        i_PackTargetSpd := g_Dut_Point[i_PackBaseIdx].iSpeedY2;
                        i_PackAxisAcc   := gi_4축AccDec;
                        di_PackAxisPPR  := gdi_4축PPR;
                        di_PackTarget   := di_PackBase;
                    5: (* Z2 — 원본 유지 *)
                        di_PackBase     := g_Dut_Point[i_PackBaseIdx].diPosZ2;
                        i_PackTargetSpd := g_Dut_Point[i_PackBaseIdx].iSpeedZ2;
                        i_PackAxisAcc   := gi_5축AccDec;
                        di_PackAxisPPR  := gdi_5축PPR;
                        di_PackTarget   := di_PackBase;
                END_CASE;
                PackTableData.TargetPosition := di_PackTarget;
                PackTableData.TargetSpeed    := INT_TO_UDINT(i_PackTargetSpd)
                                              * DINT_TO_UDINT(di_PackAxisPPR)
                                              * INT_TO_UDINT(i_PackOvrd) / 20;
                PackTableData.AccTime := i_PackAxisAcc;
                PackTableData.DecTime := i_PackAxisAcc;
                F151_WRT(s1_BankSlot:=w_PackBankSlot,
                         s2_Start:=Adr_Of_Var(PackTableData),
                         n_Number:=16,
                         d_Start:=w_PackTableOff);
            END_FOR;
        ELSE
            i_WriteTableNo := DINT_TO_INT(di_StepP1) + 10026;
        END_IF;

        (* 뱅크슬롯 쓰기: 각 축에 "i_WriteTableNo 실행" 지시 *)
        FOR i_LoopAxis := 1 TO 5 DO
            IF (w_EffOpt AND SHL(WORD#1, INT_TO_WORD(i_LoopAxis - 1))) <> 0 THEN
                F151_WRT(s1_BankSlot:=16#0000, s2_Start:=Adr_Of_Var(i_WriteTableNo), n_Number:=1, d_Start:=INT_TO_WORD(16#0100 + i_LoopAxis - 1));
            END_IF;
        END_FOR;
        t_SettleTime  := T#50MS;
        b_SettleStart := TRUE;
        i_SeqState    := 12;

    12: (* [NEW] RTEX 전파 대기 - F151_WRT 완료 플래그가 없어 고정 딜레이 사용 *)
        IF b_SettleDone THEN
            b_SettleStart := FALSE;
            i_SeqState    := 20;
        END_IF;

    20: (* 기동 신호 ON *)
        FOR i_LoopAxis := 1 TO 5 DO
            IF (w_EffOpt AND SHL(WORD#1, INT_TO_WORD(i_LoopAxis - 1))) <> 0 THEN arr_bStart[i_LoopAxis] := TRUE; END_IF;
        END_FOR;
        b_BusySeen   := FALSE;    (* BUSY 상승 래치 클리어 *)
        b_TimerStart := FALSE;
        i_SeqState   := 21;

    21: (* BUSY 상승 래치. 타임아웃 시 INP 백업 체크로 "이미 제자리" 판별 *)
        (* 대상 축 중 어느 하나라도 BUSY=TRUE를 보이면 래치 *)
        FOR i_LoopAxis := 1 TO 5 DO
            IF (w_EffOpt AND SHL(WORD#1, INT_TO_WORD(i_LoopAxis - 1))) <> 0 THEN
                IF arr_bBusy[i_LoopAxis] THEN b_BusySeen := TRUE; END_IF;
            END_IF;
        END_FOR;

        IF b_BusySeen THEN
            b_TimerStart := FALSE;
            FOR i_LoopAxis := 1 TO 5 DO arr_bStart[i_LoopAxis] := FALSE; END_FOR;
            (* [NEW] diParam2 = 이행 모드: 0=완료 후 이행(완료대기 state 30 경유),
               1=동시 이행(기동 확인만 하고 즉시 다음 스텝, 이동은 백그라운드 계속).
               diParam2 미설정(0) → 기존 동작 유지(하위호환). *)
            IF di_StepP2 = 1 THEN
                i_SeqState := 99;
            ELSE
                i_SeqState := 30;
            END_IF;
        ELSE
            b_TimerStart := TRUE;
            IF b_WaitDone THEN
                (* t_WaitTime 내 BUSY 못 봤음 — 두 가지 가능성:
                   (A) 이미 목표 위치에 있어서 RTEX가 즉시 완료 (BUSY 안 뜸) → INP=TRUE
                   (B) 명령 실패 (서보 알람/거부/배선 등)                   → INP=FALSE
                   따라서 INP 체크로 구분하여 (A)는 정상 진행, (B)는 에러 21 *)
                b_AllDone := TRUE;
                FOR i_LoopAxis := 1 TO 5 DO
                    IF (w_EffOpt AND SHL(WORD#1, INT_TO_WORD(i_LoopAxis - 1))) <> 0 THEN
                        IF NOT arr_bDone[i_LoopAxis] THEN b_AllDone := FALSE; END_IF;
                    END_IF;
                END_FOR;

                b_TimerStart := FALSE;
                FOR i_LoopAxis := 1 TO 5 DO arr_bStart[i_LoopAxis] := FALSE; END_FOR;

                IF b_AllDone THEN
                    (* 모든 활성 축 INP=TRUE → 이미 제자리. 정상 완료로 간주 *)
                    i_SeqState := 99;
                ELSE
                    (* 하나라도 INP=FALSE → 진짜 기동 실패 *)
                    i_StepAlarmID := 21;
                    i_SeqState := 900;
                END_IF;
            END_IF;
        END_IF;

    30: (* 완료 대기 - BUSY 하강 + INP(DONE) 확인 *)
        b_AllDone := TRUE;
        FOR i_LoopAxis := 1 TO 5 DO
            IF (w_EffOpt AND SHL(WORD#1, INT_TO_WORD(i_LoopAxis - 1))) <> 0 THEN
                IF arr_bBusy[i_LoopAxis] OR (NOT arr_bDone[i_LoopAxis]) THEN b_AllDone := FALSE; END_IF;
            END_IF;
        END_FOR;
        IF b_AllDone THEN i_SeqState := 99; END_IF;


    (* ──── [출력 제어 OUT] ──── *)
    (* TODO(Option A 8-3): 워드 OR/AND 분기 단순화 검토 *)
    40:
        i_OutIndex  := DINT_TO_INT(di_StepP1);
        i_OutType   := DINT_TO_INT(di_StepP2);
        w_BitMask   := SHL(WORD#1, INT_TO_WORD(i_OutIndex MOD 16));
        IF di_StepP3 > 0 THEN
            (* 타이머 기동후출력: 빈 슬롯 찾아 타이머 시작 후 즉시 다음 스텝 진행 *)
            i_OutDelaySlot := -1;
            FOR i_OutDelayFind := 0 TO 4 DO
                IF (i_OutDelaySlot < 0) AND (NOT b_OutDelayPending[i_OutDelayFind]) THEN
                    i_OutDelaySlot := i_OutDelayFind;
                END_IF;
            END_FOR;
            IF i_OutDelaySlot >= 0 THEN
                i_OutDelayPort[i_OutDelaySlot]    := i_OutIndex;
                i_OutDelayType[i_OutDelaySlot]    := DINT_TO_INT(di_StepP2);
                w_OutDelayOpt[i_OutDelaySlot]     := w_StepOpt;
                t_OutDelaySetting[i_OutDelaySlot] := DINT_TO_TIME(di_StepP3);
                b_OutDelayStart[i_OutDelaySlot]   := TRUE;
                b_OutDelayPending[i_OutDelaySlot] := TRUE;
            ELSE
                i_StepAlarmID  := 98;
                i_SeqState := 900;
            END_IF;
        ELSE
            (* 즉시 출력 *)
            CASE i_OutType OF
                0: (* 시스템 출력 *)
                    IF w_StepOpt = 1 THEN w_system_Output := w_system_Output OR w_BitMask;
                    ELSE                  w_system_Output := w_system_Output AND (NOT w_BitMask);
                    END_IF;
                1: (* 밸브 출력 *)
                    IF w_StepOpt = 1 THEN w_Valve_Output := w_Valve_Output OR w_BitMask;
                    ELSE                  w_Valve_Output := w_Valve_Output AND (NOT w_BitMask);
                    END_IF;
                2: (* 내부비트 *)
                    IF i_OutIndex < 16 THEN
                        IF w_StepOpt = 1 THEN w_internal_Bit0 := w_internal_Bit0 OR w_BitMask;
                        ELSE                  w_internal_Bit0 := w_internal_Bit0 AND (NOT w_BitMask);
                        END_IF;
                    ELSE
                        IF w_StepOpt = 1 THEN w_internal_Bit1 := w_internal_Bit1 OR w_BitMask;
                        ELSE                  w_internal_Bit1 := w_internal_Bit1 AND (NOT w_BitMask);
                        END_IF;
                    END_IF;
            END_CASE;
        END_IF;
        i_SeqState := 99;


    (* ──── [입력 대기 IN] ──── *)
    60: (* 초기화 *)
        i_WaitPort       := DINT_TO_INT(di_StepP1);
        t_InputTimeout   := DINT_TO_TIME(di_StepP2);
        b_InputWaitStart := TRUE;
        i_SeqState       := 61;

    61: (* 입력 상태 확인 *)
        (* TODO(Option A 8-1): 포트→비트 매핑은 state 51, 70과 중복 - 헬퍼 추출 검토 *)
        IF i_WaitPort >= 0 AND i_WaitPort <= 15 THEN
            w_InputMask  := SHL(WORD#1, INT_TO_WORD(i_WaitPort));
            b_CurrentInput := (w_Input0 AND w_InputMask) <> 0;
        ELSIF i_WaitPort >= 32 AND i_WaitPort <= 47 THEN
            w_InputMask  := SHL(WORD#1, INT_TO_WORD(i_WaitPort - 32));
            b_CurrentInput := (w_Input1 AND w_InputMask) <> 0;
        ELSIF i_WaitPort >= 100 AND i_WaitPort <= 115 THEN
            w_InputMask  := SHL(WORD#1, INT_TO_WORD(i_WaitPort - 100));
            b_CurrentInput := (w_internal_Bit0 AND w_InputMask) <> WORD#0;
        ELSIF i_WaitPort >= 116 AND i_WaitPort <= 131 THEN
            w_InputMask  := SHL(WORD#1, INT_TO_WORD(i_WaitPort - 116));
            b_CurrentInput := (w_internal_Bit1 AND w_InputMask) <> WORD#0;
        ELSE
            b_CurrentInput := FALSE;
        END_IF;

        b_InputCondMet := FALSE;
        IF w_StepOpt = 1 THEN
            IF b_CurrentInput THEN
                b_InputWaitStart := FALSE; i_SeqState := 99; b_InputCondMet := TRUE;
            END_IF;
        ELSE
            IF NOT b_CurrentInput THEN
                b_InputWaitStart := FALSE; i_SeqState := 99; b_InputCondMet := TRUE;
            END_IF;
        END_IF;

        b_TimeoutImmediate := (di_StepP2 = 0);
        IF NOT b_InputCondMet THEN
            IF b_InputWaitDone OR b_TimeoutImmediate THEN
                b_InputWaitStart := FALSE;
                CASE DINT_TO_INT(di_StepP3) OF
                    0: b_InputWaitStart := TRUE;
                    1: w_UserAlarm := INT_TO_WORD(DINT_TO_INT(di_StepP4));
                       i_ControlCmd := 0; i_CheckRunState := 0; i_SeqState := 0;
                    2: w_UserAlarm := INT_TO_WORD(DINT_TO_INT(di_StepP4) + 1000);
                       i_SeqState := 99;
                END_CASE;
            END_IF;
        END_IF;


    (* ──── [CALL] - [REWRITTEN] 동기는 내부 스택 푸시, 병렬은 외부 펄스 ──── *)
    80:
        i_CallSlot     := DINT_TO_INT(di_StepP1);
        b_CallParallel := (w_StepOpt = 1);

        IF b_NoSubCall THEN
            (* Monitor 인스턴스 등 - CALL 불가 *)
            i_StepAlarmID  := 94;
            i_SeqState := 900;
        ELSIF i_CallSlot < 0 OR i_CallSlot > 39 THEN
            i_StepAlarmID  := 96;
            i_SeqState := 900;
        ELSIF b_CallParallel THEN
            (* 병렬 CALL → 외부 워커(FB_Monitor)에게 1스캔 펄스, 캘러는 다음 스텝 *)
            i_ParallelSlot  := i_CallSlot;
            b_ParallelStart := TRUE;
            i_SeqState      := 99;
        ELSE
            (* 동기 CALL → 내부 스택 푸시 *)
            IF i_StackTop >= 3 THEN
                i_StepAlarmID  := 93;       (* 스택 오버플로 *)
                i_SeqState := 900;
            ELSE
                (* 캘러의 복귀 위치(다음 스텝) 보존 후 ctx[현재 top]에 저장 *)
                i_CurrentStep := i_CurrentStep + 1;
                IF i_CurrentStep > 99 THEN i_CurrentStep := 0; END_IF;
                ctx_SlotNo[i_StackTop]      := i_ActiveSlotNo;
                ctx_CurrentStep[i_StackTop] := i_CurrentStep;
                ctx_SeqState[i_StackTop]    := 10;

                (* 새 컨텍스트로 푸시 *)
                i_StackTop := i_StackTop + 1;
                i_ActiveSlotNo := i_CallSlot;
                i_CurrentStep  := 0;
                i_SeqState     := 10;
            END_IF;
        END_IF;

    (* state 81, 82 제거됨 - 서브 완료 대기 불필요 *)


    (* ──── [점프 JMP] ──── *)
    70:
        (* ─ 조건식 평가 ─ *)
        IF w_StepOpt = 0 THEN
            b_JmpCond := TRUE;
        ELSE
            i_JmpPort := DINT_TO_INT(di_StepP3);
            IF DINT_TO_INT(di_StepP2) = 2 THEN
                b_JmpCond := (i_ControlCmd = DINT_TO_INT(di_StepP3));
            ELSIF DINT_TO_INT(di_StepP2) = 1 THEN
                i_JmpBit    := i_JmpPort MOD 16;
                w_InputMask := SHL(WORD#1, INT_TO_WORD(i_JmpBit));
                CASE i_JmpPort / 16 OF
                    0: b_JmpCond := (w_ModeWord0 AND w_InputMask) <> 0;
                    1: b_JmpCond := (w_ModeWord1 AND w_InputMask) <> 0;
                    2: b_JmpCond := (w_ModeWord2 AND w_InputMask) <> 0;
                    ELSE b_JmpCond := FALSE;
                END_CASE;
            ELSE
                (* TODO(Option A 8-1): state 61, 51과 동일 패턴 - 헬퍼 추출 검토 *)
                IF i_JmpPort >= 0 AND i_JmpPort <= 15 THEN
                    w_InputMask := SHL(WORD#1, INT_TO_WORD(i_JmpPort));
                    b_JmpCond := (w_Input0 AND w_InputMask) <> 0;
                ELSIF i_JmpPort >= 32 AND i_JmpPort <= 47 THEN
                    w_InputMask := SHL(WORD#1, INT_TO_WORD(i_JmpPort - 32));
                    b_JmpCond := (w_Input1 AND w_InputMask) <> 0;
                ELSIF i_JmpPort >= 100 AND i_JmpPort <= 115 THEN
                    w_InputMask := SHL(WORD#1, INT_TO_WORD(i_JmpPort - 100));
                    b_JmpCond := (w_internal_Bit0 AND w_InputMask) <> WORD#0;
                ELSIF i_JmpPort >= 116 AND i_JmpPort <= 131 THEN
                    w_InputMask := SHL(WORD#1, INT_TO_WORD(i_JmpPort - 116));
                    b_JmpCond := (w_internal_Bit1 AND w_InputMask) <> WORD#0;
                ELSE
                    b_JmpCond := FALSE;
                END_IF;
            END_IF;
        END_IF;

        (* ─ 실제 점프 여부 결정 ─ *)
        IF w_StepOpt = 0 THEN
            b_JmpDoJump := TRUE;
        ELSIF DINT_TO_INT(di_StepP4) = 1 THEN
            b_JmpDoJump := b_JmpCond;
        ELSE
            b_JmpDoJump := NOT b_JmpCond;
        END_IF;

        IF b_JmpDoJump THEN
            IF DINT_TO_INT(di_StepP1) < 0 OR DINT_TO_INT(di_StepP1) > 99 THEN
                i_StepAlarmID  := 95;
                i_SeqState := 900;
            ELSE
                i_CurrentStep := DINT_TO_INT(di_StepP1);
                i_SeqState    := 10;
            END_IF;
        ELSE
            i_SeqState := 99;
        END_IF;


    (* ──── [타이머 TMR] ──── *)
    50:
        IF DINT_TO_INT(di_StepP3) = 1 THEN
            i_HoldPort       := DINT_TO_INT(di_StepP2);
            t_HoldSetting    := DINT_TO_TIME(di_StepP1);
            b_HoldTimerStart := FALSE;
            i_SeqState       := 51;
        ELSE
            t_DelaySetting := DINT_TO_TIME(di_StepP1);
            b_DelayStart   := TRUE;
            IF b_DelayDone THEN
                b_DelayStart := FALSE; i_SeqState := 99;
            END_IF;
        END_IF;

    51: (* 신호 유지 대기 루프 *)
        (* TODO(Option A 8-1): state 61, 70과 동일 패턴 - 헬퍼 추출 검토 *)
        IF i_HoldPort >= 0 AND i_HoldPort <= 15 THEN
            w_InputMask := SHL(WORD#1, INT_TO_WORD(i_HoldPort));
            b_HoldInput := (w_Input0 AND w_InputMask) <> 0;
        ELSIF i_HoldPort >= 32 AND i_HoldPort <= 47 THEN
            w_InputMask := SHL(WORD#1, INT_TO_WORD(i_HoldPort - 32));
            b_HoldInput := (w_Input1 AND w_InputMask) <> 0;
        ELSIF i_HoldPort >= 100 AND i_HoldPort <= 115 THEN
            w_InputMask := SHL(WORD#1, INT_TO_WORD(i_HoldPort - 100));
            b_HoldInput := (w_internal_Bit0 AND w_InputMask) <> WORD#0;
        ELSIF i_HoldPort >= 116 AND i_HoldPort <= 131 THEN
            w_InputMask := SHL(WORD#1, INT_TO_WORD(i_HoldPort - 116));
            b_HoldInput := (w_internal_Bit1 AND w_InputMask) <> WORD#0;
        ELSE
            b_HoldInput := FALSE;
        END_IF;

        IF w_StepOpt = 1 THEN b_HoldTimerStart := b_HoldInput;
        ELSE                  b_HoldTimerStart := NOT b_HoldInput;
        END_IF;

        IF b_HoldDone THEN
            b_HoldTimerStart := FALSE; i_SeqState := 99;
        END_IF;


    99: (* 스텝 완료 *)
        b_StepDone := TRUE;
        i_CurrentStep := i_CurrentStep + 1;
        IF i_CurrentStep > 99 THEN i_CurrentStep := 0; END_IF;
        IF i_ControlCmd = 2 THEN
            i_CheckRunState := 0;
            i_SeqState      := 1;
        ELSE
            i_SeqState := 10;
        END_IF;

    900: (* 에러 - 이 상태에 머무름. b_AlarmReset 으로 클리어 후 Reset 으로 state 0 복귀 *)
        b_StepAlarm          := TRUE;
        b_TimerStart     := FALSE;
        b_DelayStart     := FALSE;
        b_InputWaitStart := FALSE;
        b_HoldTimerStart := FALSE;
        b_SettleStart    := FALSE;
        FOR i_OutDelaySlot := 0 TO 4 DO
            b_OutDelayStart[i_OutDelaySlot]   := FALSE;
            b_OutDelayPending[i_OutDelaySlot] := FALSE;
        END_FOR;
        FOR i_LoopAxis := 1 TO 5 DO arr_bStart[i_LoopAxis] := FALSE; END_FOR;

END_CASE;


(* ── 4. 출력 갱신 + 컨텍스트 저장 ── *)
(* HMI 모니터링용 출력 *)
i_CurrentSlot := i_ActiveSlotNo;
i_StackDepth  := i_StackTop;
b_IsBusy      := (i_SeqState <> 0) OR (i_StackTop > 0);

(* 활성 컨텍스트 저장 *)
ctx_SlotNo[i_StackTop]      := i_ActiveSlotNo;
ctx_CurrentStep[i_StackTop] := i_CurrentStep;
ctx_SeqState[i_StackTop]    := i_SeqState;


(* ── 5. 타이머 호출 (단일 인스턴스) ── *)
tmr_StartWait (IN := b_TimerStart,     PT := t_WaitTime,      Q => b_WaitDone);
tmr_StepDelay (IN := b_DelayStart,     PT := t_DelaySetting,  Q => b_DelayDone);
tmr_InputWait (IN := b_InputWaitStart, PT := t_InputTimeout,  Q => b_InputWaitDone);
tmr_HoldTimer (IN := b_HoldTimerStart, PT := t_HoldSetting,   Q => b_HoldDone);
tmr_Settle    (IN := b_SettleStart,    PT := t_SettleTime,    Q => b_SettleDone);
