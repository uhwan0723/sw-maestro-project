from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAPHS_DIR = ROOT / "graphs"


def discover_graphs() -> dict[str, Path]:
    if not GRAPHS_DIR.exists():
        return {}
    return {
        path.name: path
        for path in sorted(GRAPHS_DIR.iterdir())
        if path.is_dir() and (path / "langgraph.json").exists()
    }


def select_graphs(names: list[str]) -> dict[str, Path]:
    graphs = discover_graphs()
    if not names:
        return graphs

    selected: dict[str, Path] = {}
    missing: list[str] = []
    for name in names:
        if name in graphs:
            selected[name] = graphs[name]
        else:
            missing.append(name)

    if missing:
        available = ", ".join(graphs) or "none"
        raise SystemExit(f"Unknown graph(s): {', '.join(missing)}. Available: {available}")
    return selected


def run(command: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=str(cwd), check=True)


def ensure_env_file(graph_dir: Path) -> None:
    env_file = graph_dir / ".env"
    env_example = graph_dir / ".env.example"
    if env_file.exists() or not env_example.exists():
        return
    shutil.copyfile(env_example, env_file)
    print(f"created {env_file.relative_to(ROOT)} from .env.example")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install dependencies for local LangGraph apps.")
    parser.add_argument("graphs", nargs="*", help="Graph directory names under graphs/. Defaults to all graphs.")
    args = parser.parse_args()

    selected = select_graphs(args.graphs)
    run([sys.executable, "-m", "pip", "install", "-U", "langgraph-cli[inmem]"], ROOT)

    if not selected:
        print("No LangGraph apps found under graphs/<name>/langgraph.json. Installed LangGraph CLI only.")
        return 0

    for name, graph_dir in selected.items():
        requirements = graph_dir / "requirements.txt"
        print(f"\n[{name}]")
        ensure_env_file(graph_dir)
        if requirements.exists():
            run([sys.executable, "-m", "pip", "install", "-r", str(requirements)], graph_dir)
        else:
            print("requirements.txt not found, skipping graph-specific dependency install.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
