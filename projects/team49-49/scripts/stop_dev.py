from __future__ import annotations

import argparse
import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT_PID = os.getpid()
DEFAULT_PORTS = [8000, 5173, 5174, 2024, 2025]


def powershell(script: str) -> str:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return (result.stdout or "").strip()


def process_table() -> list[dict[str, str]]:
    output = powershell(
        r"""
        Get-CimInstance Win32_Process |
          Where-Object { $_.Name -in @('python.exe','node.exe') } |
          ForEach-Object { "$($_.ProcessId)`t$($_.Name)`t$($_.CommandLine)" }
        """
    )
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            rows.append({"pid": parts[0], "name": parts[1], "command": parts[2]})
    return rows


def port_owners(ports: list[int]) -> set[int]:
    if not ports:
        return set()
    joined = ",".join(str(port) for port in ports)
    output = powershell(
        f"""
        Get-NetTCPConnection -LocalPort {joined} -ErrorAction SilentlyContinue |
          Where-Object {{ $_.State -eq 'Listen' }} |
          Select-Object -ExpandProperty OwningProcess -Unique
        """
    )
    owners: set[int] = set()
    for line in output.splitlines():
        try:
            owners.add(int(line.strip()))
        except ValueError:
            pass
    return owners


def is_known_dev_process(row: dict[str, str], include_pytest: bool, include_playwright_mcp: bool) -> bool:
    command = row["command"] or ""
    pid = int(row["pid"])
    if pid == CURRENT_PID:
        return False
    if include_playwright_mcp and "@playwright" in command and "mcp" in command:
        return True
    markers = [
        "scripts/dev_all.py",
        "scripts\\dev_all.py",
        "scripts/langgraph_dev.py",
        "scripts\\langgraph_dev.py",
        "langgraph.exe",
        "uvicorn",
        "vite",
        "npm\\bin\\npm-cli.js",
    ]
    if include_pytest:
        markers.extend(["pytest", "-m pytest"])
    if not any(marker in command for marker in markers):
        return False
    return ROOT in command or "langgraph.exe" in command or "vite" in command


def stop_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    subprocess.run(["kill", "-TERM", str(pid)], check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stop local app, LangGraph, test, and browser helper processes.")
    parser.add_argument("--include-pytest", action="store_true", help="Also stop pytest processes for this workspace.")
    parser.add_argument(
        "--include-playwright-mcp",
        action="store_true",
        help="Also stop @playwright/mcp helper processes.",
    )
    parser.add_argument(
        "--ports",
        default=",".join(str(port) for port in DEFAULT_PORTS),
        help="Comma-separated ports whose listening owners should be stopped when they match known dev commands.",
    )
    args = parser.parse_args()

    ports = [int(item.strip()) for item in args.ports.split(",") if item.strip()]
    owners = port_owners(ports)
    rows = process_table()
    pids: set[int] = set()
    by_pid = {int(row["pid"]): row for row in rows}

    for row in rows:
        pid = int(row["pid"])
        if is_known_dev_process(row, args.include_pytest, args.include_playwright_mcp):
            pids.add(pid)

    for pid in owners:
        row = by_pid.get(pid)
        if row and is_known_dev_process(row, include_pytest=True, include_playwright_mcp=False):
            pids.add(pid)

    if not pids:
        print("No matching local dev processes found.")
        return 0

    for pid in sorted(pids):
        print(f"Stopping process tree {pid}")
        stop_process_tree(pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
