"""
WiFi 관리 유틸 — nmcli 래퍼

Raspberry Pi OS (NetworkManager) 기반. 실패 시 빈 결과를 반환하여 UI가 안전하게 처리.
"""
import subprocess
from typing import List, Dict, Optional


def _run(args: List[str], timeout: float = 10.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, capture_output=True, text=True, timeout=timeout, check=False
    )


def is_available() -> bool:
    try:
        return _run(["nmcli", "-v"], timeout=2).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_status() -> Dict[str, str]:
    """현재 WiFi 연결 상태 / IP 조회. 각 nmcli 호출 3초 타임아웃."""
    info = {"ssid": "", "ip": "", "signal": "", "iface": ""}
    try:
        r = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"], timeout=3)
        for line in r.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 4 and parts[1] == "wifi":
                info["iface"] = parts[0]
                if parts[2] == "connected":
                    info["ssid"] = parts[3]
                break

        if info["iface"]:
            r2 = _run(["nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", info["iface"]], timeout=3)
            for line in r2.stdout.strip().splitlines():
                if line.startswith("IP4.ADDRESS"):
                    val = line.split(":", 1)[1].split("/")[0]
                    info["ip"] = val
                    break

        if info["ssid"]:
            r3 = _run(["nmcli", "-t", "-f", "ACTIVE,SIGNAL,SSID", "device", "wifi", "list"], timeout=3)
            for line in r3.stdout.strip().splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and parts[0] == "yes":
                    info["signal"] = parts[1]
                    break
    except (subprocess.TimeoutExpired, Exception):
        pass
    return info


def scan(rescan: bool = True, timeout: float = 15.0) -> List[Dict[str, str]]:
    """주변 WiFi 스캔. [{ssid, signal, security, in_use}]"""
    try:
        if rescan:
            _run(["nmcli", "device", "wifi", "rescan"], timeout=8)
        r = _run(
            ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return []

    networks: Dict[str, Dict[str, str]] = {}
    for raw in r.stdout.splitlines():
        line = raw.replace(r"\:", "\x00")  # escape colons inside fields
        parts = [p.replace("\x00", ":") for p in line.split(":")]
        if len(parts) < 4:
            continue
        in_use, ssid, signal, security = parts[0], parts[1], parts[2], ":".join(parts[3:])
        if not ssid:
            continue
        # 가장 강한 신호만 유지
        prev = networks.get(ssid)
        try:
            sig_i = int(signal) if signal else 0
        except ValueError:
            sig_i = 0
        if prev is None or sig_i > int(prev["signal"] or 0):
            networks[ssid] = {
                "ssid": ssid,
                "signal": signal,
                "security": security,
                "in_use": "*" if in_use.strip() == "*" else "",
            }
    return sorted(networks.values(), key=lambda x: int(x["signal"] or 0), reverse=True)


def _delete_connection_profile(name: str) -> None:
    """동일 이름의 NM 연결 프로파일이 있으면 모두 삭제. (key-mgmt 누락 등 손상된 프로파일 방어)"""
    try:
        _run(["nmcli", "connection", "delete", "id", name], timeout=5)
    except subprocess.TimeoutExpired:
        pass


def connect(ssid: str, password: Optional[str] = None, timeout: float = 30.0) -> Dict[str, str]:
    """WiFi 접속. 성공 시 {'ok': '1'}, 실패 시 {'ok': '0', 'error': 메시지}"""
    # 비밀번호로 새로 접속할 때는 기존 프로파일을 정리해 NM 상태 손상(예: key-mgmt 누락) 회피
    if password:
        _delete_connection_profile(ssid)
    args = ["nmcli", "device", "wifi", "connect", ssid]
    if password:
        args += ["password", password]
    try:
        r = _run(args, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": "0", "error": "연결 시간 초과"}
    if r.returncode == 0:
        return {"ok": "1"}
    msg = (r.stderr or r.stdout or "알 수 없는 오류").strip()
    return {"ok": "0", "error": msg}


def connect_saved(ssid: str, timeout: float = 30.0) -> Dict[str, str]:
    """저장된 NM 프로파일로 재접속 시도. 비밀번호 없이 SSID 만으로."""
    try:
        r = _run(["nmcli", "connection", "up", "id", ssid], timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": "0", "error": "연결 시간 초과"}
    if r.returncode == 0:
        return {"ok": "1"}
    return {"ok": "0", "error": (r.stderr or r.stdout or "알 수 없는 오류").strip()}


def disconnect() -> Dict[str, str]:
    status = get_status()
    iface = status.get("iface") or "wlan0"
    try:
        r = _run(["nmcli", "device", "disconnect", iface], timeout=10)
    except subprocess.TimeoutExpired:
        return {"ok": "0", "error": "시간 초과"}
    if r.returncode == 0:
        return {"ok": "1"}
    return {"ok": "0", "error": (r.stderr or r.stdout).strip()}


# --- 유선 이더넷 ---------------------------------------------------------------

def _first_ethernet_device() -> str:
    try:
        r = _run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device"], timeout=3)
        for line in r.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[1] == "ethernet":
                return parts[0]
    except (subprocess.TimeoutExpired, Exception):
        pass
    return "eth0"


def _active_connection_for(iface: str) -> str:
    try:
        r = _run(["nmcli", "-t", "-f", "DEVICE,CONNECTION", "device"], timeout=3)
        for line in r.stdout.strip().splitlines():
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[0] == iface and parts[1] and parts[1] != "--":
                return parts[1]
    except (subprocess.TimeoutExpired, Exception):
        pass
    return ""


def _ethernet_profile(iface: str) -> str:
    """이더넷이 끊긴 상태에서도 조작할 연결 프로파일명을 결정.
    1) iface 에 현재 활성 연결이 있으면 그 이름.
    2) 없으면 interface-name 이 iface 로 고정된 저장 프로파일.
    3) 그래도 없으면 임의의 802-3-ethernet 저장 프로파일(이더넷 1개 가정).
    DHCP 미응답으로 device 가 disconnected 여도 setter 가 프로파일을
    찾아 고정IP/DHCP 를 적용할 수 있게 한다."""
    act = _active_connection_for(iface)
    if act:
        return act
    try:
        r = _run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"], timeout=3)
        eth_profiles = []
        for line in r.stdout.strip().splitlines():
            parts = line.rsplit(":", 1)
            if len(parts) == 2 and parts[1] == "802-3-ethernet":
                eth_profiles.append(parts[0])
        for name in eth_profiles:
            g = _run(["nmcli", "-g", "connection.interface-name",
                      "connection", "show", name], timeout=3)
            if g.stdout.strip() == iface:
                return name
        if eth_profiles:
            return eth_profiles[0]
    except (subprocess.TimeoutExpired, Exception):
        pass
    return ""


def get_ethernet_status() -> Dict[str, str]:
    """이더넷 상태 조회. 각 nmcli 호출 3초 타임아웃(UI 블로킹 방지)."""
    info = {
        "iface": _first_ethernet_device(),
        "state": "",
        "connection": "",
        "ip": "",
        "gateway": "",
        "method": "",
    }
    try:
        r = _run(["nmcli", "-t", "-f", "DEVICE,STATE,CONNECTION", "device"], timeout=3)
        for line in r.stdout.strip().splitlines():
            parts = line.split(":", 2)
            if len(parts) >= 2 and parts[0] == info["iface"]:
                info["state"] = parts[1]
                if len(parts) >= 3:
                    info["connection"] = parts[2] if parts[2] and parts[2] != "--" else ""
                break

        # 끊긴 상태(DHCP 미응답 등)면 활성 연결이 없으므로, iface 에 묶인
        # 저장 프로파일로 폴백 → UI 표시 및 DHCP/고정IP 버튼이 동작하도록.
        if not info["connection"]:
            info["connection"] = _ethernet_profile(info["iface"])

        r2 = _run(["nmcli", "-t", "-f", "IP4.ADDRESS,IP4.GATEWAY", "device", "show", info["iface"]], timeout=3)
        for line in r2.stdout.strip().splitlines():
            if line.startswith("IP4.ADDRESS"):
                info["ip"] = line.split(":", 1)[1].split("/")[0]
            elif line.startswith("IP4.GATEWAY"):
                info["gateway"] = line.split(":", 1)[1]

        if info["connection"]:
            r3 = _run(["nmcli", "-t", "-f", "ipv4.method", "connection", "show", info["connection"]], timeout=3)
            for line in r3.stdout.strip().splitlines():
                if line.startswith("ipv4.method"):
                    info["method"] = line.split(":", 1)[1]
                    break
    except (subprocess.TimeoutExpired, Exception):
        pass
    return info


def set_ethernet_dhcp() -> Dict[str, str]:
    info = get_ethernet_status()
    conn = info["connection"]
    iface = info["iface"]
    if not conn:
        return {"ok": "0", "error": "활성 이더넷 연결 프로파일을 찾지 못했습니다."}
    try:
        _run(["nmcli", "connection", "modify", conn,
              "ipv4.method", "auto",
              "ipv4.addresses", "",
              "ipv4.gateway", "",
              "ipv4.dns", ""], timeout=10)
        r = _run(["nmcli", "connection", "up", conn], timeout=20)
    except subprocess.TimeoutExpired:
        return {"ok": "0", "error": "시간 초과"}
    if r.returncode == 0:
        return {"ok": "1"}
    return {"ok": "0", "error": (r.stderr or r.stdout).strip()}


def set_ethernet_static(ip: str, prefix: int, gateway: str, dns: str = "") -> Dict[str, str]:
    info = get_ethernet_status()
    conn = info["connection"]
    if not conn:
        return {"ok": "0", "error": "활성 이더넷 연결 프로파일을 찾지 못했습니다."}
    args = ["nmcli", "connection", "modify", conn,
            "ipv4.method", "manual",
            "ipv4.addresses", f"{ip}/{prefix}",
            "ipv4.gateway", gateway,
            "ipv4.dns", dns]
    try:
        _run(args, timeout=10)
        r = _run(["nmcli", "connection", "up", conn], timeout=20)
    except subprocess.TimeoutExpired:
        return {"ok": "0", "error": "시간 초과"}
    if r.returncode == 0:
        return {"ok": "1"}
    return {"ok": "0", "error": (r.stderr or r.stdout).strip()}


# --- 인터넷 우선순위(유선/무선) -------------------------------------------------
# eth0(PLC망)·wlan0 가 같은 192.168.0.x 대역이면, 어느 인터페이스가 그 대역
# (인터넷 게이트웨이 포함)을 가져갈지는 ipv4.route-metric(낮을수록 우선)으로
# 결정된다. NM 기본값은 이더넷≈100 < WiFi=600 이라, eth0 가 올라오면 게이트웨이
# 까지 eth0(인터넷 없음)로 가버려 인터넷이 끊긴다. 아래 함수로 영구 조정.
_PRIO_HIGH = 100   # 우선(낮은 메트릭)
_PRIO_LOW = 700    # 비우선(WiFi 기본 600 보다 높게 두어 확실히 양보)


def _first_wifi_device() -> str:
    try:
        r = _run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device"], timeout=3)
        for line in r.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[1] == "wifi":
                return parts[0]
    except (subprocess.TimeoutExpired, Exception):
        pass
    return "wlan0"


def _wifi_profile(iface: str) -> str:
    act = _active_connection_for(iface)
    if act:
        return act
    try:
        r = _run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"], timeout=3)
        for line in r.stdout.strip().splitlines():
            parts = line.rsplit(":", 1)
            if len(parts) == 2 and parts[1] == "802-11-wireless":
                return parts[0]
    except (subprocess.TimeoutExpired, Exception):
        pass
    return ""


def _conn_field(conn: str, field: str) -> str:
    if not conn:
        return ""
    try:
        r = _run(["nmcli", "-g", field, "connection", "show", conn], timeout=3)
        return r.stdout.strip()
    except (subprocess.TimeoutExpired, Exception):
        return ""


def _device_state(iface: str) -> str:
    try:
        r = _run(["nmcli", "-t", "-f", "DEVICE,STATE", "device"], timeout=3)
        for line in r.stdout.strip().splitlines():
            p = line.split(":", 1)
            if len(p) == 2 and p[0] == iface:
                return p[1]
    except (subprocess.TimeoutExpired, Exception):
        pass
    return ""


def set_internet_priority(prefer: str, plc_ip: str = "") -> Dict[str, str]:
    """인터넷(공유 대역·기본 라우트) 우선 인터페이스 설정. 영구 저장.

    prefer="wifi": WiFi 가 대역/기본 라우트 우선. eth0 는 never-default 로
        인터넷을 절대 제공하지 않게 하고, plc_ip 가 주어지면 그 호스트(/32)
        만 eth0 로 강제 고정 → PLC 통신은 eth0, 인터넷은 WiFi 로 분리.
    prefer="eth": eth0 가 우선(메트릭↓). PLC 호스트 라우트는 제거.
    """
    eth_iface = _first_ethernet_device()
    wifi_iface = _first_wifi_device()
    eth_conn = _ethernet_profile(eth_iface)
    wifi_conn = _wifi_profile(wifi_iface)
    if not eth_conn:
        return {"ok": "0", "error": "이더넷 연결 프로파일을 찾지 못했습니다."}

    try:
        if prefer == "wifi":
            eth_args = ["nmcli", "connection", "modify", eth_conn,
                        "ipv4.route-metric", str(_PRIO_LOW),
                        "ipv4.never-default", "yes"]
            if plc_ip:
                eth_args += ["ipv4.routes", f"{plc_ip}/32"]
            else:
                eth_args += ["ipv4.routes", ""]
            _run(eth_args, timeout=10)
            if wifi_conn:
                _run(["nmcli", "connection", "modify", wifi_conn,
                      "ipv4.route-metric", str(_PRIO_HIGH),
                      "ipv4.never-default", "no"], timeout=10)
        elif prefer == "eth":
            _run(["nmcli", "connection", "modify", eth_conn,
                  "ipv4.route-metric", str(_PRIO_HIGH),
                  "ipv4.never-default", "no",
                  "ipv4.routes", ""], timeout=10)
            if wifi_conn:
                _run(["nmcli", "connection", "modify", wifi_conn,
                      "ipv4.route-metric", str(_PRIO_LOW),
                      "ipv4.never-default", "no"], timeout=10)
        else:
            return {"ok": "0", "error": f"알 수 없는 우선순위: {prefer}"}

        # 연결된 인터페이스에만 즉시 재적용(reapply 는 링크 유지·비차단).
        # eth0 가 DHCP 미응답으로 멈춰 있을 수 있어 connection up 은 피한다.
        for ifc, cn in ((wifi_iface, wifi_conn), (eth_iface, eth_conn)):
            if cn and _device_state(ifc) == "connected":
                _run(["nmcli", "device", "reapply", ifc], timeout=15)
    except subprocess.TimeoutExpired:
        return {"ok": "0", "error": "시간 초과"}
    return {"ok": "1"}


def get_internet_priority() -> str:
    """현재 우선순위 추정: eth0 가 never-default=yes 거나 메트릭이 WiFi 보다
    크면 'wifi', 아니면 'eth'. 미설정(기본)일 땐 NM 기본값 기준 'eth'."""
    eth_conn = _ethernet_profile(_first_ethernet_device())
    wifi_conn = _wifi_profile(_first_wifi_device())
    eth_nd = _conn_field(eth_conn, "ipv4.never-default")
    if eth_nd == "yes":
        return "wifi"

    def _m(v: str, default: int) -> int:
        try:
            n = int(v)
            return default if n < 0 else n
        except (ValueError, TypeError):
            return default

    em = _m(_conn_field(eth_conn, "ipv4.route-metric"), 100)
    wm = _m(_conn_field(wifi_conn, "ipv4.route-metric"), 600)
    return "wifi" if wm < em else "eth"
