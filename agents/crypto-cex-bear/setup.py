#!/usr/bin/env python3
"""
AgentBear Smart Setup Launcher
Attempts local browser setup, falls back to CLI
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

# Check if config already exists
CONFIG_FILE = 'bond_config.yaml'

def config_exists():
    """Check if config file already exists"""
    return Path(CONFIG_FILE).exists()

def has_display():
    """Check if GUI is available"""
    if sys.platform == 'win32':
        return True  # Windows usually has display
    if sys.platform == 'darwin':
        return True  # macOS usually has display
    # Linux: check DISPLAY env var
    return os.environ.get('DISPLAY') is not None

def has_flask():
    """Check if Flask is installed"""
    try:
        import flask
        return True
    except ImportError:
        return False

def try_browser_setup():
    """Try to run local browser setup"""
    print("\n" + "="*50)
    print("🖥️  AgentBear Local Setup")
    print("="*50)
    
    # Check if Flask is available
    if not has_flask():
        print("❌ Flask not installed")
        print("   Install with: pip install flask pyyaml")
        return False
    
    # Check if setup_server.py exists
    if not Path('setup_server.py').exists():
        print("❌ setup_server.py not found in current directory")
        return False
    
    print("✅ Starting local setup server...")
    print("📍 Opening browser to: http://localhost:5000")
    
    try:
        # Start Flask server
        proc = subprocess.Popen(
            [sys.executable, 'setup_server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        # Wait for server to start
        time.sleep(2)
        
        # Open browser
        webbrowser.open('http://localhost:5000')
        
        print("✅ Browser opened!")
        print("📝 Fill in the form and click 'Save Configuration'")
        print("\n⏳ Server running... (Press Ctrl+C to stop)\n")
        
        # Keep server running
        try:
            proc.wait()
        except KeyboardInterrupt:
            print("\n\n✅ Setup complete! Closing server...")
            proc.terminate()
            proc.wait(timeout=5)
        
        # Check if config was created
        if config_exists():
            print("✅ Configuration saved successfully!")
            print(f"📄 Config file: {CONFIG_FILE}")
            return True
        else:
            print("⚠️  No configuration was saved")
            return False
    
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False

def fallback_cli_setup():
    """Fallback to CLI setup"""
    print("\n" + "="*50)
    print("🖥️  AgentBear CLI Setup (Fallback)")
    print("="*50 + "\n")
    
    # Check if setup_cli.py exists
    if not Path('setup_cli.py').exists():
        print("❌ setup_cli.py not found in current directory")
        return False
    
    try:
        subprocess.run([sys.executable, 'setup_cli.py'], check=True)
        
        if config_exists():
            print("\n✅ Configuration saved successfully!")
            print(f"📄 Config file: {CONFIG_FILE}")
            return True
    except subprocess.CalledProcessError:
        print("\n❌ Setup failed")
        return False
    
    return False

def main():
    """Main setup logic"""
    
    # Check if config already exists
    if config_exists():
        print("\n" + "="*50)
        print("✅ Configuration Already Exists")
        print("="*50)
        print(f"📄 Config file: {CONFIG_FILE}")
        print("\nTo reconfigure, delete this file and run setup again:")
        print(f"   rm {CONFIG_FILE}")
        print("   python3 setup.py\n")
        return True
    
    # Try browser setup first (if display available)
    if has_display():
        print("\n💡 Attempting local browser setup...")
        if try_browser_setup():
            return True
        print("\n⚠️  Browser setup failed, trying CLI fallback...\n")
    else:
        print("\n💡 Headless environment detected, using CLI setup...\n")
    
    # Fallback to CLI
    if fallback_cli_setup():
        return True
    
    # Both failed
    print("\n" + "="*50)
    print("❌ Setup Failed")
    print("="*50)
    print("\nPlease check:")
    print("1. Flask is installed: pip install flask pyyaml")
    print("2. setup_server.py and setup_cli.py exist in current directory")
    print("3. templates/setup.html exists")
    return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
