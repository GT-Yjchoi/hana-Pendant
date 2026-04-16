(* ===========================================================================
   [FB 본문]  ── 3개 인스턴스로 운용 ──

   PROGRAM 인스턴스 선언:
       FB_Main   : <이FB타입명>;   (* 슬롯 0 고정, b_Run = 외부 제어 *)
       FB_Sub    : <이FB타입명>;   (* 슬롯 동적, b_Run = FB_Main.b_CallStart *)
       FB_SubSub : <이FB타입명>;   (* 슬롯 동적, b_Run = FB_Sub.b_CallStart  *)

   PROGRAM 배선:
       (* Main ↔ Sub *)
       FB_Sub.i_SlotNo      := FB_Main.i_CallSlotOut;
       FB_Sub.b_Run         := FB_Main.b_CallStart;
       FB_Main.b_SubDone    := FB_Sub.b_Step_End;
       FB_Main.b_SubError   := FB_Sub.b_Error;
       FB_Main.b_SubBusy    := FB_Sub.b_IsBusy;        (* [NEW] 병렬 CALL 충돌 방지 *)
       FB_Main.b_NoSubCall  := FALSE;

       (* Sub ↔ SubSub *)
       FB_SubSub.i_SlotNo   := FB_Sub.i_CallSlotOut;
       FB_SubSub.b_Run      := FB_Sub.b_CallStart;
       FB_Sub.b_SubDone     := FB_SubSub.b_Step_End;
       FB_Sub.b_SubError    := FB_SubSub.b_Error;
       FB_Sub.b_SubBusy     := FB_SubSub.b_IsBusy;     (* [NEW] *)
       FB_Sub.b_NoSubCall   := FALSE;

       (* SubSub는 최하위 - 서브 FB 없음 *)
       FB_SubSub.b_SubBusy   := FALSE;
       FB_SubSub.b_NoSubCall := TRUE;                   (* [NEW] CALL 스텝 만나면 에러 94 *)

   스텝 데이터 메모리 레이아웃 (DT20000~, 슬롯당 1000 Words):
       Word +0  : iCommand  (WORD)
       Word +1  : wOption   (WORD)
       Word +2~3: diParam1  (DINT, Low/High)
       Word +4~5: diParam2  (DINT, Low/High)
       Word +6~7: diParam3  (DINT, Low/High)
       Word +8~9: diParam4  (DINT, Low/High)

   ── VAR_INPUT ──
       i_SlotNo        : INT;    (* 실행할 슬롯 번호 0~39, 시작 시 래치됨 *)
       b_Run           : BOOL;
       b_Reset         : BOOL;

       b_SubDone       : BOOL;   (* 서브 완료 - PROGRAM에서 연결 *)
       b_SubError      : BOOL;   (* 서브 에러  - PROGRAM에서 연결 *)
       b_SubBusy       : BOOL;   (* [NEW] 서브 실행중 - Sub.b_IsBusy에 연결, 없으면 FALSE *)
       b_NoSubCall     : BOOL;   (* [NEW] 이 인스턴스는 CALL 불가(최하위). SubSub 인스턴스에 TRUE 배선 *)
       w_ServoBusy     : WORD;
       w_ServoDone     : WORD;
       w_Input0        : WORD;
       w_Input1        : WORD;
       w_ModeWord0     : WORD;
       w_ModeWord1     : WORD;
       w_ModeWord2     : WORD;
       t_WaitTime      : TIME;

   ── VAR_IN_OUT ──
       i_ControlCmd    : INT;    (* 0=정지, 1=자동, 2=확인운전 - FB 내부에서 0으로 클리어 가능 *)
       i_CheckRunState : INT;    (* 확인운전 상태 - FB 내부에서 클리어 가능 *)
       w_system_Output : WORD;   (* 시스템 출력 - FB가 직접 비트 조작 *)
       w_Valve_Output  : WORD;   (* 밸브 출력  - FB가 직접 비트 조작 *)
       w_internal_Bit0 : WORD;   (* 내부 비트 0~15 *)
       w_internal_Bit1 : WORD;   (* 내부 비트 16~31 *)
       w_R_Input       : WORD;   (* R입력 R0~RF, DT126 워드 비트 - HMI port 200~215 *)

   ── VAR_OUTPUT ──
       b_Error         : BOOL;
       i_ErrorID       : INT;
       b_StepDone      : BOOL;   (* 스텝 완료 펄스(다음 스텝 읽기 진입 시 자동 클리어) *)
       b_Step_End      : BOOL;   (* 시퀀스 END 도달 - PROGRAM에서 b_SubDone에 연결 *)
       b_IsBusy        : BOOL;   (* [NEW] 실행중(i_SeqState<>0). 상위 FB의 b_SubBusy에 연결 *)
       w_SeqPopup      : WORD;
       i_CurrentStep   : INT;
       i_CallSlotOut   : INT;    (* 호출할 슬롯 번호 *)
       b_CallStart     : BOOL;   (* 서브 기동 트리거 - PROGRAM에서 b_Run에 연결 *)
       b_CallParallelOut : BOOL; (* 병렬 호출 여부 *)

   ── 에러 ID ──
       21 : POS 축 이동 확인 실패
       50 : 서브 시퀀스 에러
       93 : 병렬 CALL 실패 - 서브 FB가 이미 실행중
       94 : CALL 사용 불가 - 이 인스턴스는 최하위(b_NoSubCall=TRUE)
       95 : JMP 타겟 스텝 번호 범위 초과(0~99)
       96 : CALL 슬롯 번호 범위 초과(0~39)
       97 : 실행 슬롯 번호 범위 초과(0~39)
       98 : OUT 지연 타이머 슬롯 없음(2개 모두 사용중)
       99 : 알 수 없는 커맨드

   ── VAR (내부) ──
       (* 슬롯/스텝 *)
       (* 전역변수 필요: g_SeqData AT DT20000 : ARRAY[0..3999] OF DUT_STEP_DATA *)
       i_ActiveSlotNo  : INT;
       di_StepBase     : DINT;
       i_StepCmd       : INT;
       w_StepOpt       : WORD;
       di_StepP1       : DINT;
       di_StepP2       : DINT;
       di_StepP3       : DINT;
       di_StepP4       : DINT;
       (* 상태머신 *)
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
       (* 타이머 *)
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
       (* 타이머 기동후출력 - 2슬롯 개별 선언 *)
       tmr_OD0 : TON; tmr_OD1 : TON;
       b_OutDelayStart   : ARRAY[0..1] OF BOOL;
       b_OutDelayPending : ARRAY[0..1] OF BOOL;
       t_OutDelaySetting : ARRAY[0..1] OF TIME;
       i_OutDelayPort    : ARRAY[0..1] OF INT;
       i_OutDelayType    : ARRAY[0..1] OF INT;
       w_OutDelayOpt     : ARRAY[0..1] OF WORD;
       i_OutDelaySlot    : INT;
       (* JMP *)
       i_JmpPort       : INT;
       i_JmpBit        : INT;
       b_JmpCond       : BOOL;
       b_JmpDoJump     : BOOL;   (* [NEW] 실제 점프 여부(조건/옵션 반영 후) *)
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


(* ── 0. 상승 에지 검출 ── *)
b_RunRising      := b_Run AND NOT b_RunPrev;
b_RunPrev        := b_Run;

b_CheckRunRising := (i_CheckRunState = 1) AND NOT b_CheckRunPrev;
b_CheckRunPrev   := (i_CheckRunState = 1);


(* ── 1. 서보 상태 입력 매핑 ── *)
FOR i_LoopAxis := 1 TO 5 DO
    arr_bBusy[i_LoopAxis] := (w_ServoBusy AND SHL(WORD#1, INT_TO_WORD(7 + i_LoopAxis))) <> 0;
    arr_bDone[i_LoopAxis] := (w_ServoDone AND SHL(WORD#1, INT_TO_WORD(i_LoopAxis - 1))) <> 0;
END_FOR;


(* ── 리셋 ── *)
IF b_Reset THEN
    i_SeqState       := 0;
    i_CurrentStep    := 0;
    i_ActiveSlotNo   := 0;
    b_Error          := FALSE;
    i_ErrorID        := 0;
    b_StepDone       := FALSE;
    b_Step_End       := FALSE;
    b_IsBusy         := FALSE;
    b_TimerStart     := FALSE;
    b_DelayStart     := FALSE;
    b_InputWaitStart := FALSE;
    b_HoldTimerStart := FALSE;
    b_OutDelayStart[0]:=FALSE; b_OutDelayPending[0]:=FALSE;
    b_OutDelayStart[1]:=FALSE; b_OutDelayPending[1]:=FALSE;
    w_SeqPopup       := 0;
    w_PopupResp      := 0;
    b_CallStart       := FALSE;
    i_CallSlotOut     := 0;
    i_CallSlot        := 0;
    b_CallParallelOut := FALSE;
    (* 에지 감지 플래그 초기화 - 리셋 직후 스퓨리어스 상승엣지 방지 *)
    b_RunPrev        := FALSE;
    b_CheckRunPrev   := FALSE;
    b_RunRising      := FALSE;
    b_CheckRunRising := FALSE;
    FOR i_LoopAxis := 1 TO 5 DO arr_bStart[i_LoopAxis] := FALSE; END_FOR;
    w_system_Output  := 0;
    w_Valve_Output   := 0;
    w_internal_Bit0  := 0;
    w_internal_Bit1  := 0;
    RETURN;
END_IF;


(* ── 2. 타이머 기동후출력 백그라운드 처리 (2슬롯 인라인) ── *)
tmr_OD0(IN:=b_OutDelayStart[0],PT:=t_OutDelaySetting[0]);
IF b_OutDelayPending[0] AND tmr_OD0.Q THEN b_OutDelayStart[0]:=FALSE; b_OutDelayPending[0]:=FALSE;
    w_BitMask:=SHL(WORD#1,INT_TO_WORD(i_OutDelayPort[0] MOD 16));
    IF i_OutDelayType[0]=0 THEN IF w_OutDelayOpt[0]=1 THEN w_system_Output:=w_system_Output OR w_BitMask; ELSE w_system_Output:=w_system_Output AND(NOT w_BitMask); END_IF;
    ELSIF i_OutDelayType[0]=1 THEN IF w_OutDelayOpt[0]=1 THEN w_Valve_Output:=w_Valve_Output OR w_BitMask; ELSE w_Valve_Output:=w_Valve_Output AND(NOT w_BitMask); END_IF;
    ELSIF i_OutDelayPort[0]<16 THEN IF w_OutDelayOpt[0]=1 THEN w_internal_Bit0:=w_internal_Bit0 OR w_BitMask; ELSE w_internal_Bit0:=w_internal_Bit0 AND(NOT w_BitMask); END_IF;
    ELSE IF w_OutDelayOpt[0]=1 THEN w_internal_Bit1:=w_internal_Bit1 OR w_BitMask; ELSE w_internal_Bit1:=w_internal_Bit1 AND(NOT w_BitMask); END_IF; END_IF; END_IF;

tmr_OD1(IN:=b_OutDelayStart[1],PT:=t_OutDelaySetting[1]);
IF b_OutDelayPending[1] AND tmr_OD1.Q THEN b_OutDelayStart[1]:=FALSE; b_OutDelayPending[1]:=FALSE;
    w_BitMask:=SHL(WORD#1,INT_TO_WORD(i_OutDelayPort[1] MOD 16));
    IF i_OutDelayType[1]=0 THEN IF w_OutDelayOpt[1]=1 THEN w_system_Output:=w_system_Output OR w_BitMask; ELSE w_system_Output:=w_system_Output AND(NOT w_BitMask); END_IF;
    ELSIF i_OutDelayType[1]=1 THEN IF w_OutDelayOpt[1]=1 THEN w_Valve_Output:=w_Valve_Output OR w_BitMask; ELSE w_Valve_Output:=w_Valve_Output AND(NOT w_BitMask); END_IF;
    ELSIF i_OutDelayPort[1]<16 THEN IF w_OutDelayOpt[1]=1 THEN w_internal_Bit0:=w_internal_Bit0 OR w_BitMask; ELSE w_internal_Bit0:=w_internal_Bit0 AND(NOT w_BitMask); END_IF;
    ELSE IF w_OutDelayOpt[1]=1 THEN w_internal_Bit1:=w_internal_Bit1 OR w_BitMask; ELSE w_internal_Bit1:=w_internal_Bit1 AND(NOT w_BitMask); END_IF; END_IF; END_IF;



(* ── 3. 시퀀스 로직 ── *)
CASE i_SeqState OF

    0: (* 대기 *)
        b_StepDone       := FALSE;
        b_TimerStart     := FALSE;
        b_DelayStart     := FALSE;
        b_Step_End       := FALSE;
        IF i_ControlCmd = 1 AND b_Run THEN
            IF i_SlotNo < 0 OR i_SlotNo > 39 THEN
                i_ErrorID  := 97;
                i_SeqState := 900;
            ELSE
                i_ActiveSlotNo := i_SlotNo;   (* 슬롯 번호 래치 *)
                IF i_CurrentStep < 0 OR i_CurrentStep > 99 THEN i_CurrentStep := 0; END_IF;
                i_SeqState := 10;
            END_IF;
        ELSIF i_ControlCmd = 2 AND b_CheckRunRising THEN
            IF i_SlotNo < 0 OR i_SlotNo > 39 THEN
                i_ErrorID  := 97;
                i_SeqState := 900;
            ELSE
                i_ActiveSlotNo := i_SlotNo;
                IF i_CurrentStep < 0 OR i_CurrentStep > 99 THEN i_CurrentStep := 0; END_IF;
                i_SeqState := 10;
            END_IF;
        END_IF;

    1: (* 확인운전 - 스텝 완료 후 다음 상승엣지까지 대기 *)
        (* 레벨이 아닌 엣지로 대기하여 버튼을 계속 눌러도 1스텝씩만 진행 *)
        IF b_CheckRunRising THEN
            i_SeqState := 10;
        END_IF;

    10: (* 스텝 데이터 읽기 + 커맨드 해석 *)
        b_StepDone  := FALSE;  (* 새 스텝 진입 시 이전 완료 펄스 클리어 *)
        (* 전역변수: g_SeqData AT DT20000 : ARRAY[0..3999] OF DUT_STEP_DATA *)
        (* 인덱스 = 슬롯 × 100 + 스텝  (최대 39×100+99 = 3999)             *)
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
            99: i_CurrentStep := 0; b_Step_End := TRUE;
                IF i_ControlCmd = 2 THEN
                    i_CheckRunState := 0;
                END_IF;
                i_SeqState := 0;
            0:  i_SeqState := 0;
            ELSE i_ErrorID := 99; i_SeqState := 900;
        END_CASE;


    (* ──── [위치 이동 POS] ──── *)
    11: (* 테이블 번호 쓰기 *)
        i_WriteTableNo := DINT_TO_INT(di_StepP1) + 10026;
        FOR i_LoopAxis := 1 TO 5 DO
            IF (w_StepOpt AND SHL(WORD#1, INT_TO_WORD(i_LoopAxis - 1))) <> 0 THEN
                F151_WRT(s1_BankSlot:=16#0000, s2_Start:=Adr_Of_Var(i_WriteTableNo), n_Number:=1, d_Start:=INT_TO_WORD(16#0100 + i_LoopAxis - 1));
            END_IF;
        END_FOR;
        i_SeqState := 20;

    20: (* 기동 신호 ON *)
        FOR i_LoopAxis := 1 TO 5 DO
            IF (w_StepOpt AND SHL(WORD#1, INT_TO_WORD(i_LoopAxis - 1))) <> 0 THEN arr_bStart[i_LoopAxis] := TRUE; END_IF;
        END_FOR;
        b_TimerStart := FALSE;
        i_SeqState := 21;

    21: (* 기동 확인 *)
        b_AnyBusy := FALSE;
        FOR i_LoopAxis := 1 TO 5 DO
            IF arr_bStart[i_LoopAxis] AND arr_bBusy[i_LoopAxis] THEN arr_bStart[i_LoopAxis]:=FALSE; b_AnyBusy:=TRUE; END_IF;
        END_FOR;

        IF b_AnyBusy THEN
            b_TimerStart := FALSE;
            FOR i_LoopAxis := 1 TO 5 DO arr_bStart[i_LoopAxis] := FALSE; END_FOR;
            i_SeqState := 30;
        ELSE
            b_TimerStart := TRUE;
            IF b_WaitDone THEN
                b_AllDone := TRUE;
                FOR i_LoopAxis := 1 TO 5 DO
                    IF (w_StepOpt AND SHL(WORD#1, INT_TO_WORD(i_LoopAxis - 1))) <> 0 THEN
                        IF NOT arr_bDone[i_LoopAxis] THEN b_AllDone := FALSE; END_IF;
                    END_IF;
                END_FOR;
                b_TimerStart := FALSE;
                FOR i_LoopAxis := 1 TO 5 DO arr_bStart[i_LoopAxis] := FALSE; END_FOR;
                IF b_AllDone THEN i_SeqState := 99; ELSE i_ErrorID := 21; i_SeqState := 900; END_IF;
            END_IF;
        END_IF;

    30: (* 완료 대기 *)
        b_AllDone := TRUE;
        FOR i_LoopAxis := 1 TO 5 DO
            IF (w_StepOpt AND SHL(WORD#1, INT_TO_WORD(i_LoopAxis - 1))) <> 0 THEN
                IF arr_bBusy[i_LoopAxis] THEN b_AllDone := FALSE; END_IF;
            END_IF;
        END_FOR;
        IF b_AllDone THEN i_SeqState := 99; END_IF;


    (* ──── [출력 제어 OUT] ──── *)
    40:
        i_OutIndex  := DINT_TO_INT(di_StepP1);
        i_OutType   := DINT_TO_INT(di_StepP2);
        w_BitMask   := SHL(WORD#1, INT_TO_WORD(i_OutIndex MOD 16));
        IF di_StepP3 > 0 THEN
            (* 타이머 기동후출력: 빈 슬롯 찾아서 타이머 시작 후 즉시 다음 스텝 진행 *)
            i_OutDelaySlot := -1;
            IF NOT b_OutDelayPending[0] THEN i_OutDelaySlot := 0;
            ELSIF NOT b_OutDelayPending[1] THEN i_OutDelaySlot := 1;
            END_IF;
            IF i_OutDelaySlot >= 0 THEN
                i_OutDelayPort[i_OutDelaySlot]    := i_OutIndex;
                i_OutDelayType[i_OutDelaySlot]    := DINT_TO_INT(di_StepP2);
                w_OutDelayOpt[i_OutDelaySlot]     := w_StepOpt;
                t_OutDelaySetting[i_OutDelaySlot] := DINT_TO_TIME(di_StepP3);
                b_OutDelayStart[i_OutDelaySlot]   := TRUE;
                b_OutDelayPending[i_OutDelaySlot] := TRUE;
            ELSE
                (* 슬롯 없음: 에러 처리 *)
                i_ErrorID  := 98;
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
        ELSIF i_WaitPort >= 200 AND i_WaitPort <= 215 THEN
            w_InputMask  := SHL(WORD#1, INT_TO_WORD(i_WaitPort - 200));
            b_CurrentInput := (w_R_Input AND w_InputMask) <> WORD#0;
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
                    1: w_SeqPopup := INT_TO_WORD(DINT_TO_INT(di_StepP4));
                       i_ControlCmd := 0; i_CheckRunState := 0; i_SeqState := 0;
                    2: w_SeqPopup := INT_TO_WORD(DINT_TO_INT(di_StepP4) + 1000);
                       i_SeqState := 99;
                END_CASE;
            END_IF;
        END_IF;


    (* ──── [CALL - 서브 시퀀스 호출] ──── *)
    80: (* CALL 기동 *)
        i_CallSlot := DINT_TO_INT(di_StepP1);
        IF b_NoSubCall THEN
            (* 최하위 인스턴스(SubSub 등) - 서브 FB 없음 *)
            i_ErrorID  := 94;
            i_SeqState := 900;
        ELSIF b_SubBusy THEN
            (* 서브가 아직 이전 CALL 실행중 - 병렬/동기 모두 거절 *)
            i_ErrorID  := 93;
            i_SeqState := 900;
        ELSIF i_CallSlot < 0 OR i_CallSlot > 39 THEN
            i_ErrorID  := 96;
            i_SeqState := 900;
        ELSE
            b_CallParallel    := (w_StepOpt = 1);
            i_CallSlotOut     := i_CallSlot;
            b_CallParallelOut := b_CallParallel;
            b_CallStart       := TRUE;
            i_SeqState        := 82;
        END_IF;

    82: (* b_CallStart 하강 후 분기 *)
        b_CallStart := FALSE;
        IF b_CallParallel THEN
            i_SeqState := 99;   (* 병렬: 즉시 다음 스텝 *)
        ELSE
            i_SeqState := 81;   (* 동기: 완료 대기 *)
        END_IF;

    81: (* 서브 완료 대기 *)
        IF b_SubDone THEN
            i_SeqState := 99;
        ELSIF b_SubError THEN
            i_ErrorID := 50; i_SeqState := 900;
        END_IF;


    (* ──── [점프 JMP] ──── *)
    70:
        (* ─ 조건식 평가 ─ *)
        IF w_StepOpt = 0 THEN
            b_JmpCond := TRUE;   (* 무조건 점프 *)
        ELSE
            i_JmpPort := DINT_TO_INT(di_StepP3);
            IF DINT_TO_INT(di_StepP2) = 2 THEN
                (* 운전상태 비교: 0=정지, 1=자동, 2=확인운전 *)
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
                ELSIF i_JmpPort >= 200 AND i_JmpPort <= 215 THEN
                    w_InputMask := SHL(WORD#1, INT_TO_WORD(i_JmpPort - 200));
                    b_JmpCond := (w_R_Input AND w_InputMask) <> WORD#0;
                ELSE
                    b_JmpCond := FALSE;
                END_IF;
            END_IF;
        END_IF;

        (* ─ 실제 점프 여부 결정 (P4=1: 조건참 점프, 그외: 조건거짓 점프) ─ *)
        IF w_StepOpt = 0 THEN
            b_JmpDoJump := TRUE;
        ELSIF DINT_TO_INT(di_StepP4) = 1 THEN
            b_JmpDoJump := b_JmpCond;
        ELSE
            b_JmpDoJump := NOT b_JmpCond;
        END_IF;

        (* ─ 타겟 스텝 범위 검사 후 분기 ─ *)
        IF b_JmpDoJump THEN
            IF DINT_TO_INT(di_StepP1) < 0 OR DINT_TO_INT(di_StepP1) > 99 THEN
                i_ErrorID  := 95;
                i_SeqState := 900;
            ELSE
                i_CurrentStep := DINT_TO_INT(di_StepP1);
                i_SeqState    := 10;
            END_IF;
        ELSE
            i_SeqState := 99;
        END_IF;


    (* ──── [타이머 TMR] ──── *)
    (* di_StepP3 = 0: 단순 대기 / di_StepP3 = 1: 신호 유지 모드 *)
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
        ELSIF i_HoldPort >= 200 AND i_HoldPort <= 215 THEN
            w_InputMask := SHL(WORD#1, INT_TO_WORD(i_HoldPort - 200));
            b_HoldInput := (w_R_Input AND w_InputMask) <> WORD#0;
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
            (* 확인운전: CheckRunState를 0으로 내려 다음 상승엣지까지 정지 *)
            i_CheckRunState := 0;
            i_SeqState      := 1;
        ELSE
            i_SeqState := 10;   (* 자동운전: 즉시 다음 스텝 *)
        END_IF;

    900: (* 에러 *)
        b_Error          := TRUE;
        b_TimerStart     := FALSE;
        b_DelayStart     := FALSE;
        b_InputWaitStart := FALSE;
        b_HoldTimerStart := FALSE;
        (* 지연 출력 - 미발사분 취소 (타이머/펜딩 동시 클리어) *)
        b_OutDelayStart[0]   := FALSE; b_OutDelayPending[0] := FALSE;
        b_OutDelayStart[1]   := FALSE; b_OutDelayPending[1] := FALSE;
        (* 서보 기동 플래그 취소 *)
        FOR i_LoopAxis := 1 TO 5 DO arr_bStart[i_LoopAxis] := FALSE; END_FOR;

END_CASE;


(* ── 3. Busy 상태 출력 갱신 ── *)
(* 상위 FB의 b_SubBusy 배선용. 대기(0)는 FALSE, 그 외 모든 실행/에러 상태는 TRUE *)
b_IsBusy := (i_SeqState <> 0);


(* ── 4. 타이머 호출 (매 스캔) ── *)
tmr_StartWait (IN := b_TimerStart,     PT := t_WaitTime,      Q => b_WaitDone);
tmr_StepDelay (IN := b_DelayStart,     PT := t_DelaySetting,  Q => b_DelayDone);
tmr_InputWait (IN := b_InputWaitStart, PT := t_InputTimeout,  Q => b_InputWaitDone);
tmr_HoldTimer (IN := b_HoldTimerStart, PT := t_HoldSetting,   Q => b_HoldDone);
