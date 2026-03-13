"""
Coding Bear Agent - AI-powered coding assistant
Analyzes code, writes new code, edits files, and syncs with GitHub
"""

import os
import sys
import yaml
import json
import logging
import subprocess
import shutil
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import anthropic
import openai
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.prompt import Confirm

from memory import CodeMemory
from code_analyzer import CodeAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
console = Console()


@dataclass
class AgentConfig:
    """Configuration for Coding Bear Agent"""
    name: str = "coding-bear"
    version: str = "0.1.0"
    model_provider: str = "anthropic"  # or "openai"
    model_name: str = "claude-3-5-sonnet-20241022"
    api_key: str = ""
    telegram_token: str = ""
    github_token: str = ""
    memory_enabled: bool = True
    max_context_lines: int = 100
    review_strictness: str = "medium"  # low, medium, high


class CodingBearAgent:
    """
    Main coding agent class
    Handles code analysis, review, debugging, and refactoring
    """
    
    def __init__(self, config_path: str = "bond_config.yaml"):
        self.config = self._load_config(config_path)
        self.memory = CodeMemory() if self.config.memory_enabled else None
        self.analyzer = CodeAnalyzer()
        self._setup_llm()
        
    def _load_config(self, config_path: str) -> AgentConfig:
        """Load configuration from YAML file"""
        if not os.path.exists(config_path):
            console.print(f"[red]Config file not found: {config_path}[/red]")
            console.print("[yellow]Copy bond_config.example.yaml to bond_config.yaml and fill in your API keys[/yellow]")
            sys.exit(1)
            
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
            
        # Map from bond_config structure
        agent_config = AgentConfig()
        agent_config.name = config_dict.get('agent', {}).get('name', 'coding-bear')
        
        model_config = config_dict.get('model', {})
        agent_config.model_provider = model_config.get('provider', 'anthropic')
        agent_config.model_name = model_config.get('name', 'claude-3-5-sonnet-20241022')
        
        if agent_config.model_provider == 'anthropic':
            agent_config.api_key = model_config.get('anthropic_api_key', '')
        else:
            agent_config.api_key = model_config.get('openai_api_key', '')
            
        agent_config.telegram_token = config_dict.get('telegram', {}).get('bot_token', '')
        agent_config.github_token = config_dict.get('github', {}).get('token', '')
        agent_config.memory_enabled = config_dict.get('memory', {}).get('enabled', True)
        
        return agent_config
    
    def _setup_llm(self):
        """Initialize LLM client"""
        if self.config.model_provider == 'anthropic':
            if not self.config.api_key:
                raise ValueError("Anthropic API key not configured")
            self.client = anthropic.Anthropic(api_key=self.config.api_key)
        else:
            if not self.config.api_key:
                raise ValueError("OpenAI API key not configured")
            openai.api_key = self.config.api_key
            self.client = openai
    
    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 4000) -> str:
        """Call LLM with prompt"""
        try:
            if self.config.model_provider == 'anthropic':
                response = self.client.messages.create(
                    model=self.config.model_name,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                return response.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Error: {str(e)}"
    
    def analyze_code(self, file_path: str, code: str = None) -> Dict[str, Any]:
        """Analyze code for issues, patterns, and improvements"""
        if code is None:
            with open(file_path, 'r') as f:
                code = f.read()
        
        console.print(f"[blue]Analyzing {file_path}...[/blue]")
        
        # Basic analysis
        analysis = self.analyzer.analyze(code, file_path)
        
        # LLM-powered deep analysis
        system_prompt = """You are an expert code reviewer. Analyze the provided code and return a JSON response with:
- issues: list of issues found (severity, line, description, suggestion)
- patterns: design patterns identified
- complexity: complexity score (1-10)
- suggestions: refactoring suggestions
- security: security concerns

Respond in valid JSON only."""
        
        user_prompt = f"Analyze this code:\n\n```{self._get_language(file_path)}\n{code[:8000]}\n```"
        
        llm_response = self._call_llm(system_prompt, user_prompt)
        
        try:
            deep_analysis = json.loads(llm_response)
        except json.JSONDecodeError:
            deep_analysis = {"raw_response": llm_response}
        
        # Store in memory
        if self.memory:
            self.memory.store_analysis(file_path, {**analysis, **deep_analysis})
        
        return {**analysis, **deep_analysis}
    
    def review_code(self, file_path: str, code: str = None) -> str:
        """Perform comprehensive code review"""
        if code is None:
            with open(file_path, 'r') as f:
                code = f.read()
        
        analysis = self.analyze_code(file_path, code)
        
        system_prompt = """You are a senior software engineer doing a code review. Provide:
1. Overall assessment
2. Critical issues (must fix)
3. Warnings (should fix)
4. Suggestions (nice to have)
5. Positive feedback (what's done well)

Be constructive and specific."""
        
        user_prompt = f"Review this code:\n\n```{self._get_language(file_path)}\n{code[:8000]}\n```\n\nAnalysis: {json.dumps(analysis, indent=2)}"
        
        review = self._call_llm(system_prompt, user_prompt)
        
        console.print(Panel(Markdown(review), title=f"Code Review: {file_path}", border_style="green"))
        
        return review
    
    def debug_error(self, error_message: str, code: str = None, context: str = None) -> str:
        """Help debug an error"""
        console.print(f"[yellow]Debugging error...[/yellow]")
        
        system_prompt = """You are a debugging expert. Analyze the error and provide:
1. Root cause explanation
2. Exact fix needed
3. Prevention tips
4. Related issues to check

Be specific about line numbers and code changes."""
        
        user_prompt = f"Error: {error_message}\n"
        if code:
            user_prompt += f"\nCode:\n```\n{code[:5000]}\n```"
        if context:
            user_prompt += f"\nContext: {context}"
        
        debug_response = self._call_llm(system_prompt, user_prompt)
        
        console.print(Panel(Markdown(debug_response), title="Debug Analysis", border_style="yellow"))
        
        return debug_response
    
    def refactor_code(self, file_path: str, code: str = None, goal: str = "improve") -> str:
        """Refactor code based on goal"""
        if code is None:
            with open(file_path, 'r') as f:
                code = f.read()
        
        console.print(f"[blue]Refactoring {file_path} for: {goal}...[/blue]")
        
        system_prompt = f"""You are a refactoring expert. Refactor the code to {goal}.
Provide:
1. Explanation of changes
2. Refactored code
3. Benefits of the changes

Return the complete refactored code that can be used directly."""
        
        user_prompt = f"Refactor this code:\n\n```{self._get_language(file_path)}\n{code[:8000]}\n```"
        
        refactored = self._call_llm(system_prompt, user_prompt, max_tokens=6000)
        
        console.print(Panel(Syntax(refactored, self._get_language(file_path)), title="Refactored Code", border_style="cyan"))
        
        return refactored
    
    def generate_tests(self, file_path: str, code: str = None) -> str:
        """Generate unit tests for code"""
        if code is None:
            with open(file_path, 'r') as f:
                code = f.read()
        
        console.print(f"[blue]Generating tests for {file_path}...[/blue]")
        
        system_prompt = """You are a testing expert. Generate comprehensive unit tests.
Include:
- Edge cases
- Error cases
- Happy path tests
- Mocking if needed

Use appropriate testing framework for the language."""
        
        user_prompt = f"Generate tests for:\n\n```{self._get_language(file_path)}\n{code[:8000]}\n```"
        
        tests = self._call_llm(system_prompt, user_prompt, max_tokens=6000)
        
        console.print(Panel(Syntax(tests, self._get_language(file_path)), title="Generated Tests", border_style="green"))
        
        return tests
    
    def explain_code(self, code: str, detail_level: str = "medium") -> str:
        """Explain code in natural language"""
        system_prompt = f"""Explain the provided code at {detail_level} detail level.
Include:
1. What the code does
2. How it works step by step
3. Key concepts/algorithms used
4. Potential gotchas"""
        
        user_prompt = f"Explain this code:\n\n```\n{code[:5000]}\n```"
        
        explanation = self._call_llm(system_prompt, user_prompt)
        
        console.print(Panel(Markdown(explanation), title="Code Explanation", border_style="blue"))
        
        return explanation
    
    def _get_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.sql': 'sql',
            '.sh': 'bash',
            '.yaml': 'yaml',
            '.json': 'json',
            '.md': 'markdown'
        }
        return lang_map.get(ext, 'text')
    
    def interactive_mode(self):
        """Run interactive coding session"""
        console.print(Panel.fit(
            "[bold green]🐻 Coding Bear Agent[/bold green]\n"
            "Your AI coding assistant is ready!\n\n"
            "Commands:\n"
            "  generate <desc>   - Generate new code\n"
            "  implement <file>  - Add feature to file\n"
            "  review <file>     - Review code\n"
            "  debug <error>     - Debug error\n"
            "  refactor <file>   - Refactor code\n"
            "  edit <file>       - Edit file\n"
            "  test <file>       - Generate tests\n"
            "  read <file>       - Read file\n"
            "  git <cmd>         - Git operations\n"
            "  help              - Show help\n"
            "  exit              - Quit",
            title="Coding Bear",
            border_style="green"
        ))
        
        while True:
            try:
                user_input = console.input("[bold green]coding-bear>[/bold green] ").strip()
                
                if not user_input:
                    continue
                
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                if command == 'exit':
                    console.print("[green]Goodbye! 👋[/green]")
                    break
                elif command == 'help':
                    self._show_help()
                elif command == 'generate':
                    self.generate_code(arg)
                elif command == 'implement':
                    impl_parts = arg.split(maxsplit=1)
                    if len(impl_parts) == 2:
                        self.implement_feature(impl_parts[0], impl_parts[1])
                    else:
                        console.print("[red]Usage: implement <file> <feature description>[/red]")
                elif command == 'review':
                    if os.path.exists(arg):
                        self.review_code(arg)
                    else:
                        console.print("[red]File not found[/red]")
                elif command == 'debug':
                    self.debug_error(arg)
                elif command == 'refactor':
                    if os.path.exists(arg):
                        self.refactor_code(arg)
                    else:
                        console.print("[red]File not found[/red]")
                elif command == 'edit':
                    edit_parts = arg.split(maxsplit=1)
                    if len(edit_parts) == 2:
                        self.edit_file(edit_parts[0], edit_parts[1])
                    else:
                        console.print("[red]Usage: edit <file> <changes description>[/red]")
                elif command == 'test':
                    if os.path.exists(arg):
                        self.generate_tests(arg)
                    else:
                        console.print("[red]File not found[/red]")
                elif command == 'explain':
                    self.explain_code(arg)
                elif command == 'read':
                    self.read_file(arg)
                elif command == 'git':
                    git_parts = arg.split(maxsplit=1)
                    git_cmd = git_parts[0] if git_parts else ""
                    git_arg = git_parts[1] if len(git_parts) > 1 else ""
                    
                    if git_cmd == 'status':
                        self.git_status()
                    elif git_cmd == 'commit':
                        if git_arg:
                            self.git_commit(git_arg)
                        else:
                            console.print("[red]Usage: git commit <message>[/red]")
                    elif git_cmd == 'push':
                        self.git_push()
                    elif git_cmd == 'pull':
                        self.git_pull()
                    else:
                        console.print("[red]Git commands: status, commit <msg>, push, pull[/red]")
                else:
                    # General question
                    response = self._call_llm(
                        "You are a helpful coding assistant. Answer the user's question concisely.",
                        user_input
                    )
                    console.print(Markdown(response))
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    
    def _show_help(self):
        """Show help information"""
        help_text = """
# Coding Bear Commands

## Code Generation
- `generate <description>` - Write new code from scratch
  Example: `generate "a Python script to scrape Hacker News"`

- `implement <feature>` - Add feature to existing file
  Example: `implement add error handling to main.py`

## File Operations
- `write <file> <code>` - Write code to file
- `edit <file> <changes>` - Edit existing file
- `read <file>` - Read file contents

## Git Operations
- `git status` - Check repository status
- `git commit <message>` - Commit changes
- `git push` - Push to remote
- `git pull` - Pull from remote

## Code Review & Analysis
- `review <file>` - Comprehensive code review
- `debug <error>` - Debug errors
- `refactor <file>` - Improve code quality
- `test <file>` - Generate unit tests
- `explain <code>` - Explain what code does

## General
- Just type any coding question!
        """
        console.print(Markdown(help_text))

    def generate_code(self, description: str, language: str = "python", save_path: str = None) -> str:
        """Generate new code from description"""
        console.print(f"[blue]Generating {language} code...[/blue]")
        
        system_prompt = f"""You are an expert {language} developer. 
Write clean, well-documented, production-ready code based on the user's description.
Include:
- Proper error handling
- Type hints (if applicable)
- Docstrings/comments
- Best practices for the language

Output ONLY the code, no explanations."""

        user_prompt = f"Write {language} code for: {description}"
        
        code = self._call_llm(system_prompt, user_prompt, max_tokens=6000)
        
        console.print(Panel(Syntax(code, language), title="Generated Code", border_style="green"))
        
        # Offer to save
        if save_path or Confirm.ask("Save to file?", default=False):
            if not save_path:
                save_path = console.input("Enter file path: ")
            self.write_file(save_path, code)
        
        return code

    def implement_feature(self, file_path: str, feature_description: str) -> str:
        """Implement a new feature in existing file"""
        if not os.path.exists(file_path):
            console.print(f"[red]File not found: {file_path}[/red]")
            return ""
        
        with open(file_path, 'r') as f:
            existing_code = f.read()
        
        console.print(f"[blue]Implementing feature in {file_path}...[/blue]")
        
        system_prompt = """You are a senior software engineer. Implement the requested feature
in the existing code. Return the COMPLETE updated file with the new feature integrated.
Maintain existing code style and patterns."""

        user_prompt = f"""Existing code:
```
{existing_code}
```

Feature to implement: {feature_description}

Return the complete updated file."""

        updated_code = self._call_llm(system_prompt, user_prompt, max_tokens=6000)
        
        # Extract code from markdown if present
        if "```" in updated_code:
            lines = updated_code.split('\n')
            in_code = False
            code_lines = []
            for line in lines:
                if line.startswith('```'):
                    in_code = not in_code
                    continue
                if in_code:
                    code_lines.append(line)
            updated_code = '\n'.join(code_lines)
        
        console.print(Panel(
            Syntax(updated_code, self._get_language(file_path)), 
            title=f"Updated: {file_path}", 
            border_style="cyan"
        ))
        
        if Confirm.ask(f"Save changes to {file_path}?", default=True):
            self.write_file(file_path, updated_code)
            console.print(f"[green]✓ Saved to {file_path}[/green]")
        
        return updated_code

    def write_file(self, file_path: str, content: str):
        """Write content to file"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            f.write(content)
        
        console.print(f"[green]✓ Written {len(content)} characters to {file_path}[/green]")
        
        # Track in memory
        if self.memory:
            self.memory.store_file_write(file_path, len(content))

    def edit_file(self, file_path: str, edit_description: str):
        """Edit file based on description"""
        if not os.path.exists(file_path):
            console.print(f"[red]File not found: {file_path}[/red]")
            return
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        system_prompt = """You are a precise code editor. Make ONLY the requested changes.
Return the COMPLETE updated file with your changes applied."""

        user_prompt = f"""File: {file_path}

Current content:
```
{content}
```

Changes to make: {edit_description}

Return the complete updated file."""

        updated = self._call_llm(system_prompt, user_prompt, max_tokens=6000)
        
        # Clean up markdown
        if "```" in updated:
            lines = updated.split('\n')
            in_code = False
            result = []
            for line in lines:
                if line.startswith('```'):
                    in_code = not in_code
                    continue
                if in_code:
                    result.append(line)
            updated = '\n'.join(result)
        
        # Show diff
        self._show_diff(content, updated, file_path)
        
        if Confirm.ask("Apply changes?", default=True):
            backup_path = f"{file_path}.backup"
            shutil.copy(file_path, backup_path)
            self.write_file(file_path, updated)
            console.print(f"[green]✓ Changes applied (backup: {backup_path})[/green]")

    def _show_diff(self, old: str, new: str, file_path: str):
        """Show diff between old and new code"""
        import difflib
        diff = list(difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"{file_path} (old)",
            tofile=f"{file_path} (new)"
        ))
        
        if diff:
            console.print(Panel(
                ''.join(diff)[:4000],
                title="Changes",
                border_style="yellow"
            ))
        else:
            console.print("[yellow]No changes detected[/yellow]")

    def read_file(self, file_path: str, limit: int = 100) -> str:
        """Read and display file"""
        if not os.path.exists(file_path):
            console.print(f"[red]File not found: {file_path}[/red]")
            return ""
        
        with open(file_path, 'r') as f:
            lines = f.readlines()[:limit]
            content = ''.join(lines)
        
        console.print(Panel(
            Syntax(content, self._get_language(file_path)),
            title=file_path,
            border_style="blue"
        ))
        
        return content

    def git_status(self):
        """Show git status"""
        try:
            result = subprocess.run(
                ['git', 'status'],
                capture_output=True,
                text=True,
                check=True
            )
            console.print(Panel(
                result.stdout,
                title="Git Status",
                border_style="purple"
            ))
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Git error: {e.stderr}[/red]")

    def git_commit(self, message: str):
        """Commit changes"""
        try:
            # Stage all changes
            subprocess.run(['git', 'add', '-A'], check=True)
            # Commit
            subprocess.run(['git', 'commit', '-m', message], check=True)
            console.print(f"[green]✓ Committed: {message}[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Git commit failed: {e}[/red]")

    def git_push(self):
        """Push to remote"""
        try:
            result = subprocess.run(
                ['git', 'push'],
                capture_output=True,
                text=True,
                check=True
            )
            console.print("[green]✓ Pushed to remote[/green]")
            if result.stdout:
                console.print(result.stdout)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Git push failed: {e.stderr}[/red]")

    def git_pull(self):
        """Pull from remote"""
        try:
            result = subprocess.run(
                ['git', 'pull'],
                capture_output=True,
                text=True,
                check=True
            )
            console.print("[green]✓ Pulled from remote[/green]")
            if result.stdout:
                console.print(result.stdout)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Git pull failed: {e.stderr}[/red]")


def start_telegram_bot(config_path):
    """Check if Telegram should be started and return True if started"""
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f) or {}
    except:
        return False
    
    telegram_config = config_data.get('telegram', {})
    telegram_enabled = telegram_config.get('enabled', False)
    telegram_token = telegram_config.get('bot_token', '')
    
    if not telegram_enabled or not telegram_token:
        return False
    
    return True


def run_telegram_only(config_path):
    """Run only Telegram bot (blocks)"""
    console.print("[green]✓ Starting Telegram bot...[/green]")
    try:
        from telegram_bot import CodingBearTelegramBot
        bot = CodingBearTelegramBot()
        bot.run()
    except Exception as e:
        console.print(f"[red]✗ Failed to start Telegram bot: {e}[/red]")
        logger.error(f"Telegram bot error: {e}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Coding Bear Agent')
    parser.add_argument('--config', default='bond_config.yaml', help='Config file path')
    parser.add_argument('--review', help='Review a file')
    parser.add_argument('--debug', help='Debug an error')
    parser.add_argument('--refactor', help='Refactor a file')
    parser.add_argument('--test', help='Generate tests for file')
    parser.add_argument('--generate', '-g', help='Generate code from description')
    parser.add_argument('--implement', nargs=2, metavar=('FILE', 'FEATURE'), help='Implement feature in file')
    parser.add_argument('--edit', nargs=2, metavar=('FILE', 'CHANGES'), help='Edit file')
    parser.add_argument('--read', help='Read file contents')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--telegram', '-t', action='store_true', help='Run Telegram bot only (blocks)')
    parser.add_argument('--no-telegram', action='store_true', help='Skip auto-starting Telegram bot')
    
    args = parser.parse_args()
    
    # Check if Telegram should auto-start
    telegram_configured = start_telegram_bot(args.config)
    
    # If --telegram flag or auto-start and not disabled
    if args.telegram or (telegram_configured and not args.no_telegram):
        run_telegram_only(args.config)
        return  # Don't go into interactive mode
    
    # Otherwise run interactive mode
    agent = CodingBearAgent(args.config)
    
    if args.review:
        agent.review_code(args.review)
    elif args.debug:
        agent.debug_error(args.debug)
    elif args.refactor:
        agent.refactor_code(args.refactor)
    elif args.test:
        agent.generate_tests(args.test)
    elif args.generate:
        agent.generate_code(args.generate)
    elif args.implement:
        agent.implement_feature(args.implement[0], args.implement[1])
    elif args.edit:
        agent.edit_file(args.edit[0], args.edit[1])
    elif args.read:
        agent.read_file(args.read)
    else:
        agent.interactive_mode()


if __name__ == '__main__':
    main()