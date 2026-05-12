import json
import re
from typing import Protocol

from app.models.schemas import KnowledgeCardCreate
from app.services.llm import LLMClient


RULES: tuple[tuple[str, str, str, str], ...] = (
    ("decision", "결정사항", "decided", "high"),
    ("idea", "아이디어", "proposed", "medium"),
    ("idea", "idea", "proposed", "medium"),
    ("hypothesis", "가설", "needs_validation", "medium"),
    ("hypothesis", "hypothesis", "needs_validation", "medium"),
    ("evidence", "근거", "validated", "high"),
    ("evidence", "evidence", "validated", "high"),
    ("risk", "리스크", "needs_validation", "medium"),
    ("risk", "위험", "needs_validation", "medium"),
    ("risk", "risk", "needs_validation", "medium"),
    ("decision", "결정", "decided", "high"),
    ("decision", "decision", "decided", "high"),
    ("problem", "문제점", "proposed", "medium"),
    ("problem", "문제", "proposed", "medium"),
    ("problem", "pain", "proposed", "medium"),
    ("target_user", "타깃", "proposed", "medium"),
    ("target_user", "타겟", "proposed", "medium"),
    ("target_user", "대상 사용자", "proposed", "medium"),
    ("target_user", "target user", "proposed", "medium"),
    ("target_user", "사용자", "proposed", "medium"),
    ("feature", "기능 후보", "proposed", "medium"),
    ("feature", "기능", "proposed", "medium"),
    ("feature", "feature", "proposed", "medium"),
    ("question", "오픈 질문", "needs_review", "low"),
    ("question", "질문", "needs_review", "low"),
    ("question", "open question", "needs_review", "low"),
)

LLM_EXTRACTION_SYSTEM_PROMPT = """
You are the Knowledge Card extraction layer for Ideation Context Hub.
Use three internal stages:
1. filter: ignore greetings, fillers, and chunks without reusable product context.
2. extract: extract only grounded Knowledge Cards from the provided chunk.
3. keyword: assign concise keywords and tags from the same evidence.
Return strict JSON only: {"cards": [{...}]}.
Allowed card_type values: idea, problem, target_user, hypothesis, evidence, decision, risk, feature, question.
Allowed status values: proposed, needs_validation, validated, rejected, decided, needs_review.
Allowed confidence values: low, medium, high.
""".strip()


class CardExtractor(Protocol):
    def extract(
        self,
        chunk: str,
        workspace_id: int,
        source_document_id: int,
        source_chunk_id: int,
    ) -> list[KnowledgeCardCreate]:
        """Extract cards from one stored chunk."""


class DeterministicCardExtractor:
    def extract(
        self,
        chunk: str,
        workspace_id: int,
        source_document_id: int,
        source_chunk_id: int,
    ) -> list[KnowledgeCardCreate]:
        cards: list[KnowledgeCardCreate] = []
        for line in self._candidate_lines(chunk):
            rule = self._match_rule(line)
            if rule is None:
                continue
            card_type, marker, status, confidence = rule
            content = self._strip_marker(line, marker)
            cards.append(
                KnowledgeCardCreate(
                    workspace_id=workspace_id,
                    source_document_id=source_document_id,
                    source_chunk_id=source_chunk_id,
                    card_type=card_type,
                    title=self._title(content),
                    summary=content,
                    evidence_quote=line,
                    keywords=self._keywords(content),
                    tags=[status],
                    status=status,
                    confidence=confidence,
                )
            )

        if cards:
            return cards

        return [
            KnowledgeCardCreate(
                workspace_id=workspace_id,
                source_document_id=source_document_id,
                source_chunk_id=source_chunk_id,
                card_type="question",
                title=self._title(chunk),
                summary=chunk.strip(),
                evidence_quote=chunk.strip(),
                keywords=self._keywords(chunk),
                tags=["needs_review"],
                status="needs_review",
                confidence="low",
            )
        ]

    @staticmethod
    def _candidate_lines(chunk: str) -> list[str]:
        lines: list[str] = []
        pending_heading_marker = ""

        for raw_line in re.split(r"\n+", chunk):
            line = raw_line.strip()
            if not line:
                continue

            heading = DeterministicCardExtractor._heading_text(line)
            if heading:
                rule = DeterministicCardExtractor._match_rule(heading)
                pending_heading_marker = rule[1] if rule else ""
                continue

            for sentence in re.split(r"(?<=[.!?。！？])\s+", line):
                sentence = sentence.strip(" -\t")
                if not sentence:
                    continue
                bare_marker = DeterministicCardExtractor._bare_marker(sentence)
                if bare_marker:
                    pending_heading_marker = bare_marker
                    continue
                if pending_heading_marker and DeterministicCardExtractor._match_rule(sentence) is None:
                    sentence = f"{pending_heading_marker}: {sentence}"
                lines.extend(DeterministicCardExtractor._split_labeled_segments(sentence))
                pending_heading_marker = ""
        return lines

    @staticmethod
    def _match_rule(line: str) -> tuple[str, str, str, str] | None:
        lowered = line.lower()
        for card_type, marker, status, confidence in RULES:
            if re.match(rf"^\s*{re.escape(marker.lower())}\s*[:：-]?", lowered):
                return card_type, marker, status, confidence
        for card_type, marker, status, confidence in RULES:
            if marker.lower() in lowered:
                return card_type, marker, status, confidence
        return None

    @staticmethod
    def _strip_marker(line: str, marker: str) -> str:
        pattern = re.compile(rf"^\s*{re.escape(marker)}\s*[:：-]?\s*", re.IGNORECASE)
        return pattern.sub("", line).strip() or line.strip()

    @staticmethod
    def _title(content: str) -> str:
        title_match = re.match(r"^(.+?[.!?。！？])(?:\s|$)", content.strip())
        title = title_match.group(1).strip() if title_match else content.strip()
        return title[:80] or "검토 필요 카드"

    @staticmethod
    def _keywords(content: str) -> list[str]:
        keywords: list[str] = []
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*|[가-힣]{2,}", content):
            if token not in keywords and token not in {"사용자는", "그리고", "하지만", "있다", "한다"}:
                keywords.append(token)
        return keywords[:8]

    @staticmethod
    def _heading_text(line: str) -> str:
        match = re.match(r"^#{1,6}\s+(.+)$", line.strip())
        return match.group(1).strip() if match else ""

    @staticmethod
    def _split_labeled_segments(line: str) -> list[str]:
        markers = sorted((marker for _, marker, _, _ in RULES), key=len, reverse=True)
        label_pattern = "|".join(re.escape(marker) for marker in markers)
        matches = list(re.finditer(rf"(?i)(?<!\w)({label_pattern})\s*[:：-]", line))
        if len(matches) <= 1:
            return [line]

        segments: list[str] = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
            segment = line[match.start() : end].strip(" -\t")
            if segment:
                segments.append(segment)
        return segments

    @staticmethod
    def _bare_marker(line: str) -> str:
        normalized = line.strip().lower().rstrip(":：-")
        for _, marker, _, _ in RULES:
            if normalized == marker.lower():
                return marker
        return ""


class LLMCardExtractor:
    def __init__(
        self,
        llm_client: LLMClient,
        fallback_extractor: CardExtractor | None = None,
        max_attempts: int = 2,
    ):
        self.llm_client = llm_client
        self.fallback_extractor = fallback_extractor or DeterministicCardExtractor()
        self.max_attempts = max_attempts

    def extract(
        self,
        chunk: str,
        workspace_id: int,
        source_document_id: int,
        source_chunk_id: int,
    ) -> list[KnowledgeCardCreate]:
        user_prompt = self._user_prompt(chunk)
        last_error = ""
        for attempt in range(self.max_attempts):
            prompt = user_prompt
            if last_error:
                prompt = f"{user_prompt}\n\nPrevious JSON/schema error: {last_error}\nReturn corrected JSON only."
            try:
                raw = self.llm_client.complete(LLM_EXTRACTION_SYSTEM_PROMPT, prompt)
            except Exception as error:
                last_error = str(error)
                continue
            if raw is None:
                return self.fallback_extractor.extract(chunk, workspace_id, source_document_id, source_chunk_id)
            try:
                return self._parse_cards(raw, workspace_id, source_document_id, source_chunk_id)
            except (KeyError, json.JSONDecodeError, ValueError) as error:
                last_error = str(error)
                if attempt + 1 >= self.max_attempts:
                    break
        return self._needs_review_card(chunk, workspace_id, source_document_id, source_chunk_id)

    @staticmethod
    def _user_prompt(chunk: str) -> str:
        return f"Chunk:\n{chunk.strip()}\n\nReturn JSON."

    @staticmethod
    def _parse_cards(
        raw: str,
        workspace_id: int,
        source_document_id: int,
        source_chunk_id: int,
    ) -> list[KnowledgeCardCreate]:
        data = json.loads(LLMCardExtractor._json_text(raw))
        raw_cards = data.get("cards")
        if not isinstance(raw_cards, list):
            raise ValueError("cards must be a list")
        cards: list[KnowledgeCardCreate] = []
        for raw_card in raw_cards:
            if not isinstance(raw_card, dict):
                raise ValueError("card item must be an object")
            cards.append(
                KnowledgeCardCreate(
                    workspace_id=workspace_id,
                    source_document_id=source_document_id,
                    source_chunk_id=source_chunk_id,
                    card_type=raw_card["card_type"],
                    title=raw_card["title"],
                    summary=raw_card["summary"],
                    evidence_quote=raw_card["evidence_quote"],
                    keywords=raw_card.get("keywords", []),
                    tags=raw_card.get("tags", []),
                    status=raw_card.get("status", "proposed"),
                    confidence=raw_card.get("confidence", "medium"),
                )
            )
        if not cards:
            raise ValueError("cards cannot be empty")
        return cards

    @staticmethod
    def _json_text(raw: str) -> str:
        text = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        return fenced.group(1).strip() if fenced else text

    @staticmethod
    def _needs_review_card(
        chunk: str,
        workspace_id: int,
        source_document_id: int,
        source_chunk_id: int,
    ) -> list[KnowledgeCardCreate]:
        return [
            KnowledgeCardCreate(
                workspace_id=workspace_id,
                source_document_id=source_document_id,
                source_chunk_id=source_chunk_id,
                card_type="question",
                title=DeterministicCardExtractor._title(chunk),
                summary=chunk.strip(),
                evidence_quote=chunk.strip(),
                keywords=DeterministicCardExtractor._keywords(chunk),
                tags=["needs_review", "llm_parse_failed"],
                status="needs_review",
                confidence="low",
            )
        ]
