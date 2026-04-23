# PLC (Panasonic FP0H) 개발 노트

이 문서는 Pendant 프로젝트에서 사용하는 Panasonic FP0H PLC의 **벤더 특이 사항**과 **재사용 가능한 패턴**을 정리합니다. 코드에서 자명하지 않거나 매뉴얼을 다시 찾기 어려운 내용 위주로 기록합니다.

---

## TON 타이머 배열 (FP0H 전용 패턴)

표준 IEC `TON` 인스턴스는 FP0H에서 직접 ARRAY로 선언이 안 됩니다. 대신 **DUT(Data Unit Type) 인스턴스**를 ARRAY로 선언하고, `TON_FUN` 함수를 통해 호출하는 패턴을 사용합니다.

### 선언

```pascal
VAR
    at_ton : ARRAY[0..2] OF TON_FUN_INSTANCE_DUT;
END_VAR
```

### 호출

```pascal
TON_FUN(
    IN          := b_test,
    PT          := t#1s,
    dutInstance := at_ton[0],
    Q           => b_test1,
    ET          => t_test
);
```

### 핵심 포인트
- 배열 인덱스를 바꿔 가며 호출하면 **하나의 함수 호출로 여러 타이머를 다중 인스턴스화** 가능
- `dutInstance`에 ARRAY 요소를 전달하는 것이 핵심 — 각 요소가 독립된 타이머 상태를 보유
- 단일 FB에서 슬롯/컨텍스트별 타이머 처리에 활용 가능

### 활용 예 (콜 스택별 타이머)

```pascal
VAR
    at_StartWait : ARRAY[0..3] OF TON_FUN_INSTANCE_DUT;
    b_WaitDone   : BOOL;
    t_Elapsed    : TIME;
END_VAR

TON_FUN(
    IN          := b_TimerStart,
    PT          := t_WaitTime,
    dutInstance := at_StartWait[i_StackTop],
    Q           => b_WaitDone,
    ET          => t_Elapsed
);
```

---

## FB 인스턴스 코드 복제

FP0H는 **FB 인스턴스마다 코드가 컴파일 시점에 복제**됩니다. (LS XGB 등 코드 공유 PLC와 다름)

- `plc_fb.st` 본체 = 약 **3,475 PLC 스텝**
- 인스턴스 N개 사용 → **N × 3,475 스텝** 소비

→ **메모리 절감의 핵심은 인스턴스 수 줄이기 + FB 본체 줄이기**.

대안: ST `FUNCTION`은 인라인 확장될 가능성이 있어 절감 효과 보장 안 됨. 코드 공유가 필요하면 별도 FB 추출이 더 안전 (단, 인스턴스화 비용 발생).

---

## 메모리 맵 요약 (현재 프로젝트 기준)

| 영역 | 주소 | 용도 |
|---|---|---|
| 모니터링 (PLC→HMI) | DT100 ~ DT160 | 축위치, I/O, 상태, 알람 등 |
| 제어 명령 (HMI→PLC) | DT200 ~ DT215 | 운전 명령, 모드, 알람리셋 등 |
| 하트비트 | DT214 | 주기적 +1 |
| 축 설정 | DT15000 ~ DT15049 | 사용축 마스크 등 |
| 포인트 데이터 | DT16000 ~ DT19199 | 100개 × 32 워드 |
| 시퀀스 데이터 | DT20000 ~ DT59999 | 40 슬롯 × 1000 워드 (100스텝 × 10워드) |

상세는 `utils/plc_client.py:30-61` 참조.

---

## 시퀀스 스텝 명령어 코드

`plc_fb.st`에서 사용하는 `iCommand` 매핑 (`_convert_json_step_to_10words` 참조):

| Cmd | 명령 | 비고 |
|---|---|---|
| 10 | POS | 위치 이동, opt = 사용축 비트마스크 |
| 20 | OUT | 출력 제어, p2 = 출력 타입 (0:시스템 / 1:밸브 / 2:내부) |
| 21 | IN  | 입력 대기, p2 = 타임아웃, p3 = 동작 |
| 30 | TMR | 타이머, p3=0 단순 / p3=1 신호유지 |
| 40 | JMP | 점프, opt=0 무조건 / opt=1 조건부 |
| 50 | CALL | 서브시퀀스 호출, opt=0 동기 / opt=1 병렬 |
| 99 | END | 시퀀스 종료 |

---

## 에러 ID 매핑

`plc_fb.st` 헤더 주석 참조. 변경 시 HMI 알람 표시(`utils/languages.py` 등)와 동기화 필요.

| ID | 의미 |
|---|---|
| 21 | POS 축 이동 확인 실패 |
| 22 | 패킹 베이스 인덱스 범위 오류 (pack_base 스텝의 point_index 가 0~59 초과) |
| 50 | 서브 시퀀스 에러 |
| 93 | 병렬 CALL 실패 (서브 FB 실행중) |
| 94 | CALL 사용 불가 (이 인스턴스는 최하위) |
| 95 | JMP 타겟 스텝 범위 초과 |
| 96 | CALL 슬롯 번호 범위 초과 |
| 97 | 실행 슬롯 번호 범위 초과 |
| 98 | OUT 지연 타이머 슬롯 없음 |
| 99 | 알 수 없는 커맨드 |
