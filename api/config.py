"""
Configuration management for the String Authority API.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# Load .env file if it exists (won't override existing environment variables)
# This allows .env files in remote environments while keeping db_config.json for local dev
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path, override=False)

def get_database_config() -> Optional[Dict[str, str]]:
    """
    Load database configuration from environment variables, .env file, or db_config.json.
    
    Priority order:
    1. Environment variables (already set in OS environment)
    2. .env file (for remote environments)
    3. db_config.json (for local development)
    
    Returns:
        Dict with database connection parameters or None if config not found
    """
    # First try environment variables (highest priority - already set or loaded from .env)
    if all(os.environ.get(key) for key in ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']):
        return {
            'host': os.environ['DB_HOST'],
            'port': os.environ.get('DB_PORT', '5432'),
            'database': os.environ['DB_NAME'],
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD']
        }
    
    # Fallback to db_config.json in parent directory (for local development)
    config_path = Path(__file__).parent.parent / 'db_config.json'
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    
    return None

def get_pagination_config() -> Dict[str, int]:
    """
    Get pagination configuration from environment variables.
    
    Returns:
        Dict with pagination settings
    """
    return {
        'max_page_size': int(os.environ.get('MAX_PAGE_SIZE', 10)),
        'default_page_size': int(os.environ.get('DEFAULT_PAGE_SIZE', 10))
    }