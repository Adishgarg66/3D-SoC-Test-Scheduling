#!/usr/bin/env python3
"""
capstone/scripts/connect_raspberry_pi.py
========================================
Utility to discover, deploy to, and connect with a Raspberry Pi (Pi 4 / 3 / Zero / 5)
over local network (TCP Socket or SSH) for Hardware-in-the-Loop (HIL) SoC test replay.

Examples:
  python capstone/scripts/connect_raspberry_pi.py --discover
  python capstone/scripts/connect_raspberry_pi.py --ping --host raspberrypi.local --transport ssh --user pi
  python capstone/scripts/connect_raspberry_pi.py --deploy --host 192.168.1.50 --user pi --start-server
  python capstone/scripts/connect_raspberry_pi.py --ping --host 192.168.1.50 --port 5055
"""

import argparse
import json
import os
import re
import socket
import subprocess
import sys
from typing import Dict, List, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from capstone.src.hardware.rpi_remote_bridge import RemoteRPiHILClient, SERVER_SCRIPT_PATH

# Known IEEE OUI prefixes assigned to Raspberry Pi Foundation / Trading Ltd
RPI_MAC_PREFIXES = (
    "b8:27:eb",
    "dc:a6:32",
    "e4:5f:01",
    "d8:3a:dd",
    "2c:cf:67",
)


def _check_tcp_port(ip: str, port: int, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def discover_raspberry_pis() -> List[Dict[str, object]]:
    """Probes mDNS hostnames and the local ARP table for Raspberry Pi boards."""
    candidates: Dict[str, Dict[str, object]] = {}

    # 1. Check mDNS hostnames
    for hostname in ("raspberrypi.local", "pi.local", "rpi.local"):
        try:
            ip = socket.gethostbyname(hostname)
            candidates[ip] = {
                "ip": ip,
                "hostname": hostname,
                "source": "mDNS",
                "mac": "unknown",
            }
        except socket.gaierror:
            pass

    # 2. Check ARP cache for Raspberry Pi MAC OUIs
    try:
        arp_out = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
        for line in arp_out.stdout.splitlines():
            ip_match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", line)
            mac_match = re.search(r"\bat\s+([0-9a-fA-F:]{11,17})", line)
            if not ip_match or not mac_match:
                continue
            ip = ip_match.group(1)
            # Normalize single-digit mac octets from macOS `arp -a` (e.g. b8:27:eb -> b8:27:eb)
            mac_parts = [p.zfill(2) for p in mac_match.group(1).lower().split(":")]
            mac = ":".join(mac_parts)
            if mac.startswith(RPI_MAC_PREFIXES):
                entry = candidates.setdefault(ip, {"ip": ip, "hostname": ip, "source": "ARP (RPi MAC OUI)"})
                entry["mac"] = mac
    except Exception:
        pass

    results = []
    for ip, info in candidates.items():
        info["ssh_port_22_open"] = _check_tcp_port(ip, 22)
        info["hil_port_5055_open"] = _check_tcp_port(ip, 5055)
        results.append(info)
    return results


def start_remote_tcp_server(client: RemoteRPiHILClient, port: int = 5055) -> None:
    """Starts rpi_hil_server.py in background on the remote Pi over SSH."""
    client.deploy_hil_server()
    remote_cmd = (
        f"nohup python3 {client.remote_script_path} --host 0.0.0.0 --port {port} "
        f"> ~/rpi_hil_server.log 2>&1 < /dev/null &"
    )
    subprocess.run(
        ["ssh", "-p", str(client.ssh_port), "-o", "ConnectTimeout=10", client.ssh_target, remote_cmd],
        check=True,
        timeout=15,
    )
    print(f"Started TCP HIL server on {client.ssh_target}:{port} (log: ~/rpi_hil_server.log)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover, deploy, and connect to Raspberry Pi HIL Tester")
    parser.add_argument("--discover", action="store_true", help="Scan mDNS & ARP cache for Raspberry Pi devices")
    parser.add_argument("--ping", action="store_true", help="Verify hardware connection & GPIO driver on Pi")
    parser.add_argument("--deploy", action="store_true", help="Upload rpi_hil_server.py to Pi over SCP")
    parser.add_argument("--start-server", action="store_true", help="Start background TCP HIL server on Pi (with --deploy)")
    parser.add_argument("--host", help="Raspberry Pi IP address or hostname (e.g. raspberrypi.local or 192.168.1.50)")
    parser.add_argument("--user", help="SSH username on Raspberry Pi (e.g. pi)")
    parser.add_argument("--port", type=int, default=5055, help="HIL TCP server port (default: 5055)")
    parser.add_argument("--ssh-port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument("--transport", choices=["tcp", "ssh"], default="tcp", help="Connection transport (default: tcp)")
    args = parser.parse_args()

    if args.discover or (not args.host and not args.ping and not args.deploy):
        print("Scanning local network for Raspberry Pi devices...")
        found = discover_raspberry_pis()
        if not found:
            print("No Raspberry Pi auto-detected via mDNS/ARP.")
            print("Tip: Find its IP on the Pi using `hostname -I`, then run:")
            print("  python3 capstone/scripts/connect_raspberry_pi.py --ping --host <RPI_IP> --user <USER> --transport ssh")
        else:
            print(json.dumps(found, indent=2))
        if not args.host:
            return

    if not args.host:
        parser.error("--host is required with --ping or --deploy")

    client = RemoteRPiHILClient(
        host=args.host,
        port=args.port,
        transport=args.transport,
        ssh_user=args.user,
        ssh_port=args.ssh_port,
    )

    if args.deploy:
        client.deploy_hil_server()
        if args.start_server:
            start_remote_tcp_server(client, port=args.port)

    if args.ping:
        resp = client.ping()
        print("\n=== Raspberry Pi Connection Verified ===")
        print(json.dumps(resp, indent=2))


if __name__ == "__main__":
    main()
