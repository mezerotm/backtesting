import os
import json
import logging
from datetime import datetime
from functools import lru_cache
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)

class BaseFetcher:
    """Base class for data fetchers with common utilities"""
    
    def __init__(self, force_refresh: bool = False, cache_subdir: str = 'default'):
        """Initialize fetcher with cache directory
        
        Args:
            force_refresh: Whether to bypass cache
            cache_subdir: Subdirectory name for this fetcher's cache
        """
        # Create a specific cache subdirectory in public/cache for each type of data
        self.cache_dir = os.path.join('public', 'cache', 'data', cache_subdir)
        print(f"[DEBUG] Initializing cache directory: {self.cache_dir}")
        os.makedirs(self.cache_dir, exist_ok=True)
        print(f"[DEBUG] Cache directory created: {os.path.exists(self.cache_dir)}")
        self.force_refresh = force_refresh
    
    def _get_cache_path(self, key: str) -> str:
        """Get the cache file path for a given key"""
        # Sanitize the key to be a valid filename
        safe_key = "".join(c for c in key if c.isalnum() or c in ('-', '_'))
        cache_path = os.path.join(self.cache_dir, f"{safe_key}.json")
        print(f"[DEBUG] Generated cache path: {cache_path}")
        return cache_path
    
    def _load_from_cache(self, key: str, max_age_hours: int = 24) -> Optional[Dict]:
        """Load data from cache if it exists and is not expired"""
        try:
            cache_path = self._get_cache_path(key)
            print(f"[DEBUG] Loading from cache: {cache_path}")
            if not os.path.exists(cache_path):
                print(f"[DEBUG] Cache file does not exist: {cache_path}")
                return None
                
            # Check if cache is expired
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))
            if file_age.total_seconds() > (max_age_hours * 3600):
                print(f"[DEBUG] Cache file is expired: {cache_path}")
                return None
                
            print(f"[DEBUG] Loading cache file: {cache_path}")
            with open(cache_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"[ERROR] Error loading from cache: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return None
    
    def _save_to_cache(self, key: str, data: Dict) -> None:
        """Save data to cache"""
        try:
            cache_path = self._get_cache_path(key)
            print(f"[DEBUG] Saving to cache: {cache_path}")
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            print(f"[DEBUG] Cache file saved: {os.path.exists(cache_path)}")
        except Exception as e:
            print(f"[ERROR] Error saving to cache: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
    
    def _should_use_cache(self, max_age_hours: int = 24) -> bool:
        """Determine if cache should be used based on force_refresh setting"""
        return not self.force_refresh 