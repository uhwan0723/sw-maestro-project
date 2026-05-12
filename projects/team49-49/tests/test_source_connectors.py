from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.services.source_connectors import (
    GitHubConnector,
    LinearConnector,
    McpConnector,
    NotionConnector,
    SlackConnector,
    SourceConnectorConfigError,
    WebConnector,
    build_source_connector_registry,
)


class FakeResponse:
    def __init__(self, payload=None, text="", status_code=200, content=None):
        self.payload = payload
        self.text = text
        self.status_code = status_code
        self.content = content if content is not None else text.encode("utf-8")
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"{self.status_code} error")

    def json(self):
        return self.payload


class FakeHTTPClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.requests.append({"method": "GET", "url": url, "headers": headers or {}, "params": params or {}, "timeout": timeout})
        return self.responses.pop(0)

    def post(self, url, headers=None, json=None, timeout=None):
        self.requests.append({"method": "POST", "url": url, "headers": headers or {}, "json": json or {}, "timeout": timeout})
        return self.responses.pop(0)


def test_notion_connector_fetches_page_blocks_as_markdown():
    http = FakeHTTPClient(
        [
            FakeResponse({"properties": {"title": {"title": [{"plain_text": "Product Notes"}]}}}),
            FakeResponse(
                {
                    "results": [
                        {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "Decisions"}]}},
                        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "GraphDB is deferred."}]}},
                    ],
                    "has_more": False,
                }
            ),
        ]
    )
    connector = NotionConnector(token="secret_notion", http_client=http)

    result = connector.fetch("https://www.notion.so/Product-3588aaeba57c802e8824c6b8db0d9b7f?pvs=21", "")

    assert result.title == "Product Notes.md"
    assert result.external_id == "3588aaeba57c802e8824c6b8db0d9b7f"
    assert "## Decisions" in result.content
    assert "GraphDB is deferred." in result.content
    assert http.requests[0]["url"] == "https://api.notion.com/v1/pages/3588aaeba57c802e8824c6b8db0d9b7f"
    assert http.requests[0]["headers"]["Authorization"] == "Bearer secret_notion"


def test_notion_connector_fetches_child_pages_as_child_documents():
    child_page_id = "11111111222233334444555555555555"
    http = FakeHTTPClient(
        [
            FakeResponse({"properties": {"title": {"title": [{"plain_text": "Parent Spec"}]}}}),
            FakeResponse(
                {
                    "results": [
                        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "결정: parent context"}]}},
                        {"id": child_page_id, "type": "child_page", "child_page": {"title": "Child Spec"}},
                    ],
                    "has_more": False,
                }
            ),
            FakeResponse({"properties": {"title": {"title": [{"plain_text": "Child Spec"}]}}}),
            FakeResponse(
                {
                    "results": [
                        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "가설: child context"}]}},
                    ],
                    "has_more": False,
                }
            ),
        ]
    )
    connector = NotionConnector(token="secret_notion", http_client=http)

    result = connector.fetch("https://www.notion.so/Parent-3588aaeba57c802e8824c6b8db0d9b7f?pvs=21", "")

    assert result.title == "Parent Spec.md"
    assert "결정: parent context" in result.content
    assert len(result.child_documents) == 1
    child = result.child_documents[0]
    assert child.title == "Child Spec.md"
    assert child.external_id == child_page_id
    assert child.source_url.endswith(child_page_id)
    assert child.fetched_via == "notion_api"
    assert "가설: child context" in child.content


def test_github_connector_fetches_blob_url_with_raw_accept_header():
    http = FakeHTTPClient([FakeResponse(text="결정: GitHub PRD를 source로 저장한다.")])
    connector = GitHubConnector(token="ghp_secret", http_client=http)

    result = connector.fetch("https://github.com/org/repo/blob/main/docs/prd.md", "")

    assert result.title == "prd.md"
    assert result.content == "결정: GitHub PRD를 source로 저장한다."
    assert http.requests[0]["url"] == "https://api.github.com/repos/org/repo/contents/docs/prd.md"
    assert http.requests[0]["params"] == {"ref": "main"}
    assert http.requests[0]["headers"]["Accept"] == "application/vnd.github.raw+json"
    assert http.requests[0]["headers"]["Authorization"] == "Bearer ghp_secret"


def test_github_connector_fetches_issue_body_and_comments():
    http = FakeHTTPClient(
        [
            FakeResponse({"title": "Source intake", "body": "URL-only ingestion"}),
            FakeResponse([{"user": {"login": "mentor"}, "body": "Add evidence quotes."}]),
        ]
    )
    connector = GitHubConnector(token="ghp_secret", http_client=http)

    result = connector.fetch("https://github.com/org/repo/issues/17", "")

    assert result.title == "github-issues-17-source-intake.md"
    assert "# Source intake" in result.content
    assert "URL-only ingestion" in result.content
    assert "mentor: Add evidence quotes." in result.content
    assert http.requests[0]["url"] == "https://api.github.com/repos/org/repo/issues/17"
    assert http.requests[1]["url"] == "https://api.github.com/repos/org/repo/issues/17/comments"


def test_linear_connector_fetches_issue_by_identifier():
    http = FakeHTTPClient(
        [
            FakeResponse(
                {
                    "data": {
                        "issue": {
                            "identifier": "ICH-17",
                            "title": "Retrieval quality",
                            "description": "Answer only from stored context.",
                            "state": {"name": "In Progress"},
                            "labels": {"nodes": [{"name": "ai"}]},
                            "comments": {"nodes": [{"body": "Need evidence quotes.", "user": {"name": "Jihwan"}}]},
                        }
                    }
                }
            )
        ]
    )
    connector = LinearConnector(token="lin_secret", http_client=http)

    result = connector.fetch("", "ICH-17")

    assert result.title == "ICH-17-retrieval-quality.md"
    assert "# ICH-17 Retrieval quality" in result.content
    assert "State: In Progress" in result.content
    assert "Labels: ai" in result.content
    assert "Jihwan: Need evidence quotes." in result.content
    assert http.requests[0]["url"] == "https://api.linear.app/graphql"
    assert http.requests[0]["headers"]["Authorization"] == "Bearer lin_secret"


def test_linear_connector_extracts_issue_identifier_from_url():
    http = FakeHTTPClient(
        [
            FakeResponse(
                {
                    "data": {
                        "issue": {
                            "identifier": "ICH-17",
                            "title": "Retrieval quality",
                            "description": "",
                            "state": {"name": "Todo"},
                            "labels": {"nodes": []},
                            "comments": {"nodes": []},
                        }
                    }
                }
            )
        ]
    )
    connector = LinearConnector(token="lin_secret", http_client=http)

    result = connector.fetch("https://linear.app/team/issue/ICH-17/retrieval-quality", "")

    assert result.external_id == "ICH-17"
    assert http.requests[0]["json"]["variables"] == {"id": "ICH-17"}


def test_slack_connector_fetches_thread_transcript():
    http = FakeHTTPClient(
        [
            FakeResponse(
                {
                    "ok": True,
                    "messages": [
                        {"user": "U1", "text": "결정: Slack thread를 저장한다.", "ts": "171430.000100"},
                        {"user": "U2", "text": "근거: 회의 맥락이 남아 있다.", "ts": "171430.000200"},
                    ],
                }
            )
        ]
    )
    connector = SlackConnector(token="xoxb_secret", http_client=http)

    result = connector.fetch("slack://channels/C0123/171430.000100", "")

    assert result.title == "slack-C0123-171430.000100.md"
    assert "U1: 결정: Slack thread를 저장한다." in result.content
    assert "U2: 근거: 회의 맥락이 남아 있다." in result.content
    assert http.requests[0]["url"] == "https://slack.com/api/conversations.replies"
    assert http.requests[0]["params"] == {"channel": "C0123", "ts": "171430.000100"}


def test_slack_connector_parses_archive_permalink_timestamp():
    http = FakeHTTPClient([FakeResponse({"ok": True, "messages": [{"user": "U1", "text": "회의록 링크 저장", "ts": "171430000100.000200"}]})])
    connector = SlackConnector(token="xoxb_secret", http_client=http)

    result = connector.fetch("https://workspace.slack.com/archives/C0123/p171430000100000200", "")

    assert result.external_id == "C0123:171430000100.000200"
    assert http.requests[0]["params"] == {"channel": "C0123", "ts": "171430000100.000200"}


def test_mcp_connector_reads_resource_text_content():
    http = FakeHTTPClient(
        [
            FakeResponse(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "contents": [
                            {"uri": "notion://page/abc", "mimeType": "text/markdown", "text": "결정: MCP resource를 저장한다."}
                        ]
                    },
                }
            )
        ]
    )
    connector = McpConnector(server_url="https://mcp.example/mcp", access_token="mcp_secret", http_client=http)

    result = connector.fetch("notion://page/abc", "")

    assert result.title == "abc.md"
    assert result.content == "결정: MCP resource를 저장한다."
    assert http.requests[0]["url"] == "https://mcp.example/mcp"
    assert http.requests[0]["headers"]["Authorization"] == "Bearer mcp_secret"
    assert http.requests[0]["json"]["method"] == "resources/read"


def test_web_connector_strips_script_and_style_content():
    http = FakeHTTPClient([FakeResponse(text="<html><style>.x{}</style><body><h1>Title</h1><script>x()</script><p>Body text</p></body></html>")])
    connector = WebConnector(http_client=http)

    result = connector.fetch("https://example.com/post", "")

    assert result.title == "post.txt"
    assert "Title" in result.content
    assert "Body text" in result.content
    assert "script" not in result.content.lower()


def test_source_connector_registry_uses_minimal_source_env_surface():
    settings = Settings(
        _env_file=None,
        notion_token="notion",
        github_token="github",
        slack_token="slack",
        linear_token="linear",
        mcp_server_url="https://mcp.example/mcp",
        mcp_access_token="mcp",
    )

    registry = build_source_connector_registry(settings, http_client=FakeHTTPClient([]))

    assert {"notion", "github", "slack", "linear", "mcp", "web"} <= set(registry)
    assert not hasattr(settings, "mcp_protocol_version")
    assert not hasattr(settings, "source_fetch_timeout_seconds")
    assert not hasattr(settings, "source_max_bytes")


def test_source_connector_registry_does_not_create_http_clients_until_fetch(monkeypatch):
    def fail_eager_client_creation():
        raise AssertionError("httpx.Client should be lazy")

    monkeypatch.setattr("app.services.source_connectors.httpx.Client", fail_eager_client_creation)

    registry = build_source_connector_registry(Settings(_env_file=None))

    assert {"notion", "github", "slack", "linear", "mcp", "web"} <= set(registry)
    with pytest.raises(SourceConnectorConfigError, match="ICH_GITHUB_TOKEN"):
        registry["github"].fetch("https://github.com/org/repo/blob/main/docs/prd.md", "")


def test_token_backed_connectors_report_missing_configuration():
    with pytest.raises(SourceConnectorConfigError, match="ICH_NOTION_TOKEN"):
        NotionConnector(token="", http_client=FakeHTTPClient([])).fetch("https://notion.so/page-id", "")
