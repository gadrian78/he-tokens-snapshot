######################################
#
# My Hive Engine Tokens Snapshot
#
# Created by https://peakd.com/@gadrian using "vibe" coding in June 2025.
#
# Use it or modify to your needs freely. Keep this author details and add to it, if you build on it.
#
######################################

import requests
from collections import defaultdict
from datetime import datetime, timedelta
import time
from prettytable import PrettyTable, TableStyle
import argparse

from hiveengine.api import Api
from hiveengine.market import Market

api = Api()
market = Market(api)

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

VERSION = "1.0"

DEFAULT_ACCOUNT = "gadrian" # change to your username
DEFAULT_TOKENS = ["SWAP.HIVE", "SPS", "DEC", "LEO"] # change to your prefered list of Hive-Engine tokens

DEBUG = False

def debug_log(text):
    if (DEBUG):
        print(text)

def fetch_from_hive_engine(contract, table, query):
    try:
        result = api.find(contract, table, query, limit=1000)
        if result is None:
            debug_log(f"⚠️ Warning: No results for {table} with query {query}")
            return []
        return result
    except Exception as e:
        print(f"❌ Error fetching {table}: {e}")
        return []

def get_token_holdings(account, tokens):
    liquid = fetch_from_hive_engine("tokens", "balances", {"account": account})
    delegated = fetch_from_hive_engine("tokens", "delegations", {"from": account})

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

def get_volume_since(trades, since_seconds_ago):
    now = int(time.time())  # current UNIX time (seconds)
    cutoff = now - since_seconds_ago
    return sum(float(t["volume"]) for t in trades if t.get("volume") and t["timestamp"] >= cutoff)

def get_24h_volume(trades):
    return get_volume_since(trades, 86400)

def get_market_info(symbol):
    # Fetch trade history (includes price & timestamp)
    trades = market.get_trades_history(symbol, limit=1000)
    if not trades:
        if (symbol == "SWAP.HIVE"):
            debug_log(f"  No trades returned for {symbol}")
            return 1.0, 0.0
        else:
            print(f"⚠️ No trades returned for {symbol}")
            return 0.0, 0.0

    # Latest price (first trade)
    price_hive = float(trades[0]["price"])
    vol24 = get_24h_volume(trades)

    return price_hive, vol24

def display_table(token_data, hive_price_usd, btc_price_usd, account):
    # Sort tokens by total USD value (descending)
    sorted_tokens = sorted(token_data, key=lambda x: x["total_usd"], reverse=True)

    table = PrettyTable()
    table.field_names = [
        "Symbol", "Liquid", "Staked", "Delegated", "Total", 
        "Price (HIVE)", "Price (USD)", 
        "24h Vol (USD)", "USD Value", "HIVE Value", "BTC Value"
    ]

    total_usd = total_hive = total_btc = 0

    for token in sorted_tokens:
        table.add_row([
            token["symbol"],
            f'{token["liquid"]:,.3f}',
            f'{token["staked"]:,.3f}',
            f'{token["delegated"]:,.3f}',
            f'{token["liquid"] + token["staked"] + token["delegated"]:,.3f}',
            f'{token["price_hive"]:,.6f}',
            f'{token["price_usd"]:,.2f}',
            f'{token["volume_24h_usd"]:,.2f}',
            f'{token["total_usd"]:,.2f}',
            f'{token["total_hive"]:,.3f}',
            f'{token["total_btc"]:,.8f}',
        ])

        total_usd += token["total_usd"]
        total_hive += token["total_hive"]
        total_btc += token["total_btc"]

    table.add_divider()

    # Add summary row
    table.add_row([
        "TOTAL", "", "", "", "",
        "", "",
        "",
        f'{total_usd:,.2f}',
        f'{total_hive:,.3f}',
        f'{total_btc:,.8f}'
    ])

    table.align = "r"
    table.align["Symbol"] = "l"

    
    table.set_style(TableStyle.SINGLE_BORDER)

    print(table)

    # Add BTC/HIVE ratio, and prices of HIVE and BTC
    if btc_price_usd > 0:
        hive_btc_ratio = int(btc_price_usd / hive_price_usd)
        print()
        print(f"  HIVE BTC ≈ 1 / {hive_btc_ratio:,.0f}")
        print(f"  HIVE USD = {hive_price_usd:,.6f}")
        print(f"  BTC  USD = {btc_price_usd:,.0f}")
        print()

def get_hive_price_usd():
    try:
        resp = requests.get(COINGECKO_API, params={"ids":"hive","vs_currencies":"usd"})
        resp.raise_for_status()
        return resp.json().get("hive", {}).get("usd", 0)
    except Exception as e:
        print(f"❌ Error fetching HIVE price: {e}")
        return 0

def get_btc_price_usd():
    try:
        resp = requests.get(COINGECKO_API, params={"ids":"bitcoin","vs_currencies":"usd"})
        resp.raise_for_status()
        return resp.json().get("bitcoin", {}).get("usd", 0)
    except Exception as e:
        print(f"❌ Error fetching BTC price: {e}")
        return 0

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

def validate_token(token):
    """
    Validate token according to rules:
    - Must be uppercase (should be automatically)
    - Only letters and dots (for tokens like SWAP.BTC)
    - Maximum 10 characters
    """
    if not token:
        return False, "Token cannot be empty"
    
    # Check length
    if len(token) > 10:
        return False, f"Token '{token}' exceeds 10 character limit"
    
    # Check if uppercase
    if token != token.upper():
        return False, f"Token '{token}' must be uppercase"
    
    # Check allowed characters (letters and dots only)
    allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ.')
    if not all(c in allowed_chars for c in token):
        return False, f"Token '{token}' can only contain uppercase letters and dots"
    
    return True, "Valid token"

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=f"My Hive Engine Tokens Snapshot v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 he-tokens-snapshot.py
  python3 he-tokens-snapshot.py -u alice
  python3 he-tokens-snapshot.py -u bob -t SPS LEO DEC
  python3 he-tokens-snapshot.py --username charlie --tokens SWAP.BTC DBOND INCOME

Remarks:
  - Username must be a valid Hive username.
  - Tokens must be valid Hive-Engine tokens.

Tip:
  Use redirect to have the output in a file instead of the screen.
        """
    )
    
    parser.add_argument(
        '-u', '--username',
        type=str,
        help='Hive username to check (default: gadrian)'
    )
    
    parser.add_argument(
        '-t', '--tokens',
        nargs='+',
        type=str,
        help='List of tokens to snapshot (default: SWAP.HIVE SPS DEC LEO)'
    )
    
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Use command line arguments if provided, otherwise use defaults
    ACCOUNT = args.username if args.username else DEFAULT_ACCOUNT
    TOKENS = [token.upper() for token in args.tokens] if args.tokens else DEFAULT_TOKENS

    if (ACCOUNT):
        ACCOUNT = ACCOUNT.lower()
    # Validate username
    is_valid_user, user_msg = validate_username(ACCOUNT)
    if not is_valid_user:
        print(f"❌ Invalid username '{ACCOUNT}': {user_msg}")
        print("   Username must be a valid Hive username.")
        return
    
    # Validate tokens
    for token in TOKENS:
        is_valid_token, token_msg = validate_token(token)
        if not is_valid_token:
            print(f"❌ Invalid token: {token_msg}")
            print("   Token must be a valid Hive-Engine token.")
            return
    
    # Display what we're using
    print(f"🎯 Account: @{ACCOUNT}")
    print(f"🪙 Tokens: {', '.join(TOKENS)}")
    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"   Snapshot date/time: {dt}")
    print()

    debug_log(f"🔄 Fetching portfolio data for @{ACCOUNT}...")
    
    holdings = get_token_holdings(ACCOUNT, TOKENS)
    hive_usd = get_hive_price_usd()
    btc_usd = get_btc_price_usd()
    
    debug_log(f"💰 HIVE Price: ${hive_usd:.6f}")
    debug_log(f"🪙 BTC Price: ${btc_usd:.0f}")
    debug_log('')

    token_data = []
    
    for sym in TOKENS:
        if sym in holdings:
            d = holdings[sym]
            debug_log(f"📊 Fetching market data for {sym}...")
            price_hive, vol24_hive = get_market_info(sym)
            total_amount = d['liquid'] + d['staked'] + d['delegated_away']
            price_usd = price_hive * hive_usd
            vol24_usd = vol24_hive * hive_usd
            total_usd = total_amount * price_usd
            total_hive = total_amount * price_hive
            total_btc = total_usd / btc_usd if btc_usd > 0 else 0
            
            token_data.append({
                "symbol": sym,
                "liquid": d['liquid'],
                "staked": d['staked'],
                "delegated": d['delegated_away'],
                "price_hive": price_hive,
                "price_usd": price_usd,
                "volume_24h_usd": vol24_usd,
                "total_usd": total_usd,
                "total_hive": total_hive,
                "total_btc": total_btc
            })
        else:
            debug_log(f"❌ No holdings for {sym}... Printing all as zero.")
            token_data.append({
                "symbol": sym,
                "liquid": 0.0,
                "staked": 0.0,
                "delegated": 0.0,
                "price_hive": 0.0,
                "price_usd": 0.0,
                "volume_24h_usd": 0.0,
                "total_usd": 0.0,
                "total_hive": 0.0,
                "total_btc": 0.0
            })

    if token_data:
        print()
        display_table(token_data, hive_usd, btc_usd, ACCOUNT)
    else:
        print("❌ No token data to display")

if __name__ == "__main__":
    main()
