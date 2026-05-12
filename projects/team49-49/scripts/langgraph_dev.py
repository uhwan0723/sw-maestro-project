from __future__ import annotations

import argparse
import os
import shutil
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


def print_graphs(graphs: dict[str, Path]) -> None:
    if not graphs:
        print("No LangGraph apps found under graphs/<name>/langgraph.json.", flush=True)
        return
    for name, path in graphs.items():
        print(f"{name}: {path.relative_to(ROOT)}", flush=True)


def select_graphs(names: list[str], run_all: bool) -> dict[str, Path]:
    graphs = discover_graphs()
    if run_all:
        return graphs
    if not names:
        names = list(graphs)

    selected: dict[str, Path] = {}
    missing: list[str] = []
    for name in names:
        path = Path(name)
        if path.exists() and (path / "langgraph.json").exists():
            selected[path.name] = path.resolve()
        elif name in graphs:
            selected[name] = graphs[name]
        else:
            missing.append(name)

    if missing:
        available = ", ".join(graphs) or "none"
        print(f"LangGraph app(s) not found yet: {', '.join(missing)}. Available: {available}", flush=True)
    return selected


def ensure_ready(graphs: dict[str, Path]) -> int:
    if shutil.which("langgraph") is None:
        print("LangGraph CLI is not installed. Run: npm run langgraph:install", flush=True)
        return 1

    missing_env = [
        graph_dir.relative_to(ROOT)
        for graph_dir in graphs.values()
        if (graph_dir / ".env.example").exists() and not (graph_dir / ".env").exists()
    ]
    if missing_env:
        print("Missing .env for LangGraph app(s):", flush=True)
        for path in missing_env:
            print(f"- {path}", flush=True)
        print("Run: npm run langgraph:install", flush=True)
        return 1
    return 0


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


def start_graph(name: str, graph_dir: Path, port: int, tunnel: bool) -> subprocess.Popen[str]:
    command = ["langgraph", "dev", "--port", str(port), "--allow-blocking", "--no-browser"]
    if tunnel:
        command.append("--tunnel")

    print(f"[{name}] http://127.0.0.1:{port}", flush=True)
    print(f"[{name}] https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:{port}", flush=True)
    return subprocess.Popen(
        resolve_command(command),
        cwd=str(graph_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=os.environ.copy(),
    )


def run_graphs(graphs: dict[str, Path], port: int, tunnel: bool) -> int:
    if not graphs:
        print("No LangGraph apps found under graphs/<name>/langgraph.json.", flush=True)
        return 0

    ready_code = ensure_ready(graphs)
    if ready_code:
        return ready_code

    if len(graphs) == 1:
        name, graph_dir = next(iter(graphs.items()))
        print(f"[{name}] http://127.0.0.1:{port}", flush=True)
        print(f"[{name}] https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:{port}", flush=True)
        command = ["langgraph", "dev", "--port", str(port), "--allow-blocking", "--no-browser"]
        if tunnel:
            command.append("--tunnel")
        return subprocess.call(resolve_command(command), cwd=str(graph_dir), env=os.environ.copy())

    processes: list[tuple[str, subprocess.Popen[str]]] = []
    try:
        for offset, (name, graph_dir) in enumerate(graphs.items()):
            process = start_graph(name, graph_dir, port + offset, tunnel)
            processes.append((name, process))
            threading.Thread(target=stream_output, args=(name, process), daemon=True).start()

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
        for _, process in processes:
            if process.poll() is None:
                terminate_process_tree(process)


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
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local LangGraph apps from graphs/<name>.")
    parser.add_argument("graphs", nargs="*", help="Graph names under graphs/ or paths with langgraph.json.")
    parser.add_argument("--all", action="store_true", help="Run every graph under graphs/ on consecutive ports.")
    parser.add_argument("--list", action="store_true", help="List discovered graphs.")
    parser.add_argument("--port", type=int, default=2024, help="First LangGraph dev server port.")
    parser.add_argument("--tunnel", action="store_true", help="Pass --tunnel to langgraph dev.")
    args = parser.parse_args()

    graphs = discover_graphs()
    if args.list:
        print_graphs(graphs)
        return 0

    selected = select_graphs(args.graphs, args.all)
    return run_graphs(selected, args.port, args.tunnel)


if __name__ == "__main__":
    raise SystemExit(main())
