"""
Hive Layer 1 Holdings Module

Functions for tracking Layer 1 Hive holdings: liquid HIVE, HIVE Power, 
liquid HBD, HBD in savings, and HIVE in savings.

Used by the Hive Portfolio Tracker tool.

Created by https://peakd.com/@gadrian using "vibe" coding in June-July 2025.
"""

import requests
import time
from prettytable import PrettyTable, TableStyle
from datetime import datetime

from modules.cache_utils import price_cache, l1_cache, is_cache_valid, save_cache

# Global debug flag that can be set by the main module
DEBUG = False

def debug_log(text):
    """Debug logging function that respects the DEBUG flag"""
    if DEBUG:
        print(text)

def set_debug_mode(enabled):
    """Set debug mode for this module"""
    global DEBUG
    DEBUG = enabled

# Hive API endpoints
HIVE_API_ENDPOINTS = [
    "https://api.hive.blog",
    "https://api.hivekings.com",
    "https://anyx.io",
    "https://api.openhive.network"
]

def call_hive_api(method, params, retries=3, timeout=10):
    """
    Make a call to Hive API with fallback endpoints
    
    Args:
        method: API method name (e.g., 'condenser_api.get_accounts')
        params: Parameters for the API call
        retries: Number of retry attempts per endpoint
        timeout: Request timeout in seconds
        
    Returns:
        API response result or None if all attempts fail
    """
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    for endpoint in HIVE_API_ENDPOINTS:
        for attempt in range(retries):
            try:
                debug_log(f"🔄 Calling {endpoint} (attempt {attempt + 1}/{retries})")
                response = requests.post(endpoint, json=payload, timeout=timeout)
                response.raise_for_status()
                
                data = response.json()
                if "result" in data:
                    debug_log(f"✅ API call successful to {endpoint}")
                    return data["result"]
                elif "error" in data:
                    debug_log(f"❌ API error from {endpoint}: {data['error']}")
                    
            except requests.exceptions.Timeout:
                debug_log(f"⏰ Timeout calling {endpoint}")
                if attempt < retries - 1:
                    time.sleep(2)
                    
            except requests.exceptions.RequestException as e:
                debug_log(f"❌ Request error to {endpoint}: {e}")
                if attempt < retries - 1:
                    time.sleep(2)
                    
            except Exception as e:
                debug_log(f"❌ Unexpected error with {endpoint}: {e}")
                if attempt < retries - 1:
                    time.sleep(2)
    
    debug_log(f"❌ All API endpoints failed for method {method}")
    return None

def get_hive_account_info(username):
    """
    Get account information from Hive blockchain
    
    Args:
        username: Hive username
        
    Returns:
        Dict with account information or None if failed
    """
    cache_key = f"hive_account_{username}"
    
    # Check cache first
    if cache_key in l1_cache and is_cache_valid(l1_cache[cache_key]):
        debug_log(f"📋 Using cached account info for @{username}")
        return l1_cache[cache_key]["value"]
    
    debug_log(f"🔍 Fetching account info for @{username}")
    
    result = call_hive_api("condenser_api.get_accounts", [[username]])
    
    if result and len(result) > 0:
        account_data = result[0]
        # Cache the result
        l1_cache[cache_key] = {"value": account_data, "timestamp": time.time()}
        save_cache()
        return account_data
    else:
        debug_log(f"❌ Failed to get account info for @{username}")
        return None

def get_hive_global_properties():
    """
    Get global properties from Hive blockchain
    
    Returns:
        Dict with global properties or None if failed
    """
    cache_key = "hive_global_props"
    
    # Check cache first
    if cache_key in l1_cache and is_cache_valid(l1_cache[cache_key]):
        debug_log(f"🌍 Using cached global properties")
        return l1_cache[cache_key]["value"]
    
    debug_log(f"🌍 Fetching global properties")
    
    result = call_hive_api("condenser_api.get_dynamic_global_properties", [])
    
    if result:
        # Cache the result
        l1_cache[cache_key] = {"value": result, "timestamp": time.time()}
        save_cache()
        return result
    else:
        debug_log(f"❌ Failed to get global properties")
        return None

def calculate_hive_power(vesting_shares, global_props):
    """
    Calculate HIVE Power from vesting shares
    
    Args:
        vesting_shares: Vesting shares string (e.g., "1000.000000 VESTS")
        global_props: Global properties dict
        
    Returns:
        Float value of HIVE Power
    """
    try:
        # Parse vesting shares
        vests = float(vesting_shares.split()[0])
        
        # Get conversion rate from global properties
        total_vesting_fund_hive = float(global_props["total_vesting_fund_hive"].split()[0])
        total_vesting_shares = float(global_props["total_vesting_shares"].split()[0])
        
        if total_vesting_shares > 0:
            hive_power = vests * total_vesting_fund_hive / total_vesting_shares
            return hive_power
        else:
            return 0.0
            
    except Exception as e:
        debug_log(f"❌ Error calculating HIVE Power: {e}")
        return 0.0

def parse_hive_amount(amount_str):
    """
    Parse Hive amount string to float
    
    Args:
        amount_str: Amount string (e.g., "100.000 HIVE" or "50.000 HBD")
        
    Returns:
        Float value
    """
    try:
        return float(amount_str.split()[0])
    except:
        return 0.0

def get_hive_layer1_holdings(username):
    """
    Get Layer 1 Hive holdings for a user
    
    Args:
        username: Hive username
        
    Returns:
        Dict with Layer 1 holdings data
    """
    debug_log(f"🏦 Fetching Layer 1 holdings for @{username}")
    
    # Get account info
    account_info = get_hive_account_info(username)
    if not account_info:
        return None
    
    # Get global properties for HIVE Power calculation
    global_props = get_hive_global_properties()
    if not global_props:
        return None
    
    # Parse holdings
    holdings = {}
    
    # Liquid HIVE
    holdings["liquid_hive"] = parse_hive_amount(account_info.get("balance", "0.000 HIVE"))
    
    # HIVE Power (owned + delegated in - delegated out)
    vesting_shares = account_info.get("vesting_shares", "0.000000 VESTS")
    delegated_vesting_shares = account_info.get("delegated_vesting_shares", "0.000000 VESTS")
    received_vesting_shares = account_info.get("received_vesting_shares", "0.000000 VESTS")
    
    # Calculate individual components
    owned_hp = calculate_hive_power(vesting_shares, global_props)
    delegated_out_hp = calculate_hive_power(delegated_vesting_shares, global_props)
    delegated_in_hp = calculate_hive_power(received_vesting_shares, global_props)
    
    holdings["hive_power_owned"] = owned_hp
    holdings["hive_power_delegated_out"] = delegated_out_hp
    holdings["hive_power_delegated_in"] = delegated_in_hp
    holdings["hive_power_effective"] = owned_hp + delegated_in_hp - delegated_out_hp
    
    # Liquid HBD
    holdings["liquid_hbd"] = parse_hive_amount(account_info.get("hbd_balance", "0.000 HBD"))
    
    # HBD in savings
    holdings["savings_hbd"] = parse_hive_amount(account_info.get("savings_hbd_balance", "0.000 HBD"))
    
    # HIVE in savings
    holdings["savings_hive"] = parse_hive_amount(account_info.get("savings_balance", "0.000 HIVE"))
    
    debug_log(f"✅ Successfully fetched Layer 1 holdings for @{username}")
    return holdings

def get_hbd_price_usd():
    """Get current HBD price in USD from CoinGecko"""
    if "HBD" in price_cache and is_cache_valid(price_cache["HBD"]):
        return price_cache["HBD"]["value"]

    try:
        resp = requests.get("https://api.coingecko.com/api/v3/simple/price", 
                          params={"ids":"hive_dollar","vs_currencies":"usd"})
        resp.raise_for_status()
        price = resp.json().get("hive_dollar", {}).get("usd", 1.0)  # Default to $1 if not found
        price_cache["HBD"] = {"value": price, "timestamp": time.time()}
        save_cache()
        return price
    except Exception as e:
        debug_log(f"❌ Error fetching HBD price: {e}")
        return 1.0  # Default to $1 for HBD

def calculate_layer1_values(holdings, hive_usd, hbd_usd, btc_usd):
    """
    Calculate USD, HIVE, and BTC values for Layer 1 holdings
    
    Args:
        holdings: Dict with Layer 1 holdings
        hive_usd: HIVE price in USD
        hbd_usd: HBD price in USD
        btc_usd: BTC price in USD
        
    Returns:
        Dict with calculated values
    """
    if not holdings:
        return None
    
    values = {}
    
    # HIVE holdings (liquid + savings + effective HP)
    total_hive = holdings["liquid_hive"] + holdings["savings_hive"] + holdings["hive_power_owned"]
    values["total_hive_amount"] = total_hive
    values["total_hive_usd"] = total_hive * hive_usd
    values["total_hive_btc"] = values["total_hive_usd"] / btc_usd if btc_usd > 0 else 0
    
    # HBD holdings (liquid + savings)
    total_hbd = holdings["liquid_hbd"] + holdings["savings_hbd"]
    values["total_hbd_amount"] = total_hbd
    values["total_hbd_usd"] = total_hbd * hbd_usd
    values["total_hbd_btc"] = values["total_hbd_usd"] / btc_usd if btc_usd > 0 else 0
    
    # Combined totals
    values["total_combined_usd"] = values["total_hive_usd"] + values["total_hbd_usd"]
    values["total_combined_hive"] = values["total_combined_usd"] / hive_usd if hive_usd > 0 else 0
    values["total_combined_btc"] = values["total_combined_usd"] / btc_usd if btc_usd > 0 else 0
    
    # Individual component values
    values["liquid_hive_usd"] = holdings["liquid_hive"] * hive_usd
    values["savings_hive_usd"] = holdings["savings_hive"] * hive_usd
    values["hive_power_usd"] = holdings["hive_power_owned"] * hive_usd
    values["liquid_hbd_usd"] = holdings["liquid_hbd"] * hbd_usd
    values["savings_hbd_usd"] = holdings["savings_hbd"] * hbd_usd
    
    return values

def display_layer1_table(holdings, values, hive_usd, hbd_usd, btc_usd, username):
    """
    Display Layer 1 holdings in a formatted table
    
    Args:
        holdings: Dict with Layer 1 holdings
        values: Dict with calculated values
        hive_usd: HIVE price in USD
        hbd_usd: HBD price in USD
        btc_usd: BTC price in USD
        username: Hive username
    """
    if not holdings or not values:
        print("ℹ️ No Layer 1 holdings found")
        return
    
    table = PrettyTable()
    table.field_names = [
        "Asset Type", "Amount", "Price (USD)", "USD Value", "HIVE Value", "BTC Value"
    ]
    
    # Add rows for each holding type
    rows = [
        ["Liquid HIVE", f'{holdings["liquid_hive"]:,.3f}', f'${hive_usd:,.2f}', 
         f'${values["liquid_hive_usd"]:,.2f}', f'{holdings["liquid_hive"]:,.3f}', 
         f'{values["liquid_hive_usd"] / btc_usd:.8f}' if btc_usd > 0 else '0.00000000'],
        
        ["Owned HP", f'{holdings["hive_power_owned"]:,.3f}', f'${hive_usd:,.2f}', 
         f'${values["hive_power_usd"]:,.2f}', f'{holdings["hive_power_owned"]:,.3f}', 
         f'{values["hive_power_usd"] / btc_usd:.8f}' if btc_usd > 0 else '0.00000000'],
        
        ["HIVE Savings", f'{holdings["savings_hive"]:,.3f}', f'${hive_usd:.6f}', 
         f'${values["savings_hive_usd"]:,.2f}', f'{holdings["savings_hive"]:,.3f}', 
         f'{values["savings_hive_usd"] / btc_usd:.8f}' if btc_usd > 0 else '0.00000000'],
        
        ["Liquid HBD", f'{holdings["liquid_hbd"]:,.3f}', f'${hbd_usd:.6f}', 
         f'${values["liquid_hbd_usd"]:,.2f}', f'{holdings["liquid_hbd"] / hive_usd:.3f}' if hive_usd > 0 else '0.000', 
         f'{values["liquid_hbd_usd"] / btc_usd:.8f}' if btc_usd > 0 else '0.00000000'],
        
        ["HBD Savings", f'{holdings["savings_hbd"]:,.3f}', f'${hbd_usd:.6f}', 
         f'${values["savings_hbd_usd"]:,.2f}', f'{holdings["savings_hbd"] / hive_usd:.3f}' if hive_usd > 0 else '0.000', 
         f'{values["savings_hbd_usd"] / btc_usd:.8f}' if btc_usd > 0 else '0.00000000']
    ]
    
    # Only add rows with non-zero values
    for row in rows:
        if float(row[1].replace(',', '')) > 0:
            table.add_row(row)
    
    # Add totals if we have multiple non-zero holdings
    non_zero_count = sum(1 for row in rows if float(row[1].replace(',', '')) > 0)
    if non_zero_count > 1:
        table.add_divider()
        table.add_row([
            "TOTAL", "", "",
            f'${values["total_combined_usd"]:,.2f}',
            f'{values["total_combined_hive"]:,.3f}',
            f'{values["total_combined_btc"]:.8f}'
        ])
    
    table.align = "r"
    table.align["Asset Type"] = "l"
    table.set_style(TableStyle.SINGLE_BORDER)
    
    print("🏦 LAYER 1 HIVE HOLDINGS:")
    print(table)
    
    # Add detailed HIVE Power breakdown if relevant
    if holdings["hive_power_delegated_in"] > 0 or holdings["hive_power_delegated_out"] > 0:
        print()
        print("📊 HIVE Power Details:")
        print(f"   Owned HP:        {holdings['hive_power_owned']:11,.3f} HIVE")
        if holdings["hive_power_delegated_in"] > 0:
            print(f"   Delegated In:   +{holdings['hive_power_delegated_in']:11,.3f} HIVE")
        if holdings["hive_power_delegated_out"] > 0:
            print(f"   Delegated Out:  -{holdings['hive_power_delegated_out']:11,.3f} HIVE")
        print(f"   Effective HP:    {holdings['hive_power_effective']:11,.3f} HIVE")

def create_layer1_json_data(holdings, values, hive_usd, hbd_usd, btc_usd, username, timestamp):
    """
    Create JSON data structure for Layer 1 holdings
    
    Args:
        holdings: Dict with Layer 1 holdings
        values: Dict with calculated values
        hive_usd: HIVE price in USD
        hbd_usd: HBD price in USD
        btc_usd: BTC price in USD
        username: Hive username
        timestamp: Timestamp string
        
    Returns:
        Dict with Layer 1 data for JSON serialization
    """
    if not holdings or not values:
        return {}
    
    return {
        "liquid_hive": {
            "amount": holdings["liquid_hive"],
            "value_usd": values["liquid_hive_usd"],
            "value_hive": holdings["liquid_hive"],
            "value_btc": values["liquid_hive_usd"] / btc_usd if btc_usd > 0 else 0
        },
        "hive_power": {
            "owned": holdings["hive_power_owned"],
            "delegated_in": holdings["hive_power_delegated_in"],
            "delegated_out": holdings["hive_power_delegated_out"],
            "value_usd": values["hive_power_usd"], # hive power owned
            "value_hive": holdings["hive_power_owned"],
            "value_btc": values["hive_power_usd"] / btc_usd if btc_usd > 0 else 0
        },
        "savings_hive": {
            "amount": holdings["savings_hive"],
            "value_usd": values["savings_hive_usd"],
            "value_hive": holdings["savings_hive"],
            "value_btc": values["savings_hive_usd"] / btc_usd if btc_usd > 0 else 0
        },
        "liquid_hbd": {
            "amount": holdings["liquid_hbd"],
            "value_usd": values["liquid_hbd_usd"],
            "value_hive": holdings["liquid_hbd"] / hive_usd if hive_usd > 0 else 0,
            "value_btc": values["liquid_hbd_usd"] / btc_usd if btc_usd > 0 else 0
        },
        "savings_hbd": {
            "amount": holdings["savings_hbd"],
            "value_usd": values["savings_hbd_usd"],
            "value_hive": holdings["savings_hbd"] / hive_usd if hive_usd > 0 else 0,
            "value_btc": values["savings_hbd_usd"] / btc_usd if btc_usd > 0 else 0
        },
        "totals": {
            "total_hive_amount": values["total_hive_amount"],
            "total_hbd_amount": values["total_hbd_amount"],
            "total_value_usd": values["total_combined_usd"],
            "total_value_hive": values["total_combined_hive"],
            "total_value_btc": values["total_combined_btc"]
        }
    }

def get_user_layer1_portfolio(username):
    """
    Get complete Layer 1 portfolio for a user
    
    Args:
        username: Hive username
        
    Returns:
        Tuple of (holdings, values) or (None, None) if failed
    """
    debug_log(f"🏦 Getting Layer 1 portfolio for @{username}")
    
    # Get holdings
    holdings = get_hive_layer1_holdings(username)
    if not holdings:
        return None, None
    
    # Get prices
    from modules.regular_tokens import get_hive_price_usd, get_btc_price_usd
    hive_usd = get_hive_price_usd()
    btc_usd = get_btc_price_usd()
    hbd_usd = get_hbd_price_usd()
    
    # Calculate values
    values = calculate_layer1_values(holdings, hive_usd, hbd_usd, btc_usd)
    
    return holdings, values
