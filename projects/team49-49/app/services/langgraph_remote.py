from typing import Any, Protocol


class RemoteLangGraphRunner(Protocol):
    def is_configured(self, assistant_id: str | None = None) -> bool:
        """Return whether this runner can call a remote LangGraph assistant."""

    def run(self, assistant_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Run a remote LangGraph assistant and return its latest update payload."""


class NoOpRemoteLangGraphClient:
    def is_configured(self, assistant_id: str | None = None) -> bool:
        return False

    def run(self, assistant_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("Remote LangGraph is not configured.")


class LangGraphSDKClient:
    def __init__(self, deployment_url: str, api_key: str):
        self.deployment_url = deployment_url.rstrip("/")
        self.api_key = api_key
        self._client: Any | None = None

    def is_configured(self, assistant_id: str | None = None) -> bool:
        return bool(self.deployment_url and self.api_key and (assistant_id is None or assistant_id))

    def run(self, assistant_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured(assistant_id):
            raise RuntimeError("Remote LangGraph deployment URL, API key, or assistant ID is missing.")

        latest: dict[str, Any] = {}
        for chunk in self._get_client().runs.stream(
            None,
            assistant_id,
            input=payload,
            stream_mode="updates",
        ):
            data = getattr(chunk, "data", None)
            if isinstance(data, dict):
                latest.update(data)
            elif data is not None:
                latest["output"] = data
        return latest

    def _get_client(self) -> Any:
        if self._client is None:
            from langgraph_sdk import get_sync_client

            self._client = get_sync_client(url=self.deployment_url, api_key=self.api_key)
        return self._client


def build_remote_langgraph_client(settings: Any) -> RemoteLangGraphRunner:
    deployment_url = getattr(settings, "langgraph_deployment_url", "")
    api_key = getattr(settings, "langsmith_api_key", "")
    if not deployment_url or not api_key:
        return NoOpRemoteLangGraphClient()
    return LangGraphSDKClient(deployment_url=deployment_url, api_key=api_key)


class RelationLinkingAdapter:
    def __init__(
        self,
        remote_runner: RemoteLangGraphRunner | None = None,
        assistant_id: str = "",
        local_detector: Any | None = None,
    ):
        self.remote_runner = remote_runner
        self.assistant_id = assistant_id
        if local_detector is None:
            from app.services.relations import CandidateRelationDetector
            self.local_detector = CandidateRelationDetector()
        else:
            self.local_detector = local_detector

    def run(
        self,
        workspace_id: int,
        new_cards: list[dict[str, Any]],
        existing_cards: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if self.remote_runner and self.remote_runner.is_configured(self.assistant_id):
            payload = {
                "workspace_id": workspace_id,
                "new_cards": new_cards,
                "existing_cards": existing_cards,
            }
            try:
                result = self.remote_runner.run(self.assistant_id, payload)
                if "relation_candidates" in result:
                    return result["relation_candidates"]
            except Exception:
                pass

        relations = []
        for card in new_cards:
            relations.extend(self.local_detector.detect(card, existing_cards))
        return relations
