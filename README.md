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
└── README.md
```

Each agent has its own code, dependencies, config template, and README.

---

## Adding a New Agent

1. Create a folder under `agents/` with a `-bear` suffix
2. Add your code, `requirements.txt`, and `README.md`
3. If something can be reused across agents, move it to `shared/`

---

> Focused over bloated. Each bear does one job and does it well. 🐻
