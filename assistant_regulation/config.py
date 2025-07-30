"""
Configuration management for the Streamlit application
"""
import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

@dataclass
class APIConfig:
    """Configuration for API providers"""
    mistral_enabled: bool = True
    ollama_enabled: bool = True
    ollama_base_url: str = "http://localhost:11434"
    retry_attempts: int = 3
    timeout_seconds: int = 30
    fallback_enabled: bool = True


@dataclass
class UIConfig:
    """Configuration for UI elements"""
    theme: str = "dark"
    language: str = "fr"
    enable_debug: bool = False
    max_message_history: int = 50
    auto_scroll: bool = True
    show_timestamps: bool = True


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization"""
    enable_caching: bool = True
    cache_ttl_minutes: int = 60
    parallel_processing: bool = True
    max_workers: int = 4
    batch_size: int = 3


@dataclass
class AppConfiguration:
    """Main application configuration"""
    api: APIConfig
    ui: UIConfig
    performance: PerformanceConfig
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfiguration':
        """Create from dictionary"""
        return cls(
            api=APIConfig(**data.get('api', {})),
            ui=UIConfig(**data.get('ui', {})),
            performance=PerformanceConfig(**data.get('performance', {}))
        )


class ConfigManager:
    """Manages application configuration with persistence"""
    
    def __init__(self, config_file: str = "app_config.json"):
        self.config_file = Path(config_file)
        self._config: Optional[AppConfiguration] = None
        self.load_config()
    
    def load_config(self) -> AppConfiguration:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._config = AppConfiguration.from_dict(data)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                self._config = self._create_default_config()
        else:
            self._config = self._create_default_config()
            self.save_config()
        
        return self._config
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        if self._config:
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self._config.to_dict(), f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving config: {e}")
    
    def _create_default_config(self) -> AppConfiguration:
        """Create default configuration"""
        return AppConfiguration(
            api=APIConfig(),
            ui=UIConfig(),
            performance=PerformanceConfig()
        )
    
    @property
    def config(self) -> AppConfiguration:
        """Get current configuration"""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def update_api_config(self, **kwargs) -> None:
        """Update API configuration"""
        for key, value in kwargs.items():
            if hasattr(self.config.api, key):
                setattr(self.config.api, key, value)
        self.save_config()
    
    def update_ui_config(self, **kwargs) -> None:
        """Update UI configuration"""
        for key, value in kwargs.items():
            if hasattr(self.config.ui, key):
                setattr(self.config.ui, key, value)
        self.save_config()
    
    def update_performance_config(self, **kwargs) -> None:
        """Update performance configuration"""
        for key, value in kwargs.items():
            if hasattr(self.config.performance, key):
                setattr(self.config.performance, key, value)
        self.save_config()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self._config = self._create_default_config()
        self.save_config()
    
    def get_env_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables"""
        overrides = {}
        
        # API overrides
        if os.getenv('OLLAMA_BASE_URL'):
            overrides['ollama_base_url'] = os.getenv('OLLAMA_BASE_URL')
        
        if os.getenv('API_TIMEOUT'):
            try:
                overrides['timeout_seconds'] = int(os.getenv('API_TIMEOUT'))
            except ValueError:
                pass
        
        # UI overrides
        if os.getenv('APP_LANGUAGE'):
            overrides['language'] = os.getenv('APP_LANGUAGE')
        
        if os.getenv('APP_THEME'):
            overrides['theme'] = os.getenv('APP_THEME')
        
        # Performance overrides
        if os.getenv('MAX_WORKERS'):
            try:
                overrides['max_workers'] = int(os.getenv('MAX_WORKERS'))
            except ValueError:
                pass
        
        return overrides


# Global configuration manager instance
config_manager = ConfigManager()


def get_app_config() -> AppConfiguration:
    """Get application configuration"""
    return config_manager.config


def update_config(**kwargs) -> None:
    """Update configuration with keyword arguments"""
    # Separate by category
    api_updates = {k.replace('api_', ''): v for k, v in kwargs.items() if k.startswith('api_')}
    ui_updates = {k.replace('ui_', ''): v for k, v in kwargs.items() if k.startswith('ui_')}
    perf_updates = {k.replace('perf_', ''): v for k, v in kwargs.items() if k.startswith('perf_')}
    
    if api_updates:
        config_manager.update_api_config(**api_updates)
    if ui_updates:
        config_manager.update_ui_config(**ui_updates)
    if perf_updates:
        config_manager.update_performance_config(**perf_updates) 