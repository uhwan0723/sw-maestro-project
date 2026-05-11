from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any

import yfinance as yf

from app.models.enums import SectorCode


YFINANCE_SOURCE = "yfinance"
KOSPI_TICKER_SUFFIX = ".KS"

SECTOR_REPRESENTATIVE_TICKERS: Mapping[SectorCode, tuple[str, ...]] = {
    SectorCode.SEMICONDUCTOR: (
        "005930.KS",  # Samsung Electronics
        "000660.KS",  # SK hynix
        "042700.KS",  # HANMI Semiconductor
        "000990.KS",  # DB HiTek
        "108320.KS",  # LX Semicon
    ),
    SectorCode.PHARMACEUTICAL: (
        "068270.KS",  # Celltrion
        "207940.KS",  # Samsung Biologics
        "000100.KS",  # Yuhan
        "128940.KS",  # Hanmi Pharm
        "326030.KS",  # SK Biopharmaceuticals
    ),
}


class YFinanceClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class MarketQuote:
    sector: SectorCode
    ticker: str
    price: float | None
    change_percent: float | None
    volume: int | None
    source: str = YFINANCE_SOURCE


class YFinanceClient:
    def __init__(
        self,
        *,
        tickers_by_sector: Mapping[SectorCode, Sequence[str]] | None = None,
        ticker_factory: Callable[[str], Any] = yf.Ticker,
    ) -> None:
        self._tickers_by_sector = tickers_by_sector or SECTOR_REPRESENTATIVE_TICKERS
        self._ticker_factory = ticker_factory

    def get_tickers_for_sector(self, sector: SectorCode) -> tuple[str, ...]:
        tickers = self._tickers_by_sector.get(sector)
        if tickers is None:
            raise YFinanceClientError(f"Unsupported sector: {sector}")
        _validate_kospi_tickers(tickers)
        return tuple(tickers)

    def fetch_sector_quotes(self, sector: SectorCode) -> list[MarketQuote]:
        return [
            self.fetch_quote(sector=sector, ticker=ticker)
            for ticker in self.get_tickers_for_sector(sector)
        ]

    def fetch_quote(self, *, sector: SectorCode, ticker: str) -> MarketQuote:
        try:
            fast_info = self._ticker_factory(ticker).fast_info
            price = _to_float(
                _read_first(
                    fast_info,
                    ("last_price", "lastPrice", "regularMarketPrice"),
                )
            )
            previous_close = _to_float(
                _read_first(
                    fast_info,
                    (
                        "previous_close",
                        "previousClose",
                        "regularMarketPreviousClose",
                    ),
                )
            )
            volume = _to_int(
                _read_first(
                    fast_info,
                    ("last_volume", "lastVolume", "regularMarketVolume", "volume"),
                )
            )
        except Exception as exc:
            raise YFinanceClientError(
                f"Failed to fetch yfinance data for ticker: {ticker}"
            ) from exc

        return MarketQuote(
            sector=sector,
            ticker=ticker,
            price=price,
            change_percent=_calculate_change_percent(price, previous_close),
            volume=volume,
        )


def _read_first(source: Any, keys: Sequence[str]) -> Any:
    for key in keys:
        value = _read_value(source, key)
        if value is not None:
            return value
    return None


def _validate_kospi_tickers(tickers: Sequence[str]) -> None:
    invalid_tickers = [
        ticker for ticker in tickers if not ticker.endswith(KOSPI_TICKER_SUFFIX)
    ]
    if invalid_tickers:
        raise YFinanceClientError(
            "Only KOSPI yfinance tickers with .KS suffix are supported: "
            + ", ".join(invalid_tickers)
        )


def _read_value(source: Any, key: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(key)

    try:
        return source[key]
    except (KeyError, TypeError):
        pass

    return getattr(source, key, None)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _calculate_change_percent(
    price: float | None,
    previous_close: float | None,
) -> float | None:
    if price is None or previous_close in (None, 0):
        return None
    return ((price - previous_close) / previous_close) * 100
