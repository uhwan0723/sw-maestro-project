from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.models.enums import SectorCode
from app.models.market import MarketMetric


PRICE_METRIC = "price"
CHANGE_PERCENT_METRIC = "change_percent"
VOLUME_METRIC = "volume"
TRACKED_MARKET_METRICS = {PRICE_METRIC, CHANGE_PERCENT_METRIC, VOLUME_METRIC}


@dataclass(frozen=True)
class TickerIndicator:
    ticker: str
    price: float | None
    change_percent: float | None
    volume: int | None
    sources: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "price": self.price,
            "change_percent": self.change_percent,
            "volume": self.volume,
            "sources": list(self.sources),
        }


@dataclass(frozen=True)
class SectorComparisonIndicator:
    ticker_count: int
    price_count: int
    change_percent_count: int
    volume_count: int
    average_change_percent: float | None
    rising_count: int
    falling_count: int
    flat_count: int
    total_volume: int | None
    average_volume: float | None
    top_gainer: str | None
    top_loser: str | None
    most_traded: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "ticker_count": self.ticker_count,
            "price_count": self.price_count,
            "change_percent_count": self.change_percent_count,
            "volume_count": self.volume_count,
            "average_change_percent": self.average_change_percent,
            "rising_count": self.rising_count,
            "falling_count": self.falling_count,
            "flat_count": self.flat_count,
            "total_volume": self.total_volume,
            "average_volume": self.average_volume,
            "top_gainer": self.top_gainer,
            "top_loser": self.top_loser,
            "most_traded": self.most_traded,
        }


@dataclass(frozen=True)
class NormalizedIndicatorContext:
    sector: SectorCode
    reference_date: date
    tickers: tuple[TickerIndicator, ...]
    comparison: SectorComparisonIndicator

    @property
    def has_data(self) -> bool:
        return self.comparison.ticker_count > 0

    def to_payload(self) -> dict[str, Any]:
        return {
            "sector": self.sector.value,
            "reference_date": self.reference_date.isoformat(),
            "tickers": [ticker.to_payload() for ticker in self.tickers],
            "comparison": self.comparison.to_payload(),
        }


def normalize_market_metrics(
    *,
    sector: SectorCode,
    reference_date: date,
    metrics: Sequence[MarketMetric],
) -> NormalizedIndicatorContext:
    metric_values: defaultdict[str, dict[str, float]] = defaultdict(dict)
    metric_sources: defaultdict[str, set[str]] = defaultdict(set)

    for metric in metrics:
        parsed_metric = _parse_metric_name(metric.metric_name)
        if parsed_metric is None:
            continue

        ticker, metric_kind = parsed_metric
        metric_values[ticker][metric_kind] = metric.metric_value
        metric_sources[ticker].add(metric.source)

    tickers = tuple(
        TickerIndicator(
            ticker=ticker,
            price=values.get(PRICE_METRIC),
            change_percent=values.get(CHANGE_PERCENT_METRIC),
            volume=_normalize_volume(values.get(VOLUME_METRIC)),
            sources=tuple(sorted(metric_sources[ticker])),
        )
        for ticker, values in sorted(metric_values.items())
    )

    return NormalizedIndicatorContext(
        sector=sector,
        reference_date=reference_date,
        tickers=tickers,
        comparison=_build_sector_comparison(tickers),
    )


def _parse_metric_name(metric_name: str) -> tuple[str, str] | None:
    ticker, separator, metric_kind = metric_name.partition(":")
    if not separator or not ticker or metric_kind not in TRACKED_MARKET_METRICS:
        return None
    return ticker, metric_kind


def _normalize_volume(value: float | None) -> int | None:
    if value is None:
        return None
    return int(value)


def _build_sector_comparison(
    tickers: tuple[TickerIndicator, ...],
) -> SectorComparisonIndicator:
    prices = [ticker.price for ticker in tickers if ticker.price is not None]
    change_percents = [
        ticker.change_percent
        for ticker in tickers
        if ticker.change_percent is not None
    ]
    volumes = [ticker.volume for ticker in tickers if ticker.volume is not None]

    return SectorComparisonIndicator(
        ticker_count=len(tickers),
        price_count=len(prices),
        change_percent_count=len(change_percents),
        volume_count=len(volumes),
        average_change_percent=_average_float(change_percents),
        rising_count=sum(1 for value in change_percents if value > 0),
        falling_count=sum(1 for value in change_percents if value < 0),
        flat_count=sum(1 for value in change_percents if value == 0),
        total_volume=sum(volumes) if volumes else None,
        average_volume=_average_int(volumes),
        top_gainer=_top_change_ticker(tickers),
        top_loser=_bottom_change_ticker(tickers),
        most_traded=_most_traded_ticker(tickers),
    )


def _average_float(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _average_int(values: Sequence[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _top_change_ticker(tickers: Sequence[TickerIndicator]) -> str | None:
    candidates = [
        ticker for ticker in tickers if ticker.change_percent is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda ticker: ticker.change_percent or 0).ticker


def _bottom_change_ticker(tickers: Sequence[TickerIndicator]) -> str | None:
    candidates = [
        ticker for ticker in tickers if ticker.change_percent is not None
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda ticker: ticker.change_percent or 0).ticker


def _most_traded_ticker(tickers: Sequence[TickerIndicator]) -> str | None:
    candidates = [ticker for ticker in tickers if ticker.volume is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda ticker: ticker.volume or 0).ticker
