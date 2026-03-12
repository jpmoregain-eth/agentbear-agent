#!/usr/bin/env python3
"""
AgentBear CLI Setup (Fallback)
Interactive terminal-based configuration
"""

import os
import sys
from pathlib import Path
import yaml

CONFIG_FILE = 'bond_config.yaml'

def get_input(prompt, default=''):
    """Get user input with optional default"""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    try:
        user_input = input(full_prompt).strip()
        return user_input if user_input else default
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled")
        sys.exit(1)

def validate_api_key(key, prefix):
    """Validate API key format"""
    if not key:
        return False
    if prefix and not key.startswith(prefix):
        print(f"⚠️  Warning: Key doesn't start with '{prefix}'")
    return True

def save_config(config_data):
    """Save configuration to YAML file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return False

def main():
    """Main CLI setup flow"""
    
    print("\n" + "="*60)
    print(" 🐻 AgentBear Setup Wizard")
    print("="*60 + "\n")
    
    # Check if config already exists
    if Path(CONFIG_FILE).exists():
        print(f"⚠️  {CONFIG_FILE} already exists")
        response = input("Overwrite? [y/N]: ").strip().lower()
        if response != 'y':
            print("❌ Setup cancelled")
            return False
    
    print("\n📋 AGENT SETTINGS\n")
    agent_name = get_input("Agent name", "Sentinel")
    user_name = get_input("Your name", "Trader")
    
    print("\n🔑 API KEYS\n")
    print("Get your API keys from:")
    print("  • Claude: console.anthropic.com")
    print("  • Binance: binance.com/account/api-management\n")
    
    claude_key = get_input("Claude API key (sk-ant-...)", "")
    if not validate_api_key(claude_key, "sk-ant-"):
        return False
    
    binance_key = get_input("Binance API key", "")
    if not binance_key:
        print("❌ Binance API key is required")
        return False
    
    binance_secret = get_input("Binance API secret", "")
    if not binance_secret:
        print("❌ Binance API secret is required")
        return False
    
    print("\n💱 EXCHANGE SETTINGS\n")
    testnet_input = get_input("Use Binance testnet? [Y/n]", "y").lower()
    testnet = testnet_input != 'n'
    
    print("\n📱 TELEGRAM BOT\n")
    print("Get token from @BotFather on Telegram\n")
    telegram_token = get_input("Telegram bot token (123456:ABC-DEF...)", "")
    if not telegram_token:
        print("❌ Telegram token is required")
        return False
    
    print("\n💾 STORAGE\n")
    db_path = get_input("Database path", "agentbear_memory.db")
    
    # Build config
    config = {
        'agent': {
            'name': agent_name,
        },
        'user': {
            'name': user_name,
        },
        'models': {
            'default': 'claude-3-5-sonnet-20241022'
        },
        'api_keys': {
            'anthropic': claude_key,
        },
        'exchange': {
            'type': 'binance',
            'api_key': binance_key,
            'api_secret': binance_secret,
            'testnet': testnet,
        },
        'telegram': {
            'token': telegram_token,
        },
        'database': {
            'path': db_path,
        }
    }
    
    # Show review
    print("\n" + "="*60)
    print(" 📋 REVIEW CONFIGURATION")
    print("="*60 + "\n")
    
    print(f"Agent Name ...................... {config['agent']['name']}")
    print(f"User Name ....................... {config['user']['name']}")
    print(f"Claude Model .................... {config['models']['default']}")
    print(f"Exchange ........................ {config['exchange']['type']}")
    print(f"Testnet ......................... {'✅ Yes' if config['exchange']['testnet'] else '❌ No'}")
    print(f"Database ........................ {config['database']['path']}")
    print(f"Telegram ........................ Configured")
    print(f"Binance API ..................... Configured\n")
    
    # Confirm
    response = input("Save this configuration? [Y/n]: ").strip().lower()
    
    if response == 'n':
        print("❌ Setup cancelled")
        return False
    
    # Save
    print("\n💾 Saving configuration...", end=" ", flush=True)
    if save_config(config):
        print("✅")
        print(f"\n✅ Configuration saved to: {CONFIG_FILE}\n")
        print("📝 Next steps:")
        print("   1. Start the agent: python3 backend/telegram_bot.py")
        print("   2. Message your bot on Telegram: /help\n")
        return True
    else:
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
