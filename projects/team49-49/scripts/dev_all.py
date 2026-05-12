from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAPHS_DIR = ROOT / "graphs"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def discover_graphs() -> dict[str, Path]:
    if not GRAPHS_DIR.exists():
        return {}
    return {
        path.name: path
        for path in sorted(GRAPHS_DIR.iterdir())
        if path.is_dir() and (path / "langgraph.json").exists()
    }


def stream_output(name: str, process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print(f"[{name}] {line}", end="", flush=True)


def resolve_command(command: list[str]) -> list[str]:
    if os.name == "nt" and not Path(command[0]).suffix:
        for suffix in (".cmd", ".exe", ".bat"):
            executable = shutil.which(f"{command[0]}{suffix}")
            if executable:
                return [executable, *command[1:]]
    executable = shutil.which(command[0])
    if executable:
        return [executable, *command[1:]]
    return command


def start_process(
    name: str,
    command: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.Popen[str]:
    print(f"[{name}] $ {' '.join(command)}", flush=True)
    resolved_command = resolve_command(command)
    process = subprocess.Popen(
        resolved_command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env or os.environ.copy(),
    )
    threading.Thread(target=stream_output, args=(name, process), daemon=True).start()
    return process


def selected_graph_names(raw: list[str]) -> list[str]:
    if raw:
        return raw
    configured = os.environ.get("ICH_DEV_LANGGRAPH_GRAPHS", "").strip()
    if configured:
        return [item.strip() for item in configured.split(",") if item.strip()]
    return list(discover_graphs().keys())


def start_langgraph_processes(graph_names: list[str], first_port: int) -> list[tuple[str, subprocess.Popen[str]]]:
    if not graph_names:
        return []

    if shutil.which("langgraph") is None:
        print("[langgraph] CLI is not installed. Run: npm run langgraph:install", flush=True)
        return []

    graphs = discover_graphs()
    processes: list[tuple[str, subprocess.Popen[str]]] = []
    for offset, name in enumerate(graph_names):
        graph_dir = graphs.get(name)
        if graph_dir is None:
            available = ", ".join(graphs) or "none"
            print(f"[langgraph] unknown graph '{name}'. Available: {available}", flush=True)
            continue

        if (graph_dir / ".env.example").exists() and not (graph_dir / ".env").exists():
            print(f"[langgraph:{name}] missing .env. Run: npm run langgraph:install", flush=True)
            continue

        port = first_port + offset
        print(f"[langgraph:{name}] Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:{port}", flush=True)
        process = start_process(
            f"langgraph:{name}",
            ["langgraph", "dev", "--port", str(port)],
            graph_dir,
        )
        processes.append((f"langgraph:{name}", process))

    return processes


def terminate(processes: list[tuple[str, subprocess.Popen[str]]]) -> None:
    for name, process in processes:
        if process.poll() is None:
            print(f"[{name}] stopping", flush=True)
            terminate_process_tree(process)

    deadline = time.time() + 5
    for _, process in processes:
        while process.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if process.poll() is None:
            process.kill()


def terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    process.terminate()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run backend, frontend, and local LangGraph apps together.")
    parser.add_argument("--no-langgraph", action="store_true", help="Run only FastAPI and Vite.")
    parser.add_argument("--graph", action="append", default=[], help="LangGraph app name under graphs/. Can be repeated.")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--langgraph-port", type=int, default=2024)
    args = parser.parse_args()

    backend_env = os.environ.copy()
    if not args.no_langgraph:
        graph_names = selected_graph_names(args.graph)
        if graph_names:
            backend_env.setdefault("LANGGRAPH_DEPLOYMENT_URL", f"http://127.0.0.1:{args.langgraph_port}")
            backend_env.setdefault("LANGSMITH_API_KEY", "local")
            backend_env.setdefault("LANGGRAPH_QA_ASSISTANT_ID", graph_names[0])

    processes: list[tuple[str, subprocess.Popen[str]]] = []
    try:
        if not args.no_langgraph:
            processes.extend(start_langgraph_processes(selected_graph_names(args.graph), args.langgraph_port))

        processes.append(
            (
                "backend",
                start_process(
                    "backend",
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "app.main:create_app",
                        "--factory",
                        "--reload",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(args.backend_port),
                    ],
                    ROOT,
                    backend_env,
                ),
            )
        )
        processes.append(
            (
                "frontend",
                start_process(
                    "frontend",
                    [
                        "npm",
                        "--prefix",
                        "frontend",
                        "run",
                        "dev",
                        "--",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(args.frontend_port),
                    ],
                    ROOT,
                ),
            )
        )

        print(f"[app] Frontend: http://127.0.0.1:{args.frontend_port}", flush=True)
        print(f"[app] Backend:  http://127.0.0.1:{args.backend_port}", flush=True)

        while True:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    print(f"[{name}] exited with code {code}", flush=True)
                    return code
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 130
    finally:
        terminate(processes)


if __name__ == "__main__":
    if os.name == "nt":
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    raise SystemExit(main())
