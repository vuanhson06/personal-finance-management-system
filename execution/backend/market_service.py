"""
market_service.py — Live Market Data Service
=============================================
Provides live financial asset price data by fetching from the Yahoo Finance
API via `yfinance`. Implements an in-memory TTL cache (5 minutes by default)
to prevent redundant API calls and avoid rate-limiting.

Public API:
    fetch_price(symbol)              → dict | None
    fetch_watchlist_prices(symbols)  → list[dict]
    get_user_watchlist_data(uid, db) → list[dict]
    clear_cache(symbol?)             → None

Cache Strategy:
    - Cache is checked BEFORE every API call.
    - A valid cache hit returns instantly with zero network I/O.
    - A stale or missing cache entry triggers a fresh yfinance fetch.
    - Cache TTL is configurable via CACHE_TTL_SECONDS (default: 300s).

Error Handling:
    - All yfinance exceptions are caught internally and logged.
    - Failed fetches return None — callers must handle None gracefully.
    - DB stack traces NEVER propagate to the UI layer.

Directive Reference:
    - directives/backend_logic_rules.md — Section 2 (Data Isolation),
                                          Section 4 (Safe Error Propagation)
    - directives/db_rules.md           — Section 4 (Security Protocols)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import MarketWatch

# =============================================================================
# Logging
# =============================================================================

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# =============================================================================
# Step 4.1 — Cache Configuration & CacheEntry Dataclass
# =============================================================================

# Time-to-live for cached price data in seconds.
# 300s = 5 minutes — balances freshness with rate-limit safety.
CACHE_TTL_SECONDS: int = 300


@dataclass
class CacheEntry:
    """
    Holds a single cached market price result for one asset symbol.

    Attributes:
        symbol:     The asset ticker symbol (e.g., 'AAPL', 'BTC-USD').
        price:      The last known market price as a float.
        currency:   The currency of the price (e.g., 'USD').
        exchange:   The exchange the asset trades on (e.g., 'NMS', 'CCC').
        fetched_at: The datetime when this price was retrieved from the API.
    """
    symbol: str
    price: float
    currency: str
    exchange: str
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """
        Serializes this cache entry to a plain dictionary suitable for
        passing to the frontend layer or merging with DB metadata.

        Returns:
            A dict with keys: symbol, price, currency, exchange, fetched_at.
        """
        return {
            "symbol":     self.symbol,
            "price":      self.price,
            "currency":   self.currency,
            "exchange":   self.exchange,
            "fetched_at": self.fetched_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


# =============================================================================
# Step 4.2 — Module-Level In-Memory Cache Store
# =============================================================================

# Module-level dict — persists for the lifetime of the running process.
# Key: asset symbol (str), Value: CacheEntry
# No external dependency (Redis, memcached, etc.) needed at this stage.
_cache: dict[str, CacheEntry] = {}


# =============================================================================
# Step 4.3 — Cache Validity Check
# =============================================================================

def _is_cache_valid(entry: CacheEntry) -> bool:
    """
    Determines whether a cached price entry is still within the TTL window.

    Compares the entry's `fetched_at` timestamp against the current time.
    If the age is less than CACHE_TTL_SECONDS, the cache is still valid.

    Args:
        entry: The CacheEntry to validate.

    Returns:
        True if the cache entry is fresh (within TTL), False if stale.
    """
    age: timedelta = datetime.now() - entry.fetched_at
    return age.total_seconds() < CACHE_TTL_SECONDS


# =============================================================================
# Step 4.4 — Core Price Fetcher (Cache-First)
# =============================================================================

def fetch_price(symbol: str) -> Optional[dict]:
    """
    Fetches the current market price for a single asset symbol.

    Implements a cache-first strategy:
        1. Check _cache for a valid (non-stale) entry → return immediately.
        2. On cache miss or stale entry → call yfinance API.
        3. On success → update _cache and return the result dict.
        4. On any failure → log internally and return None.

    The returned dict is safe to pass directly to the frontend. It contains
    no raw yfinance objects — only serializable primitive types.

    Args:
        symbol: A valid Yahoo Finance ticker symbol (e.g., 'AAPL', 'BTC-USD',
                'GC=F' for Gold futures).

    Returns:
        A dict with keys {symbol, price, currency, exchange, fetched_at}
        if successful, or None if the fetch failed for any reason.

    Example:
        result = fetch_price("AAPL")
        if result:
            print(f"Apple: ${result['price']} {result['currency']}")
    """
    symbol = symbol.upper().strip()

    # --- Step 1: Cache hit check ---
    if symbol in _cache and _is_cache_valid(_cache[symbol]):
        logger.debug("Cache HIT  for '%s' (age: fresh).", symbol)
        return _cache[symbol].to_dict()

    logger.info("Cache MISS for '%s' — fetching from yfinance...", symbol)

    # --- Step 2: Live API fetch ---
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info  # fast_info is lighter than .info (no full scrape)

        price: Optional[float] = getattr(info, "last_price", None)
        currency: str = getattr(info, "currency", "USD") or "USD"
        exchange: str = getattr(info, "exchange", "N/A") or "N/A"

        # Guard: yfinance may return None for price on invalid/delisted symbols
        if price is None or price <= 0:
            logger.warning(
                "yfinance returned no valid price for '%s'. "
                "Symbol may be invalid, delisted, or market is closed.",
                symbol,
            )
            return None

        # --- Step 3: Update cache ---
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
        # --- Step 4: Safe failure ---
        # Log full details internally; return None to caller — never re-raise.
        logger.error(
            "Failed to fetch price for '%s'. %s: %s",
            symbol, type(e).__name__, e,
        )
        return None


# =============================================================================
# Step 4.5 — Batch Watchlist Fetcher
# =============================================================================

def fetch_watchlist_prices(symbols: list[str]) -> list[dict]:
    """
    Fetches current market prices for a list of asset symbols in sequence.

    Calls `fetch_price()` for each symbol and collects only the successful
    results (non-None). Symbols that fail to fetch are silently skipped
    so one bad symbol never blocks the rest of the watchlist from loading.

    This is the primary function called by the frontend dashboard ticker.

    Args:
        symbols: A list of Yahoo Finance ticker symbols to fetch.
                 Can be a mix of Stocks, Crypto, and Commodity symbols.

    Returns:
        A list of result dicts for all successfully fetched symbols.
        Returns an empty list if all fetches fail or symbols is empty.

    Example:
        prices = fetch_watchlist_prices(["AAPL", "BTC-USD", "GC=F"])
        for item in prices:
            print(f"{item['symbol']}: {item['price']} {item['currency']}")
    """
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


# =============================================================================
# Step 4.6 — DB-Aware User Watchlist Service
# =============================================================================

def get_user_watchlist_data(user_id: int, db: Session) -> list[dict]:
    """
    Retrieves live price data for all assets in a specific user's watchlist.

    Workflow:
        1. Query the `MarketWatch` table for all entries owned by `user_id`
           (enforcing the data isolation rule: UserID filter is MANDATORY).
        2. Extract the list of asset symbols.
        3. Pass symbols to `fetch_watchlist_prices()` for live price retrieval.
        4. Merge each live price result with the DB-stored `AssetType` label
           (e.g., 'Stock', 'Crypto', 'Gold') for a complete response object.

    Data Isolation: This function ALWAYS filters by `user_id`. A generic
    query without a UserID filter is strictly prohibited per
    directives/backend_logic_rules.md (Section 2 — The Golden Rule).

    Args:
        user_id: The authenticated user's UserID. Must be the current user's ID.
        db:      An active SQLAlchemy Session.

    Returns:
        A list of enriched dicts combining live price data with DB metadata.
        Each dict contains: {symbol, price, currency, exchange, fetched_at,
                             asset_type, watch_id}.
        Returns an empty list if the user has no watchlist entries or all
        fetches fail.

    Example:
        db = next(get_db())
        watchlist = get_user_watchlist_data(current_user.UserID, db)
        for asset in watchlist:
            print(f"[{asset['asset_type']}] {asset['symbol']}: ${asset['price']}")
    """
    # Step 1: Fetch this user's watchlist from DB — UserID filter is MANDATORY
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

    # Step 3: Fetch live prices for all symbols
    symbols: list[str] = list(symbol_meta.keys())
    price_results: list[dict] = fetch_watchlist_prices(symbols)

    # Step 4: Merge live price data with DB metadata
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


# =============================================================================
# Step 4.7 — Cache Invalidation Utility
# =============================================================================

def clear_cache(symbol: Optional[str] = None) -> None:
    """
    Manually invalidates the in-memory price cache.

    Use this utility to:
        - Force a fresh API fetch for a specific symbol (e.g., after a
          known price event or for testing purposes).
        - Clear the entire cache (e.g., at application startup or teardown).

    Args:
        symbol: If provided (as a ticker string), only that symbol's cache
                entry is removed. If None, the entire cache is cleared.

    Example:
        clear_cache("AAPL")     # Invalidate Apple only
        clear_cache()           # Flush the entire cache
    """
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
