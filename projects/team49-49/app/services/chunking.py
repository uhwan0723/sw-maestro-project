import re


VALUABLE_PATTERNS = (
    "아이디어",
    "가설",
    "근거",
    "결정",
    "리스크",
    "위험",
    "문제",
    "타깃",
    "사용자",
    "기능",
    "질문",
    "검증",
    "멘토",
    "인터뷰",
    "피드백",
    "idea",
    "hypothesis",
    "evidence",
    "decision",
    "risk",
    "problem",
    "feature",
)

LOW_VALUE_PATTERNS = ("ㅋㅋ", "ㅎㅎ", "감사", "좋아요", "네", "음", "어", "맞아요")


def chunk_text(text: str, max_chars: int = 900) -> list[str]:
    paragraphs = _planning_paragraphs(text)
    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        current = ""
        for sentence in re.split(r"(?<=[.!?。！？])\s+|\n+", paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            if current and len(current) + len(sentence) + 1 > max_chars:
                chunks.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            chunks.append(current)
    return chunks


def filter_reusable_chunks(chunks: list[str]) -> list[str]:
    reusable: list[str] = []
    for chunk in chunks:
        normalized = chunk.strip().lower()
        if len(normalized) < 12:
            continue
        if any(pattern in normalized for pattern in LOW_VALUE_PATTERNS) and not any(
            pattern in normalized for pattern in VALUABLE_PATTERNS
        ):
            continue
        if any(pattern in normalized for pattern in VALUABLE_PATTERNS):
            reusable.append(chunk)
    return reusable


def _planning_paragraphs(text: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if block.strip()]
    paragraphs: list[str] = []
    heading_context: list[str] = []

    for block in blocks:
        heading = _markdown_heading(block)
        if heading:
            heading_context = [*heading_context, heading][-2:]
            continue

        paragraph = block
        if heading_context:
            paragraph = "\n".join([*heading_context, paragraph])
        paragraphs.append(paragraph)

    return paragraphs


def _markdown_heading(block: str) -> str:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) != 1:
        return ""
    match = re.match(r"^#{1,6}\s+(.+)$", lines[0])
    return match.group(1).strip() if match else ""
