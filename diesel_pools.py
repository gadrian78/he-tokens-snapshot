"""
Hive Engine Diesel Pools Module

Extracted from the main Hive Engine tokens snapshot script.
Contains all diesel pool related functionality.

Usage:
    from diesel_pools import get_user_pool_portfolio, display_diesel_pools_table
    
    pool_data = get_user_pool_portfolio(account, api_instance, token_prices)
    display_diesel_pools_table(pool_data, hive_price_usd, btc_price_usd, account)

Created by https://peakd.com/@gadrian using "vibe" coding in June 2025.
"""

import time
import random
from prettytable import PrettyTable, TableStyle

from hive_engine_utils import fetch_from_hive_engine

# Global debug flag - can be set from main script
DEBUG = False

def debug_log(text):
    """Debug logging function"""
    if DEBUG:
        print(text)

def get_diesel_pool_info(api, token_pair, retries=5, delay=3):
    """Enhanced pool info fetching with multiple fallback methods"""
    try:
        # Split the token pair
        tokens = token_pair.split(":")
        if len(tokens) != 2:
            debug_log(f"⚠️ Invalid token pair format: {token_pair}")
            return None
            
        base_token, quote_token = tokens
        debug_log(f"🔍 Looking for pool: {base_token}/{quote_token}")
        
        # Try different query methods with enhanced error handling
        pool_info = None
        
        for attempt in range(retries):
            try:
                # Add delay between attempts
                if attempt > 0:
                    sleep_time = delay * (attempt + 1) + random.uniform(0.5, 2.0)
                    debug_log(f"⏳ Waiting {sleep_time:.1f} seconds before pool info retry {attempt + 1}/{retries}...")
                    time.sleep(sleep_time)
                
                # Method 1: Query by tokenPair
                debug_log(f"🔍 Method 1: Querying by tokenPair '{token_pair}'...")
                pool_data = fetch_from_hive_engine(api, "marketpools", "pools", {"tokenPair": token_pair}, limit=1)
                if pool_data and len(pool_data) > 0:
                    pool_info = pool_data[0]
                    debug_log(f"✅ Found pool info using tokenPair query for {token_pair}")
                    break
                
                # Method 2: Query by base and quote symbols
                debug_log(f"🔍 Method 2: Querying by baseSymbol='{base_token}', quoteSymbol='{quote_token}'...")
                pool_data = fetch_from_hive_engine(api, "marketpools", "pools", 
                                                   {"baseSymbol": base_token, "quoteSymbol": quote_token}, limit=1)
                if pool_data and len(pool_data) > 0:
                    pool_info = pool_data[0]
                    debug_log(f"✅ Found pool info using base/quote query for {token_pair}")
                    break
                
                # Method 3: Try reversed order
                debug_log(f"🔍 Method 3: Querying by baseSymbol='{quote_token}', quoteSymbol='{base_token}'...")
                pool_data = fetch_from_hive_engine(api, "marketpools", "pools", 
                                                   {"baseSymbol": quote_token, "quoteSymbol": base_token}, limit=1)
                if pool_data and len(pool_data) > 0:
                    pool_info = pool_data[0]
                    debug_log(f"✅ Found pool info using reversed base/quote query for {token_pair}")
                    break
                
                # Method 4: Try querying all pools and filter locally
                debug_log(f"🔍 Method 4: Fetching all pools and filtering locally...")
                all_pools = fetch_from_hive_engine(api, "marketpools", "pools", {}, limit=100)
                if all_pools:
                    for pool in all_pools:
                        pool_token_pair = pool.get("tokenPair", "")
                        pool_base = pool.get("baseSymbol", "")
                        pool_quote = pool.get("quoteSymbol", "")
                        
                        # Check if this pool matches our target
                        if (pool_token_pair == token_pair or 
                            (pool_base == base_token and pool_quote == quote_token) or
                            (pool_base == quote_token and pool_quote == base_token)):
                            pool_info = pool
                            debug_log(f"✅ Found pool info using local filtering for {token_pair}")
                            break
                    
                    if pool_info:
                        break
                
                debug_log(f"❌ No pool found with any method on attempt {attempt + 1}")
                
            except Exception as e:
                debug_log(f"❌ Error in pool info attempt {attempt + 1}: {e}")
                continue
        
        if not pool_info:
            debug_log(f"❌ No pool info found for {token_pair} after all attempts")
            return None
            
        # Extract and validate pool data
        actual_base_token = pool_info.get("baseSymbol", base_token)
        actual_quote_token = pool_info.get("quoteSymbol", quote_token)
        base_quantity = float(pool_info.get("baseQuantity", 0))
        quote_quantity = float(pool_info.get("quoteQuantity", 0))
        total_shares = float(pool_info.get("totalShares", 0))
        
        if total_shares == 0:
            debug_log(f"⚠️ Pool {token_pair} has zero total shares")
            return None
        
        pool_data = {
            "token_pair": token_pair,
            "base_token": actual_base_token,
            "quote_token": actual_quote_token,
            "base_quantity": base_quantity,
            "quote_quantity": quote_quantity,
            "total_shares": total_shares,
            "pool_id": pool_info.get("_id", "")
        }
        
        debug_log(f"✅ Pool {token_pair}: {actual_base_token}/{actual_quote_token} - {base_quantity:.4f}/{quote_quantity:.4f} tokens, {total_shares:.4f} total shares")
        
        return pool_data
        
    except Exception as e:
        debug_log(f"❌ Fatal error fetching pool info for {token_pair}: {e}")
        return None

def get_diesel_pool_holdings(api, account, retries=5, delay=3):
    """Enhanced diesel pool holdings fetching with better error handling"""
    for attempt in range(retries):
        try:
            if attempt > 0:
                sleep_time = delay * attempt + random.uniform(0.5, 2.0)
                debug_log(f"⏳ Waiting {sleep_time:.1f} seconds before retry {attempt + 1}/{retries}...")
                time.sleep(sleep_time)
            
            debug_log(f"🔄 Fetching diesel pool positions for @{account} (attempt {attempt + 1}/{retries})")
            
            # Fetch user's liquidity positions
            positions = fetch_from_hive_engine(api, "marketpools", "liquidityPositions", {"account": account})
            
            if not positions:
                debug_log(f"No diesel pool positions found for @{account}")
                return {}
                
            pool_holdings = {}
            
            for position in positions:
                pool_id = position.get("_id")
                token_pair = position.get("tokenPair", "")
                shares = float(position.get("shares", 0))
                
                if shares > 0 and token_pair:
                    # Split token pair to get individual tokens
                    tokens = token_pair.split(":")
                    if len(tokens) == 2:
                        base_token, quote_token = tokens
                        
                        pool_holdings[token_pair] = {
                            "pool_id": pool_id,
                            "shares": shares,
                            "token_pair": token_pair,
                            "base_token": base_token,
                            "quote_token": quote_token
                        }
                        debug_log(f"✅ Found diesel pool position: {token_pair} - {shares} shares")
                    else:
                        debug_log(f"⚠️ Invalid token pair format: {token_pair}")
            
            debug_log(f"✅ Successfully fetched {len(pool_holdings)} diesel pool positions")
            return pool_holdings
            
        except Exception as e:
            error_msg = str(e).lower()
            debug_log(f"❌ Error fetching diesel pool holdings (attempt {attempt + 1}/{retries}): {e}")
            
            # Check for specific errors that warrant retrying
            if ("service temporarily unavailable" in error_msg or 
                "503" in error_msg or 
                "timeout" in error_msg or 
                "connection" in error_msg):
                continue
            else:
                # For other errors, don't retry as aggressively
                if attempt >= 2:
                    break
            
        # If this was the last attempt, return empty dict
        if attempt == retries - 1:
            debug_log(f"❌ All {retries} attempts failed for diesel pool holdings")
            return {}
    
    return {}

def calculate_pool_token_values(user_shares, pool_info, token_prices):
    """Calculate the underlying token values for user's pool shares"""
    
    if not pool_info or user_shares == 0:
        return {"base_amount": 0, "quote_amount": 0, "base_value_hive": 0, "quote_value_hive": 0, "total_value_hive": 0}
    
    total_shares = pool_info["total_shares"]
    user_share_ratio = user_shares / total_shares
    
    # Calculate user's share of underlying tokens
    base_amount = pool_info["base_quantity"] * user_share_ratio
    quote_amount = pool_info["quote_quantity"] * user_share_ratio
    
    # Get token prices (default to 0 if not found)
    base_token = pool_info["base_token"]
    quote_token = pool_info["quote_token"]
    
    base_price_hive = token_prices.get(base_token, 0)
    quote_price_hive = token_prices.get(quote_token, 0)
    
    # Calculate values in HIVE
    base_value_hive = base_amount * base_price_hive
    quote_value_hive = quote_amount * quote_price_hive
    total_value_hive = base_value_hive + quote_value_hive

    debug_log(f"Pool {pool_info['token_pair']} calculated value: {total_value_hive} HIVE")
    
    return {
        "base_token": base_token,
        "quote_token": quote_token,
        "base_amount": base_amount,
        "quote_amount": quote_amount,
        "base_price_hive": base_price_hive,
        "quote_price_hive": quote_price_hive,
        "base_value_hive": base_value_hive,
        "quote_value_hive": quote_value_hive,
        "total_value_hive": total_value_hive,
        "user_shares": user_shares,
        "share_percentage": user_share_ratio * 100
    }

def get_user_pool_portfolio(account, api, token_prices):
    """
    Main function to get user's complete diesel pool portfolio
    
    Args:
        account (str): Hive username
        api: Hive Engine API instance
        token_prices (dict): Dictionary of token prices in HIVE
    
    Returns:
        list: List of pool data dictionaries with calculated values
    """
    debug_log(f"🏊 Fetching diesel pool positions for @{account}...")
    pool_holdings = get_diesel_pool_holdings(api, account)

    pool_data = []
    if pool_holdings:
        debug_log(f"🏊 Processing {len(pool_holdings)} diesel pool positions...")
        
        for pool_token_pair, pool_position in pool_holdings.items():
            debug_log(f"📊 Fetching pool info for {pool_token_pair}...")
            pool_info = get_diesel_pool_info(api, pool_token_pair)
            
            if pool_info:
                # Calculate pool values
                pool_values = calculate_pool_token_values(
                    pool_position["shares"], 
                    pool_info, 
                    token_prices
                )
                
                if pool_values["total_value_hive"] > 0:
                    pool_data.append({
                        "token_pair": pool_token_pair,
                        "base_token": pool_values["base_token"],
                        "quote_token": pool_values["quote_token"],
                        "base_amount": pool_values["base_amount"],
                        "quote_amount": pool_values["quote_amount"],
                        "user_shares": pool_values["user_shares"],
                        "share_percentage": pool_values["share_percentage"],
                        "total_hive": pool_values["total_value_hive"]
                    })
    
    return pool_data

def display_diesel_pools_table(pool_data, hive_price_usd, btc_price_usd, account):
    """Display diesel pool holdings in a formatted table"""
    
    if not pool_data:
        return
    
    # Add USD and BTC values to pool data
    for pool in pool_data:
        pool["total_usd"] = pool["total_hive"] * hive_price_usd
        pool["total_btc"] = pool["total_usd"] / btc_price_usd if btc_price_usd > 0 else 0
        
    # Sort pools by total USD value (descending)
    sorted_pools = sorted(pool_data, key=lambda x: x["total_usd"], reverse=True)

    table = PrettyTable()
    table.field_names = [
        "Pool", "Base Token", "Base Amount", "Quote Token", "Quote Amount", 
        "Shares", "Share %", "USD Value", "HIVE Value", "BTC Value"
    ]

    total_usd = total_hive = total_btc = 0

    for pool in sorted_pools:
        pool_name = pool.get("token_pair", pool.get("symbol", "UNKNOWN"))

        table.add_row([
            pool_name,
            pool["base_token"],
            f'{pool["base_amount"]:,.4f}',
            pool["quote_token"], 
            f'{pool["quote_amount"]:,.4f}',
            f'{pool["user_shares"]:,.4f}',
            f'{pool["share_percentage"]:.4f}%',
            f'{pool["total_usd"]:,.2f}',
            f'{pool["total_hive"]:,.4f}',
            f'{pool["total_btc"]:,.8f}',
        ])

        total_usd += pool["total_usd"]
        total_hive += pool["total_hive"]
        total_btc += pool["total_btc"]

    if len(sorted_pools) > 1:  # Only add totals if more than one pool
        table.add_divider()
        table.add_row([
            "TOTAL", "", "", "", "", "", "",
            f'{total_usd:,.2f}',
            f'{total_hive:,.4f}',
            f'{total_btc:,.8f}'
        ])

    table.align = "r"
    table.align["Pool"] = "l"
    table.align["Base Token"] = "l" 
    table.align["Quote Token"] = "l"
    table.set_style(TableStyle.SINGLE_BORDER)

    print("🏊 DIESEL POOL POSITIONS:")
    print(table)
    print()

def get_all_diesel_pools(api):
    """Get list of all available diesel pools for validation"""
    try:
        pools = []
        offset = 0
        limit = 1000
        
        while True:
            batch = fetch_from_hive_engine(api, "marketpools", "pools", {}, limit=limit, offset=offset)
            if not batch:
                break
            pools.extend(batch)
            if len(batch) < limit:
                break
            offset += len(batch)
            
        return {p["symbol"] for p in pools if "symbol" in p}
        
    except Exception as e:
        debug_log(f"❌ Error fetching diesel pools list: {e}")
        return set()

def set_debug_mode(debug_enabled):
    """Set debug mode for this module"""
    global DEBUG
    DEBUG = debug_enabled
