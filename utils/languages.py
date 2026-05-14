from PySide6.QtCore import QObject, Signal

# ========================================================
# [언어 데이터 사전]
# ========================================================
TRANSLATIONS = {
    # --- 네비게이션 ---
    "nav_manual":   {"KR": "수동운전", "EN": "MANUAL"},
    "nav_auto":     {"KR": "자동운전", "EN": "AUTO"},
    "nav_mode":     {"KR": "모드",     "EN": "MODE"},
    "nav_pos":      {"KR": "위치설정", "EN": "POSITION"},
    "nav_timer":    {"KR": "타이머",   "EN": "TIMER"},
    "nav_packing":  {"KR": "패킹",     "EN": "PACKING"},
    "nav_data":     {"KR": "데이터",     "EN": "DATA"},
    "nav_setting":  {"KR": "설정",     "EN": "SETTING"},

    # --- 상단바 ---
    "lbl_mode":     {"KR": "모드: ",   "EN": "MODE: "},
    "lbl_comm":     {"KR": "통신: ",   "EN": "COMM: "},
    "lbl_alarm":    {"KR": "알람: ",   "EN": "ALARM: "},
    "lbl_mold":     {"KR": "데이터: ",  "EN": "DATA: "},

    # --- 공통 버튼 (예/아니오) ---
    "btn_yes":      {"KR": "예 (Yes)",   "EN": "Yes"},
    "btn_no":       {"KR": "아니오 (No)", "EN": "No"},
    "btn_confirm":  {"KR": "확인",       "EN": "OK"},

    # ========================================================
    # [금형 데이터 관리 (PageData) 관련 텍스트] - START
    # ========================================================
    "data_title":          {"KR": "금형 데이터 관리", "EN": "Mold Data Management"},
    "data_list_header":    {"KR": " 저장된 파일 목록", "EN": " Saved File List"},
    "data_preview_header": {"KR": "[X] 데이터 미리보기 (Step Preview)", "EN": "[X] Step Preview"},
    "data_info_default":   {"KR": "파일을 선택하면 상세 정보가 표시됩니다.", "EN": "Select a file to view details."},
    "data_info_empty":     {"KR": "i 저장된 동작 데이터가 없습니다.", "EN": "i No sequence data saved."},
    
    # 버튼
    "btn_load_file":       {"KR": "불러오기\n(LOAD)", "EN": "LOAD\n(FILE)"},
    "btn_new_file":        {"KR": "새로만들기\n(NEW)", "EN": "NEW\n(CREATE)"},
    "btn_save_file":       {"KR": "저장\n(SAVE)",     "EN": "SAVE\n(FILE)"},
    "btn_del_file":        {"KR": "파일 삭제\n(DELETE)", "EN": "DELETE\n(FILE)"},

    # 팝업 제목
    "title_notice":        {"KR": "알림", "EN": "Notice"},
    "title_error":         {"KR": "오류", "EN": "Error"},
    "title_done":          {"KR": "완료", "EN": "Done"},
    "title_new":           {"KR": "새로 만들기 안내", "EN": "Create New Data"},
    "title_save":          {"KR": "저장 확인", "EN": "Save Confirmation"},
    "title_load":          {"KR": "불러오기 확인", "EN": "Load Confirmation"},
    "title_del":           {"KR": "삭제 확인", "EN": "Delete Confirmation"},
    "title_dup":           {"KR": "중복 확인", "EN": "Duplicate Warning"},

    # 팝업 메시지
    "msg_new_confirm":     {"KR": "현재 설정되어 있는 조건을 기준으로\n데이터를 새로 만듭니다.\n\n계속하시겠습니까?", 
                            "EN": "Create new data based on current settings.\n\nDo you want to continue?"},
    "msg_no_save_target":  {"KR": "저장할 대상 파일이 없습니다.\n먼저 파일을 불러오거나 새로 만들어주세요.", 
                            "EN": "No target file to save.\nPlease load or create a file first."},
    "msg_save_confirm":    {"KR": "현재 로딩되어있는 [{0}] 에 저장됩니다.", "EN": "Overwrite to [{0}]?"},
    "msg_save_done":       {"KR": "저장되었습니다.", "EN": "Saved successfully."},
    "msg_no_sel_load":     {"KR": "불러올 파일을 목록에서 먼저 선택해주세요.", "EN": "Please select a file to load."},
    "msg_load_confirm":    {"KR": "현재 데이터가 사라집니다.\n'{0}' 파일을 불러오시겠습니까?", 
                            "EN": "Current data will be lost.\nLoad '{0}'?"},
    "msg_load_done":       {"KR": "데이터를 불러왔습니다.", "EN": "Data loaded successfully."},
    "msg_no_sel_del":      {"KR": "삭제할 파일을 목록에서 먼저 선택해주세요.", "EN": "Please select a file to delete."},
    "msg_del_confirm":     {"KR": "정말로 '{0}' 파일을 삭제하시겠습니까?", "EN": "Are you sure you want to delete '{0}'?"},
    "msg_del_done":        {"KR": "파일이 삭제되었습니다.", "EN": "File deleted."},
    "msg_dup_confirm":     {"KR": "'{0}' 파일이 이미 존재합니다.\n덮어쓰시겠습니까?", "EN": "File '{0}' already exists.\nOverwrite?"},
    # ========================================================
    # [금형 데이터 관리 (PageData) 관련 텍스트] - END
    # ========================================================

    # --- 패킹 화면 ---
    "pack_title":   {"KR": "패킹(팔레타이징) 설정", "EN": "Packing (Palletizing) Setup"},
    "sim_title":    {"KR": " 적재 시뮬레이션 (Simulation)", "EN": " Stacking Simulation"},
    "sim_mc":       {"KR": " Injection MC (사출기)", "EN": " Injection MC"},
    "sim_head":     {"KR": "HEAD", "EN": "HEAD"},
    "z_level":      {"KR": "Z",     "EN": "Z"},
    "btn_x_first":    {"KR": "순서: X → Y → Z (행 우선)", "EN": "Order: X → Y → Z (Row)"},
    "btn_y_first":    {"KR": "순서: Y → X → Z (열 우선)", "EN": "Order: Y → X → Z (Col)"},
    "btn_z_first_x":  {"KR": "순서: Z → X → Y (기둥-행)", "EN": "Order: Z → X → Y (Stack-Row)"},
    "btn_z_first_y":  {"KR": "순서: Z → Y → X (기둥-열)", "EN": "Order: Z → Y → X (Stack-Col)"},
    "btn_play":     {"KR": "▶ 시뮬레이션 재생", "EN": "▶ Play Simulation"},
    "btn_stop":     {"KR": "■ 정지 (Stop)",    "EN": "■ Stop"},
    "axis_set":     {"KR": " 축 설정", "EN": "-Axis Set"},
    "curr_pos":     {"KR": "현재위치(No.)", "EN": "Current(No.)"},
    "set_cnt":      {"KR": "설정횟수(EA)", "EN": "Count(EA)"},
    "set_pitch":    {"KR": "설정피치(mm)", "EN": "Pitch(mm)"},
    "dir_label":    {"KR": "진행 방향", "EN": "Direction"},
    "dir_pos":      {"KR": "+ 방향 (정방향)", "EN": "+ Dir (Forward)"},
    "dir_neg":      {"KR": "- 방향 (역방향)", "EN": "- Dir (Reverse)"},

    # --- 설정 화면 ---
    "settings_title": {"KR": "시스템 설정", "EN": "System Settings"},
    "sec_general":    {"KR": "일반 설정 (General)", "EN": "General Settings"},
    "sec_hardware":   {"KR": "하드웨어 제어 (Hardware)", "EN": "Hardware Control"},
    "lang_label":     {"KR": "언어 (Language):", "EN": "Language:"},

    # --- 타이머 화면 ---
    "timer_popup_title":   {"KR": "타이머 설정", "EN": "Timer Settings"},
    "timer_name_label":    {"KR": "타이머 명칭", "EN": "Timer Name"},
    "timer_value_label":   {"KR": "설정 시간 (초)", "EN": "Set Time (sec)"},
    "timer_no_data":       {
        "KR": "설정된 타이머 스텝이 없습니다.\n'위치설정' 메뉴의 시퀀스 편집에서 타이머를 추가하세요.", 
        "EN": "No timer steps found.\nPlease add a timer in the Sequence Editor."
    },
    "btn_cancel":          {"KR": "취소", "EN": "Cancel"},
    "btn_save":            {"KR": "저장", "EN": "Save"},

    # --- 수동 운전 ---
    "manual_title": {"KR": "수동운전", "EN": "MANUAL CONTROL"},
    "pos_title":    {"KR": "현재 위치", "EN": "Current Position"},
    "arm_title":    {"KR": "암 선택", "EN": "Arm Selection"},
    "btn_prod_arm": {"KR": "제품암 조작", "EN": "Product Arm"},
    "btn_runner_arm": {"KR": "런너암 조작", "EN": "Runner Arm"},
    "valve_title":  {"KR": "밸브조작", "EN": "Valve Control"},
    "io_title":     {"KR": "I/O 모니터", "EN": "I/O Monitor"},
    "lbl_io_input":  {"KR": "입력 신호 (INPUT)", "EN": "INPUT SIGNAL"},
    "lbl_io_output": {"KR": "출력 신호 (OUTPUT)", "EN": "OUTPUT SIGNAL"},

    "v_chuck_1":    {"KR": "척 1", "EN": "Chuck 1"},
    "v_chuck_2":    {"KR": "척 2", "EN": "Chuck 2"},
    "v_chuck_3":    {"KR": "척 3", "EN": "Chuck 3"},
    "v_chuck_4":    {"KR": "척 4", "EN": "Chuck 4"},
    "v_vac_1":      {"KR": "흡착 1", "EN": "Vac 1"},
    "v_vac_2":      {"KR": "흡착 2", "EN": "Vac 2"},
    "v_vac_3":      {"KR": "흡착 3", "EN": "Vac 3"},
    "v_vac_4":      {"KR": "흡착 4", "EN": "Vac 4"},
    "v_posture_inv":{"KR": "포스쳐 반전", "EN": "Pos. Invert"},
    "v_posture_ret":{"KR": "포스쳐 복귀", "EN": "Pos. Return"},
    "v_swivel_rot": {"KR": "스위블 회전", "EN": "Swivel Rot"},
    "v_swivel_ret": {"KR": "스위블 복귀", "EN": "Swivel Ret"},
    "v_nip_1":      {"KR": "니퍼 컷팅 1", "EN": "Nipper 1"},
    "v_nip_2":      {"KR": "니퍼 컷팅 2", "EN": "Nipper 2"},
    "v_cv_out":     {"KR": "컨베이어 출력", "EN": "Conv. Out"},
    "v_feeder":     {"KR": "공급기 출력", "EN": "Feeder Out"},

    # --- 자동 운전 ---
    "auto_title":      {"KR": "자동운전", "EN": "AUTO RUN"},
    "auto_ctrl_title": {"KR": "자동 제어", "EN": "AUTO CONTROL"},
    "info_title":      {"KR": "운전 정보", "EN": "OPERATION INFO"},
    "lbl_extract_cnt": {"KR": "포장횟수", "EN": "Pack Cnt"},
    "lbl_mold_time":   {"KR": "포장시간", "EN": "Pack Time"},
    "btn_auto_run":    {"KR": "자동운전", "EN": "AUTO"},
    "btn_check_run":   {"KR": "확인운전", "EN": "CHECK"},
    "btn_stop":        {"KR": "정지",     "EN": "STOP"},
    "btn_start":       {"KR": "시작",     "EN": "START"},
    "btn_pause":       {"KR": "일시정지", "EN": "PAUSE"},
    "btn_resume":      {"KR": "재개",     "EN": "RESUME"},

    # --- 기본 모드 ---
    "mode_title":          {"KR": "동작모드", "EN": "Operation Mode"},
    
    "mode_prod_takeout":   {"KR": "제품측 취출", "EN": "Product Takeout"},
    "mode_runner_takeout": {"KR": "런너측 취출", "EN": "Runner Takeout"},
    "mode_wait_move":      {"KR": "주행 대기",   "EN": "Wait (Traverse)"},
    "mode_wait_down":      {"KR": "하강 대기",   "EN": "Wait (Descent)"},
    "mode_open_move":      {"KR": "주행도중개방", "EN": "Open during Move"},
    "mode_open_ret":       {"KR": "복귀도중개방", "EN": "Open during Return"},
    "mode_safety_1":       {"KR": "안전도어 회피", "EN": "Safety Door 1"},
    "mode_safety_2":       {"KR": "안전도어 회피2", "EN": "Safety Door 2"},
    "mode_inv_drop":       {"KR": "낙하측 반전", "EN": "Invert (Release)"},
    "mode_inv_move":       {"KR": "주행도중 반전", "EN": "Invert (Move)"},
    "mode_inv_wait":       {"KR": "취출대기 반전", "EN": "Invert (Wait)"},
    "mode_fix_side":       {"KR": "고정측 취출", "EN": "Fixed Side Ext."},
    "mode_open_prod":      {"KR": "제품 형내개방", "EN": "Mold Open (Prod)"},
    "mode_open_run":       {"KR": "런너 형내개방", "EN": "Mold Open (Run)"},
    "mode_eject_link":     {"KR": "에젝터 연동",   "EN": "Ejector Link"},
    "mode_undercut":       {"KR": "언더컷 취출모드", "EN": "Undercut Mode"},
    "mode_chuck1_use":     {"KR": "척1 사용", "EN": "Use Chuck 1"},
    "mode_chuck1_sens":    {"KR": "척1 감지", "EN": "Chuck 1 Sensor"},
    "mode_chuck2_use":     {"KR": "척2 사용", "EN": "Use Chuck 2"},
    "mode_chuck2_sens":    {"KR": "척2 감지", "EN": "Chuck 2 Sensor"},
    "mode_chuck3_use":     {"KR": "척3 사용", "EN": "Use Chuck 3"},
    "mode_chuck3_sens":    {"KR": "척3 감지", "EN": "Chuck 3 Sensor"},
    "mode_chuck4_use":     {"KR": "척4 사용", "EN": "Use Chuck 4"},
    "mode_chuck4_sens":    {"KR": "척4 감지", "EN": "Chuck 4 Sensor"},
    "mode_vac1_use":       {"KR": "흡착1 사용", "EN": "Use Vacuum 1"},
    "mode_vac1_sens":      {"KR": "흡착1 감지", "EN": "Vac 1 Sensor"},
    "mode_vac2_use":       {"KR": "흡착2 사용", "EN": "Use Vacuum 2"},
    "mode_vac2_sens":      {"KR": "흡착2 감지", "EN": "Vac 2 Sensor"},
    "mode_vac3_use":       {"KR": "흡착3 사용", "EN": "Use Vacuum 3"},
    "mode_vac3_sens":      {"KR": "흡착3 감지", "EN": "Vac 3 Sensor"},
    "mode_vac4_use":       {"KR": "흡착4 사용", "EN": "Use Vacuum 4"},
    "mode_vac4_sens":      {"KR": "흡착4 감지", "EN": "Vac 4 Sensor"},
    "mode_2point_open":    {"KR": "2포인트 개방", "EN": "2-Point Open"},
    "mode_process_mon":    {"KR": "공정감시 모드", "EN": "Process Monitor"},
}

class LanguageManager(QObject):
    sig_lang_changed = Signal(str)
    _instance = None

    def __init__(self):
        super().__init__()
        self.current_lang = "KR"

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_language(self, lang_code):
        if lang_code not in ["KR", "EN"]: return
        self.current_lang = lang_code
        self.sig_lang_changed.emit(lang_code)

    def get_text(self, key):
        data = TRANSLATIONS.get(key, {})
        return data.get(self.current_lang, key)