import json

import streamlit as st
from pydantic import ValidationError
from streamlit_local_storage import LocalStorage

from app.api_client import BackendError, check_health, fetch_briefing
from app.components.briefing_view import render_briefing
from app.constants import CATEGORY_OPTIONS, CITY_OPTIONS, DEFAULT_LENGTH
from app.mock_data import make_mock_briefing
from app.schemas import BriefingRequest, BriefingResponse

LOCAL_STORAGE_KEY = "morning_briefing_settings"

MOCK_SCENARIOS = {
    "정상": "normal",
    "날씨 실패": "no_weather",
    "뉴스 실패": "no_news",
    "둘 다 실패": "all_failed",
    "LLM 실패": "llm_fail",
}


def _load_saved_settings(local_storage: LocalStorage) -> dict | None:
    raw = local_storage.getItem(LOCAL_STORAGE_KEY)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _save_settings(
    local_storage: LocalStorage, location: str, categories: list[str]
) -> None:
    payload = json.dumps(
        {"location": location, "categories": categories},
        ensure_ascii=False,
    )
    local_storage.setItem(LOCAL_STORAGE_KEY, payload)


def _resolve_defaults(saved: dict | None) -> tuple[str, list[str]]:
    settings = saved or {}
    location = settings.get("location") or CITY_OPTIONS[0]
    if location not in CITY_OPTIONS:
        location = CITY_OPTIONS[0]
    categories = [c for c in settings.get("categories", []) if c in CATEGORY_OPTIONS]
    if not categories:
        categories = ["IT"]
    return location, categories


def _build_briefing(
    req: BriefingRequest, *, use_mock: bool, mock_scenario: str
) -> BriefingResponse:
    if use_mock:
        return make_mock_briefing(req, scenario=mock_scenario)
    return fetch_briefing(req)


def _run_briefing(
    req: BriefingRequest, *, use_mock: bool, mock_scenario: str, spinner_text: str
) -> None:
    """브리핑을 호출해 session_state에 결과를 저장한다. 마지막 요청도 함께 보존."""
    with st.spinner(spinner_text):
        try:
            st.session_state.briefing = _build_briefing(
                req, use_mock=use_mock, mock_scenario=mock_scenario
            )
            st.session_state.error = None
            st.session_state.last_request = req
        except BackendError as exc:
            st.session_state.briefing = None
            st.session_state.error = str(exc)


st.set_page_config(page_title="☀️ 모닝 브리핑", page_icon="☀️", layout="wide")

st.markdown("# ☀️ 모닝 브리핑")
st.caption("일어나서 한 번, 오늘 입을 옷 · 우산 여부 · 꼭 알아야 할 뉴스를 한 화면에.")

local_storage = LocalStorage()
saved = _load_saved_settings(local_storage)
default_location, default_categories = _resolve_defaults(saved)

with st.sidebar:
    st.subheader("개발 모드")
    use_mock = st.toggle(
        "Mock 응답 사용",
        value=True,
        help="백엔드/에이전트 미완성 동안 가짜 응답으로 화면 개발",
    )
    mock_scenario_label = "정상"
    if use_mock:
        mock_scenario_label = st.selectbox(
            "Mock 시나리오",
            list(MOCK_SCENARIOS.keys()),
            index=0,
        )
    else:
        if check_health():
            st.success("연결됨")
        else:
            st.error("연결 실패")

    st.divider()

    st.subheader("설정")
    if saved:
        st.caption("저장된 설정을 불러왔습니다.")
    with st.form("settings"):
        location = st.selectbox(
            "위치", CITY_OPTIONS, index=CITY_OPTIONS.index(default_location)
        )
        categories = st.multiselect(
            "관심 카테고리 (1~5개)",
            CATEGORY_OPTIONS,
            default=default_categories,
            max_selections=5,
        )
        submitted = st.form_submit_button("브리핑 생성", use_container_width=True)

    if saved and st.button(
        "설정 초기화",
        use_container_width=True,
        help="저장된 위치/카테고리를 지우고 첫 방문 상태로 돌아갑니다.",
    ):
        local_storage.deleteItem(LOCAL_STORAGE_KEY)
        for key in ("briefing", "error", "last_request", "_auto_called"):
            st.session_state.pop(key, None)
        st.rerun()

    if submitted:
        if not categories:
            st.warning("카테고리를 1개 이상 선택해 주세요.")
        else:
            try:
                req = BriefingRequest(
                    location=location,
                    categories=categories,
                    length=DEFAULT_LENGTH,
                )
            except ValidationError as exc:
                st.session_state.briefing = None
                st.session_state.error = f"입력 검증 실패: {exc}"
            else:
                _save_settings(local_storage, location, categories)
                _run_briefing(
                    req,
                    use_mock=use_mock,
                    mock_scenario=MOCK_SCENARIOS[mock_scenario_label],
                    spinner_text="브리핑을 만들고 있습니다…",
                )

# 저장된 설정이 있으면 페이지 진입 시 자동으로 한 번 호출 (기획서 §3 자동 생성)
auto_call_eligible = (
    saved is not None
    and not submitted
    and st.session_state.get("briefing") is None
    and st.session_state.get("error") is None
    and not st.session_state.get("_auto_called", False)
)
if auto_call_eligible:
    st.session_state._auto_called = True
    try:
        auto_req = BriefingRequest(
            location=default_location,
            categories=default_categories,
            length=DEFAULT_LENGTH,
        )
    except ValidationError as exc:
        st.session_state.error = f"저장된 설정이 유효하지 않습니다: {exc}"
    else:
        _run_briefing(
            auto_req,
            use_mock=use_mock,
            mock_scenario=MOCK_SCENARIOS[mock_scenario_label],
            spinner_text="저장된 설정으로 브리핑을 불러오고 있습니다…",
        )

if st.session_state.get("error"):
    st.error(st.session_state.error)

briefing = st.session_state.get("briefing")
if briefing is None:
    if saved is None:
        st.info(
            "처음 방문하셨습니다. 사이드바에서 설정을 입력하고 '브리핑 생성'을 눌러 주세요."
        )
    else:
        st.info("'브리핑 생성'을 눌러 주세요.")
else:
    spacer, refresh_col = st.columns([5, 1])
    with refresh_col:
        last_req: BriefingRequest | None = st.session_state.get("last_request")
        if st.button(
            "다시 생성",
            use_container_width=True,
            disabled=last_req is None,
            help="같은 설정으로 즉시 재호출합니다.",
        ) and last_req is not None:
            _run_briefing(
                last_req,
                use_mock=use_mock,
                mock_scenario=MOCK_SCENARIOS[mock_scenario_label],
                spinner_text="다시 생성하고 있습니다…",
            )
            st.rerun()
    render_briefing(briefing)
