# 🐻 crypto-cex-bear

Scans Binance for trading opportunities and delivers insights via Telegram, powered by Claude.

---

## What It Does

Monitors the top 20 Binance pairs for:
- **High volatility** — pairs moving >3% in 24h
- **Wide spreads** — unusual bid-ask gaps
- **Volume anomalies** — abnormal trading activity

Claude analyzes the data and sends you a clean summary on Telegram.

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up your config
```bash
cp bond_config.example.yaml bond_config.yaml
nano bond_config.yaml
```

You'll need:
- **Binance API key** (read-only) — [Get it here](https://www.binance.com/en/account/api-management)
- **Claude API key** — [Get it here](https://console.anthropic.com/)
- **Telegram bot token** — Message @BotFather on Telegram

### 3. Run
```bash
python telegram_bot.py
```

---

## Telegram Commands

| Command | What it does |
|---------|-------------|
| `/opportunities` | Scans top 20 pairs for opportunities |
| `/analyze BTCUSDT` | Deep dive into a specific pair |
| `/status` | Check if the agent is running |
| `/help` | Show all commands |

---

## Architecture

```
telegram_bot.py     ← Telegram interface
    ↓
crypto_agent.py     ← Orchestrator
    ↓
binance_analyzer.py ← Fetches market data
    ↓
Claude              ← Analyzes + formats output
    ↓
memory.py           ← Stores history in SQLite
```

---

## Security

⚠️ Never commit `bond_config.yaml` with real keys. It's already in `.gitignore` — keep it that way.

---

*Not financial advice. DYOR always. 🐻*
