"""
Setup Server for Coding Bear
Web-based configuration wizard

If running headless (no display), automatically falls back to CLI setup (setup.py)
"""

import os
import sys
import subprocess
import yaml
import logging
from pathlib import Path

# Check if running headless before importing Flask
def is_headless():
    """Detect if running in headless environment"""
    # Check for DISPLAY environment variable (Linux)
    if os.environ.get('DISPLAY'):
        return False
    
    # Check if we're in a terminal-only environment
    if not sys.stdout.isatty():
        return True
    
    # Check for SSH connection without X11 forwarding
    if os.environ.get('SSH_CONNECTION') and not os.environ.get('DISPLAY'):
        return True
    
    # Try to detect if we can open a browser
    try:
        import webbrowser
        # On Linux, check if we have a browser that can open
        if sys.platform == 'linux':
            # Check for common browsers
            browsers = ['google-chrome', 'chromium', 'firefox', 'xdg-open']
            has_browser = any(
                subprocess.run(['which', b], capture_output=True).returncode == 0
                for b in browsers
            )
            if not has_browser:
                return True
    except:
        pass
    
    return False

# If headless, run CLI setup instead
if is_headless():
    print("🐻 Headless environment detected. Starting CLI setup...")
    setup_script = Path(__file__).parent / 'setup.py'
    subprocess.run([sys.executable, str(setup_script)])
    sys.exit(0)

from flask import Flask, render_template, request, jsonify, redirect, url_for

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'coding-bear-setup-secret'

# Setup steps
SETUP_STEPS = [
    {'number': 1, 'title': 'Welcome', 'description': 'Introduction'},
    {'number': 2, 'title': 'API Keys', 'description': 'Model Configuration'},
    {'number': 3, 'title': 'Features', 'description': 'Enable Features'},
    {'number': 4, 'title': 'Complete', 'description': 'Finish Setup'}
]


@app.route('/')
def index():
    """Redirect to setup"""
    return redirect(url_for('setup', step=1))


@app.route('/setup')
def setup_redirect():
    """Redirect to step 1"""
    return redirect(url_for('setup', step=1))


@app.route('/setup/<int:step>', methods=['GET', 'POST'])
def setup(step):
    """Setup wizard"""
    if step < 1 or step > len(SETUP_STEPS):
        return redirect(url_for('setup', step=1))
    
    if request.method == 'POST':
        # Save progress
        save_setup_progress(step, request.form)
        
        # Move to next step
        if step < len(SETUP_STEPS):
            return redirect(url_for('setup', step=step + 1))
        else:
            # Final step - create config
            create_config()
            return redirect(url_for('complete'))
    
    # Load existing progress
    progress = load_setup_progress()
    
    return render_template('setup.html',
                         step=step,
                         steps=SETUP_STEPS,
                         progress=progress,
                         total_steps=len(SETUP_STEPS))


@app.route('/complete')
def complete():
    """Setup complete page"""
    config_path = Path(__file__).parent / 'bond_config.yaml'
    return render_template('complete.html', config_exists=config_path.exists())


@app.route('/api/validate', methods=['POST'])
def validate_api_key():
    """Validate API key"""
    data = request.json
    provider = data.get('provider')
    api_key = data.get('api_key')
    
    if not api_key:
        return jsonify({'valid': False, 'error': 'API key is required'})
    
    try:
        if provider == 'anthropic':
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            # Make a test request
            client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            return jsonify({'valid': True})
        else:
            import openai
            client = openai.OpenAI(api_key=api_key)
            client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return jsonify({'valid': True})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})


@app.route('/api/config', methods=['GET'])
def get_config_status():
    """Get current config status"""
    config_path = Path(__file__).parent / 'bond_config.yaml'
    example_path = Path(__file__).parent / 'bond_config.example.yaml'
    
    return jsonify({
        'config_exists': config_path.exists(),
        'config_path': str(config_path),
        'example_path': str(example_path)
    })


def save_setup_progress(step, form_data):
    """Save setup progress to temp file"""
    progress_file = Path(__file__).parent / '.setup_progress'
    
    data = {}
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            data = yaml.safe_load(f) or {}
    
    data[f'step_{step}'] = dict(form_data)
    
    with open(progress_file, 'w') as f:
        yaml.dump(data, f)
    
    logger.info(f"Saved progress for step {step}")


def load_setup_progress():
    """Load setup progress"""
    progress_file = Path(__file__).parent / '.setup_progress'
    
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}


def create_config():
    """Create final config file from progress"""
    progress = load_setup_progress()
    
    config = {
        'agent': {
            'name': 'coding-bear',
            'version': '0.1.0',
            'log_level': 'INFO',
            'max_file_size': 100000,
            'max_context_lines': 100
        },
        'model': {
            'provider': 'anthropic',
            'name': 'claude-3-5-sonnet-20241022',
            'anthropic_api_key': '',
            'openai_api_key': '',
            'max_tokens': 4000,
            'temperature': 0.3
        },
        'telegram': {
            'enabled': False,
            'bot_token': '',
            'allowed_users': []
        },
        'github': {
            'enabled': False,
            'token': '',
            'webhook_secret': ''
        },
        'memory': {
            'enabled': True,
            'db_path': 'coding_memory.db',
            'max_history': 1000
        }
    }
    
    # Apply step 2 (API keys)
    step2 = progress.get('step_2', {})
    config['model']['provider'] = step2.get('provider', 'anthropic')
    config['model']['name'] = step2.get('model_name', 'claude-3-5-sonnet-20241022')
    
    if config['model']['provider'] == 'anthropic':
        config['model']['anthropic_api_key'] = step2.get('anthropic_key', '')
    else:
        config['model']['openai_api_key'] = step2.get('openai_key', '')
    
    # Apply step 3 (Features)
    step3 = progress.get('step_3', {})
    config['telegram']['enabled'] = step3.get('enable_telegram') == 'on'
    config['telegram']['bot_token'] = step3.get('telegram_token', '')
    config['github']['enabled'] = step3.get('enable_github') == 'on'
    config['github']['token'] = step3.get('github_token', '')
    config['memory']['enabled'] = step3.get('enable_memory', 'on') == 'on'
    
    # Save config
    config_path = Path(__file__).parent / 'bond_config.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    # Clean up progress
    progress_file = Path(__file__).parent / '.setup_progress'
    if progress_file.exists():
        progress_file.unlink()
    
    logger.info(f"Config created at {config_path}")


if __name__ == '__main__':
    import webbrowser
    import threading
    
    print("🐻 Coding Bear Setup Server")
    print("=" * 40)
    
    # Try to open browser automatically
    url = "http://localhost:5000"
    browser_opened = False
    
    def open_browser():
        global browser_opened
        try:
            webbrowser.open(url)
            browser_opened = True
        except:
            pass
    
    # Open browser in a thread (slight delay to let server start)
    threading.Timer(1.5, open_browser).start()
    
    print(f"\nStarting server at {url}")
    if not browser_opened:
        print("\nIf browser doesn't open automatically,")
        print(f"please manually open: {url}")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n[yellow]Server is already running![/yellow]")
            print(f"Please open: {url}")
        else:
            raise