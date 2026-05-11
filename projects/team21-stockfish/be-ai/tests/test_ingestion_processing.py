from datetime import date, datetime

from app.ingestion.indicator_normalizer import normalize_market_metrics
from app.ingestion.naver_news_client import NaverNewsArticle
from app.ingestion.news_processor import (
    clean_news_text,
    process_naver_news_articles,
    process_saved_news_articles,
)
from app.ingestion.yfinance_client import YFinanceClient, YFinanceClientError
from app.models.enums import SectorCode
from app.models.market import MarketMetric
from app.models.news import NewsArticle


def test_yfinance_client_normalizes_fast_info_quote() -> None:
    class FakeTicker:
        fast_info = {
            "last_price": 110_000,
            "previous_close": 100_000,
            "last_volume": 1_234_567,
        }

    client = YFinanceClient(ticker_factory=lambda _ticker: FakeTicker())

    quote = client.fetch_quote(
        sector=SectorCode.SEMICONDUCTOR,
        ticker="005930.KS",
    )

    assert quote.price == 110_000
    assert quote.change_percent == 10.0
    assert quote.volume == 1_234_567
    assert quote.source == "yfinance"


def test_yfinance_client_rejects_non_kospi_tickers() -> None:
    client = YFinanceClient(
        tickers_by_sector={SectorCode.SEMICONDUCTOR: ("AAPL",)},
    )

    try:
        client.get_tickers_for_sector(SectorCode.SEMICONDUCTOR)
    except YFinanceClientError as exc:
        assert ".KS" in str(exc)
    else:
        raise AssertionError("YFinanceClientError was not raised")


def test_normalize_market_metrics_builds_ticker_and_sector_comparison() -> None:
    metrics = [
        MarketMetric(
            sector=SectorCode.SEMICONDUCTOR,
            reference_date=date(2026, 5, 8),
            metric_name="005930.KS:price",
            metric_value=70_000,
            source="yfinance",
        ),
        MarketMetric(
            sector=SectorCode.SEMICONDUCTOR,
            reference_date=date(2026, 5, 8),
            metric_name="005930.KS:change_percent",
            metric_value=1.5,
            source="yfinance",
        ),
        MarketMetric(
            sector=SectorCode.SEMICONDUCTOR,
            reference_date=date(2026, 5, 8),
            metric_name="005930.KS:volume",
            metric_value=1_000,
            source="yfinance",
        ),
        MarketMetric(
            sector=SectorCode.SEMICONDUCTOR,
            reference_date=date(2026, 5, 8),
            metric_name="000660.KS:change_percent",
            metric_value=-0.5,
            source="yfinance",
        ),
        MarketMetric(
            sector=SectorCode.SEMICONDUCTOR,
            reference_date=date(2026, 5, 8),
            metric_name="ignored_metric",
            metric_value=999,
            source="yfinance",
        ),
    ]

    context = normalize_market_metrics(
        sector=SectorCode.SEMICONDUCTOR,
        reference_date=date(2026, 5, 8),
        metrics=metrics,
    )

    assert context.has_data
    assert [ticker.ticker for ticker in context.tickers] == ["000660.KS", "005930.KS"]
    assert context.comparison.ticker_count == 2
    assert context.comparison.average_change_percent == 0.5
    assert context.comparison.rising_count == 1
    assert context.comparison.falling_count == 1
    assert context.comparison.top_gainer == "005930.KS"
    assert context.comparison.top_loser == "000660.KS"
    assert context.comparison.most_traded == "005930.KS"


def test_clean_news_text_removes_html_entities_and_extra_whitespace() -> None:
    assert clean_news_text("  <b>삼성전자</b>&amp; SK하이닉스\n  상승  ") == (
        "삼성전자& SK하이닉스 상승"
    )


def test_process_naver_news_articles_cleans_extracts_and_deduplicates() -> None:
    published_at = datetime(2026, 5, 8, 9, 0)
    articles = [
        NaverNewsArticle(
            sector=SectorCode.SEMICONDUCTOR,
            title="<b>삼성전자</b> HBM 수출 기대",
            link="https://n.news.naver.com/article/1",
            original_link="https://example.com/news/1",
            description="반도체 수출과 HBM 수요가 개선된다는 설명입니다.",
            published_at=published_at,
        ),
        NaverNewsArticle(
            sector=SectorCode.SEMICONDUCTOR,
            title="중복 기사",
            link="https://n.news.naver.com/article/duplicate",
            original_link="https://example.com/news/1",
            description="같은 원문 URL입니다.",
            published_at=published_at,
        ),
    ]

    processed = process_naver_news_articles(articles)

    assert len(processed) == 1
    assert processed[0].title == "삼성전자 HBM 수출 기대"
    assert processed[0].url == "https://n.news.naver.com/article/1"
    assert processed[0].original_url == "https://example.com/news/1"
    assert {"삼성전자", "HBM", "반도체", "수출"}.issubset(
        set(processed[0].keywords)
    )


def test_process_saved_news_articles_uses_title_as_summary_fallback() -> None:
    article = NewsArticle(
        sector=SectorCode.PHARMACEUTICAL,
        reference_date=date(2026, 5, 8),
        title="<b>셀트리온</b> 임상 결과 발표",
        url="https://example.com/news/2",
        source="naver_news",
        published_at=datetime(2026, 5, 8, 10, 0),
        summary=None,
        keywords=[],
    )

    processed = process_saved_news_articles([article])

    assert len(processed) == 1
    assert processed[0].title == "셀트리온 임상 결과 발표"
    assert processed[0].summary == "셀트리온 임상 결과 발표"
    assert "셀트리온" in processed[0].keywords
