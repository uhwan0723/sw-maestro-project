from types import SimpleNamespace

from app.services.langgraph_remote import LangGraphSDKClient, NoOpRemoteLangGraphClient, build_remote_langgraph_client


class FakeChunk:
    def __init__(self, data):
        self.data = data


class FakeRuns:
    def __init__(self):
        self.calls = []

    def stream(self, thread_id, assistant_id, input, stream_mode):
        self.calls.append(
            {
                "thread_id": thread_id,
                "assistant_id": assistant_id,
                "input": input,
                "stream_mode": stream_mode,
            }
        )
        return [
            FakeChunk({"retrieve_context": {"cards": [1]}}),
            FakeChunk({"generate_answer": {"result": {"answer": "remote answer"}}}),
        ]


class FakeSyncClient:
    def __init__(self):
        self.runs = FakeRuns()


def test_remote_langgraph_client_streams_updates_with_sdk_client():
    fake_sync_client = FakeSyncClient()
    client = LangGraphSDKClient(deployment_url="https://langgraph.example", api_key="lsv2_key")
    client._client = fake_sync_client

    result = client.run("qa_assistant", {"question": "왜?"})

    assert result["retrieve_context"]["cards"] == [1]
    assert result["generate_answer"]["result"]["answer"] == "remote answer"
    assert fake_sync_client.runs.calls[0]["assistant_id"] == "qa_assistant"
    assert fake_sync_client.runs.calls[0]["input"] == {"question": "왜?"}
    assert fake_sync_client.runs.calls[0]["stream_mode"] == "updates"


def test_remote_langgraph_builder_uses_noop_without_required_env():
    client = build_remote_langgraph_client(SimpleNamespace(langgraph_deployment_url="", langsmith_api_key=""))

    assert isinstance(client, NoOpRemoteLangGraphClient)
    assert client.is_configured("qa") is False
