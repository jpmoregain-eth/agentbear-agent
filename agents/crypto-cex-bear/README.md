# 🐻 crypto-cex-bear

Scans Binance for trading opportunities and delivers insights via Telegram, powered by Claude.

## What It Does

Monitors the top 20 Binance pairs for:
- **High volatility** — pairs moving >3% in 24h
- **Wide spreads** — unusual bid-ask gaps
- **Volume anomalies** — abnormal trading activity

## Quick Start
```bash
pip install -r requirements.txt
cp bond_config.example.yaml bond_config.yaml
nano bond_config.yaml   # add your API keys
python telegram_bot.py
```

## Telegram Commands

| Command | What it does |
|---------|-------------|
| `/opportunities` | Scans top 20 pairs |
| `/analyze BTCUSDT` | Deep dive into a pair |
| `/status` | Check agent status |
| `/help` | Show all commands |

## Security
Never commit `bond_config.yaml` with real keys — it's already in `.gitignore`.

---
*Not financial advice. DYOR always. 🐻*
