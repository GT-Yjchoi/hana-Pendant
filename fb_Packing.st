(* ---------------------------------------------------------------------------
   fb_Packing : 파렛타이징 타겟 좌표 계산 및 RTEX 스크래치 테이블 기록

   기능
     베이스 포인트(g_Dut_Point[i_BasePointIdx])의 좌표에
     (pack_idx × pitch × dir) 오프셋을 더해 **RTEX 스크래치 테이블(10089, idx=63)**
     에만 기록. 원본 포인트 데이터는 절대 변경하지 않음 → HMI 에는 티칭값 그대로 표시.

   가감산 축
     X(1축), Y(2축), Z(3축) 3축만 오프셋 적용.
     Y2(4축), Z2(5축)는 베이스 좌표 그대로 사용.

   호출 시점
     new_plc_fb.st 의 POS 처리 state 11 에서 w_StepOpt bit5(pack_base)가 ON 이면 호출.
     1 스캔 rising edge 로 F151_WRT 5회 실행 후 Done.

   RTEX 전파
     F151_WRT 후 RTEX 전파에 50ms 필요 — state 11 → state 12 의 기존 settle
     타이머(T#50MS)가 표 번호 write 와 함께 커버함.

   속도 배율
     fb_WriteMotionTable 와 동일 공식:
       TargetSpeed = speed% × RatedRPM × PPR × (override/10) / 6000
       현재 전축 RatedRPM = 3000 → speed% × PPR × override / 20

   GLOBAL 의존성 (fb_WriteMotionTable 와 공유)
     TYPE (DUT)
       TABLE_DATA_DUT  : RTEX 테이블 구조체
       POINT_DATA_DUT  : 포인트 데이터 구조체 (diPosX/iSpeedX/... 8축분)
     GLOBAL_VAR
       g_Dut_Point      : ARRAY[0..59] OF POINT_DATA_DUT;
       gi_SpeedOverride : INT;                 (* DT216 전체 속도 배율 1..10 *)
       gi_1축AccDec ~ gi_5축AccDec : INT;      (* 축별 가감속 시간 *)
       gdi_1축PPR   ~ gdi_5축PPR   : DINT;     (* 축별 서보 1회전당 펄스수 *)
     END_VAR
     ※ Global Variables 로 승격되어 있으므로 VAR_INPUT 으로 다시 받지 않음.
       두 FB 공통 참조 → 와이어링 생략 + 인스턴스 코드 복제 비용 절감.

   스크래치 테이블 제약
     RTEX 테이블 64개 중 할당:
       인덱스 0..59 : 일반 포인트 (총 60개)
       인덱스 60..62 : 예비 (미래 확장용)
       인덱스 63    : 파렛타이징 스크래치 (fb_Packing 전용, RTEX 10089)
     fb_WriteMotionTable.i_WriteCount 최대 60 으로 클램프.

   ---- 선언부 (FPWIN 편집기의 변수 탭에 입력) --------------------------------

   VAR_INPUT
       b_Execute        : BOOL;                  (* 실행 트리거 (rising edge) *)
       i_BasePointIdx   : INT;                   (* 베이스 포인트 인덱스 0..59 *)
       i_PackIdxX       : INT;                   (* 현재 X 스택 인덱스 (0-based) *)
       i_PackIdxY       : INT;                   (* 현재 Y 스택 인덱스 *)
       i_PackIdxZ       : INT;                   (* 현재 Z 스택 인덱스 *)
       di_PitchX        : DINT;                  (* X 피치 (0.001mm 단위) *)
       di_PitchY        : DINT;                  (* Y 피치 *)
       di_PitchZ        : DINT;                  (* Z 피치 *)
       i_DirX           : INT;                   (* X 방향 +1 / -1 *)
       i_DirY           : INT;                   (* Y 방향 +1 / -1 *)
       i_DirZ           : INT;                   (* Z 방향 (보통 +1) *)
   END_VAR

   VAR_OUTPUT
       b_Done           : BOOL;                  (* 1 스캔 완료 펄스 *)
       b_Error          : BOOL;                  (* 에러 발생 *)
       i_ErrorID        : INT;                   (* 1: 포인트 인덱스 범위 오류 *)
   END_VAR

   VAR
       R_TRIG_Execute   : R_TRIG;
       i_LoopAxis       : INT;
       w_BankSlot       : WORD;
       w_TableOffset    : WORD;
       di_BasePos       : DINT;
       di_Offset        : DINT;
       di_TargetPos     : DINT;
       i_TargetSpeed    : INT;
       i_AccDec         : INT;
       di_PPR           : DINT;
       i_RealOverride   : INT;
       TableData        : TABLE_DATA_DUT;
   END_VAR

   VAR CONSTANT
       SCRATCH_TABLE_IDX : INT := 63;    (* RTEX 테이블 번호 10089 = 10026 + 63 *)
       MAX_POINT_IDX     : INT := 59;    (* 일반 포인트 0..59 (60~62 예약, 63 스크래치) *)
   END_VAR

   -------------------------------------------------------------------------- *)

R_TRIG_Execute(CLK := b_Execute);

IF R_TRIG_Execute.Q THEN

    (* 출력 초기화 *)
    b_Done    := FALSE;
    b_Error   := FALSE;
    i_ErrorID := 0;

    (* 포인트 인덱스 범위 체크 *)
    IF (i_BasePointIdx < 0) OR (i_BasePointIdx > MAX_POINT_IDX) THEN
        b_Error   := TRUE;
        i_ErrorID := 1;
        RETURN;
    END_IF;

    (* 속도 배율 클램프 (fb_WriteMotionTable 와 동일) *)
    IF (gi_SpeedOverride < 1) OR (gi_SpeedOverride > 10) THEN
        i_RealOverride := 10;
    ELSE
        i_RealOverride := gi_SpeedOverride;
    END_IF;

    (* 공통 테이블 데이터 (fb_WriteMotionTable 와 동일 기본값) *)
    TableData.ControlCode := 16#0001;      (* E point *)
    TableData.Pattern     := 16#0000;      (* End *)
    TableData.dummy1      := 0;
    TableData.dummy2      := 0;
    TableData.AuxPoint    := 0;
    TableData.DwellTime   := 0;
    TableData.AuxOutput   := 0;
    TableData.dummy3      := 0;
    TableData.dummy4      := 0;

    (* 스크래치 테이블 오프셋: 테이블당 16 Words (0x10) *)
    w_TableOffset := INT_TO_WORD(SCRATCH_TABLE_IDX * 16);

    (* ==========================================================
       5축 반복: 각 축의 베이스 좌표 + 오프셋(X/Y/Z만)을 스크래치 기록
       ========================================================== *)
    FOR i_LoopAxis := 1 TO 5 DO

        (* 축별 뱅크 슬롯 (0x6000 | (axis<<8)) *)
        w_BankSlot := 16#6000 OR SHL(INT_TO_WORD(i_LoopAxis), 8);

        (* 축별 베이스 좌표 / 속도 / 파라미터 추출 + 오프셋 계산 *)
        CASE i_LoopAxis OF
            1:  (* X축 — 오프셋 적용 *)
                di_BasePos    := g_Dut_Point[i_BasePointIdx].diPosX;
                i_TargetSpeed := g_Dut_Point[i_BasePointIdx].iSpeedX;
                i_AccDec      := gi_1축AccDec;
                di_PPR        := gdi_1축PPR;
                di_Offset     := INT_TO_DINT(i_PackIdxX) * di_PitchX * INT_TO_DINT(i_DirX);
                di_TargetPos  := di_BasePos + di_Offset;

            2:  (* Y축 — 오프셋 적용 *)
                di_BasePos    := g_Dut_Point[i_BasePointIdx].diPosY;
                i_TargetSpeed := g_Dut_Point[i_BasePointIdx].iSpeedY;
                i_AccDec      := gi_2축AccDec;
                di_PPR        := gdi_2축PPR;
                di_Offset     := INT_TO_DINT(i_PackIdxY) * di_PitchY * INT_TO_DINT(i_DirY);
                di_TargetPos  := di_BasePos + di_Offset;

            3:  (* Z축 — 오프셋 적용 *)
                di_BasePos    := g_Dut_Point[i_BasePointIdx].diPosZ;
                i_TargetSpeed := g_Dut_Point[i_BasePointIdx].iSpeedZ;
                i_AccDec      := gi_3축AccDec;
                di_PPR        := gdi_3축PPR;
                di_Offset     := INT_TO_DINT(i_PackIdxZ) * di_PitchZ * INT_TO_DINT(i_DirZ);
                di_TargetPos  := di_BasePos + di_Offset;

            4:  (* Y2축 — 오프셋 없음 (원본 유지) *)
                di_BasePos    := g_Dut_Point[i_BasePointIdx].diPosY2;
                i_TargetSpeed := g_Dut_Point[i_BasePointIdx].iSpeedY2;
                i_AccDec      := gi_4축AccDec;
                di_PPR        := gdi_4축PPR;
                di_TargetPos  := di_BasePos;

            5:  (* Z2축 — 오프셋 없음 (원본 유지) *)
                di_BasePos    := g_Dut_Point[i_BasePointIdx].diPosZ2;
                i_TargetSpeed := g_Dut_Point[i_BasePointIdx].iSpeedZ2;
                i_AccDec      := gi_5축AccDec;
                di_PPR        := gdi_5축PPR;
                di_TargetPos  := di_BasePos;
        END_CASE;

        (* 테이블 구조체 필드 채우기 *)
        TableData.TargetPosition := di_TargetPos;
        (* 속도 계산: speed% × PPR × override / 20 (fb_WriteMotionTable 동일 공식) *)
        TableData.TargetSpeed := INT_TO_UDINT(i_TargetSpeed)
                                 * DINT_TO_UDINT(di_PPR)
                                 * INT_TO_UDINT(i_RealOverride)
                                 / 20;
        TableData.AccTime := i_AccDec;
        TableData.DecTime := i_AccDec;

        (* RTEX 스크래치 테이블(10089) 쓰기 *)
        F151_WRT(
            s1_BankSlot := w_BankSlot,
            s2_Start    := Adr_Of_Var(TableData),
            n_Number    := 16,
            d_Start     := w_TableOffset
        );

    END_FOR;

    b_Done := TRUE;

END_IF;

IF NOT b_Execute THEN
    b_Done := FALSE;
END_IF;
