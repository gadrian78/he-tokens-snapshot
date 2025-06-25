import os
import json
import time

# Constants
CACHE_DIR = "__cache"
PRICE_CACHE_FILE = os.path.join(CACHE_DIR, "price_cache.json")
MARKET_CACHE_FILE = os.path.join(CACHE_DIR, "market_cache.json")
DIESEL_CACHE_FILE = os.path.join(CACHE_DIR, "diesel_cache.json")
CACHE_EXPIRATION_SECONDS = 900  # 15 minutes

# Global caches (token -> {"value": ..., "timestamp": ...})
price_cache = {}
market_cache = {}
diesel_cache = {}

def load_cache():
    """Load caches from JSON files on import"""
    global price_cache, market_cache
    os.makedirs(CACHE_DIR, exist_ok=True)

    if os.path.exists(PRICE_CACHE_FILE):
        try:
            with open(PRICE_CACHE_FILE, "r") as f:
                price_cache = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load price_cache: {e}")

    if os.path.exists(MARKET_CACHE_FILE):
        try:
            with open(MARKET_CACHE_FILE, "r") as f:
                market_cache = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load market_cache: {e}")
    if os.path.exists(DIESEL_CACHE_FILE):
        try:
            with open(DIESEL_CACHE_FILE, "r") as f:
                diesel_cache = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load diesel_cache: {e}")

def save_cache():
    """Write caches to JSON files"""
    try:
        with open(PRICE_CACHE_FILE, "w") as f:
            json.dump(price_cache, f)
        with open(MARKET_CACHE_FILE, "w") as f:
            json.dump(market_cache, f)
        with open(DIESEL_CACHE_FILE, "w") as f:
            json.dump(diesel_cache, f)
    except Exception as e:
        print(f"❌ Error saving caches: {e}")

def is_cache_valid(entry, expiration=CACHE_EXPIRATION_SECONDS):
    """Check if a cache entry is still fresh"""
    if not entry or "timestamp" not in entry:
        return False
    return (time.time() - entry["timestamp"]) < expiration

def clear_caches():
    """Remove expired cache entries only"""
    now = time.time()

    def remove_expired(cache):
        keys_to_delete = [k for k, v in cache.items()
                          if "timestamp" not in v or now - v["timestamp"] > CACHE_EXPIRATION_SECONDS]
        for k in keys_to_delete:
            del cache[k]

    remove_expired(price_cache)
    remove_expired(market_cache)
    remove_expired(diesel_cache)
    save_cache()

# Load caches immediately on import
load_cache()

