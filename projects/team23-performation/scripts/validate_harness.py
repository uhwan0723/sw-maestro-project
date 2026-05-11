#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_SKILLS = (
  "performation-orchestrator",
  "performation-venue-data",
  "performation-source-research",
  "performation-trust-review",
  "performation-demo-qa",
)
REQUIRED_FILES = (
  "AGENTS.md",
  "README.md",
  "pyproject.toml",
  ".env.example",
  "docs/project-brief.md",
  "docs/harness/performation/team-spec.md",
  "docs/harness/performation/output-contract.md",
  "docs/harness/performation/scenario-matrix.md",
  "docs/harness/performation/git-policy.md",
  "apps/frontend/src/performation_frontend/app.py",
  "apps/frontend/src/performation_frontend/api.py",
  "apps/backend/src/performation_backend/main.py",
  "packages/agent/src/performation_agent/workflow.py",
  "packages/agent/src/performation_agent/state.py",
  "packages/agent/src/performation_agent/nodes/analyze_input.py",
  "packages/agent/src/performation_agent/nodes/load_venue_data.py",
  "packages/agent/src/performation_agent/nodes/build_search_queries.py",
  "packages/agent/src/performation_agent/nodes/search_public_web.py",
  "packages/agent/src/performation_agent/nodes/infer_venue_from_search.py",
  "packages/agent/src/performation_agent/nodes/infer_event_candidates.py",
  "packages/agent/src/performation_agent/nodes/extract_event_info.py",
  "packages/agent/src/performation_agent/nodes/classify_sources.py",
  "packages/agent/src/performation_agent/nodes/summarize_information.py",
  "packages/agent/src/performation_agent/nodes/assign_confidence.py",
  "packages/agent/src/performation_agent/nodes/format_response.py",
  "packages/agent/src/performation_agent/tools/search.py",
  "packages/agent/src/performation_agent/prompts/input_analysis.md",
  "packages/domain/src/performation_domain/models.py",
  "packages/venue-data/src/performation_venue_data/repository.py",
  "packages/venue-data/src/performation_venue_data/data/venues.json",
  "tests/test_architecture_boundaries.py",
  "tests/test_backend_api.py",
  "tests/test_agent_workflow.py",
  ".agents/skills/harness/SKILL.md",
  ".codex/skills/harness/SKILL.md",
  ".claude/agents/performation-supervisor.md",
  ".claude/agents/performation-source-researcher.md",
  ".claude/agents/performation-trust-reviewer.md",
)


def fail(message: str) -> None:
  print(f"FAIL: {message}")
  raise SystemExit(1)


def read(path: Path) -> str:
  return path.read_text(encoding="utf-8")


def assert_file(relative: str) -> Path:
  path = ROOT / relative
  if not path.exists():
    fail(f"missing required file: {relative}")
  if not path.is_file():
    fail(f"required path is not a file: {relative}")
  return path


def assert_skill_frontmatter(relative: str) -> None:
  path = assert_file(relative)
  content = read(path).lstrip("\ufeff")
  normalized = content.replace("\r\n", "\n").replace("\r", "\n")
  if not normalized.startswith("---\n"):
    fail(f"missing YAML frontmatter: {relative}")
  try:
    _, frontmatter, _ = normalized.split("---", 2)
  except ValueError:
    fail(f"malformed YAML frontmatter: {relative}")
  if "name:" not in frontmatter:
    fail(f"frontmatter missing name: {relative}")
  if "description:" not in frontmatter:
    fail(f"frontmatter missing description: {relative}")


def assert_mentions(path: Path, required_terms: tuple[str, ...]) -> None:
  content = read(path)
  for term in required_terms:
    if term not in content:
      fail(f"{path.relative_to(ROOT)} does not mention required term: {term}")


def assert_not_mentions(path: Path, forbidden_terms: tuple[str, ...]) -> None:
  content = read(path)
  for term in forbidden_terms:
    if term in content:
      fail(f"{path.relative_to(ROOT)} mentions forbidden term: {term}")


def assert_tree_not_mentions(relative: str, forbidden_terms: tuple[str, ...]) -> None:
  root = ROOT / relative
  if not root.exists():
    fail(f"missing required directory: {relative}")
  for path in root.rglob("*.py"):
    assert_not_mentions(path, forbidden_terms)


def main() -> int:
  for relative in REQUIRED_FILES:
    assert_file(relative)

  for skill in PROJECT_SKILLS:
    assert_skill_frontmatter(f".agents/skills/{skill}/SKILL.md")
    codex_path = ROOT / ".codex" / "skills" / skill
    if not codex_path.exists():
      fail(f"missing Codex skill mirror: .codex/skills/{skill}")
    assert_skill_frontmatter(f".codex/skills/{skill}/SKILL.md")

  team_spec = assert_file("docs/harness/performation/team-spec.md")
  assert_mentions(
    team_spec,
    (
      "Supervisor",
      "Producer-Reviewer",
      "official_confirmed",
      "public_review_reference",
      "latest_official_check_required",
      "uncertain",
    ),
  )

  brief = assert_file("docs/project-brief.md")
  assert_mentions(
    brief,
    (
      "KSPO DOME",
      "Blue Square",
      "YES24 Live Hall",
      "FastAPI",
      "Gradio",
      "LangGraph",
      "frontend",
      "backend",
      "agent",
    ),
  )

  git_policy = assert_file("docs/harness/performation/git-policy.md")
  assert_mentions(
    git_policy,
    (
      "feat",
      "fix",
      "test",
      "docs",
      "chore",
      "python3 scripts/validate_harness.py",
      "<type>: <한글 요약>",
    ),
  )

  frontend_app = assert_file("apps/frontend/src/performation_frontend/app.py")
  frontend_api = assert_file("apps/frontend/src/performation_frontend/api.py")
  assert_mentions(frontend_api, ("httpx", "PERFORMATION_API_URL", "/guides"))
  assert_not_mentions(
    frontend_app,
    (
      "performation_agent",
      "performation_venue_data",
      "langgraph",
      "TAVILY_API_KEY",
      "BRAVE_SEARCH_API_KEY",
    ),
  )
  assert_not_mentions(
    frontend_api,
    (
      "performation_agent",
      "performation_venue_data",
      "langgraph",
      "TAVILY_API_KEY",
      "BRAVE_SEARCH_API_KEY",
    ),
  )

  backend_app = assert_file("apps/backend/src/performation_backend/main.py")
  assert_mentions(backend_app, ("FastAPI", "generate_visit_guide", "performation_agent"))

  agent_workflow = assert_file("packages/agent/src/performation_agent/workflow.py")
  assert_mentions(
    agent_workflow,
    (
      "StateGraph",
      "analyze_input",
      "load_venue_data",
      "build_search_queries",
      "search_public_web",
      "infer_venue_from_search",
      "infer_event_candidates",
      "extract_event_info",
      "classify_sources",
      "summarize_information",
      "assign_confidence",
      "format_response",
    ),
  )
  assert_tree_not_mentions("packages/agent/src/performation_agent", ("fastapi", "gradio"))

  print("PASS: Performation harness structure is valid.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
