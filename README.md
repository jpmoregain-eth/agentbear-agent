# AgentBear CEX Agent - Week 1 MVP

🐻 **Lean, fast Binance market analyzer powered by Claude**

## Quick Start

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Run Setup
```bash
python3 setup.py
```

Browser opens to `http://localhost:5000` for configuration, or falls back to CLI.

### 3. Start Agent
```bash
python3 backend/telegram_bot.py
```

## Features

- Multi-step setup wizard with model selection (Claude, OpenAI, Kimi, Google)
- API key validation before saving
- Binance market analysis
- Telegram bot interface
- Local browser-based configuration

## Configuration

Setup creates `bond_config.yaml` with:
- Agent settings
- AI model selection
- API keys (dynamic based on model)
- Binance exchange settings
- Telegram bot token
- Local SQLite database

## Commands

Once running on Telegram:
- `/help` - Show available commands
- `/status` - Check agent status
- `/opportunities` - Find trading opportunities
- `/analyze <pair>` - Analyze specific pair

## Support

📖 Full docs available in README files and setup guides.

---

🚀 Happy trading! Remember: DYOR always.
