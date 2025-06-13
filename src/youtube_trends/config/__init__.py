"""
Configuration loader for YouTube Trends.
"""

import json
import os
from pathlib import Path

class ConfigLoader:
    """Loads and manages configuration files."""
    
    def __init__(self):
        """Initialize the configuration loader."""
        self.config_dir = Path(__file__).parent
        self.configs = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load all configuration files from the config directory."""
        for config_file in self.config_dir.glob('*.json'):
            config_name = config_file.stem
            with open(config_file, 'r', encoding='utf-8') as f:
                self.configs[config_name] = json.load(f)
    
    def get_config(self, config_name):
        """
        Get a specific configuration.
        
        Args:
            config_name (str): Name of the configuration to load
            
        Returns:
            dict: Configuration data
        """
        if config_name not in self.configs:
            raise ValueError(f"Configuration '{config_name}' not found")
        return self.configs[config_name]
    
    def get_countries(self, config_name):
        """
        Get list of countries for a specific configuration.
        
        Args:
            config_name (str): Name of the configuration
            
        Returns:
            list: List of country codes
        """
        config = self.get_config(config_name)
        return list(config.keys())
    
    def get_search_terms(self, config_name, country):
        """
        Get search terms for a specific configuration and country.
        
        Args:
            config_name (str): Name of the configuration
            country (str): Country code
            
        Returns:
            list: List of search terms
        """
        config = self.get_config(config_name)
        if country not in config:
            raise ValueError(f"Country '{country}' not found in configuration '{config_name}'")
        return config[country]['search_terms']
    
    def get_country_config(self, config_name, country):
        """
        Get full configuration for a specific country.
        
        Args:
            config_name (str): Name of the configuration
            country (str): Country code
            
        Returns:
            dict: Country-specific configuration
        """
        config = self.get_config(config_name)
        if country not in config:
            raise ValueError(f"Country '{country}' not found in configuration '{config_name}'")
        return config[country] 