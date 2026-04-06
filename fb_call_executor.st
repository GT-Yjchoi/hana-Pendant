(* ====================================================================
   [FB] CallExecutor  ─  시퀀스 CALL 라우팅 전담
   ====================================================================

   역할
   ─────
   · 여러 시퀀스 FB 인스턴스 간 CALL 관계를 추적·라우팅
   · 호출된 슬롯이 완료(b_Step_End)되면 호출자에게 SubDone 통보
   · N단계 중첩 CALL 지원  (슬롯 수 내에서 재귀/순환은 에러)
   · 병렬 CALL: 기동 펄스만 발생, 완료 통보 없음
   · 슬롯 0(Main)은 외부 제어로 기동 → arr_SubRun[0] 미사용
   · 슬롯 0은 CALL 대상으로 지정 불가 (에러 처리)

   ── VAR_INPUT ──
       arr_CallStart    : ARRAY[0..39] OF BOOL;
           (* 슬롯i의 b_CallStart 연결 *)
       arr_CallSlot     : ARRAY[0..39] OF INT;
           (* 슬롯i의 i_CallSlotOut 연결 *)
       arr_CallParallel : ARRAY[0..39] OF BOOL;
           (* 슬롯i의 b_CallParallelOut 연결 *)
       arr_StepEnd      : ARRAY[0..39] OF BOOL;
           (* 슬롯i의 b_Step_End 연결 *)
       arr_FBError      : ARRAY[0..39] OF BOOL;
           (* 슬롯i의 b_Error 연결 *)
       b_Reset          : BOOL;

   ── VAR_OUTPUT ──
       arr_SubRun       : ARRAY[0..39] OF BOOL;
           (* 슬롯i의 b_Run 연결 - 1스캔 기동 펄스 *)
       arr_SubDone      : ARRAY[0..39] OF BOOL;
           (* 슬롯i의 b_SubDone 연결 - 완료 래치 *)
       arr_SubError     : ARRAY[0..39] OF BOOL;
           (* 슬롯i의 b_SubError 연결 *)

   ── VAR ──
       arr_CallerOf     : ARRAY[0..39] OF INT;
           (* 슬롯i를 호출한 슬롯 번호. -1=없음(직접기동 또는 병렬) *)
       arr_IsParallel   : ARRAY[0..39] OF BOOL;
           (* 슬롯i가 병렬로 호출됐는지 *)
       arr_IsRunning    : ARRAY[0..39] OF BOOL;
           (* 슬롯i 현재 실행 중 여부 *)
       arr_CallPrev     : ARRAY[0..39] OF BOOL;
           (* CallStart 이전값 - 상승 에지 검출용 *)
       arr_EndPrev      : ARRAY[0..39] OF BOOL;
           (* StepEnd 이전값 *)
       arr_ErrPrev      : ARRAY[0..39] OF BOOL;
           (* FBError 이전값 *)
       i_Loop           : INT;
       i_Target         : INT;
       i_Caller         : INT;

   ── PROGRAM 배선 예시 ──
       (* 인스턴스 선언: Exec : CallExecutor; *)

       (* 슬롯 0 (Main) *)
       Exec.arr_CallStart[0]    := FB_Main.b_CallStart;
       Exec.arr_CallSlot[0]     := FB_Main.i_CallSlotOut;
       Exec.arr_CallParallel[0] := FB_Main.b_CallParallelOut;
       Exec.arr_StepEnd[0]      := FB_Main.b_Step_End;
       Exec.arr_FBError[0]      := FB_Main.b_Error;
       FB_Main.b_SubDone        := Exec.arr_SubDone[0];
       FB_Main.b_SubError       := Exec.arr_SubError[0];
       (* FB_Main.b_Run은 외부 제어 명령으로 직접 연결, arr_SubRun[0] 미사용 *)

       (* 슬롯 1 (Sub1) *)
       Exec.arr_CallStart[1]    := FB_Sub1.b_CallStart;
       Exec.arr_CallSlot[1]     := FB_Sub1.i_CallSlotOut;
       Exec.arr_CallParallel[1] := FB_Sub1.b_CallParallelOut;
       Exec.arr_StepEnd[1]      := FB_Sub1.b_Step_End;
       Exec.arr_FBError[1]      := FB_Sub1.b_Error;
       FB_Sub1.b_Run            := Exec.arr_SubRun[1];
       FB_Sub1.b_SubDone        := Exec.arr_SubDone[1];
       FB_Sub1.b_SubError       := Exec.arr_SubError[1];

       (* 슬롯 2~N: 동일 패턴 반복 *)

       (* 실행 순서: FB_Main → FB_Sub1 → ... → Exec 순으로 PROGRAM에서 호출 *)
       (*   이렇게 하면 동일 스캔에서 StepEnd → SubDone 전달이 보장됨          *)

   ==================================================================== *)


(* ──── 0. 리셋 ──── *)
IF b_Reset THEN
    FOR i_Loop := 0 TO 39 DO
        arr_CallerOf[i_Loop]   := -1;
        arr_IsParallel[i_Loop] := FALSE;
        arr_IsRunning[i_Loop]  := FALSE;
        arr_SubRun[i_Loop]     := FALSE;
        arr_SubDone[i_Loop]    := FALSE;
        arr_SubError[i_Loop]   := FALSE;
        arr_CallPrev[i_Loop]   := FALSE;
        arr_EndPrev[i_Loop]    := FALSE;
        arr_ErrPrev[i_Loop]    := FALSE;
    END_FOR;
    RETURN;
END_IF;


(* ──── 1. SubRun 펄스 클리어 ────
   이전 스캔에서 발생시킨 기동 펄스를 내림.
   Sub FB는 이미 b_Run 상승 에지를 감지했으므로 이번 스캔에 내려도 무방.  *)
FOR i_Loop := 0 TO 39 DO
    arr_SubRun[i_Loop] := FALSE;
END_FOR;


(* ──── 2. CALL 요청 처리 ──── *)
FOR i_Loop := 0 TO 39 DO

    IF arr_CallStart[i_Loop] AND NOT arr_CallPrev[i_Loop] THEN
        (* CallStart 상승 에지 감지 *)

        (* 새 CALL 시작 시 이전 완료·에러 신호 클리어 *)
        arr_SubDone[i_Loop]  := FALSE;
        arr_SubError[i_Loop] := FALSE;

        i_Target := arr_CallSlot[i_Loop];

        IF i_Target <= 0 OR i_Target > 39 THEN
            (* 슬롯 0(Main) 및 범위 밖 지정 불가 *)
            arr_SubError[i_Loop] := TRUE;

        ELSIF i_Target = i_Loop THEN
            (* 자기 자신 호출 불가 *)
            arr_SubError[i_Loop] := TRUE;

        ELSIF arr_IsRunning[i_Target] THEN
            (* 대상 슬롯이 이미 실행 중 - 순환 호출 또는 중복 병렬 호출 *)
            arr_SubError[i_Loop] := TRUE;

        ELSE
            (* 정상 호출 등록 *)
            arr_CallerOf[i_Target]   := i_Loop;
            arr_IsParallel[i_Target] := arr_CallParallel[i_Loop];
            arr_IsRunning[i_Target]  := TRUE;
            arr_SubRun[i_Target]     := TRUE;   (* 1스캔 기동 펄스 발생 *)
        END_IF;

    END_IF;

    arr_CallPrev[i_Loop] := arr_CallStart[i_Loop];

END_FOR;


(* ──── 3. 종료 감지 → 호출자 통보 ──── *)
FOR i_Loop := 0 TO 39 DO

    IF arr_StepEnd[i_Loop] AND NOT arr_EndPrev[i_Loop] THEN
        (* StepEnd 상승 에지: 해당 슬롯의 시퀀스가 END(99)에 도달 *)

        IF arr_IsRunning[i_Loop] THEN
            arr_IsRunning[i_Loop]  := FALSE;
            i_Caller               := arr_CallerOf[i_Loop];
            arr_CallerOf[i_Loop]   := -1;
            arr_IsParallel[i_Loop] := FALSE;

            IF i_Caller >= 0 AND NOT arr_IsParallel[i_Loop] THEN
                (* 동기 호출: 호출자의 SubDone 래치 SET
                   → 호출자 FB(state 81)가 다음 스캔에서 감지하고 전진 *)
                arr_SubDone[i_Caller] := TRUE;
            END_IF;
            (* 병렬 호출: 완료 통보 없음, 호출자는 이미 다음 스텝 진행 중 *)
        END_IF;

    END_IF;

    arr_EndPrev[i_Loop] := arr_StepEnd[i_Loop];

END_FOR;


(* ──── 4. 에러 감지 → 호출자로 에러 전파 ──── *)
FOR i_Loop := 0 TO 39 DO

    IF arr_FBError[i_Loop] AND NOT arr_ErrPrev[i_Loop] THEN
        (* FBError 상승 에지: 해당 슬롯에서 에러 발생 *)

        IF arr_IsRunning[i_Loop] THEN
            arr_IsRunning[i_Loop]  := FALSE;
            i_Caller               := arr_CallerOf[i_Loop];
            arr_CallerOf[i_Loop]   := -1;
            arr_IsParallel[i_Loop] := FALSE;

            IF i_Caller >= 0 THEN
                (* 호출자에게 에러 전파 → 호출자도 state 900으로 이행 *)
                arr_SubError[i_Caller] := TRUE;
            END_IF;
        END_IF;

    END_IF;

    arr_ErrPrev[i_Loop] := arr_FBError[i_Loop];

END_FOR;
