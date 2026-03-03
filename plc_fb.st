
(* ===========================================================================
    변수 등록리스트


 	VAR_IN_OUT
		b_Run: BOOL;
	END_VAR
	VAR_INPUT
		b_Reset: BOOL:=FALSE;
		gw_ModeWord0: WORD;		(* DT206: 모드 설정 워드 0 (모드 0~15) *)
		gw_ModeWord1: WORD;		(* DT207: 모드 설정 워드 1 (모드 16~31) *)
		gw_ModeWord2: WORD;		(* DT208: 모드 설정 워드 2 (모드 32~39) *)
	END_VAR
	VAR_IN_OUT
		arr_StepData: ARRAY [0..49] OF DUT_STEP_DATA;
		gw_SeqPopup: WORD;		(* DT159: HMI 팝업 요청 (1=팝업 표시) *)
		gw_PopupResp: WORD;		(* DT160: HMI 응답 (1=계속, 2=정지) *)
		gw_InternalBit0: WORD;	(* WR0: M00~M15 내부비트 *)
		gw_InternalBit1: WORD;	(* WR1: M16~M31 내부비트 *)
	END_VAR
	VAR_OUTPUT
		arr_bStart: ARRAY [1..8] OF BOOL:=[8(FALSE)];
		arr_bSeqOut: ARRAY [1..8] OF BOOL:=[8(FALSE)];
		valveOutput: ARRAY [0..31] OF BOOL:=[32(FALSE)];
		i_CurrentStep: INT:=0;
		b_StepDone: BOOL:=FALSE;
		b_Error: BOOL:=FALSE;
		i_ErrorID: INT:=0;
		b_Step_End: BOOL:=FALSE;
	END_VAR
	VAR
		arr_bBusy: ARRAY [1..8] OF BOOL:=[8(FALSE)];
		arr_bDone: ARRAY [1..8] OF BOOL:=[8(FALSE)];
		i_BusyStartAddr: INT:=0;
		i_DoneStartAddr: INT:=0;
		i_SeqState: INT:=0;
		i_LoopAxis: INT:=0;
		w_AxisMask: WORD:=0;
		b_AllDone: BOOL:=FALSE;
		b_AnyBusy: BOOL:=FALSE;
		i_WriteTableNo: INT:=10;
		w_WriteAddr: WORD:=99;
		tmr_StartWait: TON;
		t_WaitTime: TIME:=T#0.5s;
		w_ShiftNum: WORD:=0;
		b_TimerStart: BOOL:=FALSE;
		i_ResetLoop: INT:=0;
		i_OutIndex: INT:=0;
		b_DelayStart: BOOL:=FALSE;
		t_DelaySetting: TIME:=T#0s;
		tmr_StepDelay: TON;
		b_WaitDone: BOOL:=FALSE;
		b_DelayDone: BOOL:=FALSE;
		tmr_InputWait: TON;
		b_InputWaitStart: BOOL:=FALSE;
		b_InputWaitDone: BOOL:=FALSE;
		t_InputTimeout: TIME:=T#5s;
		b_CurrentInput: BOOL:=FALSE;
		i_WaitPort: INT:=0;
		w_InputMask: WORD:=0;
		i_PopupResponse: INT:=0;
		b_InputCondMet: BOOL:=FALSE;	(* 입력 조건 충족 여부 (타임아웃 블록 충돌 방지용) *)
		b_TimeoutImmediate: BOOL:=FALSE;	(* 타임아웃 미사용(diParam2=0) 즉시 분기 플래그 *)
		b_JmpCond: BOOL:=FALSE;			(* JMP 조건 평가 결과 *)
		i_JmpPort: INT:=0;				(* JMP 조건 포트/모드 번호 *)
		i_JmpBit: INT:=0;				(* JMP 모드 조건 비트 번호 *)
		@'': @'';
	END_VAR


=========================================================================== *)






(* ===========================================================================
   [FB 본문]
=========================================================================== *)

(* 1. 입력 매핑 *)
FOR i_LoopAxis := 1 TO 8 DO
    w_ShiftNum := INT_TO_WORD(7 + i_LoopAxis);
    w_AxisMask := SHL(WORD#1, w_ShiftNum); 
    IF (WX11 AND w_AxisMask) <> 0 THEN arr_bBusy[i_LoopAxis] := TRUE; ELSE arr_bBusy[i_LoopAxis] := FALSE; END_IF;

    w_ShiftNum := INT_TO_WORD(i_LoopAxis - 1);
    w_AxisMask := SHL(WORD#1, w_ShiftNum);
    IF (WX12 AND w_AxisMask) <> 0 THEN arr_bDone[i_LoopAxis] := TRUE; ELSE arr_bDone[i_LoopAxis] := FALSE; END_IF;
END_FOR;

(* 리셋 로직 *)
IF b_Reset THEN
    i_SeqState := 0;
    i_CurrentStep := 0; 
    b_Error := FALSE;
    i_ErrorID := 0;
    b_StepDone := FALSE;
    b_TimerStart := FALSE;
    b_DelayStart := FALSE;
    b_InputWaitStart := FALSE;
    gw_SeqPopup := 0;
    gw_PopupResp := 0;

    FOR i_LoopAxis := 1 TO 8 DO arr_bStart[i_LoopAxis] := FALSE; END_FOR;
    FOR i_ResetLoop := 0 TO 31 DO valveOutput[i_ResetLoop] := FALSE; END_FOR;
    gw_InternalBit0 := 0;   (* M00~M15 내부비트 초기화 *)
    gw_InternalBit1 := 0;   (* M16~M31 내부비트 초기화 *)
    
    RETURN;
END_IF;


(* 2. 시퀀스 로직 *)
CASE i_SeqState OF

    0: (* 대기 *)
        b_StepDone := FALSE;
        b_TimerStart := FALSE; 
        b_DelayStart := FALSE; 
		b_Step_End := false;
        IF b_Run THEN
            IF i_CurrentStep < 0 OR i_CurrentStep > 49 THEN i_CurrentStep := 0; END_IF;
            i_SeqState := 10; 
        END_IF;

    10: (* 커맨드 해석 *)
        CASE arr_StepData[i_CurrentStep].iCommand OF
            10: i_SeqState := 11;
            20: i_SeqState := 40;
            21: i_SeqState := 60;
            30: i_SeqState := 50;
            40: i_SeqState := 70;
            99: b_Run := FALSE; i_CurrentStep := 0; i_SeqState := 0; b_Step_End := true;
            0:  i_SeqState := 0;
            ELSE i_ErrorID := 99; i_SeqState := 900; 
        END_CASE;

    (* ---- [위치 이동] ---- *)
    11: (* 테이블 번호 쓰기 *)
        i_WriteTableNo := DINT_TO_INT(arr_StepData[i_CurrentStep].diParam1) + 10026;
        FOR i_LoopAxis := 1 TO 8 DO
            w_ShiftNum := INT_TO_WORD(i_LoopAxis - 1);
            w_AxisMask := SHL(WORD#1, w_ShiftNum);
            IF (arr_StepData[i_CurrentStep].wOption AND w_AxisMask) <> 0 THEN
                w_WriteAddr := 16#0100 OR INT_TO_WORD(i_LoopAxis - 1);
                F151_WRT(s1_BankSlot := 16#0000, s2_Start := Adr_Of_Var(i_WriteTableNo), n_Number := 1, d_Start := w_WriteAddr);
            END_IF;
        END_FOR;
        i_SeqState := 20;

    20: (* 기동 신호 ON *)
        FOR i_LoopAxis := 1 TO 8 DO
            w_ShiftNum := INT_TO_WORD(i_LoopAxis - 1);
            w_AxisMask := SHL(WORD#1, w_ShiftNum);
            IF (arr_StepData[i_CurrentStep].wOption AND w_AxisMask) <> 0 THEN
                arr_bStart[i_LoopAxis] := TRUE;
            END_IF;
        END_FOR;
        b_TimerStart := FALSE; 
        i_SeqState := 21;

    21: (* 기동 확인 *)
        b_AnyBusy := FALSE;
        FOR i_LoopAxis := 1 TO 8 DO
            IF arr_bStart[i_LoopAxis] AND arr_bBusy[i_LoopAxis] THEN
                arr_bStart[i_LoopAxis] := FALSE; 
                b_AnyBusy := TRUE; 
            END_IF;
        END_FOR;

        IF b_AnyBusy THEN
            b_TimerStart := FALSE;
            FOR i_LoopAxis := 1 TO 8 DO arr_bStart[i_LoopAxis] := FALSE; END_FOR;
            i_SeqState := 30;
        ELSE
            b_TimerStart := TRUE; 
            
            (* [수정] .Q 대신 b_WaitDone 변수 확인 *)
            (* 주의: 아래쪽 타이머 호출 코드에 의해 b_WaitDone이 업데이트됨 *)
            IF b_WaitDone THEN
                b_AllDone := TRUE;
                FOR i_LoopAxis := 1 TO 8 DO
                     w_ShiftNum := INT_TO_WORD(i_LoopAxis - 1);
                     w_AxisMask := SHL(WORD#1, w_ShiftNum);
                     IF (arr_StepData[i_CurrentStep].wOption AND w_AxisMask) <> 0 THEN
                         IF NOT arr_bDone[i_LoopAxis] THEN b_AllDone := FALSE; END_IF;
                     END_IF;
                END_FOR;
                b_TimerStart := FALSE; 
                FOR i_LoopAxis := 1 TO 8 DO arr_bStart[i_LoopAxis] := FALSE; END_FOR;
                IF b_AllDone THEN i_SeqState := 99; ELSE i_ErrorID := 21; i_SeqState := 900; END_IF;
            END_IF;
        END_IF;

    30: (* 완료 대기 *)
        b_AllDone := TRUE;
        FOR i_LoopAxis := 1 TO 8 DO
            w_ShiftNum := INT_TO_WORD(i_LoopAxis - 1);
            w_AxisMask := SHL(WORD#1, w_ShiftNum);
            IF (arr_StepData[i_CurrentStep].wOption AND w_AxisMask) <> 0 THEN
                IF arr_bBusy[i_LoopAxis] THEN b_AllDone := FALSE; END_IF;
            END_IF;
        END_FOR;
        IF b_AllDone THEN i_SeqState := 99; END_IF;

    (* ---- [출력 제어] ---- *)
    40:
        i_OutIndex := DINT_TO_INT(arr_StepData[i_CurrentStep].diParam1);
        IF i_OutIndex >= 0 AND i_OutIndex <= 31 THEN
            valveOutput[i_OutIndex] := (arr_StepData[i_CurrentStep].wOption = 1);
        ELSIF i_OutIndex >= 100 AND i_OutIndex <= 115 THEN
            (* M00~M15 → gw_InternalBit0 비트 제어 *)
            w_InputMask := SHL(WORD#1, INT_TO_WORD(i_OutIndex - 100));
            IF arr_StepData[i_CurrentStep].wOption = 1 THEN
                gw_InternalBit0 := gw_InternalBit0 OR w_InputMask;
            ELSE
                gw_InternalBit0 := gw_InternalBit0 AND (NOT w_InputMask);
            END_IF;
        ELSIF i_OutIndex >= 116 AND i_OutIndex <= 131 THEN
            (* M16~M31 → gw_InternalBit1 비트 제어 *)
            w_InputMask := SHL(WORD#1, INT_TO_WORD(i_OutIndex - 116));
            IF arr_StepData[i_CurrentStep].wOption = 1 THEN
                gw_InternalBit1 := gw_InternalBit1 OR w_InputMask;
            ELSE
                gw_InternalBit1 := gw_InternalBit1 AND (NOT w_InputMask);
            END_IF;
        END_IF;
        i_SeqState := 99;

    (* ---- [입력 대기] ---- *)
    60: (* 입력 대기 초기화 *)
        i_WaitPort := DINT_TO_INT(arr_StepData[i_CurrentStep].diParam1);
        t_InputTimeout := DINT_TO_TIME(arr_StepData[i_CurrentStep].diParam2);
        b_InputWaitStart := TRUE;
        i_SeqState := 61;

    61: (* 입력 상태 확인 *)
        (* 입력 읽기 *)
        IF i_WaitPort >= 0 AND i_WaitPort <= 15 THEN
            w_InputMask := SHL(WORD#1, INT_TO_WORD(i_WaitPort));
            b_CurrentInput := (WX0 AND w_InputMask) <> 0;
        ELSIF i_WaitPort >= 16 AND i_WaitPort <= 31 THEN
            w_InputMask := SHL(WORD#1, INT_TO_WORD(i_WaitPort - 16));
            b_CurrentInput := (WX1 AND w_InputMask) <> 0;
        ELSIF i_WaitPort >= 100 AND i_WaitPort <= 115 THEN
            (* M00~M15 → gw_InternalBit0 비트 읽기 *)
            w_InputMask := SHL(WORD#1, INT_TO_WORD(i_WaitPort - 100));
            b_CurrentInput := (gw_InternalBit0 AND w_InputMask) <> 0;
        ELSIF i_WaitPort >= 116 AND i_WaitPort <= 131 THEN
            (* M16~M31 → gw_InternalBit1 비트 읽기 *)
            w_InputMask := SHL(WORD#1, INT_TO_WORD(i_WaitPort - 116));
            b_CurrentInput := (gw_InternalBit1 AND w_InputMask) <> 0;
        ELSE
            b_CurrentInput := FALSE;
        END_IF;

        (* ON/OFF 조건 체크 *)
        b_InputCondMet := FALSE;
        IF arr_StepData[i_CurrentStep].wOption = 1 THEN
            IF b_CurrentInput THEN
                b_InputWaitStart := FALSE;
                i_SeqState := 99;
                b_InputCondMet := TRUE;
            END_IF;
        ELSE
            IF NOT b_CurrentInput THEN
                b_InputWaitStart := FALSE;
                i_SeqState := 99;
                b_InputCondMet := TRUE;
            END_IF;
        END_IF;

        (* 타임아웃 처리 (조건 미충족 시에만) *)
        (* b_TimeoutImmediate: diParam2=0(미사용)일 때 즉시 분기 *)
        b_TimeoutImmediate := (arr_StepData[i_CurrentStep].diParam2 = 0);
        IF NOT b_InputCondMet THEN
            IF b_InputWaitDone OR b_TimeoutImmediate THEN
                b_InputWaitStart := FALSE;
                CASE DINT_TO_INT(arr_StepData[i_CurrentStep].diParam3) OF
                    1: (* 계속 대기 - 타이머 리셋 후 입력 대기 유지 *)
                        b_InputWaitStart := TRUE;
                    2: (* stop - 에러 정지 *)
                        i_ErrorID := 61;
                        i_SeqState := 900;
                    3: (* jump - 특정 스텝으로 *)
                        i_CurrentStep := DINT_TO_INT(arr_StepData[i_CurrentStep].diParam4);
                        i_SeqState := 10;
                    ELSE (* ask - 작업자 팝업 요청 *)
                        gw_SeqPopup := 1;
                        gw_PopupResp := 0;
                        i_SeqState := 62;
                END_CASE;
            END_IF;
        END_IF;

    62: (* 작업자 응답 대기 *)
        i_PopupResponse := WORD_TO_INT(gw_PopupResp);
        IF i_PopupResponse = 1 THEN       (* 계속 *)
            gw_SeqPopup := 0;
            gw_PopupResp := 0;
            b_InputWaitStart := TRUE;     (* 타이머 리셋 후 입력 대기 재개 *)
            i_SeqState := 61;
        ELSIF i_PopupResponse = 2 THEN    (* 정지 *)
            gw_SeqPopup := 0;
            gw_PopupResp := 0;
            i_ErrorID := 62;
            i_SeqState := 900;
        END_IF;

    (* ---- [점프] ---- *)
    70: (* JMP 처리 *)
        IF arr_StepData[i_CurrentStep].wOption = 0 THEN
            (* 무조건 점프 *)
            i_CurrentStep := DINT_TO_INT(arr_StepData[i_CurrentStep].diParam1);
            i_SeqState := 10;
        ELSE
            (* 조건부 점프 - 조건 읽기 *)
            i_JmpPort := DINT_TO_INT(arr_StepData[i_CurrentStep].diParam3);
            IF DINT_TO_INT(arr_StepData[i_CurrentStep].diParam2) = 1 THEN
                (* MODE 조건 (0~39) *)
                i_JmpBit := i_JmpPort MOD 16;
                w_InputMask := SHL(WORD#1, INT_TO_WORD(i_JmpBit));
                CASE i_JmpPort / 16 OF
                    0: b_JmpCond := (gw_ModeWord0 AND w_InputMask) <> 0;
                    1: b_JmpCond := (gw_ModeWord1 AND w_InputMask) <> 0;
                    2: b_JmpCond := (gw_ModeWord2 AND w_InputMask) <> 0;
                    ELSE b_JmpCond := FALSE;
                END_CASE;
            ELSE
                (* PORT 조건 *)
                IF i_JmpPort >= 0 AND i_JmpPort <= 15 THEN
                    w_InputMask := SHL(WORD#1, INT_TO_WORD(i_JmpPort));
                    b_JmpCond := (WX0 AND w_InputMask) <> 0;
                ELSIF i_JmpPort >= 16 AND i_JmpPort <= 31 THEN
                    w_InputMask := SHL(WORD#1, INT_TO_WORD(i_JmpPort - 16));
                    b_JmpCond := (WX1 AND w_InputMask) <> 0;
                ELSIF i_JmpPort >= 100 AND i_JmpPort <= 115 THEN
                    (* M00~M15 → gw_InternalBit0 비트 읽기 *)
                    w_InputMask := SHL(WORD#1, INT_TO_WORD(i_JmpPort - 100));
                    b_JmpCond := (gw_InternalBit0 AND w_InputMask) <> 0;
                ELSIF i_JmpPort >= 116 AND i_JmpPort <= 131 THEN
                    (* M16~M31 → gw_InternalBit1 비트 읽기 *)
                    w_InputMask := SHL(WORD#1, INT_TO_WORD(i_JmpPort - 116));
                    b_JmpCond := (gw_InternalBit1 AND w_InputMask) <> 0;
                ELSE
                    b_JmpCond := FALSE;
                END_IF;
            END_IF;
            (* ON/OFF 비교 및 점프 실행 *)
            IF DINT_TO_INT(arr_StepData[i_CurrentStep].diParam4) = 1 THEN
                (* ON 조건 *)
                IF b_JmpCond THEN
                    i_CurrentStep := DINT_TO_INT(arr_StepData[i_CurrentStep].diParam1);
                    i_SeqState := 10;
                ELSE
                    i_SeqState := 99;
                END_IF;
            ELSE
                (* OFF 조건 *)
                IF NOT b_JmpCond THEN
                    i_CurrentStep := DINT_TO_INT(arr_StepData[i_CurrentStep].diParam1);
                    i_SeqState := 10;
                ELSE
                    i_SeqState := 99;
                END_IF;
            END_IF;
        END_IF;

    (* ---- [타이머 지연] ---- *)
    50:
        t_DelaySetting := DINT_TO_TIME(arr_StepData[i_CurrentStep].diParam1);
        b_DelayStart := TRUE;

        (* [수정] .Q 대신 b_DelayDone 변수 확인 *)
        IF b_DelayDone THEN
            b_DelayStart := FALSE; 
            i_SeqState := 99;      
        END_IF;


    99: (* 스텝 완료 *)
        b_StepDone := TRUE; 
        i_CurrentStep := i_CurrentStep + 1;
        IF i_CurrentStep > 49 THEN i_CurrentStep := 0; END_IF;
        IF b_Run THEN i_SeqState := 10; ELSE i_SeqState := 0; END_IF;

    900: (* 에러 *)
        b_Error := TRUE;
        b_TimerStart := FALSE;
        b_DelayStart := FALSE;

END_CASE;

(* ===========================================================================
   [3. 타이머 호출 (Output Mapping 적용)] 
   - Q => 변수명 : 이렇게 하면 .Q를 안 써도 결과가 변수에 담깁니다.
=========================================================================== *)

(* 에러 체크용 타이머 *)
tmr_StartWait(IN := b_TimerStart, PT := t_WaitTime, Q => b_WaitDone);

(* 시퀀스 지연용 타이머 *)
tmr_StepDelay(IN := b_DelayStart, PT := t_DelaySetting, Q => b_DelayDone);

(* 입력 대기 타임아웃 타이머 *)
tmr_InputWait(IN := b_InputWaitStart, PT := t_InputTimeout, Q => b_InputWaitDone);