from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, urlparse

import httpx


MCP_PROTOCOL_VERSION = "2025-06-18"


@dataclass
class SourceFetchResult:
    title: str
    content: str
    external_id: str = ""
    source_url: str = ""
    fetched_via: str = "external"
    child_documents: list[SourceFetchResult] = field(default_factory=list)


class SourceConnector(Protocol):
    def fetch(self, source_url: str, external_id: str) -> SourceFetchResult:
        """Fetch source content from a configured read-only provider."""


class SourceConnectorError(ValueError):
    pass


class SourceConnectorConfigError(SourceConnectorError):
    pass


class SourceConnectorInputError(SourceConnectorError):
    pass


class SourceConnectorFetchError(SourceConnectorError):
    pass


class _LazyHTTPClientMixin:
    _http_client: Any | None

    @property
    def http_client(self) -> Any:
        if self._http_client is None:
            self._http_client = httpx.Client()
        return self._http_client


class NotionConnector(_LazyHTTPClientMixin):
    def __init__(
        self,
        token: str,
        http_client: Any | None = None,
        timeout: float = 12.0,
        max_child_depth: int = 4,
        max_child_pages: int = 100,
    ):
        self.token = token
        self._http_client = http_client
        self.timeout = timeout
        self.max_child_depth = max_child_depth
        self.max_child_pages = max_child_pages

    def fetch(self, source_url: str, external_id: str) -> SourceFetchResult:
        if not self.token:
            raise SourceConnectorConfigError("ICH_NOTION_TOKEN is required for Notion automatic source ingestion.")
        page_id = _extract_notion_page_id(source_url, external_id)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Accept": "application/json",
        }
        return self._fetch_page(
            page_id=page_id,
            source_url=source_url,
            headers=headers,
            depth=0,
            visited=set(),
            fetched_child_count=[0],
        )

    def _fetch_page(
        self,
        page_id: str,
        source_url: str,
        headers: dict[str, str],
        depth: int,
        visited: set[str],
        fetched_child_count: list[int],
    ) -> SourceFetchResult:
        page_id = page_id.replace("-", "")
        if page_id in visited:
            raise SourceConnectorFetchError("Notion page tree contains a cycle.")
        visited.add(page_id)
        page = _json_response(
            self.http_client.get(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, timeout=self.timeout),
            "Notion page fetch failed.",
        )
        title = _notion_title(page) or page_id
        blocks = self._fetch_blocks(page_id, headers)
        content = "\n\n".join(line for line in (_format_notion_block(block) for block in blocks) if line).strip()
        if not content:
            raise SourceConnectorFetchError("Notion page returned no readable block content.")
        child_documents: list[SourceFetchResult] = []
        if depth < self.max_child_depth:
            for block in blocks:
                if block.get("type") != "child_page":
                    continue
                child_page_id = (block.get("id") or "").replace("-", "")
                if not child_page_id or child_page_id in visited:
                    continue
                if fetched_child_count[0] >= self.max_child_pages:
                    break
                fetched_child_count[0] += 1
                child_documents.append(
                    self._fetch_page(
                        page_id=child_page_id,
                        source_url=_notion_page_url(child_page_id),
                        headers=headers,
                        depth=depth + 1,
                        visited=visited,
                        fetched_child_count=fetched_child_count,
                    )
                )
        return SourceFetchResult(
            title=_ensure_extension(title, "md"),
            content=content,
            external_id=page_id,
            source_url=source_url,
            fetched_via="notion_api",
            child_documents=child_documents,
        )

    def _fetch_blocks(self, page_id: str, headers: dict[str, str]) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        cursor = None
        while True:
            params = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            data = _json_response(
                self.http_client.get(
                    f"https://api.notion.com/v1/blocks/{page_id}/children",
                    headers=headers,
                    params=params,
                    timeout=self.timeout,
                ),
                "Notion block fetch failed.",
            )
            blocks.extend(data.get("results", []))
            if not data.get("has_more"):
                return blocks
            cursor = data.get("next_cursor")


class GitHubConnector(_LazyHTTPClientMixin):
    def __init__(self, token: str, http_client: Any | None = None, timeout: float = 12.0):
        self.token = token
        self._http_client = http_client
        self.timeout = timeout

    def fetch(self, source_url: str, external_id: str) -> SourceFetchResult:
        if not self.token:
            raise SourceConnectorConfigError("ICH_GITHUB_TOKEN is required for GitHub automatic source ingestion.")
        parsed = urlparse(source_url)
        if parsed.netloc == "raw.githubusercontent.com":
            return self._fetch_raw_url(parsed)
        if parsed.netloc.lower() != "github.com":
            raise SourceConnectorInputError("GitHub source_url must be a github.com or raw.githubusercontent.com link.")
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 2:
            raise SourceConnectorInputError("GitHub source_url must include owner and repository.")
        owner, repo = parts[0], parts[1]
        if len(parts) >= 5 and parts[2] == "blob":
            return self._fetch_file(owner, repo, parts[3], "/".join(parts[4:]))
        if len(parts) >= 4 and parts[2] in {"issues", "pull"}:
            return self._fetch_issue_or_pull(owner, repo, parts[2], parts[3])
        raise SourceConnectorInputError("GitHub source_url must point to a blob file, issue, pull request, or raw file.")

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _fetch_file(self, owner: str, repo: str, ref: str, path: str) -> SourceFetchResult:
        response = self.http_client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(path, safe='/')}",
            headers=self._headers("application/vnd.github.raw+json"),
            params={"ref": ref},
            timeout=self.timeout,
        )
        _raise_for_status(response, "GitHub file fetch failed.")
        content = _response_text(response)
        if not content.strip():
            raise SourceConnectorFetchError("GitHub file returned no readable content.")
        return SourceFetchResult(title=Path(path).name, content=content.strip(), external_id=f"{owner}/{repo}:{ref}:{path}", fetched_via="github_api")

    def _fetch_raw_url(self, parsed) -> SourceFetchResult:
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 4:
            raise SourceConnectorInputError("GitHub raw URL must include owner, repository, ref, and path.")
        owner, repo, ref = parts[0], parts[1], parts[2]
        return self._fetch_file(owner, repo, ref, "/".join(parts[3:]))

    def _fetch_issue_or_pull(self, owner: str, repo: str, kind: str, number: str) -> SourceFetchResult:
        endpoint_kind = "pulls" if kind == "pull" else "issues"
        item = _json_response(
            self.http_client.get(
                f"https://api.github.com/repos/{owner}/{repo}/{endpoint_kind}/{number}",
                headers=self._headers(),
                timeout=self.timeout,
            ),
            f"GitHub {kind} fetch failed.",
        )
        comments = _json_response(
            self.http_client.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments",
                headers=self._headers(),
                timeout=self.timeout,
            ),
            f"GitHub {kind} comments fetch failed.",
        )
        title = item.get("title") or f"{kind}-{number}"
        lines = [f"# {title}", "", item.get("body") or ""]
        for comment in comments:
            user = (comment.get("user") or {}).get("login") or "unknown"
            body = comment.get("body") or ""
            if body.strip():
                lines.extend(["", f"{user}: {body.strip()}"])
        return SourceFetchResult(
            title=_ensure_extension(f"github-{kind}-{number}-{_slug(title)}", "md"),
            content="\n".join(lines).strip(),
            external_id=f"{owner}/{repo}#{number}",
            fetched_via="github_api",
        )


class SlackConnector(_LazyHTTPClientMixin):
    def __init__(self, token: str, http_client: Any | None = None, timeout: float = 12.0):
        self.token = token
        self._http_client = http_client
        self.timeout = timeout

    def fetch(self, source_url: str, external_id: str) -> SourceFetchResult:
        if not self.token:
            raise SourceConnectorConfigError("ICH_SLACK_TOKEN is required for Slack automatic source ingestion.")
        channel_id, ts = _extract_slack_channel_and_ts(source_url, external_id)
        data = _json_response(
            self.http_client.get(
                "https://slack.com/api/conversations.replies",
                headers={"Authorization": f"Bearer {self.token}"},
                params={"channel": channel_id, "ts": ts},
                timeout=self.timeout,
            ),
            "Slack thread fetch failed.",
        )
        if data.get("ok") is False:
            raise SourceConnectorFetchError(f"Slack thread fetch failed: {data.get('error') or 'unknown_error'}")
        messages = data.get("messages") or []
        lines = []
        for message in messages:
            speaker = message.get("user") or message.get("username") or message.get("bot_id") or "unknown"
            text = _collapse_ws(message.get("text") or "")
            if text:
                lines.append(f"{speaker}: {text}")
        content = "\n".join(lines).strip()
        if not content:
            raise SourceConnectorFetchError("Slack thread returned no readable messages.")
        return SourceFetchResult(title=f"slack-{channel_id}-{ts}.md", content=content, external_id=f"{channel_id}:{ts}", fetched_via="slack_api")


class LinearConnector(_LazyHTTPClientMixin):
    def __init__(self, token: str, http_client: Any | None = None, timeout: float = 12.0):
        self.token = token
        self._http_client = http_client
        self.timeout = timeout

    def fetch(self, source_url: str, external_id: str) -> SourceFetchResult:
        if not self.token:
            raise SourceConnectorConfigError("ICH_LINEAR_TOKEN is required for Linear automatic source ingestion.")
        issue_id = _extract_linear_issue_id(source_url, external_id)
        query = """
        query SourceIntakeIssue($id: String!) {
          issue(id: $id) {
            identifier
            title
            description
            state { name }
            labels { nodes { name } }
            comments { nodes { body user { name } } }
          }
        }
        """
        data = _json_response(
            self.http_client.post(
                "https://api.linear.app/graphql",
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                json={"query": query, "variables": {"id": issue_id}},
                timeout=self.timeout,
            ),
            "Linear issue fetch failed.",
        )
        if data.get("errors"):
            raise SourceConnectorFetchError(f"Linear issue fetch failed: {data['errors'][0].get('message', 'unknown_error')}")
        issue = (data.get("data") or {}).get("issue")
        if not issue:
            raise SourceConnectorFetchError("Linear issue was not found.")
        identifier = issue.get("identifier") or issue_id
        title = issue.get("title") or identifier
        content = _format_linear_issue(issue)
        return SourceFetchResult(title=_ensure_extension(f"{identifier}-{_slug(title)}", "md"), content=content, external_id=identifier, fetched_via="linear_api")


class McpConnector(_LazyHTTPClientMixin):
    def __init__(self, server_url: str, access_token: str, http_client: Any | None = None, timeout: float = 12.0):
        self.server_url = server_url
        self.access_token = access_token
        self._http_client = http_client
        self.timeout = timeout

    def fetch(self, source_url: str, external_id: str) -> SourceFetchResult:
        if not self.server_url:
            raise SourceConnectorConfigError("ICH_MCP_SERVER_URL is required for MCP automatic source ingestion.")
        if not self.access_token:
            raise SourceConnectorConfigError("ICH_MCP_ACCESS_TOKEN is required for MCP automatic source ingestion.")
        resource_uri = (source_url or external_id or "").strip()
        if not resource_uri:
            raise SourceConnectorInputError("MCP source requires source_url or external_id resource URI.")
        data = _json_response(
            self.http_client.post(
                self.server_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
                },
                json={"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {"uri": resource_uri}},
                timeout=self.timeout,
            ),
            "MCP resource fetch failed.",
        )
        if data.get("error"):
            raise SourceConnectorFetchError(f"MCP resource fetch failed: {data['error'].get('message', 'unknown_error')}")
        contents = ((data.get("result") or {}).get("contents") or [])
        text_parts = [item.get("text", "") for item in contents if item.get("text")]
        content = "\n\n".join(text_parts).strip()
        if not content:
            raise SourceConnectorFetchError("MCP resource returned no readable text content.")
        return SourceFetchResult(title=_title_from_resource_uri(resource_uri), content=content, external_id=external_id or resource_uri, fetched_via="mcp")


class WebConnector(_LazyHTTPClientMixin):
    def __init__(self, http_client: Any | None = None, timeout: float = 12.0):
        self._http_client = http_client
        self.timeout = timeout

    def fetch(self, source_url: str, external_id: str) -> SourceFetchResult:
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"}:
            raise SourceConnectorInputError("Web source_url must be an http or https link.")
        response = self.http_client.get(source_url, headers={"User-Agent": "Ideation-Context-Hub/1.0"}, timeout=self.timeout)
        _raise_for_status(response, "Web source fetch failed.")
        content = _html_to_text(_response_text(response))
        if not content.strip():
            raise SourceConnectorFetchError("Web source returned no readable content.")
        filename = Path(parsed.path).name or parsed.netloc or "web-source"
        return SourceFetchResult(title=_ensure_extension(filename, "txt"), content=content.strip(), external_id=external_id, fetched_via="web_fetch")


def build_source_connector_registry(settings: Any, http_client: Any | None = None) -> dict[str, SourceConnector]:
    timeout = float(getattr(settings, "source_fetch_timeout_seconds", 12) or 12)
    return {
        "notion": NotionConnector(getattr(settings, "notion_token", ""), http_client=http_client, timeout=timeout),
        "github": GitHubConnector(getattr(settings, "github_token", ""), http_client=http_client, timeout=timeout),
        "slack": SlackConnector(getattr(settings, "slack_token", ""), http_client=http_client, timeout=timeout),
        "linear": LinearConnector(getattr(settings, "linear_token", ""), http_client=http_client, timeout=timeout),
        "mcp": McpConnector(
            server_url=getattr(settings, "mcp_server_url", ""),
            access_token=getattr(settings, "mcp_access_token", ""),
            http_client=http_client,
            timeout=timeout,
        ),
        "web": WebConnector(http_client=http_client, timeout=timeout),
    }


def _json_response(response: Any, message: str) -> dict[str, Any] | list[Any]:
    _raise_for_status(response, message)
    try:
        data = response.json()
    except Exception as error:
        raise SourceConnectorFetchError(message) from error
    if not isinstance(data, (dict, list)):
        raise SourceConnectorFetchError(message)
    return data


def _raise_for_status(response: Any, message: str) -> None:
    try:
        response.raise_for_status()
    except Exception as error:
        status_code = getattr(response, "status_code", "")
        suffix = f" Provider returned {status_code}." if status_code else ""
        raise SourceConnectorFetchError(f"{message}{suffix}") from error


def _response_text(response: Any) -> str:
    text = getattr(response, "text", "")
    if text:
        return text
    content = getattr(response, "content", b"")
    if isinstance(content, bytes):
        return content.decode("utf-8-sig")
    return str(content)


def _extract_notion_page_id(source_url: str, external_id: str) -> str:
    raw = (external_id or source_url or "").strip()
    match = re.search(r"([0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", raw)
    if not match:
        raise SourceConnectorInputError("Notion source requires a page URL or page id.")
    return match.group(1).replace("-", "")


def _notion_page_url(page_id: str) -> str:
    return f"https://www.notion.so/{page_id.replace('-', '')}"


def _notion_title(page: dict[str, Any]) -> str:
    for property_value in (page.get("properties") or {}).values():
        title_items = property_value.get("title")
        if isinstance(title_items, list):
            title = "".join(item.get("plain_text", "") for item in title_items).strip()
            if title:
                return title
    return ""


def _format_notion_block(block: dict[str, Any]) -> str:
    block_type = block.get("type", "")
    value = block.get(block_type) or {}
    text = _rich_text(value.get("rich_text", []))
    if not text and block_type == "child_page":
        text = value.get("title", "")
    if not text:
        return ""
    if block_type == "heading_1":
        return f"# {text}"
    if block_type == "heading_2":
        return f"## {text}"
    if block_type == "heading_3":
        return f"### {text}"
    if block_type == "bulleted_list_item":
        return f"- {text}"
    if block_type == "numbered_list_item":
        return f"1. {text}"
    if block_type == "quote":
        return f"> {text}"
    if block_type == "code":
        language = value.get("language", "")
        return f"```{language}\n{text}\n```"
    return text


def _rich_text(items: list[dict[str, Any]]) -> str:
    return "".join(item.get("plain_text", "") for item in items).strip()


def _extract_slack_channel_and_ts(source_url: str, external_id: str) -> tuple[str, str]:
    raw = (source_url or external_id or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme == "slack":
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if parsed.netloc == "channels" and len(parts) >= 2:
            return parts[0], parts[1]
    archive = re.search(r"/archives/([^/]+)/p(\d+)", raw)
    if archive:
        compact_ts = archive.group(2)
        if len(compact_ts) > 6:
            return archive.group(1), f"{compact_ts[:-6]}.{compact_ts[-6:]}"
    if ":" in raw:
        channel, ts = raw.split(":", 1)
        if channel and ts:
            return channel, ts
    raise SourceConnectorInputError("Slack source requires slack://channels/{channel_id}/{timestamp}, archive URL, or channel:timestamp.")


def _extract_linear_issue_id(source_url: str, external_id: str) -> str:
    raw = (external_id or source_url or "").strip()
    match = re.search(r"[A-Z][A-Z0-9]+-\d+", raw)
    if match:
        return match.group(0)
    uuid_match = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", raw)
    if uuid_match:
        return uuid_match.group(0)
    raise SourceConnectorInputError("Linear source requires an issue URL, issue identifier, or issue id.")


def _format_linear_issue(issue: dict[str, Any]) -> str:
    identifier = issue.get("identifier") or "Linear"
    title = issue.get("title") or identifier
    state = ((issue.get("state") or {}).get("name") or "").strip()
    labels = [node.get("name", "") for node in ((issue.get("labels") or {}).get("nodes") or []) if node.get("name")]
    lines = [f"# {identifier} {title}", ""]
    if state:
        lines.append(f"State: {state}")
    if labels:
        lines.append(f"Labels: {', '.join(labels)}")
    description = (issue.get("description") or "").strip()
    if description:
        lines.extend(["", description])
    comments = ((issue.get("comments") or {}).get("nodes") or [])
    for comment in comments:
        body = (comment.get("body") or "").strip()
        if body:
            user = ((comment.get("user") or {}).get("name") or "unknown").strip()
            lines.extend(["", f"{user}: {body}"])
    return "\n".join(lines).strip()


class _ReadableTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._skip_depth += 1
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "div", "li", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth:
            self.parts.append(data)


def _html_to_text(value: str) -> str:
    if "<" not in value or ">" not in value:
        return value.strip()
    parser = _ReadableTextParser()
    parser.feed(value)
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def _ensure_extension(value: str, extension: str) -> str:
    clean = value.strip() or f"source.{extension}"
    if Path(clean).suffix:
        return clean
    return f"{clean}.{extension}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9가-힣_-]+", "-", value.strip()).strip("-")
    return slug.lower() or "source"


def _title_from_resource_uri(resource_uri: str) -> str:
    parsed = urlparse(resource_uri)
    candidate = Path(parsed.path).name or parsed.netloc or "mcp-resource"
    return _ensure_extension(candidate, "md")


def _collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
