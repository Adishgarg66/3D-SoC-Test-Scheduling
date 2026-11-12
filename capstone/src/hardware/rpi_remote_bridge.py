"""
capstone/src/hardware/rpi_remote_bridge.py
==========================================
Unified Remote & Local Hardware-in-the-Loop (HIL) Bridge for Raspberry Pi (Pi 4 / 3 / Zero / 5).

Enables connecting a Mac/PC running the SoC test scheduler directly to a Raspberry Pi over:
1. Direct TCP Socket (connecting to `rpi_hil_server.py` running on the Pi, default port 5055)
2. SSH One-Shot / Auto-Deploy (`ssh`/`scp` executing GPIO waveforms cleanly over stdin/stdout)
3. Local Physical GPIO (when executed directly on the Raspberry Pi)
4. Calibrated Mock Fallback (when running offline without physical hardware)
"""

import json
import logging
import os
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional

from capstone.src.hardware.rpi_hil_server import (
    DEFAULT_CLOCK_PIN,
    DEFAULT_TAM_PINS,
    GPIOBackend,
    execute_replay,
    serialize_schedule,
)

SERVER_SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "rpi_hil_server.py"))


class RemoteRPiHILClient:
    """Client for executing 2D and 3D SoC test schedules on a remote Raspberry Pi."""

    def __init__(
        self,
        host: str,
        port: int = 5055,
        transport: str = "tcp",
        ssh_user: Optional[str] = None,
        ssh_port: int = 22,
        timeout: float = 60.0,
        remote_script_path: str = "~/rpi_hil_server.py",
        auto_deploy: bool = True,
    ):
        # Allow passing "user@host" seamlessly
        if "@" in host and not ssh_user:
            ssh_user, host = host.split("@", 1)

        self.host = host.strip()
        self.port = int(port)
        self.transport = transport.lower()
        self.ssh_user = ssh_user.strip() if ssh_user else None
        self.ssh_port = int(ssh_port)
        self.timeout = float(timeout)
        self.remote_script_path = remote_script_path
        self.auto_deploy = auto_deploy

        if self.transport not in ("tcp", "ssh"):
            raise ValueError(f"Unsupported transport '{self.transport}'. Use 'tcp' or 'ssh'.")

    @property
    def ssh_target(self) -> str:
        return f"{self.ssh_user}@{self.host}" if self.ssh_user else self.host

    def _exchange_on_socket(self, sock: socket.socket, payload: Dict[str, Any]) -> Dict[str, Any]:
        encoded = (json.dumps(payload) + "\n").encode("utf-8")
        sock.settimeout(self.timeout)
        sock.sendall(encoded)
        chunks: List[bytes] = []
        while True:
            data = sock.recv(65536)
            if not data:
                break
            chunks.append(data)
            if b"\n" in data:
                break
        raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
        if not raw:
            raise ConnectionError(f"Empty response from Raspberry Pi at {self.host}:{self.port}")
        resp = json.loads(raw.splitlines()[0])
        if resp.get("status") != "ok":
            raise RuntimeError(f"Raspberry Pi HIL error: {resp.get('error', resp)}")
        return resp

    def _send_tcp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            return self._exchange_on_socket(sock, payload)

    def deploy_hil_server(self) -> bool:
        """Uploads the standalone rpi_hil_server.py script to the Raspberry Pi via SCP."""
        cmd = [
            "scp",
            "-P", str(self.ssh_port),
            "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=accept-new",
            SERVER_SCRIPT_PATH,
            f"{self.ssh_target}:{self.remote_script_path}",
        ]
        logging.info(f"Deploying '{os.path.basename(SERVER_SCRIPT_PATH)}' to {self.ssh_target}:{self.remote_script_path}...")
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode != 0:
            raise ConnectionError(f"SCP deploy to {self.ssh_target} failed: {res.stderr.strip()}")
        logging.info("Successfully deployed HIL server script to Raspberry Pi.")
        return True

    def _send_ssh(self, payload: Dict[str, Any], force_mock: bool = False) -> Dict[str, Any]:
        """Executes rpi_hil_server.py --stdio directly over SSH stdin/stdout."""
        if self.auto_deploy:
            self.deploy_hil_server()

        mock_flag = " --mock" if force_mock else ""
        remote_cmd = f"python3 {self.remote_script_path} --stdio{mock_flag}"
        cmd = [
            "ssh",
            "-p", str(self.ssh_port),
            "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=accept-new",
            self.ssh_target,
            remote_cmd,
        ]
        encoded_in = json.dumps(payload) + "\n"
        res = subprocess.run(cmd, input=encoded_in, capture_output=True, text=True, timeout=self.timeout + 15.0)
        if res.returncode != 0:
            raise ConnectionError(
                f"SSH HIL command failed on {self.ssh_target} (exit {res.returncode}): {res.stderr.strip()}"
            )

        out = res.stdout.strip()
        if not out:
            raise ConnectionError(f"No JSON telemetry returned from {self.ssh_target}. stderr={res.stderr.strip()}")
        resp = json.loads(out.splitlines()[-1])
        if resp.get("status") != "ok":
            raise RuntimeError(f"Raspberry Pi HIL error: {resp.get('error', resp)}")
        return resp

    def ping(self) -> Dict[str, Any]:
        """Verifies connectivity and reads hardware/GPIO details from the Raspberry Pi."""
        req = {"command": "ping"}
        return self._send_tcp(req) if self.transport == "tcp" else self._send_ssh(req)

    def replay_schedule(
        self,
        schedule_result: Any,
        time_scale_factor: float = 1e-5,
        is_3d: bool = True,
    ) -> Dict[str, Any]:
        """Transmits a 2D or 3D test schedule to the Raspberry Pi for hardware execution."""
        req = {
            "command": "replay",
            "time_scale_factor": time_scale_factor,
            "schedule": serialize_schedule(schedule_result, is_3d=is_3d),
        }
        rpc_start = time.perf_counter()
        resp = self._send_tcp(req) if self.transport == "tcp" else self._send_ssh(req)
        rpc_elapsed = time.perf_counter() - rpc_start
        report = resp["report"]
        report["client_roundtrip_sec"] = round(rpc_elapsed, 6)
        report["transport"] = self.transport
        report["remote_endpoint"] = f"{self.transport}://{self.ssh_target if self.transport == 'ssh' else f'{self.host}:{self.port}'}"
        return report


class BaseRaspberryPiTester:
    """
    Shared Hardware-in-the-Loop (HIL) tester supporting:
    - Remote physical Raspberry Pi execution (TCP or SSH)
    - Local physical GPIO execution (when run on a Raspberry Pi)
    - Calibrated Mock Simulator fallback
    """

    def __init__(
        self,
        is_3d: bool = True,
        clock_pin: int = DEFAULT_CLOCK_PIN,
        tam_control_pins: Optional[List[int]] = None,
        test_clock_freq_hz: float = 1000.0,
        mock_mode: Optional[bool] = None,
        remote_host: Optional[str] = None,
        remote_port: int = 5055,
        transport: str = "tcp",
        ssh_user: Optional[str] = None,
        ssh_port: int = 22,
        allow_mock_fallback: bool = True,
    ):
        self.is_3d = is_3d
        self.clock_pin = clock_pin
        self.tam_control_pins = tam_control_pins or list(DEFAULT_TAM_PINS)
        self.test_clock_freq_hz = test_clock_freq_hz
        self.cycle_time_sec = 1.0 / test_clock_freq_hz
        self.remote_host = remote_host
        self.allow_mock_fallback = allow_mock_fallback
        self.client: Optional[RemoteRPiHILClient] = None
        self.local_backend: Optional[GPIOBackend] = None

        if remote_host:
            self.mock_mode = False
            self.client = RemoteRPiHILClient(
                host=remote_host,
                port=remote_port,
                transport=transport,
                ssh_user=ssh_user,
                ssh_port=ssh_port,
            )
            self.hardware_status = f"Remote RPi ({transport.upper()} -> {remote_host})"
            self.status = self.hardware_status
            logging.info(f"RPi Tester Bridge Status: {self.hardware_status}")
        else:
            force_mock = True if mock_mode is True else False
            self.local_backend = GPIOBackend(
                clock_pin=self.clock_pin,
                tam_pins=self.tam_control_pins,
                force_mock=force_mock,
            )
            self.mock_mode = not self.local_backend.is_physical
            self.hardware_status = (
                "Initialized (Mock Engine)"
                if self.mock_mode
                else f"Connected ({self.local_backend.board_model} via {self.local_backend.backend_name})"
            )
            self.status = self.hardware_status
            logging.info(f"RPi Tester Bridge Status: {self.hardware_status}")

    def ping_remote(self) -> Optional[Dict[str, Any]]:
        """Tests connection to the configured remote Raspberry Pi."""
        if not self.client:
            return None
        return self.client.ping()

    def replay_schedule(self, schedule_result: Any, time_scale_factor: float = 1e-5) -> Dict[str, Any]:
        """Replays an optimized 2D or 3D test schedule on Raspberry Pi hardware or fallback simulator."""
        logging.info(f"Beginning HIL Schedule Replay for '{schedule_result.algorithm_name}'")
        logging.info(f"Target Schedule Makespan: {schedule_result.makespan:,} cycles")

        if self.client is not None:
            try:
                report = self.client.replay_schedule(
                    schedule_result,
                    time_scale_factor=time_scale_factor,
                    is_3d=self.is_3d,
                )
                logging.info(
                    f"Remote RPi HIL Replay Completed in {report['total_wall_clock_sec']:.4f}s | "
                    f"Mode: {report['hardware_mode']}"
                )
                return report
            except Exception as exc:
                if not self.allow_mock_fallback:
                    raise
                logging.warning(f"Remote RPi connection failed ({exc}). Falling back to Mock Simulator.")
                if self.local_backend is None:
                    self.local_backend = GPIOBackend(
                        clock_pin=self.clock_pin,
                        tam_pins=self.tam_control_pins,
                        force_mock=True,
                    )
                self.mock_mode = True

        backend = self.local_backend or GPIOBackend(force_mock=True)
        payload = {
            "time_scale_factor": time_scale_factor,
            "schedule": serialize_schedule(schedule_result, is_3d=self.is_3d),
        }
        report = execute_replay(backend, payload)
        logging.info(f"HIL Replay Completed in {report['total_wall_clock_sec']:.4f} seconds.")
        logging.info(f"Hardware Overhead: {report['overhead_percentage']:.2f}% | Mode: {report['hardware_mode']}")
        return report

    def cleanup(self) -> None:
        if self.local_backend is not None:
            self.local_backend.cleanup()
