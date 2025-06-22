"""
Hive Engine Utilities Module

Common functions and utilities for interacting with Hive Engine API.
Used by the Hive Engine Tokens Snapshot tool.

Created by https://peakd.com/@gadrian using "vibe" coding in June 2025.
"""

import requests
import time
import random
from collections import defaultdict

# Global caches
price_cache = {}
market_cache = {}

def debug_log(text):
    """Simple debug logging function - can be overridden by importing modules"""
    # This will be overridden by the main module's DEBUG setting
    pass

def fetch_from_hive_engine(api, contract, table, query, limit=1000, offset=0, retries=5, delay=3):
    """
    Enhanced fetch function with exponential backoff and better error handling
    
    Args:
        api: Hive Engine API instance
        contract: Contract name (e.g., 'tokens', 'market')
        table: Table name (e.g., 'balances', 'buyBook')
        query: Query parameters dict
        limit: Maximum number of records to fetch
        offset: Starting offset for pagination
        retries: Number of retry attempts
        delay: Base delay between retries in seconds
        
    Returns:
        List of results or empty list if all attempts fail
    """
    for attempt in range(retries):
        try:
            # Add random delay to avoid hitting rate limits
            if attempt > 0:
                jitter = random.uniform(0.5, 1.5)
                sleep_time = delay * (2 ** (attempt - 1)) + jitter  # Exponential backoff with jitter
                debug_log(f"⏳ Waiting {sleep_time:.1f} seconds before retry {attempt + 1}/{retries}...")
                time.sleep(sleep_time)
            
            result = api.find(contract, table, query, limit=limit, offset=offset)
            if result is None:
                debug_log(f"⚠️ Warning: No results for {table} with query {query}")
                return []
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            debug_log(f"❌ Error fetching {table} (attempt {attempt + 1}/{retries}): {e}")
            
            # Check for specific error types
            if "service temporarily unavailable" in error_msg or "503" in error_msg:
                debug_log(f"🔄 Service unavailable, will retry...")
                continue
            elif "timeout" in error_msg or "connection" in error_msg:
                debug_log(f"🔄 Connection issue, will retry...")
                continue
            elif "rate limit" in error_msg or "429" in error_msg:
                debug_log(f"🔄 Rate limited, will retry with longer delay...")
                time.sleep(delay * 2)  # Longer delay for rate limiting
                continue
            else:
                # For other errors, don't retry as much
                if attempt >= 2:
                    break
                    
        # If this was the last attempt, return empty
        if attempt == retries - 1:
            debug_log(f"❌ All {retries} attempts failed for {table}")
            return []
    
    return []

def get_volume_since(trades, since_seconds_ago):
    """Calculate volume since a certain time ago"""
    now = int(time.time())  # current UNIX time (seconds)
    cutoff = now - since_seconds_ago
    return sum(float(t["volume"]) for t in trades if t.get("volume") and t["timestamp"] >= cutoff)

def get_24h_volume(trades):
    """Calculate 24-hour trading volume"""
    return get_volume_since(trades, 86400)

def fetch_market_metrics(api, symbol):
    """Fetch market metrics for a given symbol"""
    try:
        result = api.find("market", "metrics", {"symbol": symbol}, limit=1)
        return result[0] if result else None
    except Exception as e:
        debug_log(f"⚠️ Error fetching metrics for {symbol}: {e}")
        return None

def get_market_info(api, market, symbol, retries=3, delay=2, trade_batch_limit=1000):
    """
    Get market information (price and volume) for a token symbol
    
    Args:
        api: Hive Engine API instance
        market: Hive Engine Market instance  
        symbol: Token symbol (e.g., 'LEO', 'SPS')
        retries: Number of retry attempts
        delay: Delay between retries
        trade_batch_limit: Batch size for trade history fetching
        
    Returns:
        Tuple of (price_in_hive, 24h_volume_in_hive)
    """
    global market_cache
    
    if symbol in market_cache:
        return market_cache[symbol]

    # Special handling for SWAP.HIVE
    if symbol == "SWAP.HIVE":
        market_cache[symbol] = (1.0, 0.0)
        return 1.0, 0.0

    # First, try to get market metrics to get basic price info
    try:
        metrics = fetch_market_metrics(api, symbol)
        if metrics:
            # Extract price from metrics if available
            last_price = float(metrics.get('lastPrice', 0))
            volume = float(metrics.get('volume', 0))
            
            if last_price > 0:
                debug_log(f"  📊 Using metrics data for {symbol}: Price={last_price:.8f} HIVE, Vol={volume:.2f}")
                market_cache[symbol] = (last_price, volume)
                return last_price, volume
    except Exception as e:
        debug_log(f"⚠️ Error fetching metrics for {symbol}: {e}")

    # Try to get trades history (this fails for problematic tokens)
    for attempt in range(retries):
        try:
            offset = 0
            all_trades = []
            while True:
                trades = market.get_trades_history(symbol, limit=trade_batch_limit, offset=offset)
                if not trades:
                    break
                all_trades.extend(trades)
                if len(trades) < trade_batch_limit:
                    break
                offset += trade_batch_limit

            if all_trades:
                price_hive = float(all_trades[0]["price"])
                vol24 = get_24h_volume(all_trades)
                debug_log(f"  📈 Using trades data for {symbol}: Price={price_hive:.8f} HIVE, 24h Vol={vol24:.2f}")
                market_cache[symbol] = (price_hive, vol24)
                return price_hive, vol24

        except Exception as e:
            debug_log(f"⚠️ Trades history failed for {symbol} (attempt {attempt + 1}): {e}")
            
            # If trades history fails, try alternative methods
            if "does not exists" in str(e).lower():
                debug_log(f"  🔄 Trying alternative price sources for {symbol}...")
                
                # Method 1: Try order book data
                try:
                    buy_book = market.get_buy_book(symbol, limit=1)
                    sell_book = market.get_sell_book(symbol, limit=1)
                    
                    price_from_orders = 0.0
                    
                    if buy_book and len(buy_book) > 0:
                        buy_price = float(buy_book[0]["price"])
                        price_from_orders = buy_price
                        debug_log(f"  💰 Found buy price for {symbol}: {buy_price:.8f} HIVE")
                    
                    if sell_book and len(sell_book) > 0:
                        sell_price = float(sell_book[0]["price"])
                        if price_from_orders == 0.0:
                            price_from_orders = sell_price
                        else:
                            # Use average of buy/sell if both available
                            price_from_orders = (price_from_orders + sell_price) / 2
                        debug_log(f"  💱 Found sell price for {symbol}: {sell_price:.8f} HIVE")
                    
                    if price_from_orders > 0:
                        debug_log(f"  ✅ Using order book price for {symbol}: {price_from_orders:.8f} HIVE")
                        market_cache[symbol] = (price_from_orders, 0.0)  # No volume data from order book
                        return price_from_orders, 0.0
                        
                except Exception as order_error:
                    debug_log(f"  ⚠️ Order book also failed for {symbol}: {order_error}")
                
                # Method 2: Try direct API call to market data
                try:
                    # Alternative: Try fetching from market table directly
                    market_data = fetch_from_hive_engine(api, "market", "buyBook", {"symbol": symbol}, limit=1)
                    if not market_data:
                        market_data = fetch_from_hive_engine(api, "market", "sellBook", {"symbol": symbol}, limit=1)
                    
                    if market_data and len(market_data) > 0:
                        price = float(market_data[0].get("price", 0))
                        if price > 0:
                            debug_log(f"  ✅ Using direct market data for {symbol}: {price:.8f} HIVE")
                            market_cache[symbol] = (price, 0.0)
                            return price, 0.0
                            
                except Exception as direct_error:
                    debug_log(f"  ⚠️ Direct market query failed for {symbol}: {direct_error}")
                
                break  # Don't retry if it's a "does not exists" error
            
            if attempt < retries - 1:
                time.sleep(delay)

    # If all methods fail, check if we got metrics data earlier
    try:
        metrics = fetch_market_metrics(api, symbol)
        if metrics:
            last_price = float(metrics.get('lastPrice', 0))
            if last_price > 0:
                debug_log(f"  🔄 Falling back to metrics price for {symbol}: {last_price:.8f} HIVE")
                market_cache[symbol] = (last_price, 0.0)
                return last_price, 0.0
    except:
        pass

    debug_log(f"❌ All methods failed for {symbol}. Setting price to 0.")
    market_cache[symbol] = (0.0, 0.0)
    return 0.0, 0.0

def get_token_holdings(api, account, tokens):
    """
    Get token holdings (liquid, staked, delegated) for an account
    
    Args:
        api: Hive Engine API instance
        account: Hive username
        tokens: List of token symbols to check
        
    Returns:
        Dict with token holdings data
    """
    liquid = fetch_from_hive_engine(api, "tokens", "balances", {"account": account})
    delegated = fetch_from_hive_engine(api, "tokens", "delegations", {"from": account})

    tokens = set(tokens)  # for fast lookup
    res = defaultdict(lambda: {"liquid": 0, "staked": 0, "delegated_away": 0})

    for b in liquid:
        s = b["symbol"]
        if s not in tokens:
            continue
        res[s]["liquid"] = float(b["balance"])
        res[s]["staked"] = float(b.get("stake", 0))  # or "staked" if that's the correct field
        res[s]["delegated_away"] = float(b.get("delegations", 0))

    for d in delegated:
        s = d["symbol"]
        if s not in tokens:
            continue
        res[s]["delegated_away"] += float(d["quantity"])

    return res

def fetch_all_tokens(api):
    """
    Fetch complete list of all tokens from Hive Engine for validation
    
    Args:
        api: Hive Engine API instance
        
    Returns:
        Set of all valid token symbols
    """
    tokens = []
    offset = 0
    limit = 1000
    while True:
        batch = fetch_from_hive_engine(api, "tokens", "tokens", {}, limit=limit, offset=offset)
        if not batch:
            break
        tokens.extend(batch)
        offset += len(batch)
    return {t["symbol"] for t in tokens if "symbol" in t}

# CoinGecko API utilities
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

def get_hive_price_usd():
    """Get current HIVE price in USD from CoinGecko"""
    global price_cache
    
    if "HIVE" in price_cache:
        return price_cache["HIVE"]

    try:
        resp = requests.get(COINGECKO_API, params={"ids":"hive","vs_currencies":"usd"})
        resp.raise_for_status()
        price = resp.json().get("hive", {}).get("usd", 0)
        price_cache["HIVE"] = price
        return price
    except Exception as e:
        print(f"❌ Error fetching HIVE price: {e}")
        return 0

def get_btc_price_usd():
    """Get current BTC price in USD from CoinGecko"""
    global price_cache
    
    if "BTC" in price_cache:
        return price_cache["BTC"]

    try:
        resp = requests.get(COINGECKO_API, params={"ids":"bitcoin","vs_currencies":"usd"})
        resp.raise_for_status()
        price = resp.json().get("bitcoin", {}).get("usd", 0)
        price_cache["BTC"] = price
        return price
    except Exception as e:
        print(f"❌ Error fetching BTC price: {e}")
        return 0

# Validation utilities
def validate_username(username):
    """
    Validate Hive username according to rules:
    - Must be lowercase (should be automatically)
    - Start with a letter
    - Only letters, numbers, dashes, and dots
    - Length between 3 and 16 characters
    - Dashes and dots cannot be consecutive or at beginning/end
    """
    if not username:
        return False, "Username cannot be empty"
    
    # Check length
    if len(username) < 3 or len(username) > 16:
        return False, "Username must be between 3 and 16 characters"
    
    # Check if lowercase
    if username != username.lower():
        return False, "Username must be lowercase"
    
    # Check if starts with letter
    if not username[0].isalpha():
        return False, "Username must start with a letter"
    
    # Check if ends with dash or dot
    if username[-1] in '-.':
        return False, "Username cannot end with dash or dot"
    
    # Check allowed characters
    allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789-.')
    if not all(c in allowed_chars for c in username):
        return False, "Username can only contain letters, numbers, dashes, and dots"
    
    # Check for consecutive dashes/dots
    for i in range(len(username) - 1):
        if username[i] in '-.' and username[i + 1] in '-.':
            return False, "Username cannot have consecutive dashes or dots"
    
    return True, "Valid username"

def validate_token(token, valid_token_symbols):
    """
    Validate if a token exists in Hive Engine
    
    Args:
        token: Token symbol to validate
        valid_token_symbols: Set of valid token symbols
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not token:
        return False, "Token cannot be empty"
    
    if token not in valid_token_symbols:
        return False, f"Token '{token}' is not found in Hive Engine token list"
    
    return True, "Valid token"

def clear_caches():
    """Clear all global caches"""
    global price_cache, market_cache
    price_cache.clear()
    market_cache.clear()
