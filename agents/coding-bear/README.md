# coding-bear 🤖

A coding agent for AgentBear that helps with code review, debugging, refactoring, and development tasks.

## Features

- 🔍 **Code Review** - Analyze code for bugs, security issues, and best practices
- 🐛 **Debugging** - Help diagnose and fix errors
- ♻️ **Refactoring** - Suggest and apply code improvements
- 📚 **Documentation** - Generate docs and comments
- 🧪 **Testing** - Create unit tests and test cases
- 💬 **Telegram Interface** - Chat with your coding assistant

## Capabilities

- Analyze Python, JavaScript, TypeScript, Go, Rust, and more
- GitHub integration for PR reviews
- Local file system analysis
- Context-aware suggestions
- Memory of your codebase patterns

## Quick Start

1. Copy config: `cp bond_config.example.yaml bond_config.yaml`
2. Add your API keys (Claude/OpenAI)
3. Run: `python coding_agent.py`
4. Chat on Telegram!

## Commands

- `review <file>` - Review code file
- `debug <error>` - Debug an error
- `refactor <file>` - Suggest refactoring
- `test <file>` - Generate tests
- `docs <file>` - Generate documentation
- `explain <code>` - Explain code snippet