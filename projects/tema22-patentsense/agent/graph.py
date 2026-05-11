import os
import json
from pathlib import Path
import numpy as np
from typing import TypedDict, Annotated, Optional

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage
from openai import OpenAI
from dotenv import load_dotenv

from tools.kipris import search_patents_multi
from tools.patent_tools import (
    search_patent_tool,
    get_claim_tool,
    get_representative_image_tool,
    fetch_image_tool,
    embed_query_tool,
    embed_passage_tool,
    PATENT_TOOLS,
)
from agent.prompts import (
    PREPROCESS_PROMPT,
    KEYWORD_EXTRACTION_PROMPT,
    REPORT_GENERATION_PROMPT,
    CONFLICT_ANALYSIS_PROMPT,
    DIFFERENTIATOR_PROMPT,
)

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


# ── State ────────────────────────────────────────────────────────────────────

class PatentState(TypedDict):
    user_idea: str
    processed_idea: str        # LLM 전처리된 기술 중심 표현
    preprocess_detail: dict    # 전처리 세부 내용 (core_technology, tech_components, search_query)
    keywords: list[str]
    patents: list[dict]
    ranked_patents: list[dict]
    report: str
    conflict_points: list[str]
    differentiators: list[dict | str]
    messages: Annotated[list, add_messages]
    error: Optional[str]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _solar_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("SOLAR_API_KEY"),
        base_url="https://api.upstage.ai/v1",
    )


def _chat(messages: list[dict], temperature: float = 0.0) -> str:
    client = _solar_client()
    resp = client.chat.completions.create(
        model="solar-pro",
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content


def _embed(text: str, model: str = "embedding-query") -> list[float]:
    client = _solar_client()
    resp = client.embeddings.create(model=model, input=text)
    return resp.data[0].embedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a, dtype=float), np.array(b, dtype=float)
    norm_a, norm_b = np.linalg.norm(va), np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def _parse_json_object(raw: str) -> dict:
    """LLM이 JSON 앞뒤에 설명/마크다운을 붙여도 최대한 복구한다."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and start < end:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return {}

    return {}


def _fallback_conflicts(ranked: list[dict]) -> list[str]:
    conflicts = []
    for i, patent in enumerate(ranked[:3], 1):
        title = patent.get("title", "유사 특허")
        score = patent.get("similarity_score", 0)
        abstract = (patent.get("abstract", "") or "").strip()
        clue = abstract[:90] + ("..." if len(abstract) > 90 else "")
        conflicts.append(
            f"특허 {i}({title}, 유사도 {score}%)와 핵심 기능 설명이 겹칠 수 있습니다. "
            f"특히 '{clue or title}' 부분을 기준으로 입력 아이디어의 구성/동작 차이를 더 명확히 해야 합니다."
        )
    return conflicts


def _fallback_differentiators(idea: str, ranked: list[dict], conflicts: list[str]) -> list[dict]:
    top_title = ranked[0].get("title", "상위 유사 특허") if ranked else "상위 유사 특허"
    return [
        {
            "title": "사용자 맥락 기반 자동 제어",
            "target_conflict": conflicts[0] if conflicts else "상위 유사 특허와 기능 목적이 유사한 부분",
            "difference_from_prior_art": f"{top_title}가 명시적 명령/기능 수행 중심이라면, 본 아이디어는 사용자의 상황 문장·환경 상태·이전 사용 패턴을 함께 해석해 동작을 결정하는 방향으로 차별화할 수 있습니다.",
            "feature_design": "사용자 입력을 명령어로만 보지 않고 상황 신호로 분류한 뒤, 현재 상태와 결합해 추천 동작을 생성합니다.",
            "implementation_steps": [
                "입력 문장을 명령형/상황형/불명확 입력으로 분류",
                "현재 상태값과 최근 사용 패턴을 상태 객체로 구성",
                "상황형 입력일 때 추천 동작과 조정 강도를 산출",
                "사용자에게 적용 전 확인 또는 즉시 적용 결과를 제공",
            ],
            "user_scenario": "사용자가 '방이 좀 어두워'라고 말하면 시스템이 현재 조도와 과거 선호 밝기를 참고해 조명을 20% 올리는 제안을 반환합니다.",
            "expected_effect": "단순 음성 명령 수행보다 사용자 경험이 자연스러워지고, 기존 특허와 다른 지능형 의사결정 흐름을 강조할 수 있습니다.",
            "remaining_risk": "상황 인식 자체가 기존 특허에 포함되어 있는지 청구항 기준으로 추가 확인해야 합니다.",
        },
        {
            "title": "다중 대상 개별 제어 플로우",
            "target_conflict": conflicts[1] if len(conflicts) > 1 else "제어 대상과 동작 방식이 유사한 부분",
            "difference_from_prior_art": "유사 특허가 단일 대상 또는 일괄 제어 중심이라면, 여러 대상을 동시에 다루되 각 대상별 제어값을 분리해 적용하는 점을 차별점으로 삼을 수 있습니다.",
            "feature_design": "입력에서 대상 목록과 각 대상별 값을 추출해 제어 계획을 만든 뒤, 대상별 실행 결과를 개별적으로 보여줍니다.",
            "implementation_steps": [
                "입력 문장에서 대상 엔티티와 속성값을 추출",
                "대상별 명령 객체를 생성",
                "명령 객체별 실행/실패 상태를 따로 기록",
                "사용자에게 대상별 결과와 재시도 옵션을 표시",
            ],
            "user_scenario": "'거실은 70%, 침실은 30%로 맞춰줘'라고 입력하면 거실/침실을 별도 제어 단위로 처리하고 결과를 각각 표시합니다.",
            "expected_effect": "복합 명령 처리 능력이 생기며, 단순 일괄 제어와 다른 제품 가치를 제시할 수 있습니다.",
            "remaining_risk": "다중 대상 제어가 이미 청구항에 넓게 포함되어 있을 가능성이 있어, 대상별 상태 관리 방식까지 구체화해야 합니다.",
        },
        {
            "title": "실패 원인 안내와 대안 제안",
            "target_conflict": conflicts[2] if len(conflicts) > 2 else "사용자에게 결과만 제공하는 기존 흐름",
            "difference_from_prior_art": "기존 유사 특허가 제어 수행 자체에 초점을 둔다면, 실패/모호한 입력에서 원인을 설명하고 대체 명령을 제안하는 상호작용 흐름으로 차별화할 수 있습니다.",
            "feature_design": "명령 처리 실패 시 실패 유형을 분류하고 사용자가 바로 고칠 수 있는 대안 문장을 제공합니다.",
            "implementation_steps": [
                "실패 케이스를 유형별로 분류",
                "각 실패 유형에 대응하는 사용자 안내 문구 작성",
                "대체 명령 예시를 자동 생성",
                "재입력 없이 버튼/선택지로 수정 실행 가능하게 구성",
            ],
            "user_scenario": "'저쪽 불 꺼줘'처럼 대상이 모호하면 '거실 조명 또는 침실 조명 중 무엇을 끌까요?'처럼 선택지를 제공합니다.",
            "expected_effect": "비전문가도 시스템을 쉽게 사용할 수 있고, 단순 제어 엔진보다 사용성 중심의 차별점을 확보할 수 있습니다.",
            "remaining_risk": "사용자 안내 UI/UX 자체는 특허 차별점으로 약할 수 있어, 실패 유형 분류 로직을 기술적으로 구체화해야 합니다.",
        },
    ]


# ── Nodes ─────────────────────────────────────────────────────────────────────

def preprocess_idea(state: PatentState) -> dict:
    prompt = PREPROCESS_PROMPT.format(idea=state["user_idea"])
    raw = _chat([{"role": "user", "content": prompt}])
    data = _parse_json_object(raw)

    if isinstance(data, dict) and data.get("solution"):
        tech_field = data.get("tech_field", "")
        problem = data.get("problem", "")
        solution = data.get("solution", "")
        effect = data.get("effect", "")
        components = data.get("tech_components", [])

        # 임베딩용: 특허 명세서 구조로 합친 텍스트
        processed = " ".join(filter(None, [tech_field, problem, solution, effect])).strip()
        detail = {
            "tech_field": tech_field,
            "problem": problem,
            "solution": solution,
            "effect": effect,
            "tech_components": components,
        }
    else:
        processed = state["user_idea"]
        detail = {}

    return {"processed_idea": processed, "preprocess_detail": detail}


def extract_keywords(state: PatentState) -> dict:
    idea = state.get("processed_idea") or state["user_idea"]
    prompt = KEYWORD_EXTRACTION_PROMPT.format(idea=idea)
    raw = _chat([{"role": "user", "content": prompt}])

    try:
        data = json.loads(raw)
        keywords = data.get("keywords", []) if isinstance(data, dict) else data
    except json.JSONDecodeError:
        keywords = [k.strip() for k in raw.replace('"', "").split(",") if k.strip()]

    keywords = [k for k in keywords if k][:5]
    return {"keywords": keywords}


def search_patents(state: PatentState) -> dict:
    detail = state.get("preprocess_detail", {})
    tech_components = detail.get("tech_components", [])
    keywords = state.get("keywords", [])

    # 전처리된 tech_components 우선, 없으면 키워드로 폴백
    if tech_components:
        search_terms = tech_components[:5]
    elif keywords:
        search_terms = keywords[:3]
    else:
        return {"patents": [], "error": "검색어 추출에 실패했습니다."}

    try:
        patents = search_patents_multi(search_terms, count_per_keyword=10)
    except RuntimeError as e:
        return {"patents": [], "error": str(e)}

    return {"patents": patents}


def rank_by_similarity(state: PatentState) -> dict:
    patents = state["patents"]
    if not patents:
        return {"ranked_patents": []}

    idea_text = state.get("processed_idea") or state["user_idea"]
    idea_vec = embed_query_tool.invoke(idea_text)

    # 1차: 제목+초록으로 유사도 계산 → Top 15 선정
    ranked = []
    for patent in patents:
        patent_text = f"{patent['title']} {patent['abstract']}".strip()
        if not patent_text:
            continue
        patent_vec = embed_passage_tool.invoke(patent_text)
        score = _cosine_similarity(idea_vec, patent_vec)
        ranked.append({**patent, "similarity_score": round(score * 100, 1)})

    ranked.sort(key=lambda x: x["similarity_score"], reverse=True)
    top15 = ranked[:15]

    # 2차: Top 15 청구항 조회 후 제목+초록+청구항으로 재랭킹
    reranked = []
    for patent in top15:
        claim = get_claim_tool.invoke(patent["application_number"])

        patent_text = " ".join(filter(None, [
            patent.get("title", ""),
            patent.get("abstract", ""),
            claim,
        ])).strip()

        patent_vec = embed_passage_tool.invoke(patent_text)
        score = _cosine_similarity(idea_vec, patent_vec)
        reranked.append({**patent, "similarity_score": round(score * 100, 1), "claim": claim})

    reranked.sort(key=lambda x: x["similarity_score"], reverse=True)
    top5 = reranked[:5]

    # Top 5 대표도면 조회 (실패해도 진행)
    for p in top5:
        img_info = get_representative_image_tool.invoke(p["application_number"])
        small_url = img_info.get("path", "")
        large_url = img_info.get("large_path", "") or small_url
        p["image_data"] = fetch_image_tool.invoke(small_url) if small_url else ""
        p["image_url_large"] = large_url

    return {"ranked_patents": top5}


_STATUS_BADGE = {
    "등록": "✅ 등록",
    "공개": "📂 공개",
    "거절": "❌ 거절",
    "말소": "🗑️ 말소",
    "취하": "🚫 취하",
    "포기": "⛔ 포기",
    "심사중": "⏳ 심사중",
    "소멸": "💤 소멸",
}


def _format_applicants(raw: str) -> str:
    """KIPRIS는 출원인이 여러명이면 '|'로 구분. 콤마 표기로 변환."""
    if not raw:
        return "-"
    return ", ".join(part.strip() for part in raw.split("|") if part.strip())


def _format_status(raw: str) -> str:
    if not raw:
        return "-"
    return _STATUS_BADGE.get(raw.strip(), raw.strip())


def analyze_conflicts(state: PatentState) -> dict:
    ranked = state["ranked_patents"]
    if not ranked:
        return {"conflict_points": []}

    patent_lines = []
    for i, p in enumerate(ranked[:5], 1):
        patent_lines.append(
            f"{i}. {p['title']} | 유사도 {p['similarity_score']}% | 초록: {p.get('abstract','')}"
        )

    prompt = CONFLICT_ANALYSIS_PROMPT.format(
        idea=state["user_idea"],
        patents="\n".join(patent_lines),
    )

    raw = _chat([{"role": "user", "content": prompt}], temperature=0.1)
    data = _parse_json_object(raw)
    conflicts = data.get("conflicts", []) if isinstance(data, dict) else []
    conflicts = [c.strip() for c in conflicts if isinstance(c, str) and c.strip()][:5]

    if not conflicts:
        conflicts = _fallback_conflicts(ranked)

    return {"conflict_points": conflicts}


def derive_differentiators(state: PatentState) -> dict:
    conflicts = state.get("conflict_points", [])
    ranked = state.get("ranked_patents", [])
    if not conflicts:
        return {"differentiators": []}

    patent_lines = []
    for i, p in enumerate(ranked[:5], 1):
        patent_lines.append(
            f"특허 {i}: {p.get('title', '')} | 유사도 {p.get('similarity_score', 0)}% | "
            f"출원번호 {p.get('application_number', '-')} | 초록: {p.get('abstract', '')}"
        )

    prompt = DIFFERENTIATOR_PROMPT.format(
        idea=state["user_idea"],
        patents="\n".join(patent_lines),
        conflicts="\n".join(f"- {c}" for c in conflicts),
    )

    raw = _chat([{"role": "user", "content": prompt}], temperature=0.25)
    data = _parse_json_object(raw)
    differentiators = data.get("differentiators", []) if isinstance(data, dict) else []

    cleaned = []
    for item in differentiators[:5]:
        if isinstance(item, dict):
            cleaned.append({
                "title": str(item.get("title", "")).strip(),
                "target_conflict": str(item.get("target_conflict", "")).strip(),
                "difference_from_prior_art": str(item.get("difference_from_prior_art", "")).strip(),
                "feature_design": str(item.get("feature_design", "")).strip(),
                "implementation_steps": [str(s).strip() for s in item.get("implementation_steps", []) if str(s).strip()][:5],
                "user_scenario": str(item.get("user_scenario", "")).strip(),
                "expected_effect": str(item.get("expected_effect", "")).strip(),
                "remaining_risk": str(item.get("remaining_risk", "")).strip(),
            })
        elif isinstance(item, str) and item.strip():
            cleaned.append(item.strip())

    if not cleaned:
        cleaned = _fallback_differentiators(state["user_idea"], ranked, conflicts)

    return {"differentiators": cleaned}


def generate_report(state: PatentState) -> dict:
    ranked = state["ranked_patents"]

    if not ranked:
        msg = "유사 특허를 찾지 못했습니다. 키워드를 더 구체적으로 입력해 주세요."
        return {"report": msg, "messages": [AIMessage(content=msg)]}

    patent_lines = []
    patent_table_rows = []
    detail_blocks = []

    for i, p in enumerate(ranked, 1):
        score = p["similarity_score"]
        grade = "🔴 높음" if score >= 70 else ("🟡 중간" if score >= 40 else "🟢 낮음")
        applicants = _format_applicants(p.get("applicant", ""))
        status = _format_status(p.get("register_status", ""))
        abstract = p.get("abstract", "") or "(초록 없음)"
        abstract_preview = abstract[:150] + "..." if len(abstract) > 150 else abstract

        patent_lines.append(
            f"{i}. [{score}%] {p['title']}\n"
            f"   출원번호: {p['application_number']} | 출원인: {applicants} | 상태: {status}\n"
            f"   요약: {abstract_preview}"
        )
        patent_table_rows.append(
            f"| {i} | {score}% {grade} | {status} | {p['title']} | {p['application_number']} | {applicants} |"
        )

        # 대표도면 (lightbox)
        image_data = p.get("image_data", "")
        image_url_large = p.get("image_url_large", "")
        if image_data:
            modal_id = f"lb{p['application_number']}"
            if image_url_large:
                image_html = (
                    f'<p>'
                    f'<a class="lb-thumb-link" href="#{modal_id}">'
                    f'<img class="lb-thumb" src="{image_data}" alt="대표도면" '
                    f'style="max-width:320px; max-height:320px; border:1px solid #ddd; '
                    f'padding:6px; background:#fff;"/>'
                    f'</a>'
                    f'<br/><small style="color:#666;">🔍 이미지 클릭 시 큰 화면으로 보기</small>'
                    f'</p>\n'
                    f'<div id="{modal_id}" class="lb-overlay">'
                    f'<a href="#_" class="lb-backdrop"></a>'
                    f'<div class="lb-content">'
                    f'<a href="#_" class="lb-close" title="닫기">×</a>'
                    f'<img src="{image_url_large}" alt="대표도면 확대"/>'
                    f'</div>'
                    f'</div>\n'
                )
            else:
                image_html = (
                    f'<p><img src="{image_data}" alt="대표도면" '
                    f'style="max-width:320px; max-height:320px; border:1px solid #ddd; '
                    f'padding:6px; background:#fff;"/></p>\n'
                )
        else:
            image_html = ""

        detail_blocks.append(
            f"<details>\n"
            f"<summary><b>{i}. [{score}%] {p['title']}</b> &nbsp;|&nbsp; {status} &nbsp;|&nbsp; {applicants}</summary>\n\n"
            f"<div class='detail-inner'>\n"
            f"{image_html}"
            f"<blockquote>\n"
            f"<b>출원번호</b>: <code>{p['application_number']}</code><br>\n"
            f"<b>IPC</b>: <code>{p.get('ipc_code', '-')}</code><br>\n"
            f"<b>공개일</b>: {p.get('open_date', '-')}\n"
            f"</blockquote>\n\n"
            f"<b>📄 초록</b>\n\n{abstract}\n"
            f"</div>\n"
            f"</details>"
        )

    patent_table = (
        "| # | 유사도 | 상태 | 발명 명칭 | 출원번호 | 출원인 |\n"
        "|---|--------|------|----------|---------|--------|\n"
        + "\n".join(patent_table_rows)
    )

    conflict_points = state.get("conflict_points", [])
    differentiators = state.get("differentiators", [])

    conflict_section = "\n".join(f"- {c}" for c in conflict_points) if conflict_points else "- 분석 가능한 충돌 요소를 충분히 추출하지 못했습니다."

    if differentiators:
        diff_lines = []
        for i, item in enumerate(differentiators, 1):
            if isinstance(item, dict):
                steps = item.get("implementation_steps", [])
                step_lines = "\n".join(f"  {idx}. {step}" for idx, step in enumerate(steps, 1)) or "  -"
                diff_lines.append(
                    f"#### {i}. {item.get('title') or '차별점'}\n"
                    f"- **대응하는 충돌 요소**: {item.get('target_conflict') or '-'}\n"
                    f"- **기존 유사 특허와 다른 점**: {item.get('difference_from_prior_art') or '-'}\n"
                    f"- **기능 설계안**: {item.get('feature_design') or '-'}\n"
                    f"- **MVP 구현 단계**:\n{step_lines}\n"
                    f"- **사용 시나리오**: {item.get('user_scenario') or '-'}\n"
                    f"- **기대 효과**: {item.get('expected_effect') or '-'}\n"
                    f"- **남는 리스크/확인 필요 지점**: {item.get('remaining_risk') or '-'}"
                )
            else:
                diff_lines.append(f"- {item}")
        diff_section = "\n\n".join(diff_lines)
    else:
        diff_section = "- 차별점 도출을 위해 입력을 조금 더 구체화해 주세요."

    # LLM 리포트 (섹션 1~4)
    prompt = REPORT_GENERATION_PROMPT.format(
        idea=state["user_idea"],
        patents="\n\n".join(patent_lines),
        patent_table=patent_table,
        conflicts=conflict_section,
    )
    llm_report = _chat([{"role": "user", "content": prompt}], temperature=0.3)

    # 전처리 결과 섹션
    detail = state.get("preprocess_detail", {})
    if detail:
        components = ", ".join(detail.get("tech_components", []))
        preprocess_section = (
            f"### 🔍 AI 기술 분석\n"
            f"| 항목 | 내용 |\n"
            f"|------|------|\n"
            f"| 🔬 기술 분야 | {detail.get('tech_field', '-')} |\n"
            f"| ⚠️ 해결 과제 | {detail.get('problem', '-')} |\n"
            f"| 💡 해결 수단 | {detail.get('solution', '-')} |\n"
            f"| ✅ 기대 효과 | {detail.get('effect', '-')} |\n"
            f"| 🔧 검색 키워드 | {components} |\n\n"
        )
    else:
        preprocess_section = ""

    report = (
        f"{preprocess_section}"
        f"{llm_report}\n\n"
        f"<!-- CARD_BREAK -->\n\n"
        f"### 5) 확보 가능한 차별점\n{diff_section}\n\n"
        f"### 6) 다음 행동 제안\n"
        f"- 위 차별점 중 구현 난이도가 낮고 기존 특허와 기술적 거리가 큰 항목을 1~2개 선택해 MVP 기능으로 구체화하세요.\n"
        f"- 선택한 차별점마다 입력 데이터, 처리 로직, 출력 결과를 한 문장씩 더 좁혀보세요.\n"
        f"- 상위 유사 특허의 청구항을 확인해 여전히 겹치는 구성요소가 있는지 전문가 검토를 받으세요.\n\n"
        f"---\n"
        f"⚠️ *본 분석은 참고용이며, 최종 법적 판단은 반드시 변리사/전문가와 상담하세요.*\n\n"
        f"<!-- CARD_BREAK -->\n\n"
        f"### 📋 유사 특허 상세 (클릭하여 초록 펼치기)\n\n"
        + "\n\n".join(detail_blocks)
    )

    return {"report": report, "messages": [AIMessage(content=report)]}


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(PatentState)

    g.add_node("preprocess_idea", preprocess_idea)
    g.add_node("extract_keywords", extract_keywords)
    g.add_node("search_patents", search_patents)
    g.add_node("rank_by_similarity", rank_by_similarity)
    g.add_node("analyze_conflicts", analyze_conflicts)
    g.add_node("derive_differentiators", derive_differentiators)
    g.add_node("generate_report", generate_report)

    g.set_entry_point("preprocess_idea")
    g.add_edge("preprocess_idea", "extract_keywords")
    g.add_edge("extract_keywords", "search_patents")
    g.add_edge("search_patents", "rank_by_similarity")
    g.add_edge("rank_by_similarity", "analyze_conflicts")
    g.add_edge("analyze_conflicts", "derive_differentiators")
    g.add_edge("derive_differentiators", "generate_report")
    g.add_edge("generate_report", END)

    return g.compile()


agent = build_graph()
