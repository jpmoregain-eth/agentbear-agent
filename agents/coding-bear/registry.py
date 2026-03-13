"""
Agent Bear Registry Module
Manages registry of running bear agents for discovery and communication
"""

import json
import os
import socket
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Registry file location
REGISTRY_PATH = Path.home() / '.agentbear' / 'registry.json'


def find_available_port(start_port: int = 5001, max_port: int = 5100) -> int:
    """Find an available port for the bear API"""
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    raise RuntimeError(f"No available ports found between {start_port} and {max_port}")


def ensure_registry_dir():
    """Ensure registry directory exists"""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_registry() -> Dict[str, Any]:
    """Load the registry from file"""
    ensure_registry_dir()
    
    if not REGISTRY_PATH.exists():
        return {}
    
    try:
        with open(REGISTRY_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Could not load registry: {e}")
        return {}


def save_registry(registry: Dict[str, Any]):
    """Save registry to file"""
    ensure_registry_dir()
    
    try:
        with open(REGISTRY_PATH, 'w') as f:
            json.dump(registry, f, indent=2, default=str)
    except IOError as e:
        logger.error(f"Could not save registry: {e}")


def register_bear(
    bear_id: str,
    bear_type: str,
    port: int,
    name: str = None,
    capabilities: List[str] = None,
    metadata: Dict[str, Any] = None
) -> bool:
    """
    Register a bear in the registry
    
    Args:
        bear_id: Unique identifier for this bear instance
        bear_type: Type of bear (coding, crypto, research, etc.)
        port: API port the bear is listening on
        name: Optional display name
        capabilities: List of capabilities (e.g., ['code_review', 'debug', 'generate'])
        metadata: Additional metadata
    
    Returns:
        True if registered successfully
    """
    registry = load_registry()
    
    registry[bear_id] = {
        'type': bear_type,
        'port': port,
        'name': name or bear_id,
        'capabilities': capabilities or [],
        'status': 'running',
        'started_at': datetime.now().isoformat(),
        'last_seen': datetime.now().isoformat(),
        'metadata': metadata or {}
    }
    
    save_registry(registry)
    logger.info(f"Registered bear: {bear_id} on port {port}")
    return True


def unregister_bear(bear_id: str) -> bool:
    """Remove a bear from the registry"""
    registry = load_registry()
    
    if bear_id in registry:
        del registry[bear_id]
        save_registry(registry)
        logger.info(f"Unregistered bear: {bear_id}")
        return True
    
    return False


def update_bear_status(bear_id: str, status: str = 'running'):
    """Update bear status and last_seen timestamp"""
    registry = load_registry()
    
    if bear_id in registry:
        registry[bear_id]['status'] = status
        registry[bear_id]['last_seen'] = datetime.now().isoformat()
        save_registry(registry)


def get_bear(bear_id: str) -> Optional[Dict[str, Any]]:
    """Get information about a specific bear"""
    registry = load_registry()
    return registry.get(bear_id)


def get_bears_by_type(bear_type: str) -> List[Dict[str, Any]]:
    """Get all bears of a specific type"""
    registry = load_registry()
    return [
        {'id': k, **v} 
        for k, v in registry.items() 
        if v.get('type') == bear_type and v.get('status') == 'running'
    ]


def get_all_bears() -> List[Dict[str, Any]]:
    """Get all registered bears"""
    registry = load_registry()
    return [{'id': k, **v} for k, v in registry.items()]


def get_bears_by_capability(capability: str) -> List[Dict[str, Any]]:
    """Get all bears that have a specific capability"""
    registry = load_registry()
    return [
        {'id': k, **v} 
        for k, v in registry.items() 
        if capability in v.get('capabilities', []) and v.get('status') == 'running'
    ]


def cleanup_stale_bears(max_age_minutes: int = 30):
    """Remove bears that haven't been seen recently"""
    registry = load_registry()
    now = datetime.now()
    
    stale = []
    for bear_id, info in list(registry.items()):
        try:
            last_seen = datetime.fromisoformat(info.get('last_seen', ''))
            age_minutes = (now - last_seen).total_seconds() / 60
            
            if age_minutes > max_age_minutes:
                stale.append(bear_id)
        except (ValueError, TypeError):
            stale.append(bear_id)
    
    for bear_id in stale:
        del registry[bear_id]
        logger.info(f"Cleaned up stale bear: {bear_id}")
    
    if stale:
        save_registry(registry)
    
    return stale


def call_bear_api(bear_id: str, endpoint: str, method: str = 'POST', data: Dict = None) -> Optional[Dict]:
    """
    Call an API endpoint on a registered bear
    
    Args:
        bear_id: The bear to call
        endpoint: API endpoint (e.g., '/api/code/generate')
        method: HTTP method
        data: Request data
    
    Returns:
        Response data or None if failed
    """
    import requests
    
    bear = get_bear(bear_id)
    if not bear:
        logger.error(f"Bear not found: {bear_id}")
        return None
    
    if bear.get('status') != 'running':
        logger.error(f"Bear not running: {bear_id}")
        return None
    
    port = bear.get('port')
    if not port:
        logger.error(f"Bear has no port: {bear_id}")
        return None
    
    url = f"http://localhost:{port}{endpoint}"
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url, timeout=30)
        else:
            response = requests.post(url, json=data, timeout=30)
        
        response.raise_for_status()
        return response.json()
    
    except requests.RequestException as e:
        logger.error(f"Failed to call bear {bear_id}: {e}")
        return None


# For testing
if __name__ == '__main__':
    print("Testing registry...")
    
    # Test registration
    register_bear(
        'coding-bear-test',
        'coding',
        5001,
        name='Test Coding Bear',
        capabilities=['code_review', 'debug', 'generate'],
        metadata={'version': '0.1.0'}
    )
    
    print(f"Registry: {json.dumps(load_registry(), indent=2)}")
    
    # Test query
    bears = get_bears_by_type('coding')
    print(f"Coding bears: {bears}")
    
    # Cleanup
    unregister_bear('coding-bear-test')
    print("Test complete")