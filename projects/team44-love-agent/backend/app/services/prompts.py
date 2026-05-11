from __future__ import annotations

import os
import re
from pathlib import Path

from app.schemas.consultation import AGENT_NAMES, AgentId


class PromptRegistry:
    """Loads markdown prompt guidance without making the backend depend on Git."""

    def __init__(self, prompt_dir: Path | str | None = None) -> None:
        self.prompt_dir = self._resolve_prompt_dir(prompt_dir)

    def supervisor_prompt(self, stage: str) -> str:
        content = self._read("supervisor.md")
        headings = {
            "analysis": "1단계",
            "summary_1": "2단계",
            "classify_2": "3단계",
        }
        return self._extract_section(content, headings[stage]) or content

    def agent_round_prompt(self, agent_id: AgentId, round_number: int) -> str:
        agent_content = self._read("relationship_agents.md")
        round_content = self._read("round_prompts.md")
        agent_section = self._extract_section(agent_content, AGENT_NAMES[agent_id]) or agent_content
        round_section = self._extract_section(round_content, f"{round_number}라운드") or round_content
        return "\n\n".join(part for part in [agent_section, round_section] if part)

    def final_summary_prompt(self) -> str:
        return self._read("final_summary.md")

    def _read(self, filename: str) -> str:
        if self.prompt_dir is None:
            return ""
        path = self.prompt_dir / filename
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8-sig").strip()

    @staticmethod
    def _extract_section(content: str, heading_fragment: str) -> str:
        if not content:
            return ""
        pattern = re.compile(
            rf"^##\s+.*{re.escape(heading_fragment)}.*$",
            flags=re.MULTILINE,
        )
        match = pattern.search(content)
        if match is None:
            return ""
        next_heading = re.search(r"^##\s+", content[match.end() :], flags=re.MULTILINE)
        end = match.end() + next_heading.start() if next_heading else len(content)
        return content[match.start() : end].strip()

    @staticmethod
    def _resolve_prompt_dir(prompt_dir: Path | str | None) -> Path | None:
        candidates: list[Path] = []
        if prompt_dir is not None:
            candidates.append(Path(prompt_dir))
        env_dir = os.getenv("PROMPT_DIR")
        if env_dir:
            candidates.append(Path(env_dir))

        cwd = Path.cwd()
        candidates.extend(
            [
                cwd / "agents" / "prompts",
                cwd.parent / "agents" / "prompts",
            ]
        )

        current = Path(__file__).resolve()
        for parent in current.parents:
            candidates.append(parent / "agents" / "prompts")

        for candidate in candidates:
            if (candidate / "supervisor.md").exists():
                return candidate
        return None

