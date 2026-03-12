"""
Coding Bear Agent - AI-powered coding assistant
Analyzes code, reviews PRs, debugs errors, and helps with development
"""

import os
import sys
import yaml
import json
import logging
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
            "  review <file>     - Review code\n"
            "  debug <error>     - Debug error\n"
            "  refactor <file>   - Refactor code\n"
            "  test <file>       - Generate tests\n"
            "  explain <code>    - Explain code\n"
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
                elif command == 'test':
                    if os.path.exists(arg):
                        self.generate_tests(arg)
                    else:
                        console.print("[red]File not found[/red]")
                elif command == 'explain':
                    self.explain_code(arg)
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

## Code Review
- `review <file>` - Comprehensive code review
- Example: `review src/main.py`

## Debugging
- `debug <error message>` - Analyze and fix errors
- Example: `debug "TypeError: 'NoneType' object is not callable"`

## Refactoring
- `refactor <file>` - Improve code quality
- Example: `refactor old_script.py`

## Testing
- `test <file>` - Generate unit tests
- Example: `test utils.py`

## Explanation
- `explain <code snippet>` - Explain what code does
- Example: `explain "def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)"`

## General
- Just type any coding question!
        """
        console.print(Markdown(help_text))


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Coding Bear Agent')
    parser.add_argument('--config', default='bond_config.yaml', help='Config file path')
    parser.add_argument('--review', help='Review a file')
    parser.add_argument('--debug', help='Debug an error')
    parser.add_argument('--refactor', help='Refactor a file')
    parser.add_argument('--test', help='Generate tests for file')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    agent = CodingBearAgent(args.config)
    
    if args.review:
        agent.review_code(args.review)
    elif args.debug:
        agent.debug_error(args.debug)
    elif args.refactor:
        agent.refactor_code(args.refactor)
    elif args.test:
        agent.generate_tests(args.test)
    else:
        agent.interactive_mode()


if __name__ == '__main__':
    main()