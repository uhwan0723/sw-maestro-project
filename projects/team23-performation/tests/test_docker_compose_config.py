from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_defines_backend_and_frontend_targets() -> None:
  content = (ROOT / "Dockerfile").read_text(encoding="utf-8")

  assert "FROM runtime AS backend" in content
  assert "FROM runtime AS frontend" in content
  assert "apps/backend/src:packages/agent/src:packages/domain/src:packages/venue-data/src" in content
  assert "apps/frontend/src:packages/domain/src" in content
  assert "performation_backend.main:app" in content
  assert 'GRADIO_SERVER_NAME="0.0.0.0"' in content
  assert 'GRADIO_SERVER_PORT="7860"' in content
  assert 'CMD ["python", "-m", "performation_frontend.app"]' in content


def test_compose_wires_frontend_to_backend_service() -> None:
  content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

  assert "  backend:" in content
  assert "  frontend:" in content
  assert "target: backend" in content
  assert "target: frontend" in content
  assert "PERFORMATION_API_URL: \"${PERFORMATION_FRONTEND_API_URL:-http://backend:8000}\"" in content
  assert "GRADIO_SERVER_NAME: \"${GRADIO_SERVER_NAME:-0.0.0.0}\"" in content
  assert "GRADIO_SERVER_PORT: \"${GRADIO_SERVER_PORT:-7860}\"" in content
  assert "\"${PERFORMATION_FRONTEND_PORT:-7860}:${GRADIO_SERVER_PORT:-7860}\"" in content
  assert "condition: service_healthy" in content


def test_compose_exposes_optional_agent_provider_environment() -> None:
  content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

  assert "KOPIS_API_KEY" in content
  assert "TAVILY_API_KEY" in content
  assert "BRAVE_SEARCH_API_KEY" in content
  assert "GEMINI_API_KEY" in content
  assert "PERFORMATION_CACHE_ENABLED" in content
