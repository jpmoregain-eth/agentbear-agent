# 🐻 AgentBear

A collection of focused AI agents, each built to do one thing well.

Every agent follows the `-bear` naming convention and lives in its own folder under `agents/`.

---

## Agents

| Agent | Description | Status |
|-------|-------------|--------|
| [crypto-cex-bear](./agents/crypto-cex-bear) | Binance market analyzer via Telegram | ✅ Live |

---

## Structure

```
agentbear-agent/
├── agents/
│   └── crypto-cex-bear/   ← each agent is self-contained
├── shared/                ← common utilities (coming soon)
└── README.md              ← you are here
```

Each agent has its own:
- Code
- Dependencies (`requirements.txt`)
- Config template
- README with setup instructions

---

## Adding a New Agent

1. Create a new folder under `agents/` with a `-bear` suffix
   ```
   mkdir agents/your-agent-bear
   ```
2. Add your code, a `requirements.txt`, and a `README.md`
3. If something can be reused across agents, move it to `shared/`

---

## Philosophy

> Focused over bloated. Each bear does one job and does it well.

---

*Not financial advice. DYOR always. 🐻*
