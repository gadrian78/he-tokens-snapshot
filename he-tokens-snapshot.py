######################################
#
# My Hive Engine Tokens Snapshot
#
# Created by https://peakd.com/@gadrian using "vibe" coding in June 2025.
#
# Use it or modify to your needs freely. Keep this author details and add to it, if you build on it.
#
######################################

from datetime import datetime
from prettytable import PrettyTable, TableStyle
import argparse

from hiveengine.api import Api
from hiveengine.market import Market

# Import configs
from config import DEFAULT_ACCOUNT, DEFAULT_TOKENS

# Import our utility functions
from regular_tokens import (
    debug_log as util_debug_log,
    get_hive_price_usd,
    get_btc_price_usd,
    get_token_holdings,
    get_market_info,
    fetch_all_tokens,
    clear_caches
)

from utils import (
    validate_token,
    validate_username,
)

# Import diesel pool functions
from diesel_pools import (
    get_user_pool_portfolio,
    display_diesel_pools_table,
    set_debug_mode
)

api = Api()
market = Market(api)

VERSION = "1.31"

DEBUG = False

def debug_log(text):
    """Local debug logging function that respects the DEBUG flag"""
    if DEBUG:
        print(text)

# Override the utility module's debug_log function
util_debug_log.debug_log = debug_log

# Set debug mode for diesel pools module if available
set_debug_mode(DEBUG)

def display_table(token_data, hive_price_usd, btc_price_usd, account):
    """Display token holdings in a formatted table"""
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
        total = token["liquid"] + token["staked"] + token["delegated"]
        if total > 0:
            table.add_row([
                token["symbol"],
                f'{token["liquid"]:,.3f}',
                f'{token["staked"]:,.3f}',
                f'{token["delegated"]:,.3f}',
                f'{total:,.3f}',
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

    if len(sorted_tokens) > 1:  # Only add totals if more than one token
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

    print("💰 TOKEN HOLDINGS:")
    print(table)

def parse_arguments():
    """Command-line arguments parsing"""
    parser = argparse.ArgumentParser(
        description=f"My Hive Engine Tokens Snapshot v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 he-tokens-snapshot.py
  python3 he-tokens-snapshot.py -u alice
  python3 he-tokens-snapshot.py -u bob -t SPS LEO DEC
  python3 he-tokens-snapshot.py --username charlie --tokens SWAP.BTC DBOND INCOME
  python3 he-tokens-snapshot.py --debug

Remarks:
  - Username must be a valid Hive username.
  - Tokens must be valid Hive-Engine tokens.
  - Diesel pools are tracked automatically.
  - Use --debug to see detailed processing information.

Tip:
  Use redirect to have the output in a file instead of the screen.
        """
    )
    
    parser.add_argument(
        '-u', '--username',
        type=str,
        help=f'Hive username to check (default: {DEFAULT_ACCOUNT})'
    )
    
    parser.add_argument(
        '-t', '--tokens',
        nargs='+',
        type=str,
        help=f'List of tokens to snapshot (default: {" ".join(DEFAULT_TOKENS)})'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )
    
    return parser.parse_args()

def main():
    global DEBUG
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Set debug mode
    if (args.debug): DEBUG = args.debug
    
    # Update debug functions
    util_debug_log = debug_log
    set_debug_mode(DEBUG)
    
    # Use command line arguments if provided, otherwise use defaults
    ACCOUNT = args.username if args.username else DEFAULT_ACCOUNT
    TOKENS = [token.upper() for token in args.tokens] if args.tokens else DEFAULT_TOKENS

    if ACCOUNT:
        ACCOUNT = ACCOUNT.lower()
        
    # Validate username
    is_valid_user, user_msg = validate_username(ACCOUNT)
    if not is_valid_user:
        print(f"❌ Invalid username '{ACCOUNT}': {user_msg}")
        print("   Username must be a valid Hive username.")
        return
    
    debug_log(f"🎯 Account: @{ACCOUNT}")
    debug_log("🔍 Fetching token list from Hive Engine for validation...")
    
    valid_token_symbols = fetch_all_tokens(api)
    debug_log(f"✅ Found {len(valid_token_symbols)} valid tokens")

    # Validate tokens
    for token in TOKENS:
        is_valid_token, token_msg = validate_token(token, valid_token_symbols)
        if not is_valid_token:
            print(f"❌ Invalid token: {token_msg}")
            print("   Token must be a valid Hive-Engine token.")
            return

    # Display what we're using
    debug_log(f"🪙 Tokens: {', '.join(TOKENS)}")
    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    debug_log(f"   Snapshot date/time: {dt}")
    debug_log('')

    print(f"🔄 Fetching data for @{ACCOUNT}...")

    # Get regular token holdings
    debug_log("📊 Fetching token holdings...")
    holdings = get_token_holdings(api, ACCOUNT, TOKENS)        

    # Get price data
    debug_log("💰 Fetching HIVE and BTC prices...")
    hive_usd = get_hive_price_usd()
    btc_usd = get_btc_price_usd()
    
    debug_log(f"💰 HIVE: ${hive_usd:.6f}, BTC: ${btc_usd:.0f}")

    # Process regular tokens
    token_data = []
    token_prices = {}  # Store prices for diesel pool calculations

    for sym in TOKENS:
        d = holdings.get(sym, {"liquid": 0.0, "staked": 0.0, "delegated_away": 0.0})
        debug_log(f"📊 Fetching market data for {sym}...")
        price_hive, vol24_hive = get_market_info(api, market, sym)
        
        # Store price for diesel pool calculations
        token_prices[sym] = price_hive
        
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

    # Get diesel pool holdings if available
    pool_data = []
    debug_log("🏊 Fetching diesel pool positions...")

    # Get additional token prices that might be needed for pools
    # We'll let the diesel pool module handle price fetching for pool tokens
    pool_data = get_user_pool_portfolio(ACCOUNT, api, token_prices)

    if pool_data:
        debug_log(f"✅ Found {len(pool_data)} diesel pool positions")
        # Convert to USD and BTC values
        for pool in pool_data:
            pool["total_usd"] = pool["total_hive"] * hive_usd
            pool["total_btc"] = pool["total_usd"] / btc_usd if btc_usd > 0 else 0
    else:
        debug_log("ℹ️ No diesel pool positions found")

    # Display header information
    print()
    print(f"🎯 Account: @{ACCOUNT}")
    print(f"🪙 Tokens: {', '.join(TOKENS)}")
    print(f"   Snapshot date/time: {dt}")
    print()
    print(f"💰 HIVE Price: ${hive_usd:.6f}")
    print(f"🪙 BTC Price: ${btc_usd:,.0f}")
    print()

    # Display results
    has_token_data = any(t["total_usd"] > 0 for t in token_data)
    has_pool_data = len(pool_data) > 0

    if has_token_data:
        display_table(token_data, hive_usd, btc_usd, ACCOUNT)
        print()
    else:
        print("ℹ️ No significant token holdings found")
    
    if has_pool_data:
        display_diesel_pools_table(pool_data, hive_usd, btc_usd, ACCOUNT)
        print()
    else:
        debug_log("ℹ️ No diesel pool positions found")
    
    # Display combined totals if both exist
    if has_token_data and has_pool_data:
        total_tokens_usd = sum(t["total_usd"] for t in token_data)
        total_pools_usd = sum(p["total_usd"] for p in pool_data)
        total_combined_usd = total_tokens_usd + total_pools_usd
        
        total_tokens_hive = sum(t["total_hive"] for t in token_data)
        total_pools_hive = sum(p["total_hive"] for p in pool_data)
        total_combined_hive = total_tokens_hive + total_pools_hive
        
        total_combined_btc = total_combined_usd / btc_usd if btc_usd > 0 else 0
        
        print("=" * 80)
        print("📊 COMBINED PORTFOLIO SUMMARY:")
        print(f"   Regular Tokens:   ${total_tokens_usd:8,.2f} USD  |  {total_tokens_hive:9,.3f} HIVE")
        print(f"   Diesel Pools:     ${total_pools_usd:8,.2f} USD  |  {total_pools_hive:9,.3f} HIVE") 
        print(f"   TOTAL PORTFOLIO:  ${total_combined_usd:8,.2f} USD  |  {total_combined_hive:9,.3f} HIVE  |  {total_combined_btc:3.8f} BTC")
        print("=" * 80)

    # Add BTC/HIVE ratio, and prices of HIVE and BTC
    if btc_usd > 0 and hive_usd > 0:
        hive_btc_ratio = int(btc_usd / hive_usd)
        print()
        print(f"  HIVE:BTC ≈ 1/{hive_btc_ratio:,.0f}")
        print(f"  HIVE:USD = ${hive_usd:,.6f}")
        print(f"  BTC :USD = ${btc_usd:,.0f}")
        print()

    # Clear caches at the end
    clear_caches()

if __name__ == "__main__":
    main()
