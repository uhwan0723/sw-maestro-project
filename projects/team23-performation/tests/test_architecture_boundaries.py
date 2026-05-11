from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_calls_backend_without_agent_imports() -> None:
  frontend_app = ROOT / "apps" / "frontend" / "src" / "performation_frontend" / "app.py"
  frontend_api = ROOT / "apps" / "frontend" / "src" / "performation_frontend" / "api.py"
  content = frontend_app.read_text(encoding="utf-8") + frontend_api.read_text(encoding="utf-8")

  assert "httpx" in content
  assert "PERFORMATION_API_URL" in content
  assert "performation_agent" not in content
  assert "performation_venue_data" not in content


def test_agent_package_has_no_ui_or_api_framework_dependency() -> None:
  agent_root = ROOT / "packages" / "agent" / "src" / "performation_agent"
  for path in agent_root.rglob("*.py"):
    content = path.read_text(encoding="utf-8").casefold()
    assert "fastapi" not in content
    assert "gradio" not in content
