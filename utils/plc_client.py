import socket
import struct
import threading
import time
from PySide6.QtCore import QObject, Signal

class PLCClient(QObject):
    sig_connected = Signal(bool)
    sig_monitor_data = Signal(dict)  # 모니터링 데이터 (PLC → HMI)
    sig_error = Signal(str)

    def __init__(self):
        super().__init__()
        self.sock = None
        self.is_connected = False
        self._monitor_running = False
        self.lock = threading.Lock()
        self._last_ip = None
        self._last_port = None
        self._reconnect_running = False

        # --- PLC 통신 설정 ---
        self.USE_HEADER = True      
        self.DEST_UNIT_NO = 0x01    
        
        # ===== 메모리 맵 =====

        # 1. 실시간 모니터링 블록 (PLC → HMI): DT100~
        self.MONITOR_ADDR  = 100
        self.MONITOR_COUNT = 61
        self.ADDR_SEQ_POPUP = 159   # DT159: 시퀀스 팝업 요청코드

        # 2. 제어 명령 블록 (HMI → PLC): DT200~
        self.ADDR_CTRL_CMD    = 200  # 운전 제어 명령
        self.ADDR_JOG_PRESS   = 201  # 조작압 선택
        self.ADDR_CHECK_RUN   = 202  # 확인운전 제어
        self.ADDR_VALVE_OUT   = 204  # 밸브 수동출력 (204~205, 2 Words)
        self.ADDR_JOG_CTRL    = 205  # 조그 제어
        self.ADDR_MODE        = 206  # 모드 설정 (206~208, 3 Words)
        self.ADDR_JOG_SPEED   = 211  # 조그 속도
        self.ADDR_ALARM_RESET = 212  # 알람 리셋
        self.ADDR_SOFT_ESTOP  = 213  # 소프트 비상정지 (0=정상, 1=비상정지)
        self.HEARTBEAT_ADDR   = 214  # 하트비트
        self.ADDR_JOG_MODE    = 215  # 수동조작 모드 선택 (0=앱솔루트기동, 1=JOG기동)
        self.heartbeat_value  = 0
        self._heartbeat_skip  = False

        # 3. 시퀀스 데이터 블록: DT20000~ (40슬롯 × 1000 = DT20000~DT59999)
        self.SEQ_BASE_ADDR = 20000
        self.SLOT_SIZE     = 1000   # 100스텝 × 10워드
        self.MAX_SLOTS     = 40

        # 4. 포인트 데이터 블록: DT16000~ (100개 × 32 = DT16000~DT19199)
        self.POINT_BASE_ADDR = 16000
        self.POINT_SIZE      = 32
        self.MAX_POINTS      = 100

        # 5. 축 설정 블록: DT15000~ (50 Words)
        self.AXIS_PARAM_ADDR   = 15000
        self.ADDR_AXIS_DATASET = self.AXIS_PARAM_ADDR + 33  # 데이터셋 트리거

    def connect_to_plc(self, ip, port):
        """PLC 연결"""
        self._last_ip = ip
        self._last_port = port
        try:
            print(f"[PLC] 연결 시도: {ip}:{port}")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10.0)  # 3초 → 10초로 증가 (대용량 전송 대응)
            self.sock.connect((ip, int(port)))
            self.is_connected = True
            self.sig_connected.emit(True)
            print("[PLC] 연결 성공!")
            self.start_monitoring()
            return True, "연결 성공"
        except Exception as e:
            self.is_connected = False
            self.sig_connected.emit(False)
            print(f"[PLC] 연결 실패: {e}")
            return False, f"연결 실패: {e}"

    def disconnect_plc(self):
        """PLC 연결 해제"""
        self._monitor_running = False
        self._reconnect_running = False
        self.is_connected = True  # 재연결 루프 while 조건(not is_connected) 즉시 탈출
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None
        self.is_connected = False
        self.sig_connected.emit(False)
        print("[PLC] 연결 해제")

    def _update_heartbeat(self):
        """
        하트비트 값을 +1 증가시키고 DT214에 전송
        - 0~100 범위를 순환
        - 100 다음에는 0으로 리셋
        - 무한루프 방지: _heartbeat_skip 플래그 사용
        """
        # 하트비트 값 증가
        self.heartbeat_value += 1
        if self.heartbeat_value > 100:
            self.heartbeat_value = 0
        
        # DT214에 하트비트 값 쓰기 (무한루프 방지)
        if not self._heartbeat_skip:
            self._heartbeat_skip = True  # 플래그 설정으로 재귀 방지
            try:
                # send_packet을 직접 호출하지 않고 저수준으로 전송
                body = struct.pack('<BBBHH', 0x80, 0x50, 0x09, self.HEARTBEAT_ADDR, 1)
                data_part = struct.pack('<H', self.heartbeat_value)
                self._send_packet_raw(body + data_part)
                # print(f"[하트비트] DT214 = {self.heartbeat_value}")  # 필요시 주석 해제
            except OSError:
                pass  # 하트비트 전송 실패는 무시
            finally:
                self._heartbeat_skip = False  # 플래그 해제

    def _send_packet_raw(self, body):
        """
        패킷 전송 (하트비트 전용, _update_heartbeat 호출 안함)
        """
        if not self.sock or not self.is_connected: 
            return None
        try:
            length = len(body)
            # LS PLC 프레임 헤더
            prefix = b'\x10\x00' + struct.pack('<H', length) + b'\x02\x00\x02\x00\x00\x00'
            suffix = bytes([0x01, self.DEST_UNIT_NO])
            packet = prefix + suffix + body
            
            self.sock.send(packet)
            response = self.sock.recv(4096)
            
            # 헤더 제거하고 데이터 반환
            if len(response) > 12: 
                return response[12:]
            return response
        except OSError:
            return None

    def send_packet(self, body):
        """패킷 전송 (헤더 포함)"""
        if not self.sock or not self.is_connected:
            return None
        with self.lock:
            try:
                length = len(body)
                # LS PLC 프레임 헤더
                prefix = b'\x10\x00' + struct.pack('<H', length) + b'\x02\x00\x02\x00\x00\x00'
                suffix = bytes([0x01, self.DEST_UNIT_NO])
                packet = prefix + suffix + body

                t_start = time.time()
                self.sock.send(packet)
                response = self.sock.recv(4096)
                elapsed = (time.time() - t_start) * 1000  # ms

                if elapsed > 30:
                    print(f"[PLC] [!] 응답 지연: {elapsed:.1f}ms")

                # ★ 통신 성공 시 하트비트 업데이트
                self._update_heartbeat()

                # 헤더 제거하고 데이터 반환
                if len(response) > 12:
                    return response[12:]
                return response
            except Exception as e:
                print(f"[PLC] 통신 에러: {e}")
                self.is_connected = False
                self.sig_connected.emit(False)
                self._start_reconnect()
                return None

    def read_words(self, area_code, start_addr, count):
        """Word 읽기"""
        body = struct.pack('<BBBHH', 0x80, 0x51, area_code, start_addr, count)
        resp = self.send_packet(body)
        if resp and len(resp) > 3:
            data = resp[3:]
            words = [struct.unpack('<H', data[i:i+2])[0] for i in range(0, len(data), 2)]
            return words
        return None

    def write_words(self, area_code, start_addr, values):
        """Word 쓰기"""
        if not isinstance(values, list):
            values = [values]
        
        # 값 검증
        clean_values = []
        for val in values:
            try:
                clean_values.append(int(val) & 0xFFFF)
            except (TypeError, ValueError):
                clean_values.append(0)
        
        header_part = struct.pack('<BBBHH', 0x80, 0x50, area_code, start_addr, len(clean_values))
        data_part = b''.join([struct.pack('<H', v) for v in clean_values])
        result = self.send_packet(header_part + data_part)
        
        if result:
            print(f"[PLC] O Write DT{start_addr} = {len(clean_values)} Words")
        else:
            print(f"[PLC] X Write FAILED DT{start_addr}")
        
        return result

    def write_bit(self, area_code, addr, bit_pos, on_off):
        """비트 쓰기"""
        curr = self.read_words(area_code, addr, 1)
        if not curr: return
        val = curr[0]
        if on_off: 
            val |= (1 << bit_pos)
        else:      
            val &= ~(1 << bit_pos)
        self.write_words(area_code, addr, [val])

    def write_dint(self, area_code, addr, value):
        """DINT(32비트) 쓰기"""
        v = int(value)
        low = v & 0xFFFF
        high = (v >> 16) & 0xFFFF
        self.write_words(area_code, addr, [low, high])

    def patch_tmr_step_time(self, slot_id, step_idx, time_sec):
        """TMR 스텝의 diParam1(시간값)만 PLC에 직접 패치 (슬롯 전체 재전송 없이)"""
        if not self.is_connected:
            return False
        if not (0 <= slot_id < self.MAX_SLOTS) or not (0 <= step_idx < 100):
            return False
        # Word 오프셋: 스텝당 10Words, diParam1 = +2~3
        addr = self.SEQ_BASE_ADDR + slot_id * self.SLOT_SIZE + step_idx * 10 + 2
        value = int(round(time_sec * 100))
        result = self.write_dint(0x09, addr, value)
        print(f"[PLC] TMR 패치 Slot={slot_id} Step={step_idx} DT{addr} = {value} ({time_sec}s)")
        return result

    # =========================================================
    # 제어 명령 (HMI → PLC) - DT200~208
    # =========================================================
    
    def send_control_command(self, mode):
        """
        DT200: 운전 제어 명령
        - 0: 정지
        - 1: 자동 (AUTO RUN)
        - 2: 확인운전 (CHECK RUN)
        """
        print(f"[PLC] 운전 제어 명령 → DT{self.ADDR_CTRL_CMD} = {mode}")
        return self.write_words(0x09, self.ADDR_CTRL_CMD, [mode])
    
    def send_jog_command(self, jog_value):
        """
        DT201: 조작 압 선택
        - 0: 제품압
        - 1: 티칭압
        """
        print(f"[PLC] 조작 압 선택 → DT{self.ADDR_JOG_PRESS} = {jog_value}")
        return self.write_words(0x09, self.ADDR_JOG_PRESS, [jog_value])
    
    def send_check_run_command(self, state):
        """
        DT202: 확인운전 제어
        - 확인운전 시작/중지 명령
        """
        print(f"[PLC] 확인운전 제어 → DT{self.ADDR_CHECK_RUN} = {state}")
        return self.write_words(0x09, self.ADDR_CHECK_RUN, [state])
    
    def write_jog_bits(self, bit_mask):
        """
        DT204~205: 밸브 수동 제어 (Bit 단위)
        - 32개 밸브를 Bit로 제어 (2 Words)
        """
        low = bit_mask & 0xFFFF
        high = (bit_mask >> 16) & 0xFFFF
        return self.write_words(0x09, self.ADDR_VALVE_OUT, [low, high])

    def write_jog_bit(self, bit_pos, is_on):
        """
        DT204~205: 특정 밸브 On/Off
        bit_pos: 0~31 (밸브 번호)
        """
        addr = self.ADDR_VALVE_OUT if bit_pos < 16 else self.ADDR_VALVE_OUT + 1
        bit_index = bit_pos % 16
        self.write_bit(0x09, addr, bit_index, is_on)
    
    def send_jog_control(self, jog_bit):
        """
        DT205: 조그 제어 명령 (Bit 단위)
        - 즉별 조그 이동 신호
        """
        return self.write_words(0x09, self.ADDR_JOG_CTRL, [jog_bit])
    
    def send_mode_settings(self, mode_data):
        """
        DT206~208: 모드 설정 변경 (3 Words = 40개 모드)
        mode_data: 길이 40의 boolean 리스트
        """
        if len(mode_data) < 40:
            mode_data = mode_data + [False] * (40 - len(mode_data))
        
        # 40개 모드를 3 Words로 압축
        words = [0, 0, 0]
        for i in range(40):
            word_idx = i // 16
            bit_idx = i % 16
            if mode_data[i]:
                words[word_idx] |= (1 << bit_idx)
        
        print(f"[PLC] 모드 설정 → DT{self.ADDR_MODE}~{self.ADDR_MODE+2} = {words}")
        return self.write_words(0x09, self.ADDR_MODE, words)

    def read_mode_settings(self):
        """
        DT206~208에서 현재 모드 설정 읽기
        반환: 길이 44의 boolean 리스트 (모드 0~43)
        """
        words = self.read_words(0x09, self.ADDR_MODE, 3)
        if not words or len(words) < 3:
            return None
        result = []
        for i in range(44):
            word_idx = i // 16
            bit_idx = i % 16
            result.append(bool(words[word_idx] & (1 << bit_idx)))
        return result

    def send_soft_estop(self, active):
        """
        DT213: 소프트 비상정지
        - True  / 1 : 비상정지 발동
        - False / 0 : 비상정지 해제
        """
        val = 1 if active else 0
        print(f"[PLC] 소프트 비상정지 → DT{self.ADDR_SOFT_ESTOP} = {val}")
        return self.write_words(0x09, self.ADDR_SOFT_ESTOP, [val])

    def send_jog_mode(self, mode):
        """
        DT215: 수동조작 모드 선택
        - 0: 앱솔루트기동 (위치결정 수동조작)
        - 1: JOG기동 (JOG 수동조작)
        """
        print(f"[PLC] 수동조작 모드 → DT{self.ADDR_JOG_MODE} = {mode} ({'JOG' if mode else 'ABS'})")
        return self.write_words(0x09, self.ADDR_JOG_MODE, [mode])

    # =========================================================
    # 모니터링 (PLC → HMI) - DT100~141
    # =========================================================
    
    def _start_reconnect(self):
        """자동 재연결 시작 (이미 실행 중이면 무시)"""
        if self._reconnect_running or not self._last_ip:
            return
        self._reconnect_running = True
        threading.Thread(target=self._reconnect_loop, daemon=True).start()

    def _reconnect_loop(self):
        """5초 간격으로 재연결 시도"""
        interval = 5
        while not self.is_connected:
            print(f"[PLC] {interval}초 후 재연결 시도... ({self._last_ip}:{self._last_port})")
            time.sleep(interval)
            if self.is_connected:
                break
            try:
                if self.sock:
                    try:
                        self.sock.close()
                    except OSError:
                        pass
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(5.0)
                self.sock.connect((self._last_ip, int(self._last_port)))
                self.is_connected = True
                self.sig_connected.emit(True)
                print("[PLC] 재연결 성공!")
                self.start_monitoring()
            except Exception as e:
                print(f"[PLC] 재연결 실패: {e}")
        self._reconnect_running = False

    def start_monitoring(self):
        """실시간 모니터링 시작"""
        if self._monitor_running:
            return
        self._monitor_running = True
        print("[PLC] 모니터링 시작 (DT100~DT140, 0.05초 주기)")
        threading.Thread(target=self._mon_loop, daemon=True).start()

    def _mon_loop(self):
        """모니터링 루프 (0.1초 주기)"""
        while self._monitor_running and self.is_connected:
            raw = self.read_words(0x09, self.MONITOR_ADDR, self.MONITOR_COUNT)

            if raw and len(raw) >= 40:  # 최소 40개 이상
                try:
                    res = self._parse_monitor_data(raw)
                    self.sig_monitor_data.emit(res)
                except Exception as e:
                    print(f"[PLC] 모니터링 파싱 에러: {e}")

            time.sleep(0.05)  # 50ms 주기
        self._monitor_running = False  # 루프 종료 시 플래그 리셋 (재연결 후 재시작 가능하도록)

    def _parse_monitor_data(self, raw):
        """
        모니터링 데이터 파싱
        raw: DT100~DT141의 Word 배열 (42개)
        """
        res = {}
        
        # ===== 1. 8축 현재 위치 (DT100~115) =====
        # DINT * 8 = 16 Words
        res['axis_pos'] = []
        for i in range(0, 16, 2):
            v = raw[i] | (raw[i+1] << 16)
            if v >= 0x80000000:  # 음수 처리
                v -= 0x100000000
            # 0.001mm 단위 → mm 변환
            res['axis_pos'].append(v / 1000.0)
        
        # ===== 2. 입력(X) 상태 (DT116~119) =====
        # WORD * 4 = X0~X3F (64점 모니터링)
        res['inputs'] = raw[16:20]  # DT116, 117, 118, 119
        
        # ===== 3. 출력(Y) 상태 (DT120~123) =====
        # WORD * 4 = Y0~Y3F (64점 모니터링)
        res['outputs'] = raw[20:24]  # DT120, 121, 122, 123
        
        # ===== 4. 밸브 동작 상태 (DT124~125) =====
        # WORD * 2 = 32개 밸브 On/Off
        res['valve_status'] = raw[24:26]  # DT124, 125
        
        # ===== 6. 현재 운전 상태 (DT129) =====
        # INT: 1=수동, 2=자동, 0=정지, 3=일정지(확인운전)
        res['op_status'] = raw[29]  # DT129
        
        # ===== 7. 확인운전 상태 (DT130) =====
        # INT: 현재 확인운전 진행 상태
        res['check_run_status'] = raw[30] if len(raw) > 30 else 0  # DT130
        
        # ===== 8. 현재 시퀀스 단계 (DT131) =====
        # INT: 현재 실행 중인 스텝 번호
        res['current_step'] = raw[31] if len(raw) > 31 else 0  # DT131
        
        # ===== 9. 총 취출 횟수 (DT132~133) =====
        # DINT: 완료된 사이클 수
        if len(raw) > 33:
            res['total_count'] = raw[32] | (raw[33] << 16)  # DT132-133
        else:
            res['total_count'] = 0
        
        # ===== 10. 현재 성형 시간 (DT134~135) =====
        # DINT: 사이클 타임 (0.1초 단위)
        if len(raw) > 35:
            v = raw[34] | (raw[35] << 16)
            res['mold_time'] = v / 10.0  # 0.1초 → 초 변환
        else:
            res['mold_time'] = 0.0
        
        # ===== 11. 현재 취출 시간 (DT136~137) =====
        # DINT: 로봇 동작 타임 (0.1초 단위)
        if len(raw) > 37:
            v = raw[36] | (raw[37] << 16)
            res['takeout_time'] = v / 10.0  # 0.1초 → 초 변환
        else:
            res['takeout_time'] = 0.0
        
        # ===== 12. 패킹 현재 횟수 (DT138~140) =====
        # INT * 3: X, Y, Z축 적재 카운트
        if len(raw) > 40:
            res['packing_counts'] = [raw[38], raw[39], raw[40]]  # DT138, 139, 140
        else:
            res['packing_counts'] = [0, 0, 0]
        
        # ===== 13. 축 알람 상태 (DT141) + 축별 에러코드 (DT143~DT158) =====
        # DT141: 비트0=1축, 비트1=2축, ... 비트7=8축
        # DT143~158: 축별 에러코드 (DINT, 2워드씩)
        res['axis_alarms'] = []
        res['axis_error_codes'] = [0] * 8  # 8축 에러코드
        if len(raw) > 41:
            alarm_word = raw[41]
            for i in range(8):
                if alarm_word & (1 << i):
                    res['axis_alarms'].append(i + 1)  # 축 번호 (1~8)
            if alarm_word & (1 << 8):  # 비상정지 (9번째 비트)
                res['axis_alarms'].append(9)
        for i in range(8):
            idx = 43 + i * 2  # DT143=index43, DT145=index45, ...
            if len(raw) > idx + 1:
                res['axis_error_codes'][i] = raw[idx] | (raw[idx + 1] << 16)

        # ===== 14. 시퀀스 팝업 요청 (DT159) =====
        # 0=없음, 1=입력대기 타임아웃 팝업
        res['seq_popup'] = raw[59] if len(raw) > 59 else 0

        # ===== 15. 작업자 응답 (DT160) =====
        # 0=대기, 1=계속, 2=정지
        res['popup_response'] = raw[60] if len(raw) > 60 else 0

        return res

    # =========================================================
    # 유틸리티
    # =========================================================
    
    def read_dint(self, area_code, addr):
        """DINT(32비트) 읽기"""
        words = self.read_words(area_code, addr, 2)
        if words and len(words) == 2:
            v = words[0] | (words[1] << 16)
            if v >= 0x80000000:
                v -= 0x100000000
            return v
        return 0
    
    # =========================================================
    # 시퀀스 데이터 전송 (HMI → PLC)
    # =========================================================
    
    def _split_32bit(self, value):
        """32비트 값을 Low/High Word로 분리"""
        v = int(value)
        if v < 0:
            v += 0x100000000
        low = v & 0xFFFF
        high = (v >> 16) & 0xFFFF
        return low, high
    
    def _convert_active_axes_to_word(self, active_axes):
        """
        사용축 배열을 1개 Word로 변환 (비트 패킹)
        
        active_axes: [True, False, True, ...] (8개 축)
        반환: 0x0000 ~ 0x00FF (비트 0~7)
        
        예시:
        - [True, False, False, ...] → 0x0001 (X축만)
        - [True, True, False, ...] → 0x0003 (X, Y축)
        - [True, True, True, ...] → 0x0007 (X, Y, Z축)
        """
        if not active_axes or not isinstance(active_axes, list):
            return 0x00FF  # 기본값: 전축 사용
        
        word_value = 0
        for i in range(min(8, len(active_axes))):
            if active_axes[i]:
                word_value |= (1 << i)
        
        return word_value
    
    def _convert_json_step_to_10words(self, step_data):
        """
        JSON 스텝 데이터를 10 Words로 변환
        
        step_data: {
            "type": "POS" | "OUT" | "IN" | "TMR" | "JMP" | "CALL" | "END",
            "active_axes": [True, True, False, ...],  # POS 스텝용
            ...
        }
        
        반환: [cmd, opt, p1_low, p1_high, p2_low, p2_high, p3_low, p3_high, p4_low, p4_high]
        """
        cmd, opt, p1, p2, p3, p4 = 0, 0, 0, 0, 0, 0
        step_type = step_data.get("type", "NOP")
        
        if step_type == "POS":
            cmd = 10
            p1 = int(step_data.get("point_index", 0))
            
            # ★ 사용축 비트를 opt에 저장
            active_axes = step_data.get("active_axes", [True] * 8)
            opt = self._convert_active_axes_to_word(active_axes)
            
            # 디버그 출력
            axes_str = "".join(["X" if active_axes[0] else "-",
                               "Y" if active_axes[1] else "-",
                               "Z" if active_axes[2] else "-",
                               "Y2" if active_axes[3] else "-",
                               "Z2" if active_axes[4] else "-",
                               "θ" if active_axes[5] else "-",
                               "R1" if active_axes[6] else "-",
                               "R2" if active_axes[7] else "-"])
            print(f"    → 사용축: {axes_str} (0x{opt:04X})")
            
        elif step_type == "OUT":
            cmd = 20
            on_value = step_data.get("on", step_data.get("on_off", False))
            opt = 1 if on_value else 0
            port = int(step_data.get("port", step_data.get("io_index", 0)))
            # out_type: 0=시스템출력(DT203), 1=밸브출력(DT204), 2=내부비트(DT300~301)
            out_type = int(step_data.get("out_type", 0))
            p1 = port
            p2 = out_type
            # p3: 딜레이 시간 (0=즉시, >0=타이머 기동후출력, 단위 0.01초)
            if step_data.get("delay_enable", False):
                delay_time = float(step_data.get("delay_time", 0.0))
                p3 = int(delay_time * 100)
            print(f"[DEBUG OUT] out_type={out_type}, bit={port}, on={on_value}, delay_p3={p3}")
            
        elif step_type == "IN":
            cmd = 21
            # ★ "on" 키 지원
            on_value = step_data.get("on", step_data.get("on_off", True))
            opt = 1 if on_value else 0
            # ★ "port" 키 지원
            port = int(step_data.get("port", step_data.get("io_index", 0)))
            
            print(f"[DEBUG IN] step_data: {step_data}")
            print(f"[DEBUG IN] port={port}, on={on_value}")
            
            # ★ 포트 종류별 처리
            if 200 <= port <= 215:
                p1 = port  # R입력 (DT126 비트, PLC FB에서 200~215로 판별)
                print(f"[DEBUG IN] R입력 R{port-200:02X} (DT126.{port-200}) → P1={p1}")
            elif 100 <= port <= 131:
                p1 = port  # 내부 비트
                print(f"[DEBUG IN] 내부비트 M{port-100:02d} → P1={p1}")
            else:
                p1 = port  # 시스템/밸브 입력 X
                print(f"[DEBUG IN] 입력 X{port:02X} → P1={p1}")
            
            # ★ P2: 타임아웃 (1초 = 100 단위, 미사용 시 0)
            timeout_enabled = step_data.get("timeout_enabled", True)
            timeout_sec = float(step_data.get("timeout", 5.0))
            p2 = int(timeout_sec * 100) if timeout_enabled else 0
            
            # ★ P3: 타임아웃 동작 (0:계속대기, 1:알람+정지, 2:알람+진행)
            action = step_data.get("timeout_action", "continue")
            if action == "ask":
                p3 = 1
            elif action == "alarm_go":
                p3 = 2
            else:  # "continue"
                p3 = 0

            # ★ P4: 알람 번호 (알람 동작일 때 사용)
            p4 = int(step_data.get("timeout_alarm_no", 1))

            print(f"[DEBUG IN] timeout={timeout_sec}s({p2}units), action={action}({p3}), alarm_no={p4}")
            
        elif step_type == "TMR":
            cmd = 30
            # 1초 = 100 단위 (page_timer와 동일 기준)
            if "time" in step_data:
                p1 = int(float(step_data["time"]) * 100)
            elif "value" in step_data:
                p1 = int(step_data["value"])
            else:
                p1 = 100

            if step_data.get("tmr_mode") == "hold":
                # 신호 유지 모드: p2=포트, p3=1(모드플래그), opt=ON(1)/OFF(0)
                p2 = int(step_data.get("port", 0))
                p3 = 1
                opt = 1 if step_data.get("on", True) else 0
                print(f"[DEBUG TMR-HOLD] port={p2}, on={bool(opt)}, hold_time={p1}")
            # else: 단순 대기 - p2=p3=0, opt=0 그대로
                
        elif step_type == "JMP":
            cmd = 40

            is_conditional = step_data.get("condition", False)

            if is_conditional:
                # 조건부 점프 (opt=1)
                opt = 1
                p1 = int(step_data.get("target_step", 0))

                cond_type = step_data.get("cond_type", "PORT")
                if cond_type == "MODE":
                    p2 = 1
                elif cond_type == "STATE":
                    p2 = 2
                else:
                    p2 = 0
                p3 = int(step_data.get("cond_value", 0))
                p4 = 1 if step_data.get("cond_on", True) else 0

                print(f"[DEBUG JMP 조건부] target={p1}, type={cond_type}({p2}), value={p3}, on={p4}")

            else:
                # 무조건 점프 (opt=0)
                opt = 0
                p1 = int(step_data.get("target_step", 0))
                print(f"[DEBUG JMP 무조건] target={p1}")
            
        elif step_type == "CALL":
            cmd = 50
            p1 = int(step_data.get("sequence_id", 0))
            
            # ★ 실행 모드: 0=대기, 1=동시실행
            is_parallel = step_data.get("parallel", False)
            opt = 1 if is_parallel else 0
            
            print(f"[DEBUG CALL] seq_id={p1}, parallel={is_parallel}({opt})")
            
        elif step_type == "END":
            cmd = 99
        
        # 32비트 값을 Low/High Word로 분리
        p1_l, p1_h = self._split_32bit(p1)
        p2_l, p2_h = self._split_32bit(p2)
        p3_l, p3_h = self._split_32bit(p3)
        p4_l, p4_h = self._split_32bit(p4)
        
        return [cmd, opt, p1_l, p1_h, p2_l, p2_h, p3_l, p3_h, p4_l, p4_h]
    
    def send_sequence_to_slot(self, slot_id, json_steps):
        """
        시퀀스 데이터를 PLC 슬롯에 전송 (분할 전송)
        
        slot_id: 0~39 (0=Main, 1~39=서브 시퀀스)
        json_steps: 스텝 딕셔너리 리스트
        
        반환: True=성공, False=실패
        """
        if not (0 <= slot_id < self.MAX_SLOTS):
            print(f"[PLC] X 잘못된 슬롯 번호: {slot_id}")
            return False
        
        # ★ 자동으로 END 스텝 추가 (마지막에 END가 없으면)
        steps_with_end = list(json_steps)  # 복사
        if not steps_with_end or steps_with_end[-1].get("type") != "END":
            steps_with_end.append({"type": "END", "name": "시퀀스 종료"})
            print(f"[PLC] i  END 스텝 자동 추가됨")
        
        print(f"[PLC] → Slot {slot_id} 시퀀스 변환 시작 ({len(steps_with_end)}개 스텝)")
        
        # JSON 스텝을 10 Words씩 변환
        flat_data = []
        for idx, step in enumerate(steps_with_end):
            try:
                words = self._convert_json_step_to_10words(step)
                flat_data.extend(words)
                print(f"  Step {idx}: {step.get('type', 'NOP')} → CMD={words[0]}, OPT=0x{words[1]:04X}, P1={words[2]|words[3]<<16}")
            except Exception as e:
                print(f"  X Step {idx} 변환 실패: {e}")
                flat_data.extend([0] * 10)
        
        # 100개 스텝 = 1000 Words로 패딩
        total_len = 100 * 10
        if len(flat_data) < total_len:
            flat_data.extend([0] * (total_len - len(flat_data)))

        # ★★★ 한 번에 전송 (1000 Words = 1000 Words 제한, 분할 전송) ★★★
        addr = self.SEQ_BASE_ADDR + (slot_id * self.SLOT_SIZE)
        print(f"[PLC] → DT{addr}에 {len(flat_data)} Words 전송 중...")
        
        result = self.write_words(0x09, addr, flat_data)
        
        if result:
            print(f"[PLC] O Slot {slot_id} 전송 성공")
            return True
        else:
            print(f"[PLC] X Slot {slot_id} 전송 실패")
            return False
    
    def send_all_points(self, points_dict, ordered_names):
        """
        모든 포인트 데이터를 PLC에 전송 (분할 전송)
        
        points_dict: {"Point_1": {"coords": [...], "speeds": [...]}, ...}
        ordered_names: ["Point_1", "Point_2", ...]
        
        반환: True=성공, False=실패
        """
        print(f"[PLC] → 포인트 테이블 전송 시작 ({len(ordered_names)}개 포인트)")
        
        # 100개 포인트 × 32 Words = 3200 Words 버퍼 생성
        total_buffer = [0] * (self.MAX_POINTS * self.POINT_SIZE)
        
        for i, name in enumerate(ordered_names):
            if i >= self.MAX_POINTS:
                print(f"  [!] 최대 포인트 수({self.MAX_POINTS}) 초과, {name} 스킵")
                break
            
            if name not in points_dict:
                print(f"  [!] 포인트 '{name}' 데이터 없음")
                continue
            
            try:
                p_data = points_dict[name]
                coords = p_data.get("coords", [0.0] * 8)
                speeds = p_data.get("speeds", [100.0] * 8)
                
                # 포인트 데이터 생성 (32 Words)
                chunk = [0] * self.POINT_SIZE
                chunk[0] = 0xFF      # 유효 플래그
                chunk[1] = 100       # 전체 속도
                
                # 8축 좌표 (0.001mm 단위로 변환)
                for axis in range(8):
                    val_int = int(float(coords[axis]) * 1000)
                    low, high = self._split_32bit(val_int)
                    chunk[2 + axis*2] = low
                    chunk[3 + axis*2] = high
                
                # 8축 속도 (%)
                for axis in range(8):
                    chunk[18 + axis] = int(float(speeds[axis]))
                
                # 버퍼에 복사
                start_idx = i * self.POINT_SIZE
                total_buffer[start_idx : start_idx + self.POINT_SIZE] = chunk
                
                print(f"  Point {i}: {name} → X={coords[0]:.3f}, Y={coords[1]:.3f}")
                
            except Exception as e:
                print(f"  X 포인트 '{name}' 변환 실패: {e}")
        
        # ★★★ 분할 전송 (500 Words = 1000 Bytes씩, 안정성 우선) ★★★
        print(f"[PLC] → DT{self.POINT_BASE_ADDR}에 분할 전송 중...")
        chunk_size = 500  # 500 Words씩 전송 (안정성 확보)
        total_chunks = (len(total_buffer) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(total_buffer), chunk_size):
            chunk_num = i // chunk_size + 1
            chunk = total_buffer[i:i+chunk_size]
            addr = self.POINT_BASE_ADDR + i
            
            print(f"  → Chunk {chunk_num}/{total_chunks}: DT{addr} ({len(chunk)} Words)")
            result = self.write_words(0x09, addr, chunk)
            
            if not result:
                print(f"[PLC] X 포인트 Chunk {chunk_num}/{total_chunks} 전송 실패 (DT{addr})")
                return False
            
            # 진행 상황 표시
            progress = (chunk_num * 100) // total_chunks
            print(f"  O 완료: {progress}%")
            
            # 짧은 대기 (안정성)
            time.sleep(0.05)  # 50ms (여유 확보)
        
        print(f"[PLC] O 포인트 테이블 전송 성공 ({total_chunks}개 청크)")
        return True
