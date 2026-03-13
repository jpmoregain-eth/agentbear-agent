"""
Configuration Module
Handles agent configuration and settings
Encrypts sensitive fields (API keys) when saving
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# Import crypto utils for encryption
try:
    from crypto_utils import encrypt_config, decrypt_config
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("crypto_utils not available, API keys will be stored in plain text")

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Model configuration"""
    provider: str = "anthropic"  # anthropic or openai
    name: str = "claude-3-5-sonnet-20241022"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    max_tokens: int = 4000
    temperature: float = 0.3


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    enabled: bool = False
    bot_token: str = ""
    allowed_users: list = None
    
    def __post_init__(self):
        if self.allowed_users is None:
            self.allowed_users = []


@dataclass
class GitHubConfig:
    """GitHub integration configuration"""
    enabled: bool = False
    token: str = ""
    webhook_secret: str = ""


@dataclass
class MemoryConfig:
    """Memory configuration"""
    enabled: bool = True
    db_path: str = "coding_memory.db"
    max_history: int = 1000


@dataclass
class AgentConfig:
    """Main agent configuration"""
    name: str = "coding-bear"
    version: str = "0.1.0"
    log_level: str = "INFO"
    max_file_size: int = 100000  # bytes
    max_context_lines: int = 100
    

class Config:
    """Configuration manager"""
    
    def __init__(self, config_path: str = "bond_config.yaml"):
        self.config_path = config_path
        self.agent = AgentConfig()
        self.model = ModelConfig()
        self.telegram = TelegramConfig()
        self.github = GitHubConfig()
        self.memory = MemoryConfig()
        
        if os.path.exists(config_path):
            self._load_from_file()
        else:
            logger.warning(f"Config file not found: {config_path}")
            self._load_from_env()
    
    def _load_from_file(self):
        """Load configuration from YAML file with decryption"""
        try:
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            # Decrypt sensitive fields if crypto is available
            if CRYPTO_AVAILABLE:
                data = decrypt_config(data)
                logger.debug("Decrypted sensitive config fields")
            
            # Load agent config
            if 'agent' in data:
                agent_data = data['agent']
                self.agent.name = agent_data.get('name', self.agent.name)
                self.agent.version = agent_data.get('version', self.agent.version)
                self.agent.log_level = agent_data.get('log_level', self.agent.log_level)
            
            # Load model config
            if 'model' in data:
                model_data = data['model']
                self.model.provider = model_data.get('provider', self.model.provider)
                self.model.name = model_data.get('name', self.model.name)
                self.model.anthropic_api_key = model_data.get('anthropic_api_key', '')
                self.model.openai_api_key = model_data.get('openai_api_key', '')
                self.model.max_tokens = model_data.get('max_tokens', self.model.max_tokens)
                self.model.temperature = model_data.get('temperature', self.model.temperature)
            
            # Load telegram config
            if 'telegram' in data:
                tg_data = data['telegram']
                self.telegram.enabled = tg_data.get('enabled', False)
                self.telegram.bot_token = tg_data.get('bot_token', '')
                self.telegram.allowed_users = tg_data.get('allowed_users', [])
            
            # Load github config
            if 'github' in data:
                gh_data = data['github']
                self.github.enabled = gh_data.get('enabled', False)
                self.github.token = gh_data.get('token', '')
                self.github.webhook_secret = gh_data.get('webhook_secret', '')
            
            # Load memory config
            if 'memory' in data:
                mem_data = data['memory']
                self.memory.enabled = mem_data.get('enabled', True)
                self.memory.db_path = mem_data.get('db_path', self.memory.db_path)
                self.memory.max_history = mem_data.get('max_history', self.memory.max_history)
            
            logger.info(f"Configuration loaded from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        self.model.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
        self.model.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.telegram.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.github.token = os.getenv('GITHUB_TOKEN', '')
        
        if os.getenv('TELEGRAM_BOT_TOKEN'):
            self.telegram.enabled = True
        if os.getenv('GITHUB_TOKEN'):
            self.github.enabled = True
        
        logger.info("Configuration loaded from environment variables")
    
    def validate(self) -> bool:
        """Validate configuration"""
        errors = []
        
        # Check API keys
        if self.model.provider == 'anthropic' and not self.model.anthropic_api_key:
            errors.append("Anthropic API key is required")
        elif self.model.provider == 'openai' and not self.model.openai_api_key:
            errors.append("OpenAI API key is required")
        
        # Check Telegram token if enabled
        if self.telegram.enabled and not self.telegram.bot_token:
            errors.append("Telegram bot token is required when Telegram is enabled")
        
        # Check GitHub token if enabled
        if self.github.enabled and not self.github.token:
            errors.append("GitHub token is required when GitHub is enabled")
        
        if errors:
            for error in errors:
                logger.error(f"Config validation: {error}")
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'agent': asdict(self.agent),
            'model': asdict(self.model),
            'telegram': asdict(self.telegram),
            'github': asdict(self.github),
            'memory': asdict(self.memory)
        }
    
    def save(self, path: str = None):
        """Save configuration to file with encryption"""
        save_path = path or self.config_path
        
        try:
            config_dict = self.to_dict()
            
            # Encrypt sensitive fields if crypto is available
            if CRYPTO_AVAILABLE:
                config_dict = encrypt_config(config_dict)
                logger.info("Encrypted sensitive config fields before saving")
            
            with open(save_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
            
            # Set restrictive permissions on config file
            os.chmod(save_path, 0o600)
            
            logger.info(f"Configuration saved to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")


# Global config instance
_config: Optional[Config] = None


def get_config(config_path: str = "bond_config.yaml") -> Config:
    """Get or create global config instance"""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config(config_path: str = "bond_config.yaml"):
    """Reload configuration from file"""
    global _config
    _config = Config(config_path)
    return _config