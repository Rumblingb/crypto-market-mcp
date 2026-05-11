"""
Crypto/Stock Market Data MCP Server
Provides real-time crypto market data via the CoinGecko API (free tier, no API key needed).
Runs as an MCP (Model Context Protocol) server with 5 tools.
"""

import json
import httpx
from typing import Any
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent

# ── CoinGecko API Base ──────────────────────────────────────────────────────
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEFAULT_CURRENCY = "usd"
MAX_TOOLS = 5

server = Server("crypto-market-data")


def _request(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make a GET request to CoinGecko and return parsed JSON."""
    url = f"{COINGECKO_BASE}{path}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "crypto-market-mcp/1.0",
    }
    # CoinGecko free tier: 50 calls/min, no API key required
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        detail = exc.response.text[:500]
        if status == 429:
            raise RuntimeError(
                "CoinGecko rate limit hit (50 req/min). Wait and retry."
            ) from exc
        raise RuntimeError(
            f"CoinGecko API error {status}: {detail}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Network error contacting CoinGecko: {exc}") from exc


def _fmt_price(price: Any) -> str:
    """Format a price number for display."""
    if price is None:
        return "N/A"
    if isinstance(price, (int, float)):
        if price < 0.001:
            return f"${price:.8f}"
        if price < 1:
            return f"${price:.6f}"
        if price < 1000:
            return f"${price:.2f}"
        return f"${price:,.2f}"
    return str(price)


def _fmt_percent(val: Any) -> str:
    """Format a percentage change value."""
    if val is None:
        return "N/A"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"


def _fmt_big(val: Any) -> str:
    """Format a large number (market cap, volume) into human-readable string."""
    if val is None:
        return "N/A"
    try:
        v = float(val)
    except (ValueError, TypeError):
        return str(val)
    if v >= 1_000_000_000_000:
        return f"${v / 1_000_000_000_000:.2f}T"
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v / 1_000:.2f}K"
    return f"${v:.2f}"


# ── Tool Implementations ────────────────────────────────────────────────────

def tool_crypto_price(coin_id: str, vs_currency: str = DEFAULT_CURRENCY) -> str:
    """
    Get current price, market cap, volume, and 24h change for a specific coin.
    
    Args:
        coin_id: CoinGecko coin ID (e.g. 'bitcoin', 'ethereum')
        vs_currency: Target currency (e.g. 'usd', 'eur', 'gbp')
    """
    data = _request(f"/simple/price", {
        "ids": coin_id.lower(),
        "vs_currencies": vs_currency.lower(),
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
    })
    
    if coin_id.lower() not in data:
        return f"❌ Coin '{coin_id}' not found. Use crypto_search to find the correct coin_id."
    
    coin = data[coin_id.lower()]
    price = coin.get(vs_currency.lower())
    mcap = coin.get(f"{vs_currency.lower()}_market_cap")
    vol = coin.get(f"{vs_currency.lower()}_24h_vol")
    change = coin.get(f"{vs_currency.lower()}_24h_change")
    
    lines = [
        f"📊 {coin_id.capitalize()} — {vs_currency.upper()}",
        f"   Price:      {_fmt_price(price)}",
        f"   Market Cap: {_fmt_big(mcap)}",
        f"   24h Vol:    {_fmt_big(vol)}",
        f"   24h Change: {_fmt_percent(change)}",
    ]
    return "\n".join(lines)


def tool_crypto_top(limit: int = 10, vs_currency: str = DEFAULT_CURRENCY) -> str:
    """
    Get top N cryptocurrencies by market cap.
    
    Args:
        limit: Number of coins to return (1-100, default 10)
        vs_currency: Target currency (e.g. 'usd', 'eur', 'gbp')
    """
    limit = max(1, min(100, limit))
    data = _request("/coins/markets", {
        "vs_currency": vs_currency.lower(),
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": "false",
    })
    
    if not data:
        return "No data returned from CoinGecko."
    
    lines = [f"🏆 Top {limit} Cryptocurrencies by Market Cap ({vs_currency.upper()})\n"]
    for i, coin in enumerate(data, 1):
        name = coin.get("name", "?")
        symbol = coin.get("symbol", "?").upper()
        price = _fmt_price(coin.get("current_price"))
        mcap = _fmt_big(coin.get("market_cap"))
        change = _fmt_percent(coin.get("price_change_percentage_24h"))
        lines.append(f"  {i:2d}. {symbol:6s} {name:20s}  {price:>14s}  MCap {mcap:>8s}  {change:>8s}")
    
    return "\n".join(lines)


def tool_crypto_search(query: str) -> str:
    """
    Search for coins by name or symbol.
    
    Args:
        query: Search query (coin name or symbol)
    """
    data = _request("/search", {"query": query.strip()})
    coins = data.get("coins", [])
    
    if not coins:
        return f"No coins found matching '{query}'."
    
    # Limit to top 15 results for readability
    top = coins[:15]
    lines = [f"🔍 Search results for '{query}' ({len(coins)} total)\n"]
    for c in top:
        cid = c.get("id", "?")
        name = c.get("name", "?")
        symbol = c.get("symbol", "?").upper()
        market_rank = c.get("market_cap_rank")
        rank_str = f"#{market_rank}" if market_rank else "-"
        lines.append(f"  {rank_str:>4s}  {symbol:6s}  {name:25s}  (id: {cid})")
    
    return "\n".join(lines)


def tool_crypto_trending() -> str:
    """Get trending coins on CoinGecko right now."""
    data = _request("/search/trending")
    coins = data.get("coins", [])
    
    if not coins:
        return "No trending data available right now."
    
    lines = ["🔥 Trending Cryptocurrencies Right Now\n"]
    for i, entry in enumerate(coins[:15], 1):
        item = entry.get("item", {})
        name = item.get("name", "?")
        symbol = item.get("symbol", "?").upper()
        cid = item.get("id", "?")
        market_rank = item.get("market_cap_rank")
        price_btc = item.get("price_btc")
        
        rank_str = f"#{market_rank}" if market_rank else "-"
        btc_str = f"  BTC: {price_btc:.12f}" if price_btc else ""
        lines.append(f"  {i:2d}. {symbol:6s} {name:25s}  Rank {rank_str:>5s}{btc_str}  (id: {cid})")
    
    return "\n".join(lines)


def tool_crypto_historical(coin_id: str, days: int = 7) -> str:
    """
    Get historical price data for a coin.
    
    Args:
        coin_id: CoinGecko coin ID (e.g. 'bitcoin', 'ethereum')
        days: Number of days of historical data (1, 7, 14, 30, 90, 180, 365, 'max')
    """
    data = _request(f"/coins/{coin_id.lower()}/market_chart", {
        "vs_currency": DEFAULT_CURRENCY,
        "days": str(days),
    })
    
    prices = data.get("prices", [])
    if not prices:
        return f"No historical data returned for '{coin_id}'."
    
    # Extract meaningful sample points
    # For a clean report, use first, last, and periodic samples
    n = len(prices)
    period = max(1, n // 10)  # Show ~10 points
    
    lines = [f"📈 Historical Price Data for {coin_id.capitalize()} — last {days} day(s) ({DEFAULT_CURRENCY.upper()})\n"]
    lines.append(f"  {'Date':<16s}  {'Price':>14s}  {'Change':>10s}")
    lines.append(f"  {'────':<16s}  {'─────':>14s}  {'──────':>10s}")
    
    from datetime import datetime, timezone
    
    prev = None
    for idx in range(0, n, period):
        ts_ms, price_val = prices[idx]
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        price_str = _fmt_price(price_val)
        
        if prev is not None:
            pct = ((price_val - prev) / prev) * 100
            change_str = _fmt_percent(pct)
        else:
            change_str = "—"
        
        lines.append(f"  {dt:<16s}  {price_str:>14s}  {change_str:>10s}")
        prev = price_val
    
    # Also show latest
    ts_ms, price_val = prices[-1]
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    price_str = _fmt_price(price_val)
    if prev is not None and len(prices) > 1:
        pct = ((price_val - prev) / prev) * 100
        change_str = _fmt_percent(pct)
    else:
        change_str = "—"
    
    if (n - 1) % period != 0:
        lines.append(f"  {dt:<16s}  {price_str:>14s}  {change_str:>10s}")
    
    # Summary stats
    vals = [p[1] for p in prices]
    low = min(vals)
    high = max(vals)
    first_val = vals[0]
    last_val = vals[-1]
    total_change = ((last_val - first_val) / first_val) * 100
    
    lines.append("")
    lines.append(f"  📊 Summary:")
    lines.append(f"     Low:    {_fmt_price(low)}")
    lines.append(f"     High:   {_fmt_price(high)}")
    lines.append(f"     Start:  {_fmt_price(first_val)}")
    lines.append(f"     End:    {_fmt_price(last_val)}")
    lines.append(f"     Change: {_fmt_percent(total_change)}")
    
    return "\n".join(lines)


# ── MCP Tool Definitions ────────────────────────────────────────────────────

TOOLS: list[Tool] = [
    Tool(
        name="crypto_price",
        description="Get current price, market cap, volume, and 24h change for a cryptocurrency using CoinGecko",
        inputSchema={
            "type": "object",
            "properties": {
                "coin_id": {
                    "type": "string",
                    "description": "CoinGecko coin ID (e.g. 'bitcoin', 'ethereum', 'solana')",
                },
                "vs_currency": {
                    "type": "string",
                    "description": "Target currency (default: 'usd'). Options: usd, eur, gbp, jpy, etc.",
                    "default": DEFAULT_CURRENCY,
                },
            },
            "required": ["coin_id"],
        },
    ),
    Tool(
        name="crypto_top",
        description="Get top N cryptocurrencies by market cap",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of coins to return (1-100, default 10)",
                    "default": 10,
                },
                "vs_currency": {
                    "type": "string",
                    "description": "Target currency (default: 'usd')",
                    "default": DEFAULT_CURRENCY,
                },
            },
        },
    ),
    Tool(
        name="crypto_search",
        description="Search for cryptocurrencies by name or symbol",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (coin name or symbol, e.g. 'bitcoin', 'eth', 'sol')",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="crypto_trending",
        description="Get trending cryptocurrencies on CoinGecko right now",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="crypto_historical",
        description="Get historical price data for a cryptocurrency over a specified number of days",
        inputSchema={
            "type": "object",
            "properties": {
                "coin_id": {
                    "type": "string",
                    "description": "CoinGecko coin ID (e.g. 'bitcoin', 'ethereum')",
                },
                "days": {
                    "type": "number",
                    "description": "Number of days of historical data (1, 7, 14, 30, 90, 180, 365, or 'max')",
                    "default": 7,
                },
            },
            "required": ["coin_id"],
        },
    ),
]


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "crypto_price":
            coin_id = arguments.get("coin_id", "")
            vs_currency = arguments.get("vs_currency", DEFAULT_CURRENCY)
            result = tool_crypto_price(coin_id, vs_currency)
        elif name == "crypto_top":
            limit = arguments.get("limit", 10)
            vs_currency = arguments.get("vs_currency", DEFAULT_CURRENCY)
            result = tool_crypto_top(limit, vs_currency)
        elif name == "crypto_search":
            query = arguments.get("query", "")
            result = tool_crypto_search(query)
        elif name == "crypto_trending":
            result = tool_crypto_trending()
        elif name == "crypto_historical":
            coin_id = arguments.get("coin_id", "")
            days = arguments.get("days", 7)
            result = tool_crypto_historical(coin_id, days)
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=result)]
    except (RuntimeError, ValueError) as e:
        return [TextContent(type="text", text=f"❌ Error: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Unexpected error: {e}")]


async def main() -> None:
    """Run the MCP server using stdio transport."""
    async with server.run_stdio() as running:
        await running.wait_for_shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
