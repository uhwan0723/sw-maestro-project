from __future__ import annotations

import os
import uuid

import gradio as gr
from performation_domain import (
    EventCandidate,
    EventInfo,
    GuideResponse,
)

from performation_frontend.api import PerformationAPIError, get_guide
from performation_frontend.styles import CSS


def request_guide(query: str) -> str:
    query = query.strip()
    if not query:
        return "공연명 또는 공연장명을 입력해주세요."

    try:
        data = get_guide(query)
    except PerformationAPIError as exc:
        return str(exc)

    return render_guide_markdown(data)


def render_guide_markdown(guide: GuideResponse) -> str:
    venue = guide.venue
    event_info = guide.event_info
    candidates = guide.event_candidates
    sources = guide.sources

    sections = [
        "# 공연 관람 준비 가이드",
        "",
        "## 공연장 기본 정보",
    ]

    if venue:
        sections.extend(
            [
                f"- 공연장: {venue.name}",
                f"- 주소: {venue.address or '확인 필요'}",
                f"- 가까운 역: {venue.nearest_station or '확인 필요'}",
            ]
        )
    else:
        sections.append("- 공연장: 지원 범위 밖 또는 확인 필요")

    sections.extend(
        [
            "",
            *render_event_info_section(event_info),
            "",
            "## 관람 전 핵심 요약",
            *[f"- {item}" for item in guide.summary],
            "",
            *render_candidate_section(candidates),
            "",
            "## 준비물 체크리스트",
            *[f"- {item}" for item in guide.checklist],
            "",
            "## 교통 및 입장 팁",
            *[f"- {item}" for item in guide.transit_and_entry_tips],
            "",
            "## 공식 확인 필요 항목",
            *[f"- {item}" for item in guide.official_check_required],
            "",
            "## 참고 출처",
            *[
                f"- {source.title or '출처'} ({source.source_type.value}): {source.url}"
                for source in sources
            ],
            "",
            "## 신뢰도 메모",
            *[f"- {item}" for item in guide.confidence_notes],
        ]
    )

    return "\n".join(sections)


def render_event_info_section(event_info: EventInfo | None) -> list[str]:
    if not event_info:
        return []
    rows = [
        ("공연명", event_info.title),
        ("날짜", event_info.date_text),
        ("시간", event_info.time_text),
        ("장소", event_info.venue_name),
        (
            "신뢰도",
            event_info.confidence_label.value if event_info.confidence_label else "",
        ),
    ]
    lines = ["## 공연 정보"]
    lines.extend(f"- {label}: {value}" for label, value in rows if value)
    return lines


def render_candidate_section(candidates: list[EventCandidate]) -> list[str]:
    if not candidates:
        return []
    lines = ["## 공연 후보"]
    for candidate in candidates:
        meta = " / ".join(
            item
            for item in (
                candidate.region,
                candidate.date_text,
                candidate.venue_name,
            )
            if item
        )
        label = candidate.name or "후보"
        confidence = (
            candidate.confidence_label.value if candidate.confidence_label else ""
        )
        suffix = f" - {meta}" if meta else ""
        lines.append(f"- {label}{suffix} ({confidence})")
    return lines


def on_submit(
    query: str,
    chat_history: list[dict[str, str]],
    session_data: dict[str, dict],
    session_id: str | None,
):
    query = query.strip()
    if not query:
        return "", chat_history, session_data, session_id, gr.update()

    if session_id is None:
        session_id = str(uuid.uuid4())
        session_data[session_id] = {"title": query[:20], "history": []}

    response_md = request_guide(query)

    chat_history.append({"role": "user", "content": query})
    chat_history.append({"role": "assistant", "content": response_md})

    session_data[session_id]["history"] = chat_history

    choices = [
        (data["title"], sid) for sid, data in reversed(list(session_data.items()))
    ]

    return (
        "",
        chat_history,
        session_data,
        session_id,
        gr.update(choices=choices, value=session_id),
    )


def load_session(session_id: str | None, session_data: dict[str, dict]):
    if session_id in session_data:
        return session_data[session_id]["history"], session_id
    return [], session_id


def start_new_chat():
    return [], None, gr.update(value=None)


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Performation", fill_height=True) as demo:
        # State: { "session_id": { "title": str, "history": list } }
        sessions = gr.State({})
        current_session_id = gr.State(None)

        with gr.Sidebar():
            gr.Markdown("### 가이드 기록")
            new_chat_btn = gr.Button("새 채팅", variant="secondary")
            history_list = gr.Radio(
                choices=[],
                label=None,
                show_label=False,
                elem_id="history-list",
                interactive=True,
            )

        with gr.Column():
            gr.Markdown("# Performation")
            chatbot = gr.Chatbot(
                scale=1,
            )

            with gr.Row():
                query_input = gr.Textbox(
                    placeholder="공연명 또는 공연장명을 입력하세요 (예: KSPO DOME 콘서트)",
                    container=False,
                    scale=7,
                )
                submit_btn = gr.Button("가이드 생성", variant="primary", scale=1)

        submit_btn.click(
            fn=on_submit,
            inputs=[query_input, chatbot, sessions, current_session_id],
            outputs=[query_input, chatbot, sessions, current_session_id, history_list],
        )
        query_input.submit(
            fn=on_submit,
            inputs=[query_input, chatbot, sessions, current_session_id],
            outputs=[query_input, chatbot, sessions, current_session_id, history_list],
        )

        history_list.change(
            fn=load_session,
            inputs=[history_list, sessions],
            outputs=[chatbot, current_session_id],
        )

        new_chat_btn.click(
            fn=start_new_chat,
            outputs=[chatbot, current_session_id, history_list],
        )

    return demo


def launch_app() -> None:
    server_name = os.getenv("GRADIO_SERVER_NAME") or "127.0.0.1"
    server_port = int(os.getenv("GRADIO_SERVER_PORT") or "7860")
    build_app().launch(server_name=server_name, server_port=server_port, css=CSS)


if __name__ == "__main__":
    launch_app()
