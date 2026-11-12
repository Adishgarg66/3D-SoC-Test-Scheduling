"""
tests/test_rpi_connection.py
============================
Unit and loopback integration tests for Raspberry Pi remote HIL connectivity:
1. Standalone rpi_hil_server protocol & replay telemetry
2. Live TCP socket client-server replay for 2D & 3D schedules
3. Stdio JSON pipe execution (used over SSH)
4. Connection parsing, unreachable fallback, and CLI flags
"""

import json
import os
import socket
import subprocess
import sys
import threading

import pytest

from capstone.src.hardware.rpi_hil_server import (
    GPIOBackend,
    handle_request,
    serialize_schedule,
    serve_connection,
)
from capstone.src.hardware.rpi_remote_bridge import RemoteRPiHILClient, SERVER_SCRIPT_PATH
from capstone.fixed_stacking.src.hardware.rpi_tester import RaspberryPi5Tester
from src.models.soc_2d import ScheduleResult2D, ScheduledTask2D
from src.models.soc_3d import ScheduleResult3D, ScheduledTask3D


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def sample_3d_schedule():
    tasks = [
        ScheduledTask3D(1, "c17", 0, 1000, 1000, 3.5, 4, 0, 0.2, 0.2, 0),
        ScheduledTask3D(4, "c880", 0, 2000, 2000, 6.8, 8, 1, 0.8, 0.7, 8),
    ]
    return ScheduleResult3D(
        algorithm_name="TestMACO3D",
        makespan=2000,
        tasks=tasks,
        power_profile=[10.3],
        thermal_profile=[42.0],
        tsv_profile=[8],
        peak_power=10.3,
        peak_temperature=42.0,
        max_tsv_used=8,
        constraint_status="Safe",
    )


@pytest.fixture
def sample_2d_schedule():
    tasks = [
        ScheduledTask2D(1, "c17", 0, 1500, 1500, 3.5, 4, 0.2, 0.2),
    ]
    return ScheduleResult2D(
        algorithm_name="TestGreedy2D",
        makespan=1500,
        tasks=tasks,
        power_profile=[3.5],
        tam_profile=[4],
        peak_power=3.5,
        max_tam_used=4,
        constraint_status="Safe",
    )


def test_serialize_schedules(sample_3d_schedule, sample_2d_schedule):
    p3d = serialize_schedule(sample_3d_schedule, is_3d=True)
    assert p3d["is_3d"] is True
    assert p3d["makespan"] == 2000
    assert len(p3d["tasks"]) == 2
    assert p3d["tasks"][1]["layer_id"] == 1

    p2d = serialize_schedule(sample_2d_schedule, is_3d=False)
    assert p2d["is_3d"] is False
    assert p2d["makespan"] == 1500
    assert p2d["max_tam_used"] == 4


def test_server_ping_and_unknown_command():
    backend = GPIOBackend(force_mock=True)
    resp, stop = handle_request(backend, {"command": "ping"})
    assert stop is False
    assert resp["status"] == "ok"
    assert resp["gpio_backend"] == "mock"

    err_resp, _ = handle_request(backend, {"command": "invalid_op"})
    assert err_resp["status"] == "error"


def test_socket_client_server_3d_and_2d_replay(monkeypatch, sample_3d_schedule, sample_2d_schedule):
    backend = GPIOBackend(clock_pin=18, tam_pins=[2, 3, 4, 14, 15, 17, 27, 22], force_mock=True)

    def _pair_connect(address, timeout=None):
        client_sock, server_sock = socket.socketpair()
        threading.Thread(
            target=serve_connection,
            args=(server_sock, backend),
            daemon=True,
        ).start()
        return client_sock

    monkeypatch.setattr(socket, "create_connection", _pair_connect)

    port = 5055
    client = RemoteRPiHILClient(host="127.0.0.1", port=port, transport="tcp", timeout=5.0)
    ping_resp = client.ping()
    assert ping_resp["status"] == "ok"
    assert ping_resp["clock_pin"] == 18

    tester3d = RaspberryPi5Tester(remote_host="127.0.0.1", remote_port=port, allow_mock_fallback=False)
    rep3d = tester3d.replay_schedule(sample_3d_schedule, time_scale_factor=1e-6)
    assert rep3d["makespan_cycles"] == 2000
    assert rep3d["cycles_replayed"] == 3000
    assert rep3d["max_tsv_channels_used"] == 8
    assert rep3d["remote_endpoint"] == f"tcp://127.0.0.1:{port}"

    rep2d = client.replay_schedule(sample_2d_schedule, time_scale_factor=1e-6, is_3d=False)
    assert rep2d["makespan_cycles"] == 1500
    assert rep2d["max_tam_used"] == 4


def test_cli_includes_rpi_flags():
    cli_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "run_test_suite.py"))
    res = subprocess.run([sys.executable, cli_path, "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    for flag in ("--rpi-host", "--rpi-port", "--rpi-transport", "--rpi-user", "--rpi-ping"):
        assert flag in res.stdout


def test_stdio_pipe_mode(sample_3d_schedule):
    req = {
        "command": "replay",
        "time_scale_factor": 1e-6,
        "schedule": serialize_schedule(sample_3d_schedule, is_3d=True),
    }
    proc = subprocess.run(
        [sys.executable, SERVER_SCRIPT_PATH, "--stdio", "--mock"],
        input=json.dumps(req) + "\n",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    resp = json.loads(proc.stdout.strip().splitlines()[-1])
    assert resp["status"] == "ok"
    assert resp["report"]["makespan_cycles"] == 2000
    assert resp["report"]["task_events_count"] == 2


def test_user_at_host_parsing_and_fallback(sample_3d_schedule):
    unused_port = _free_tcp_port()
    client = RemoteRPiHILClient(host="pi@192.0.2.1", port=unused_port, transport="ssh")
    assert client.ssh_user == "pi"
    assert client.host == "192.0.2.1"
    assert client.ssh_target == "pi@192.0.2.1"

    tester_fallback = RaspberryPi5Tester(
        remote_host="127.0.0.1",
        remote_port=unused_port,
        allow_mock_fallback=True,
    )
    report = tester_fallback.replay_schedule(sample_3d_schedule, time_scale_factor=1e-6)
    assert report["hardware_mode"] == "Mock RPi Simulator"
    assert report["makespan_cycles"] == 2000
