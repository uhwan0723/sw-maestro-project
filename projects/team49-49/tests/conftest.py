import pytest

from app.services.llm import NoOpLLMClient


@pytest.fixture(autouse=True)
def disable_default_app_llm(monkeypatch, request):
    if "create_app" not in request.module.__dict__:
        return

    import app.main as app_main

    monkeypatch.setattr(app_main, "build_llm_client", lambda settings: NoOpLLMClient())
