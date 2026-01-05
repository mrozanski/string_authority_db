"""
Configuration management for the String Authority API.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional

def get_database_config() -> Optional[Dict[str, str]]:
    """
    Load database configuration from db_config.json or environment variables.
    
    Returns:
        Dict with database connection parameters or None if config not found
    """
    # First try environment variables
    if all(os.environ.get(key) for key in ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']):
        return {
            'host': os.environ['DB_HOST'],
            'port': os.environ.get('DB_PORT', '5432'),
            'database': os.environ['DB_NAME'],
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD']
        }
    
    # Then try db_config.json in parent directory
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