import asyncio
from datetime import date

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.state import AgentState
from app.db.base import Base
from app.models.analysis import AnalysisResult
from app.models.enums import RequestType, SectorCode
from app.models.market import MarketMetric
from app.models.news import NewsArticle
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.market_repository import MarketRepository
from app.repositories.news_repository import NewsRepository
from app.schemas.chat import ChatRequest, ChatTurn
from app.schemas.common import SourceInfo, WarningMessage
from app.services.analysis_service import AnalysisService
from app.services.chat_service import ChatService


def run(coro):
    return asyncio.run(coro)


async def with_session(callback):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            return await callback(session)
    finally:
        await engine.dispose()


def test_market_repository_upsert_updates_existing_metric() -> None:
    async def scenario(session):
        repository = MarketRepository(session)
        metric = MarketMetric(
            sector=SectorCode.SEMICONDUCTOR,
            reference_date=date(2026, 5, 8),
            metric_name="005930.KS:price",
            metric_value=70_000,
            source="yfinance",
        )

        await repository.upsert(metric)
        await repository.upsert(
            MarketMetric(
                sector=SectorCode.SEMICONDUCTOR,
                reference_date=date(2026, 5, 8),
                metric_name="005930.KS:price",
                metric_value=71_000,
                source="yfinance",
            )
        )

        rows = await repository.list_by_sector_and_date(
            sector=SectorCode.SEMICONDUCTOR,
            reference_date=date(2026, 5, 8),
        )

        assert len(rows) == 1
        assert rows[0].metric_value == 71_000

    run(with_session(scenario))


def test_news_repository_insert_if_new_ignores_duplicate_url() -> None:
    async def scenario(session):
        repository = NewsRepository(session)
        article = NewsArticle(
            sector=SectorCode.PHARMACEUTICAL,
            reference_date=date(2026, 5, 8),
            title="셀트리온 뉴스",
            url="https://example.com/news",
            source="naver_news",
            published_at=None,
            summary="요약",
            keywords=["셀트리온"],
        )

        first = await repository.insert_if_new(article)
        duplicate = await repository.insert_if_new(article)

        assert first is not None
        assert duplicate is None
        assert (await repository.get_by_url("https://example.com/news")).title == (
            "셀트리온 뉴스"
        )

    run(with_session(scenario))


def test_analysis_repository_upsert_updates_cached_payload() -> None:
    async def scenario(session):
        repository = AnalysisRepository(session)

        await repository.upsert(
            AnalysisResult(
                sector=SectorCode.SEMICONDUCTOR,
                reference_date=date(2026, 5, 8),
                trend_label="혼조 또는 보합",
                confidence=0.5,
                beginner_summary="이전 요약",
                key_evidence=[],
                sources=[],
                caution="주의",
            )
        )
        await repository.upsert(
            AnalysisResult(
                sector=SectorCode.SEMICONDUCTOR,
                reference_date=date(2026, 5, 8),
                trend_label="상승 우세",
                confidence=0.8,
                beginner_summary="새 요약",
                key_evidence=[
                    {
                        "title": "근거",
                        "description": "설명",
                        "source": None,
                    }
                ],
                sources=[],
                caution="주의",
            )
        )

        cached = await repository.get_by_sector_and_date(
            sector=SectorCode.SEMICONDUCTOR,
            reference_date=date(2026, 5, 8),
        )

        assert cached.trend_label == "상승 우세"
        assert cached.confidence == 0.8
        assert cached.beginner_summary == "새 요약"
        assert len(cached.key_evidence) == 1

    run(with_session(scenario))


def test_chat_service_trims_history_and_maps_agent_state_to_response() -> None:
    seen_state: AgentState | None = None

    async def agent_runner(state: AgentState) -> AgentState:
        nonlocal seen_state
        seen_state = state
        return AgentState(
            request_type=RequestType.TERM_EXPLANATION,
            final_answer="PER은 주가수익비율입니다.",
            safety_notice="교육용 정보입니다.",
            warnings=[WarningMessage(code="notice", message="안내")],
        )

    request = ChatRequest(
        message="PER이 뭐야?",
        session_id="session-1",
        history=[
            ChatTurn(role="user", content="첫 질문"),
            ChatTurn(role="assistant", content="첫 답변"),
            ChatTurn(role="user", content="직전 질문"),
        ],
    )

    response = run(
        ChatService(agent_runner=agent_runner, max_history_turns=2).respond(request)
    )

    assert seen_state is not None
    assert [turn.content for turn in seen_state.chat_history] == ["첫 답변", "직전 질문"]
    assert seen_state.session_id == "session-1"
    assert response.request_type is RequestType.TERM_EXPLANATION
    assert response.answer == "PER은 주가수익비율입니다."
    assert response.safety_notice == "교육용 정보입니다."
    assert response.warnings[0].code == "notice"
    assert response.session_id == "session-1"


def test_analysis_service_returns_cached_analysis_without_agent_call() -> None:
    async def scenario(session):
        repository = AnalysisRepository(session)
        await repository.upsert(
            AnalysisResult(
                sector=SectorCode.SEMICONDUCTOR,
                reference_date=date.today(),
                trend_label="상승 우세",
                confidence=0.77,
                beginner_summary="캐시된 요약",
                key_evidence=[],
                sources=[
                    SourceInfo(
                        title="시장 지표",
                        url="market://semiconductor/today",
                        provider="yfinance",
                    ).model_dump(mode="json")
                ],
                caution="교육용 분석입니다.",
            )
        )
        await session.commit()

        async def agent_runner(_state: AgentState) -> AgentState:
            raise AssertionError("cached analysis should not run the agent")

        response = await AnalysisService(
            session,
            agent_runner=agent_runner,
        ).get_today_sector_analysis(SectorCode.SEMICONDUCTOR)

        assert response.sector is SectorCode.SEMICONDUCTOR
        assert response.beginner_summary == "캐시된 요약"
        assert response.confidence == 0.77
        assert response.sources[0].url == "market://semiconductor/today"
        assert response.warnings == []

    run(with_session(scenario))


def test_analysis_service_refresh_runs_agent_and_persists_result() -> None:
    async def scenario(session):
        async def agent_runner(state: AgentState) -> AgentState:
            assert state.request_type is RequestType.SECTOR_ANALYSIS
            assert state.sector is SectorCode.PHARMACEUTICAL
            return AgentState(
                request_type=RequestType.SECTOR_ANALYSIS,
                sector=SectorCode.PHARMACEUTICAL,
                beginner_summary="새 분석 요약",
                trend_label="혼조 또는 보합",
                confidence=0.62,
                key_evidence=[],
                sources=[],
                caution="교육용 분석입니다.",
                warnings=[WarningMessage(code="low_data", message="데이터가 적습니다.")],
            )

        response = await AnalysisService(
            session,
            agent_runner=agent_runner,
        ).get_today_sector_analysis(
            SectorCode.PHARMACEUTICAL,
            refresh=True,
        )
        cached = await AnalysisRepository(session).get_by_sector_and_date(
            sector=SectorCode.PHARMACEUTICAL,
            reference_date=date.today(),
        )

        assert response.beginner_summary == "새 분석 요약"
        assert response.warnings[0].code == "low_data"
        assert cached.trend_label == "혼조 또는 보합"
        assert cached.confidence == 0.62

    run(with_session(scenario))
