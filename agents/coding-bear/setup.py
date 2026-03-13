"""
Setup Script for Coding Bear
Interactive CLI setup wizard
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, Any

# Rich for pretty UI
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()


def print_header():
    """Print welcome header"""
    console.print(Panel.fit(
        "[bold cyan]🐻 Coding Bear Setup[/bold cyan]\n"
        "AI Coding Assistant Configuration",
        box=box.ROUNDED,
        border_style="cyan"
    ))


def setup_model_config() -> Dict[str, Any]:
    """Setup model configuration"""
    console.print("\n[bold cyan]Step 1: AI Model Configuration[/bold cyan]\n")
    
    # Choose provider
    provider = Prompt.ask(
        "Select AI provider",
        choices=["anthropic", "openai"],
        default="anthropic"
    )
    
    # Choose model
    if provider == "anthropic":
        model_name = Prompt.ask(
            "Select model",
            choices=["claude-sonnet-4-6", "gpt-4o"],
            default="claude-sonnet-4-6"
        )
        api_key = Prompt.ask(
            "Enter your Anthropic API key",
            password=True
        )
        
        return {
            "provider": provider,
            "name": model_name,
            "anthropic_api_key": api_key,
            "openai_api_key": "",
            "max_tokens": 4000,
            "temperature": 0.3
        }
    else:
        model_name = "gpt-4o"  # Only option for OpenAI
        api_key = Prompt.ask(
            "Enter your OpenAI API key",
            password=True
        )
        
        return {
            "provider": provider,
            "name": model_name,
            "anthropic_api_key": "",
            "openai_api_key": api_key,
            "max_tokens": 4000,
            "temperature": 0.3
        }


def setup_telegram() -> Dict[str, Any]:
    """Setup Telegram configuration"""
    console.print("\n[bold cyan]Step 2: Telegram Bot (Optional)[/bold cyan]\n")
    
    enable = Confirm.ask(
        "Enable Telegram bot interface?",
        default=False
    )
    
    if not enable:
        return {
            "enabled": False,
            "bot_token": "",
            "allowed_users": []
        }
    
    console.print("\n[yellow]Get your bot token from @BotFather: https://t.me/BotFather[/yellow]\n")
    
    token = Prompt.ask("Enter Telegram bot token")
    
    return {
        "enabled": True,
        "bot_token": token,
        "allowed_users": []
    }


def setup_github() -> Dict[str, Any]:
    """Setup GitHub configuration"""
    console.print("\n[bold cyan]Step 3: GitHub Integration (Optional)[/bold cyan]\n")
    
    enable = Confirm.ask(
        "Enable GitHub integration for PR reviews?",
        default=False
    )
    
    if not enable:
        return {
            "enabled": False,
            "token": "",
            "webhook_secret": ""
        }
    
    console.print("\n[yellow]Create token at: https://github.com/settings/tokens[/yellow]")
    console.print("[yellow]Required scopes: repo, read:user[/yellow]\n")
    
    token = Prompt.ask("Enter GitHub token", password=True)
    
    return {
        "enabled": True,
        "token": token,
        "webhook_secret": ""
    }


def setup_memory() -> Dict[str, Any]:
    """Setup memory configuration"""
    console.print("\n[bold cyan]Step 4: Memory & Learning[/bold cyan]\n")
    
    enable = Confirm.ask(
        "Enable memory to remember code patterns?",
        default=True
    )
    
    return {
        "enabled": enable,
        "db_path": "coding_memory.db",
        "max_history": 1000
    }


def create_config(model: Dict, telegram: Dict, github: Dict, memory: Dict):
    """Create configuration file"""
    config = {
        "agent": {
            "name": "coding-bear",
            "version": "0.1.0",
            "log_level": "INFO",
            "max_file_size": 100000,
            "max_context_lines": 100
        },
        "model": model,
        "telegram": telegram,
        "github": github,
        "memory": memory
    }
    
    config_path = Path(__file__).parent / "bond_config.yaml"
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    console.print(f"\n[green]✓ Configuration saved to {config_path}[/green]\n")
    
    return config_path


def print_summary(config_path: Path):
    """Print setup summary"""
    console.print(Panel(
        "[bold green]🎉 Setup Complete![/bold green]\n\n"
        "Your Coding Bear agent is ready!\n\n"
        "[cyan]To start:[/cyan]\n"
        f"  1. Review config: [yellow]{config_path}[/yellow]\n"
        "  2. Run: [yellow]python coding_agent.py[/yellow]\n"
        "  3. Or use Telegram bot (if enabled)\n\n"
        "[cyan]Commands:[/cyan]\n"
        "  • review <file> - Code review\n"
        "  • debug <error> - Debug errors\n"
        "  • refactor <file> - Refactor code\n"
        "  • test <file> - Generate tests\n"
        "  • explain <code> - Explain code\n\n"
        "Happy coding! 🐻",
        box=box.ROUNDED,
        border_style="green"
    ))


def main():
    """Main setup function"""
    print_header()
    
    console.print("\n[yellow]This wizard will help you configure Coding Bear.[/yellow]\n")
    
    # Check if config already exists
    config_path = Path(__file__).parent / "bond_config.yaml"
    if config_path.exists():
        overwrite = Confirm.ask(
            f"Config already exists at {config_path}. Overwrite?",
            default=False
        )
        if not overwrite:
            console.print("[yellow]Setup cancelled.[/yellow]")
            return
    
    # Setup steps
    try:
        model_config = setup_model_config()
        telegram_config = setup_telegram()
        github_config = setup_github()
        memory_config = setup_memory()
        
        # Create config
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Saving configuration...", total=None)
            config_path = create_config(model_config, telegram_config, github_config, memory_config)
            progress.update(task, completed=True)
        
        # Print summary
        print_summary(config_path)
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Setup cancelled by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n\n[red]Error during setup: {e}[/red]")
        logger.exception("Setup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()