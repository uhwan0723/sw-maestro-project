"""리마인더 생성 — LLM 기반 타이밍 + 룰 기반 폴백"""

import json
from datetime import datetime, timedelta

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_upstage import ChatUpstage

load_dotenv()

_llm = ChatUpstage(model="solar-pro2", temperature=0)

CATEGORY_META = {
    "면접": {"emoji": "📋", "tip": "서류·복장을 미리 점검하세요."},
    "시험": {"emoji": "📚", "tip": "컨디션 관리와 복습 잊지 마세요!"},
    "약속": {"emoji": "🤝", "tip": "장소와 시간을 다시 한번 확인하세요."},
    "마감": {"emoji": "⏰", "tip": "제출 전 최종 검토를 해보세요."},
    "기타": {"emoji": "📅", "tip": ""},
}

SYSTEM_PROMPT = """당신은 일정 리마인더 타이밍 전문가입니다.
일정 정보를 받아 적절한 리마인더 시점과 준비 팁을 생성합니다.

규칙:
- 일정의 중요도와 필요한 준비 시간을 고려해 리마인더 개수와 타이밍을 결정하세요
- 리마인더는 1~4개 사이로 생성하세요
- 각 remind_at은 반드시 현재 시각 이후, 일정 시작 시각 이전이어야 합니다
- remind_at은 ISO 8601 형식 (예: "2025-06-13T09:00:00")
- tip은 해당 시점에 맞는 실용적인 준비 조언 한 줄 (한국어)

반드시 다음 JSON 형식으로만 답하세요. 다른 텍스트 절대 포함 금지:
{"reminders": [{"remind_at": "2025-06-13T09:00:00", "tip": "서류와 복장을 미리 점검하세요."}, ...]}"""


def _parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _at_time(base: datetime, hour: int, minute: int = 0) -> datetime:
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _is_future(remind_at: datetime, now: datetime) -> bool:
    if remind_at.tzinfo and now.tzinfo is None:
        now = now.astimezone(remind_at.tzinfo)
    elif remind_at.tzinfo is None and now.tzinfo:
        now = now.replace(tzinfo=None)
    return remind_at > now


def _dday_label(remind_at: datetime, start: datetime) -> str:
    delta = (start.date() - remind_at.date()).days
    if delta == 0:
        return "D-Day"
    return f"D-{delta}"


def _format_start(start: datetime) -> str:
    weekdays = "월화수목금토일"
    wd = weekdays[start.weekday()]
    hour, minute = start.hour, start.minute
    period = "오전" if hour < 12 else "오후"
    h = hour % 12 or 12
    time_str = f"{h}:{minute:02d}" if minute else f"{h}시"
    return f"{start.month}월 {start.day}일({wd}) {period} {time_str}"


def _build_message(title: str, category: str, start: datetime, remind_at: datetime, tip: str) -> str:
    meta = CATEGORY_META.get(category, CATEGORY_META["기타"])
    dday = _dday_label(remind_at, start)
    formatted = _format_start(start)
    tip_line = f"\n{tip}" if tip else ""
    return f"{meta['emoji']} {dday} | {title}\n일시: {formatted}{tip_line}"


def _generate_llm(event: dict, start: datetime, now: datetime) -> list[dict] | None:
    """LLM으로 리마인더 타이밍과 팁 생성. 실패 시 None 반환."""
    prompt = (
        f"현재 시각: {now.isoformat()}\n"
        f"일정 제목: {event['title']}\n"
        f"일정 설명: {event.get('description', '(없음)')}\n"
        f"카테고리: {event.get('category', '기타')}\n"
        f"시작 시각: {event['start_time']}"
    )
    try:
        response = _llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data = json.loads(raw)
        llm_reminders = data.get("reminders", [])
        if not llm_reminders:
            return None

        result = []
        for r in llm_reminders:
            remind_at = _parse_datetime(r["remind_at"])
            if not _is_future(remind_at, now) or remind_at >= start:
                continue
            result.append({"remind_at": remind_at, "tip": r.get("tip", "")})
        return result if result else None
    except Exception as exc:
        print(f"[reminder] LLM 생성 실패, 룰 기반 폴백: {exc}")
        return None


def _generate_rules(event: dict, start: datetime, now: datetime) -> list[dict]:
    """룰 기반 폴백."""
    category = event.get("category") or "기타"
    tip = CATEGORY_META.get(category, CATEGORY_META["기타"])["tip"]

    rules = {
        "면접": [
            _at_time(start - timedelta(days=2), 9),
            _at_time(start - timedelta(days=1), 20),
            _at_time(start, 8),
        ],
        "시험": [
            _at_time(start - timedelta(days=3), 9),
            _at_time(start - timedelta(days=1), 20),
            _at_time(start, 8),
        ],
        "약속": [start - timedelta(hours=2)],
        "마감": [
            _at_time(start - timedelta(days=1), 9),
            _at_time(start, 9),
        ],
        "기타": [start - timedelta(hours=1)],
    }

    result = []
    for remind_at in rules.get(category, rules["기타"]):
        if _is_future(remind_at, now):
            result.append({"remind_at": remind_at, "tip": tip})
    return result


def generate_reminders(event: dict) -> list[dict]:
    """LLM 기반 리마인더 생성, 실패 시 룰 기반 폴백."""
    start = _parse_datetime(event["start_time"])
    now = datetime.now(start.tzinfo) if start.tzinfo else datetime.now()
    title = event["title"]
    category = event.get("category") or "기타"

    timings = _generate_llm(event, start, now)
    if timings is None:
        timings = _generate_rules(event, start, now)

    reminders = []
    for t in timings:
        reminders.append({
            "event_id": event["id"],
            "remind_at": t["remind_at"].isoformat(),
            "message": _build_message(title, category, start, t["remind_at"], t["tip"]),
            "is_sent": 0,
            "created_by": "ai",
        })

    return reminders
