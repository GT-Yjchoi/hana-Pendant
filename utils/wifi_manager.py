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
