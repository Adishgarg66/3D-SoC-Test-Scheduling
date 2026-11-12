#!/usr/bin/env python3
"""
capstone/src/hardware/rpi_hil_server.py
=======================================
Standalone Hardware-in-the-Loop (HIL) Execution Server for Raspberry Pi (Pi 4 / 3 / Zero / 5).
Zero third-party dependencies beyond Python stdlib + OS GPIO drivers (RPi.GPIO / gpiozero).

Supports two communication transports from a remote host (Mac/PC):
1. TCP Socket Server: `python3 rpi_hil_server.py --host 0.0.0.0 --port 5055`
2. SSH One-Shot Stdio: `ssh pi@<ip> python3 rpi_hil_server.py --stdio`
"""

import argparse
from datetime import datetime, timezone
import json
import logging
import os
import platform
import signal
import socket
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [RPi-HIL-Server] - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

DEFAULT_CLOCK_PIN = 18
DEFAULT_TAM_PINS = [2, 3, 4, 14, 15, 17, 27, 22]


def detect_board_model() -> str:
    """Reads Raspberry Pi hardware model string from device-tree when available."""
    model_path = "/proc/device-tree/model"
    if os.path.exists(model_path):
        try:
            with open(model_path, "r", encoding="utf-8", errors="ignore") as f:
                model = f.read().replace("\x00", "").strip()
                if model:
                    return model
        except OSError:
            pass
    return f"{platform.system()} ({platform.machine()})"


def detect_os_release() -> str:
    """Reads human-readable OS distribution name when available."""
    os_release_path = "/etc/os-release"
    if os.path.exists(os_release_path):
        try:
            with open(os_release_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except OSError:
            pass
    return platform.platform()


class GPIOBackend:
    """Unified GPIO driver supporting RPi.GPIO (Pi 4/3/Zero), gpiozero (Pi 5/lgpio), and Mock."""

    def __init__(
        self,
        clock_pin: int = DEFAULT_CLOCK_PIN,
        tam_pins: Optional[List[int]] = None,
        force_mock: bool = False,
    ):
        self.clock_pin = clock_pin
        self.tam_pins = tam_pins or list(DEFAULT_TAM_PINS)
        self.backend_name = "mock"
        self.is_physical = False
        self._gpio = None
        self._gz_devices: Dict[int, Any] = {}
        self.board_model = detect_board_model()

        if not force_mock:
            self._init_physical_driver()

    def _init_physical_driver(self) -> None:
        # 1. Try RPi.GPIO (standard for Raspberry Pi 4 / 3 / Zero)
        try:
            import RPi.GPIO as GPIO  # type: ignore

            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.clock_pin, GPIO.OUT, initial=GPIO.LOW)
            for pin in self.tam_pins:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            self._gpio = GPIO
            self.backend_name = "RPi.GPIO"
            self.is_physical = True
            logging.info(f"Initialized physical GPIO via RPi.GPIO on '{self.board_model}'")
            return
        except Exception as exc:
            logging.debug(f"RPi.GPIO unavailable ({exc}); checking gpiozero fallback.")

        # 2. Try gpiozero (works cleanly with lgpio on Pi 5 and newer kernels)
        try:
            from gpiozero import DigitalOutputDevice  # type: ignore

            self._gz_devices[self.clock_pin] = DigitalOutputDevice(self.clock_pin, initial_value=False)
            for pin in self.tam_pins:
                self._gz_devices[pin] = DigitalOutputDevice(pin, initial_value=False)
            self.backend_name = "gpiozero"
            self.is_physical = True
            logging.info(f"Initialized physical GPIO via gpiozero on '{self.board_model}'")
            return
        except Exception as exc:
            logging.warning(f"Physical GPIO unavailable ({exc}); using calibrated Mock Engine.")

        self.backend_name = "mock"
        self.is_physical = False

    def set_pins(self, pins: List[int], high: bool) -> None:
        if self.backend_name == "RPi.GPIO" and self._gpio is not None:
            state = self._gpio.HIGH if high else self._gpio.LOW
            for pin in pins:
                self._gpio.output(pin, state)
        elif self.backend_name == "gpiozero":
            for pin in pins:
                dev = self._gz_devices.get(pin)
                if dev is not None:
                    dev.on() if high else dev.off()
        else:
            time.sleep(0.00005 * len(pins))

    def pulse_clock(self) -> None:
        if self.backend_name == "RPi.GPIO" and self._gpio is not None:
            self._gpio.output(self.clock_pin, self._gpio.HIGH)
            self._gpio.output(self.clock_pin, self._gpio.LOW)
        elif self.backend_name == "gpiozero":
            clk = self._gz_devices.get(self.clock_pin)
            if clk is not None:
                clk.on()
                clk.off()

    def cleanup(self) -> None:
        if self.backend_name == "RPi.GPIO" and self._gpio is not None:
            try:
                self._gpio.cleanup()
            except Exception:
                pass
        elif self.backend_name == "gpiozero":
            for dev in self._gz_devices.values():
                try:
                    dev.close()
                except Exception:
                    pass
            self._gz_devices.clear()


def serialize_schedule(schedule_result: Any, is_3d: bool = True) -> Dict[str, Any]:
    """Converts ScheduleResult2D or ScheduleResult3D into a JSON-serializable dict."""
    tasks_payload = []
    for task in schedule_result.tasks:
        tasks_payload.append({
            "core_id": int(task.core_id),
            "core_name": str(task.core_name),
            "start_time": int(task.start_time),
            "end_time": int(task.end_time),
            "duration": int(task.duration),
            "power": float(task.power),
            "tam_width": int(task.tam_width),
            "layer_id": int(getattr(task, "layer_id", 0)),
        })

    return {
        "is_3d": is_3d,
        "algorithm": str(schedule_result.algorithm_name),
        "makespan": int(schedule_result.makespan),
        "peak_power": float(getattr(schedule_result, "peak_power", 0.0)),
        "peak_temperature": float(getattr(schedule_result, "peak_temperature", 0.0)),
        "max_tsv_used": int(getattr(schedule_result, "max_tsv_used", 0)),
        "max_tam_used": int(getattr(schedule_result, "max_tam_used", 0)),
        "constraint_status": str(getattr(schedule_result, "constraint_status", "Safe")),
        "tasks": tasks_payload,
    }


def execute_replay(backend: GPIOBackend, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Executes an incoming 2D or 3D SoC test schedule on the configured GPIO backend."""
    schedule = payload.get("schedule", {})
    time_scale_factor = float(payload.get("time_scale_factor", 1e-6))
    tasks = sorted(schedule.get("tasks", []), key=lambda t: t.get("start_time", 0))
    makespan = int(schedule.get("makespan", 0))
    is_3d = bool(schedule.get("is_3d", True))

    hardware_mode = (
        f"Physical {backend.board_model} ({backend.backend_name})"
        if backend.is_physical
        else "Mock RPi Simulator"
    )

    started_at_utc = datetime.now(timezone.utc).isoformat()
    start_epoch = time.time()
    start_wall = time.perf_counter()
    total_overhead_sec = 0.0
    cycles_replayed = 0
    gpio_events_count = 0
    task_events = []
    exec_error: Optional[str] = None

    try:
        for task in tasks:
            t_task_start = time.perf_counter()
            tam_width = int(task.get("tam_width", 1))
            active_pins = backend.tam_pins[:min(max(tam_width, 1), len(backend.tam_pins))]
            duration = int(task.get("duration", 0))

            t_pin_start = time.perf_counter()
            backend.set_pins(active_pins, high=True)
            backend.pulse_clock()
            t_pin_end = time.perf_counter()

            overhead_lag = t_pin_end - t_pin_start
            total_overhead_sec += overhead_lag

            if duration > 0 and time_scale_factor > 0:
                time.sleep(duration * time_scale_factor)

            cycles_replayed += duration
            t_off_start = time.perf_counter()
            backend.set_pins(active_pins, high=False)
            t_off_end = time.perf_counter()
            total_overhead_sec += (t_off_end - t_off_start)

            # Transitions per task: assert N TAM pins, pulse clock (rising+falling=2), de-assert N pins
            transitions = 2 * len(active_pins) + 2
            gpio_events_count += transitions
            wall_task_sec = time.perf_counter() - t_task_start

            task_events.append({
                "core_id": task.get("core_id"),
                "core_name": task.get("core_name"),
                "layer_id": task.get("layer_id", 0),
                "start_cycle": task.get("start_time", 0),
                "end_cycle": task.get("end_time", 0),
                "duration_cycles": duration,
                "hardware_pins_used": active_pins,
                "gpio_transitions": transitions,
                "pin_setup_overhead_ms": round(overhead_lag * 1000.0, 4),
                "wall_task_ms": round(wall_task_sec * 1000.0, 4),
            })
    except Exception as exc:
        exec_error = str(exc)
        logging.error(f"HIL Replay interrupted with error: {exec_error}")

    total_wall = time.perf_counter() - start_wall
    end_epoch = time.time()
    ended_at_utc = datetime.now(timezone.utc).isoformat()

    expected_pure_makespan = makespan * time_scale_factor
    cumulative_sleep_target = cycles_replayed * time_scale_factor
    overhead_vs_makespan_pct = (
        ((total_wall - expected_pure_makespan) / expected_pure_makespan * 100.0)
        if expected_pure_makespan > 0
        else 0.0
    )
    overhead_vs_sleep_pct = (
        ((total_wall - cumulative_sleep_target) / cumulative_sleep_target * 100.0)
        if cumulative_sleep_target > 0
        else 0.0
    )
    os_jitter_sec = max(0.0, total_wall - total_overhead_sec - cumulative_sleep_target)

    report = {
        "algorithm": schedule.get("algorithm", "Unknown"),
        "hardware_mode": hardware_mode,
        "board_model": backend.board_model,
        "gpio_backend": backend.backend_name,
        "is_physical_hardware": backend.is_physical,
        "hostname": socket.gethostname(),
        "os_release": detect_os_release(),
        "kernel_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "started_at_utc": started_at_utc,
        "ended_at_utc": ended_at_utc,
        "start_epoch_sec": round(start_epoch, 6),
        "end_epoch_sec": round(end_epoch, 6),
        "execution_status": "Success" if exec_error is None else "Error",
        "error": exec_error,
        "time_scale_factor": time_scale_factor,
        "makespan_cycles": makespan,
        "cycles_replayed": cycles_replayed,
        "total_wall_clock_sec": round(total_wall, 6),
        "expected_pure_time_sec": round(expected_pure_makespan, 6),
        "pure_simulation_sec": round(expected_pure_makespan, 6),
        "scaled_schedule_makespan_sec": round(expected_pure_makespan, 6),
        "cumulative_task_sleep_sec": round(cumulative_sleep_target, 6),
        "total_hardware_overhead_sec": round(total_overhead_sec, 6),
        "hardware_overhead_sec": round(total_overhead_sec, 6),
        "sleep_and_os_jitter_sec": round(os_jitter_sec, 6),
        "overhead_percentage": round(overhead_vs_makespan_pct, 2),
        "overhead_vs_cumulative_sleep_pct": round(overhead_vs_sleep_pct, 2),
        "gpio_events_count": gpio_events_count,
        "peak_power_watts": schedule.get("peak_power", 0.0),
        "task_events_count": len(task_events),
        "task_events": task_events,
        "constraint_status": schedule.get("constraint_status", "Safe"),
    }

    if is_3d:
        report["peak_temperature_celsius"] = schedule.get("peak_temperature", 0.0)
        report["max_tsv_channels_used"] = schedule.get("max_tsv_used", 0)
    else:
        report["max_tam_used"] = schedule.get("max_tam_used", 0)

    return report


def handle_request(backend: GPIOBackend, req: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Processes a single JSON command packet. Returns (response_dict, should_stop_server)."""
    cmd = req.get("command", "").lower()

    if cmd == "ping":
        return {
            "status": "ok",
            "command": "ping",
            "board_model": backend.board_model,
            "gpio_backend": backend.backend_name,
            "is_physical_hardware": backend.is_physical,
            "hostname": socket.gethostname(),
            "os_release": detect_os_release(),
            "kernel_release": platform.release(),
            "architecture": platform.machine(),
            "clock_pin": backend.clock_pin,
            "tam_pins": backend.tam_pins,
            "python_version": platform.python_version(),
        }, False

    if cmd == "replay":
        report = execute_replay(backend, req)
        return {"status": "ok", "command": "replay", "report": report}, False

    if cmd == "shutdown":
        return {"status": "ok", "command": "shutdown", "message": "Server shutting down."}, True

    return {"status": "error", "error": f"Unknown command: '{cmd}'"}, False


def _recv_json_line(conn: socket.socket) -> Optional[Dict[str, Any]]:
    chunks: List[bytes] = []
    while True:
        data = conn.recv(65536)
        if not data:
            break
        chunks.append(data)
        if b"\n" in data:
            break
    raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
    if not raw:
        return None
    line = raw.splitlines()[0]
    return json.loads(line)


def serve_connection(conn: socket.socket, backend: GPIOBackend) -> bool:
    """Processes one framed JSON request on an accepted socket. Returns True if server should stop."""
    with conn:
        conn.settimeout(120.0)
        try:
            req = _recv_json_line(conn)
            if req is None:
                return False
            resp, should_stop = handle_request(backend, req)
            conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
            return should_stop
        except Exception as exc:
            err_payload = {"status": "error", "error": str(exc)}
            try:
                conn.sendall((json.dumps(err_payload) + "\n").encode("utf-8"))
            except OSError:
                pass
            return False


def serve_tcp(host: str, port: int, clock_pin: int, tam_pins: List[int], force_mock: bool) -> None:
    """Starts persistent TCP HIL server listening for schedule execution packets."""
    backend = GPIOBackend(clock_pin=clock_pin, tam_pins=tam_pins, force_mock=force_mock)
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(5)
    server_sock.settimeout(1.0)

    running = True

    def _stop_handler(signum, frame):
        nonlocal running
        running = False

    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, _stop_handler)
        signal.signal(signal.SIGTERM, _stop_handler)

    logging.info(
        f"Listening on {host}:{port} | Board: '{backend.board_model}' | GPIO Backend: {backend.backend_name}"
    )

    try:
        while running:
            try:
                conn, _addr = server_sock.accept()
            except socket.timeout:
                continue
            if serve_connection(conn, backend):
                running = False
    finally:
        server_sock.close()
        backend.cleanup()
        logging.info("RPi HIL server stopped cleanly.")


def run_stdio(clock_pin: int, tam_pins: List[int], force_mock: bool) -> None:
    """Executes one request piped via stdin and returns JSON over stdout (used by SSH transport)."""
    backend = GPIOBackend(clock_pin=clock_pin, tam_pins=tam_pins, force_mock=force_mock)
    try:
        raw = sys.stdin.readline().strip()
        if not raw:
            print(json.dumps({"status": "error", "error": "Empty stdin payload"}))
            return
        req = json.loads(raw)
        resp, _ = handle_request(backend, req)
        print(json.dumps(resp), flush=True)
    finally:
        backend.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser(description="Raspberry Pi HIL Execution Server (2D & 3D SoC Tester)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind IP address for TCP server (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5055, help="TCP port (default: 5055)")
    parser.add_argument("--clock-pin", type=int, default=DEFAULT_CLOCK_PIN, help="BCM clock pin (default: 18)")
    parser.add_argument("--mock", action="store_true", help="Force calibrated mock GPIO engine")
    parser.add_argument("--stdio", action="store_true", help="One-shot stdin/stdout JSON mode (for SSH)")
    args = parser.parse_args()

    if args.stdio:
        run_stdio(clock_pin=args.clock_pin, tam_pins=DEFAULT_TAM_PINS, force_mock=args.mock)
    else:
        serve_tcp(host=args.host, port=args.port, clock_pin=args.clock_pin, tam_pins=DEFAULT_TAM_PINS, force_mock=args.mock)


if __name__ == "__main__":
    main()
