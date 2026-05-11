import pytest
from fastapi.testclient import TestClient

from performation_backend.main import app


client = TestClient(app)


def test_health_check() -> None:
  response = client.get("/health")

  assert response.status_code == 200
  assert response.json() == {"status": "ok"}


def test_create_guide_uses_agent_workflow() -> None:
  response = client.post("/guides", json={"query": "예스24라이브홀 스탠딩"})

  assert response.status_code == 200
  payload = response.json()
  assert payload["input_type"] == "venue_with_detail_question"
  assert payload["venue"]["name"] == "YES24 Live Hall"
  assert payload["event_info"] is None
  assert payload["event_candidates"] == []
  assert payload["fallback_used"] is True


def test_analyze_alias_uses_guide_response_contract() -> None:
  response = client.post("/analyze", json={"query": "예스24라이브홀 스탠딩"})

  assert response.status_code == 200
  payload = response.json()
  assert payload["input_type"] == "venue_with_detail_question"
  assert payload["venue"]["name"] == "YES24 Live Hall"
  assert "summary" in payload
  assert "sources" in payload


def test_guide_request_trims_query_before_workflow() -> None:
  response = client.post("/guides", json={"query": "  예스24라이브홀 스탠딩  "})

  assert response.status_code == 200
  assert response.json()["input"] == "예스24라이브홀 스탠딩"


@pytest.mark.parametrize("endpoint", ["/guides", "/analyze"])
def test_blank_query_is_rejected(endpoint: str) -> None:
  response = client.post(endpoint, json={"query": "   "})

  assert response.status_code == 400
  payload = response.json()
  assert payload["status"] == "error"
  assert "error_message" in payload


def test_internal_error_returns_500() -> None:
  from unittest.mock import patch
  from fastapi.testclient import TestClient

  safe_client = TestClient(app, raise_server_exceptions=False)
  with patch("performation_backend.main.generate_visit_guide", side_effect=RuntimeError("agent failure")):
    response = safe_client.post("/guides", json={"query": "KSPO DOME"})

  assert response.status_code == 500
  payload = response.json()
  assert payload["status"] == "error"
  assert "error_message" in payload


def test_agent_timeout_returns_504() -> None:
  import time
  from unittest.mock import patch

  def slow_guide(_query: str):
    time.sleep(1)

  with patch("performation_backend.main._AGENT_TIMEOUT", 0.01), \
       patch("performation_backend.main.generate_visit_guide", side_effect=slow_guide):
    response = client.post("/guides", json={"query": "KSPO DOME"})

  assert response.status_code == 504
  payload = response.json()
  assert payload["status"] == "error"
  assert "error_message" in payload
