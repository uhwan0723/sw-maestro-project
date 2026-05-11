from app.agents.strategy import llm as llm_mod


class FakeChatUpstage:
    def __init__(self, *, model: str, api_key: str, temperature: float):
        self.model = model
        self.api_key = api_key
        self.temperature = temperature


def test_build_chat_uses_settings_api_key(monkeypatch):
    monkeypatch.delenv("UPSTAGE_API_KEY", raising=False)
    monkeypatch.setattr(llm_mod.settings, "upstage_api_key", "settings-key")
    monkeypatch.setattr(llm_mod, "ChatUpstage", FakeChatUpstage)

    chat = llm_mod._build_chat("recommend")

    assert chat.api_key == "settings-key"
    assert chat.temperature == 0.0


def test_model_for_uses_settings_model_when_env_is_absent(monkeypatch):
    monkeypatch.delenv("UPSTAGE_MODEL_RECOMMEND", raising=False)
    monkeypatch.setattr(llm_mod.settings, "upstage_model_recommend", "settings-model")

    assert llm_mod._model_for("recommend") == "settings-model"
