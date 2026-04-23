(* -------------------------------------------------- *)
(* MainAxis.st                                         *)
(* RTEX 축 1~5 간소화 모니터링 (개별 BOOL 필드 접근)    *)
(* -------------------------------------------------- *)

(*
VAR_INPUT
    uiSlotNumber        : UINT;   (* 0..3 *)
END_VAR
VAR_OUTPUT
    bLinkEstablished    : BOOL;

    bAxisConnected1     : BOOL;
    bAxisConnected2     : BOOL;
    bAxisConnected3     : BOOL;
    bAxisConnected4     : BOOL;
    bAxisConnected5     : BOOL;

    bAxisServoLocked1   : BOOL;
    bAxisServoLocked2   : BOOL;
    bAxisServoLocked3   : BOOL;
    bAxisServoLocked4   : BOOL;
    bAxisServoLocked5   : BOOL;

    diCurrentValue1     : DINT;
    diCurrentValue2     : DINT;
    diCurrentValue3     : DINT;
    diCurrentValue4     : DINT;
    diCurrentValue5     : DINT;

    iMotorRPM1          : INT;    (* 1축 현재 RPM (1워드) *)
    iMotorRPM2          : INT;    (* 2축 현재 RPM *)
    iMotorRPM3          : INT;    (* 3축 현재 RPM *)
    iMotorRPM4          : INT;    (* 4축 현재 RPM *)
    iMotorRPM5          : INT;    (* 5축 현재 RPM *)

    dwErrorID1          : DWORD;
    dwErrorID2          : DWORD;
    dwErrorID3          : DWORD;
    dwErrorID4          : DWORD;
    dwErrorID5          : DWORD;

    wError              : WORD;   (* 축별 에러 비트. bit0=1축 ~ bit4=5축 *)

    bError              : BOOL;   (* 슬롯 범위 에러 *)
END_VAR
VAR
    iIXsave             : INT;
    iIYsave             : INT;
    RTEX_WX10_DUT       : BOOL16_OVERLAPPING_DUT;
    RTEX_WX11_DUT       : BOOL16_OVERLAPPING_DUT;
    Error_DUT           : BOOL16_OVERLAPPING_DUT;
END_VAR
*)

iIXsave := IX;
iIYsave := IY;

(* 슬롯 범위 체크 *)
IF (uiSlotNumber > 3) THEN
    bError := TRUE;
    IX := iIXsave;
    IY := iIYsave;
    RETURN;
ELSE
    bError := FALSE;
END_IF;

(* 슬롯 고정 IX — WX10/11 1회 읽기로 5축 공용 처리 *)
IX := uiSlotNumber * 8;
RTEX_WX10_DUT.w0 := IXWX10;
RTEX_WX11_DUT.w0 := IXWX11;

(* 링크 상태 (WX10 bit 0) *)
bLinkEstablished  := RTEX_WX10_DUT.b0;

(* 연결 상태 (WX10 bit 8~12) *)
bAxisConnected1   := RTEX_WX10_DUT.b8;
bAxisConnected2   := RTEX_WX10_DUT.b9;
bAxisConnected3   := RTEX_WX10_DUT.b10;
bAxisConnected4   := RTEX_WX10_DUT.b11;
bAxisConnected5   := RTEX_WX10_DUT.b12;

(* 서보락 상태 (WX11 bit 0~4) *)
bAxisServoLocked1 := RTEX_WX11_DUT.b0;
bAxisServoLocked2 := RTEX_WX11_DUT.b1;
bAxisServoLocked3 := RTEX_WX11_DUT.b2;
bAxisServoLocked4 := RTEX_WX11_DUT.b3;
bAxisServoLocked5 := RTEX_WX11_DUT.b4;

(* 현재값 (DINT, 2워드) — 축별 F150_READ *)
F150_READ(s1_BankSlot := (16#0100 + uiSlotNumber),
          s2_Start    := 16#003E,
          n_Number    := 2,
          d_Start     := Adr_Of_Var(diCurrentValue1));
F150_READ(s1_BankSlot := (16#0100 + uiSlotNumber),
          s2_Start    := 16#007E,
          n_Number    := 2,
          d_Start     := Adr_Of_Var(diCurrentValue2));
F150_READ(s1_BankSlot := (16#0100 + uiSlotNumber),
          s2_Start    := 16#00BE,
          n_Number    := 2,
          d_Start     := Adr_Of_Var(diCurrentValue3));
F150_READ(s1_BankSlot := (16#0100 + uiSlotNumber),
          s2_Start    := 16#00FE,
          n_Number    := 2,
          d_Start     := Adr_Of_Var(diCurrentValue4));
F150_READ(s1_BankSlot := (16#0100 + uiSlotNumber),
          s2_Start    := 16#013E,
          n_Number    := 2,
          d_Start     := Adr_Of_Var(diCurrentValue5));

(* 현재 모터 RPM (INT, 1워드) — 축별 F150_READ
   1축: 0x0033, 2축: 0x0073, 3축: 0x00B3, 4축: 0x00F3, 5축: 0x0133 (간격 0x0040) *)
F150_READ(s1_BankSlot := (16#0100 + uiSlotNumber),
          s2_Start    := 16#0033,
          n_Number    := 1,
          d_Start     := Adr_Of_Var(iMotorRPM1));
F150_READ(s1_BankSlot := (16#0100 + uiSlotNumber),
          s2_Start    := 16#0073,
          n_Number    := 1,
          d_Start     := Adr_Of_Var(iMotorRPM2));
F150_READ(s1_BankSlot := (16#0100 + uiSlotNumber),
          s2_Start    := 16#00B3,
          n_Number    := 1,
          d_Start     := Adr_Of_Var(iMotorRPM3));
F150_READ(s1_BankSlot := (16#0100 + uiSlotNumber),
          s2_Start    := 16#00F3,
          n_Number    := 1,
          d_Start     := Adr_Of_Var(iMotorRPM4));
F150_READ(s1_BankSlot := (16#0100 + uiSlotNumber),
          s2_Start    := 16#0133,
          n_Number    := 1,
          d_Start     := Adr_Of_Var(iMotorRPM5));

(* 슬롯 에러 플래그 워드 1회 읽기 *)
F150_READ(s1_BankSlot := uiSlotNumber,
          s2_Start    := 16#0110,
          n_Number    := 1,
          d_Start     := Error_DUT.w0);

(* 에러 ID — 플래그가 서 있는 축만 버퍼 읽기 *)
IF (Error_DUT.b0) THEN
    F150_READ(s1_BankSlot := uiSlotNumber,
              s2_Start    := 16#012A,
              n_Number    := 2,
              d_Start     := Adr_Of_Var(dwErrorID1));
ELSE
    dwErrorID1 := 0;
END_IF;

IF (Error_DUT.b1) THEN
    F150_READ(s1_BankSlot := uiSlotNumber,
              s2_Start    := 16#013A,
              n_Number    := 2,
              d_Start     := Adr_Of_Var(dwErrorID2));
ELSE
    dwErrorID2 := 0;
END_IF;

IF (Error_DUT.b2) THEN
    F150_READ(s1_BankSlot := uiSlotNumber,
              s2_Start    := 16#014A,
              n_Number    := 2,
              d_Start     := Adr_Of_Var(dwErrorID3));
ELSE
    dwErrorID3 := 0;
END_IF;

IF (Error_DUT.b3) THEN
    F150_READ(s1_BankSlot := uiSlotNumber,
              s2_Start    := 16#015A,
              n_Number    := 2,
              d_Start     := Adr_Of_Var(dwErrorID4));
ELSE
    dwErrorID4 := 0;
END_IF;

IF (Error_DUT.b4) THEN
    F150_READ(s1_BankSlot := uiSlotNumber,
              s2_Start    := 16#016A,
              n_Number    := 2,
              d_Start     := Adr_Of_Var(dwErrorID5));
ELSE
    dwErrorID5 := 0;
END_IF;

(* 축별 에러 비트 워드 (bit0=1축 ~ bit4=5축) *)
wError := 0;
IF (Error_DUT.b0 OR (dwErrorID1 <> 0)) THEN wError := wError OR 16#0001; END_IF;
IF (Error_DUT.b1 OR (dwErrorID2 <> 0)) THEN wError := wError OR 16#0002; END_IF;
IF (Error_DUT.b2 OR (dwErrorID3 <> 0)) THEN wError := wError OR 16#0004; END_IF;
IF (Error_DUT.b3 OR (dwErrorID4 <> 0)) THEN wError := wError OR 16#0008; END_IF;
IF (Error_DUT.b4 OR (dwErrorID5 <> 0)) THEN wError := wError OR 16#0010; END_IF;

IX := iIXsave;
IY := iIYsave;
