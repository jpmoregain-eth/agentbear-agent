#!/usr/bin/env python3
"""
Local setup server for AgentBear
Runs on localhost:5000 and provides browser-based configuration UI
"""

import os
import json
from flask import Flask, render_template, request, jsonify
from pathlib import Path
import yaml

app = Flask(__name__, template_folder='templates')

# Determine config file location
CONFIG_FILE = 'bond_config.yaml'

def validate_claude_key(key):
    """Validate Claude API key by testing it"""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        # Try a simple API call
        client.messages.count_tokens(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": "test"}]
        )
        return True
    except Exception as e:
        return False

def validate_openai_key(key):
    """Validate OpenAI API key"""
    try:
        import requests
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

def validate_kimi_key(key):
    """Validate Kimi API key"""
    try:
        import requests
        response = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"messages": [{"role": "user", "content": "test"}], "model": "moonshot-v1-8k"},
            timeout=5
        )
        return response.status_code in [200, 400]  # 400 means auth worked but request invalid
    except:
        return False

def validate_google_key(key):
    """Validate Google Gemini API key"""
    try:
        import requests
        response = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

def validate_binance_key(key):
    """Validate Binance API key"""
    try:
        from binance.spot import Spot
        client = Spot(api_key=key)
        client.account()
        return True
    except:
        return False

def validate_telegram_token(token):
    """Validate Telegram bot token"""
    try:
        import requests
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=5
        )
        return response.status_code == 200 and response.json().get('ok', False)
    except:
        return False

def save_config(data):
    """Save configuration to bond_config.yaml"""
    model = data.get('model', 'claude')
    
    config = {
        'agent': {
            'name': data.get('agent_name', 'Sentinel'),
        },
        'user': {
            'name': data.get('user_name', 'Trader'),
        },
        'models': {
            'default': 'claude-3-5-sonnet-20241022' if model == 'claude' else model
        },
        'api_keys': {
            model: data.get('api_key', ''),
        },
        'exchange': {
            'type': 'binance',
            'api_key': data.get('binance_key', ''),
            'api_secret': data.get('binance_secret', ''),
            'testnet': data.get('testnet', False),
        },
        'telegram': {
            'token': data.get('telegram_token', ''),
        },
        'database': {
            'path': data.get('db_path', 'agentbear_memory.db'),
        }
    }
    
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return True

@app.route('/')
def index():
    """Serve the setup form"""
    return render_template('setup.html')

@app.route('/api/config', methods=['POST'])
def save_setup():
    """Handle form submission and save config"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['agent_name', 'user_name', 'model', 'api_key', 'binance_key', 'binance_secret', 'telegram_token']
        missing = [f for f in required if not data.get(f)]
        
        if missing:
            return jsonify({'success': False, 'error': f'Missing fields: {", ".join(missing)}'}), 400
        
        # Save config
        save_config(data)
        
        return jsonify({
            'success': True,
            'message': 'Configuration saved successfully!',
            'config_file': CONFIG_FILE
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-key', methods=['POST'])
def test_key():
    """Test if an API key is valid"""
    try:
        data = request.get_json()
        service = data.get('service')
        key = data.get('key')
        
        if not key:
            return jsonify({'success': False, 'error': 'No key provided'})
        
        # Test based on service
        if service == 'claude':
            valid = validate_claude_key(key)
        elif service == 'openai':
            valid = validate_openai_key(key)
        elif service == 'kimi':
            valid = validate_kimi_key(key)
        elif service == 'google':
            valid = validate_google_key(key)
        elif service == 'binance':
            valid = validate_binance_key(key)
        elif service == 'telegram':
            valid = validate_telegram_token(key)
        else:
            return jsonify({'success': False, 'error': 'Unknown service'})
        
        return jsonify({'success': valid, 'service': service})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Check if config already exists"""
    exists = Path(CONFIG_FILE).exists()
    return jsonify({'config_exists': exists, 'config_file': CONFIG_FILE})

if __name__ == '__main__':
    print("🚀 AgentBear Setup Server")
    print("📍 Open browser to: http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    app.run(host='localhost', port=5000, debug=False)
