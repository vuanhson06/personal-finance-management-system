import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import MarketWatch

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

CACHE_TTL_SECONDS: int = 300


@dataclass
class CacheEntry:
    symbol: str
    price: float
    currency: str
    exchange: str
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "symbol":     self.symbol,
            "price":      self.price,
            "currency":   self.currency,
            "exchange":   self.exchange,
            "fetched_at": self.fetched_at.strftime("%Y-%m-%d %H:%M:%S"),
        }

_cache: dict[str, CacheEntry] = {}

def _is_cache_valid(entry: CacheEntry) -> bool:
    age: timedelta = datetime.now() - entry.fetched_at
    return age.total_seconds() < CACHE_TTL_SECONDS


def fetch_price(symbol: str) -> Optional[dict]:
    symbol = symbol.upper().strip()

    if symbol in _cache and _is_cache_valid(_cache[symbol]):
        logger.debug("Cache HIT  for '%s' (age: fresh).", symbol)
        return _cache[symbol].to_dict()

    logger.info("Cache MISS for '%s' — fetching from yfinance...", symbol)

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info  

        price: Optional[float] = getattr(info, "last_price", None)
        currency: str = getattr(info, "currency", "USD") or "USD"
        exchange: str = getattr(info, "exchange", "N/A") or "N/A"

        if price is None or price <= 0:
            logger.warning(
                "yfinance returned no valid price for '%s'. "
                "Symbol may be invalid, delisted, or market is closed.",
                symbol,
            )
            return None

        entry = CacheEntry(
            symbol=symbol,
            price=round(float(price), 4),
            currency=currency,
            exchange=exchange,
            fetched_at=datetime.now(),
        )
        _cache[symbol] = entry

        logger.info(
            "Fetched '%s': %.4f %s (exchange: %s).",
            symbol, entry.price, entry.currency, entry.exchange,
        )
        return entry.to_dict()

    except Exception as e:
        logger.error(
            "Failed to fetch price for '%s'. %s: %s",
            symbol, type(e).__name__, e,
        )
        return None



def fetch_watchlist_prices(symbols: list[str]) -> list[dict]:
    if not symbols:
        logger.warning("fetch_watchlist_prices called with an empty symbol list.")
        return []

    results: list[dict] = []
    for symbol in symbols:
        result = fetch_price(symbol)
        if result is not None:
            results.append(result)
        else:
            logger.warning("Skipping '%s' — fetch returned no data.", symbol)

    logger.info(
        "Watchlist fetch complete: %d/%d symbols successful.",
        len(results), len(symbols),
    )
    return results

def get_user_watchlist_data(user_id: int, db: Session) -> list[dict]:
    watch_entries: list[MarketWatch] = db.execute(
        select(MarketWatch).where(MarketWatch.UserID == user_id)
    ).scalars().all()

    if not watch_entries:
        logger.info("User %d has no MarketWatch entries.", user_id)
        return []

    # Step 2: Build symbol → DB metadata map
    symbol_meta: dict[str, dict] = {
        entry.AssetSymbol.upper(): {
            "asset_type": entry.AssetType or "Unknown",
            "watch_id":   entry.WatchID,
        }
        for entry in watch_entries
    }

    symbols: list[str] = list(symbol_meta.keys())
    price_results: list[dict] = fetch_watchlist_prices(symbols)

    enriched: list[dict] = []
    for price_data in price_results:
        sym: str = price_data["symbol"]
        meta: dict = symbol_meta.get(sym, {"asset_type": "Unknown", "watch_id": None})
        enriched.append({**price_data, **meta})

    logger.info(
        "Watchlist data ready for user %d: %d assets with live prices.",
        user_id, len(enriched),
    )
    return enriched


def clear_cache(symbol: Optional[str] = None) -> None:
    global _cache
    if symbol is not None:
        key: str = symbol.upper().strip()
        if key in _cache:
            del _cache[key]
            logger.info("Cache cleared for symbol '%s'.", key)
        else:
            logger.warning(
                "clear_cache('%s') called but symbol not found in cache.", key
            )
    else:
        count: int = len(_cache)
        _cache = {}
        logger.info("Entire cache cleared. %d entries removed.", count)
