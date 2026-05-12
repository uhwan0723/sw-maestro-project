import json
from pathlib import Path
import sys
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository


def run_smoke(db_path: str | Path = "data/local_smoke.sqlite3") -> dict[str, Any]:
    sqlite_path = Path(db_path)
    repository = SQLiteRepository(sqlite_path)
    app = create_app(repository=repository)
    app.state.settings.upstage_api_key = ""
    app.state.settings.langgraph_qa_assistant_id = ""
    app.state.remote_langgraph_client = None
    client = TestClient(app)

    health = client.get("/health").json()
    workspace = client.post(
        "/api/workspaces",
        json={"name": "Local SQLite Smoke", "description": "Local verification workspace"},
    ).json()
    workspace_id = workspace["id"]
    ingestion = client.post(
        f"/api/workspaces/{workspace_id}/documents/text",
        json={
            "filename": "local-smoke.md",
            "content": (
                "결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.\n\n"
                "근거: 로컬 MVP는 별도 서버 없이 SQLite 파일로 실행 가능해야 한다."
            ),
        },
    ).json()
    qa = client.post(
        f"/api/workspaces/{workspace_id}/qa",
        json={"question": "왜 GraphDB를 제외했어?"},
    ).json()

    return {
        "database": str(sqlite_path),
        "health": health,
        "workspace_id": workspace_id,
        "ingestion": ingestion,
        "qa": qa,
    }


def main() -> None:
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
