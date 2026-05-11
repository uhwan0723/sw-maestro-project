import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from agent.graph import agent, PatentState

st.set_page_config(
    page_title="PatentSense | AI 특허 유사도 분석",
    page_icon="🔍",
    layout="wide",
)

# ── 스타일 ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { max-width: 1280px; margin: 0 auto; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
details { margin: 8px 0; padding: 8px 14px; border: 1px solid #e1e4e8; border-radius: 8px; background: #fafbfc; }
details summary { cursor: pointer; font-weight: 500; padding: 4px 0; }
details[open] summary { margin-bottom: 8px; border-bottom: 1px solid #e1e4e8; padding-bottom: 8px; }

/* 이미지 라이트박스 (CSS :target 방식) */
.lb-thumb { cursor: zoom-in; transition: transform 0.15s; }
.lb-thumb:hover { transform: scale(1.02); }
.lb-overlay {
    display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.85); z-index: 99999;
    align-items: center; justify-content: center;
}
.lb-overlay:target { display: flex; }
.lb-content { position: relative; max-width: 90vw; max-height: 90vh; }
.lb-content img { max-width: 90vw; max-height: 90vh; background: #fff; border-radius: 4px; }
.lb-close {
    position: absolute; top: -36px; right: 0;
    color: #fff; font-size: 32px; line-height: 1;
    text-decoration: none; user-select: none;
}
.lb-close:hover { color: #ddd; }
.lb-backdrop {
    position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: -1;
}
a.lb-thumb-link, a.lb-thumb-link:hover { text-decoration: none; }
.score-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-weight: bold;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# ── 헤더 ──────────────────────────────────────────────────────────────────────
st.title("🔍 PatentSense")
st.caption("자연어 아이디어 입력 → KIPRIS 국내 특허 유사도 분석 AI 에이전트")

with st.expander("ℹ️ 사용 방법"):
    st.markdown("""
- 아이디어를 **한 문장 이상으로 구체적으로** 입력해주세요 (예: *음성으로 조명 밝기를 조절하는 스마트홈 기기*)
- 또는 청구항 형태로 구체적으로 입력하셔도 됩니다
- AI가 아이디어를 기술 용어로 분석한 후 KIPRIS에서 유사 특허를 검색·분석합니다
- 결과는 참고용이며, 법적 판단은 변리사와 상담하세요
""")

# ── 세션 초기화 ────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── 채팅 이력 표시 ─────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

# ── 입력 처리 ─────────────────────────────────────────────────────────────────
if idea := st.chat_input("아이디어를 한 문장 이상 구체적으로 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": idea})
    with st.chat_message("user"):
        st.markdown(idea)

    with st.chat_message("assistant"):
        step_placeholder = st.empty()
        result_placeholder = st.empty()

        initial_state: PatentState = {
            "user_idea": idea,
            "processed_idea": "",
            "preprocess_detail": {},
            "keywords": [],
            "patents": [],
            "ranked_patents": [],
            "report": "",
            "conflict_points": [],
            "differentiators": [],
            "messages": [],
            "error": None,
        }

        final_state = None
        error_msg = None

        try:
            for chunk in agent.stream(initial_state):
                node_name = next(iter(chunk))
                updates = chunk[node_name]

                if node_name == "preprocess_idea":
                    detail = updates.get("preprocess_detail", {})
                    if detail:
                        components = ", ".join(detail.get("tech_components", []))
                        step_placeholder.info(
                            f"⚙️ **기술 분석 완료**  \n"
                            f"🔬 기술 분야: {detail.get('tech_field', '-')}  \n"
                            f"⚠️ 해결 과제: {detail.get('problem', '-')}  \n"
                            f"💡 해결 수단: {detail.get('solution', '-')}  \n"
                            f"✅ 기대 효과: {detail.get('effect', '-')}  \n"
                            f"🔧 검색 키워드: {components}"
                        )

                elif node_name == "extract_keywords":
                    kws = updates.get("keywords", [])
                    step_placeholder.info(f"🔑 키워드 추출 완료: **{', '.join(kws)}**")

                elif node_name == "search_patents":
                    cnt = len(updates.get("patents", []))
                    err = updates.get("error")
                    if err:
                        step_placeholder.warning(f"⚠️ 특허 검색 중 오류: {err}")
                    else:
                        step_placeholder.info(f"📂 특허 검색 완료: **{cnt}건** 후보 발견")

                elif node_name == "rank_by_similarity":
                    cnt = len(updates.get("ranked_patents", []))
                    step_placeholder.info(f"📐 유사도 계산 완료: **Top {cnt}** 특허 선정")

                elif node_name == "analyze_conflicts":
                    cnt = len(updates.get("conflict_points", []))
                    step_placeholder.info(f"🧩 충돌 요소 분석 완료: **{cnt}개**")

                elif node_name == "derive_differentiators":
                    cnt = len(updates.get("differentiators", []))
                    step_placeholder.info(f"🚀 차별점 도출 완료: **{cnt}개**")

                elif node_name == "generate_report":
                    step_placeholder.empty()
                    report = updates.get("report", "")
                    if report:
                        result_placeholder.markdown(report, unsafe_allow_html=True)
                        final_state = updates

        except Exception as e:
            error_msg = f"❌ 오류가 발생했습니다: {str(e)}"
            step_placeholder.empty()
            result_placeholder.error(error_msg)

        if final_state:
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_state.get("report", ""),
            })
        elif error_msg:
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg,
            })

# ── 사이드바 ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")
    st.markdown("---")
    st.markdown("**데이터 소스**")
    st.markdown("- 🇰🇷 KIPRIS 국내 특허 DB")
    st.markdown("**AI 모델**")
    st.markdown("- 💬 Solar Pro (Upstage)")
    st.markdown("- 🧮 Solar Embedding")
    st.markdown("---")
    if st.button("🗑️ 대화 초기화"):
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    st.caption("PatentSense v0.1 | AI·SW마에스트로 17기 22조")
