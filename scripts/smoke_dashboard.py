#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CONFIG = ROOT / "tests" / "fixtures" / "dashboard" / "config.json"


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def get_json(url: str) -> tuple[int, dict[str, Any]]:
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(url, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def wait_until_ready(base_url: str, process: subprocess.Popen[str]) -> dict[str, Any]:
    deadline = time.monotonic() + 20
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            status, payload = get_json(f"{base_url}/api/ready")
            if status == 200:
                return payload
        except (OSError, URLError, ValueError) as exc:
            last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"dashboard did not become ready: {last_error}")


def stop_process(process: subprocess.Popen[str]) -> str:
    if process.poll() is None:
        process.terminate()
    try:
        output, _ = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate(timeout=5)
    return output


def main() -> int:
    port = available_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["CROSS_ASSET_CONFIG_PATH"] = str(FIXTURE_CONFIG)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        ready = wait_until_ready(base_url, process)
        expected = {
            "/api/health": 200,
            "/api/config": 200,
            "/api/dates": 200,
            "/api/assets": 200,
            "/api/playback": 200,
        }
        for path, expected_status in expected.items():
            status, _payload = get_json(f"{base_url}{path}")
            if status != expected_status:
                raise RuntimeError(f"{path} returned {status}, expected {expected_status}")
        if ready["date_count"] != 2 or ready["asset_count"] != 2:
            raise RuntimeError(f"unexpected readiness payload: {ready}")
        print(json.dumps({"status": "ok", "base_url": base_url, "ready": ready}))
        return 0
    except Exception:
        output = stop_process(process)
        if output:
            print(output, file=sys.stderr)
        raise
    finally:
        if process.poll() is None:
            stop_process(process)


if __name__ == "__main__":
    raise SystemExit(main())
