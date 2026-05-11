# Crypto Market Data MCP Server

An MCP (Model Context Protocol) server that provides real-time cryptocurrency market data using the [CoinGecko API](https://www.coingecko.com/en/api) — **completely free, no API key required** (50 requests/min).

## Features

- **Live prices** — current price, market cap, 24h volume, 24h change for any coin
- **Top coins** — ranked by market cap (customizable count)
- **Search** — find coins by name or symbol
- **Trending** — see what's hot on CoinGecko right now
- **Historical data** — price charts over custom time ranges (1 day to 1 year)

## Requirements

- Python 3.10+
- pip

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Start the MCP server

```bash
python server.py
```

The server communicates over **stdio** — it's designed to be used by MCP-compatible clients (e.g., Claude Desktop, Cursor, VS Code via `@modelcontextprotocol`).

### Client Configuration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "crypto-market-data": {
      "command": "python",
      "args": ["/path/to/crypto-market-mcp/server.py"]
    }
  }
}
```

## Tools

### 1. `crypto_price`

Get real-time price + market data for a specific coin.

| Parameter     | Type   | Default | Description                                    |
|---------------|--------|---------|------------------------------------------------|
| `coin_id`     | string | —       | CoinGecko coin ID (e.g. `bitcoin`, `ethereum`) |
| `vs_currency` | string | `usd`   | Target currency (usd, eur, gbp, jpy, etc.)     |

### 2. `crypto_top`

List top N coins by market cap.

| Parameter     | Type   | Default | Description                               |
|---------------|--------|---------|-------------------------------------------|
| `limit`       | number | `10`    | Number of coins (1–100)                   |
| `vs_currency` | string | `usd`   | Target currency                           |

### 3. `crypto_search`

Search coins by name or ticker symbol.

| Parameter | Type   | Default | Description                  |
|-----------|--------|---------|------------------------------|
| `query`   | string | —       | Name or symbol (e.g. `sol`) |

### 4. `crypto_trending`

See what's trending on CoinGecko right now. No parameters.

### 5. `crypto_historical`

Get historical price data points for a coin.

| Parameter | Type   | Default | Description                                      |
|-----------|--------|---------|--------------------------------------------------|
| `coin_id` | string | —       | CoinGecko coin ID                                |
| `days`    | number | `7`     | Days of history (1, 7, 14, 30, 90, 180, 365)    |

## Rate Limits

CoinGecko free tier allows **50 calls per minute** per IP. This server does not add caching — consider adding a reverse proxy or cache if you exceed that rate.

## Deployment (Smithery)

This server is configured for [Smithery](https://smithery.ai/). The `smithery.yaml` is included — just connect your GitHub repo on Smithery and it'll work out of the box.

## Pricing & Licensing

**$19/month** for premium support or self-hosted deployment assistance.

- [Subscribe here](https://buy.stripe.com/dRm6oJ4Hd2Jugek0wz1oI0m)

## License

MIT
