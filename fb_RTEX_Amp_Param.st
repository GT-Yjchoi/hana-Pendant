(* ---------------------------------------------------------------------------
   fb_RTEX_Amp_Param : RTEX 서보 앰프 파라미터 읽기/쓰기 (1~5축)
   - DUT(dutAxis) 사용 안 함
   - bExecute 상승 엣지 → 1축부터 5축까지 순차 처리
   - 각 축마다 제어플래그 폴링 후 다음 축으로 진행
   - 모든 축 처리 완료 시 bDone 발행

   uiFunction : 1 = 읽기 (Read)
                2 = 쓰기 (Write, RAM)
                3 = EEPROM 쓰기 (영구 저장)

   파라미터 지령 인터페이스 (16#5200 + uiSlotNumber):
     +16#0000 : Amp ID (축 번호, 0-base: 0~7)
     +16#0001 : 제어 플래그 (2=read, 4=write, 5=EEPROM)
     +16#0002 : 상태 (응답)
     +16#0003 : 파라미터 분류 (Class)
     +16#0024 : 파라미터 번호
     +16#0026 : 파라미터 값 (DINT, 2 워드)
--------------------------------------------------------------------------- *)

(*
VAR_INPUT
    bExecute           : BOOL;
    uiSlotNumber       : UINT;   (* RTEX 모듈 슬롯 0~3 *)
    uiFunction         : UINT;   (* 1=읽기, 2=쓰기, 3=EEPROM 쓰기 *)
    uiClass            : UINT;   (* 파라미터 분류 *)
    uiParameter        : UINT;   (* 파라미터 번호 *)
END_VAR
VAR_IN_OUT
    diParameterData1   : DINT;   (* 1축 파라미터 값 — 쓰기 시 입력, 읽기 시 출력 *)
    diParameterData2   : DINT;
    diParameterData3   : DINT;
    diParameterData4   : DINT;
    diParameterData5   : DINT;
END_VAR
VAR_OUTPUT
    bBusy              : BOOL;
    bDone              : BOOL;
    bError             : BOOL;
    dwErrorID          : DWORD;
    uiStatus           : UINT;   (* 마지막 처리된 축의 완료 상태 *)
END_VAR
VAR
    iState             : INT;    (* 0=idle, 1=init axis, 2=wait, 10=done, 900=error *)
    iCurrentAxis       : INT;    (* 1~5 *)
    awTemp             : ARRAY[0..1] OF WORD;
    diTempData         : DINT;   (* 쓰기/읽기 임시 버퍼 *)
    bExecutePrev       : BOOL;   (* bExecute 엣지 검출용 *)
END_VAR
*)


(* ── 0. bExecute 상승/하강 엣지 검출 ── *)
IF (bExecute AND NOT bExecutePrev) THEN
    (* 상승 엣지 — 처리 시작 *)
    IF (uiSlotNumber > 3) THEN
        dwErrorID := 1;
        bError := TRUE;
        iState := 900;
    ELSIF ((uiFunction < 1) OR (uiFunction > 3)) THEN
        dwErrorID := 4;
        bError := TRUE;
        iState := 900;
    ELSIF (bBusy) THEN
        dwErrorID := 8;
        bError := TRUE;
        iState := 900;
    ELSE
        bBusy := TRUE;
        bDone := FALSE;
        bError := FALSE;
        dwErrorID := 0;
        iCurrentAxis := 1;
        iState := 1;
    END_IF;
ELSIF (NOT bExecute AND bExecutePrev) THEN
    (* 하강 엣지 — 상태 리셋 *)
    bError := FALSE;
    dwErrorID := 0;
    bBusy := FALSE;
    bDone := FALSE;
    uiStatus := 0;
    iState := 0;
END_IF;
bExecutePrev := bExecute;


(* ── 1. 상태 머신 ── *)
CASE iState OF

    0: (* idle — 아무 동작 없음. 빈 CASE 브랜치 금지되어 no-op 명시 *)
        iState := 0;


    1: (* 현재 축 초기화: amp id, class, param, (쓰기 데이터), 제어플래그 순서 *)

        (* 1-1. Amp ID 쓰기 (1-base 축 번호 직결) *)
        awTemp[0] := INT_TO_WORD(iCurrentAxis);
        F151_WRT(s1_BankSlot := 16#5200 + uiSlotNumber,
                 s2_Start   := awTemp[0],
                 n_Number   := 1,
                 d_Start    := 16#0000);

        (* 1-2. 파라미터 분류 *)
        F151_WRT(s1_BankSlot := 16#5200 + uiSlotNumber,
                 s2_Start   := uiClass,
                 n_Number   := 1,
                 d_Start    := 16#0003);

        (* 1-3. 파라미터 번호 *)
        F151_WRT(s1_BankSlot := 16#5200 + uiSlotNumber,
                 s2_Start   := uiParameter,
                 n_Number   := 1,
                 d_Start    := 16#0024);

        (* 1-4. 쓰기 함수(2)일 때만 데이터 쓰기 *)
        IF (uiFunction = 2) THEN
            CASE iCurrentAxis OF
                1: diTempData := diParameterData1;
                2: diTempData := diParameterData2;
                3: diTempData := diParameterData3;
                4: diTempData := diParameterData4;
                5: diTempData := diParameterData5;
            END_CASE;
            F151_WRT(s1_BankSlot := 16#5200 + uiSlotNumber,
                     s2_Start   := Adr_Of_Var(diTempData),
                     n_Number   := 2,
                     d_Start    := 16#0026);
        END_IF;

        (* 1-5. 제어 플래그 설정 (기동) *)
        CASE uiFunction OF
            1: awTemp[0] := 2;   (* 읽기 요청 *)
            2: awTemp[0] := 4;   (* 쓰기 요청 *)
            3: awTemp[0] := 5;   (* EEPROM 쓰기 *)
        END_CASE;
        F151_WRT(s1_BankSlot := 16#5200 + uiSlotNumber,
                 s2_Start   := awTemp[0],
                 n_Number   := 1,
                 d_Start    := 16#0001);

        iState := 2;


    2: (* 완료 대기 — 제어 플래그가 0이 되면 앰프 처리 완료 *)

        F150_READ(s1_BankSlot := 16#5200 + uiSlotNumber,
                  s2_Start   := 16#0001,
                  n_Number   := 2,
                  d_Start    := awTemp[0]);

        IF (awTemp[0] = 0) THEN
            (* 현재 축 처리 완료 *)
            IF ((awTemp[1] = 2) AND ((uiFunction = 1) OR (uiFunction = 2))) THEN
                (* 정상 완료: 파라미터 값 읽기 *)
                F150_READ(s1_BankSlot := 16#5200 + uiSlotNumber,
                          s2_Start   := 16#0026,
                          n_Number   := 2,
                          d_Start    := Adr_Of_Var(diTempData));
                CASE iCurrentAxis OF
                    1: diParameterData1 := diTempData;
                    2: diParameterData2 := diTempData;
                    3: diParameterData3 := diTempData;
                    4: diParameterData4 := diTempData;
                    5: diParameterData5 := diTempData;
                END_CASE;
            END_IF;
            uiStatus := TO_UINT(awTemp[1]);

            (* 다음 축으로 또는 완료 *)
            IF (iCurrentAxis >= 5) THEN
                iState := 10;
            ELSE
                iCurrentAxis := iCurrentAxis + 1;
                iState := 1;
            END_IF;
        END_IF;


    10: (* 전체 완료 *)
        bBusy := FALSE;
        bDone := TRUE;
        iState := 0;


    900: (* 에러 *)
        bBusy := FALSE;
        bDone := FALSE;
        (* bError, dwErrorID는 이미 세팅됨 *)
        iState := 0;

END_CASE;
