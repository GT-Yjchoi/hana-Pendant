(* ---------------------------------------------------------------------------
   FB_WriteMotionTable_v5 : 일괄 쓰기 (Batch Write)
   기능 : DUT 배열의 데이터를 10026번 테이블부터 순차적으로 기록.
   제한 : 하드웨어는 10089번(총 64개)까지 가능하나, 테이블 할당 정책상
          최대 60개(10026~10085, idx 0..59)만 기록. 나머지는 예비/패킹 스크래치 전용.
            idx 0..59  : 일반 포인트 (fb_WriteMotionTable 전담)
            idx 60..62 : 예비 (미래 확장)
            idx 63     : 파렛타이징 스크래치 (fb_Packing 전용, RTEX 10089)

   전체속도 배율 (gi_SpeedOverride) : 1~10 단계
     DT216 을 글로벌 변수로 매핑.
     최종 속도 = 포인트속도(%) × (gi_SpeedOverride / 10)
     예) gi_SpeedOverride=10 → 100%, =5 → 50%, =1 → 10%

   ---- VAR_INPUT (FPWIN 변수 탭) --------------------------------------------
       b_Execute       : BOOL;     (* 실행 트리거 (rising edge) *)
       i_WriteCount    : INT;      (* 기록할 포인트 수 (최대 60으로 클램프) *)

   ---- VAR_OUTPUT -----------------------------------------------------------
       b_Done          : BOOL;
       b_Error         : BOOL;
       i_ErrorID       : INT;

   ---- GLOBAL 의존성 (fb_Packing 과 공유) ----------------------------------
       GLOBAL_VAR
           g_Dut_Point      : ARRAY[0..59] OF POINT_DATA_DUT;
           gi_SpeedOverride : INT;                (* DT216 전체 속도 배율 1..10 *)
           gi_1축AccDec ~ gi_5축AccDec : INT;
           gdi_1축PPR   ~ gdi_5축PPR   : DINT;
       END_VAR
     ※ 이전 버전에서 위 변수들이 이 FB 의 VAR_INPUT 으로 선언돼 있었다면
       FPWIN 변수 탭에서 제거하고 Global Variables 로 승격.
       두 FB 모두 글로벌을 직접 참조 → 인스턴스 코드 크기 감소.
--------------------------------------------------------------------------- *)

R_TRIG_Execute(CLK := b_Execute);

IF R_TRIG_Execute.Q THEN

    (* 초기화 *)
    b_Done := FALSE;
    b_Error := FALSE;
    i_ErrorID := 0;

    (* 1. 개수 제한 로직 (Safety Guard) *)
    (* 할당 정책상 최대 60개(idx 0..59)까지만 기록. 60~62 예비, 63 스크래치 *)
    IF i_WriteCount > 60 THEN
        i_RealCount := 60;
    ELSE
        i_RealCount := i_WriteCount;
    END_IF;

    (* 1-1. 전체속도 배율 클램프 (1~10) *)
    (* 0 또는 음수/범위초과 입력 시 안전값(10=100%)로 강제 *)
    IF gi_SpeedOverride < 1 OR gi_SpeedOverride > 10 THEN
        i_RealOverride := 10;
    ELSE
        i_RealOverride := gi_SpeedOverride;
    END_IF;
    
    (* 0개 이하면 실행 안 함 *)
    IF i_RealCount <= 0 THEN
        b_Done := TRUE;
        RETURN;
    END_IF;


    (* 2. 공통 테이블 데이터 설정 *)
    TableData.ControlCode := 16#0001; (* E point *)
    TableData.Pattern := 16#0000;     (* End *)
    TableData.dummy1 := 0;
    TableData.dummy2 := 0;
//    TableData.AccTime := 0;
//    TableData.DecTime := 0;
    TableData.AuxPoint := 0;
    TableData.DwellTime := 0;
    TableData.AuxOutput := 0;
    TableData.dummy3 := 0;
    TableData.dummy4 := 0;


    (* 3. 이중 반복문 실행 *)
    (* Outer Loop: 1축 ~ 5축 *)
    FOR i_LoopAxis := 1 TO 5 DO
        
        (* 뱅크 슬롯 계산 (축 변경) *)
        w_BankSlot := 16#6000 OR SHL(INT_TO_WORD(i_LoopAxis), 8);

        (* Inner Loop: 테이블 번호 (0 ~ RealCount-1) *)
        FOR i_LoopTable := 0 TO (i_RealCount - 1) DO

            (* 3-1. 축 번호에 따라 데이터 추출 *)
            (* i_LoopTable이 곧 DUT 배열의 인덱스가 됨 *)
            (* gdi_*축PPR = 서보 1회전당 지령펄스수 (DINT: 고해상도 인코더 대응) *)
            CASE i_LoopAxis OF
                1:
                    di_TargetPos := g_Dut_Point[i_LoopTable].diPosX;
                    i_TargetSpeed := g_Dut_Point[i_LoopTable].iSpeedX;
					i_AccDec := gi_1축AccDec;
					di_PPR := gdi_1축PPR;
                2:
                    di_TargetPos := g_Dut_Point[i_LoopTable].diPosY;
                    i_TargetSpeed := g_Dut_Point[i_LoopTable].iSpeedY;
					i_AccDec := gi_2축AccDec;
					di_PPR := gdi_2축PPR;
                3:
                    di_TargetPos := g_Dut_Point[i_LoopTable].diPosZ;
                    i_TargetSpeed := g_Dut_Point[i_LoopTable].iSpeedZ;
					i_AccDec := gi_3축AccDec;
					di_PPR := gdi_3축PPR;
                4:
                    di_TargetPos := g_Dut_Point[i_LoopTable].diPosY2;
                    i_TargetSpeed := g_Dut_Point[i_LoopTable].iSpeedY2;
					i_AccDec := gi_4축AccDec;
					di_PPR := gdi_4축PPR;
                5:
                    di_TargetPos := g_Dut_Point[i_LoopTable].diPosZ2;
                    i_TargetSpeed := g_Dut_Point[i_LoopTable].iSpeedZ2;
					i_AccDec := gi_5축AccDec;
					di_PPR := gdi_5축PPR;
            END_CASE;

            (* 3-2. 구조체 값 채우기 *)
            (* TargetSpeed 계산 — 속도% × 정격RPM 기반
                 정식 공식: TargetSpeed(pulses/sec) = (speed% × RatedRPM × PPR) / (100 × 60)
                                                  = (speed% × RatedRPM × PPR) / 6000

                 ※ TODO: 정격 RPM을 축별 VAR_INPUT(i_*축RatedRPM)으로 분리 필요.
                   현재는 전 축 정격 3000 RPM 고정.
                   RatedRPM=3000 대입 시: (speed% × 3000 × PPR) / 6000 = (speed% × PPR) / 2

                 검증: speed%=10, PPR=15000 → 10 × 15000 / 2 = 75,000 pulses/s
                                           → 75,000 × 60 / 15000 = 300 RPM (= 3000의 10%) ✓ *)
            TableData.TargetPosition := di_TargetPos;
            (* 전체속도 배율 적용: 원식(/2)에 (i_RealOverride/10) 곱 → 최종 /20 *)
            TableData.TargetSpeed := INT_TO_UDINT(i_TargetSpeed) * DINT_TO_UDINT(di_PPR) * INT_TO_UDINT(i_RealOverride) / 20;
			TableData.AccTime := i_AccDec;
			TableData.DecTime := i_AccDec;
            (* 3-3. 테이블 오프셋 계산 *)
            (* 10026번이 0번지. 테이블마다 16(10H)씩 증가 *)
            w_TableOffset := INT_TO_WORD(i_LoopTable * 16);

            (* 3-4. 하드웨어 쓰기 (F151) *)
            F151_WRT( 
                s1_BankSlot := w_BankSlot,
                s2_Start := Adr_Of_Var(TableData),
                n_Number := 16, 
                d_Start := w_TableOffset 
            );
            
        END_FOR; (* End of Table Loop *)
        
    END_FOR; (* End of Axis Loop *)

    b_Done := TRUE;

END_IF;

IF NOT b_Execute THEN
    b_Done := FALSE;
END_IF;